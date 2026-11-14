"""Build and verify an editable SolidWorks part from an STL working copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace


SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS / "mesh"))
from convert import UNIT_IN_MM, convert as prepare_mesh

SW_SCRIPT = SCRIPTS / "solidworks" / "solidworks-part.ps1"


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def mesh_stage(args, source, work):
    identity = {
        "source_sha256": hash_file(source),
        "input_units": args.units,
        "holes": args.holes,
        "hole_diameter_mm": args.hole_diameter_mm,
    }
    step = work / "geometry.step"
    report_path = work / "geometry.json"
    request_path = work / "mesh-request.json"
    if any(path.exists() for path in (step, report_path, request_path)):
        if not all(path.is_file() for path in (step, report_path, request_path)):
            raise ValueError("Incomplete mesh stage. Use a new work directory.")
        if read_json(request_path) != identity:
            raise ValueError("Existing mesh stage has a different source or geometry options. Use a new work directory.")
        report = read_json(report_path)
        if report["step_sha256"] != hash_file(step) or report["mesh"]["source_sha256"] != identity["source_sha256"]:
            raise ValueError("Mesh stage geometry or report no longer matches its recorded hash.")
        return step, report

    print("Preparing closed geometry from STL", flush=True)
    report = prepare_mesh(SimpleNamespace(
        input=source, output=step, units=args.units, holes=args.holes,
        hole_diameter_mm=args.hole_diameter_mm, ocp_path=args.ocp_path, report=report_path,
    ))
    with request_path.open("x", encoding="utf-8") as stream:
        json.dump(identity, stream, indent=2)
    return step, report


def powershell():
    system = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    executable = system / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if os.name != "nt" or not executable.is_file():
        raise OSError("Native SLDPRT creation requires Windows PowerShell 5.1 and SolidWorks.")
    return executable


def sw(args, job, mode, log_name, **parameters):
    command = [str(powershell()), "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
               "-File", str(SW_SCRIPT), "-Mode", mode]
    if args.sw_root:
        parameters["SwRoot"] = args.sw_root.resolve(strict=True)
    for key, value in parameters.items():
        if value is not None:
            command += ["-" + key, str(value)]
    log = job / (log_name + ".log")
    print(f"SolidWorks {mode} ({log.name})", flush=True)
    with log.open("xb") as stream:
        try:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=args.sw_timeout)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f"SolidWorks {mode} timed out. Inspect the desktop for a dialog. Log: {log}") from error
    if result.returncode:
        raise RuntimeError(f"SolidWorks {mode} exited with {result.returncode}. Log: {log}")
    return log.read_text(encoding="utf-8", errors="replace")


def verify_import(log, report, bounds_tolerance, volume_tolerance):
    solids = re.findall(r"^solid_count=(\d+)\s*$", log, re.M)
    bounds = re.findall(r"^bounds_mm=([^\r\n]+)", log, re.M)
    volume = re.findall(r"^volume_mm3=([^\r\n]+)", log, re.M)
    if not solids or solids[-1] != "1" or not bounds or not volume:
        raise ValueError("SolidWorks did not report a measurable imported solid.")
    expected = report["round_trip"]
    xyz_bounds = [axis[end_index] for end_index in (0, 1) for axis in expected["bounds_mm"]]
    native_bounds = list(map(float, bounds[-1].split(",")))
    native_volume = float(volume[-1])
    if len(native_bounds) != 6 or not all(math.isfinite(v) for v in [*native_bounds, native_volume]):
        raise ValueError("Invalid measurements for SolidWorks import.")
    if max(abs(a - b) for a, b in zip(native_bounds, xyz_bounds)) > bounds_tolerance:
        raise ValueError("SolidWorks import bounds differ from the working STEP.")
    if abs(native_volume - expected["volume_mm3"]) > volume_tolerance:
        raise ValueError("SolidWorks import volume differs from the working STEP.")


def stage_part(path, job, name):
    original = path.resolve(strict=True)
    if not original.is_file() or original.suffix.lower() != ".sldprt":
        raise ValueError(f"Expected a native SLDPRT file: {original}")
    staged = job / (name + ".SLDPRT")
    shutil.copyfile(original, staged)
    return staged


def build_part(args, source, work, step, report):
    job = Path(tempfile.mkdtemp(prefix="native-", dir=work))
    print(f"Native working directory: {job}", flush=True)
    baseline = job / "baseline.SLDPRT"
    if args.imported_part:
        seed = stage_part(args.imported_part, job, "imported")
    else:
        seed = job / "import_source.step"
        shutil.copyfile(step, seed)
    try:
        audit = sw(args, job, "Prepare", "01-import", Source=seed, Destination=baseline)
    except RuntimeError as error:
        if args.imported_part:
            raise
        raise RuntimeError(
            f"{error}\nIf STEP import failed, open {step} in desktop SolidWorks, "
            "save a working SLDPRT, then rerun with --imported-part."
        ) from error
    verify_import(audit, report, args.bounds_tolerance_mm, args.volume_tolerance_mm3)

    defined = job / "editable.SLDPRT"
    if args.plan:
        sw(args, job, "Rebuild", "02-rebuild", Source=args.plan.resolve(strict=True),
           Destination=defined, Template=args.template.resolve(strict=True) if args.template else None)
        route = "SolidWorks native feature reconstruction"
    else:
        if args.recognized_part:
            recognized = stage_part(args.recognized_part, job, "recognized")
            route = "supplied SolidWorks recognition candidate"
        else:
            recognized = job / "recognized.SLDPRT"
            try:
                sw(args, job, "Recognize", "02-recognize", Source=baseline, Destination=recognized,
                   RecognitionOptions=args.recognition_options)
            except RuntimeError as error:
                raise RuntimeError(
                    f"{error}\nReview FeatureWorks on {baseline}. Supply a saved recognition candidate "
                    "with --recognized-part or a measured native feature plan with --plan."
                ) from error
            route = "FeatureWorks automatic recognition"
        sw(args, job, "Define", "03-define", Source=recognized, Destination=defined)

    validate = {
        "Source": defined, "Baseline": baseline,
        "VolumeToleranceMm3": args.volume_tolerance_mm3, "BoundsToleranceMm": args.bounds_tolerance_mm,
        "EditDimension": args.edit_dimension or "__auto__",
    }
    if not args.no_preview:
        validate["Preview"] = job / "review.bmp"
    sw(args, job, "Validate", "04-validate", **validate)
    if hash_file(source) != report["mesh"]["source_sha256"]:
        raise ValueError("The source STL changed during conversion. Rerun with a new work directory.")
    return defined, route, job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--units", choices=tuple(UNIT_IN_MM), default="mm")
    parser.add_argument("--holes", choices=("auto", "require", "keep"), default="auto")
    parser.add_argument("--hole-diameter-mm", type=float)
    parser.add_argument("--ocp-path", type=Path)
    parser.add_argument("--sw-root", type=Path)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--imported-part", type=Path)
    route = parser.add_mutually_exclusive_group()
    route.add_argument("--plan", type=Path)
    route.add_argument("--recognized-part", type=Path)
    parser.add_argument("--recognition-options", type=int, default=9)
    parser.add_argument("--edit-dimension")
    parser.add_argument("--volume-tolerance-mm3", type=float, default=0.01)
    parser.add_argument("--bounds-tolerance-mm", type=float, default=0.001)
    parser.add_argument("--sw-timeout", type=int, default=180, help="timeout per SolidWorks stage, in seconds")
    parser.add_argument("--no-preview", action="store_true")
    args = parser.parse_args()
    if args.hole_diameter_mm is not None and (
        not math.isfinite(args.hole_diameter_mm) or args.hole_diameter_mm <= 0 or args.holes == "keep"
    ):
        parser.error("--hole-diameter-mm requires a positive finite value with hole reconstruction enabled.")
    if args.sw_timeout <= 0 or any(not math.isfinite(v) or v < 0 for v in (args.volume_tolerance_mm3, args.bounds_tolerance_mm)):
        parser.error("Provide a positive timeout and finite, nonnegative tolerances.")
    try:
        source = args.input.resolve(strict=True)
        output = args.output.resolve()
        work = args.work_dir.resolve()
        if not source.is_file() or source.suffix.lower() != ".stl" or output.suffix.lower() != ".sldprt":
            raise ValueError("Use an STL input and an SLDPRT output.")
        if output.exists():
            raise FileExistsError(f"Output already exists: {output}")
        powershell()
        work.mkdir(parents=True, exist_ok=True)
        step, report = mesh_stage(args, source, work)
        candidate, route_name, job = build_part(args, source, work, step, report)
        output.parent.mkdir(parents=True, exist_ok=True)
        with candidate.open("rb") as input_stream, output.open("xb") as output_stream:
            shutil.copyfileobj(input_stream, output_stream)
        if hash_file(output) != hash_file(candidate):
            raise OSError("Final copy did not match the validated candidate.")
        print(json.dumps({"output": str(output), "route": route_name, "work_dir": str(job),
                          "input_units": args.units, "hole_status": report["hole_status"],
                          "sha256": hash_file(output)}, ensure_ascii=False, indent=2))
    except (OSError, ImportError, ValueError, RuntimeError) as error:
        parser.exit(1, f"STL to editable SolidWorks part stopped: {error}\n")


if __name__ == "__main__":
    main()
