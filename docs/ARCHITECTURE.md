# System Architecture

## Overview

The application follows a layered architecture so the user interface, business logic, database access code, and physical data stores remain clearly separated.

![System Architecture](System_Architecture.svg)

## Presentation layer

The Flask web interface exposes the application workflows:

- card catalogue search and filtering
- card detail
- collection management
- wishlist management
- trade matching
- trade creation and completion
- analytics

The presentation layer does not directly query either database. Requests are routed through the application services.

## Application and business logic layer

### Card Catalogue Service

Coordinates catalogue search and card-detail retrieval. Structured catalogue attributes come from MariaDB, while nested attacks, abilities, weaknesses, resistances, and legalities can be retrieved from MongoDB.

### Collection and Wishlist Service

Handles CRUD operations for owned cards and wanted cards. Collection records track both total quantity and the subset currently available for trade.

### Trading Service

Implements the main relational workflow.

Trade completion is treated as one atomic operation:

1. lock the trade and participating collection rows
2. validate the current status
3. validate that each owner still has enough copies
4. validate that the requested quantity is still marked tradeable
5. subtract cards from the current owner
6. add cards to the receiving user
7. mark the trade as completed
8. commit all changes

If any step fails, the operation is rolled back.

### Analytics Service

Combines relational analytics with MongoDB aggregations. SQL is used for collection summaries and set completion. MongoDB is used for nested document analysis such as weakness distribution and attack-based queries.

## Database access layer

### Relational Service

The relational service uses PyMySQL to communicate with MariaDB. It contains CRUD functions, advanced joins, views, aggregate queries, and transaction logic.

### MongoDB Service

The MongoDB service uses PyMongo and exposes nested-field queries and aggregation pipelines.

## Data storage layer

### MariaDB

MariaDB stores strongly structured and transactional information:

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

This side of the application demonstrates relational integrity, normalised relationships, multi-table joins, constraints, indexes, views, and ACID transactions.

### MongoDB

MongoDB stores the variable nested parts of a card:

```text
abilities
attacks
weaknesses
resistances
retreat cost
legalities
rules
ancient traits
evolution targets
```

This structure supports operations that are naturally document-oriented, including nested keyword queries and aggregation pipelines using stages such as `$unwind`, `$group`, `$avg`, `$sort`, and `$project`.

## Data ingestion pipeline

The source CSV contains 17,172 card records and 29 source attributes.

The import pipeline performs two transformations from one source:

**Relational transformation**

- derives a stable `set_id`
- normalises sets, cards, and card types
- converts numeric/date attributes to appropriate SQL types
- preserves relational keys and constraints

**Document transformation**

- parses stringified arrays and objects
- creates one `card_details` document per card
- retains nested structures for attacks, abilities, weaknesses, legalities, and other optional fields
- creates indexes used by the document queries

This allows both database models to represent the same card catalogue according to their respective strengths.
