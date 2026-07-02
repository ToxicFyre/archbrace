"""AR101 negative fixture: a production module using a logger."""

import logging

logger = logging.getLogger(__name__)


def show(value):
    logger.info(value)
