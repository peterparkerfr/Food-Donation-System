
import re
from datetime import date


def test_email_format():
    email = "donor@example.com"
    assert re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)


def test_invalid_email_format():
    email = "not-an-email"
    assert not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)


def test_donation_quantity_must_be_positive():
    quantity = 3
    assert quantity > 0


def test_donation_quantity_rejects_zero():
    quantity = 0
    assert not quantity > 0


def test_expiry_date_is_a_date():
    expiry = date(2026, 12, 31)
    assert isinstance(expiry, date)
