"""AR102 negative fixture: a broad handler that logs and re-raises."""

import logging

logger = logging.getLogger(__name__)


def run():
    try:
        risky()
    except Exception:
        logger.exception("risky failed")
        raise
