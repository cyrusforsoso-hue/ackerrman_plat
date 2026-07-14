#!/usr/bin/env python3
"""Generate Gazebo SDF model from path.csv for visualization in Gazebo.

Usage:
  python3 generate_path_sdf.py --input /path/to/path.csv --output /path/to/output.sdf
"""
import argparse
import csv
import math
import sys


def generate(input_csv, output_sdf):
    points = []
    with open(input_csv, 'r') as f:
        for row in csv.reader(f):
            if not row or row[0].startswith('#'):
                continue
            if len(row) < 7:
                continue
            x, y, z = float(row[0]), float(row[1]), float(row[2])
            points.append((x, y, z))

    if len(points) < 2:
        print(f'Error: need at least 2 points, got {len(points)}')
        sys.exit(1)

    radius = 0.04
    line_width = 0.02

    visuals_xml = ''
    for i, (x, y, z) in enumerate(points):
        visuals_xml += f'''
            <visual name="pt_{i}">
              <pose>{x} {y} {z} 0 0 0</pose>
              <geometry><sphere><radius>{radius}</radius></sphere></geometry>
              <material><ambient>0 1 0 1</ambient></material>
            </visual>'''

    for i in range(len(points) - 1):
        p1, p2 = points[i], points[i + 1]
        cx = (p1[0] + p2[0]) / 2.0
        cy = (p1[1] + p2[1]) / 2.0
        cz = (p1[2] + p2[2]) / 2.0
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]
        length = math.hypot(dx, dy, dz)
        if length < 1e-6:
            continue
        yaw = math.atan2(dy, dx)
        pitch = math.atan2(-dz, math.hypot(dx, dy))
        visuals_xml += f'''
            <visual name="line_{i}">
              <pose>{cx} {cy} {cz} 0 {pitch} {yaw}</pose>
              <geometry><box><size>{length} {line_width} {line_width * 0.5}</size></box></geometry>
              <material><ambient>0 0.8 0 1</ambient></material>
            </visual>'''

    sdf = f'''<?xml version="1.0"?>
<sdf version="1.6">
  <model name="reference_path">
    <static>true</static>
    <link name="path_link">
      {visuals_xml}
    </link>
  </model>
</sdf>'''

    with open(output_sdf, 'w') as f:
        f.write(sdf)

    print(f'Generated {output_sdf}: {len(points)} waypoints')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Path to input CSV file')
    parser.add_argument('--output', required=True, help='Path to output SDF file')
    args = parser.parse_args()
    generate(args.input, args.output)
