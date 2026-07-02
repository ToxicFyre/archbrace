"""AR001 positive fixture: a function longer than a small configured limit."""


def long_function(value):
    total = value
    total += 1
    total += 2
    total += 3
    total += 4
    return total
