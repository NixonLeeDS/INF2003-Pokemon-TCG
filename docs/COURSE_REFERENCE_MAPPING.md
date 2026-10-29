# INF2003 Course Concepts Applied in the Project

This document maps the implemented Pokémon TCG system to the main database concepts covered in INF2003. It is intended as a project-design reference and final-report aid, not as a replacement for the original course materials.

## 1. Relational model and database design

The project separates structured data into eight relational entities:

```text
USERS
SETS
CARDS
CARD_TYPE
COLLECTION_ITEM
WISHLIST_ITEM
TRADES
TRADE_ITEM
```

Primary keys identify rows, foreign keys enforce valid relationships, and composite keys are used where a logical relationship is uniquely identified by more than one attribute.

The application architecture also separates the user-facing interface, application logic and data-storage layers.

## 2. ER modelling

The ER model captures:

- entities and key attributes;
- one-to-many relationships such as SETS → CARDS;
- user/card many-to-many relationships resolved through COLLECTION_ITEM and WISHLIST_ITEM;
- distinct requester and recipient roles for TRADES;
- card ownership within TRADE_ITEM.

Editable and rendered versions are stored in:

```text
docs/ERD.drawio
docs/ERD.svg
```

## 3. SQL and CRUD

The system demonstrates the four basic data operations:

- **CREATE:** adding collection, wishlist and trade records;
- **READ:** catalogue search, collection/wishlist views and analytics;
- **UPDATE:** quantity, tradeable quantity, priority and trade status;
- **DELETE:** removing collection/wishlist records.

The application also uses filtering, sorting, aliases, joins, grouping and aggregate functions.

## 4. Complex relational queries

### Five-table trade matching

The flagship relational query answers:

> Which cards on a user's wishlist are currently owned and marked tradeable by another user?

It joins:

```text
WISHLIST_ITEM
CARDS
SETS
COLLECTION_ITEM
USERS
```

### Reciprocal matching

A second query finds users for whom both sides have something the other wants. This reuses the collection and wishlist relationships from both participants' perspectives.

### Set completion

Set-completion analysis combines joins, a subquery, `COUNT(DISTINCT ...)`, `GROUP BY` and percentage calculation.

Examples are stored in `schema/demo_queries.sql`.

## 5. Database refinement and normalization

The schema separates catalogue metadata, user-owned quantities, wishlists and trades rather than repeating user/card/set information in one large table.

This reduces:

- update anomalies;
- insertion anomalies;
- deletion anomalies;
- repeated catalogue data.

Junction tables are used to represent many-to-many relationships cleanly.

## 6. Integrity constraints

The MariaDB schema includes:

- primary keys;
- foreign keys;
- unique usernames and email addresses;
- non-negative collection quantities;
- `trade_quantity <= quantity`;
- wishlist priority range checks;
- allowed trade-status values;
- different requester and recipient users;
- positive trade-item quantities.

These constraints complement application-level validation.

## 7. Indexing and query performance

Indexes are created for attributes used frequently in search, filtering and joins, including:

```text
cards(card_name)
cards(set_id)
cards(rarity)
collection_item(card_id, trade_quantity)
wishlist_item(card_id)
trades(status)
```

`schema/demo_queries.sql` includes an `EXPLAIN` example so query plans can be examined when demonstrating index use.

Indexes are selected for actual access patterns instead of being created indiscriminately, because indexes improve retrieval but also add storage and update overhead.

## 8. Transactions and concurrency

Trade completion is the main transaction use case.

The implementation:

1. starts a transaction;
2. locks the trade row;
3. locks the relevant trade-item and collection rows;
4. validates trade status and current quantities;
5. subtracts cards from each current owner;
6. adds cards to the receiving user;
7. marks the trade as completed;
8. commits if every operation succeeds;
9. rolls back if any validation or database operation fails.

This gives the project a concrete ACID-style workflow rather than treating transactions as a theoretical feature.

## 9. Raw-data ingestion

The source Pokémon TCG dataset contains 17,172 card records and 29 source attributes.

The import pipeline:

- reads the raw CSV with pandas;
- derives a stable set identifier;
- converts structured fields into relational rows;
- parses stringified nested fields;
- bulk-loads structured data into MariaDB;
- upserts nested card documents into MongoDB.

This mirrors the course workflow of moving raw file data into a database programmatically.

## 10. NoSQL extension

MongoDB is not used only as a secondary card-detail store.

The project performs useful operations on nested structures, including:

- attack/ability keyword search;
- high-damage attack search;
- weakness distribution;
- legality distribution;
- average number of attacks by Pokémon type.

The aggregation functions use operators such as:

```text
$unwind
$group
$avg
$sort
$project
```

This gives the non-relational half of the project its own meaningful query workload.

## Source-material handling

The original INF2003 lecture and lab files are kept outside the public Git repository because supplied course materials include SIT Restricted/Internal markings. A source-file index is maintained in `references/README.md`.
