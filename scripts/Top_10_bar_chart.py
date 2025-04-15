import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('rose-pine')

# Load the CSV
df = pd.read_csv("~/bachelor-thesis/data/db_exports/dnssec_owners.csv", sep="\t")

# Clean and rename columns
df.columns = [col.strip().lower() for col in df.columns]
df = df.rename(columns={"count": "count", "owner": "owner"})

# Ensure 'count' is numeric
df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)

# Sort by count and get top 10
top10 = df.sort_values("count", ascending=False).head(10)

# Calculate total and percentage
total_count = df["count"].sum()
top10["percentage"] = (top10["count"] / total_count * 100).round(1)

# Plot
plt.figure(figsize=(10, 6))
bars = plt.bar(top10["owner"], top10["count"], color="skyblue", edgecolor="black")

# Add percentage labels above bars
for bar, pct in zip(bars, top10["percentage"]):
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width() / 2, height + 0.5, f"{pct}%", ha='center', va='bottom', fontsize=9)

# Labels and formatting
plt.title("Top 10 Organizations by Number of DNSSEC Servers")
plt.xlabel("Organization")
plt.ylabel("Number of DNSSEC Servers")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()

# Save as SVG
plt.savefig("/home/ubuntu/bachelor-thesis/data/plots/top10_dnssec_servers_by_org.svg", format="svg")
