#!/bin/bash

# Configuration
DB_HOST="localhost"
DB_USER="pink"
DB_PASS="passw"
DB_NAME="dns_servers"

# Machine_id: 0 for VU VM and 1 for Cloudlab VM
resolvers=$(mysql -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -N -e "
    SELECT id, ip FROM dns_resolvers
    WHERE id NOT IN (SELECT DISTINCT resolver_id FROM traceroute_hops);
")

echo "Found $(echo "$resolvers" | wc -l) resolvers to trace"

while IFS=$'\t' read -r resolver_id ip_address; do
    echo "Tracing $ip_address (ID: $resolver_id)"
    traceroute_output=$(traceroute "$ip_address" 2>/dev/null)

    printf "$traceroute_output" | while IFS= read -r line; do
        if [[ "$line" =~ ^[[:space:]]*[0-9]+ ]]; then
            hop_num=$(printf '%s' "$line" | awk '{print $1}')

            # Extract IP address from parentheses
            hop_ip=$(printf '%s' "$line" | grep -oE '\([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\)' | head -1 | tr -d '()' )
            hostname=$(printf '%s' "$line" | awk '{print $2}')

            if [ -n "$hop_ip" ]; then
                if [ -n "$hostname" ] && [ "$hostname" != "*" ]; then
                    escaped_hostname=$(printf '%s' "$hostname" | sed "s/'/''/g")
                    hostname_sql="'$escaped_hostname'"
                else
                    hostname_sql="NULL"
                fi

                mysql -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
                INSERT INTO traceroute_hops (resolver_id, machine_id, hop_number, ip_address, hostname)
                VALUES ($resolver_id, 0, $hop_num, '$hop_ip', "$hostname_sql");
                " 2>/dev/null
            fi
        fi
    done

    sleep 0.5

done <<< "$resolvers"

echo "Traceroute completed"
