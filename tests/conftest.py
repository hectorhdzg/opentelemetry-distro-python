# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Opt-in Python logger isolation for logging pipeline tests."""

import logging

import pytest


@pytest.fixture(name="isolated_loggers")
def _isolated_loggers(monkeypatch):
    """Restore handlers and logger settings without touching OTel globals."""
    loggers = {}

    def get_logger(name=""):
        logger = logging.getLogger(name)
        if logger not in loggers:
            loggers[logger] = logger.level
            monkeypatch.setattr(logger, "handlers", [])
            logger.setLevel(logging.WARNING)
            monkeypatch.setattr(logger, "disabled", False)
            monkeypatch.setattr(logger, "propagate", True)
        return logger

    original_disable = logging.root.manager.disable
    logging.disable(logging.NOTSET)
    get_logger()
    try:
        yield get_logger
    finally:
        for logger, original_level in loggers.items():
            for handler in logger.handlers:
                handler.close()
            logger.setLevel(original_level)
        logging.disable(original_disable)
