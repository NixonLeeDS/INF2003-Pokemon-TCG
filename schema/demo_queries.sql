USE inf2003_pokemon;
-- Replace 1 with the user ID printed by the deterministic seed.
SET @demo_user_id = 1;

-- Find suppliers for wanted cards
-- Who can currently supply cards on my wishlist?
SELECT
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
WHERE wi.user_id = @demo_user_id
ORDER BY wi.priority DESC, c.card_name, owner.username;

-- Find a mutually useful swap
-- Who has something I want and wants something I can offer?
SELECT DISTINCT
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
WHERE my_wish.user_id = @demo_user_id
ORDER BY partner.username, wanted.card_name, offered.card_name;

-- Measure progress toward completing a set
-- Of all catalogue cards in each set, how many different cards do I own?
SELECT s.set_id, s.set_name,
       COUNT(DISTINCT owned.card_id) AS owned_unique,
       COUNT(DISTINCT all_cards.card_id) AS set_total,
       ROUND(100.0 * COUNT(DISTINCT owned.card_id) / NULLIF(COUNT(DISTINCT all_cards.card_id),0), 2) AS completion_pct
FROM sets s
JOIN cards all_cards ON all_cards.set_id=s.set_id
LEFT JOIN (
    SELECT ci.card_id
    FROM collection_item ci
    WHERE ci.user_id=@demo_user_id AND ci.quantity>0
) owned ON owned.card_id=all_cards.card_id
GROUP BY s.set_id, s.set_name
HAVING owned_unique > 0
ORDER BY completion_pct DESC, s.set_name;

-- Identify wishlist cards with no supplier
-- Which wanted cards cannot currently be sourced through trading?
SELECT c.card_id, c.card_name, s.set_name, wi.priority
FROM wishlist_item wi
JOIN cards c ON c.card_id = wi.card_id
JOIN sets s ON s.set_id = c.set_id
WHERE wi.user_id = @demo_user_id
  AND NOT EXISTS (
      SELECT 1 FROM collection_item ci
      WHERE ci.card_id = wi.card_id
        AND ci.user_id <> wi.user_id AND ci.trade_quantity > 0
  )
ORDER BY wi.priority DESC, c.card_id;

SELECT * FROM user_collection_summary ORDER BY total_cards DESC, username;

-- Inspect the same supplier-matching query executed by Trade Matches.
EXPLAIN FORMAT=JSON
SELECT
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
WHERE wi.user_id = @demo_user_id
ORDER BY wi.priority DESC, c.card_name, owner.username;
