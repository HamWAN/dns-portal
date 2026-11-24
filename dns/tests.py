"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import SimpleTestCase, TestCase

from dns.models import Record


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)


class RecordCleanTest(SimpleTestCase):
    def clean(self, type, content, name='HamWAN.org'):
        record = Record(name=name, type=type, content=content)
        record.clean()
        return record

    def test_name_is_lowercased(self):
        for type in ('A', 'CNAME', 'TXT'):
            self.assertEqual(self.clean(type, 'x').name, 'hamwan.org')

    def test_hostname_content_is_lowercased(self):
        for type in ('CNAME', 'NS', 'PTR', 'MX', 'SRV'):
            self.assertEqual(self.clean(type, 'Foo.HamWAN.net').content,
                             'foo.hamwan.net')

    def test_txt_content_preserves_case(self):
        value = 'example-domain-verification=AbC123xYz'
        self.assertEqual(self.clean('TXT', value).content, value)
