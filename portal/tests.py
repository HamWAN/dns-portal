import unittest
import json

from django.urls import reverse
from django.test import TestCase

from dns.models import Record
from portal.models import Host, IPAddress
from portal import views


class AnsibleHostsTest(TestCase):
    fixtures = ['domains.json', 'example_host.json']

    def test_ansible_hosts_view(self):
        response = self.client.get(reverse(views.ansible_hosts))
        self.assertEqual(response.status_code, 200)
        expected = json.loads('''{
                                   "_meta": {"hostvars": {}},
                                   "name_s1.seattle": { "hosts": ["s1.seattle.hamwan.net"] },
                                   "os_": { "hosts": ["s1.seattle.hamwan.net"] },
                                   "type_sector": { "hosts": ["s1.seattle.hamwan.net"] },
                                   "owner_": { "hosts": ["s1.seattle.hamwan.net"] }
                                 }'''
                             )
        actual = json.loads(response.content)
        self.assertEqual(expected, actual)


class IPAddressTest(TestCase):
    databases = '__all__'
    fixtures = ['domains.json', 'example_host.json']

    def _assert_address_records(self, address, want=1):
        a_records = Record.objects.filter(type="A", content=str(address.ip))
        self.assertEqual(want, a_records.count())
        if want:
            self.assertEqual(address.fqdn(), a_records[0].name)
        ptr_record = Record.objects.filter(
            type="PTR", name=address._generate_ptr())
        self.assertEqual(want, ptr_record.count())

    def test_create_address(self):
        host = Host.objects.get(name="s1.seattle")
        ip = IPAddress(host=host, interface="wlan2", ip="44.25.2.2")
        ip.save()
        self._assert_address_records(ip)

    def test_update_address(self):
        old_addr = "44.25.0.1"
        new_addr = "44.25.0.2"
        address = IPAddress.objects.get(ip=old_addr)
        self.assertEqual(1, IPAddress.objects.filter(ip=old_addr).count())
        self.assertEqual(0, IPAddress.objects.filter(ip=new_addr).count())
        address.ip = new_addr
        address.save()
        self.assertEqual(0, IPAddress.objects.filter(ip=old_addr).count())
        self.assertEqual(1, IPAddress.objects.filter(ip=new_addr).count())

    def test_delete_address(self):
        old_addr = "44.25.0.1"
        address = IPAddress.objects.get(ip=old_addr)
        self.assertEqual(1, IPAddress.objects.filter(ip=old_addr).count())
        address.delete()
        self.assertEqual(0, IPAddress.objects.filter(ip=old_addr).count())

    def test_rename_host(self):
        host = Host.objects.get(name="s1.seattle")
        host.name = "s2.seattle"
        host.save()

        cname_records = Record.objects.filter(type="CNAME")
        self.assertEqual(1, cname_records.count())
        self.assertEqual(host.fqdn(), cname_records[0].name)
        self.assertEqual("loopback.s2.seattle.hamwan.net",
                         cname_records[0].content)

        addresses = IPAddress.objects.filter(host=host)
        self.assertEqual(3, addresses.count())
        for addr in addresses:
            self._assert_address_records(addr)

    def test_delete_host(self):
        host = Host.objects.get(name="s1.seattle")
        host.delete()
        for model in Host, IPAddress, Record:
            self.assertFalse(model.objects.count(),
                             msg="orphaned objects: {}".format(model.objects.all()))


#TODO: host test case if we delete their site, owner (set null)
#TODO: subnet test case if we delete their owner (set null)
