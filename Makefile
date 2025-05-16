# --- CONFIGURATION ---
DB_USER = root
DB_NAME = dns_servers
TABLE_NAME = dns_servers
SQL_DUMP_FILE = backup.sql
INPUT_FILE = ~/bachelor-thesis/data/dns_servers.txt
OUTPUT_FILE = ~/bachelor-thesis/data/output.txt
SCAN_SCRIPT = ~/bachelor-thesis/scripts/dns_scan.sh
EXPORT_DIR = ~/bachelor-thesis/data/db_exports

# --- COMMANDS ---

.PHONY: help backup import insert export scan owners asns

help:
	@echo "Available targets:"
	@echo "  make backup        - Dump the current MySQL database to $(SQL_DUMP_FILE)"
	@echo "  make import        - Import database from $(SQL_DUMP_FILE)"
	@echo "  make insert        - Insert IPs from $(INPUT_FILE) into the database (IP only)"
	@echo "  make export        - Run a MySQL command and save output to $(OUTPUT_FILE)"
	@echo "  make scan          - Run full scan script on all IPs from the database"
	@echo "  make owners        - Export table of all owners of dns servers and how many they own"
	@echo "  make asns          - Export table of all asns of dns servers and how many they 'own'"

# 1. Backup the MySQL database to file
backup:
	mysqldump -u$(DB_USER) $(DB_NAME) > $(SQL_DUMP_FILE)

# 2. Import database from backup file
import:
	sudo mysql < $(SQL_DUMP_FILE)
	# sudo mysql -u$(DB_USER) -e "source $(SQL_DUMP_FILE)"

# 3. Insert list of DNS servers into the database (IP only)
insert:
	sudo mysql -u$(DB_USER) -D $(DB_NAME) -e "CREATE TABLE IF NOT EXISTS $(TABLE_NAME) (id INT AUTO_INCREMENT PRIMARY KEY, ip VARCHAR(45));"
	while read -r ip; do \
		sudo mysql -u$(DB_USER) -D $(DB_NAME) -e "INSERT INTO $(TABLE_NAME) (ip) VALUES ('$$ip');"; \
	done < $(INPUT_FILE)

# 4. Run a SQL command and write result to a file
export:
	mysql -u$(DB_USER) -D $(DB_NAME) -e "SELECT * FROM $(TABLE_NAME);" > $(OUTPUT_FILE)

# 5. Run scan script on all DNS servers in the database
scan:
	bash $(SCAN_SCRIPT)

# Export DNSSEC-supporting servers grouped by owner
owners:
	@mkdir -p $(EXPORT_DIR)
	mysql -u$(DB_USER) -e \
	"SELECT COUNT(*) AS count, owner FROM $(DB_NAME).$(TABLE_NAME) WHERE dnssec_support=1 GROUP BY owner ORDER BY count DESC;" \
	> $(EXPORT_DIR)/dnssec_owners_count.csv

# Export DNSSEC-supporting servers grouped by ASN
asns:
	@mkdir -p $(EXPORT_DIR)
	mysql -u$(DB_USER) -e \
	"SELECT COUNT(*) AS count, asn FROM $(DB_NAME).$(TABLE_NAME) WHERE dnssec_support=1 GROUP BY asn ORDER BY count DESC;" \
	> $(EXPORT_DIR)/dnssec_asn_count.csv

# --- RESET DATABASE ENTRIES ---
reset_db:
	sudo mysql -u $(DB_USER) -D $(DB_NAME) -e "DELETE FROM $(TABLE_NAME);"
