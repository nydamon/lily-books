"""ISBN generation utilities."""

import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def generate_isbn_13() -> str:
    """Generate a valid ISBN-13 number."""
    # Start with 978 (common prefix for books)
    prefix = "978"
    
    # Generate 9 random digits
    middle = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    
    # Calculate check digit
    isbn_without_check = prefix + middle
    check_digit = calculate_isbn13_check_digit(isbn_without_check)
    
    return isbn_without_check + str(check_digit)

def calculate_isbn13_check_digit(isbn_12: str) -> int:
    """Calculate the check digit for ISBN-13."""
    total = 0
    for i, digit in enumerate(isbn_12):
        weight = 1 if i % 2 == 0 else 3
        total += int(digit) * weight
    
    remainder = total % 10
    return 0 if remainder == 0 else 10 - remainder

def generate_isbn_10() -> str:
    """Generate a valid ISBN-10 number."""
    # Generate 9 random digits
    middle = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    
    # Calculate check digit
    isbn_without_check = middle
    check_digit = calculate_isbn10_check_digit(isbn_without_check)
    
    return isbn_without_check + str(check_digit)

def calculate_isbn10_check_digit(isbn_9: str) -> str:
    """Calculate the check digit for ISBN-10."""
    total = 0
    for i, digit in enumerate(isbn_9):
        total += int(digit) * (10 - i)
    
    remainder = total % 11
    if remainder == 0:
        return '0'
    elif remainder == 1:
        return 'X'
    else:
        return str(11 - remainder)

def generate_isbns_for_book(slug: str, title: str) -> dict:
    """Generate ISBNs for a book (ebook and audiobook)."""
    # Use book title and slug to create deterministic but unique ISBNs
    random.seed(hash(slug + title))
    
    ebook_isbn = generate_isbn_13()
    audiobook_isbn = generate_isbn_13()
    
    # Reset random seed
    random.seed()
    
    return {
        "ebook_isbn": ebook_isbn,
        "audiobook_isbn": audiobook_isbn
    }
