from __future__ import absolute_import

import cStringIO as StringIO
import datetime

import mx.DateTime
import pytz

from .schema import solr_date, SolrSchema, SolrError, SolrUpdate

not_utc = pytz.timezone('Etc/GMT-3')

samples_from_pydatetimes = {
    "2009-07-23T03:24:34.000376Z":
        [datetime.datetime(2009, 07, 23, 3, 24, 34, 376),
         datetime.datetime(2009, 07, 23, 3, 24, 34, 376, pytz.utc)],
    "2009-07-23T00:24:34.000376Z":
        [not_utc.localize(datetime.datetime(2009, 07, 23, 3, 24, 34, 376)),
         datetime.datetime(2009, 07, 23, 0, 24, 34, 376, pytz.utc)],
    "2009-07-23T03:24:34.000000Z":
        [datetime.datetime(2009, 07, 23, 3, 24, 34),
         datetime.datetime(2009, 07, 23, 3, 24, 34, tzinfo=pytz.utc)],
    "2009-07-23T00:24:34.000000Z":
        [not_utc.localize(datetime.datetime(2009, 07, 23, 3, 24, 34)),
         datetime.datetime(2009, 07, 23, 0, 24, 34, tzinfo=pytz.utc)]
    }

samples_from_mxdatetimes = {
    "2009-07-23T03:24:34.000376Z":
        [mx.DateTime.DateTime(2009, 07, 23, 3, 24, 34.000376),
         datetime.datetime(2009, 07, 23, 3, 24, 34, 376, pytz.utc)],
    "2009-07-23T03:24:34.000000Z":
        [mx.DateTime.DateTime(2009, 07, 23, 3, 24, 34),
         datetime.datetime(2009, 07, 23, 3, 24, 34, tzinfo=pytz.utc)],
    }


samples_from_strings = {
    # These will not have been serialized by us, but we should deal with them
    "2009-07-23T03:24:34Z":
        datetime.datetime(2009, 07, 23, 3, 24, 34, tzinfo=pytz.utc),
    "2009-07-23T03:24:34.1Z":
        datetime.datetime(2009, 07, 23, 3, 24, 34, 100000, pytz.utc),
    "2009-07-23T03:24:34.123Z":
        datetime.datetime(2009, 07, 23, 3, 24, 34, 123000, pytz.utc)
    }

def check_solr_date_from_date(s, date, canonical_date):
    assert str(solr_date(date)) == s
    check_solr_date_from_string(s, canonical_date)

def check_solr_date_from_string(s, date):
    assert solr_date(s).v == date


def test_solr_date_from_pydatetimes():
    for k, v in samples_from_pydatetimes.items():
        yield check_solr_date_from_date, k, v[0], v[1]

def test_solr_date_from_mxdatetimes():
    for k, v in samples_from_mxdatetimes.items():
        yield check_solr_date_from_date, k, v[0], v[1]

def test_solr_date_from_strings():
    for k, v in samples_from_strings.items():
        yield check_solr_date_from_string, k, v


good_schema = \
"""
<schema name="timetric" version="1.1">
  <types>
    <fieldType name="sint" class="solr.SortableIntField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="string" class="solr.StrField" sortMissingLast="true" omitNorms="true"/>
    <fieldType name="boolean" class="solr.BoolField" sortMissingLast="true" omitNorms="true"/>
  </types>
  <fields>
    <field name="int_field" required="true" type="sint"/>
    <field name="text_field" required="true" type="string" multiValued="true"/>
    <field name="boolean_field" required="false" type="boolean"/>
  </fields>
  <defaultSearchField>text_field</defaultSearchField>
  <uniqueKey>int_field</uniqueKey>
 </schema>
"""

