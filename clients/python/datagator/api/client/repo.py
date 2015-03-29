# -*- coding: utf-8 -*-
"""
    datagator.api.client.repo
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2015 by `University of Denver <http://pardee.du.edu/>`_
    :license: Apache 2.0, see LICENSE for more details.

    :author: `LIU Yu <liuyu@opencps.net>`_
    :date: 2015/01/28
"""

from __future__ import unicode_literals, with_statement

import io
import json
import jsonschema
import logging
import tempfile

from . import environ
from ._compat import to_native, to_unicode, to_bytes
from ._entity import Entity, validated


__all__ = ['DataSet', 'Repo', ]
__all__ = [to_native(n) for n in __all__]


_log = logging.getLogger(__name__)


class DataSetRevision(object):

    MAX_PAYLOAD_SIZE = 2 ** 24  # 16 MB
    MAX_BUFFER_SIZE = 2 ** 16   # 64 kB

    __slots__ = ['__uri', '__tmp', '__len', ]

    def __init__(self, uri):
        self.__uri = uri
        super(DataSetRevision, self).__init__()
        self.__tmp = None
        self.__len = 0
        self._rewind()
        pass

    def _rewind(self):
        if len(self) > 0:
            raise AssertionError("cannot rewind a pending revision")
        elif self.__tmp is not None:
            _log.debug("attempting to rewind an empty revision")
            # which is unnecessary, thus the short-cut return
            return
        _log.debug("creating new revision for '{0}'".format(self.__uri))
        f = tempfile.SpooledTemporaryFile(
            max_size=DataSetRevision.MAX_BUFFER_SIZE, suffix=".DataGatorCache")
        for attr in ("readable", "writable", "seekable"):
            if not hasattr(f, attr):
                setattr(f, attr, lambda: True)
        self.__tmp = f
        self.__len = 0
        self.__tmp.write(to_bytes("{"))
        pass

    def _commit(self):
        if len(self) == 0:
            _log.debug("attempting to commit an empty revision")
            # which is unnecessary, thus the short-cut return
            return
        elif self.__tmp is None:
            raise AssertionError("cannot commit an uninitialized revision")
        self.__tmp.write(to_bytes("}"))
        self.__tmp.flush()
        _log.debug("committing revision")
        _log.debug("  - entries count: {0}".format(len(self)))
        _log.debug("  - payload size: {0}".format(self.__tmp.tell()))
        try:
            self.__tmp.seek(0)
            if environ.DATAGATOR_API_VERSION == "v1":
                with validated(Entity.__service__.put(
                        self.__uri, data=self.__tmp), (202, )) as r:
                    # TODO watch task for completion
                    pass
            else:
                with validated(Entity.__service__.patch(
                        self.__uri, data=self.__tmp), (202, )) as r:
                    # TODO watch task for completion
                    pass
        except Exception as e:
            _log.error(e)
            raise
        else:
            # prepare for consecutive revisions
            self.__tmp.close()
            self.__tmp = None
            self.__len = 0
            self._rewind()
        pass

    def __setitem__(self, key, value):
        _log.debug("  - '{0}'".format(key))
        key = json.dumps(key)
        value = value.read() if hasattr(value, "read") else json.dumps(value)
        if len(self):
            self.__tmp.write(to_bytes(", "))
        self.__tmp.write(to_bytes(key))
        self.__tmp.write(to_bytes(": "))
        self.__tmp.write(to_bytes(value))
        self.__len += 1
        if self.__tmp.tell() < DataSetRevision.MAX_PAYLOAD_SIZE:
            return
        self._commit()

    def __len__(self):
        return self.__len

    def __enter__(self):
        self._rewind()
        return self

    def __exit__(self, ext_type, exc_value, traceback):
        if isinstance(exc_value, Exception):
            pass
        else:
            self._commit()
        return False  # re-raise exception

    def __del__(self):
        try:
            if len(self) > 0:
                _log.warning("pending revision left until garbage collection")
                self._commit()
        except:
            _log.error("failed to commit pending revisions")
            raise
        pass

    pass


