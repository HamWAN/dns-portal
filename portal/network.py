# https://djangosnippets.org/snippets/1961/
from ipaddr import _IPAddrBase, IPAddress, IPNetwork

from django.forms import ValidationError as FormValidationError
from django.core.exceptions import ValidationError
from django.forms import fields, widgets
from django.db import models
from django.core.validators import validate_ipv46_address


def reverse(ip):
    return "%s.in-addr.arpa" % '.'.join(str(ip).split('.')[::-1])


def validate_ipv46_address_str(value):
    return validate_ipv46_address(str(value))


class IPNetworkWidget(widgets.TextInput):
    def render(self, name, value, attrs=None, **kwargs):
        if isinstance(value, _IPAddrBase):
            value = str(value)
        return super(IPNetworkWidget, self).render(name, value, attrs, **kwargs)


class IPNetworkManager(models.Manager):
    use_for_related_fields = True

    def __init__(self, qs_class=models.query.QuerySet):
        self._queryset_class = qs_class
        super(IPNetworkManager, self).__init__()

    #def get_query_set(self):
    #    return self._queryset_class(self.model)

    def get_queryset(self):
        return self._queryset_class(self.model, using=self._db)

    def __getattr__(self, attr, *args):
        try:
            return getattr(self.__class__, attr, *args)
        except AttributeError:
            return getattr(self.get_query_set(), attr, *args)


class IPNetworkQuerySet(models.query.QuerySet):   

    net = None

    def network(self, key, value):
        if not isinstance(value, _IPAddrBase):
            value = IPNetwork(value)
        self.net = (key, value)
        return self

    def iterator(self):
        for obj in super(IPNetworkQuerySet, self).iterator():
            try:
                net = IPNetwork(getattr(obj, self.net[0]))   
            except (ValueError, TypeError):
                pass
            else:
                if not self.net[1] in net:
                   continue
            yield obj
            
    #@classmethod
    #def as_manager(cls, ManagerClass=IPNetworkManager):
    #    return ManagerClass(cls)

    @classmethod
    def as_manager(cls):
        class CustomManager(models.Manager):
            def get_queryset(self):
                return cls(self.model, using=self._db)

        return CustomManager()


class IPNetworkField(models.Field):
    description = "IP Network Field with CIDR support"
    empty_strings_allowed = False
    
    def db_type(self, connection):
        return 'varchar(45)'

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        # Convert the value from database format to Python object
        return self.to_python(value)

    def to_python(self, value):
        if not value:
            return None

        if isinstance(value, _IPAddrBase):
            return value

        try:
#            return IPNetwork(value.encode('latin-1'))
            return IPNetwork(value)
        except Exception as e:
            raise ValidationError(e)

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type == 'exact':
            return self.get_prep_value(value)
        elif lookup_type == 'in':
            return [self.get_prep_value(v) for v in value]           
        else:
            raise TypeError('Lookup type %r not supported.' \
                % lookup_type)

    def get_prep_value(self, value):
        if isinstance(value, _IPAddrBase):
            value = '%s' % value
        return str(value)
      
    def formfield(self, **kwargs):
        defaults = {
            'form_class' : fields.CharField,
            'widget': IPNetworkWidget(),
        }
        defaults.update(kwargs)
        return super(IPNetworkField, self).formfield(**defaults)


class IPAddressField(models.Field):
    description = "IP Address Field with IPv6 support"
    default_validators = [validate_ipv46_address_str]
    
    def db_type(self, connection):
        return 'varchar(42)'

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        # Convert the value from database format to Python object
        return self.to_python(value)

    def to_python(self, value):
        if not value or value == 'None':
            return None

        if isinstance(value, _IPAddrBase):
            return value

        try:
#            return IPAddress(value.encode('latin-1')) #premptively changing this
            return IPAddress(value)
        except Exception as e:
            return value
            raise ValidationError(e)

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type == 'exact':
            return self.get_prep_value(value)
        elif lookup_type == 'in':
            return [self.get_prep_value(v) for v in value]           
        else:
            return super(IPAddressField, self).get_prep_lookup(lookup_type, value)

    def get_prep_value(self, value):
        if isinstance(value, _IPAddrBase):
            value = '%s' % value
        return str(value)
      
    def formfield(self, **kwargs):
        defaults = {
            'form_class' : fields.CharField,
            'widget': IPNetworkWidget(),
        }
        defaults.update(kwargs)
        return super(IPAddressField, self).formfield(**defaults)
