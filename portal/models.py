import subprocess

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.template.loader import render_to_string
from django.urls import reverse

from config.settings import DATABASES, ROOT_DOMAIN
from dns.models import Record, Domain

from .fields import MACAddressField
from .network import IPAddressField, IPNetworkField, IPNetworkQuerySet
from .network import reverse as IPreverse
from ipaddress import ip_address, ip_network


domain_validator = RegexValidator(
    regex=r'^(?=^.{1,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)*[a-zA-Z0-9-]{1,63}$)$',
    message="Enter a valid hostname."
)

hostname_validator = RegexValidator(
    regex=r'^(?![0-9]+$)(?!-)[a-zA-Z0-9-]{,63}(?<!-)$',
    message="Only lowercase letters and numbers are allowed.",
)

User = get_user_model()

HOST_TYPES = (
    ('sector', 'Sector'),
    ('ptp', 'PtP'),
    ('edgerouter', 'Edge Router'),
    ('cellrouter', 'Cell Router'),
    ('client', 'Client'),
    ('server', 'Server'),
    ('vm', 'Virtual Machine'),
    ('container', 'Container'),
    ('anycast', 'Anycast service'),
    ('pdu', 'PDU'),
    ('kvm', 'KVM/iLO/DRAC'),
    ('other', 'Other'),
)

OS_TYPES = (
    ('routeros', 'RouterOS'),
    ('airos', 'AirOS'),
    ('linux', 'Linux'),
    ('esxi', 'ESXi'),
    ('windows', 'Windows'),
    ('ilo', 'iLO'),
    ('other', 'Other'),
    (None, 'None'),
)

class DomainSortManager(models.Manager):
    def get_queryset(self):
        if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql_psycopg2':
            return super(DomainSortManager, self).get_queryset().extra(
                select={'domain_order':
                    "array_reverse(regexp_split_to_array(name, '\.'))"},
                order_by=['owner__username', 'domain_order'])
        else:
            return super(DomainSortManager, self).get_queryset()


class Site(models.Model):
    name = models.CharField(max_length=250, blank=True)
    latitude = models.FloatField(null=True, blank=True,
        help_text="Decimal (e.g., 00.0000)")
    longitude = models.FloatField(null=True, blank=True,
        help_text="Decimal (e.g., 000.0000)")
    status = models.CharField(max_length=30, blank=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'portal'
        ordering = ['name']


class Host(models.Model):
    """Tracks any asset on the network."""
    objects = DomainSortManager()

    name = models.CharField(max_length=242, unique=True,
        validators=[domain_validator])
    type = models.CharField(max_length=24, choices=HOST_TYPES)
    os = models.CharField(max_length=32, null=True, choices=OS_TYPES)
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True)

    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hosts_owned", help_text="Warning: changing this field "
        "could affect your ability to administer this host record.")
    admins = models.ManyToManyField(User, blank=True,
        related_name="authorized_hosts",
        help_text="Selected admins will be allowed to edit this host record.")

    eth_mac = MACAddressField(null=True, blank=True,
        verbose_name="Ethernet MAC")
    wlan_mac = MACAddressField(null=True, blank=True,
        verbose_name="Wireless MAC")

    latitude = models.FloatField(null=True, blank=True,
        help_text="Decimal (e.g., 00.0000)")
    longitude = models.FloatField(null=True, blank=True,
        help_text="Decimal (e.g., 000.0000)")

    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name

    def fqdn(self):
        return f'{self.name}.{ROOT_DOMAIN}'

    def get_absolute_url(self):
        return reverse('host_detail', args=[self.name,])

    def save(self, *args, **kwargs):
        if self.pk is not None:
            orig_name = Host.objects.get(pk=self.pk).name
            if orig_name and orig_name != self.name:
                for ipaddress in self.ipaddresses.all():
                    if ipaddress.auto_dns:
                        ipaddress._remove_dns()
        else:
            orig_name = None

        super(Host, self).save(*args, **kwargs)

        if orig_name and orig_name != self.name:
            for ipaddress in self.ipaddresses.all():
                ipaddress.save()


