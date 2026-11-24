# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#     * Rearrange models' order
#     * Make sure each model has one field with primary_key=True
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
# into your database.
from __future__ import unicode_literals
from datetime import datetime

from django.core.mail import send_mail
from django.db import models

from config.settings import ROOT_DOMAIN


RECORD_TYPES = [(a, a) for a in ('A', 'CNAME', 'NS', 'PTR', 'SOA', 'SRV')]


# class Cryptokeys(models.Model):
#     id = models.IntegerField(primary_key=True)
#     domain = models.ForeignKey('Domains', null=True, blank=True)
#     flags = models.IntegerField()
#     active = models.BooleanField(null=True, blank=True)
#     content = models.TextField(blank=True)
#     class Meta:
#         db_table = 'cryptokeys'

# class Domainmetadata(models.Model):
#     id = models.IntegerField(primary_key=True)
#     domain = models.ForeignKey('Domains', null=True, blank=True)
#     kind = models.CharField(max_length=16, blank=True)
#     content = models.TextField(blank=True)
#     class Meta:
#         db_table = 'domainmetadata'

class Domain(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    master = models.CharField(max_length=128, null=True, blank=True)
    last_check = models.IntegerField(null=True, blank=True)
    type = models.CharField(max_length=6)
    notified_serial = models.IntegerField(null=True, blank=True)
    account = models.CharField(max_length=40, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'domains'

class Record(models.Model):
    id = models.AutoField(primary_key=True)
    domain = models.ForeignKey(Domain, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=10, blank=True)
    content = models.CharField(max_length=65535, blank=True)
    ttl = models.IntegerField(null=True, blank=True, verbose_name="TTL")
    prio = models.IntegerField(null=True, blank=True)
    change_date = models.IntegerField(null=True, editable=False)
    ordername = models.CharField(max_length=255, blank=True)
    auth = models.BooleanField(null=True, blank=True, default=True,
        verbose_name="Authoritative")

    def __str__(self):
        return self.name

    def clean(self):
        self.name = self.name.lower()
        # Only hostname-valued content is case-insensitive; TXT (SPF, DKIM,
        # domain-verification tokens, etc.) must be stored verbatim.
        if self.type in ('CNAME', 'NS', 'PTR', 'MX', 'SRV'):
            self.content = self.content.lower()

    def update_change_date(self):
        generated_serial = int(datetime.today().strftime('%Y%m%d') + '01')
        current_serial = Record.objects.filter(domain=self.domain).aggregate(
            models.Max('change_date'))['change_date__max']
        if current_serial is None or current_serial < generated_serial:
            self.change_date = generated_serial
        else:
            self.change_date = current_serial + 1

    def save(self, *args, **kwargs):
        self.update_change_date()
        super(Record, self).save(*args, **kwargs)

    class Meta:
        db_table = 'records'
        ordering = ['name', 'type', 'content']


# class Supermasters(models.Model):
#     ip = models.GenericIPAddressField()
#     nameserver = models.CharField(max_length=255)
#     account = models.CharField(max_length=40, blank=True)
#     class Meta:
#         db_table = 'supermasters'

# class Tsigkeys(models.Model):
#     id = models.IntegerField(primary_key=True)
#     name = models.CharField(max_length=255, blank=True)
#     algorithm = models.CharField(max_length=50, blank=True)
#     secret = models.CharField(max_length=255, blank=True)
#     class Meta:
#         db_table = 'tsigkeys'
