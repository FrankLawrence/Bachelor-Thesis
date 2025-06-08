import pandas as pd
import matplotlib.pyplot as plt
import pymysql

plt.style.use('rose-pine')

# MySQL Configuration
db_config = {
    'user': 'pink',
    'password': 'passw',
    'host': 'localhost',
    'database': 'dns_servers',
}

def create_plot(sql_query, title, x_label, y_label, output_path, plot_type='bar'):
    """
    Generates a bar plot or pie chart based on the SQL query provided.

    Args:
        sql_query (str): SQL query to execute.
        title (str): Title of the plot.
        x_label (str): Label for the x-axis (only for bar plots).
        y_label (str): Label for the y-axis (only for bar plots).
        output_path (str): Path to save the plot.
        plot_type (str): Type of plot to generate ('bar' or 'pie'). Defaults to 'bar'.
    """
    try:
        # Establish database connection
        cnx = pymysql.connect(**db_config)
        df = pd.read_sql(sql_query, cnx)
        cnx.close()
    except pymysql.MySQLError as err:
        print(f"Error connecting to MySQL: {err}")
        return

    # Clean and rename columns (if necessary)
    df.columns = [col.strip().lower() for col in df.columns]

    if plot_type == 'bar':
        if 'count' in df.columns and 'owner' in df.columns:
            df = df.rename(columns={"count": "count", "owner": "owner"})

            # Ensure 'count' is numeric
            df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)

            # Sort by count and get top N (e.g., top 10)
            N = 10
            top_n = df.sort_values("count", ascending=False).head(N)

            # Calculate total and percentage
            total_count = df["count"].sum()
            top_n["percentage"] = (top_n["count"] / total_count * 100).round(1)

            # Plot
            plt.figure(figsize=(10, 6))
            bars = plt.bar(top_n["owner"], top_n["count"], color="skyblue", edgecolor="black")

            # Add percentage labels above bars
            for bar, pct in zip(bars, top_n["percentage"]):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width() / 2, height + 0.5, f"{pct}%", ha='center', va='bottom', fontsize=9)

            # Labels and formatting
            plt.title(title)
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            # Save as SVG
            plt.savefig(output_path, format="svg")
            plt.close()  # Close the figure to free memory

        else:
            print("Required columns ('count' and 'owner') not found in the query result for bar plot.")

    elif plot_type == 'pie':
        if 'count' in df.columns and 'owner' in df.columns:
            df = df.rename(columns={"count": "count", "owner": "owner"})
            df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)

            # Group by owner and sort
            geo_counts = df.set_index('owner')['count'].sort_values(ascending=False)

            # Split into top 5 and "Other"
            top5 = geo_counts.head(5)
            other = geo_counts.iloc[5:].sum()
            top5['Other'] = other

            # Create pie chart
            plt.figure(figsize=(8, 8))
            top5.plot.pie(autopct='%1.1f%%', startangle=140, ylabel='', title=title)
            plt.tight_layout()

            # Save as SVG
            plt.savefig(output_path, format="svg")
            plt.close()  # Close the figure to free memory
        else:
             print("Required columns ('count' and 'owner') not found in the query result for pie chart.")
    else:
        print(f"Invalid plot_type: {plot_type}.  Must be 'bar' or 'pie'.")


def create_ip_histogram(db_config, output_path, title):
    """
    Generates a histogram of DNS resolvers based on the /8 IP address block.

    Args:
        db_config (dict): Database configuration.
        output_path (str): Path to save the plot.
        title (str): Title of the plot.
    """
    try:
        # Establish database connection
        cnx = pymysql.connect(**db_config)
        query = """
            SELECT
                SUBSTRING_INDEX(ip, '.', 1) AS ip_prefix,
                COUNT(*) AS count
            FROM dns_resolvers
            GROUP BY ip_prefix
        """
        df = pd.read_sql(query, cnx)
        cnx.close()

        # Ensure 'count' is numeric
        df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)

        # Convert IP prefix to numeric for sorting
        df['ip_prefix_numeric'] = pd.to_numeric(df['ip_prefix'], errors='coerce')
        df = df.sort_values('ip_prefix_numeric')

        # Plot
        plt.figure(figsize=(12, 6))
        plt.bar(df["ip_prefix"], df["count"], color="skyblue", edgecolor="black")

        # Labels and formatting
        plt.title(title)
        plt.xlabel("IP Address /8 Prefix")
        plt.ylabel("Number of DNS Resolvers")
        plt.xticks(rotation=45, ha='right')

        # Only show every 4th label
        for n, label in enumerate(plt.gca().xaxis.get_ticklabels()):
            if n % 5 != 0:
                label.set_visible(False)

        plt.tight_layout()

        # Save as SVG
        plt.savefig(output_path, format="svg")
        plt.close()  # Close the figure to free memory

    except pymysql.MySQLError as err:
        print(f"Error connecting to MySQL: {err}")


