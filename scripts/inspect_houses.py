#!/usr/bin/env python3
"""Inspect the first row of the houses backup to understand its structure."""
with open('/tmp/bck_houses_immat', 'r') as f:
    line = f.readline().strip()

cols = line.split('\t')
print(f"Total columns: {len(cols)}")
print("---")
for i, c in enumerate(cols):
    print(f"col{i}: [{c[:60]}]")
