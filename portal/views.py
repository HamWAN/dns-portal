import json

from django.db import DataError
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.forms.models import inlineformset_factory
from django.utils.decorators import method_decorator
from django.views.generic.edit import DeleteView

from portal.models import Host, IPAddress, Site, Subnet
from .forms import UserHostForm, UserForm, UserIPAddressForm, IPAddressFormset, UserSubnetForm


@login_required
def index(request):
    return render(request, 'portal/index.html', {
        'own_hosts':  Host.objects.select_related('owner')
            .prefetch_related('ipaddresses').filter(owner=request.user),
        'authorized_hosts':  Host.objects.select_related('owner')
            .prefetch_related('ipaddresses').filter(admins=request.user),
        'own_subnets':  Subnet.objects.select_related('owner').filter(owner=request.user),
    })


def all_hosts(request):
    return render(request, 'portal/index.html', {
        'all_hosts':  Host.objects.select_related('owner')
            .prefetch_related('ipaddresses').all(),
    })


def ansible_hosts(request):
    """Generates Ansible dynamic inventory new dict format"""

    inventory = {
        # this allows ansible to cache the result, instead of calling per host
        "_meta": {
            "hostvars": {}
        }
    }

    for host in Host.objects.select_related('owner').all():
        groups = [
            "owner_" + str(host.owner or ''),
            "type_" + str(host.type or ''),
            "name_" + str(host.name or ''),
            "os_" + str(host.os or ''),
        ]
        for group in groups:
            if group in inventory:
                inventory[group]["hosts"].append(host.fqdn())
            else:
                inventory[group] = { "hosts": [ host.fqdn() ]}
    return HttpResponse(json.dumps(inventory), content_type="application/json")


def smokeping(request):
    return render(request, 'portal/smokeping.html', {
        'sites':  Site.objects.select_related('host_set').all(),
    }, content_type='text/plain')


@login_required
def own_hosts(request):
    return render(request, 'portal/index.html', {
        'own_hosts':  Host.objects.select_related('owner')
            .prefetch_related('ipaddresses').filter(owner=request.user),
        'authorized_hosts':  Host.objects.select_related('owner')
            .prefetch_related('ipaddresses').filter(admins=request.user),
    })


def all_subnets(request, template='portal/index.html'):
    return render(request, template, {
        'all_subnets':  Subnet.objects.select_related('owner').all(),
    })


@login_required
def own_subnets(request):
    return render(request, 'portal/index.html', {
        'own_subnets':  Subnet.objects.select_related('owner').filter(owner=request.user),
    })


@login_required
def host_detail(request, name=None):
    host = name and Host.objects.get(name=name) or None
    form = UserHostForm(instance=host, request=request)
    IPAddressFormSet = inlineformset_factory(Host, IPAddress,
        form=UserIPAddressForm, formset=IPAddressFormset, extra=2)
    ipformset = IPAddressFormSet(instance=host)

    if host is None:
        can_edit = True
        if request.method == "POST":
            form = UserHostForm(request.POST, instance=host, request=request)
            if form.is_valid():
                form.save()
                messages.success(request, '%s saved. Now add an IP address.' % form.cleaned_data['name'])
                return HttpResponseRedirect('/host/%s' % form.cleaned_data['name'])
            else:
                messages.warning(request, 'Form validation error. Details below.')
    elif host.owner == request.user or request.user in host.admins.all():
        can_edit = True
        if request.method == "POST":
            form = UserHostForm(request.POST, instance=host, request=request)
            ipformset = IPAddressFormSet(request.POST, instance=host)
            if form.is_valid() and ipformset.is_valid():
                form.save()
                ipformset.save()
                messages.success(request, '%s saved.' % form.cleaned_data['name'])
                return HttpResponseRedirect('/')
            else:
                messages.warning(request, 'Form validation error. Details below.')
    else:
        can_edit = False

    return render(request, 'portal/edit_host.html', {
        'host': host,
        'form': form,
        'ipformset': ipformset,
        'can_edit': can_edit,
    })


class HostDelete(DeleteView):
    model = Host
    slug_field = 'name'
    success_url = '/host/'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(HostDelete, self).dispatch(*args, **kwargs)

    def get_object(self, queryset=None):
        """ Hook to ensure object is owned by request.user. """
        obj = super(HostDelete, self).get_object()

        if obj.owner != self.request.user:
            raise Http404
        return obj


@login_required
def subnet_detail(request, network=None):
    try:
        subnet = network and get_object_or_404(Subnet, network=network) or None
    except DataError:
        raise Http404
    form = UserSubnetForm(instance=subnet, request=request)

    if network is None or subnet.owner == request.user:
        can_edit = True
        if request.method == "POST":
            form = UserSubnetForm(request.POST, instance=subnet, request=request)
            if form.is_valid():
                form.save()
                messages.success(request, '%s saved.' % form.cleaned_data['network'])
                return HttpResponseRedirect('/')
            else:
                messages.warning(request, 'Form validation error. Details below.')
    else:
        can_edit = False

    return render(request, 'portal/edit_host.html', {
        'host': subnet,
        'form': form,
        'can_edit': can_edit,
    })


class SubnetDelete(DeleteView):
    model = Subnet
    slug_field = 'network'
    success_url = '/subnet/'
    template_name = 'portal/host_confirm_delete.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(SubnetDelete, self).dispatch(*args, **kwargs)

    def get_object(self, queryset=None):
        """ Hook to ensure object is owned by request.user. """
        obj = super(SubnetDelete, self).get_object()

        if obj.owner != self.request.user:
            raise Http404
        return obj


@login_required
def user_detail(request):
    if request.method == "POST":
        form = UserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'User settings saved.')
            return HttpResponseRedirect('/')
        else:
            messages.warning(request, 'Form validation error. Details below.')
    else:
        form = UserForm(instance=request.user)

    return render(request, 'registration/profile.html', {
        'form': form,
    })
