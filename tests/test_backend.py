#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    tests.test_backend
    ~~~~~~~~~~~~~~~~~~

    :copyright: 2015 by `University of Denver <http://pardee.du.edu/>`_
    :license: Apache 2.0, see LICENSE for more details.

    :author: `LIU Yu <liuyu@opencps.net>`_
    :date: 2015/01/19
"""

from __future__ import unicode_literals

import json
import jsonschema
import logging
import os
import sys
import time

try:
    from . import config
    from .config import *
except (ValueError, ImportError):
    import config
    from config import *

from datagator.api.client._backend import environ, DataGatorService


__all__ = ['TestBackendStatus',
           'TestRepoOperations',
           'TestDataSetOperations',
           'TestDataItemOperations',
           'TestSearchOperations', ]
__all__ = [to_native(n) for n in __all__]


_log = logging.getLogger("datagator.{0}".format(__name__))


def monitor_task(service, url, retry=5):
    task = None
    while retry > 0:
        task = service.http.get(url).json()
        assert(task.get("kind") == "datagator#Task")
        if task.get("status") in ("SUC", "ERR"):
            break
        time.sleep(0.5)
        retry -= 1
    return task


class TestBackendStatus(unittest.TestCase):
    """
    Endpoint:
        ``^/``
        ``^/schema``
    """

    @classmethod
    def setUpClass(cls):
        cls.service = DataGatorService()
        pass  # void return

    @classmethod
    def tearDownClass(cls):
        del cls.service
        pass  # void return

    def test_backend_status(self):
        msg = self.service.status
        validator = jsonschema.Draft4Validator(self.service.schema)
        self.assertEqual(validator.validate(msg), None)
        self.assertEqual(msg.get("kind"), "datagator#Status")
        self.assertEqual(msg.get("code"), 200)
        self.assertEqual(msg.get("version"), environ.DATAGATOR_API_VERSION)
        pass  # void return

    pass


@unittest.skipIf(
    not os.environ.get('DATAGATOR_CREDENTIALS', None) and
    os.environ.get('TRAVIS', False),
    "credentials required for unsupervised testing")
class TestRepoOperations(unittest.TestCase):
    """
    Endpoint:
        ``^/<repo>``
    """

    @classmethod
    def setUpClass(cls):
        cls.repo, cls.secret = get_credentials()
        cls.service = DataGatorService(auth=(cls.repo, cls.secret))
        cls.validator = jsonschema.Draft4Validator(cls.service.schema)
        pass  # void return

    @classmethod
    def tearDownClass(cls):
        del cls.service
        pass  # void return

    def test_Repo_GET(self):
        response = self.service.get(self.repo)
        self.assertEqual(response.status_code, 200)
        repo = response.json()
        self.assertEqual(self.validator.validate(repo), None)
        self.assertEqual(repo.get("kind"), "datagator#Repo")
        self.assertEqual(repo.get("name"), self.repo)
        pass  # void return

    def test_Repo_GET_NonExistence(self):
        msg = self.service.get("NonExistence").json()
        self.assertEqual(self.validator.validate(msg), None)
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 404)
        pass  # void return

    def test_Repo_PUT(self):

        IGO_Members = {
            "kind": "datagator#DataSet",
            "name": "IGO_Members",
            "repo": {
                "kind": "datagator#Repo",
                "name": self.repo
            }
        }

        response = self.service.put(self.repo, IGO_Members)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Status")
        self.assertEqual(msg.get("code"), 202)

        # monitor the task until the data set is ready or an error occurs
        self.assertTrue("Location" in response.headers)
        url = response.headers['Location']
        task = monitor_task(self.service, url)
        self.assertEqual(self.validator.validate(task), None)
        self.assertEqual(task.get("kind"), "datagator#Task")
        self.assertEqual(task.get("status"), "SUC")

        # commit an initial revision to the created data set
        UN = json.loads(to_unicode(
            load_data(os.path.join("json", "IGO_Members", "UN.json"))))
        response = self.service.put(
            "{0}/{1}".format(self.repo, "IGO_Members"), {"UN": UN})
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Status")
        self.assertEqual(msg.get("code"), 202)

        # monitor the task until the revision is committed an error occurs
        self.assertTrue("Location" in response.headers)
        url = response.headers['Location']
        task = monitor_task(self.service, url)
        self.assertEqual(self.validator.validate(task), None)
        self.assertEqual(task.get("kind"), "datagator#Task")
        self.assertEqual(task.get("status"), "SUC")

        pass  # void return

    def test_Repo_PUT_InvalidName(self):
        # triggers SchemaValidationError within backend service
        InvalidName = {
            "kind": "datagator#DataSet",
            "name": "IGO Members",
            "repo": {
                "kind": "datagator#Repo",
                "name": self.repo
            }
        }
        response = self.service.put(self.repo, InvalidName)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_Repo_PUT_MissingKind(self):
        # triggers SchemaValidationError within backend service
        MissingKind = {
            "name": "IGO_Members",
            "repo": {
                "kind": "datagator#Repo",
                "name": self.repo
            }
        }
        response = self.service.put(self.repo, MissingKind)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_Repo_PUT_InvalidKind(self):
        # triggers AssertionError within backend service
        InvalidKind = {
            "kind": "datagator#Repo",
            "name": "Whatever"
        }
        response = self.service.put(self.repo, InvalidKind)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_Repo_PUT_InconsistentRepo(self):
        # triggers AssertionError within backend service
        InconsistentRepo = {
            "kind": "datagator#DataSet",
            "name": "Whatever",
            "repo": {
                "kind": "datagator#Repo",
                "name": "NonExistentRepo"
            }
        }
        response = self.service.put(self.repo, InconsistentRepo)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    pass


@unittest.skipIf(
    not os.environ.get('DATAGATOR_CREDENTIALS', None) and
    os.environ.get('TRAVIS', False),
    "credentials required for unsupervised testing")
class TestDataSetOperations(unittest.TestCase):
    """
    Endpoint:
        ``^/<repo>``
    """

    @classmethod
    def setUpClass(cls):
        cls.repo, cls.secret = get_credentials()
        cls.service = DataGatorService(auth=(cls.repo, cls.secret))
        cls.validator = jsonschema.Draft4Validator(cls.service.schema)
        pass  # void return

    @classmethod
    def tearDownClass(cls):
        del cls.service
        pass  # void return

    def test_DataSet_GET(self):
        id = "{0}/{1}".format(self.repo, "IGO_Members")
        response = self.service.get(id)
        self.assertEqual(response.status_code, 200)
        ds = response.json()
        self.assertEqual(self.validator.validate(ds), None)
        self.assertEqual(ds.get("kind"), "datagator#DataSet")
        self.assertEqual(ds.get("name"), "IGO_Members")

        # check if ds/repo/name matches the requested one
        repo = ds.get("repo")
        self.assertEqual(self.validator.validate(repo), None)
        self.assertEqual(repo.get("kind"), "datagator#Repo")
        self.assertEqual(repo.get("name"), self.repo)

        pass  # void return

    def test_DataSet_GET_NonExistence(self):
        msg = self.service.get("Pardee/NonExistence").json()
        self.assertEqual(self.validator.validate(msg), None)
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 404)
        pass  # void return

    def test_DataSet_PUT(self):

        id = "{0}/{1}".format(self.repo, "IGO_Members")
        revision = {
            "WTO": json.loads(to_unicode(
                load_data(os.path.join("json", "IGO_Members", "WTO.json")))),
            "IMF": json.loads(to_unicode(
                load_data(os.path.join("json", "IGO_Members", "IMF.json")))),
            "OPEC": json.loads(to_unicode(
                load_data(os.path.join("json", "IGO_Members", "OPEC.json")))),
        }

        response = self.service.put(id, revision)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Status")
        self.assertEqual(msg.get("code"), 202)

        # monitor the task until the revision is committed an error occurs
        self.assertTrue("Location" in response.headers)
        url = response.headers['Location']
        task = monitor_task(self.service, url)
        self.assertEqual(self.validator.validate(task), None)
        self.assertEqual(task.get("kind"), "datagator#Task")
        self.assertEqual(task.get("status"), "SUC")

        pass  # void return

    def test_DataSet_PUT_InvalidPayload(self):
        # triggers AssertionError within backend service
        id = "{0}/{1}".format(self.repo, "IGO_Members")
        InvalidPayload = ["array", "as", "payload"]
        response = self.service.put(id, InvalidPayload)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_DataSet_PUT_MissingKind(self):
        # triggers SchemaValidationError within backend service
        id = "{0}/{1}".format(self.repo, "IGO_Members")
        MissingKind = {
            "UN": {
                "name": "IGO_Members",
                "repo": {
                    "kind": "datagator#Repo",
                    "name": self.repo
                }
            }
        }
        response = self.service.put(id, MissingKind)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_DataSet_PUT_InvalidKey(self):
        # triggers AssertionError within backend service
        id = "{0}/{1}".format(self.repo, "IGO_Members")
        InvalidKey = {
            "U#N": json.loads(to_unicode(
                load_data(os.path.join("json", "IGO_Members", "WTO.json"))))
        }
        response = self.service.put(id, InvalidKey)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_DataSet_PUT_InvalidKind(self):
        # triggers AssertionError within backend service
        id = "{0}/{1}".format(self.repo, "IGO_Members")
        InvalidKind = {
            "UN": {
                "kind": "datagator#DataSet",
                "name": "IGO_Members",
                "repo": {
                    "kind": "datagator#Repo",
                    "name": self.repo
                }
            }
        }
        response = self.service.put(id, InvalidKind)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_DataSet_PUT_RemoveNonExistent(self):
        # triggers AssertionError within backend service
        id = "{0}/{1}".format(self.repo, "IGO_Members")
        RemoveNonExistent = {
            "NonExistent": None
        }
        response = self.service.put(id, RemoveNonExistent)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    pass


@unittest.skipIf(
    not os.environ.get('DATAGATOR_CREDENTIALS', None) and
    os.environ.get('TRAVIS', False),
    "credentials required for unsupervised testing")
class TestDataItemOperations(unittest.TestCase):
    """
    Endpoint:
        ``^/<repo>/<dataset>/<key>``
    """

    @classmethod
    def setUpClass(cls):
        cls.repo, cls.secret = get_credentials()
        cls.service = DataGatorService(auth=(cls.repo, cls.secret))
        cls.validator = jsonschema.Draft4Validator(cls.service.schema)
        pass  # void return

    @classmethod
    def tearDownClass(cls):
        del cls.service
        pass  # void return

    def test_DataItem_GET(self):
        id = "{0}/{1}/{2}".format(self.repo, "IGO_Members", "UN")
        UN = json.loads(to_unicode(
            load_data(os.path.join("json", "IGO_Members", "UN.json"))))
        # full GET
        response = self.service.get(id)
        self.assertEqual(response.status_code, 200)
        item = response.json()
        self.assertEqual(self.validator.validate(item), None)
        self.assertEqual(item.get("kind"), "datagator#Matrix")
        for k in ["rowsCount", "columnsCount", "rowHeaders", "columnHeaders"]:
            self.assertEqual(item.get(k), UN.get(k))
        # conditional GET
        etag = response.headers.get("ETag")
        response = self.service.get(id, {"If-None-Match": etag})
        self.assertEqual(response.status_code, 304)
        self.assertTrue("ETag" in response.headers)
        self.assertEqual(response.headers['ETag'], etag)
        pass  # void return

    pass


class TestSearchOperations(unittest.TestCase):
    """
    Endpoint:
        ``^/search``
    """

    @classmethod
    def setUpClass(cls):
        cls.repo, cls.secret = get_credentials()
        cls.service = DataGatorService(auth=(cls.repo, cls.secret))
        cls.validator = jsonschema.Draft4Validator(cls.service.schema)
        pass  # void return

    @classmethod
    def tearDownClass(cls):
        del cls.service
        pass  # void return

    pass


def test_suite():
    return unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(eval(c)) for c in __all__])


if __name__ == '__main__':
    unittest.main(defaultTest=to_native("test_suite"))
