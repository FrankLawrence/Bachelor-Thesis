#!/bin/bash

# --- CONFIGURATION ---
DB_USER="root"
DB_NAME="dns_servers"
TABLE_NAME="dns_servers"
INPUT_FILE="dns_servers.txt"

# --- SETUP DATABASE ---
sudo mysql -u"$DB_USER" -e "CREATE DATABASE IF NOT EXISTS $DB_NAME;"
sudo mysql -u"$DB_USER" -D "$DB_NAME" -e "
CREATE TABLE IF NOT EXISTS $TABLE_NAME (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(45) UNIQUE,
    dns_data TEXT,
    dnssec_support BOOLEAN,
    owner VARCHAR(255),
    geo_location VARCHAR(255),
    asn VARCHAR(50),
    as_name VARCHAR(255),
    ip_range VARCHAR(255),
    dnssec_validated BOOLEAN,
    dnssec_error_summary TEXT,
    dnssec_status_code INT,
    reported_ns TEXT
);"

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
    dns_output=$(dig +dnssec @"$ip")
    dns_output_escaped=$(echo "$dns_output" | sed "s/'/''/g")

    supports_dnssec="0"
    if echo "$dns_output" | grep -q "RRSIG"; then
        supports_dnssec="1"
    fi

    # --- WHOIS + ASN ---
    initial_whois=$(whois "$ip")
    rir_source=$(echo "$initial_whois" | grep -i "^source:" | awk '{print tolower($2)}' | head -n 1)
    case "$rir_source" in
        apnic) whois_server="whois.apnic.net" ;;
        ripe) whois_server="whois.ripe.net" ;;
        lacnic) whois_server="whois.lacnic.net" ;;
        afrinic) whois_server="whois.afrinic.net" ;;
        arin | *) whois_server="whois.arin.net" ;;
    esac

    whois_output=$(whois -h "$whois_server" "$ip")

    owner=$(echo "$whois_output" | grep -Ei "OrgName|org-name" | head -n 1 | cut -d: -f2- | xargs)
    [ -z "$owner" ] && owner=$(echo "$whois_output" | grep -Ei "Organization|descr|owner" | head -n 1 | cut -d: -f2- | xargs)
    [ -z "$owner" ] && owner=$(echo "$whois_output" | grep -Ei "netname" | head -n 1 | cut -d: -f2- | xargs)
    [ -z "$owner" ] && owner="Unknown"

    # ASN, IP Range
    asn=$(echo "$whois_output" | grep -i 'origin' | head -n 1 | awk '{print $2}' | xargs)
    ip_range=$(echo "$whois_output" | grep -Ei 'inetnum|NetRange' | head -n 1 | cut -d: -f2- | xargs)

    # Get AS Name from origin AS number
    as_name="Unknown"
    if [[ "$asn" =~ ^AS[0-9]+$ ]]; then
        asn_num=${asn#AS}
        as_lookup=$(whois -h whois.radb.net "$asn")
        as_name=$(echo "$as_lookup" | grep -i 'as-name' | head -n1 | cut -d: -f2- | xargs)
    fi

    # --- GEO LOOKUP (Majority Vote) ---
    geo1=$(geoiplookup "$ip" | cut -d: -f2- | xargs | cut -c 1-2)
    # geo2=$(mmdblookup --file /usr/share/GeoIP/GeoLite2-City.mmdb --ip "$ip" | grep city | tail -1 | awk -F '"' '{print $4}' | xargs)
    geo2=$(echo "$whois_output" | grep 'country' | head -n1 | awk '{print $2}' | xargs | cut -c 1-2)
    #geo3=$(curl -s "https://ipinfo.io/$ip/country" 2>/dev/null | xargs)

    geo=$(majority_vote "$geo1" "$geo3")

    # DNSSEC Validation Check (optional: use google.com or another known good domain)
    domain_to_check="google.com"
    dnsviz_result=$(dnsviz probe "$domain_to_check" +json 2>/dev/null)

    # Parse result
    dnssec_validated="0"
    dnssec_status_code="2"  # default to "fail"
    dnssec_error_summary="Unknown"

    if echo "$dnsviz_result" | jq '.status' | grep -q 'ok'; then
        dnssec_validated="1"
        dnssec_status_code="0"
        dnssec_error_summary="Valid"
    elif echo "$dnsviz_result" | jq '.warnings' | grep -q .; then
        dnssec_status_code="1"
        dnssec_error_summary="Warnings present"
    else
        dnssec_error_summary=$(echo "$dnsviz_result" | jq -r '.errors[]?' | head -n 1)
    fi
    # Get reported name servers if any
    # reported_ns=$(dig @"$ip" +nssearch wurt.net | grep SOA | awk '{print $11}')


    # --- ESCAPE FOR SQL ---
    owner_escaped=$(echo "$owner" | sed "s/'/''/g")
    geo_escaped=$(echo "$geo" | sed "s/'/''/g")
    as_name_escaped=$(echo "$as_name" | sed "s/'/''/g")
    ip_range_escaped=$(echo "$ip_range" | sed "s/'/''/g")
    dnssec_error_summary_escaped=$(echo "$dnssec_error_summary" | sed "s/'/''/g")
    reported_ns_escaped=$(echo "$reported_ns" | sed "s/'/''/g")

    # --- INSERT / UPDATE ---
    sudo mysql -u"$DB_USER" -D "$DB_NAME" -e "
    INSERT INTO $TABLE_NAME (ip, dns_data, dnssec_support, owner, geo_location, asn, as_name, ip_range, \
    dnssec_validated, dnssec_error_summary, dnssec_status_code, reported_ns)
    VALUES ('$ip', '$dns_output_escaped', $supports_dnssec, '$owner_escaped', '$geo_escaped', '$asn', '$as_name_escaped', '$ip_range_escaped', \
    '$dnssec_validated', '$dnssec_error_summary_escaped', '$dnssec_status_code', '$reported_ns_escaped')
    ON DUPLICATE KEY UPDATE
        dns_data = VALUES(dns_data),
        dnssec_support = VALUES(dnssec_support),
        owner = VALUES(owner),
        geo_location = VALUES(geo_location),
        asn = VALUES(asn),
        as_name = VALUES(as_name),
        ip_range = VALUES(ip_range),
        dnssec_validated = VALUES(dnssec_validated),
        dnssec_error_summary = VALUES(dnssec_error_summary),
        dnssec_status_code = VALUES(dnssec_status_code),
        reported_ns = VALUES(reported_ns);
    "

done # < "$INPUT_FILE"
