"""Write a closed, consistently oriented STL as AP214 faceted BREP.

Standard-library only. Coordinates are converted to millimetres.
Tiny coincident-vertex noise is welded, without smoothing or reconstruction.

Entity definitions checked against primary STEP resource/EXPRESS documentation:
https://www.steptools.com/stds/smrl/data/resource_docs/geometric_and_topological_representation/sys/6_schema.htm
https://www.steptools.com/stds/smrl/data/resource_docs/geometric_and_topological_representation/sys/5_schema.htm
https://downloads.steptools.com/docs/stp_aim/html/t_faceted_brep_shape_representation.html

The AP214 representation's WR3 requires FACE_SURFACE on PLANE, even though the
generic FACETED_BREP definition also permits implicit surface geometry.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import re
import struct


def point_sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(a):
    length = math.sqrt(sum(x * x for x in a))
    if length <= 1e-14:
        raise ValueError("Degenerate triangle or direction")
    return tuple(x / length for x in a)


def real(x):
    # A STEP REAL must contain a decimal point, including scientific notation.
    s = format(float(x), ".17g").upper()
    if "." not in s:
        if "E" in s:
            s = s.replace("E", ".E")
        else:
            s += "."
    return s


def string(s):
    # ISO 10303-21 Unicode escape; resulting physical file remains plain ASCII.
    if not s.isascii():
        return "'\\X2\\" + s.encode("utf-16-be").hex().upper() + "\\X0\\'"
    return "'" + s.replace("'", "''").replace("\\", "\\\\") + "'"


class Step:
    def __init__(self):
        self.rows = []

    def add(self, value):
        number = len(self.rows) + 1
        self.rows.append(f"#{number}={value};")
        return f"#{number}"


def parse_triangles(data):
    count = struct.unpack_from('<I', data, 80)[0] if len(data) >= 84 else 0
    if count and len(data) == 84 + 50 * count:
        for index in range(count):
            raw = struct.unpack_from('<12fH', data, 84 + index * 50)
            yield (raw[3:6], raw[6:9], raw[9:12])
        return
    try:
        ascii_stl = data.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise ValueError('Invalid binary STL size or unsupported STL encoding') from error
    number = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
    vertex = re.compile(rf'vertex\s+({number})\s+({number})\s+({number})', re.I)
    facet_pattern = re.compile(r'\bfacet\s+normal\b(.*?)\bendfacet\b', re.I | re.S)
    facets = facet_pattern.findall(ascii_stl)
    if not ascii_stl.lstrip().lower().startswith('solid') or not facets:
        raise ValueError('Invalid ASCII STL')
    if len(facets) != len(re.findall(r'\bfacet\s+normal\b', ascii_stl, re.I)):
        raise ValueError('Unterminated ASCII STL facet')
    for facet in facets:
        vertices = tuple(tuple(map(float, groups)) for groups in vertex.findall(facet))
        if len(vertices) != 3:
            raise ValueError('Expected three vertices in each ASCII STL facet')
        yield vertices


def convert(source: Path, destination: Path, scale_to_mm=1.0):
    data = source.read_bytes()

    points = []
    point_ids = {}
    triangles = []
    max_weld_displacement = 0.0
    original_volume = 0.0
    for raw_triangle in parse_triangles(data):
        tri = [tuple(coordinate * scale_to_mm for coordinate in point) for point in raw_triangle]
        original_volume += sum(a * b for a, b in zip(tri[0], cross(tri[1], tri[2]))) / 6.0
        indices = []
        for p in tri:
            if not all(math.isfinite(v) for v in p):
                raise ValueError("Non-finite STL coordinate")
            key = tuple(round(v, 8) for v in p)
            if key not in point_ids:
                point_ids[key] = len(points)
                # Eliminate insignificant +/- 1e-17 zero noise only.
                points.append(tuple(0.0 if abs(v) < 1e-12 else v for v in p))
            vertex_index = point_ids[key]
            max_weld_displacement = max(max_weld_displacement, math.dist(p, points[vertex_index]))
            indices.append(vertex_index)
        if len(set(indices)) != 3:
            raise ValueError("Degenerate triangle after vertex weld")
        unit(cross(point_sub(points[indices[1]], points[indices[0]]), point_sub(points[indices[2]], points[indices[0]])))
        triangles.append(tuple(indices))

    if max_weld_displacement > 1e-8:
        raise ValueError("Vertex weld exceeded intended numerical-noise tolerance")
    edges = Counter(tuple(sorted((t[j], t[(j+1) % 3]))) for t in triangles for j in range(3))
    directed = Counter((t[j], t[(j+1) % 3]) for t in triangles for j in range(3))
    if any(n != 2 for n in edges.values()):
        raise ValueError("Mesh is not a closed 2-manifold")
    if any(directed[(a, b)] != 1 or directed[(b, a)] != 1 for a, b in edges):
        raise ValueError("Mesh orientation is inconsistent")
    adjacency = defaultdict(set)
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    visited = set()
    pending = [0]
    while pending:
        v = pending.pop()
        if v not in visited:
            visited.add(v)
            pending.extend(adjacency[v] - visited)
    if len(visited) != len(points):
        raise ValueError("This writer requires one connected shell per input")
    if abs(original_volume) < 1e-18:
        raise ValueError('STL shell has zero signed volume')
    if original_volume < 0:
        triangles = [(a, c, b) for a, b, c in triangles]

    s = Step()
    app = s.add("APPLICATION_CONTEXT('automotive design')")
    s.add(f"APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,{app})")
    product_context = s.add(f"PRODUCT_CONTEXT('',{app},'mechanical')")
    product = s.add(f"PRODUCT({string(source.stem)},{string(source.stem)},'',({product_context}))")
    formation = s.add(f"PRODUCT_DEFINITION_FORMATION('1','',{product})")
    definition_context = s.add(f"PRODUCT_DEFINITION_CONTEXT('part definition',{app},'design')")
    definition = s.add(f"PRODUCT_DEFINITION('design','',{formation},{definition_context})")
    definition_shape = s.add(f"PRODUCT_DEFINITION_SHAPE('','',{definition})")
    s.add(f"PRODUCT_RELATED_PRODUCT_CATEGORY('part','',({product}))")
    length = s.add("(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.))")
    angle = s.add("(NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.))")
    solid_angle = s.add("(NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT())")
    uncertainty = s.add(f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-7),{length},'distance_accuracy_value','')")
    context = s.add(f"(GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT(({uncertainty})) GLOBAL_UNIT_ASSIGNED_CONTEXT(({length},{angle},{solid_angle})) REPRESENTATION_CONTEXT('','3D'))")
    refs = [s.add("CARTESIAN_POINT('',(" + ",".join(real(v) for v in p) + "))") for p in points]
    faces = []
    for a, b, c in triangles:
        u = point_sub(points[b], points[a])
        v = point_sub(points[c], points[a])
        normal = unit(cross(u, v))
        reference = unit(u)
        nref = s.add("DIRECTION('',(" + ",".join(real(x) for x in normal) + "))")
        rref = s.add("DIRECTION('',(" + ",".join(real(x) for x in reference) + "))")
        placement = s.add(f"AXIS2_PLACEMENT_3D('',{refs[a]},{nref},{rref})")
        plane = s.add(f"PLANE('',{placement})")
        loop = s.add(f"POLY_LOOP('',({refs[a]},{refs[b]},{refs[c]}))")
        bound = s.add(f"FACE_OUTER_BOUND('',{loop},.T.)")
        faces.append(s.add(f"FACE_SURFACE('',({bound}),{plane},.T.)"))
    shell = s.add("CLOSED_SHELL('',(" + ",".join(faces) + "))")
    solid = s.add(f"FACETED_BREP({string(source.stem)},{shell})")
    origin = s.add("CARTESIAN_POINT('',(0.,0.,0.))")
    z_dir = s.add("DIRECTION('',(0.,0.,1.))")
    x_dir = s.add("DIRECTION('',(1.,0.,0.))")
    axes = s.add(f"AXIS2_PLACEMENT_3D('',{origin},{z_dir},{x_dir})")
    representation = s.add(f"FACETED_BREP_SHAPE_REPRESENTATION('',({axes},{solid}),{context})")
    s.add(f"SHAPE_DEFINITION_REPRESENTATION({definition_shape},{representation})")

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    header = ["ISO-10303-21;", "HEADER;", "FILE_DESCRIPTION(('Closed faceted solid converted from STL in millimetres'),'2;1');", f"FILE_NAME({string(destination.name)},{string(timestamp)},(''),(''),'STL faceted BREP writer','STL faceted BREP writer','');", "FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));", "ENDSEC;", "DATA;"]
    text = "\n".join(header + s.rows + ["ENDSEC;", "END-ISO-10303-21;", ""])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="ascii", newline="\n")
    return {
        'source_sha256': hashlib.sha256(data).hexdigest(),
        'triangles': len(triangles),
        'welded_vertices': len(points),
        'maximum_weld_displacement_mm': max_weld_displacement,
        'source_signed_volume_mm3': original_volume,
        'bounds_mm': [[min(p[j] for p in points), max(p[j] for p in points)] for j in range(3)],
    }
