import re

GHANA_E164 = re.compile(r"^\+233[0-9]{9}$")


def normalise_phone(value: str) -> str | None:
    """Return the number as +233XXXXXXXXX, or None if it isn't a Ghana mobile number.

    Accepts 0241234567, 024 123 4567, 233241234567 and +233241234567.
    """
    digits = re.sub(r"[\s\-()]", "", value)
    if digits.startswith("+"):
        number = digits
    elif digits.startswith("233"):
        number = "+" + digits
    elif digits.startswith("0") and len(digits) == 10:
        number = "+233" + digits[1:]
    else:
        return None
    return number if GHANA_E164.match(number) else None
