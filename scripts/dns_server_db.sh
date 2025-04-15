#!/bin/bash

# --- CONFIGURATION ---
DB_USER="root"
DB_NAME="dns_servers"
TABLE_NAME="dns_servers"
INPUT_FILE="dns_servers.txt"

# --- SETUP DATABASE ---
mysql -u"$DB_USER" -e "CREATE DATABASE IF NOT EXISTS $DB_NAME;"
mysql -u"$DB_USER" -D "$DB_NAME" -e "
CREATE TABLE IF NOT EXISTS $TABLE_NAME (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(45),
    dns_data TEXT,
    dnssec_support BOOLEAN,
    owner VARCHAR(255),
    geo_location VARCHAR(255)
);"

while read -r ip; do
    echo "Processing $ip..."

    dns_output=$(dig +dnssec @"$ip")
    dns_output_escaped=$(echo "$dns_output" | sed "s/'/''/g")

    supports_dnssec="0"
    if echo "$dns_output" | grep -q "RRSIG"; then
        supports_dnssec="1"
    fi

    owner=$(whois "$ip" | grep -E "OrgName|Organization|org-name|descr|mnt-by|owner" | head -n 1 | awk -F ': ' '{print $2}' | xargs)
    if [ -z "$owner" ]; then
        owner=$(echo "$whois_output" | grep -Ei "netname" | head -n 1 | cut -d: -f2- | xargs)
    fi
    if [ -z "$owner" ]; then
        owner="Unknown"
    fi
    owner_escaped=$(echo "$owner" | sed "s/'/''/g")

    geo=$(geoiplookup "$ip" | head -n 1 | cut -d: -f2- | xargs)
    geo_escaped=$(echo "$geo" | sed "s/'/''/g")

    mysql -u"$DB_USER" -D "$DB_NAME" -e "
    INSERT INTO $TABLE_NAME (ip, dns_data, dnssec_support, owner, geo_location)
    VALUES ('$ip', '$dns_output_escaped', $supports_dnssec, '$owner_escaped', '$geo_escaped');"

done < "$INPUT_FILE"
