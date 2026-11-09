"""Root entrypoint for Streamlit Cloud deployment."""

import os
import sys
from pathlib import Path

# Add project root to sys.path so bitsignal package is discoverable
ROOT_DIR = Path(__file__).resolve().parent
root_str = str(ROOT_DIR)
while root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

# Drop cached bitsignal modules that are stale: loaded from outside this checkout, or whose source
# changed on disk after the import (Streamlit Cloud keeps modules in memory across a redeploy).
_loaded_at = getattr(sys.modules.get("bitsignal"), "_LOADED_AT", None)
_names = [m for m in list(sys.modules) if m == "bitsignal" or m.startswith("bitsignal.")]
_files = {m: getattr(sys.modules.get(m), "__file__", None) for m in _names}
# A loaded package without _LOADED_AT predates this check, so it is stale too.
_changed = bool(_names) and (_loaded_at is None or any(
    f and f.startswith(root_str) and os.path.exists(f) and os.path.getmtime(f) > _loaded_at for f in _files.values()
))
for mod_name, mod_file in _files.items():
    if _changed or (mod_file and not mod_file.startswith(root_str)):
        sys.modules.pop(mod_name, None)

# Execute the main dashboard UI. Streamlit re-executes this script on every rerun,
# but a plain `import` only runs the module body once; calling main() renders every time.
from bitsignal.ui.app import main  # noqa: E402

main()
