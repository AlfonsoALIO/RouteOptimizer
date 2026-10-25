import argparse
import os
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from env_file import load_env_if_present

load_env_if_present(str(_repo_root / '.env'))

from core import Parameters
from core.batch import run_batch
from core.fixtures import load_toy_mine
from core.haul_scenario import scenario_from_haul_rows
import core.data_access as da


def scenario_from_sql(params, loaders=None, demands=None, trucks=None, resident_capacity=2):
    """Fetch haul rows (credentials from the environment) and build a scenario."""
    rows = da.fetch_from_sqlserver(loaders=loaders)

    if demands is None:
        demands = []
    if trucks is None:
        trucks = [
            {"name": "truck_%i" % i, "tonnage_capacity": 100.0}
            for i in range(1, int(params.fleet_size) + 1)
        ]

    return scenario_from_haul_rows(
        rows,
        demands=demands,
        trucks=trucks,
        resident_capacity=resident_capacity,
        shift_length_hours=float(params.shift_length),
        fleet_size=int(params.fleet_size),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Batch fleet optimizer")
    parser.add_argument(
        "--toy",
        action="store_true",
        help="Run on the toy-mine scenario (no SQL Server)",
    )
    parser.add_argument("--job-name", default="TestJob")
    parser.add_argument(
        "--fleet-size",
        type=int,
        default=None,
        help="Fleet size when loading from SQL (default: 29 for legacy parity)",
    )
    parser.add_argument(
        "--loaders",
        nargs="*",
        default=None,
        help="Optional CargCo / loader ids to include. Omit for all loaders.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Solve without writing a pickle file",
    )
    args = parser.parse_args(argv)

    if args.toy or not os.environ.get("SQLSERVER_PASSWORD"):
        scenario = load_toy_mine()
        from core.batch import parameters_from_scenario

        params = parameters_from_scenario(scenario)
    else:
        fleet_size = args.fleet_size if args.fleet_size is not None else 29
        params = Parameters(tonnage_demand={}, shift_length=12)
        params.fleet_size = fleet_size
        scenario = scenario_from_sql(params, loaders=args.loaders)
        from core.batch import parameters_from_scenario

        params = parameters_from_scenario(scenario)

    return run_batch(
        scenario, params=params, job_name=args.job_name, persist=not args.no_persist
    )


if __name__ == "__main__":
    main()