class TestReadingSchema(object):
    def setUp(self):
        self.schema = StringIO.StringIO(good_schema)
        self.s = SolrSchema(self.schema)

    def test_read_schema(self):
        """ Test that we can read in a schema correctly,
        that we get the right set of fields, the right
        default field, and the right unique key"""
        assert set(self.s.fields.keys()) \
            == set(['boolean_field', 'int_field', 'text_field'])
        assert self.s.default_field == 'text_field'
        assert self.s.unique_key == 'int_field'

    def test_serialize_dict(self):
        """ Test that each of the fields will serialize the relevant
        datatype appropriately."""
        for k, v, v2 in (('int_field', 1, u'1'),
                         ('text_field', 'text', u'text'),
                         ('text_field', u'text', u'text'),
                         ('boolean_field', True, u'true')):
                             assert self.s.serialize_value(k, v) == v2

    def test_serialize_value_fails(self):
        try:
            self.s.serialize_value('my_arse', 3)
        except SolrError:
            pass
        else:
            assert False

    def test_missing_fields(self):
        assert set(self.s.missing_fields([])) \
            == set(['int_field', 'text_field'])
        assert set(self.s.missing_fields(['boolean_field'])) \
            == set(['int_field', 'text_field'])
        assert set(self.s.missing_fields(['int_field'])) == set(['text_field'])

    def test_serialize_values(self):
        assert self.s.serialize_values('text_field', ["a", "b", "c"]) \
            == [u"a", u"b", u"c"]

    def test_serialize_values_fails_with_bad_field_name(self):
        try:
            self.s.serialize_values('text_field2', ["a", "b", "c"])
        except SolrError:
            pass
        else:
            assert False

    def test_serialize_values_fails_when_not_multivalued(self):
        try:
            self.s.serialize_values('int_field', ["a", "b", "c"])
        except SolrError:
            pass
        else:
            assert False


broken_schemata = {
"missing_name":
"""
<schema name="timetric" version="1.1">
  <types>
    <fieldType name="sint" class="solr.SortableIntField" sortMissingLast="true" omitNorms="true"/>
  </types>
  <fields>
    <field required="true" type="sint"/>
  </fields>
 </schema>
""",
"missing_type":
"""
<schema name="timetric" version="1.1">
  <types>
    <fieldType name="sint" class="solr.SortableIntField" sortMissingLast="true" omitNorms="true"/>
  </types>
  <fields>
    <field name="int_field" required="true"/>
  </fields>
 </schema>
""",
"misnamed_type":
"""
<schema name="timetric" version="1.1">
  <types>
    <fieldType name="sint" class="solr.SortableIntField" sortMissingLast="true" omitNorms="true"/>
  </types>
  <fields>
    <field name="int_field" required="true" type="sint2"/>
  </fields>
 </schema>
""",
"invalid XML":
"kjhgjhg"
}


def check_broken_schemata(n, s):
    try:
        SolrSchema(StringIO.StringIO(s))
    except SolrError:
        pass
    else:
        assert False

def test_broken_schemata():
    for k, v in broken_schemata.items():
        yield check_broken_schemata, k, v


class D(object):
    def __init__(self, int_field, text_field):
        self.int_field = int_field
        self.text_field = text_field


update_docs = [
    # One single dictionary, not making use of multivalued field
    ({"int_field":1, "text_field":"a"},
     """<add><doc><field name="int_field">1</field><field name="text_field">a</field></doc></add>"""),
    # One single dictionary, with multivalued field
    ({"int_field":1, "text_field":["a", "b"]},
     """<add><doc><field name="int_field">1</field><field name="text_field">a</field><field name="text_field">b</field></doc></add>"""),
    # List of dictionaries
    ([{"int_field":1, "text_field":"a"}, {"int_field":2, "text_field":"b"}],
     """<add><doc><field name="int_field">1</field><field name="text_field">a</field></doc><doc><field name="int_field">2</field><field name="text_field">b</field></doc></add>"""),
    # One single object, not making use of multivalued fields
    (D(1, "a"),
     """<add><doc><field name="int_field">1</field><field name="text_field">a</field></doc></add>"""),
    # One single object, with multivalued field
    (D(1, ["a", "b"]),
     """<add><doc><field name="int_field">1</field><field name="text_field">a</field><field name="text_field">b</field></doc></add>"""),
    # List of objects
    ([D(1, "a"), D(2, "b")],
     """<add><doc><field name="int_field">1</field><field name="text_field">a</field></doc><doc><field name="int_field">2</field><field name="text_field">b</field></doc></add>"""),
    # Mixed list of objects & dictionaries
    ([D(1, "a"), {"int_field":2, "text_field":"b"}],
     """<add><doc><field name="int_field">1</field><field name="text_field">a</field></doc><doc><field name="int_field">2</field><field name="text_field">b</field></doc></add>"""),
    ]

def check_update_serialization(s, obj, xml_string):
    assert str(SolrUpdate(s, obj)) == xml_string

def test_update_serialization():
    s = SolrSchema(StringIO.StringIO(good_schema))
    for obj, xml_string in update_docs:
        yield check_update_serialization, s, obj, xml_string
