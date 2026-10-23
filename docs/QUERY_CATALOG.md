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

Uses `$size`, `$unwind`, `$group` and `$avg` to compare nested attack density between PokÃ©mon types.

## R6–R8. Interactive advanced SQL demonstration

Open **SQL Demo** (`/query-demo`). SQL is stored in `services/query_demo.py`;
the page and EXPLAIN script execute that same parameterised definition.

| ID | Query key | Evidence | Result grain |
| --- | --- | --- | --- |
| R6 | collection_sets | Four tables, exactly three JOINs, GROUP BY and SUM | One user/set |
| R7 | rank_sets | CTE, aggregation, DENSE_RANK window function | One collected set |
| R8 | unavailable_wishes | Correlated NOT EXISTS anti-subquery | One unavailable wishlist card |

Three JOINs usually connect four table references; a three-table join usually
uses two JOIN clauses. R1 exceeds both interpretations: five tables, four JOINs.
R2 uses seven table references (including repeated collection, wishlist and card
roles), rather than seven distinct entities. Describe both counts accurately.

R6 counts collection rows, which are unique on (user_id, card_id), so COUNT(*) is
the number of distinct owned cards within each set. Joining CARD_TYPE here would
multiply multi-type cards and inflate SUM(quantity), so it is deliberately absent.
R7 aggregates before ranking, ties share a rank, and the final set ID gives stable
display order. R8 excludes the selected user's own stock from potential suppliers.

Run `python -m scripts.explain_queries --user-id <seed-user-id>` to collect plans
and sample results for these exact SQL definitions. MariaDB 10.2+ supports the CTE
and window-function examples. Plans and result evidence must come from a running,
populated instance; no timings or output are precomputed in this repository.
