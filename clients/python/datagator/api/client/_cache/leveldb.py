# -*- coding: utf-8 -*-
"""
    datagator.api.client._cache.leveldb
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2015 by `University of Denver <http://pardee.du.edu/>`_
    :license: Apache 2.0, see LICENSE for more details.

    :author: `LIU Yu <liuyu@opencps.net>`_
    :date: 2015/03/25
"""

from __future__ import unicode_literals, with_statement

import io
import json
import logging
import tempfile

from .._compat import to_native, to_bytes

from . import CacheManager

# this has to be absolute import, otherwise we will be self-importing.
_leveldb = __import__("leveldb")


__all__ = ['LevelDbCache', ]
__all__ = [to_native(n) for n in __all__]


_log = logging.getLogger(__name__)


class LevelDbCache(CacheManager):
    """
    LevelDB backend for disk-persisted cache management
    """

    __slots__ = ['__db', '__fs', ]

    def __init__(self, fs=None):
        self.__fs = fs or tempfile.mkdtemp(suffix=".DataGatorCache")
        self.__db = None
        pass

    @property
    def db(self):
        if self.__db is None:
            self.__db = _leveldb.LevelDB(filename=to_native(self.__fs))
        return self.__db

    def delete(self, key):
        return self.db.Delete(to_bytes(key))

    def exists(self, key):
        try:
            raw = self.db.Get(to_bytes(key))
        except KeyError:
            return False
        else:
            return True
        return False  # should NOT reach here

    def get(self, key, value=None):
        try:
            raw = self.db.Get(to_bytes(key))
        except KeyError:
            return value
        else:
            return json.loads(to_native(raw))
        return value  # should NOT reach here

    def put(self, key, value):
        return self.db.Put(to_bytes(key), to_bytes(json.dumps(value)))

    def __del__(self):
        try:
            self.__db = None
            _leveldb.DestroyDB(to_native(self.__fs))
            shutil.rmtree(self.__fs)
            self.__fs = None
        except:
            pass
        finally:
            self.__db = self.__fs = None
        pass

    pass