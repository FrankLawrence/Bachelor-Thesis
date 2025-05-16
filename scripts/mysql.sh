#!/bin/bash
query="SELECT COUNT(*) AS Count,query_type AS Query FROM openintel WHERE as_full IS NOT NULL GROUP BY query_type;"
result=$(sudo mysql -u root dns_servers -e "$query")
query="SELECT COUNT(DISTINCT nameserver) FROM tranco;"
num_dist_nameservers=$(sudo mysql -u root dns_servers -sN -e "$query")

query="SELECT COUNT(DISTINCT query_name) FROM openintel;"
num_domains_openintel=$(sudo mysql -u root dns_servers -sN -e "$query")
query="SELECT COUNT(DISTINCT query_name) FROM openintel where rrsig_signature IS NOT NULL;"
num_domains_openintel_rrsig=$(sudo mysql -u root dns_servers -sN -e "$query")

query="SELECT COUNT(DISTINCT query_name) FROM gov_domains;"
num_gov_domains=$(sudo mysql -u root dns_servers -sN -e "$query")
query="SELECT COUNT(DISTINCT query_name) FROM gov_domains where rrsig_signature IS NOT NULL;"
num_gov_domains_rrsig=$(sudo mysql -u root dns_servers -sN -e "$query")

query="SELECT COUNT(*) AS Count,nameserver AS Nameserver FROM tranco GROUP BY nameserver ORDER BY COUNT(*) DESC LIMIT 10;"
top_10_nameservers_tranco=$(sudo mysql -u root dns_servers -e "$query")
query="SELECT COUNT(*) FROM dns_resolvers;"
num_dns_resolvers=$(sudo mysql -u root dns_servers -sN -e "$query")

query="SELECT COUNT(DISTINCT query_name) FROM openintel WHERE ad_flag IS false;"
num_nonvalidated_openintel=$(sudo mysql -u root dns_servers -sN -e "$query")
query="SELECT COUNT(DISTINCT query_name) FROM openintel WHERE ad_flag IS true;"
num_validated_openintel=$(sudo mysql -u root dns_servers -sN -e "$query")
query="SELECT COUNT(DISTINCT query_name) FROM gov_domains WHERE ad_flag IS false;"
num_nonvalidated_gov=$(sudo mysql -u root dns_servers -sN -e "$query")
query="SELECT COUNT(DISTINCT query_name) FROM gov_domains WHERE ad_flag IS true;"
num_validated_gov=$(sudo mysql -u root dns_servers -sN -e "$query")

# Top domain owners
query="SELECT COUNT(*) AS Count,owner AS 'Domain owner' FROM tranco GROUP BY owner ORDER BY COUNT(*);"

printf "\e[1;41m%.20b\e[0m\n" "Openintel\n"
printf "The most popular response types that give the ASN are: \n$result\n\n"
# printf "OpenIntel collected data for $num_domains_openintel domains ($num_domains_openintel_rrisg of them have a registered rrsig signature)\n"
printf "num openintel domains: $num_domains_openintel ($num_domains_openintel_rrsig with rrsig)\n"
printf "Openintel: $num_nonvalidated_openintel not validated, $num_validated_openintel validated by DNSSEC\n"

printf "\e[1;41m%.20b\e[0m\n" "Tranco\n"
# printf "There are $num_dist_nameservers different nameservers in the tranco 1 million list.\n"
printf "nameserver tranco count: $num_dist_nameservers\n"
printf "The top 10 most used nameservers from the tranco 1 million are: \n$top_10_nameservers_tranco.\n\n"
# printf "In total, the dns_resolvers database has $num_dns_resolvers dns resolvers and nameservers combined.\n"
printf "num dns resolvers and nameservers (zmap): $num_dns_resolvers\n"

printf "\e[1;41m%.20b\e[0m\n" "Gov Domains\n"
# printf "There are $num_gov_domains registered .gov domains ($num_gov_domains_rrsig of them have a registered rrsig signature).\n"
printf "num .gov domains: $num_gov_domains ($num_gov_domains_rrsig with rrsig)\n"
printf "Gov Domains: $num_nonvalidated_gov not validated, $num_validated_gov validated by DNSSEC\n"
