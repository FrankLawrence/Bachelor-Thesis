#!/usr/bin/env python3
import matplotlib.pyplot as plt
from hilbertcurve.hilbertcurve import HilbertCurve
import ipaddress
# plt.style.use('rose-pine')

# Parameters for Hilbert curve (IPv4 = 32 bits → level=16, dim=2)
p = 16  # iterations
n = 2   # dimensions
hilbert_curve = HilbertCurve(p, n)

# Read IPs
ips = []
with open('/home/ubuntu/bachelor-thesis/data/rrsig_ips_uniq.txt') as f:
    for line in f:
        ip = line.strip()
        try:
            ip_int = int(ipaddress.IPv4Address(ip))
            point = hilbert_curve.coordinates_from_distance(ip_int)
            ips.append(point)
        except:
            continue

# Extract x, y coords
x = [pt[0] for pt in ips]
y = [pt[1] for pt in ips]

# Plot
plt.figure(figsize=(10, 10))
plt.scatter(x, y, s=0.5, alpha=0.5)
plt.title('Hilbert Map of IPs (RRSIG responses)')
plt.axis('off')
plt.show()

plt.savefig('data/plots/hilbert_map_rrsig.png', bbox_inches='tight', pad_inches=0.1)
plt.close()  # Close to free memory
