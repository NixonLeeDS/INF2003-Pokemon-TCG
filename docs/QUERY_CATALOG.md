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

`complete_trade(trade_id, actor_id)`:

1. locks the trade row
2. locks trade items
3. locks source and destination collection keys in stable order
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
$project distinct weakness types per card using $setUnion
$unwind weakness types
$group by type
$sort by card_count
```

## M4. Legality distribution

Groups documents by nested `legalities.standard` and `legalities.expanded` values.

## M5. Average attacks by type

Uses `$size`, `$unwind`, `$group` and `$avg` to compare nested attack density between Pokémon types.

## R6. Unavailable wishlist cards

**Question:** Which wanted cards have no supplier listing tradeable copies?

A correlated NOT EXISTS checks other users' stock. This appears on Trade Matches
so users can distinguish available cards from cards they cannot currently obtain.
Own stock and non-tradeable copies do not qualify as suppliers.

## Inspecting real application queries

Open **SQL Demo** (`/query-demo`) to inspect R1, R2, R3 and R6. Their SQL is defined
once in `services/query_demo.py` and executed by both the application services and
`python -m scripts.explain_queries --user-id <seed-user-id>`.

| Query | User decision | Why the relationships matter |
| --- | --- | --- |
| Supplier matching | Who should I approach for a wanted card? | Wishlist selects demand, collection checks tradeable stock, users identifies the supplier, cards and sets identify the exact printing. |
| Reciprocal matching | What can I offer that this supplier wants? | Both collection/wishlist directions must match the same partner. Card aliases label the two sides of a potential swap. |
| Set completion | Which sets am I close to completing? | All catalogue cards establish the denominator; owned distinct cards establish the numerator. Duplicate copies cannot inflate progress. |
| Unavailable wishes | Which wanted cards cannot be sourced here yet? | NOT EXISTS finds the absence of another user's tradeable stock without dropping wishlist cards that have no collection row. |

R1 uses five tables and four JOIN clauses. R2 uses seven table references but only
four distinct entities, because it examines both participants' relationships.
These counts describe the implementation; they are not reasons for adding joins.

Collection-size rankings and a separate username join in a per-user set summary
are omitted because they do not improve the trading workflow. No CTE or window
function is required just to make a query appear advanced.

Live plans/results still require a populated MariaDB instance. Query semantics are
also checked with a small SQLite fixture; that does not prove MariaDB plans or
performance. Capture actual evidence using the submission checklist.
