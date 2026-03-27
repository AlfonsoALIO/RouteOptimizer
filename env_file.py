"""Load KEY=value lines from a file into os.environ (does not override existing keys)."""

import os


def load_env_if_present(path):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        return
    with open(path, encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, _, val = line.partition('=')
            key = key.strip()
            if key.startswith('export '):
                key = key[7:].strip()
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                val = val[1:-1]
            if key and key not in os.environ:
                os.environ[key] = val
