"""Recover matched straight circular through holes on two parallel faces."""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from step_core import measurements, subshapes

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeSolid, BRepBuilderAPI_MakeWire, BRepBuilderAPI_Sewing
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepGProp import BRepGProp
from OCP.BRepLib import BRepLib
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_FACE, TopAbs_OUT, TopAbs_REVERSED, TopAbs_SHELL, TopAbs_VERTEX, TopAbs_WIRE
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt


@dataclass
class Rim:
    y: float
    center: np.ndarray  # x, z
    radius: float
    max_error: float
    area: float
    points: np.ndarray


def vertex_points(shape):
    vertices = (TopoDS.Vertex_s(vertex) for vertex in subshapes(shape, TopAbs_VERTEX))
    return np.array([BRep_Tool.Pnt_s(vertex).Coord() for vertex in vertices])


def fit_rim(wire):
    points = np.unique(np.round(vertex_points(wire), 8), axis=0)
    if len(points) < 12 or np.ptp(points[:, 1]) > 1e-6:
        raise ValueError('Expected one polygonal loop normal to Y')
    planar_points = points[:, [0, 2]]
    average = planar_points.mean(axis=0)
    local = planar_points - average
    x, z = local.T
    rhs = x*x + z*z
    fit, _, rank, _ = np.linalg.lstsq(np.column_stack([2*x, 2*z, np.ones(len(x))]), rhs, rcond=None)
    if rank != 3:
        raise ValueError('Rim vertices do not define a circle')
    center = average + fit[:2]
    radius = float(math.sqrt(fit[2] + fit[:2] @ fit[:2]))
    radial_error = float(np.max(np.abs(np.linalg.norm(planar_points-center, axis=1)-radius)))
    if radial_error > 2e-5:
        raise ValueError(f'Rim is not circular within 0.00002 mm: {radial_error}')
    angles = np.arctan2(planar_points[:, 1] - center[1], planar_points[:, 0] - center[0])
    sorted_angles = np.sort(angles)
    gaps = np.diff(np.r_[sorted_angles, sorted_angles[0]+2*math.pi])
    if np.max(gaps) > math.pi/3:
        raise ValueError('Hole rim does not cover the full circumference')
    polygon = (planar_points - center)[np.argsort(angles)]
    xp, zp = polygon.T
    area = float(abs(xp @ np.roll(zp, -1) - zp @ np.roll(xp, -1)) / 2)
    return Rim(float(points[:, 1].mean()), center, radius, radial_error, area, points)


def find_holes(shape, diameter_mm=None):
    faces_with_rims = []
    other_faces = []
    for item in subshapes(shape, TopAbs_FACE):
        face = TopoDS.Face_s(item)
        wires = [TopoDS.Wire_s(wire) for wire in subshapes(face, TopAbs_WIRE)]
        if len(wires) == 1:
            other_faces.append(face)
            continue
        adapter = BRepAdaptor_Surface(face)
        if adapter.GetType() != GeomAbs_Plane or abs(adapter.Plane().Axis().Direction().Y()) < 0.999999:
            raise ValueError('Found an unexpected surface with inner wires')
        outer = BRepTools.OuterWire_s(face)
        rims = [fit_rim(wire) for wire in wires if not wire.IsSame(outer)]
        faces_with_rims.append((face, rims))
    if not faces_with_rims:
        raise ValueError('No fully enclosed hole rims found')
    if len(faces_with_rims) != 2 or len(faces_with_rims[0][1]) != len(faces_with_rims[1][1]):
        raise ValueError('Expected two planes with matching counts of hole rims')
    faces_with_rims.sort(key=lambda item: item[1][0].y)
    (_, low_rims), (_, high_rims) = faces_with_rims
    holes = []
    unmatched = set(range(len(high_rims)))
    for low in low_rims:
        index = min(unmatched, key=lambda i: np.linalg.norm(low.center-high_rims[i].center))
        high = high_rims[index]
        unmatched.remove(index)
        if high.y <= low.y or np.linalg.norm(low.center-high.center) > 2e-5 or abs(low.radius-high.radius) > 2e-5:
            raise ValueError('Hole end loops do not describe the same straight cylinder')
        center = ((low.center + high.center)/2).tolist()
        radius = (low.radius + high.radius)/2
        if diameter_mm is not None:
            if abs(2*radius - diameter_mm) > 2e-5:
                raise ValueError(f'Requested diameter {diameter_mm:g} mm disagrees with fitted diameter {2*radius:g} mm')
            radius = diameter_mm/2
        holes.append({'x': center[0], 'z': center[1], 'y0': low.y, 'y1': high.y,
                      'radius': radius, 'max_fit_error': max(low.max_error, high.max_error),
                      'poly_area': (low.area+high.area)/2,
                      'original_rim_vertices': np.concatenate([low.points, high.points])})
    return faces_with_rims, other_faces, holes


