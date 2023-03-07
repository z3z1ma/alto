# MIT License
# Copyright (c) 2023 Alex Butler
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
"""Setup logging for alto.

This module sets up logging for alto. It is super simple, and just sets up a
logger with a single handler. The handler is a StreamHandler, which writes to
sys.stderr. The format is just the message, with no timestamp or anything else.

In the future, this module may be expanded to allow for more complex logging.
"""
import logging
import sys

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
logging.basicConfig(stream=sys.stderr, format="%(message)s")
