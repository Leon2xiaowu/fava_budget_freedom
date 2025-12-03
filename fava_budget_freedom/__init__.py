from decimal import Decimal
from datetime import timedelta
from beancount.core.amount import Amount
from beancount.core.inventory import Inventory
from fava.ext import FavaExtensionBase
from fava.context import g

from .utils import get_report_date_range, calculate_year_progress, clean_pattern_for_link, is_subset
from .budget import BudgetParser
from .usage import UsageCalculator
from .calculator import BudgetCalculator

print("Loading fava_budget_freedom module...")

class BudgetFreedom(FavaExtensionBase):
    """
    Fava extension for advanced budget reporting.
    """
    report_title = "Budget Freedom"

    def __init__(self, ledger, config=None):
        print("BudgetFreedom extension initialized!")
        super().__init__(ledger, config)

    def generate_budget_report(self):
        """
        Parses custom 'budget' directives and calculates actual usage based on wildcards.
        """
        entries, date_range = self._get_context()
        report_start, report_end = get_report_date_range(date_range)
        time_percent = calculate_year_progress(date_range)
        
        # Initialize helpers
        budget_parser = BudgetParser(self.ledger.all_entries)
        # UsageCalculator for rollover needs all entries
        usage_calculator_all = UsageCalculator(self.ledger.all_entries)
        budget_calculator = BudgetCalculator(usage_calculator_all)
        
        # UsageCalculator for report rows needs filtered entries (or we pass filtered entries to method)
        usage_calculator_report = UsageCalculator(entries) # Not strictly needed if we pass entries to method

        budgets = budget_parser.parse_budget_definitions(report_end)
        
        report_data = self._generate_report_rows(
            budgets, entries, report_start, report_end, time_percent,
            usage_calculator_report, budget_calculator
        )
        
        total_budget_row = None
        final_report_data = []
        
        for row in report_data:
            if row['pattern'] == "Expenses:*":
                total_budget_row = row
            else:
                final_report_data.append(row)
            
        return {
            'report_data': final_report_data,
            'range_start': report_start,
            'range_end': report_end,
            'total_budget_row': total_budget_row
        }

    def _generate_report_rows(self, budgets, entries, report_start, report_end, time_percent, usage_calculator, budget_calculator):
        # Pre-calculate usages to ensure each transaction counts only towards the most specific budget
        usage_map = usage_calculator.calculate_all_usages(entries, budgets, report_start, report_end)
        
        # First pass: Calculate initial effective budgets for all patterns
        effective_budgets = {}
        rollovers = {}
        latest_budgets = {}
        
        for pattern, budget_list in budgets.items():
            latest_budgets[pattern] = budget_list[-1]
            eff_budget, rollover = budget_calculator.calculate_effective_budget(
                budget_list, report_start, report_end
            )
            effective_budgets[pattern] = eff_budget
            rollovers[pattern] = rollover

        # Second pass: Adjust budgets by subtracting direct children budgets
        adjusted_budgets = {}
        for parent_pattern, parent_budget in effective_budgets.items():
            subtracted_amount = Decimal(0)
            
            # Find all subsets
            candidates = []
            for child_pattern, child_budget in effective_budgets.items():
                if parent_pattern == child_pattern:
                    continue
                if child_budget.currency != parent_budget.currency:
                    continue
                
                if is_subset(child_pattern, parent_pattern):
                    candidates.append(child_pattern)
            
            # Filter for direct children only
            direct_children = []
            for c in candidates:
                is_nested = False
                for other in candidates:
                    if c == other: continue
                    if is_subset(c, other):
                        is_nested = True
                        break
                if not is_nested:
                    direct_children.append(c)
            
            for child_pattern in direct_children:
                subtracted_amount += effective_budgets[child_pattern].number
            
            new_amount = parent_budget.number - subtracted_amount
            adjusted_budgets[parent_pattern] = Amount(new_amount, parent_budget.currency)

        report_data = []
        for pattern in budgets:
            latest_budget = latest_budgets[pattern]
            effective_budget = adjusted_budgets[pattern]
            gross_budget = effective_budgets[pattern]
            rollover = rollovers[pattern]

            # Get actual usage from the pre-calculated map
            inventory = usage_map.get(pattern, Inventory())
            actual_amount = inventory.get_currency_units(effective_budget.currency)
            
            percent = 0
            actual_val = actual_amount.number if actual_amount.number is not None else Decimal(0)
            if effective_budget.number != 0:
                percent = (actual_val / effective_budget.number) * 100
            
            # Calculate total actual usage for gross percent (including children)
            total_actual = usage_calculator.calculate_usage_for_period(
                report_start, report_end + timedelta(days=1), pattern, gross_budget.currency
            )
            total_actual_val = total_actual.number if total_actual.number is not None else Decimal(0)

            gross_percent = 0
            if gross_budget.number != 0:
                gross_percent = (total_actual_val / gross_budget.number) * 100
            
            account_name = clean_pattern_for_link(pattern)

            report_data.append({
                'pattern': pattern,
                'account_name': account_name,
                'budget': effective_budget,
                'unadjusted_budget': gross_budget,
                'actual': actual_amount,
                'total_actual': total_actual,
                'percent': percent,
                'unadjusted_percent': gross_percent,
                'time_percent': time_percent,
                'period': latest_budget['period'],
                'rollover': rollover,
                'is_rollover': latest_budget['rollover']
            })
        return report_data

    def _get_context(self):
        try:
            return g.filtered.entries, g.filtered.date_range
        except:
            return self.ledger.all_entries, None
