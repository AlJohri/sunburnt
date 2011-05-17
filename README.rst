Sunburnt
========

Sunburnt is a Python-based interface for working with the Solr
(http://lucene.apache.org/solr/) search engine.

It was written by Toby White <toby@timetric.com> for use in the Timetric
(http://timetric.com) platform.

Please send queries/comments/suggestions to:
http://groups.google.com/group/python-sunburnt

It's tested with Solr 1.4.1 and 3.1; previous versions were known to work
with 1.3 and 1.4 as well.

Dependencies
============

- Requirements:

  * `httplib2 <http://code.google.com/p/httplib2/>`_
  * `lxml <http://lxml.de>`_

- Strongly recommended:

  * `mx.DateTime <http://www.egenix.com/products/python/mxBase/mxDateTime/>`_

    Sunburnt will happily deal with dates stored either as Python datetime
    objects, or as mx.DateTime objects. The latter are preferable,
    having better semantics and a wider representation range. They will
    be used if present, otherwise sunburnt will fall back to Python
    datetime objects.

  * `pytz <http://pytz.sourceforge.net>`_

    If you're using native Python datetime objects with Solr (rather than
    mx.DateTime objects) you should also have pytz installed to guarantee
    correct timezone handling.

- Optional (only to run the tests)

  * `nose <http://somethingaboutorange.com/mrl/projects/nose/>`_
