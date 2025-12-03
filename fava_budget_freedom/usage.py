from beancount.core import data
from beancount.core.inventory import Inventory
from .utils import matches_pattern

class UsageCalculator:
    """
    Calculates actual usage of budgets based on transaction entries.
    """
    def __init__(self, all_entries):
        """
        Initialize with all ledger entries.
        
        Args:
            all_entries: All entries from the ledger (used for historical calculations).
        """
        self.all_entries = all_entries

    def calculate_usage_for_period(self, start_date, end_date, pattern, currency):
        """
        Calculate actual usage for a specific pattern and period using all entries.
        Used for rollover calculation.
        
        Args:
            start_date: Start date (inclusive).
            end_date: End date (exclusive).
            pattern: Account pattern.
            currency: Currency to sum.
        """
        inventory = Inventory()
        for entry in self.all_entries:
            if isinstance(entry, data.Transaction) and entry.date >= start_date and entry.date < end_date:
                self._accumulate_entry(entry, pattern, inventory)
        return inventory.get_currency_units(currency)

    def calculate_all_usages(self, entries, budgets, start_date, end_date):
        """
        Calculate usage for all budgets in the given period using the provided entries.
        Respects specificity (longest pattern wins).
        
        Args:
            entries: Filtered entries for the report.
            budgets: Dictionary of budget definitions.
            start_date: Start date (inclusive).
            end_date: End date (inclusive).
        """
        usage = {pattern: Inventory() for pattern in budgets}
        patterns = list(budgets.keys())
        
        for entry in entries:
            if isinstance(entry, data.Transaction):
                if entry.date >= start_date and entry.date <= end_date:
                    for posting in entry.postings:
                        account = posting.account
                        best_pattern = None
                        best_len = -1
                        
                        for pattern in patterns:
                            if matches_pattern(account, pattern):
                                # Specificity rule: longer pattern wins
                                if len(pattern) > best_len:
                                    best_pattern = pattern
                                    best_len = len(pattern)
                        
                        if best_pattern:
                            usage[best_pattern].add_amount(posting.units)
        return usage

    def _accumulate_entry(self, entry, pattern, inventory):
        for posting in entry.postings:
            if matches_pattern(posting.account, pattern):
                inventory.add_amount(posting.units)
