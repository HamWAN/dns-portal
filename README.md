# Overview

The dns-portal provides a GUI for managing basic host and network information for a site.  It integrates
with powerdns and is built on Django.  Besides basic network information (host names and IP addresses), it
also tracks basic inventory information including location, site, ownership, function, and can store adhoc notes
for each object. More information on setup can be found on
[the HamWAN website](https://hamwan.org/Standards/Network%20Engineering/Cell%20Site%20Configuration/Servers.html).

# Installation

## Create a Virtualenv

    virtualenv env
    source env/bin/activate

## Install Dependencies

    pip install -r requirements.txt

## The Directory Strucure

This is a Django web app and follows its standard structure.
Two directories contain site specific information and the files will need
to be edited for your specific implementation. The directories are provided as
templates (config.template and deploy.template). Your first step should be to make copies:

    cp -pr config.template config
    cp -pr deploy.template deploy

Later, after pulling updated versions the templates (git pull), you will want to diff your current config and deploy
to find any changes that you need to apply from the updated templates. You may also choose to commit these files to
a private git repo.

# Test

    python manage.py test

# Run

    python manage.py syncdb
    python manage.py migrate
    python manage.py runserver

Open in browser: http://127.0.0.1:8000/admin/

## Postgresql fix (after running manage.py migrate)

Manually change portal_ipaddress.ip to type "inet":

    sudo su postgres
    psql -d portal
    ALTER TABLE portal_ipaddress ALTER COLUMN ip TYPE inet USING(ipinet);
    or if that fails (in newer Postgresql)
    ALTER TABLE portal_ipaddress ALTER COLUMN ip TYPE inet USING ip::inet;
    \q
    exit

## Initial Data

Add the domains you will be serving authoritatively in DNS > Domains.
Then you will need to add SOA and NS records for each domain you are serving
including in-addr.arpa and ip6.arpa (if you have IPv6 addresses). Add these records 
in DNA > Records.
The content field for an SOA looks like this:

    a.ns.hamwan.net hostmaster.hamwan.org 0 86400 7200 3600000 86400

The content field for an NS record is just the DNS name of a authoritative nameserver for that domain, for example:

    a.ns.hamwan.net
    b.ns.hamwan.net

You will then want to add host records with addresses for these nameservers with IP addresses.  (Portal > Hosts)
