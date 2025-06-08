#!/usr/bin/env python3
"""
DNS Resolver Gini Coefficient Calculator

This script calculates Gini coefficients for DNS resolver distributions across:
- /8 address spaces (Class A networks)
- /16 address spaces (Class B networks)
- AS (Autonomous System) ownership

Requires: pip install mysql-connector-python pandas numpy matplotlib
"""

import mysql.connector
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
import sys
from typing import List, Tuple, Dict

class DNSGiniCalculator:
    def __init__(self, host='localhost', user='root', password='', database='dns_db'):
        """Initialize database connection"""
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
        self.connection = None

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            print(f"✓ Connected to MySQL database: {self.config['database']}")
        except mysql.connector.Error as err:
            print(f"✗ Database connection failed: {err}")
            sys.exit(1)

    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✓ Database connection closed")

    def calculate_gini(self, values: List[int]) -> float:
        """
        Calculate Gini coefficient for a list of values

        Args:
            values: List of counts/values

        Returns:
            Gini coefficient (0 = perfect equality, 1 = maximum inequality)
        """
        if not values or len(values) == 0:
            return 0.0

        # Remove zeros and sort
        values = [v for v in values if v > 0]
        if len(values) <= 1:
            return 0.0

        values = sorted(values)
        n = len(values)
        total = sum(values)

        if total == 0:
            return 0.0

        # Calculate Gini using the standard formula
        weighted_sum = sum((i + 1) * value for i, value in enumerate(values))
        gini = (2 * weighted_sum) / (n * total) - (n + 1) / n

        return max(0.0, min(1.0, gini))  # Clamp between 0 and 1

    def get_resolver_data(self) -> pd.DataFrame:
        """Fetch all DNS resolver data from database"""
        query = """
        SELECT ip, asn, as_name
        FROM dns_resolvers
        WHERE ip IS NOT NULL AND ip != ''
        """

        try:
            df = pd.read_sql(query, self.connection)
            print(f"✓ Loaded {len(df)} DNS resolver records")
            return df
        except Exception as e:
            print(f"✗ Error fetching resolver data: {e}")
            return pd.DataFrame()

    def extract_address_space(self, ip: str, prefix_length: int) -> str:
        """Extract /8 or /16 address space from IP"""
        try:
            octets = ip.split('.')
            if len(octets) < 4:
                return None

            if prefix_length == 8:
                return f"{octets[0]}.0.0.0/8"
            elif prefix_length == 16:
                return f"{octets[0]}.{octets[1]}.0.0/16"
            else:
                return None
        except:
            return None

    def analyze_address_space_distribution(self, df: pd.DataFrame, prefix_length: int) -> Tuple[float, Dict]:
        """Analyze distribution across /8 or /16 address spaces"""
        print(f"\nAnalyzing /{prefix_length} address space distribution...")

        # Extract address spaces
        df[f'addr_space_{prefix_length}'] = df['ip'].apply(
            lambda x: self.extract_address_space(x, prefix_length)
        )

        # Remove invalid entries
        valid_df = df[df[f'addr_space_{prefix_length}'].notna()]
        print(f"✓ {len(valid_df)} valid IP addresses for /{prefix_length} analysis")

        # Count resolvers per address space
        distribution = valid_df[f'addr_space_{prefix_length}'].value_counts()

        # Calculate Gini coefficient
        gini = self.calculate_gini(distribution.values.tolist())

        # Create summary statistics
        stats = {
            'total_resolvers': len(valid_df),
            'unique_address_spaces': len(distribution),
            'gini_coefficient': gini,
            'top_5_spaces': distribution.head(5).to_dict(),
            'min_resolvers': distribution.min(),
            'max_resolvers': distribution.max(),
            'mean_resolvers': distribution.mean(),
            'median_resolvers': distribution.median()
        }

        return gini, stats

    def analyze_as_distribution(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Analyze distribution across Autonomous Systems"""
        print("\nAnalyzing AS distribution...")

        # Filter valid ASN entries
        valid_df = df[df['asn'].notna() & (df['asn'] != '')]
        print(f"✓ {len(valid_df)} resolvers with valid ASN data")

        if len(valid_df) == 0:
            return 0.0, {'error': 'No valid ASN data found'}

        # Count resolvers per AS
        as_distribution = valid_df['asn'].value_counts()

        # Calculate Gini coefficient
        gini = self.calculate_gini(as_distribution.values.tolist())

        # Get top AS names
        top_as_details = []
        for asn in as_distribution.head(5).index:
            as_name = valid_df[valid_df['asn'] == asn]['as_name'].iloc[0]
            resolver_count = as_distribution[asn]
            top_as_details.append({
                'asn': asn,
                'as_name': as_name,
                'resolver_count': resolver_count,
                'percentage': (resolver_count / len(valid_df)) * 100
            })

        stats = {
            'total_resolvers': len(valid_df),
            'unique_as': len(as_distribution),
            'gini_coefficient': gini,
            'top_5_as': top_as_details,
            'min_resolvers': as_distribution.min(),
            'max_resolvers': as_distribution.max(),
            'mean_resolvers': as_distribution.mean(),
            'median_resolvers': as_distribution.median()
        }

        return gini, stats

    def plot_distributions(self, df: pd.DataFrame, save_plots: bool = True):
        """Create visualizations of the distributions"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('DNS Resolver Distribution Analysis', fontsize=16)

        # /8 distribution
        df['addr_space_8'] = df['ip'].apply(lambda x: self.extract_address_space(x, 8))
        dist_8 = df[df['addr_space_8'].notna()]['addr_space_8'].value_counts()

        axes[0, 0].bar(range(len(dist_8.head(20))), dist_8.head(20).values)
        axes[0, 0].set_title(f'/8 Address Space Distribution (Top 20)\nGini: {self.calculate_gini(dist_8.values.tolist()):.3f}')
        axes[0, 0].set_xlabel('Address Space Rank')
        axes[0, 0].set_ylabel('Resolver Count')

        # /16 distribution
        df['addr_space_16'] = df['ip'].apply(lambda x: self.extract_address_space(x, 16))
        dist_16 = df[df['addr_space_16'].notna()]['addr_space_16'].value_counts()

        axes[0, 1].bar(range(len(dist_16.head(20))), dist_16.head(20).values)
        axes[0, 1].set_title(f'/16 Address Space Distribution (Top 20)\nGini: {self.calculate_gini(dist_16.values.tolist()):.3f}')
        axes[0, 1].set_xlabel('Address Space Rank')
        axes[0, 1].set_ylabel('Resolver Count')

        # AS distribution
        valid_as_df = df[df['asn'].notna() & (df['asn'] != '')]
        if len(valid_as_df) > 0:
            as_dist = valid_as_df['asn'].value_counts()

            axes[1, 0].bar(range(len(as_dist.head(20))), as_dist.head(20).values)
            axes[1, 0].set_title(f'AS Distribution (Top 20)\nGini: {self.calculate_gini(as_dist.values.tolist()):.3f}')
            axes[1, 0].set_xlabel('AS Rank')
            axes[1, 0].set_ylabel('Resolver Count')

        # Lorenz curve for /8 distribution
        sorted_values = sorted(dist_8.values)
        cumsum = np.cumsum(sorted_values)
        cumsum_norm = cumsum / cumsum[-1]
        x = np.arange(1, len(sorted_values) + 1) / len(sorted_values)

        axes[1, 1].plot(x, cumsum_norm, 'b-', label='Lorenz Curve (/8)')
        axes[1, 1].plot([0, 1], [0, 1], 'r--', label='Perfect Equality')
        axes[1, 1].set_title('Lorenz Curve for /8 Distribution')
        axes[1, 1].set_xlabel('Cumulative Share of Address Spaces')
        axes[1, 1].set_ylabel('Cumulative Share of Resolvers')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        if save_plots:
            plt.savefig('dns_resolver_gini_analysis.png', dpi=300, bbox_inches='tight')
            print("✓ Plots saved as 'dns_resolver_gini_analysis.png'")

        plt.show()

    def print_results(self, results: Dict):
        """Print formatted results"""
        print("\n" + "="*80)
        print("DNS RESOLVER GINI COEFFICIENT ANALYSIS")
        print("="*80)

        for analysis_type, (gini, stats) in results.items():
            print(f"\n📊 {analysis_type.upper()} ANALYSIS")
            print("-" * 50)

            if 'error' in stats:
                print(f"❌ {stats['error']}")
                continue

            print(f"Gini Coefficient: {gini:.4f}")
            print(f"Total Resolvers: {stats['total_resolvers']:,}")
            print(f"Unique Entities: {stats['unique_entities' if 'unique_entities' in stats else 'unique_address_spaces' if 'unique_address_spaces' in stats else 'unique_as']:,}")
            print(f"Min Resolvers per Entity: {stats['min_resolvers']}")
            print(f"Max Resolvers per Entity: {stats['max_resolvers']:,}")
            print(f"Mean Resolvers per Entity: {stats['mean_resolvers']:.1f}")
            print(f"Median Resolvers per Entity: {stats['median_resolvers']:.1f}")

            # Interpretation
            if gini < 0.3:
                interpretation = "Low inequality - relatively equal distribution"
            elif gini < 0.5:
                interpretation = "Moderate inequality - some concentration"
            elif gini < 0.7:
                interpretation = "High inequality - significant concentration"
            else:
                interpretation = "Very high inequality - extreme concentration"

            print(f"Interpretation: {interpretation}")

            # Top entities
            if analysis_type == "AS":
                print("\nTop 5 Autonomous Systems:")
                for i, as_info in enumerate(stats['top_5_as'], 1):
                    print(f"  {i}. {as_info['asn']} ({as_info['as_name'][:50]}...): "
                          f"{as_info['resolver_count']:,} resolvers ({as_info['percentage']:.1f}%)")
            else:
                print(f"\nTop 5 {analysis_type} Address Spaces:")
                for space, count in list(stats['top_5_spaces'].items())[:5]:
                    percentage = (count / stats['total_resolvers']) * 100
                    print(f"  {space}: {count:,} resolvers ({percentage:.1f}%)")

    def run_analysis(self, create_plots: bool = True):
        """Run complete Gini coefficient analysis"""
        print("🔍 Starting DNS Resolver Gini Coefficient Analysis...")

        # Connect to database
        self.connect()

        try:
            # Get data
            df = self.get_resolver_data()
            if df.empty:
                print("❌ No data available for analysis")
                return

            results = {}

            # Analyze /8 distribution
            gini_8, stats_8 = self.analyze_address_space_distribution(df, 8)
            results["/8 Address Space"] = (gini_8, stats_8)

            # Analyze /16 distribution
            gini_16, stats_16 = self.analyze_address_space_distribution(df, 16)
            results["/16 Address Space"] = (gini_16, stats_16)

            # Analyze AS distribution
            gini_as, stats_as = self.analyze_as_distribution(df)
            results["AS"] = (gini_as, stats_as)

            # Print results
            self.print_results(results)

            # Create visualizations
            if create_plots:
                try:
                    self.plot_distributions(df)
                except Exception as e:
                    print(f"⚠️  Could not create plots: {e}")

        except Exception as e:
            print(f"❌ Analysis failed: {e}")

        finally:
            self.disconnect()

def main():
    """Main function with configuration"""
    # Database configuration - modify these values for your setup
    DB_CONFIG = {
        'host': 'localhost',
        'user': 'pink',
        'password': 'passw',  # Add your password here
        'database': 'dns_servers'  # Replace with your database name
    }

    print("DNS Resolver Gini Coefficient Calculator")
    print("="*50)

    # Get database credentials from user if not configured
    if not DB_CONFIG['password'] or DB_CONFIG['database'] == 'your_database_name':
        print("Please configure database connection:")
        DB_CONFIG['host'] = input(f"Host [{DB_CONFIG['host']}]: ") or DB_CONFIG['host']
        DB_CONFIG['user'] = input(f"User [{DB_CONFIG['user']}]: ") or DB_CONFIG['user']
        DB_CONFIG['password'] = input("Password: ")
        DB_CONFIG['database'] = input("Database name: ")

    # Run analysis
    calculator = DNSGiniCalculator(**DB_CONFIG)
    calculator.run_analysis(create_plots=True)

if __name__ == "__main__":
    main()
