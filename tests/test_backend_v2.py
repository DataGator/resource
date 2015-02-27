#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    tests.test_backend_v2
    ~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2015 by `University of Denver <http://pardee.du.edu/>`_
    :license: Apache 2.0, see LICENSE for more details.

    :author: `LIU Yu <liuyu@opencps.net>`_
    :date: 2015/02/26
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


def monitor_task(service, url, retry=180):
    task = None
    while retry > 0:
        task = service.http.get(url).json()
        assert(task.get("kind") == "datagator#Task")
        if task.get("status") in ("SUC", "ERR"):
            break
        time.sleep(1.0)
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
        environ.DATAGATOR_API_VERSION = "v2"
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
        environ.DATAGATOR_API_VERSION = "v2"
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

    def test_Repo_POST(self):
        response = self.service.post(self.repo, "")
        msg = response.json()
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 501)

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
        environ.DATAGATOR_API_VERSION = "v2"
        cls.repo, cls.secret = get_credentials()
        cls.service = DataGatorService(auth=(cls.repo, cls.secret))
        cls.validator = jsonschema.Draft4Validator(cls.service.schema)
        pass  # void return

    @classmethod
    def tearDownClass(cls):
        del cls.service
        pass  # void return

    def test_DataSet_00_PUT(self):

        ID = "{0}/{1}".format(self.repo, "IGO_Members")
        IGO_Members = {
            "kind": "datagator#DataSet",
            "name": "IGO_Members",
            "repo": {
                "kind": "datagator#Repo",
                "name": self.repo
            }
        }

        response = self.service.put(ID, IGO_Members)
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

        pass  # void return

    def test_DataSet_00_PUT_InvalidName(self):
        # triggers SchemaValidationError within backend service
        ID = "{0}/{1}".format(self.repo, "IGO_Members")
        InvalidName = {
            "kind": "datagator#DataSet",
            "name": "IGO Members",
            "repo": {
                "kind": "datagator#Repo",
                "name": self.repo
            }
        }
        response = self.service.put(ID, InvalidName)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_DataSet_00_PUT_MissingKind(self):
        # triggers SchemaValidationError within backend service
        ID = "{0}/{1}".format(self.repo, "IGO_Members")
        MissingKind = {
            "name": "IGO_Members",
            "repo": {
                "kind": "datagator#Repo",
                "name": self.repo
            }
        }
        response = self.service.put(ID, MissingKind)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_DataSet_00_PUT_InvalidKind(self):
        # triggers AssertionError within backend service
        ID = "{0}/{1}".format(self.repo, "Whatever")
        InvalidKind = {
            "kind": "datagator#Repo",
            "name": "Whatever"
        }
        response = self.service.put(ID, InvalidKind)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_DataSet_00_PUT_InconsistentRepo(self):
        # triggers AssertionError within backend service
        ID = "{0}/{1}".format(self.repo, "Whatever")
        InconsistentRepo = {
            "kind": "datagator#DataSet",
            "name": "Whatever",
            "repo": {
                "kind": "datagator#Repo",
                "name": "NonExistentRepo"
            }
        }
        response = self.service.put(ID, InconsistentRepo)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_DataSet_01_PATCH(self):

        ID = "{0}/{1}".format(self.repo, "IGO_Members")
        revision = {
            "UN": json.loads(to_unicode(
                load_data(os.path.join("json", "IGO_Members", "UN.json")))),
            "WTO": json.loads(to_unicode(
                load_data(os.path.join("json", "IGO_Members", "WTO.json")))),
            "IMF": json.loads(to_unicode(
                load_data(os.path.join("json", "IGO_Members", "IMF.json")))),
            "OPEC": json.loads(to_unicode(
                load_data(os.path.join("json", "IGO_Members", "OPEC.json")))),
        }

        response = self.service.patch(ID, revision)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Status")
        self.assertEqual(msg.get("code"), 202)

        # monitor the task until the revision is committed or an error occurs
        self.assertTrue("Location" in response.headers)
        url = response.headers['Location']
        task = monitor_task(self.service, url)
        self.assertEqual(self.validator.validate(task), None)
        self.assertEqual(task.get("kind"), "datagator#Task")
        self.assertEqual(task.get("status"), "SUC")

        pass  # void return

    def test_DataSet_01_PATCH_InvalidPayload(self):
        # triggers AssertionError within backend service
        ID = "{0}/{1}".format(self.repo, "IGO_Members")
        InvalidPayload = ["array", "as", "payload"]
        response = self.service.patch(ID, InvalidPayload)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_DataSet_01_PATCH_MissingKind(self):
        # triggers SchemaValidationError within backend service
        ID = "{0}/{1}".format(self.repo, "IGO_Members")
        MissingKind = {
            "UN": {
                "name": "IGO_Members",
                "repo": {
                    "kind": "datagator#Repo",
                    "name": self.repo
                }
            }
        }
        response = self.service.patch(ID, MissingKind)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_DataSet_01_PATCH_InvalidKey(self):
        # triggers AssertionError within backend service
        ID = "{0}/{1}".format(self.repo, "IGO_Members")
        InvalidKey = {
            "U#N": json.loads(to_unicode(
                load_data(os.path.join("json", "IGO_Members", "WTO.json"))))
        }
        response = self.service.patch(ID, InvalidKey)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_DataSet_01_PATCH_InvalidKind(self):
        # triggers AssertionError within backend service
        ID = "{0}/{1}".format(self.repo, "IGO_Members")
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
        response = self.service.patch(ID, InvalidKind)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 400)
        pass  # void return

    def test_DataSet_01_PATCH_RemoveNonExistent(self):
        # NOTE: this does NOT trigger an error on the backend service

        ID = "{0}/{1}".format(self.repo, "IGO_Members")
        RemoveNonExistent = {
            "NonExistent": None
        }

        response = self.service.patch(ID, RemoveNonExistent)
        msg = response.json()
        self.assertEqual(self.validator.validate(msg), None)
        _log.debug(msg.get("message"))
        self.assertEqual(msg.get("kind"), "datagator#Status")
        self.assertEqual(msg.get("code"), 202)

        # monitor the task until the revision is committed or an error occurs
        self.assertTrue("Location" in response.headers)
        url = response.headers['Location']
        task = monitor_task(self.service, url)
        self.assertEqual(self.validator.validate(task), None)
        self.assertEqual(task.get("kind"), "datagator#Task")
        self.assertEqual(task.get("status"), "SUC")
        pass  # void return

    def test_DataSet_02_GET(self):
        ID = "{0}/{1}".format(self.repo, "IGO_Members")
        response = self.service.get(ID)
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

    def test_DataSet_02_GET_NonExistence(self):
        msg = self.service.get("Pardee/NonExistence").json()
        self.assertEqual(self.validator.validate(msg), None)
        self.assertEqual(msg.get("kind"), "datagator#Error")
        self.assertEqual(msg.get("code"), 404)
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
        environ.DATAGATOR_API_VERSION = "v2"
        cls.repo, cls.secret = get_credentials()
        cls.service = DataGatorService(auth=(cls.repo, cls.secret))
        cls.validator = jsonschema.Draft4Validator(cls.service.schema)
        pass  # void return

    @classmethod
    def tearDownClass(cls):
        del cls.service
        pass  # void return

    def test_DataItem_GET(self):
        ID = "{0}/{1}/{2}".format(self.repo, "IGO_Members", "UN")
        UN = json.loads(to_unicode(
            load_data(os.path.join("json", "IGO_Members", "UN.json"))))
        # full GET
        response = self.service.get(ID)
        self.assertEqual(response.status_code, 200)
        item = response.json()
        self.assertEqual(self.validator.validate(item), None)
        self.assertEqual(item.get("kind"), "datagator#Matrix")
        for k in ["rowsCount", "columnsCount", "rowHeaders", "columnHeaders"]:
            self.assertEqual(item.get(k), UN.get(k))
        # conditional GET
        etag = response.headers.get("ETag")
        response = self.service.get(ID, {"If-None-Match": etag})
        self.assertEqual(response.status_code, 304)
        self.assertTrue("ETag" in response.headers)
        self.assertEqual(response.headers['ETag'], etag)
        pass  # void return

    def test_DataItem_POST_MatrixToXlsx(self):
        ID = "{0}/{1}/{2}".format(self.repo, "IGO_Members", "UN")
        data = {"fmt": "xlsx"}
        # submit conversion request
        response = self.service.post(ID, data=data)
        _log.debug(response.text)
        self.assertTrue(response.status_code in [201, 202])
        self.assertTrue("Location" in response.headers)
        url = response.headers['Location']
        # ready for download
        if response.status_code == 201:
            download = self.service.get(url)
            self.assertEqual(download.status_code, 200)
            self.assertTrue("Content-Type" in download.headers)
            self.assertEqual(
                download.headers['Content-Type'], "application/octet-stream")
            self.assertTrue("Content-Disposition" in download.headers)
            pass

        # pending conversion
        if response.status_code == 202:
            task = monitor_task(self.service, url)
            self.assertEqual(self.validator.validate(task), None)
            self.assertEqual(task.get("kind"), "datagator#Task")
            self.assertEqual(task.get("status"), "SUC")
            pass

        pass  # void return

    pass


class TestSearchOperations(unittest.TestCase):
    """
    Endpoint:
        ``^/search``
    """

    @classmethod
    def setUpClass(cls):
        environ.DATAGATOR_API_VERSION = "v2"
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
