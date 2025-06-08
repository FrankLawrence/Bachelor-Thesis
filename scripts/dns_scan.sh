#!/bin/bash

# --- CONFIGURATION ---
DB_USER="root"
DB_NAME="dns_servers"
TABLE_NAME="dns_resolvers"
AS_TABLE="as_ip_ranges"

# --- HELPER FUNCTION ---
majority_vote() {
    values=("$@")
    printf "%s\n" "${values[@]}" | sort | uniq -c | sort -nr | head -n1 | awk '{$1=""; print $0}' | xargs
}

echo "Fetching IPs from MySQL database..."
ip_list=($(sudo mysql -u"$DB_USER" -N -e "SELECT ip FROM $DB_NAME.$TABLE_NAME WHERE ip IS NOT NULL;"))


# --- PROCESS IP LIST ---
# while read -r ip; do
for ip in "${ip_list[@]}"; do
    echo "Processing $ip..."

    # --- DNS INFO ---
    dig_output=$(dig +dnssec @"$ip")
    dig_output_escaped=$(echo "$dig_output" | sed "s/'/\\\'/g")

    supports_dnssec="0"
    if echo "$dig_output" | grep -q "RRSIG"; then
        supports_dnssec="1"
    fi

    # --- WHOIS for owner and RIR ---
    whois_output=$(whois "$ip")

    owner=$(echo "$whois_output" | grep -Ei "OrgName|org-name" | head -n 1 | cut -d: -f2- | xargs)
    [ -z "$owner" ] && owner=$(echo "$whois_output" | grep -Ei "Organization|descr|owner" | head -n 1 | cut -d: -f2- | xargs)
    [ -z "$owner" ] && owner="Unknown"

    # --- ASN & AS NAME from local table ---
    as_info=$(sudo mysql -u"$DB_USER" -N -e "
        SELECT asn, as_name, start_ip, end_ip
        FROM $DB_NAME.$AS_TABLE
        WHERE INET_ATON('$ip') BETWEEN INET_ATON(start_ip) AND INET_ATON(end_ip)
        LIMIT 1;
    ")

    asn=$(echo "$as_info" | awk '{print $1}')
    as_name=$(echo "$as_info" | cut -d'	' -f2 | sed "s/'/''/g")

    # ASN, IP Range
    [ -z "$asn" ] && asn=$(echo "$whois_output" | grep -i 'origin' | head -n 1 | awk '{print $2}' | xargs)
    [ -z "$as_name" ] && as_name=$(echo "$whois_output" | grep netname | head -n 1 | cut -d: -f2- | xargs);
    [ -z "$asn" ] && asn="Unknown"
    [ -z "$as_name" ] && as_name="Unknown"

    # --- GEO LOOKUP (Majority Vote) ---
    geo1=$(geoiplookup "$ip" | cut -d: -f2- | xargs | cut -c 1-2)
    # geo2=$(mmdblookup --file /usr/share/GeoIP/GeoLite2-City.mmdb --ip "$ip" | grep city | tail -1 | awk -F '"' '{print $4}' | xargs)
    geo2=$(echo "$whois_output" | grep 'country' | head -n1 | awk '{print $2}' | xargs | cut -c 1-2)
    #geo3=$(curl -s "https://ipinfo.io/$ip/country" 2>/dev/null | xargs)

    geo=$(majority_vote "$geo1" "$geo3")

    # --- ESCAPE FOR SQL ---
    owner_escaped=$(echo "$owner" | sed "s/'/''/g")
    geo_escaped=$(echo "$geo" | sed "s/'/''/g")
    as_name_escaped=$(echo "$as_name" | sed "s/'/''/g")

    # --- INSERT / UPDATE ---
    sudo mysql -u"$DB_USER" -D "$DB_NAME" -e "
    INSERT INTO $TABLE_NAME (ip, dns_data, dnssec_support, owner, geo_location, asn, as_name, dnssec_validated)
    VALUES ('$ip', '$dns_output_escaped', $supports_dnssec, '$owner_escaped', '$geo_escaped', '$asn', '$as_name_escaped', '$dnssec_validated')
    ON DUPLICATE KEY UPDATE
        dns_data = VALUES(dns_data),
        dnssec_support = VALUES(dnssec_support),
        owner = VALUES(owner),
        geo_location = VALUES(geo_location),
        asn = VALUES(asn),
        as_name = VALUES(as_name),
        dnssec_validated = VALUES(dnssec_validated);
    "
    sudo mysql -u"$DB_USER" -D "$DB_NAME" -e "
    UPDATE $TABLE_NAME SET dig_output = '$dig_output_escaped', dnssec_support = $supports_dnssec WHERE ip = '$ip'
    "

done # < "$INPUT_FILE"
