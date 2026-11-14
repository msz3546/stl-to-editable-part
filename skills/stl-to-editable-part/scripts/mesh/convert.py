"""Convert a closed STL shell to a verified AP214 STEP solid."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

from faceted_step import convert as write_facets


UNIT_IN_MM = {'mm': 1.0, 'cm': 10.0, 'm': 1000.0, 'in': 25.4, 'ft': 304.8}


def convert(args):
    if args.ocp_path:
        sys.path.insert(0, str(args.ocp_path.resolve(strict=True)))

    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Interface import Interface_Static
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer

    from round_holes import find_holes, rebuild, verify as verify_cylinders
    from step_core import check_measurements, measurements, read

    source = args.input.resolve(strict=True)
    destination = args.output.resolve()
    report_path = args.report.resolve() if args.report else None
    if source.suffix.lower() != '.stl' or destination.suffix.lower() not in {'.step', '.stp'}:
        raise ValueError('Use an STL input and STEP or STP output')
    if report_path and (report_path.suffix.lower() != '.json' or report_path == destination):
        raise ValueError('The report must have a separate .json path')
    for output_path in (destination, report_path):
        if output_path and output_path.exists():
            raise FileExistsError(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory(prefix='stl-to-step-', dir=destination.parent) as temporary:
        temporary = Path(temporary)
        intermediate = temporary / 'faceted.step'
        expected = write_facets(source, intermediate, UNIT_IN_MM[args.units])
        shape = read(intermediate)
        original = measurements(shape)
        check_measurements(original, expected)

        unifier = ShapeUpgrade_UnifySameDomain(shape, True, True, False)
        unifier.SetSafeInputMode(True)
        unifier.SetLinearTolerance(1e-7)
        unifier.SetAngularTolerance(1e-6)
        unifier.Build()
        merged = unifier.Shape()
        merged_metrics = measurements(merged)
        check_measurements(merged_metrics, expected)

        final_shape = merged
        holes = []
        removed = []
        hole_status = 'polygonal geometry retained by request'
        if args.holes != 'keep':
            try:
                planes, others, candidates = find_holes(merged, args.hole_diameter_mm)
                rebuilt, removed = rebuild(planes, others, candidates)
                verify_cylinders(rebuilt, merged_metrics, candidates, removed)
            except ValueError as error:
                if args.holes == 'require' or args.hole_diameter_mm is not None:
                    raise
                hole_status = f'cylinder reconstruction skipped: {error}'
            else:
                final_shape = rebuilt
                holes = candidates
                hole_status = 'verified analytic cylinders'

        staged = temporary / 'verified.step'
        writer = STEPControl_Writer()
        if not Interface_Static.SetCVal_s('write.step.schema', 'AP214IS'):
            raise ValueError('Could not select STEP AP214')
        if not Interface_Static.SetCVal_s('write.step.unit', 'MM'):
            raise ValueError('Could not select millimetres for STEP output')
        if writer.Transfer(final_shape, STEPControl_AsIs) != IFSelect_RetDone:
            raise ValueError('STEP shape transfer failed')
        if writer.Write(str(staged)) != IFSelect_RetDone:
            raise ValueError('STEP file write failed')
        reread = read(staged)
        if holes:
            final_metrics = verify_cylinders(reread, merged_metrics, holes, removed)
        else:
            final_metrics = measurements(reread)
            check_measurements(final_metrics, expected)
            if final_metrics['faces'] != merged_metrics['faces']:
                raise ValueError('Merged face count changed during STEP round trip')
        with destination.open('xb') as output, staged.open('rb') as validated:
            shutil.copyfileobj(validated, output)

    report = {
        'input': str(source), 'output': str(destination),
        'input_units': args.units, 'output_units': 'mm', 'step_schema': 'AP214',
        'mesh': expected, 'faceted_solid': original, 'merged_solid': merged_metrics,
        'round_trip': final_metrics, 'hole_status': hole_status,
        'holes': [{key: value for key, value in hole.items() if key != 'original_rim_vertices'} for hole in holes],
        'step_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
    }
    if report_path:
        with report_path.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--units', choices=tuple(UNIT_IN_MM), default='mm', help='units of STL coordinates')
    parser.add_argument('--holes', choices=('auto', 'require', 'keep'), default='auto')
    parser.add_argument('--hole-diameter-mm', type=float, help='use this diameter if it agrees with all fitted hole rims')
    parser.add_argument('--ocp-path', type=Path, help='directory containing locally installed OCP dependencies')
    parser.add_argument('--report', type=Path, help='optional geometry verification JSON output')
    args = parser.parse_args()
    diameter = args.hole_diameter_mm
    if diameter is not None and (not math.isfinite(diameter) or diameter <= 0 or args.holes == 'keep'):
        parser.error('--hole-diameter-mm needs a positive finite value and hole reconstruction enabled')
    try:
        result = convert(args)
    except (OSError, ImportError, ValueError, RuntimeError) as error:
        parser.exit(1, f'STL conversion failed: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
