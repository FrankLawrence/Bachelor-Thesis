#!/usr/bin/env python3
"""
DNSSEC-enabled DNS Resolver Gini Calculator
Compares distribution between all resolvers vs DNSSEC-enabled resolvers
"""

import mysql.connector
from collections import Counter

def calculate_gini(values):
    """Calculate Gini coefficient for a list of values"""
    values = sorted([v for v in values if v > 0])
    if len(values) <= 1:
        return 0.0

    n = len(values)
    total = sum(values)
    weighted_sum = sum((i + 1) * value for i, value in enumerate(values))

    return (2 * weighted_sum) / (n * total) - (n + 1) / n

def analyze_resolvers(cursor, dnssec_filter=""):
    """Analyze resolver distribution with optional DNSSEC filter"""
    query = f"SELECT ip, asn, as_name FROM dns_resolvers WHERE ip IS NOT NULL {dnssec_filter}"
    cursor.execute(query)
    results = cursor.fetchall()

    ips = [row[0] for row in results]
    asns = [row[1] for row in results if row[1]]
    as_names = {row[1]: row[2] for row in results if row[1] and row[2]}

    # /8 analysis
    class_a_blocks = [ip.split('.')[0] for ip in ips if '.' in ip]
    block_counts_8 = Counter(class_a_blocks)
    gini_8 = calculate_gini(list(block_counts_8.values()))

    # /16 analysis
    class_b_blocks = ['.'.join(ip.split('.')[:2]) for ip in ips if '.' in ip and len(ip.split('.')) >= 2]
    block_counts_16 = Counter(class_b_blocks)
    gini_16 = calculate_gini(list(block_counts_16.values()))

    # AS analysis
    as_counts = Counter(asns)
    gini_as = calculate_gini(list(as_counts.values()))

    return {
        'total_resolvers': len(ips),
        'gini_8': gini_8,
        'gini_16': gini_16,
        'gini_as': gini_as,
        'unique_8_blocks': len(block_counts_8),
        'unique_16_blocks': len(block_counts_16),
        'unique_as': len(as_counts),
        'top_8_blocks': block_counts_8.most_common(5),
        'top_16_blocks': block_counts_16.most_common(5),
        'top_as': [(asn, count, as_names.get(asn, 'Unknown')) for asn, count in as_counts.most_common(5)]
    }

def print_comparison(all_results, dnssec_results):
    """Print comparison between all resolvers and DNSSEC resolvers"""
    print("="*80)
    print("DNS RESOLVER DISTRIBUTION: ALL vs DNSSEC-ENABLED")
    print("="*80)

    # Summary comparison
    print(f"\n📊 SUMMARY COMPARISON")
    print("-" * 50)
    print(f"{'Metric':<25} {'All Resolvers':<15} {'DNSSEC Only':<15} {'Difference':<10}")
    print("-" * 65)
    print(f"{'Total Resolvers':<25} {all_results['total_resolvers']:>14,} {dnssec_results['total_resolvers']:>14,} {dnssec_results['total_resolvers']/all_results['total_resolvers']*100:>9.1f}%")
    print(f"{'Gini /8':<25} {all_results['gini_8']:>14.4f} {dnssec_results['gini_8']:>14.4f} {dnssec_results['gini_8']-all_results['gini_8']:>+9.4f}")
    print(f"{'Gini /16':<25} {all_results['gini_16']:>14.4f} {dnssec_results['gini_16']:>14.4f} {dnssec_results['gini_16']-all_results['gini_16']:>+9.4f}")
    print(f"{'Gini AS':<25} {all_results['gini_as']:>14.4f} {dnssec_results['gini_as']:>14.4f} {dnssec_results['gini_as']-all_results['gini_as']:>+9.4f}")
    print(f"{'Unique /8 blocks':<25} {all_results['unique_8_blocks']:>14,} {dnssec_results['unique_8_blocks']:>14,}")
    print(f"{'Unique /16 blocks':<25} {all_results['unique_16_blocks']:>14,} {dnssec_results['unique_16_blocks']:>14,}")
    print(f"{'Unique AS':<25} {all_results['unique_as']:>14,} {dnssec_results['unique_as']:>14,}")

    # Detailed analysis
    for analysis_type, key in [("/8 Address Spaces", "top_8_blocks"), ("/16 Address Spaces", "top_16_blocks"), ("Autonomous Systems", "top_as")]:
        print(f"\n📈 TOP 5 {analysis_type.upper()}")
        print("-" * 50)
        print(f"{'Rank':<5} {'Entity':<25} {'All Count':<12} {'DNSSEC Count':<15} {'DNSSEC %':<10}")
        print("-" * 67)

        all_top = dict(all_results[key][:5]) if key != "top_as" else {item[0]: (item[1], item[2]) for item in all_results[key][:5]}
        dnssec_top = dict(dnssec_results[key][:5]) if key != "top_as" else {item[0]: (item[1], item[2]) for item in dnssec_results[key][:5]}

        # Get union of top entities from both datasets
        all_entities = set(all_top.keys()) | set(dnssec_top.keys())
        sorted_entities = sorted(all_entities, key=lambda x: all_top.get(x, (0, ''))[0] if key == "top_as" else all_top.get(x, 0), reverse=True)

        for i, entity in enumerate(sorted_entities[:5], 1):
            if key == "top_as":
                all_count = all_top.get(entity, (0, 'Unknown'))[0]
                dnssec_count = dnssec_top.get(entity, (0, 'Unknown'))[0]
                entity_name = f"{entity} ({all_top.get(entity, ('', 'Unknown'))[1][:20]})"
            else:
                all_count = all_top.get(entity, 0)
                dnssec_count = dnssec_top.get(entity, 0)
                entity_name = f"{entity}.x.x.x" if key == "top_8_blocks" else f"{entity}.x.x"

            dnssec_pct = (dnssec_count / all_count * 100) if all_count > 0 else 0
            print(f"{i:<5} {entity_name:<25} {all_count:>11,} {dnssec_count:>14,} {dnssec_pct:>9.1f}%")

def main():
    # Database config - update these
    config = {
        'host': 'localhost',
        'user': 'pink',
        'password': 'passw',
        'database': 'dns_servers'
    }

    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    print("🔍 Analyzing DNS resolver distributions...")

    # Analyze all resolvers
    print("Analyzing all DNS resolvers...")
    all_results = analyze_resolvers(cursor)

    # Analyze DNSSEC-enabled resolvers
    print("Analyzing DNSSEC-enabled resolvers...")
    dnssec_results = analyze_resolvers(cursor, "AND dnssec_support = 1")

    # Print comparison
    print_comparison(all_results, dnssec_results)

    # DNSSEC adoption insights
    dnssec_rate = dnssec_results['total_resolvers'] / all_results['total_resolvers'] * 100
    print(f"\n🔒 DNSSEC INSIGHTS")
    print("-" * 50)
    print(f"DNSSEC adoption rate: {dnssec_rate:.1f}% ({dnssec_results['total_resolvers']:,} of {all_results['total_resolvers']:,})")

    if dnssec_results['gini_as'] > all_results['gini_as']:
        print("DNSSEC resolvers are MORE concentrated by AS than general population")
    else:
        print("DNSSEC resolvers are LESS concentrated by AS than general population")

    conn.close()

if __name__ == "__main__":
    main()
