"""Root entrypoint for Streamlit Cloud deployment."""

import sys
from pathlib import Path

# Add project root to sys.path so bitsignal package is discoverable
ROOT_DIR = Path(__file__).resolve().parent
root_str = str(ROOT_DIR)
while root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

# Purge any stale bitsignal modules cached from site-packages
for mod_name in list(sys.modules.keys()):
    if mod_name == "bitsignal" or mod_name.startswith("bitsignal."):
        mod_obj = sys.modules.get(mod_name)
        mod_file = getattr(mod_obj, "__file__", None)
        if mod_file and not mod_file.startswith(root_str):
            del sys.modules[mod_name]

# Execute the main dashboard UI
import bitsignal.ui.app  # noqa: E402, F401
