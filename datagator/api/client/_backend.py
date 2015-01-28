# -*- coding: utf-8 -*-
"""
    datagator.api.client._backend
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2015 by `University of Denver <http://pardee.du.edu/>`_
    :license: Apache 2.0, see LICENSE for more details.

    :author: `LIU Yu <liuyu@opencps.net>`_
    :date: 2015/01/28
"""

from __future__ import unicode_literals, with_statement

__all__ = [b'DATAGATOR_API_USER_AGENT',
           b'DATAGATOR_API_URL',
           b'DATAGATOR_API_FOLLOW_REDIRECT',
           b'DATAGATOR_API_TIMEOUT',
           b'DATAGATOR_API_ACCEPT_ENCODING', ]


import json
import jsonschema
import requests

from requests.auth import HTTPBasicAuth
from ._compat import to_bytes


DATAGATOR_API_USER_AGENT = "datagator-client " \
                           "(python/{0}.{1}.{2})".format(*__version__)

DATAGATOR_API_URL = "https://www.data-gator.com/api/v1"
DATAGATOR_API_FOLLOW_REDIRECT = False
DATAGATOR_API_TIMEOUT = 180

DATAGATOR_API_ACCEPT_ENCODING = "gzip, deflate, identity"


def _build_message(content):
    payload = to_bytes(content)
    headers = {
        "User-Agent": DATAGATOR_API_USER_AGENT,
        "Accept-Encoding": DATAGATOR_API_ACCEPT_ENCODING,
        "Content-Type": "application/json",
        "Content-Length": len(payload)}
    return headers, payload


def commit(dataset, items, **kwargs):

    # HTTP(S) connection
    s = requests.Session()
    s.auth = HTTPBasicAuth(kwargs['user'], kwargs['password'])

    # HTTP(S) POST request
    headers, payload = _build_message(json.dumps(items))

    r = None
    try:
        r = s.request(
            method="PUT",
            url="/".join([DATAGATOR_API_URL, dataset]),
            verify=True,
            data=payload,
            headers=headers,
            allow_redirects=DATAGATOR_API_FOLLOW_REDIRECT,
            timeout=DATAGATOR_API_TIMEOUT)
    except:
        raise
    else:
        return r
    finally:
        s.close()

    pass  # void return