def replacement_plane(face, rims, holes):
    plane = BRepAdaptor_Surface(face).Plane()
    maker = BRepBuilderAPI_MakeFace(plane, BRepTools.OuterWire_s(face), True)
    normal = plane.Axis().Direction()
    into_hole = gp_Dir(-normal.X(), -normal.Y(), -normal.Z())
    for hole in holes:
        origin = gp_Pnt(hole['x'], rims[0].y, hole['z'])
        edge = BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(origin, into_hole), hole['radius'])).Edge()
        maker.Add(BRepBuilderAPI_MakeWire(edge).Wire())
    result = maker.Face()
    if not BRepCheck_Analyzer(result).IsValid():
        raise ValueError('Invalid planar face with circular openings')
    if face.Orientation() == TopAbs_REVERSED:
        result.Reverse()
    return result


def cylinder_wall(hole):
    start = gp_Pnt(hole['x'], hole['y0'], hole['z'])
    axis = gp_Ax2(start, gp_Dir(0, 1, 0))
    cylinder = BRepPrimAPI_MakeCylinder(axis, hole['radius'], hole['y1']-hole['y0']).Shape()
    for item in subshapes(cylinder, TopAbs_FACE):
        face = TopoDS.Face_s(item)
        if BRepAdaptor_Surface(face).GetType() == GeomAbs_Cylinder:
            face.Reverse()
            return face
    raise RuntimeError('Could not construct cylindrical wall')


def rebuild(faces_with_rims, other_faces, holes):
    sewing = BRepBuilderAPI_Sewing(1e-6)
    removed = [0] * len(holes)
    old_void_volumes = [0.0] * len(holes)
    for face in other_faces:
        points = vertex_points(face)
        matching = []
        for index, hole in enumerate(holes):
            deltas = points[:, None, :] - hole['original_rim_vertices'][None, :, :]
            if np.all(np.min(np.linalg.norm(deltas, axis=2), axis=1) < 1e-6):
                matching.append(index)
        if matching:
            if len(matching) != 1 or np.ptp(points[:, 1]) < 1e-6:
                raise ValueError('Ambiguous polygonal hole wall')
            index = matching[0]
            removed[index] += 1
            properties = GProp_GProps()
            BRepGProp.SurfaceProperties_s(face, properties)
            normal_x = BRepAdaptor_Surface(face).Plane().Axis().Direction().X()
            if face.Orientation() == TopAbs_REVERSED:
                normal_x = -normal_x
            # Flux of (x-center_x, 0, 0) gives void volume. The two Y-normal caps contribute zero.
            old_void_volumes[index] -= properties.Mass() * (properties.CentreOfMass().X() - holes[index]['x']) * normal_x
        else:
            sewing.Add(face)
    for count, volume, hole in zip(removed, old_void_volumes, holes):
        if count < 12:
            raise ValueError(f'Incomplete wall identification: {removed}')
        approximate_volume = hole['poly_area'] * (hole['y1']-hole['y0'])
        if abs(volume-approximate_volume) > 0.05:
            raise ValueError(f'Unexpected volume for source hole: {volume}')
        hole['original_void_mm3'] = volume
        sewing.Add(cylinder_wall(hole))
    for face, rims in faces_with_rims:
        sewing.Add(replacement_plane(face, rims, holes))
    sewing.Perform()
    if sewing.NbFreeEdges() != 0 or sewing.NbMultipleEdges() != 0:
        raise ValueError(f'Rebuilt shell has {sewing.NbFreeEdges()} free and {sewing.NbMultipleEdges()} multiple edges')
    sewn = sewing.SewedShape()
    shells = subshapes(sewn, TopAbs_SHELL)
    if len(shells) != 1:
        raise ValueError(f'Expected one sewn shell, received {len(shells)}')
    solid = BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(shells[0])).Solid()
    if not BRepLib.OrientClosedSolid_s(solid):
        raise ValueError('Rebuilt solid could not be oriented')
    return solid, removed


