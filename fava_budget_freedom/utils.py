import fnmatch
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from beancount.core.amount import Amount

def matches_pattern(account, pattern):
    """
    Check if account matches the wildcard pattern.
    
    Args:
        account: The account name to check.
        pattern: The pattern to match against (can contain *).
    """
    if '*' in pattern:
         return fnmatch.fnmatch(account, pattern)
    else:
        return account == pattern or account.startswith(pattern + ":")

def is_subset(child_pattern, parent_pattern):
    """
    Check if child_pattern is a subset of parent_pattern.
    
    Args:
        child_pattern: The potential subset pattern.
        parent_pattern: The superset pattern.
    """
    if '*' in parent_pattern:
        return fnmatch.fnmatch(child_pattern, parent_pattern)
    else:
        return child_pattern.startswith(parent_pattern + ":")

def clean_pattern_for_link(pattern):
    """
    Remove wildcards to get a linkable account name.
    
    Args:
        pattern: The budget pattern.
    """
    if pattern.endswith(":*"):
        return pattern[:-2]
    elif pattern.endswith("*"):
        return pattern[:-1]
    return pattern

def parse_amount(amount_val):
    """
    Parse amount from string or Amount object.
    
    Args:
        amount_val: The amount value from the custom directive.
    """
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

def get_report_date_range(date_range):
    """
    Determine the start and end date for the report.
    
    Args:
        date_range: The date range from Fava context.
    """
    if date_range:
        return date_range.begin, date_range.end - relativedelta(days=1)
    
    today = date.today()
    return date(today.year, 1, 1), today

def calculate_year_progress(date_range):
    """
    Calculate the percentage of time passed in the selected year.
    Returns None if the range is not a full year.
    
    Args:
        date_range: The date range from Fava context.
    """
    today = date.today()
    is_full_year = False
    report_year = today.year

    if date_range:
        if (date_range.begin.month == 1 and date_range.begin.day == 1 and
            date_range.end.month == 1 and date_range.end.day == 1 and
            date_range.end.year == date_range.begin.year + 1):
            is_full_year = True
            report_year = date_range.begin.year

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
