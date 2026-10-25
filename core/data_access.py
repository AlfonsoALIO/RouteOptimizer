""" Data access and reading elements """

import os
import pickle

try:
    import pyodbc
except ImportError:  # pragma: no cover - optional until SQL path is used
    pyodbc = None


def _odbc_braced(value):
    """Escape a value for ODBC connection strings (mitigates connection-string injection)."""
    return '{' + str(value).replace('}', '}}') + '}'


def build_haul_query(loaders=None):
    """Build the haul history SQL.

    loaders: optional iterable of CargCo / loader ids. When None or empty,
    every loader is included (no hardcoded machine list).
    """
    base = """SELECT P.Date, P.Shift, P.MachineId, R.Loads, R.HT, R.Destination, R.Distance,
            R.Material, R.CargCo, R.Cargue, M.Model FROM [PRODUC_FILTERED] R INNER JOIN
            PRINCIPAL P ON R.Id = P.Id inner JOIN
            Maquinas M ON R.Cargco = M.MachineId
            WHERE Loads IS NOT NULL"""

    if loaders:
        escaped = []
        for loader in loaders:
            text = str(loader).replace("'", "''")
            escaped.append("'%s'" % text)
        base += "\n            AND Cargco IN (%s)" % ", ".join(escaped)

    return base


def _row_to_dict(row):
    """Map a SQL haul row to the haul-scenario field names."""
    return {
        "date": row[0],
        "shift": row[1],
        "machine": row[2],
        "loads": row[3],
        "haul_time": row[4],
        "destination": row[5],
        "distance": row[6],
        "loader": row[8],  # CargCo
    }


def fetch_from_sqlserver(
    server=None,
    database=None,
    username=None,
    password=None,
    port=None,
    loaders=None,
):
    """Obtain haul rows from SQL Server.

    Credentials default to SQLSERVER_* environment variables.
    loaders filters by CargCo when provided; otherwise all loaders are returned.
    """
    if pyodbc is None:
        raise RuntimeError("pyodbc is required to fetch haul rows from SQL Server")

    server = server if server is not None else os.environ.get("SQLSERVER_SERVER", "localhost")
    database = (
        database
        if database is not None
        else os.environ.get("SQLSERVER_DATABASE", "stg_Production")
    )
    username = (
        username if username is not None else os.environ.get("SQLSERVER_USERNAME", "sa")
    )
    password = password if password is not None else os.environ.get("SQLSERVER_PASSWORD")
    if not password:
        raise RuntimeError(
            "SQLSERVER_PASSWORD is not set. Copy .env.example to .env and set database credentials."
        )
    port = int(port if port is not None else os.environ.get("SQLSERVER_PORT", "1443"))

    conn_str = (
        "DRIVER={ODBC Driver 13 for SQL Server};"
        "SERVER=%s;PORT=%s;DATABASE=%s;UID=%s;PWD=%s"
        % (
            _odbc_braced(server),
            port,
            _odbc_braced(database),
            _odbc_braced(username),
            _odbc_braced(password),
        )
    )
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    tsql = build_haul_query(loaders)

    data = []
    with cursor.execute(tsql):
        row = cursor.fetchone()
        while row:
            data.append(_row_to_dict(row))
            row = cursor.fetchone()

    return data


def persist_results(job_name, problem_results):
    """ Persists the LP results to a backend storage, current implementation to a pickle file """

    json_results = {k: v.to_json() for k, v in problem_results.items()}

    with open("%s.pickle" % job_name, "wb") as f:
        pickle.dump(json_results, f)
