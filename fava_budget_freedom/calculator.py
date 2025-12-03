from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from beancount.core.amount import Amount

class BudgetCalculator:
    """
    Calculates effective budget amounts, handling periods and rollovers.
    """
    def __init__(self, usage_calculator):
        self.usage_calculator = usage_calculator

    def calculate_effective_budget(self, budget_list, report_start, report_end):
        """
        Calculate the effective budget for the report period, including rollovers.
        
        Args:
            budget_list: List of budget definitions for a pattern.
            report_start: Start date of the report.
            report_end: End date of the report.
            
        Returns:
            Tuple of (Total Amount, Rollover Amount)
        """
        latest_budget = budget_list[-1]
        should_calculate_rollover = latest_budget['rollover'] and latest_budget['period'] == 'monthly'
        
        if not should_calculate_rollover:
            return latest_budget['amount'], Decimal(0)

        # 1. Calculate Rollover from Year Start up to Report Start
        rollover_amount = self._calculate_accumulated_rollover(
            budget_list, report_start
        )
        
        # 2. Calculate Budget for the Report Period itself
        period_budget_accumulator = self._calculate_period_budget(
            budget_list, report_start, report_end
        )
        
        total = Amount(period_budget_accumulator + rollover_amount, latest_budget['amount'].currency)
        return total, rollover_amount

    def _calculate_accumulated_rollover(self, budget_list, report_start):
        year_start = date(report_start.year, 1, 1)
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
                past_actual = self.usage_calculator.calculate_usage_for_period(
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
