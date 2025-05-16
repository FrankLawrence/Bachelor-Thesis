import dns.resolver
import requests
import ipaddress
import socket
import pymysql

db = pymysql.connect(
    host="localhost",
    user="pink",
    password="passw",
    database="dns_servers"
)
cursor = db.cursor()

# Get domains with missing info
cursor.execute("SELECT id, domain FROM tranco WHERE ip IS NULL")
domains = cursor.fetchall()
print(f"Fetched {len(domains)} domains to process.")

def get_ip(domain):
    try:
        answer = dns.resolver.resolve(domain, 'A')
        ip = answer[0].to_text()
        print(f"[IP] {domain} → {ip}")
        return ip
    except Exception as e:
        print(f"[IP] Failed to resolve {domain}: {e}")
        return None


def resolve_nameserver_info(domain):
    try:
        ns_records = dns.resolver.resolve(domain, 'NS')
        for rdata in ns_records:
            ns_name = str(rdata.target).rstrip('.')
            try:
                ns_ip = socket.gethostbyname(ns_name)
                org = get_org_from_ip(ns_ip)

                # Check if nameserver is privately run
                domain_keyword = domain.split('.')[-2].lower()
                privately_run = domain_keyword in ns_name or (org and domain_keyword in org.lower())

                print(f"[NS] {domain} → NS: {ns_name} → Org: {org} → Privately run: {privately_run}")
                return ns_name, privately_run
            except Exception as e:
                print(f"[NS] Failed to resolve NS IP: {ns_name} → {e}")
                return ns_name, None
    except Exception as e:
        print(f"[NS] Failed to get NS for {domain}: {e}")
        return None, None


def is_privately_run(domain):
    try:
        ns_answer = dns.resolver.resolve(domain, 'NS')
        for rdata in ns_answer:
            nameserver = str(rdata.target).lower()
            privately_run = domain.lower().split('.')[-2] in nameserver
            print(f"[NS] {domain} → {nameserver} → Privately run: {privately_run}")
            return privately_run, nameserver
    except Exception as e:
        print(f"[NS] Failed to resolve NS for {domain}: {e}")
        return None, None

# Populate DB
for idx, row in enumerate(domains, 1):
    _id, domain = row
    print(f"\n[{idx}/{len(domains)}] Processing domain: {domain} (ID: {_id})")

    ip = get_ip(domain)
    if not ip:
        print(f"[SKIP] Skipping {domain} due to missing IP.")
        continue

    asn, owner, country = get_as_info(ip)
    privately_run, nameserver = is_privately_run(domain)

    print(f"[DB] Updating DB for {domain}...")
    ns_name, privately_run = resolve_nameserver_info(domain)

    update = """
        UPDATE tranco
        SET ip=%s, nameserver=%s, privately_run=%s
        WHERE id=%s
    """
    cursor.execute(update, (ip, ns_name, privately_run, _id))
    db.commit()

print("✅ Done processing all domains.")
cursor.close()
db.close()
