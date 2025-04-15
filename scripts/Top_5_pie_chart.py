import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('rose-pine')

# Load the uploaded CSV file
file_path = '~/data/db_exports/dns_owners.csv'
df = pd.read_csv(file_path, delimiter='\t')
# Convert COUNT to integer
df['COUNT'] = df['COUNT'].astype(int)

# Group by owner and sum counts (in case there are duplicates)
geo_counts = df.groupby('owner')['COUNT'].sum().sort_values(ascending=False)

# Split into top 5 and "Other"
top5 = geo_counts.head(5)
other = geo_counts.iloc[5:].sum()
top5['Other'] = other

# Create pie chart
plt.figure(figsize=(8, 8))
top5.plot.pie(autopct='%1.1f%%', startangle=140, ylabel='', title='Top 5 Organizations by DNS Server Count')
plt.tight_layout()
plt.show()

# Save as SVG
plt.savefig("/home/ubuntu/data/dns_servers_by_owner.svg", format="svg")
