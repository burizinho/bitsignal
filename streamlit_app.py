"""Root entrypoint for Streamlit Cloud deployment."""

import sys
from pathlib import Path

# Add project root to sys.path so bitsignal package is discoverable
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Execute the main dashboard UI
import bitsignal.ui.app  # noqa: F401