create_ip_histogram(
    db_config=db_config,
    output_path="/home/ubuntu/bachelor-thesis/data/plots/ip_histogram.svg",
    title="Distribution of DNS Resolvers by /8 IP Address Block"
)

sql_query_1 = """
SELECT owner, COUNT(*) AS count
FROM dns_resolvers
GROUP BY owner
ORDER BY COUNT(*) DESC;
"""
create_plot(
    sql_query=sql_query_1,
    title="Top Organizations by Number of DNS Resolvers",
    x_label="Organization",
    y_label="Number of DNS Resolvers",
    output_path="/home/ubuntu/bachelor-thesis/data/plots/top10_dns_resolver_by_owner.svg",
    plot_type='bar'
)

sql_query_2 = """
SELECT owner, COUNT(*) AS count
FROM dns_resolvers
WHERE owner IS NOT NULL AND owner != ''
GROUP BY owner
"""
create_plot(
    sql_query=sql_query_2,
    title="Top 5 Organizations by DNS Resolver Count",
    x_label="",  # Not used for pie charts
    y_label="",  # Not used for pie charts
    output_path="/home/ubuntu/bachelor-thesis/data/plots/dns_resolvers_by_owner.svg",
    plot_type='pie'
)

sql_query_7 = """
SELECT owner, COUNT(*) AS count
FROM dns_resolvers
WHERE owner IS NOT NULL AND owner != '' AND dnssec_support is True
GROUP BY owner
"""
create_plot(
    sql_query=sql_query_7,
    title="Top 5 Organizations by DNSSEC Resolver Count",
    x_label="",  # Not used for pie charts
    y_label="",  # Not used for pie charts
    output_path="/home/ubuntu/bachelor-thesis/data/plots/dnssec_resolvers_by_owner.svg",
    plot_type='pie'
)

sql_query_3 = """
SELECT
   COUNT(*) AS count,
   geo_location AS COUNTRY
FROM dns_resolvers
GROUP BY geo_location
"""
create_plot(
    sql_query=sql_query_3,
    title="Top 5 Countires by DNS Resolver Count",
    x_label="",
    y_label="",
    output_path="/home/ubuntu/bachelor-thesis/data/plots/dns_resolvers_by_country.svg",
    plot_type='pie'
)

sql_query_6 = """
SELECT
   COUNT(*) AS count,
   geo_location AS COUNTRY
FROM dns_resolvers
WHERE dnssec_support is True
GROUP BY geo_location
"""
create_plot(
    sql_query=sql_query_6,
    title="Top 5 Countires by DNSSEC Resolver Count",
    x_label="",
    y_label="",
    output_path="/home/ubuntu/bachelor-thesis/data/plots/dnssec_resolvers_by_country.svg",
    plot_type='pie'
)

sql_query_4 = """
SELECT
    COUNT(*) AS `COUNT`,
    a.as_name AS `name`
FROM dns_resolvers AS d
JOIN as_ip_ranges AS a
    ON INET_ATON(d.ip) BETWEEN INET_ATON(a.start_ip) AND INET_ATON(a.end_ip)
WHERE d.as_name = a.as_name
GROUP BY a.as_name
ORDER BY COUNT(*) DESC
"""
create_plot(
    sql_query=sql_query_4,
    title="Top 5 AS by DNS Server Count",
    x_label="",
    y_label="",
    output_path="/home/ubuntu/bachelor-thesis/data/plots/dns_resolvers_by_as.svg",
    plot_type='pie'
)

# DNSSEC
sql_query_5 = """
SELECT
    COUNT(*) AS `COUNT`,
    a.as_name AS `name`
FROM dns_resolvers AS d
JOIN as_ip_ranges AS a
    ON INET_ATON(d.ip) BETWEEN INET_ATON(a.start_ip) AND INET_ATON(a.end_ip)
WHERE d.as_name = a.as_name AND d.dnssec_support IS True
GROUP BY a.as_name
ORDER BY COUNT(*) DESC
"""
create_plot(
    sql_query=sql_query_5,
    title="Top 5 AS by DNSSEC Server Count",
    x_label="",
    y_label="",
    output_path="/home/ubuntu/bachelor-thesis/data/plots/dnssec_resolvers_by_as.svg",
    plot_type='pie'
)
