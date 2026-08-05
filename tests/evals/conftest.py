import sys
from pathlib import Path

# app.py and skills/ live at the repo root; pytest's default import mode does not
# add it to sys.path since tests/evals/ has no __init__.py chain up to root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
