import os
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from env_file import load_env_if_present

load_env_if_present(str(_repo_root / '.env'))

from core import Parameters, calculate_route_times, ProblemResults
from core.optimization import LinearProblem, solve
import core.data_access as da
import pandas as pd

# Job Name TODO: Parameterize
job_name = "TestJob"

# Program parameters
params = Parameters(tonnage_demand=50, shift_length=12)


# Fetch data (credentials must not be committed; see .env.example)
server = os.environ.get('SQLSERVER_SERVER', 'localhost')
database = os.environ.get('SQLSERVER_DATABASE', 'stg_Production')
username = os.environ.get('SQLSERVER_USERNAME', 'sa')
password = os.environ.get('SQLSERVER_PASSWORD')
if not password:
    raise RuntimeError(
        'SQLSERVER_PASSWORD is not set. Copy .env.example to .env and set database credentials.'
    )

port = int(os.environ.get('SQLSERVER_PORT', '1443'))
data = da.fetch_from_sqlserver(server, database, username, password, port=port)


# Infer route times per segment and destinations

# Create a data frame from the dictionary
frame = pd.DataFrame(data)
# Locations TODO: How about the sources
locations = list(frame['destination'].unique())
# Machines
machines = list(frame['machine'].unique())
# Arc times in average
times = calculate_route_times(frame)

# Fleet size
fsize = 29 # TODO: Parameterize this


# Instantiate and solve problems

# Compute all the location pairs (arcs in the graph)
arcs = [(a, b) for a in locations for b in locations if a != b and b in times]

# Solve the subproblems
subproblems = [LinearProblem(nodes, times, fsize) for nodes in arcs]

results = dict()
for p in subproblems:
    try:
        k = p.name
        status, variables = solve(p)
        solution = ProblemResults(status, variables)
        results[k] = solution
    except Exception as e:
        print(e)

# Persist results
# TODO: Store it somewhere, perhaps Amazon's table storage for the API to retrieve later on
da.persist_results(job_name, results)