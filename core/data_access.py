""" Data access and reading elements """

import pyodbc
import pickle


def _odbc_braced(value):
    """Escape a value for ODBC connection strings (mitigates connection-string injection)."""
    return '{' + str(value).replace('}', '}}') + '}'


def fetch_from_sqlserver(server, database, username, password, port=1443):
    """ Obtains the data from Alfonsos' SQL Server database format """

    conn_str = (
        'DRIVER={ODBC Driver 13 for SQL Server};'
        'SERVER=%s;PORT=%s;DATABASE=%s;UID=%s;PWD=%s'
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

    tsql = """SELECT P.Date, P.Shift, P.MachineId, R.Loads, R.HT, R.Destination, R.Distance,
            R.Material, R.CargCo, R.Cargue, M.Model FROM [PRODUC_FILTERED] R INNER JOIN
            PRINCIPAL P ON R.Id = P.Id inner JOIN
            Maquinas M ON R.Cargco = M.MachineId

            --where P.[Date] between ('2013-01-01 00:00:00.000') and ('2013-07-01 00:00:00.000')
            AND Loads IS NOT NULL
            --and Destination in ('QUEBRADORA', 'TEPETATERA', 'TEPETAT #2')
            AND Cargco IN ('C243', 'R418', 'R422', 'R417')"""

    def to_dict(row):
        """ Auxiliary function to make a dictionary out of a SQL row """

        ret = dict()

        ret['date'] = row[0]
        ret['shift'] = row[1]
        ret['machine'] = row[2]
        ret['loads'] = row[3]
        ret['haul_time'] = row[4]
        ret['destination'] = row[5]
        ret['distance'] = row[6]

        return ret
    data = list()

    with cursor.execute(tsql):
        row = cursor.fetchone()
        while row:
            data.append(to_dict(row))
            row = cursor.fetchone()

    return data


def persist_results(job_name, problem_results):
    """ Persists the LP results to a backend storage, current implementation to a pickle file """

    json_results = {k:v.to_json() for k, v in problem_results.items()}

    with open('%s.pickle' % job_name, 'wb') as f:
        pickle.dump(json_results, f)

