"""Start a local server using the user's isolated environment and profile."""
import os
from pathlib import Path
import sys

if len(sys.argv) != 2 or sys.argv[1] not in ("analytics", "ads"):
    raise SystemExit("Expected analytics or ads")
base = Path.home() / ".config" / "flai-google"
python = base / "venv" / "bin" / "python"
profile = base / "profile.json"
if not python.is_file() or not profile.is_file():
    raise SystemExit("Setup required: see the FlaiData Google plugin installation guide")
launcher = Path(__file__).resolve().parent / "integrations" / "launch.py"
os.execv(str(python), [str(python), str(launcher), "--server", sys.argv[1], "--profile", str(profile)])