class DataSet(Entity):

    __slots__ = ['__name', '__repo', '__committer', ]

    def __init__(self, name, repo):
        super(DataSet, self).__init__(self.__class__.__name__)
        self.__name = to_unicode(name)
        self.__repo = repo
        self.__committer = DataSetRevision(self.uri)
        try:
            # the data set may not have been committed to the backend service
            # so we just verify the identifier is valid by the schema
            Entity.__schema__.validate(self.ref)
        except jsonschema.ValidationError:
            raise AssertionError("invalid dataset name")
        pass

    @property
    def uri(self):
        return "{0}/{1}".format(self.repo.name, self.name)

    @property
    def ref(self):
        return dict([
            ("kind", "datagator#DataSet"),
            ("name", self.name),
            ("repo", self.repo.ref),
        ])

    @property
    def name(self):
        return self.__name

    @property
    def repo(self):
        return self.__repo

    @property
    def rev(self):
        content = self.cache
        if "rev" not in content:
            self.cache = None
            content = self.cache
        return content.get("rev", 0)

    def __iter__(self):
        for item in self.cache.get("items", []):
            yield item.get("name")
        pass

    def __setitem__(self, key, value):
        with self.__committer as c:
            _log.debug("appending to revision")
            c[key] = value
        self.cache = None
        pass

    def __delitem__(self, key):
        with self.__committer as c:
            c[key] = None
        self.cache = None

    def update(self, items):
        if isinstance(items, dict):
            items = items.items()
        with self.__committer as c:
            _log.debug("appending to revision")
            for key, value in items:
                c[key] = value
        self.cache = None
        pass

    def __len__(self):
        return self.cache.get("itemsCount", 0)

    pass


class Repo(Entity):

    __slots__ = ['__name', ]

    def __init__(self, name, access_key=None):
        super(Repo, self).__init__(self.__class__.__name__)
        self.__name = to_unicode(name)
        if self.cache is None:
            raise AssertionError("invalid repository '{0}'".format(self.name))
        if access_key is not None:
            Entity.__service__.auth = (self.name, access_key)
        pass

    @property
    def uri(self):
        return self.name

    @property
    def name(self):
        return self.__name

    @property
    def ref(self):
        return dict([
            ("kind", "datagator#Repo"),
            ("name", self.name),
        ])

    def __contains__(self, dsname):
        try:
            # if `dsname` is not a valid name for a DataSet entity, then it is
            # guaranteed to *not* exist in the storage backend.
            ref = DataSet(dsname, self)
            # looking up `Entity.__cache__` is more preferrable than `ds.cache`
            # because the latter may trigger connection to the backend service
            if Entity.__cache__.exists(ref.uri):
                return True
            return ref.cache is not None
        except (AssertionError, RuntimeError, ):
            return False
        return False  # should NOT reach here

    def __getitem__(self, dsname):
        try:
            if dsname in self:
                return DataSet(dsname, self)
        except (AssertionError, ):
            pass
        raise KeyError("invalid dataset '{0}'".format(dsname))

    def __setitem__(self, dsname, items):
        ref = None
        try:
            ref = DataSet(dsname, self)
        except (AssertionError, ):
            raise KeyError("invalid dataset name")
        # inspect input parameters
        if isinstance(items, (dict, list, tuple)):
            # we expect the items to be either a `dict` of {`key`: `DataItem`}
            # or a sequence of pairs (`key`, `DataItem`), where `DataItem` can
            # be (i) a file-like object with serialized JSON content, or (ii) a
            # JSON-serializable `DataItem` object.
            pass
        else:
            raise ValueError("invalid data set items")
        # create / update dataset
        if environ.DATAGATOR_API_VERSION == "v1":
            with validated(Entity.__service__.put(self.uri, ref.ref), (202, )):
                # TODO watch task for completion
                pass
        else:
            with validated(
                    Entity.__service__.put(ref.uri, ref.ref), (200, 201)):
                # since v2, data set creation / update is a synchronized
                # operation, no task will be created whatsoever
                pass
        # invalidate local cache
        ref.cache = None
        self.cache = None
        ref.update(items)
        pass

    def __delitem__(self, dsname):
        raise NotImplementedError()

    def __iter__(self):
        for ref in self.cache.get("items", []):
            yield ref.get("name")
        pass

    def __len__(self):
        return self.cache.get("itemsCount", 0)

    pass
