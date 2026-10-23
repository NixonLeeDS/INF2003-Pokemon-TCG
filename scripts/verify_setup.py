from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db import mongo_database, mysql_connection


def main():
    conn = mysql_connection()
    try:
        with conn.cursor() as cur:
            for table in ["sets", "cards", "card_type", "users", "collection_item", "wishlist_item", "trades", "trade_item"]:
                cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
                print(f"MariaDB {table:18s}: {cur.fetchone()['n']}")
            cur.execute("SELECT * FROM user_collection_summary ORDER BY user_id")
            print("\nCollection summary:")
            for row in cur.fetchall():
                print(row)
    finally:
        conn.close()

    client, db = mongo_database()
    try:
        print(f"\nMongoDB card_details       : {db.card_details.count_documents({})}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
