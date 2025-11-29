import fnmatch
import collections
import calendar
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.inventory import Inventory
from fava.ext import FavaExtensionBase
from fava.context import g

print("Loading fava_budget_freedom module...")

class BudgetFreedom(FavaExtensionBase):

    report_title = "Budget Freedom"

    def __init__(self, ledger, config=None):
        print("BudgetFreedom extension initialized!")
        super().__init__(ledger, config)

    def generate_budget_report(self):
        """
        Parses custom 'budget' directives and calculates actual usage based on wildcards.
        """
        entries, date_range = self._get_context()
        report_start, report_end = self._get_report_date_range(date_range)
        time_percent = self._calculate_year_progress(date_range)
        budgets = self._parse_budget_definitions(report_end)
        
        report_data = self._generate_report_rows(
            budgets, entries, report_start, report_end, time_percent
        )
            
        return {
            'report_data': report_data,
            'range_start': report_start,
            'range_end': report_end
        }

    def _get_report_date_range(self, date_range):
        if date_range:
            return date_range.begin, date_range.end - relativedelta(days=1)
        
        today = date.today()
        return date(today.year, 1, 1), today

    def _calculate_year_progress(self, date_range):
        today = date.today()
        is_full_year = False
        report_year = today.year

        if date_range:
            if (date_range.begin.month == 1 and date_range.begin.day == 1 and
                date_range.end.month == 1 and date_range.end.day == 1 and
                date_range.end.year == date_range.begin.year + 1):
                is_full_year = True
                report_year = date_range.begin.year
        # else:
        #     is_full_year = False

        if not is_full_year:
            return None

        if today.year > report_year:
            return 100
        elif today.year < report_year:
            return 0
        
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)
        total_days = (end - start).days + 1
        passed = (today - start).days + 1
        return (passed / total_days) * 100

    def _generate_report_rows(self, budgets, entries, report_start, report_end, time_percent):
        report_data = []
        for pattern, budget_list in budgets.items():
            latest_budget = budget_list[-1]
            
            effective_budget, rollover = self._calculate_effective_budget(
                budget_list, report_start, report_end
            )

            actual_amount = self._calculate_usage(
                entries, pattern, effective_budget.currency, report_start, report_end
            )
            
            percent = 0
            actual_val = actual_amount.number if actual_amount.number is not None else Decimal(0)
            if effective_budget.number != 0:
                percent = (actual_val / effective_budget.number) * 100
            
            account_name = self._clean_pattern_for_link(pattern)

            report_data.append({
                'pattern': pattern,
                'account_name': account_name,
                'budget': effective_budget,
                'actual': actual_amount,
                'percent': percent,
                'time_percent': time_percent,
                'period': latest_budget['period'],
                'rollover': rollover,
                'is_rollover': latest_budget['rollover']
            })
        return report_data

    def _clean_pattern_for_link(self, pattern):
        if pattern.endswith(":*"):
            return pattern[:-2]
        elif pattern.endswith("*"):
            return pattern[:-1]
        return pattern

    def _get_context(self):
        try:
            return g.filtered.entries, g.filtered.date_range
        except:
            return self.ledger.all_entries, None

    def _parse_budget_definitions(self, end_date):
        budget_definitions = []
        for entry in self.ledger.all_entries:
            if isinstance(entry, data.Custom) and entry.type == "budget":
                if entry.date >= end_date:
                    continue

                if len(entry.values) >= 3:
                    pattern = str(entry.values[0].value)
                    period = str(entry.values[1].value)
                    amount_val = entry.values[2].value
                    
                    amount = self._parse_amount(amount_val)
                    if not amount:
                        continue

                    rollover = False
                    if len(entry.values) > 3:
                        if str(entry.values[3].value).lower() == "rollover":
                            rollover = True

                    budget_definitions.append({
                        'date': entry.date,
                        'pattern': pattern,
                        'amount': amount,
                        'period': period,
                        'rollover': rollover
                    })

        budgets_by_pattern = collections.defaultdict(list)
        for b in budget_definitions:
            budgets_by_pattern[b['pattern']].append(b)
            
        for p in budgets_by_pattern:
            budgets_by_pattern[p].sort(key=lambda x: x['date'])
            
        return budgets_by_pattern

    def _parse_amount(self, amount_val):
        if isinstance(amount_val, str):
            try:
                parts = amount_val.split()
                if len(parts) == 2:
                    return Amount(Decimal(parts[0]), parts[1])
            except:
                return None
        elif isinstance(amount_val, Amount):
            return amount_val
        return None

    def _calculate_effective_budget(self, budget_list, report_start, report_end):
        latest_budget = budget_list[-1]
        should_calculate_rollover = latest_budget['rollover'] and latest_budget['period'] == 'monthly'
        
        if not should_calculate_rollover:
            return latest_budget['amount'], Decimal(0)

        print(f"DEBUG: Pattern {latest_budget['pattern']}")
        print(f"DEBUG: Report Range: {report_start} to {report_end}")
        
        # 1. Calculate Rollover from Year Start up to Report Start
        rollover_amount = self._calculate_accumulated_rollover(
            budget_list, report_start
        )
        print(f"DEBUG: Rollover Amount: {rollover_amount}")
        
        # 2. Calculate Budget for the Report Period itself
        period_budget_accumulator = self._calculate_period_budget(
            budget_list, report_start, report_end
        )
        print(f"DEBUG: Period Accumulator: {period_budget_accumulator}")
        
        total = Amount(period_budget_accumulator + rollover_amount, latest_budget['amount'].currency)
        return total, rollover_amount

    def _calculate_accumulated_rollover(self, budget_list, report_start):
        latest_budget = budget_list[-1]
        year_start = date(report_start.year, 1, 1)
        
        # Find the earliest relevant budget date for this year
        # Or just start from year_start, assuming budgets exist or are 0 before definition?
        # Usually we start from max(year_start, first_budget_date)
        first_budget_date = budget_list[0]['date']
        calc_start = max(year_start, first_budget_date)
        
        current_month = date(calc_start.year, calc_start.month, 1)
        if current_month < calc_start:
             current_month = current_month + relativedelta(months=1)

        rollover_amount = Decimal(0)
        
        while current_month < report_start:
            month_end = current_month + relativedelta(months=1)
            
            active_budget = self._get_active_budget(budget_list, current_month)
            if active_budget:
                past_actual = self._get_usage_for_period(
                    current_month, month_end, active_budget['pattern'], active_budget['amount'].currency
                )
                
                past_number = past_actual.number if past_actual.number is not None else Decimal(0)
                remainder = active_budget['amount'].number - past_number
                rollover_amount += remainder
            
            current_month += relativedelta(months=1)
            
        return rollover_amount

    def _calculate_period_budget(self, budget_list, report_start, report_end):
        period_budget_accumulator = Decimal(0)
        
        current_month = date(report_start.year, report_start.month, 1)
        if current_month < report_start:
             current_month = current_month + relativedelta(months=1)
        
        cutoff_date = report_end
        if cutoff_date == date.max:
            cutoff_date = date.today()
        
        while current_month <= cutoff_date:
            active_budget = self._get_active_budget(budget_list, current_month)
            if active_budget:
                period_budget_accumulator += active_budget['amount'].number
            current_month += relativedelta(months=1)
            
        return period_budget_accumulator

    def _get_active_budget(self, budget_list, target_date):
        active = None
        for b in budget_list:
            if b['date'] <= target_date:
                active = b
            else:
                break
        return active

    def _get_usage_for_period(self, start_date, end_date, pattern, currency):
        inventory = Inventory()
        for entry in self.ledger.all_entries:
            if isinstance(entry, data.Transaction) and entry.date >= start_date and entry.date < end_date:
                self._accumulate_entry(entry, pattern, inventory)
        return inventory.get_currency_units(currency)

    def _calculate_usage(self, entries, pattern, currency, start_date, end_date):
        inventory = Inventory()
        for entry in entries:
            if isinstance(entry, data.Transaction):
                if entry.date >= start_date and entry.date <= end_date:
                    self._accumulate_entry(entry, pattern, inventory)
        return inventory.get_currency_units(currency)

    def _accumulate_entry(self, entry, pattern, inventory):
        for posting in entry.postings:
            if self._matches_pattern(posting.account, pattern):
                inventory.add_amount(posting.units)

    def _matches_pattern(self, account, pattern):
        if '*' in pattern:
             return fnmatch.fnmatch(account, pattern)
        else:
            return account == pattern or account.startswith(pattern + ":")
