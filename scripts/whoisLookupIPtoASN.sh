#!/bin/bash
# The following script can be used to perform whois lookups to IPs to get their ASN in "Bulk mode" using netcat
# Usage: <gzip compressed Tranco ndjson file; make sure there is a dip field in it>

zcat "$1" | jq -r '.dip' | (echo "begin"; cat | sort -u; echo "end") | \
netcat whois.cymru.com 43 | cut -d' ' -f1 | sed 1d
