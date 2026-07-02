"""AR102 positive fixture: a broad exception handler that swallows the error."""


def run():
    try:
        risky()
    except Exception:
        pass
