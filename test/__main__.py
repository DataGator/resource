#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    test.__main__
    ~~~~~~~~~~~~~

    :copyright: 2015 by `University of Denver <http://pardee.du.edu/>`_
    :license: Apache 2.0, see LICENSE for more details.

    :author: `LIU Yu <liuyu@opencps.net>`_
    :date: 2015/01/19
"""

from __future__ import unicode_literals

__all__ = []


import os
import os.path
import sys

from . import test_suite
from .config import unittest, to_native


if __name__ == '__main__':
    unittest.main(defaultTest=to_native("test_suite"))
