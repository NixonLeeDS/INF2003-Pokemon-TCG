from __future__ import annotations

from db import mysql_connection, mysql_cursor
from services.query_demo import run_query
from services.validation import integer, card_identifier, trade_items, transition


def list_users():
    with mysql_cursor() as (_, cur):
        cur.execute("SELECT user_id, username FROM users ORDER BY username")
        return cur.fetchall()


def search_cards(name="", set_id="", card_type="", rarity="", min_hp=None, limit=100):
    sql = """
        SELECT DISTINCT c.card_id, c.card_name, c.card_number, c.hp, c.rarity,
               s.set_id, s.set_name,
               GROUP_CONCAT(DISTINCT ct.type ORDER BY ct.type SEPARATOR ', ') AS types
        FROM cards c
        JOIN sets s ON s.set_id = c.set_id
        LEFT JOIN card_type ct ON ct.card_id = c.card_id
        WHERE (%s = '' OR c.card_name LIKE CONCAT('%%', %s, '%%'))
          AND (%s = '' OR s.set_id = %s)
          AND (%s = '' OR EXISTS (
              SELECT 1 FROM card_type ct2 WHERE ct2.card_id = c.card_id AND ct2.type = %s
          ))
          AND (%s = '' OR c.rarity = %s)
          AND (%s IS NULL OR c.hp >= %s)
        GROUP BY c.card_id, c.card_name, c.card_number, c.hp, c.rarity, s.set_id, s.set_name
        ORDER BY c.card_name, s.release_date
        LIMIT %s
    """
    params = (name, name, set_id, set_id, card_type, card_type, rarity, rarity, min_hp, min_hp, int(limit))
    with mysql_cursor() as (_, cur):
        cur.execute(sql, params)
        return cur.fetchall()


def get_card(card_id):
    with mysql_cursor() as (_, cur):
        cur.execute(
            """
            SELECT c.*, s.set_name, s.series, s.publisher, s.generation, s.release_date,
                   (SELECT GROUP_CONCAT(ct.type ORDER BY ct.type SEPARATOR ', ')
                    FROM card_type ct WHERE ct.card_id=c.card_id) AS types
            FROM cards c
            JOIN sets s ON s.set_id = c.set_id
            WHERE c.card_id = %s
            """,
            (card_id,),
        )
        return cur.fetchone()


def list_filters():
    with mysql_cursor() as (_, cur):
        cur.execute("SELECT set_id, set_name FROM sets ORDER BY set_name")
        sets = cur.fetchall()
        cur.execute("SELECT DISTINCT type FROM card_type ORDER BY type")
        types = [r["type"] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT rarity FROM cards WHERE rarity IS NOT NULL ORDER BY rarity")
        rarities = [r["rarity"] for r in cur.fetchall()]
        return sets, types, rarities


def collection(user_id):
    with mysql_cursor() as (_, cur):
        cur.execute(
            """
            SELECT ci.user_id, ci.card_id, c.card_name, s.set_name, c.rarity,
                   ci.quantity, ci.trade_quantity, ci.added_at
            FROM collection_item ci
            JOIN cards c ON c.card_id = ci.card_id
            JOIN sets s ON s.set_id = c.set_id
            WHERE ci.user_id = %s
            ORDER BY c.card_name
            """,
            (user_id,),
        )
        return cur.fetchall()


def upsert_collection(user_id, card_id, quantity=1, trade_quantity=0):
    user_id = integer(user_id, "User")
    card_id = card_identifier(card_id)
    quantity = integer(quantity, "Owned quantity")
    trade_quantity = integer(trade_quantity, "Tradeable quantity", 0, quantity)
    with mysql_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO collection_item (user_id, card_id, quantity, trade_quantity)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity=VALUES(quantity), trade_quantity=VALUES(trade_quantity)
            """,
            (user_id, card_id, quantity, trade_quantity),
        )


def remove_collection(user_id, card_id):
    user_id = integer(user_id, "User")
    card_id = card_identifier(card_id)
    with mysql_cursor() as (_, cur):
        cur.execute("DELETE FROM collection_item WHERE user_id=%s AND card_id=%s", (user_id, card_id))


def wishlist(user_id):
    with mysql_cursor() as (_, cur):
        cur.execute(
            """
            SELECT wi.user_id, wi.card_id, c.card_name, s.set_name, c.rarity, wi.priority, wi.created_at
            FROM wishlist_item wi
            JOIN cards c ON c.card_id = wi.card_id
            JOIN sets s ON s.set_id = c.set_id
            WHERE wi.user_id = %s
            ORDER BY wi.priority DESC, c.card_name
            """,
            (user_id,),
        )
        return cur.fetchall()


def upsert_wishlist(user_id, card_id, priority=3):
    user_id = integer(user_id, "User")
    card_id = card_identifier(card_id)
    priority = integer(priority, "Priority", 1, 5)
    with mysql_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO wishlist_item (user_id, card_id, priority)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE priority=VALUES(priority)
            """,
            (user_id, card_id, priority),
        )


