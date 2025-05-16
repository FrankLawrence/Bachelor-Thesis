import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

# Use your preferred style
plt.style.use('rose-pine')

# Database connection setup (replace with your actual credentials)
db_user = 'pink'
db_password = 'passw'
db_host = 'localhost'
db_port = '3306'
db_name = 'dns_servers'

# Create SQLAlchemy engine
engine = create_engine(f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')

# Query to get owner counts
query = """
SELECT owner, COUNT(*) as COUNT
FROM dns_resolvers
WHERE owner IS NOT NULL AND owner != ''
GROUP BY owner
"""

# Load data into DataFrame
df = pd.read_sql(query, engine)

# Convert COUNT to integer
df['COUNT'] = df['COUNT'].astype(int)

# Group by owner and sort (redundant after GROUP BY, but ensures ordering)
geo_counts = df.set_index('owner')['COUNT'].sort_values(ascending=False)

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
plt.savefig("/home/ubuntu/bachelor-thesis/data/dns_servers_by_owner_new.svg", format="svg")
