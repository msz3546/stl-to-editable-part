"""STEP import and geometry checks shared by the converter."""
from __future__ import annotations

from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopTools import TopTools_IndexedMapOfShape


def subshapes(shape, kind):
    ex = TopExp_Explorer(shape, kind)
    result = []
    while ex.More():
        result.append(ex.Current())
        ex.Next()
    return result


def count_unique(shape, kind):
    indexed = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, kind, indexed)
    return indexed.Extent()


def read(path):
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"STEP ReadFile failed: {path}: {status}")
    if hasattr(reader, "SetSystemLengthUnit"):
        reader.SetSystemLengthUnit(1.0)  # Open CASCADE internal coordinates: millimetres.
    transferred = reader.TransferRoots()
    if transferred < 1:
        raise RuntimeError(f"No transferable roots: {path}")
    shape = reader.OneShape()
    if shape.IsNull():
        raise RuntimeError(f"Null shape: {path}")
    return shape


def measurements(shape):
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    box = Bnd_Box()
    if hasattr(BRepBndLib, "AddOptimal_s"):
        BRepBndLib.AddOptimal_s(shape, box, False, False)
    else:
        BRepBndLib.Add_s(shape, box, False)
    bb = box.Get()
    return {"valid": bool(BRepCheck_Analyzer(shape).IsValid()), "solids": count_unique(shape, TopAbs_SOLID), "shells": count_unique(shape, TopAbs_SHELL), "faces": count_unique(shape, TopAbs_FACE), "edges": count_unique(shape, TopAbs_EDGE), "vertices": count_unique(shape, TopAbs_VERTEX), "volume_mm3": props.Mass(), "bounds_mm": [[bb[i], bb[i + 3]] for i in range(3)]}


def check_measurements(actual, expected):
    if not actual["valid"] or actual["solids"] != 1:
        raise RuntimeError(f"Expected one valid ordinary solid: {actual}")
    wanted_volume = abs(expected["source_signed_volume_mm3"])
    delta = abs(actual["volume_mm3"] - wanted_volume)
    relative = delta / wanted_volume
    if relative > 1e-6:
        raise RuntimeError(f"Volume mismatch: {relative}")
    bounds_delta = max(abs(a - b) for pair_a, pair_b in zip(actual["bounds_mm"], expected["bounds_mm"]) for a, b in zip(pair_a, pair_b))
    if bounds_delta > 1e-5:
        raise RuntimeError(f"Bounds mismatch: {bounds_delta} mm")
    return {"volume_relative_error": relative, "max_bounds_delta_mm": bounds_delta}