def remove_wishlist(user_id, card_id):
    user_id = integer(user_id, "User")
    card_id = card_identifier(card_id)
    with mysql_cursor() as (_, cur):
        cur.execute("DELETE FROM wishlist_item WHERE user_id=%s AND card_id=%s", (user_id, card_id))


def trade_matches(user_id):
    return run_query("trade_matches", user_id)


def reciprocal_trade_matches(user_id):
    return run_query("reciprocal_trade_matches", user_id)


def create_trade(requester_id, recipient_id, requester_items, recipient_items):
    requester_id = integer(requester_id, "Requester")
    recipient_id = integer(recipient_id, "Recipient")
    if requester_id == recipient_id:
        raise ValueError("Choose two different participants.")
    requester_items = trade_items(requester_items)
    recipient_items = trade_items(recipient_items)
    conn = mysql_connection(autocommit=False)
    try:
        with conn.cursor() as cur:
            for owner, card, qty in sorted(
                [(requester_id, c, q) for c, q in requester_items]
                + [(recipient_id, c, q) for c, q in recipient_items]
            ):
                cur.execute("SELECT quantity, trade_quantity FROM collection_item WHERE user_id=%s AND card_id=%s FOR UPDATE", (owner, card))
                source = cur.fetchone()
                if not source or min(source["quantity"], source["trade_quantity"]) < qty:
                    raise ValueError(f"User {owner} has insufficient tradeable copies of {card}.")
            cur.execute(
                "INSERT INTO trades (requester_id, recipient_id, status) VALUES (%s, %s, 'PENDING')",
                (requester_id, recipient_id),
            )
            trade_id = cur.lastrowid
            rows = []
            rows.extend((trade_id, card_id, requester_id, qty) for card_id, qty in requester_items)
            rows.extend((trade_id, card_id, recipient_id, qty) for card_id, qty in recipient_items)
            cur.executemany(
                "INSERT INTO trade_item (trade_id, card_id, owner_id, quantity) VALUES (%s, %s, %s, %s)",
                rows,
            )
        conn.commit()
        return trade_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_trades():
    with mysql_cursor() as (_, cur):
        cur.execute(
            """
            SELECT t.*, ru.username AS requester, pu.username AS recipient,
                   COALESCE(ti.item_lines, 0) AS item_lines
            FROM trades t
            JOIN users ru ON ru.user_id=t.requester_id
            JOIN users pu ON pu.user_id=t.recipient_id
            LEFT JOIN (SELECT trade_id, COUNT(*) AS item_lines FROM trade_item GROUP BY trade_id) ti
              ON ti.trade_id=t.trade_id
            ORDER BY t.created_at DESC
            """
        )
        return cur.fetchall()