def verify(shape, original, holes, removed):
    metrics = measurements(shape)
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props, 1e-10, True, False)
    metrics['volume_mm3'] = props.Mass()
    if not metrics['valid'] or metrics['solids'] != 1 or metrics['shells'] != 1:
        raise ValueError(f'Expected one valid solid: {metrics}')
    if metrics['faces'] != original['faces'] - sum(removed) + len(holes):
        raise ValueError('Unexpected change to faces outside the hole walls')
    bounds_delta = np.max(np.abs(np.array(metrics['bounds_mm']) - original['bounds_mm']))
    if bounds_delta > 1e-6:
        raise ValueError(f'Outer bounds changed by {bounds_delta} mm')
    expected_loss = sum(math.pi * h['radius']**2 * (h['y1']-h['y0']) - h['original_void_mm3'] for h in holes)
    volume_loss = original['volume_mm3'] - metrics['volume_mm3']
    if abs(volume_loss-expected_loss) > 0.001:
        raise ValueError(f'Volume change {volume_loss} differs from expected loss {expected_loss}')
    cylinders = []
    for item in subshapes(shape, TopAbs_FACE):
        face = TopoDS.Face_s(item)
        adaptor = BRepAdaptor_Surface(face)
        if adaptor.GetType() != GeomAbs_Cylinder:
            if adaptor.GetType() != GeomAbs_Plane:
                raise ValueError('Unexpected surface type')
            continue
        cylinder = adaptor.Cylinder()
        axis = cylinder.Axis().Direction()
        if abs(axis.Y()) < 0.999999 or abs(adaptor.LastUParameter()-adaptor.FirstUParameter()-2*math.pi) > 1e-7:
            raise ValueError('Hole wall is not a complete cylinder along Y')
        center = cylinder.Location()
        cylinders.append((center.X(), center.Z(), cylinder.Radius(), adaptor.LastVParameter()-adaptor.FirstVParameter()))
    if len(cylinders) != len(holes):
        raise ValueError(f'Expected {len(holes)} complete cylinder faces, received {len(cylinders)}')
    for hole in holes:
        target = (hole['x'], hole['z'], hole['radius'], hole['y1']-hole['y0'])
        if not any(np.max(np.abs(np.array(cylinder) - target)) < 1e-6 for cylinder in cylinders):
            raise ValueError(f'Circular wall does not match fitted hole {target}')
        center = gp_Pnt(hole['x'], (hole['y0']+hole['y1'])/2, hole['z'])
        if BRepClass3d_SolidClassifier(shape, center, 1e-7).State() != TopAbs_OUT:
            raise ValueError('Hole center is not open')
    metrics.update(cylinder_count=len(cylinders), max_bounds_change_mm=float(bounds_delta), volume_loss_mm3=volume_loss,
                   expected_loss_mm3=expected_loss)
    return metrics
