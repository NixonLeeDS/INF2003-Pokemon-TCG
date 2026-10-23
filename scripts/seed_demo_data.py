from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db import mysql_connection

USERS = [
    ("nixon", "nixon@example.test"),
    ("brendan", "brendan@example.test"),
    ("wenjie", "wenjie@example.test"),
    ("hongming", "hongming@example.test"),
    ("jonathan", "jonathan@example.test"),
]


def main():
    conn = mysql_connection(autocommit=False)
    try:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT IGNORE INTO users (username, email) VALUES (%s, %s)",
                USERS,
            )
            names = [u[0] for u in USERS]
            placeholders = ",".join(["%s"] * len(names))
            cur.execute(f"SELECT user_id, username FROM users WHERE username IN ({placeholders})", names)
            users = {row["username"]: row["user_id"] for row in cur.fetchall()}

            cur.execute("SELECT card_id FROM cards ORDER BY card_id LIMIT 20")
            cards = [r["card_id"] for r in cur.fetchall()]
            if len(cards) < 12:
                raise RuntimeError("Import card data before running the demo seed script.")

            collections = [
                (users["nixon"], cards[0], 3, 2),
                (users["nixon"], cards[1], 2, 1),
                (users["nixon"], cards[2], 1, 0),
                (users["brendan"], cards[5], 3, 2),
                (users["brendan"], cards[6], 2, 1),
                (users["brendan"], cards[7], 1, 0),
                (users["wenjie"], cards[5], 2, 1),
                (users["wenjie"], cards[8], 4, 2),
                (users["hongming"], cards[9], 2, 1),
                (users["jonathan"], cards[10], 2, 2),
            ]
            cur.executemany(
                """
                INSERT INTO collection_item (user_id, card_id, quantity, trade_quantity)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE quantity=VALUES(quantity), trade_quantity=VALUES(trade_quantity)
                """,
                collections,
            )

            wishlists = [
                (users["nixon"], cards[5], 5),
                (users["nixon"], cards[8], 4),
                (users["brendan"], cards[0], 5),
                (users["brendan"], cards[2], 3),
                (users["wenjie"], cards[1], 4),
                (users["hongming"], cards[6], 4),
                (users["jonathan"], cards[0], 5),
            ]
            cur.executemany(
                """
                INSERT INTO wishlist_item (user_id, card_id, priority)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE priority=VALUES(priority)
                """,
                wishlists,
            )
        conn.commit()
        print(f"Demo trade: requester={users['nixon']}, recipient={users['brendan']}")
        print(f"Requester gives {cards[0]}:1; recipient gives {cards[5]}:1")
        print("Rerunning the seed overwrites these demo collection quantities; use a disposable database.")
        print("Seeded demo users, collections and wishlists with guaranteed trade-match overlap.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
