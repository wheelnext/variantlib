#! /usr/bin/python
# -*- coding: utf-8 -*-

import logging as _logging
import sys
from typing import Optional


class _LoggerAPI:
    __slots__ = ["_logger"]

    # Level 0
    NOTSET = _logging.NOTSET

    # Level 10
    DEBUG = _logging.DEBUG

    # Level 20
    INFO = _logging.INFO

    # Level 30
    WARNING = _logging.WARNING

    # Level 40
    ERROR = _logging.ERROR

    # Level 50
    CRITICAL = _logging.CRITICAL

    def __init__(self) -> None:
        object.__setattr__(self, "_logger", _LoggerAPI.setup_logger())

    #
    # proxying all function calls
    #
    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return getattr(object.__getattribute__(self, "_logger"), name)

    def __delattr__(self, name):
        try:
            super().__delattr__(name)
        except AttributeError:
            delattr(object.__getattribute__(self, "_logger"), name)

    def __setattr__(self, name, value):
        try:
            super().__setattr__(name, value)
        except AttributeError:
            setattr(self._logger, name, value)

    def __str__(self):
        return str(object.__getattribute__(self, "_logger"))

    def __repr__(self):
        return repr(object.__getattribute__(self, "_logger"))

    def getLogger(self, name) -> _logging.Logger:  # noqa: N802
        return _logging.getLogger(name)

    #
    # actual logger definition
    #

    @classmethod
    def setup_logger(
        cls, handlers: Optional[list] = None, formatter: Optional[_logging.Formatter] = None
    ):
        if handlers is None:
            # Add the output handler.
            handler_stdout = _logging.StreamHandler(sys.stdout)
            handler_stdout.addFilter(lambda record: record.levelno <= _logging.INFO)

            handler_stderr = _logging.StreamHandler(sys.stderr)
            handler_stderr.addFilter(lambda record: record.levelno > _logging.INFO)

            handlers = [handler_stdout, handler_stderr]

        if formatter is None:
            # ---------------- Date Format - Directives ----------------
            # %Y: Year with century as a decimal number.
            # %m: Month as a decimal number [01,12].
            # %d: Day of the month as a decimal number [01,31].
            # %H: Hour (24-hour clock) as a decimal number [00,23].
            # %M: Minute as a decimal number [00,59].
            # %S: Second as a decimal number [00,61].
            # ----------------------------------------------------------
            formatter = _logging.Formatter(fmt="VariantLib: %(message)s")

        try:
            # Scope the logger to not conflict with users' loggers.
            _logger = _logging.getLogger("variantlib")

            # ======== Remove any handler if they already existing ========
            try:
                _logger.handlers.clear()
            except AttributeError:
                _logger.handlers = []

            for handler in handlers:
                handler.setFormatter(formatter)
                _logger.addHandler(handler)

        finally:
            _logger.setLevel(level=cls.INFO)

        _logger.propagate = False
        return _logger


_ = _LoggerAPI()
