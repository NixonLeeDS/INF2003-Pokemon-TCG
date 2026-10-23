from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.init_db import main as init_db
from scripts.import_data import main as import_data, DEFAULT_CSV
from scripts.seed_demo_data import main as seed_demo_data

def main():
    if not DEFAULT_CSV.is_file():
        raise SystemExit(f"Dataset missing: {DEFAULT_CSV}. No schema changes were made.")
    init_db()
    import_data()
    seed_demo_data()
    print("Bootstrap complete. Run: python app.py")


if __name__ == "__main__":
    main()
