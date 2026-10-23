USE inf2003_pokemon;

-- Q1: 5-table trade matching for user_id = 1
SELECT wi.user_id AS seeking_user_id, c.card_id, c.card_name, s.set_name,
       wi.priority, owner.user_id AS owner_id, owner.username AS owner_username,
       ci.trade_quantity
FROM wishlist_item wi
JOIN cards c ON c.card_id = wi.card_id
JOIN sets s ON s.set_id = c.set_id
JOIN collection_item ci ON ci.card_id = wi.card_id
 AND ci.trade_quantity > 0 AND ci.user_id <> wi.user_id
JOIN users owner ON owner.user_id = ci.user_id
WHERE wi.user_id = 1
ORDER BY wi.priority DESC, c.card_name, owner.username;

-- Q2: reciprocal trade matching
SELECT DISTINCT partner.user_id AS partner_id, partner.username AS partner_username,
       wanted.card_name AS you_want, offered.card_name AS they_want
FROM wishlist_item my_wish
JOIN collection_item partner_has ON partner_has.card_id = my_wish.card_id
 AND partner_has.trade_quantity > 0 AND partner_has.user_id <> my_wish.user_id
JOIN users partner ON partner.user_id = partner_has.user_id
JOIN cards wanted ON wanted.card_id = my_wish.card_id
JOIN wishlist_item partner_wish ON partner_wish.user_id = partner.user_id
JOIN collection_item i_have ON i_have.user_id = my_wish.user_id
 AND i_have.card_id = partner_wish.card_id AND i_have.trade_quantity > 0
JOIN cards offered ON offered.card_id = partner_wish.card_id
WHERE my_wish.user_id = 1
ORDER BY partner.username, wanted.card_name, offered.card_name;

-- Q3: set-completion analysis
SELECT s.set_id, s.set_name,
       COUNT(DISTINCT owned.card_id) AS owned_unique,
       COUNT(DISTINCT all_cards.card_id) AS set_total,
       ROUND(100.0 * COUNT(DISTINCT owned.card_id) /
             NULLIF(COUNT(DISTINCT all_cards.card_id), 0), 2) AS completion_pct
FROM sets s
JOIN cards all_cards ON all_cards.set_id = s.set_id
LEFT JOIN (
    SELECT ci.card_id
    FROM collection_item ci
    WHERE ci.user_id = 1 AND ci.quantity > 0
) owned ON owned.card_id = all_cards.card_id
GROUP BY s.set_id, s.set_name
HAVING owned_unique > 0
ORDER BY completion_pct DESC, s.set_name;

SELECT * FROM user_collection_summary ORDER BY total_cards DESC;

EXPLAIN
SELECT c.card_name, owner.username
FROM wishlist_item wi
JOIN cards c ON c.card_id = wi.card_id
JOIN collection_item ci ON ci.card_id = wi.card_id AND ci.trade_quantity > 0
JOIN users owner ON owner.user_id = ci.user_id
WHERE wi.user_id = 1 AND ci.user_id <> wi.user_id;
