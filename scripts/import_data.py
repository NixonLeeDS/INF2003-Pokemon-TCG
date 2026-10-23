from __future__ import annotations

import ast
from pathlib import Path
from typing import Any
import sys

import pandas as pd
from pymongo import ReplaceOne

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db import mongo_database, mysql_connection

DEFAULT_CSV = ROOT / "data" / "pokemon-tcg-data-master 1999-2023.csv"


def missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value)


def scalar(value: Any, default=None):
    if missing(value):
        return default
    return value


def integer(value: Any):
    if missing(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def text_number(value: Any):
    if missing(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def parse_nested(value: Any, default=None):
    if missing(value):
        return default
    if isinstance(value, (list, dict, int, float, bool)):
        return value
    text = str(value).strip()
    if not text:
        return default
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text


def set_id_from_card_id(card_id: str) -> str:
    return str(card_id).rsplit("-", 1)[0]


def clean_date(value: Any):
    if missing(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def import_mariadb(df: pd.DataFrame):
    conn = mysql_connection(autocommit=False)
    try:
        with conn.cursor() as cur:
            set_rows = {}
            card_rows = []
            type_rows = []

            for row in df.to_dict(orient="records"):
                card_id = str(row["id"])
                set_id = set_id_from_card_id(card_id)
                set_rows[set_id] = (
                    set_id,
                    scalar(row.get("set")),
                    scalar(row.get("series")),
                    scalar(row.get("publisher")),
                    scalar(row.get("generation")),
                    clean_date(row.get("release_date")),
                )

                subtypes = parse_nested(row.get("subtypes"), []) or []
                subtype_summary = ", ".join(map(str, subtypes)) if isinstance(subtypes, list) else str(subtypes)

                card_rows.append((
                    card_id,
                    set_id,
                    scalar(row.get("name")),
                    text_number(row.get("set_num")),
                    scalar(row.get("supertype")),
                    subtype_summary or None,
                    integer(row.get("level")),
                    integer(row.get("hp")),
                    scalar(row.get("rarity")),
                    scalar(row.get("artist")),
                    scalar(row.get("evolvesFrom")),
                    integer(row.get("convertedRetreatCost")),
                    scalar(row.get("flavorText")),
                    scalar(row.get("regulationMark")),
                ))

                types = parse_nested(row.get("types"), []) or []
                if isinstance(types, list):
                    type_rows.extend((card_id, str(t)) for t in types)

            cur.executemany(
                """
                INSERT INTO sets (set_id, set_name, series, publisher, generation, release_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    set_name=VALUES(set_name), series=VALUES(series), publisher=VALUES(publisher),
                    generation=VALUES(generation), release_date=VALUES(release_date)
                """,
                list(set_rows.values()),
            )

            card_sql = """
                INSERT INTO cards (
                    card_id, set_id, card_name, card_number, supertype, subtype_summary,
                    level, hp, rarity, artist, evolves_from, converted_retreat_cost,
                    flavor_text, regulation_mark
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    set_id=VALUES(set_id), card_name=VALUES(card_name), card_number=VALUES(card_number),
                    supertype=VALUES(supertype), subtype_summary=VALUES(subtype_summary), level=VALUES(level),
                    hp=VALUES(hp), rarity=VALUES(rarity), artist=VALUES(artist),
                    evolves_from=VALUES(evolves_from), converted_retreat_cost=VALUES(converted_retreat_cost),
                    flavor_text=VALUES(flavor_text), regulation_mark=VALUES(regulation_mark)
            """
            for start in range(0, len(card_rows), 1000):
                cur.executemany(card_sql, card_rows[start:start + 1000])

            cur.executemany(
                "INSERT IGNORE INTO card_type (card_id, type) VALUES (%s, %s)",
                type_rows,
            )
        conn.commit()
        print(f"MariaDB import complete: {len(set_rows)} sets, {len(card_rows)} cards, {len(type_rows)} card-type rows.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def import_mongodb(df: pd.DataFrame):
    client, db = mongo_database()
    try:
        cards = db.card_details
        operations = []
        total = 0
        for row in df.to_dict(orient="records"):
            card_id = str(row["id"])
            doc = {
                "_id": card_id,
                "card_id": card_id,
                "name": scalar(row.get("name")),
                "set_id": set_id_from_card_id(card_id),
                "set_name": scalar(row.get("set")),
                "series": scalar(row.get("series")),
                "types": parse_nested(row.get("types"), []) or [],
                "hp": integer(row.get("hp")),
                "abilities": parse_nested(row.get("abilities"), []) or [],
                "attacks": parse_nested(row.get("attacks"), []) or [],
                "weaknesses": parse_nested(row.get("weaknesses"), []) or [],
                "resistances": parse_nested(row.get("resistances"), []) or [],
                "retreat_cost": parse_nested(row.get("retreatCost"), []) or [],
                "legalities": parse_nested(row.get("legalities"), {}) or {},
                "rules": parse_nested(row.get("rules"), []) or [],
                "ancient_trait": parse_nested(row.get("ancientTrait"), None),
                "evolves_to": parse_nested(row.get("evolvesTo"), []) or [],
                "national_pokedex_numbers": parse_nested(row.get("nationalPokedexNumbers"), []) or [],
            }
            operations.append(ReplaceOne({"_id": card_id}, doc, upsert=True))
            total += 1
            if len(operations) >= 1000:
                cards.bulk_write(operations, ordered=False)
                operations.clear()
        if operations:
            cards.bulk_write(operations, ordered=False)

        cards.create_index("name")
        cards.create_index("set_id")
        cards.create_index("types")
        cards.create_index("weaknesses.type")
        cards.create_index("legalities.standard")
        cards.create_index("attacks.name")
        print(f"MongoDB import complete: {total} card_details documents.")
    finally:
        client.close()


def main(csv_path: Path = DEFAULT_CSV):
    print(f"Reading {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} rows x {len(df.columns)} columns.")
    import_mariadb(df)
    import_mongodb(df)


if __name__ == "__main__":
    main()
