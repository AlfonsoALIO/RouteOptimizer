# Runtime dependency licenses

RouteOptimizer is released under the **MIT License** (`LICENSE`). The table
below records the license of each runtime dependency used by the fleet UI and
the batch solvers, and whether it is compatible with MIT distribution.

Compatibility here means the dependency may be used alongside MIT-licensed
application code without requiring a proprietary or reciprocal license that
would prevent releasing this repository under MIT.

| Package | Role | License | Compatible with MIT |
|---------|------|---------|---------------------|
| Django | Fleet UI | BSD-3-Clause | Yes |
| PuLP | MILP modeling; uses CBC by default | BSD-ish / OSI-approved (PuLP) | Yes |
| numpy | Numeric support (UI / haul data) | BSD-3-Clause | Yes |
| pandas | Haul / frame utilities | BSD-3-Clause | Yes |
| pyodbc | Optional SQL Server haul import | MIT | Yes |
| python-dateutil | Date parsing (pandas stack) | BSD-2-Clause / Apache-2.0 dual | Yes |
| pytz | Time zones (Django / pandas) | MIT | Yes |
| six | Compatibility (older stack) | MIT | Yes |
| pyparsing | PuLP / parsing support | MIT | Yes |

Development and notebook extras listed in `lean_ui/requirements.txt` (IPython,
Pygments, prompt-toolkit, and related packages) are not required to run the
dispatch or shift-plan solvers. They are OSI-approved (BSD/MIT) where present
and do not block an MIT release of this project.

**Commercial solvers:** none are required. PuLP’s default CBC backend is used
without a commercial solver license (see NFR5 / Epic 6).
