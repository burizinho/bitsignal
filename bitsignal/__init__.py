"""BitSignal - Bitcoin Macro Cycle Sentinel."""

import time as _time

__version__ = "0.1.0"

# Import time of the package. The dashboard entrypoints compare it with the source files' mtime
# and drop stale modules: Streamlit Cloud keeps imported modules in memory across a redeploy.
_LOADED_AT = _time.time()
