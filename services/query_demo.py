"""Fixed, parameterised, read-only queries for the database demonstration."""
from db import mysql_cursor
from services.validation import integer


QUERIES = {
    "collection_sets": {
        "title": "Collection by set — three JOINs",
        "question": "Which sets does this user own, and how many copies are tradeable?",
        "techniques": "Four tables, three INNER JOINs, GROUP BY, COUNT, SUM",
        "grain": "One row per user and set with positive owned stock. Card types are excluded to avoid multiplying multi-type cards.",
        "columns": ("username", "set_id", "set_name", "unique_cards", "owned_copies", "tradeable_copies"),
        "sql": """SELECT u.username, s.set_id, s.set_name,
       COUNT(*) AS unique_cards,
       SUM(ci.quantity) AS owned_copies,
       SUM(ci.trade_quantity) AS tradeable_copies
FROM users u
JOIN collection_item ci ON ci.user_id = u.user_id
JOIN cards c ON c.card_id = ci.card_id
JOIN sets s ON s.set_id = c.set_id
WHERE u.user_id = %s AND ci.quantity > 0
GROUP BY u.user_id, u.username, s.set_id, s.set_name
ORDER BY owned_copies DESC, s.set_id""",
    },
    "rank_sets": {
        "title": "Rank collected sets — CTE and window function",
        "question": "How do sets rank by the number of physical copies this user owns?",
        "techniques": "WITH, aggregation, DENSE_RANK() OVER, deterministic ordering",
        "grain": "One row per collected set. Equal copy totals share a rank, without gaps; the set ID breaks display ties only.",
        "columns": ("set_id", "set_name", "owned_copies", "set_rank"),
        "sql": """WITH set_totals AS (
    SELECT s.set_id, s.set_name, SUM(ci.quantity) AS owned_copies
    FROM collection_item ci
    JOIN cards c ON c.card_id = ci.card_id
    JOIN sets s ON s.set_id = c.set_id
    WHERE ci.user_id = %s AND ci.quantity > 0
    GROUP BY s.set_id, s.set_name
)
SELECT set_id, set_name, owned_copies,
       DENSE_RANK() OVER (ORDER BY owned_copies DESC) AS set_rank
FROM set_totals
ORDER BY set_rank, set_id""",
    },
    "unavailable_wishes": {
        "title": "Unavailable wishlist cards — correlated NOT EXISTS",
        "question": "Which wanted cards have no tradeable stock from any other user?",
        "techniques": "Three tables, two JOINs, correlated anti-subquery, NOT EXISTS",
        "grain": "One row per wishlist card. Your own stock cannot satisfy the availability test. Missing collection rows are handled naturally.",
        "columns": ("card_id", "card_name", "set_name", "priority"),
        "sql": """SELECT c.card_id, c.card_name, s.set_name, wi.priority
FROM wishlist_item wi
JOIN cards c ON c.card_id = wi.card_id
JOIN sets s ON s.set_id = c.set_id
WHERE wi.user_id = %s
  AND NOT EXISTS (
      SELECT 1 FROM collection_item ci
      WHERE ci.card_id = wi.card_id
        AND ci.user_id <> wi.user_id AND ci.trade_quantity > 0
  )
ORDER BY wi.priority DESC, c.card_id""",
    },
}


def run_query(key, user_id):
    if key not in QUERIES:
        raise ValueError("Choose a listed demonstration query.")
    user_id = integer(user_id, "User")
    with mysql_cursor() as (_, cur):
        cur.execute(QUERIES[key]["sql"], (user_id,))
        return cur.fetchall()
