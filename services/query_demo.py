"""Shared read-only queries used by application workflows, SQL inspection and plans."""
from db import mysql_cursor
from services.validation import integer


QUERIES = {
    "trade_matches": {
        "title": 'Find suppliers for wanted cards',
        "question": 'Who can currently supply cards on my wishlist?',
        "techniques": 'Wishlist-to-stock join with card, set and supplier details',
        "grain": 'One row per wanted card and supplier. Different suppliers are separate choices.',
        "columns": ('card_id', 'card_name', 'set_name', 'priority', 'owner_username', 'trade_quantity'),
        "sql": """SELECT
    wi.user_id AS seeking_user_id,
    c.card_id,
    c.card_name,
    s.set_name,
    wi.priority,
    owner.user_id AS owner_id,
    owner.username AS owner_username,
    ci.trade_quantity
FROM wishlist_item wi
JOIN cards c ON c.card_id = wi.card_id
JOIN sets s ON s.set_id = c.set_id
JOIN collection_item ci
  ON ci.card_id = wi.card_id
 AND ci.trade_quantity > 0
 AND ci.user_id <> wi.user_id
JOIN users owner ON owner.user_id = ci.user_id
WHERE wi.user_id = %s
ORDER BY wi.priority DESC, c.card_name, owner.username""",
    },
    "reciprocal_trade_matches": {
        "title": 'Find a mutually useful swap',
        "question": 'Who has something I want and wants something I can offer?',
        "techniques": 'Collection and wishlist relationships joined in both directions',
        "grain": 'One row per partner and possible card pair. Identical-card exchanges are excluded. These are candidate swaps, not agreed quantities or reserved stock.',
        "columns": ('partner_username', 'you_want_card_id', 'you_want', 'they_want_card_id', 'they_want'),
        "sql": """SELECT DISTINCT
    partner.user_id AS partner_id,
    partner.username AS partner_username,
    wanted.card_id AS you_want_card_id,
    wanted.card_name AS you_want,
    offered.card_id AS they_want_card_id,
    offered.card_name AS they_want
FROM wishlist_item my_wish
JOIN collection_item partner_has
  ON partner_has.card_id = my_wish.card_id
 AND partner_has.trade_quantity > 0
 AND partner_has.user_id <> my_wish.user_id
JOIN users partner ON partner.user_id = partner_has.user_id
JOIN cards wanted ON wanted.card_id = my_wish.card_id
JOIN wishlist_item partner_wish ON partner_wish.user_id = partner.user_id
JOIN collection_item i_have
  ON i_have.user_id = my_wish.user_id
 AND i_have.card_id = partner_wish.card_id
 AND i_have.trade_quantity > 0
 AND i_have.card_id <> my_wish.card_id
JOIN cards offered ON offered.card_id = partner_wish.card_id
WHERE my_wish.user_id = %s
ORDER BY partner.username, wanted.card_name, offered.card_name""",
    },
    "set_completion": {
        "title": 'Measure progress toward completing a set',
        "question": 'Of all catalogue cards in each set, how many different cards do I own?',
        "techniques": 'LEFT JOIN, derived table, COUNT(DISTINCT), GROUP BY, HAVING',
        "grain": 'One row per set with at least one owned card. Duplicate copies do not increase completion. The denominator is the imported catalogue for that set.',
        "columns": ('set_id', 'set_name', 'owned_unique', 'set_total', 'completion_pct'),
        "sql": """SELECT s.set_id, s.set_name,
       COUNT(DISTINCT owned.card_id) AS owned_unique,
       COUNT(DISTINCT all_cards.card_id) AS set_total,
       ROUND(100.0 * COUNT(DISTINCT owned.card_id) / NULLIF(COUNT(DISTINCT all_cards.card_id),0), 2) AS completion_pct
FROM sets s
JOIN cards all_cards ON all_cards.set_id=s.set_id
LEFT JOIN (
    SELECT ci.card_id
    FROM collection_item ci
    WHERE ci.user_id=%s AND ci.quantity>0
) owned ON owned.card_id=all_cards.card_id
GROUP BY s.set_id, s.set_name
HAVING owned_unique > 0
ORDER BY completion_pct DESC, s.set_name""",
    },
    "unavailable_wishes": {
        "title": 'Identify wishlist cards with no supplier',
        "question": 'Which wanted cards cannot currently be sourced through trading?',
        "techniques": 'Three tables, two JOINs, correlated anti-subquery, NOT EXISTS',
        "grain": 'One row per wishlist card. Your own stock cannot satisfy the availability test. Missing collection rows are handled naturally.',
        "columns": ('card_id', 'card_name', 'set_name', 'priority'),
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
        raise ValueError("Choose a listed application query.")
    user_id = integer(user_id, "User")
    with mysql_cursor() as (_, cur):
        cur.execute(QUERIES[key]["sql"], (user_id,))
        return cur.fetchall()
