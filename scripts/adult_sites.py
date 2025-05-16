import mysql.connector
import requests
import time

# === CONFIGURATION ===
DB_CONFIG = {
    "host": "localhost",
    "user": "webuser",
    "password": "WcaoN54HYOi4rBA8x8kwprlaprysqZoU",
    "database": "dns_servers"
}

API_KEY = "7c2fc63289mshde3b6f96961e241p1611f8jsn358c5cd920d7"
API_URL = "https://similarsites1.p.rapidapi.com/v1/find-similar/"
HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "similarsites1.p.rapidapi.com"
}


# === Get next unqueried domain ===
def get_unqueried_domain(cursor):
    cursor.execute("SELECT domain FROM adult_sites WHERE queried = 0 LIMIT 1")
    row = cursor.fetchone()
    return row[0] if row else None


# === Mark domain as queried ===
def mark_queried(cursor, domain):
    cursor.execute("UPDATE adult_sites SET queried = 1 WHERE domain = %s", (domain,))


# === Insert new domains ===
def insert_domains(cursor, domains):
    for domain in domains:
        try:
            cursor.execute("INSERT IGNORE INTO adult_sites (domain) VALUES (%s)", (domain,))
        except Exception as e:
            print(f"Insert error for {domain}: {e}")


# === Query SimilarSites API ===
def fetch_similar_sites(domain):
    try:
        querystring = {"domain": domain}
        response = requests.get(API_URL, params=querystring, headers=HEADERS)
        if response.status_code == 200:
            json_data = response.json()
            return [site["Site"] for site in json_data.get("SimilarSites", [])]
        else:
            print(f"API error for {domain}: {response.status_code}")
    except Exception as e:
        print(f"Error fetching similar sites: {e}")
    return []


# === MAIN LOOP ===
def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    iteration = 0
    MAX_ITERATIONS = 5000

    while iteration < MAX_ITERATIONS:
        domain = get_unqueried_domain(cursor)
        if not domain:
            print("✅ No more unqueried domains.")
            break

        print(f"🔍 Querying similar sites for: {domain}")
        similar_sites = fetch_similar_sites(domain)
        if similar_sites:
            print(f"➕ Found {len(similar_sites)} similar sites.")
            insert_domains(cursor, similar_sites)
        else:
            print("⚠️ No similar sites found or API error.")

        mark_queried(cursor, domain)
        conn.commit()
        iteration += 1
        time.sleep(1.5)  # Prevent rapid API hitting

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
