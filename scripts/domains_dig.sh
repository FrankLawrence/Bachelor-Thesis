#!/bin/bash

DB_HOST="localhost"
DB_USER="root"
DB_PASS="passw"
DB_NAME="dns_servers"
# --- HELPER FUNCTION ---
majority_vote() {
    values=("$@")
    printf "%s\n" "${values[@]}" | sort | uniq -c | sort -nr | head -n1 | awk '{$1=""; print $0}' | xargs
}

# Get rows where IP is NULL
domains=$(sudo mysql -h "$DB_HOST" -u "$DB_USER" "$DB_NAME" -Bse \
  "SELECT id, domain FROM tranco WHERE dig_output IS NOT NULL")

while IFS=$'\t' read -r id domain; do
  echo "🔍 [$id] Processing domain: $domain"
  dig_output_domain=$(sudo mysql -h "$DB_HOST" -u "$DB_USER" "$DB_NAME" -Bse "
    SELECT dig_output FROM tranco WHERE id='${id}' LIMIT 1;")

  # Get ALL NS records, remove QUESTION section
  ns_list=$(printf "$dig_output_domain" | grep -e "IN.*NS" | sed 's/\.$//' | tail -n +2 | awk '{print $NF}')

  for ns in $ns_list; do
    ns_ip=$(dig +short "$ns" A | head -n1)

    owner_ns=""
    country_ns=""
    if [[ -n "$ns_ip" ]]; then
      whois_ns=$(whois "$ns_ip")
      owner_ns=$(echo "$whois_ns" | grep -iE "org-name|OrgName|descr|owner" | head -n1 | cut -d: -f2- | xargs)
      geo1=$(geoiplookup "$ns_ip" | cut -d: -f2- | xargs | cut -c 1-2)
      geo2=$(echo "$whois_ns" | grep -iE "^country" | head -n1 | cut -d: -f2- | xargs)
      country_ns=$(majority_vote "$geo1" "$geo3")
    fi

    # keyword=$(echo "$domain" | awk -F. '{print $(NF-1)}')
    # if echo "$ns" | grep -qi "$keyword"; then
    #   privately_run=1
    # else
    #   privately_run=0
    # fi
    privately_run=0
    if [[ -n "$owner_domain" && -n "$owner_ns" && "$owner_domain" == "$owner_ns" ]]; then
      privately_run=1
    fi

    # Escape for SQL
    ns_esc=$(printf "%q" "$ns")
    ns_ip_esc=$(printf "%q" "$ns_ip")
    owner_ns_esc=$(printf "%q" "$owner_ns")
    country_ns_esc=$(printf "%q" "$country_ns")

    # Insert nameserver (if not exists)
    sudo mysql -h "$DB_HOST" -u "$DB_USER" "$DB_NAME" -e "
      INSERT IGNORE INTO nameservers (nameserver, ip_nameserver, owner_nameserver, country_nameserver, whois_output)
      VALUES ('${ns_esc}', '${ns_ip_esc}', '${owner_ns_esc}', '${country_ns_esc}', '${whois_output}');"

    # Get nameserver id
    ns_id=$(sudo mysql -h "$DB_HOST" -u "$DB_USER" "$DB_NAME" -Bse "
      SELECT id FROM nameservers WHERE nameserver='${ns_esc}' LIMIT 1;")

    # Insert mapping into tranco_nameservers
    sudo mysql -h "$DB_HOST" -u "$DB_USER" "$DB_NAME" -e "
      INSERT IGNORE INTO tranco_nameservers (domain_id, nameserver_id)
      VALUES (${id}, ${ns_id});"

    if [[ "$privately_run" -eq 1 ]]; then
      sudo mysql -h "$DB_HOST" -u "$DB_USER" "$DB_NAME" -e "
        UPDATE tranco SET privately_run=1 WHERE id=${id};"
    fi

  done

done <<< "$domains"
