from __future__ import absolute_import

import cgi
import re
import urllib

import httplib2

from .schema import SolrSchema, SolrError

h = httplib2.Http(".cache")


class SolrConnection(object):
    def __init__(self, url, h=h):
        self.url = url.rstrip("/") + "/"
        self.update_url = self.url + "update/"
        self.select_url = self.url + "select/"
        self.request = h.request

    def commit(self):
        response = self.update("<commit/>")

    def optimize(self):
        response = self.update("<optimize/>")

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

    def add(self, docs):
        update_message = self.schema.make_update(docs)
        self.conn.update(str(update_message))

    def commit(self):
        self.conn.commit()

    def search(self, **kwargs):
        params = kwargs.copy()
        for k, v in kwargs.items():
            if hasattr(v, "items"):
                del params[k]
                params.update(v)
        return self.schema.parse_results(self.conn.select(params))

    def query(self, phrase=None):
        return SolrQuery(self, phrase)


class SolrQuery(object):
    def __init__(self, interface, phrase):
        self.interface = interface
        self.schema = interface.schema
        self.phrase = phrase
        self.filters = []
        self.options = {}

    def filter(self, **kwargs):
        for k, v in kwargs.items():
            try:
                name, rel = k.split("__")
            except ValueError:
                name, rel = k, 'eq'
            if name not in self.schema.fields:
                raise ValueError("%s is not a valid field name" % name)
            self.filters.append((name, rel, v))
            return self

    def facet_by(self, field, limit=None, mincount=None):
        if field not in self.schema.fields:
            raise ValueError("%s is not a valid field name" % field)
        self.options.update({"facet":"true",
                             "facet.field":field})
        if limit:
            self.options["f.%s.facet.limit" % field] = limit
        if mincount:
            self.options["f.%s.facet.mincount" % field] = mincount
        return self

    def execute(self):
        self.options["q"] = lucenequerysyntax_escape(str(self))
        return self.interface.search(**self.options)

    def __str__(self):
        s = [self.phrase] if self.phrase else []
        for name, rel, value in self.filters:
            s.append(" %s:%s" % (name, value))
        return ''.join(s)


def utf8_urlencode(params):
    utf8_params = {}
    for k, v in params.items():
        if isinstance(k, unicode):
            k = k.encode('utf-8')
        if isinstance(v, unicode):
            v = v.encode('utf-8')
        utf8_params[k] = v
    return urllib.urlencode(utf8_params)

lucene_special_chars = re.compile(r'([+\-&|!\(\){}\[\]\^\"~\*\?:\\])')
def lucenequerysyntax_escape(s):
    return lucene_special_chars.sub(r'\\\1', s)