class IPAddress(models.Model):
    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='ipaddresses')
    interface = models.CharField(max_length=242, null=True, blank=True,
        validators=[domain_validator],
        help_text="Leave blank for no interface subdomain.")
    ip = IPAddressField(unique=True, verbose_name="IP Address")
    auto_dns = models.BooleanField(null=True, blank=True, default=True,
        verbose_name="Auto manage DNS", help_text="Upon saving, automatically "
        "create an A record and a PTR record for this address.")
    primary = models.BooleanField(blank=True, default=False,
        help_text="Create a CNAME from the host to this interface.")

    def __str__(self):
        return "%s (%s)" % (self.fqdn(), self.ip)

    def fqdn(self):
        if self.interface:
            return f'{self.interface}.{self.host.name}.{ROOT_DOMAIN}'
        else:
            return f'{self.host.name}.{ROOT_DOMAIN}'

    def _generate_ptr(self, domain=False):
        # If domain=True, return a PTR for the /48 or /24
        ip_obj = ip_address(self.ip)
        if ip_obj.version == 6:
            rev = self.ip.exploded.replace(':', '')[::-1]
            return "%s.ip6.arpa" % '.'.join(rev[20:] if domain else rev)
        else:
            rev = str(self.ip).split('.')[::-1]
            return "%s.in-addr.arpa" % '.'.join(rev[1:] if domain else rev)

    def _add_dns(self):
        """adds or updates A and PTR records"""
        if self.pk:
            old_name = IPAddress.objects.get(pk=self.pk).fqdn().lower()
            if old_name != self.fqdn().lower():
                self._remove_dns()

        ip_obj = ip_address(self.ip)

        new_a, created = Record.objects.get_or_create(
            domain=Domain.objects.get(name=ROOT_DOMAIN),
            name=self.fqdn().lower(),
            type='AAAA' if ip_obj.version == 6 else 'A',
            content=self.ip,
            defaults={'auth': True},
        )
        new_a.save()

        try:
            zone = self._generate_ptr(domain=True)
            domain = Domain.objects.get(name=zone)
        except Domain.DoesNotExist:
            # Support PTRs in /16 allocations because
            # _generate_ptr(domain=True) only works on /24 PTRs.
            zone = zone.split('.', 1)[1]
            try:
                domain = Domain.objects.get(name=zone)
            except Domain.DoesNotExist:
                domain = None
        if domain is not None:
            new_ptr, created = Record.objects.get_or_create(
                domain=domain,
                name=self._generate_ptr(),
                type='PTR',
                defaults={'content': self.fqdn().lower(), 'auth': True},
            )
            if not created:
                new_ptr.content = self.fqdn().lower()
            new_ptr.save()

        if self.primary and self.interface:
            new_cname, created = Record.objects.get_or_create(
                domain=Domain.objects.get(name=ROOT_DOMAIN),
                name=self.host.fqdn().lower(),
                type='CNAME',
                defaults={'content': self.fqdn().lower(), 'auth': True},
            )
            if not created:
                new_cname.content = self.fqdn().lower()
            new_cname.save()

    def _remove_dns(self):
        """removes old A and CNAME records"""
        if self.pk is not None:
            orig = IPAddress.objects.get(pk=self.pk)
            Record.objects.filter(
                name__iexact=orig.fqdn(),
                type__in=['A', 'AAAA'],
                content=orig.ip,
            ).delete()
            if orig.primary:
                Record.objects.filter(
                    name__iexact=orig.host.fqdn(),
                    type='CNAME',
                    content__iexact=orig.fqdn(),
                ).delete()
            Record.objects.filter(
                name=orig._generate_ptr(),
                type='PTR',
                content__iexact=orig.fqdn(),
            ).delete()

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.pk:
            # consider IPAddress immutable
            self.delete()
            self.pk = None

        if self.auto_dns:
            # update DNS records
            self._add_dns()

        super(IPAddress, self).save(*args, **kwargs)

    def ping(self):
        """ICMP ping the host"""
        return 0 == subprocess.call(
            "ping -c 1 %s" % (self.ip),
            shell=True,
            stdout=open('/dev/null', 'w'),
            stderr=subprocess.STDOUT)

    class Meta:
        ordering = ['ip']
        verbose_name = "IP Address"
        verbose_name_plural = "IP Addresses"


@receiver(models.signals.pre_delete, sender=IPAddress)
def remote_dns_hook(sender, instance, using, **kwargs):
    if instance.auto_dns:
        instance._remove_dns()


class Subnet(models.Model):
    """IP address subnet allocations"""
    # override default query manager so we can query for address in subnet
    objects = models.Manager()

    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="subnets_owned", help_text="Warning: changing this field "
        "could affect your ability to administer this subnet record.")
    network = IPNetworkField(unique=True)
    notes = models.TextField(blank=True)


    def __str__(self):
        return str(self.network)

    def clean(self):
        # convert slop like 10.0.1.0/22 to 10.0.0.0/22

        try:
            network_obj = ip_network(str(self.network), strict=False)  # Convert to `ip_network`
            self.network = str(network_obj)  # Store it back as a string
        except ValueError as e:
            raise ValidationError(f'Invalid network format. ({e})')

    def get_all_reverse(self):
        ret = []
        if self.network.version == 4:
            for ip in self.network.iterhosts():
                ret.append(IPreverse(ip))
        return ret

    def _hosts_in_use(self):
        return IPAddress.objects.raw('SELECT "portal_ipaddress"."id", "portal_ipaddress"."host_id", "portal_ipaddress"."interface", "portal_ipaddress"."ip", "portal_ipaddress"."auto_dns", "portal_ipaddress"."primary" FROM "portal_ipaddress" WHERE "portal_ipaddress"."ip" BETWEEN %s and %s ORDER BY "portal_ipaddress"."ip" ASC;',
                                     [str(self.min()), str(self.max())])

    def _hosts_html(self):
        if self.network.version == 4:
            addresses = [a for a in self.network.iterhosts()]
            in_use = [None] * len(addresses)
            for host in self._hosts_in_use():
                try:
                    in_use[addresses.index(host.ip)] = host
                except ValueError:
                    pass
            return render_to_string('portal/addresslist.html', {
                'addresses': zip(addresses, in_use)})
    hosts = property(_hosts_html)

    def max(self):
        if self.network.version == 4:
            return max(self.network)

    def min(self):
        if self.network.version == 4:
            return min(self.network)

    def notes_short(self):
        return self.notes and self.notes.split()[0]

    def numhosts(self):
        if self.network.version == 4:
            return self.network.numhosts
        elif self.network.version == 6:
            if self.network.prefixlen < 64:
                return "%d networks" % 2**(64 - self.network.prefixlen)
            return "2<sup>%d</sup>" % (128 - self.network.prefixlen)
    numhosts.allow_tags = True
    numhosts.short_description = "Num Hosts"

    def get_absolute_url(self):
        return reverse('portal.views.subnet_detail', args=[self.network,])

    class Meta:
        ordering = ['network']