def set_trade_status(trade_id, status, actor_id):
    trade_id = integer(trade_id, "Trade")
    conn = mysql_connection(autocommit=False)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM trades WHERE trade_id=%s FOR UPDATE", (trade_id,))
            trade = cur.fetchone()
            if not trade:
                raise ValueError("Trade not found.")
            transition(trade, status, actor_id)
            cur.execute("UPDATE trades SET status=%s WHERE trade_id=%s", (status, trade_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def complete_trade(trade_id, actor_id):
    trade_id = integer(trade_id, "Trade")
    conn = mysql_connection(autocommit=False)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM trades WHERE trade_id=%s FOR UPDATE", (trade_id,))
            trade = cur.fetchone()
            if not trade:
                raise ValueError("Trade not found")
            transition(trade, "COMPLETED", actor_id)

            cur.execute("SELECT * FROM trade_item WHERE trade_id=%s ORDER BY trade_item_id FOR UPDATE", (trade_id,))
            items = cur.fetchall()
            if not items:
                raise ValueError("Trade contains no items")

            participants = {trade["requester_id"], trade["recipient_id"]}
            if {item["owner_id"] for item in items} != participants:
                raise ValueError("Both participants must offer cards.")
            # Lock every existing source/destination in stable order before any writes.
            # Missing destination rows are protected by InnoDB insert/unique locks;
            # deadlocks are rolled back and may be retried by the user.
            locked = {}
            for user, card in sorted({(u, i["card_id"]) for u in participants for i in items}):
                cur.execute("SELECT quantity, trade_quantity FROM collection_item WHERE user_id=%s AND card_id=%s FOR UPDATE", (user, card))
                locked[user, card] = cur.fetchone()
            seen = set()
            for item in items:
                key = (item["owner_id"], item["card_id"])
                if key in seen or item["owner_id"] not in participants:
                    raise ValueError("Invalid or duplicate trade item owner/card.")
                seen.add(key)
                qty = integer(item["quantity"], "Quantity")
                source = locked[key]
                if not source or min(source["quantity"], source["trade_quantity"]) < qty:
                    raise ValueError("An offered card is no longer available. Update the collection or cancel this trade.")
            for item in items:
                owner = item["owner_id"]
                if owner not in participants:
                    raise ValueError("Trade item owner is not a participant")
                receiver = trade["recipient_id"] if owner == trade["requester_id"] else trade["requester_id"]

                cur.execute(
                    """
                    SELECT quantity, trade_quantity
                    FROM collection_item
                    WHERE user_id=%s AND card_id=%s
                    FOR UPDATE
                    """,
                    (owner, item["card_id"]),
                )
                source = cur.fetchone()
                if not source or source["quantity"] < item["quantity"] or source["trade_quantity"] < item["quantity"]:
                    raise ValueError(f"Owner {owner} no longer has enough tradeable copies of {item['card_id']}")

                cur.execute(
                    """
                    UPDATE collection_item
                    SET quantity=quantity-%s, trade_quantity=trade_quantity-%s
                    WHERE user_id=%s AND card_id=%s
                    """,
                    (item["quantity"], item["quantity"], owner, item["card_id"]),
                )
                cur.execute(
                    "DELETE FROM collection_item WHERE user_id=%s AND card_id=%s AND quantity=0",
                    (owner, item["card_id"]),
                )
                cur.execute(
                    """
                    INSERT INTO collection_item (user_id, card_id, quantity, trade_quantity)
                    VALUES (%s, %s, %s, 0)
                    ON DUPLICATE KEY UPDATE quantity=quantity+VALUES(quantity)
                    """,
                    (receiver, item["card_id"], item["quantity"]),
                )

            cur.execute("UPDATE trades SET status='COMPLETED' WHERE trade_id=%s", (trade_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def collection_summary():
    with mysql_cursor() as (_, cur):
        cur.execute("SELECT * FROM user_collection_summary ORDER BY total_cards DESC, username")
        return cur.fetchall()


def set_completion(user_id):
    return run_query("set_completion", user_id)


def unavailable_wishes(user_id):
    return run_query("unavailable_wishes", user_id)
