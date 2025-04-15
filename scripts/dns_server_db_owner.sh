#!/bin/bash

DB_USER="root"
DB_NAME="dns_servers"
TABLE_NAME="dns_servers"

# Get list of IPs from the database
ips=$(mysql -u"$DB_USER" -N -e "SELECT ip FROM $DB_NAME.$TABLE_NAME;")

for ip in $ips; do
    echo "Processing $ip..."

    # Step 1: Run initial whois query to detect RIR
    initial_whois=$(whois "$ip")
    rir_source=$(echo $(echo "$initial_whois" | grep source | awk '{print tolower($2)}') | awk '{print $1}')

    # Default fallback
    whois_server=""

    case "$rir_source" in
        apnic) whois_server="whois.apnic.net" ;;
        ripe) whois_server="whois.ripe.net" ;;
        lacnic) whois_server="whois.lacnic.net" ;;
        afrinic) whois_server="whois.afrinic.net" ;;
        arin | *) whois_server="whois.arin.net" ;;
    esac

    # Step 2: Query the proper RIR whois server
    whois_output=$(whois -h "$whois_server" "$ip")

    # Try to extract organization/owner from several likely fields
    owner=$(echo "$whois_output" | grep -E "OrgName|org-name|Organization|descr|owner" | head -n 1 | cut -d':' -f2- | xargs)

    # Fallbacks
    if [ -z "$owner" ]; then
        owner=$(echo "$whois_output" | grep -Ei "netname" | head -n 1 | cut -d: -f2- | xargs)
    fi
    if [ -z "$owner" ]; then
        owner="Unknown"
    fi

    # Escape quotes for SQL
    owner_escaped=$(echo "$owner" | sed "s/'/''/g")

    # Update DB with new owner
    mysql -u"$DB_USER" -D "$DB_NAME" -e "
    UPDATE $TABLE_NAME SET owner = '$owner_escaped' WHERE ip = '$ip';
    "
done
