"""Locate candidate axis-aligned cylindrical patches in a closed STL mesh."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

import numpy as np

from faceted_step import parse_triangles


UNITS = {'mm': 1, 'cm': 10, 'm': 1000, 'in': 25.4, 'ft': 304.8}


def fit_circle(points):
    origin = points.mean(axis=0)
    shifted = points - origin
    matrix = np.c_[2 * shifted, np.ones(len(shifted))]
    xy, _, rank, _ = np.linalg.lstsq(matrix, np.sum(shifted**2, axis=1), rcond=None)
    if rank != 3:
        return None
    center = xy[:2] + origin
    radius = math.sqrt(xy[2] + xy[:2] @ xy[:2])
    return center, radius


def mesh_geometry(path, scale):
    source = np.array(list(parse_triangles(path.read_bytes())), dtype=np.float64) * scale
    if source.size == 0 or not np.isfinite(source).all():
        raise ValueError('STL has no triangles or contains nonfinite coordinates')
    vertices, indices = np.unique(source.reshape(-1, 3).round(8), axis=0, return_inverse=True)
    triangles = indices.reshape(-1, 3)
    corners = vertices[triangles]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    areas = np.linalg.norm(normals, axis=1)
    if np.any(areas == 0):
        raise ValueError('STL contains a degenerate triangle')
    owners = defaultdict(list)
    for face, (a, b, c) in enumerate(triangles):
        for start, end in ((a, b), (b, c), (c, a)):
            owners[min(start, end), max(start, end)].append((face, start < end))
    if any(len(pair) != 2 or pair[0][1] == pair[1][1] for pair in owners.values()):
        raise ValueError('STL must be a closed and consistently oriented mesh')
    adjacency = defaultdict(set)
    pairs = set()
    for ((left, _), (right, _)) in owners.values():
        adjacency[left].add(right)
        adjacency[right].add(left)
        pairs.add((min(left, right), max(left, right)))
    return vertices, triangles, normals / areas[:, None], adjacency, pairs


def section_points(points, tolerance):
    # Axial rows in a binary STL can have slightly different rounded coordinates.
    points = sorted(set(map(tuple, points)))
    unique = []
    for point in points:
        if all(math.dist(point, other) > tolerance for other in unique):
            unique.append(point)
    return np.array(unique)


def components(selected, adjacency):
    while selected:
        start = selected.pop()
        pending = [start]
        component = {start}
        while pending:
            found = adjacency[pending.pop()] & selected
            selected.difference_update(found)
            component.update(found)
            pending.extend(found)
        yield component


def probe(path, scale, tolerance):
    vertices, triangles, normals, adjacency, pairs = mesh_geometry(path, scale)
    candidates = []
    for axis in range(3):
        plane = np.delete(vertices, axis, axis=1)
        normal_mask = abs(normals[:, axis]) < 1e-3
        section_normals = np.delete(normals, axis, axis=1)
        section_centers = plane[triangles].mean(axis=1)
        seeds = {}
        for left, right in sorted(pairs):
            if not (normal_mask[left] and normal_mask[right]):
                continue
            if not 0.9 < normals[left] @ normals[right] < 0.9999:
                continue
            points = section_points(plane[triangles[[left, right]].ravel()], tolerance)
            if len(points) != 3:
                continue
            circle = fit_circle(points)
            if circle is None:
                continue
            center, radius = circle
            if radius < 10 * tolerance or radius > 10 * np.ptp(plane, axis=0).max():
                continue
            # Bin only to deduplicate seeds. Refitting uses the original coordinates.
            key = tuple(np.rint(np.r_[center, radius] / (10 * tolerance)))
            if key not in seeds:
                seeds[key] = (center, radius, set())
            seeds[key][2].update((left, right))
        accepted = []
        for center, radius, support in sorted(seeds.values(), key=lambda item: -len(item[2])):
            error = abs(np.linalg.norm(plane - center, axis=1) - radius)
            # Trim triangles can span different angular intervals at each end.
            # Check that their normals still point approximately radially and
            # reject caps and flat bridges whose vertices happen to be co-circular.
            radial = section_centers - center
            facing = abs(np.einsum('ij,ij->i', section_normals, radial))
            radial_mask = facing > 0.98 * np.linalg.norm(radial, axis=1)
            wide = radial_mask & np.all(error[triangles] <= 10 * tolerance, axis=1)
            tight = radial_mask & np.all(error[triangles] <= 3 * tolerance, axis=1)
            selections = (set(np.flatnonzero(wide)), set(np.flatnonzero(tight)))
            regions = (region for selection in selections for region in components(selection, adjacency))
            for region in regions:
                if len(region & support) < 2 or any(region <= old for old, _ in accepted):
                    continue
                faces = sorted(region)
                points = vertices[np.unique(triangles[faces])]
                cross_section = np.delete(points, axis, axis=1)
                fit = fit_circle(cross_section)
                if fit is None:
                    continue
                center_fit, radius_fit = fit
                offset = cross_section - center_fit
                error_fit = float(max(abs(np.linalg.norm(offset, axis=1) - radius_fit)))
                angles = np.sort(np.arctan2(offset[:, 1], offset[:, 0]))
                gaps = np.diff(np.r_[angles, angles[0] + 2 * np.pi])
                span = float(np.degrees(2 * np.pi - max(gaps)))
                if span < 20 or error_fit > tolerance:
                    continue
                accepted.append((region, {
                    'axis': 'XYZ'[axis],
                    'section_axes': ''.join(c for i, c in enumerate('XYZ') if i != axis),
                    'center_mm': center_fit.tolist(),
                    'radius_mm': radius_fit,
                    'max_vertex_residual_mm': error_fit,
                    'sampled_span_deg': span,
                    'bounds_mm': np.column_stack((points.min(axis=0), points.max(axis=0))).tolist(),
                    'source_triangle_indices_zero_based': [int(face) for face in faces],
                }))
        # Some seed fits cover only part of a region found by a later seed.
        candidates.extend(report for region, report in accepted
                          if not any(region < other for other, _ in accepted))
    return {
        'triangles': len(triangles),
        'bounds_mm': np.column_stack((vertices.min(axis=0), vertices.max(axis=0))).tolist(),
        'candidate_cylinders': candidates,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--units', choices=UNITS, default='mm')
    parser.add_argument('--tolerance-mm', type=float, default=3e-5)
    args = parser.parse_args()
    if not math.isfinite(args.tolerance_mm) or args.tolerance_mm <= 0:
        parser.error('tolerance must be finite and positive')
    try:
        report = probe(args.input, UNITS[args.units], args.tolerance_mm)
    except (OSError, ValueError) as error:
        parser.exit(1, f'STL probe failed: {error}\n')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
