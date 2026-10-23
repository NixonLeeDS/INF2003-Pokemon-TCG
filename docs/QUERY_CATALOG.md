# Query Catalog

## R1. Wishlist-to-trade matching, 5 tables

**Question:** Which cards on User A's wishlist are currently available for trade from other users?

Tables:

1. `wishlist_item`
2. `cards`
3. `sets`
4. `collection_item`
5. `users`

Implemented as `services.relational.trade_matches(user_id)`.

## R2. Reciprocal trade matching

**Question:** Which users have at least one card User A wants while also wanting at least one tradeable card User A owns?

This self-joins the logical collection/wishlist relationships from both sides. Implemented as `reciprocal_trade_matches`.

## R3. Set completion

**Question:** What percentage of each set has a user collected?

Uses `sets`, `cards`, `collection_item`, aggregation, `COUNT(DISTINCT ...)`, `GROUP BY` and a subquery.

## R4. Collection summary view

`user_collection_summary` reports:

- unique cards
- total physical card count
- tradeable copies
- number of sets represented

## R5. Trade transaction

`complete_trade(trade_id)`:

1. locks the trade row
2. locks trade items
3. locks source collection rows
4. validates ownership and tradeable quantities
5. subtracts from each owner
6. adds to the opposite participant
7. marks trade `COMPLETED`
8. commits all changes, otherwise rolls back

## M1. Nested attack/ability keyword search

Searches `attacks.name`, `attacks.text`, `abilities.name` and `abilities.text`.

## M2. High damage nested attack query

Uses `$unwind`, `$regexFind`, numeric conversion, `$match`, `$sort` and `$limit`.

## M3. Weakness distribution

Uses:

```text
$unwind weaknesses
$group by weaknesses.type
$sort by card_count
```

## M4. Legality distribution

Groups documents by nested `legalities.standard` and `legalities.expanded` values.

## M5. Average attacks by type

Uses `$size`, `$unwind`, `$group` and `$avg` to compare nested attack density between Pokémon types.
