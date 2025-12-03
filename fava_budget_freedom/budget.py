import collections
from beancount.core import data
from .utils import parse_amount

class BudgetParser:
    """
    Parses custom budget directives from the ledger.
    """
    def __init__(self, entries):
        self.entries = entries

    def parse_budget_definitions(self, end_date):
        """
        Parse custom 'budget' directives from entries up to end_date.
        
        Args:
            end_date: The cutoff date for budget definitions.
            
        Returns:
            A dictionary mapping patterns to a list of budget definitions sorted by date.
        """
        budget_definitions = []
        for entry in self.entries:
            if isinstance(entry, data.Custom) and entry.type == "budget":
                if entry.date >= end_date:
                    continue

                if len(entry.values) >= 3:
                    pattern = str(entry.values[0].value)
                    period = str(entry.values[1].value)
                    amount_val = entry.values[2].value
                    
                    amount = parse_amount(amount_val)
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
