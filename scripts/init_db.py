from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db import mysql_connection
from config import Config

SCHEMA = ROOT / "schema" / "create_schema.sql"


def split_sql(script: str):
    cleaned = []
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        cleaned.append(line)
    return [stmt.strip() for stmt in "\n".join(cleaned).split(";") if stmt.strip()]


def main():
    if Config.MARIADB_DATABASE != "inf2003_pokemon":
        raise ValueError("The schema targets inf2003_pokemon. Set MARIADB_DATABASE accordingly before initialising.")
    statements = split_sql(SCHEMA.read_text(encoding="utf-8"))
    conn = mysql_connection(with_database=False, autocommit=True)
    try:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
        print(f"Executed {len(statements)} schema statements from {SCHEMA.name}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
