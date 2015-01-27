#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    test.__main__
    ~~~~~~~~~~~~~

    :copyright: 2015 by `University of Denver <http://pardee.du.edu/>`_
    :license: Creative Commons 4.0 License (`CC BY-NC-SA 4.0`_).

    .. _`CC BY-NC-SA 4.0`: http://creativecommons.org/licenses/by-nc-sa/4.0/

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
