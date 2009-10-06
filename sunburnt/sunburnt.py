from __future__ import absolute_import

import cgi
from itertools import islice
import urllib

import httplib2

from .schema import SolrSchema, SolrError
from .search import SolrSearch

h = httplib2.Http(".cache")


class SolrConnection(object):
    def __init__(self, url, h=h):
        self.url = url.rstrip("/") + "/"
        self.update_url = self.url + "update/"
        self.select_url = self.url + "select/"
        self.request = h.request

    def commit(self, wait_flush=True, wait_searcher=True):
        response = self.commit_or_optimize("commit",
                                           wait_flush, wait_searcher)

    def optimize(self, wait_flush=True, wait_searcher=True):
        response = self.commit_or_optimize("optimize",
                                           wait_flush, wait_searcher)

    def commit_or_optimize(self, verb, wait_flush, wait_searcher):
        wait_flush = "true" if wait_flush else "false"
        wait_searcher = "true" if wait_searcher else "false"
        response = self.update('<%s waitFlush="%s" waitSearcher="%s"/>' %
                               (verb, wait_flush, wait_searcher))

    def rollback(self):
        response = self.update("<rollback/>")

    def update(self, update_doc):
        body = update_doc
        headers = {"Content-Type":"text/xml; charset=utf-8"}
        r, c = self.request(self.update_url, method="POST", body=body,
                            headers=headers)
        if r.status != 200:
            raise SolrError(r, c)

    def select(self, params):
        qs = utf8_urlencode(params)
        url = "%s?%s" % (self.select_url, qs)
        r, c = self.request(url)
        if r.status != 200:
            raise SolrError(r, c)
        return c


class SolrInterface(object):
    def __init__(self, url, schemadoc):
        self.conn = SolrConnection(url)
        self.schema = SolrSchema(schemadoc)

    def add(self, docs, chunk=100):
        # to avoid making messages too large, we break the message every
        # chunk docs.
        for doc_chunk in grouper(docs, chunk):
            update_message = self.schema.make_update(doc_chunk)
            self.conn.update(str(update_message))

    def delete(self, docs=None, queries=None):
        if not docs and not queries:
            raise SolrError("No docs or query specified for deletion")
        delete_message = self.schema.make_delete(docs, queries)
        self.conn.update(str(delete_message))

    def commit(self, *args, **kwargs):
        self.conn.commit(*args, **kwargs)

    def optimize(self, *args, **kwargs):
        self.conn.optimize(*args, **kwargs)

    def rollback(self):
        self.conn.rollback()

    def search(self, **kwargs):
        params = kwargs.copy()
        for k, v in kwargs.items():
            if hasattr(v, "items"):
                del params[k]
                params.update(v)
        return self.schema.parse_results(self.conn.select(params))

    def query(self, *args, **kwargs):
        q = SolrSearch(self)
        if len(args) + len(kwargs) > 0:
            return q.query(*args, **kwargs)
        else:
            return q


def utf8_urlencode(params):
    utf8_params = []
    for k, vs in params.items():
        if isinstance(k, unicode):
            k = k.encode('utf-8')
        # We allow for multivalued options with lists.
        if not hasattr(v, "__iter__"):
            vs = [vs]
        for v in vs:
            if isinstance(v, unicode):
                v = v.encode('utf-8')
            elif isinstance(v, bool):
                v = "true" if v else "false"
            utf8_params.append((k, v))
    return urllib.urlencode(utf8_params)

def grouper(iterable, n):
    "grouper('ABCDEFG', 3) --> [['ABC'], ['DEF'], ['G']]"
    i = iter(iterable)
    g = list(islice(i, 0, n))
    while g:
        yield g
        g = list(islice(i, 0, n))
