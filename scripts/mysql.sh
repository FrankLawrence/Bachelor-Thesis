#!/bin/bash
# query="SELECT COUNT(*) AS Count,query_type AS Query FROM openintel WHERE as_full IS NOT NULL GROUP BY query_type;"
# result=$(sudo mysql -u root dns_servers -e "$query")

mysql_query() {
    local query="$1"
    sudo mysql -u root dns_servers -sN -e "$query"
}

num_dist_nameservers=$(mysql_query "
SELECT
    COUNT(DISTINCT nameserver)
FROM nameservers;")

num_domains_openintel=$(mysql_query "
SELECT
    COUNT(DISTINCT query_name)
FROM openintel;")
num_domains_openintel_rrsig=$(mysql_query "
SELECT
    COUNT(DISTINCT query_name)
FROM openintel
WHERE rrsig_signature IS NOT NULL;")

num_gov_domains=$(mysql_query "
SELECT
    COUNT(DISTINCT query_name)
FROM gov_domains;")
num_gov_domains_rrsig=$(mysql_query "
SELECT
COUNT(DISTINCT query_name)
FROM gov_domains
WHERE rrsig_signature IS NOT NULL;")

query="
SELECT
    COUNT(*) AS 'Count (domains)',
    nameserver AS Nameserver
FROM tranco AS t
JOIN tranco_nameservers AS tn ON domain_id=t.id
JOIN nameservers AS n ON nameserver_id=n.id
GROUP BY nameserver
ORDER BY COUNT(*) DESC
LIMIT 10;"
top_10_nameservers_tranco=$(mysql_query "
SELECT
    COUNT(*) AS 'Count (domains)',
    nameserver AS Nameserver,
    owner_nameserver AS Owner
FROM tranco AS t
JOIN tranco_nameservers AS tn ON domain_id=t.id
JOIN nameservers AS n ON nameserver_id=n.id
GROUP BY nameserver, owner_nameserver
ORDER BY COUNT(*) DESC
LIMIT 10;")

# top_10_asn_openintel=$(mysql_query "
# SELECT
#     COUNT(DISTINCT query_name) AS 'COUNT (domains)',
#     `as` AS ASN
# FROM openintel
# WHERE `as` IS NOT NULL
# GROUP BY `as`
# ORDER BY COUNT(*) DESC
# LIMIT 10") &

num_dns_resolvers=$(mysql_query "
SELECT
    COUNT(*)
FROM dns_resolvers;")
top_10_country_resolvers=$(mysql_query "
SELECT
   COUNT(*) AS 'Count (DSN Resolvers)',
   geo_location AS COUNTRY
FROM dns_resolvers AS d
GROUP BY geo_location
ORDER BY COUNT(*) DESC
LIMIT 10;")

num_nonvalidated_openintel=$(mysql_query "
SELECT
COUNT(DISTINCT query_name)
FROM openintel
WHERE ad_flag IS false;")
num_validated_openintel=$(mysql_query "
SELECT
    COUNT(DISTINCT query_name)
FROM openintel
WHERE ad_flag IS true;")
num_nonvalidated_gov=$(mysql_query "
SELECT
    COUNT(DISTINCT query_name)
FROM gov_domains
WHERE ad_flag IS false;")
num_validated_gov=$(mysql_query "
SELECT
    COUNT(DISTINCT query_name)
FROM gov_domains
WHERE ad_flag IS true;")

num_domain_and_ns_owner=$(mysql_query "
SELECT
    COUNT(*)
FROM tranco AS t
JOIN tranco_nameservers AS tn ON domain_id=t.id
JOIN nameservers AS n ON nameserver_id=n.id
WHERE owner=n.owner_nameserver;")

# Top domain owners
query="
SELECT
    COUNT(*) AS Count,
    owner AS 'Domain owner'
FROM tranco
GROUP BY owner
ORDER BY COUNT(*);"

clear
printf "\e[1;41m%.20b\e[0m\n" "Openintel\n"
# printf "The most popular response types that give the ASN are: \n$result\n\n"
# printf "OpenIntel collected data for $num_domains_openintel domains ($num_domains_openintel_rrisg of them have a registered rrsig signature)\n"
printf "num openintel domains: $num_domains_openintel ($num_domains_openintel_rrsig with rrsig)\n"
printf "Openintel: $num_nonvalidated_openintel not validated, $num_validated_openintel validated by DNSSEC\n"

printf "\e[1;41m%.6b\e[0m\n" "Tranco\n"
# printf "There are $num_dist_nameservers different nameservers in the tranco 1 million list.\n"
printf "Nameserver tranco count: $num_dist_nameservers\n
Number nameservers owned by domain owner: $num_domain_and_ns_owner\n"
printf "The top 10 most used nameservers from the tranco 1 million are: \n$top_10_nameservers_tranco.\n\n"
# The top 10 most used AS from the openintel list are: \n$top_10_asn_openintel\n\n"
# printf "In total, the dns_resolvers database has $num_dns_resolvers dns resolvers and nameservers combined.\n"
printf "num dns resolvers and nameservers (zmap): $num_dns_resolvers\n"

printf "\e[1;41m%.11b\e[0m\n" "Gov Domains\n"
# printf "There are $num_gov_domains registered .gov domains ($num_gov_domains_rrsig of them have a registered rrsig signature).\n"
printf "num .gov domains: $num_gov_domains ($num_gov_domains_rrsig with rrsig)\n
Gov Domains: $num_nonvalidated_gov not validated, $num_validated_gov validated by DNSSEC\n"

printf "DNS resolvers that respond to me:\n"
my_asn=$(mysql_query '
SELECT as_name
FROM as_ip_ranges AS air
WHERE INET_ATON("130.37.198.76")
    BETWEEN INET_ATON(air.start_ip) AND INET_ATON(air.end_ip)')
printf "My ip is $(curl -o /dev/null https://ipinfo.io/ip), and my ASN is $my_asn.\n"
