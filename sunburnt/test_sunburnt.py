from __future__ import absolute_import

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import cgi, datetime, urlparse

from lxml.builder import E
from lxml.etree import tostring
import mx.DateTime

from .sunburnt import SolrInterface

debug = False

schema_string = \
"""<schema name="timetric" version="1.1">
  <types>
    <fieldType name="string" class="solr.StrField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="text" class="solr.TextField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="boolean" class="solr.BoolField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="int" class="solr.IntField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="sint" class="solr.SortableIntField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="long" class="solr.LongField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="slong" class="solr.SortableLongField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="float" class="solr.FloatField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="sfloat" class="solr.SortableFloatField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="double" class="solr.DoubleField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="sdouble" class="solr.SortableDoubleField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="date" class="solr.DateField" sortMissingLast="true" omitNorms="true"/>
  </types>
  <fields>
    <field name="string_field" required="true" type="string" multiValued="true"/>
    <field name="text_field" required="true" type="text"/>
    <field name="boolean_field" required="false" type="boolean"/>
    <field name="int_field" required="true" type="int"/>
    <field name="sint_field" type="sint"/>
    <field name="long_field" type="long"/>
    <field name="slong_field" type="slong"/>
    <field name="long_field" type="long"/>
    <field name="slong_field" type="slong"/>
    <field name="float_field" type="float"/>
    <field name="sfloat_field" type="sfloat"/>
    <field name="double_field" type="double"/>
    <field name="sdouble_field" type="sdouble"/>
    <field name="date_field" type="date"/>
  </fields>
  <defaultSearchField>text_field</defaultSearchField>
  <uniqueKey>int_field</uniqueKey>
</schema>"""


class MockResponse(object):
    mock_doc_seeds = [
        (0, 'zero'),
        (1, 'one'),
        (2, 'two'),
        (3, 'three'),
        (4, 'four'),
        (5, 'five'),
        (6, 'six'),
        (7, 'seven'),
        (8, 'eight'),
        (9, 'nine'),
    ]
    mock_docs = [
        dict(zip(("int_field", "string_field"), m)) for m in mock_doc_seeds
    ]

    def __init__(self, start, rows):
        self.start = start
        self.rows = rows

    @staticmethod
    def xmlify_doc(d):
        return E.doc(
            E.int({'name':'int_field'}, str(d['int_field'])),
            E.str({'name':'string_field'}, d['string_field'])
        )

    def xml_response(self):
        return tostring(E.response(
            E.lst({'name':'responseHeader'},
                E.int({'name':'status'}, '0'), E.int({'name':'QTime'}, '0')
            ),
            E.result({'name':'response', 'numFound':str(len(self.mock_docs)), 'start':str(self.start)},
               *[self.xmlify_doc(doc) for doc in self.mock_docs[self.start:self.start+self.rows]]
            )
        ))


class MockConnection(object):
    def request(self, uri, method='GET', body=None, headers=None):

        class MockStatus(object):
            def __init__(self, status):
                self.status = status

        u = urlparse.urlparse(uri)
        params = cgi.parse_qs(u.query)

        if method == 'GET' and u.path.endswith('/admin/file/') and params.get("file") == ["schema.xml"]:
            return MockStatus(200), schema_string

        elif method == 'GET' and u.path.endswith('/select/'):
            start = int(params.get("start", [0])[0])
            rows = int(params.get("rows", [10])[0])
            return MockStatus(200), MockResponse(start, rows).xml_response()


        else:
            raise ValueError("Can't handle this URI")


conn = SolrInterface("http://test.example.com/", http_connection=MockConnection())

pagination_tests = (
    ((None, None), slice(None, None, None), range(10)),
    ((None, None), slice(0, 10, None), range(10)),
    ((None, None), slice(0, 10, 1), range(10)),
    ((None, None), slice(0, 5, None), range(5)),
    ((None, None), slice(5, 10, None), range(5, 10)),
    ((None, None), slice(0, 5, 2), range(0, 5, 2)),
    ((None, None), slice(5, 10, 2), range(5, 10, 2)),
    ((None, None), slice(9, None, -1), range(9, -1, -1)), # f
    ((None, None), slice(None, 0, -1), range(9, 0, -1)), # f
    ((None, None), slice(7, 3, -2), range(7, 3, -2)), # f
    # out of range but ok
    ((None, None), slice(0, 12, None), range(10)),
    ((None, None), slice(-100, 12, None), range(10)),
    # out of range but empty
    ((None, None), slice(12, 20, None), []),
    ((None, None), slice(-100, -90), []),
    # negative offsets
    ((None, None), slice(0, -1, None), range(9)),
    ((None, None), slice(-5, -1, None), range(5, 9)),
    ((None, None), slice(-1, -5, -1), range(8, 4, -1)),
    # zero-range produced
    ((None, None), slice(10, 0, None), []),
    ((None, None), slice(0, 10, -1), []),
    ((None, None), slice(0, -3, -1), []),
    ((None, None), slice(-5, -9, None), []),
    ((None, None), slice(-9, -5, -1), []),
)

#pagination to paginated query

# indexing to cells

# IndexErrors as appropriate

def check_pagination(p):
    p_args, s_args, output = p
    assert [d['int_field'] for d in conn.query("*").paginate(*p_args)[s_args]] == output

def test_pagination():
    for p in pagination_tests:
        yield check_pagination, p
