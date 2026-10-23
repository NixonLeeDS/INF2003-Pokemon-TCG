# INF2003 Pokémon TCG Collection and Trading Management System

Team 40 starter implementation for INF2003 Database Systems.

## What is already scaffolded

- **MariaDB relational model:** `users`, `sets`, `cards`, `card_type`, `collection_item`, `wishlist_item`, `trades`, `trade_item`
- PK/FK, UNIQUE and CHECK constraints
- `user_collection_summary` SQL view and useful indexes
- Full importer for the supplied **17,172-row / 29-column** Pokémon TCG CSV
- MongoDB `card_details` documents containing nested attacks, abilities, weaknesses, resistances, legality and rules
- Deterministic synthetic demo users/collections/wishlists so trade matching returns results
- 5-table wishlist-to-trade matching query
- Reciprocal trade matching query
- Atomic trade completion using SQL transactions, row locking, validation and rollback
- Flask demo UI for cards, collections, wishlists, trade matches, trades and analytics
- MongoDB nested keyword query, high-damage attack query, weakness aggregation, legality aggregation and average-attack-count aggregation

## 1. Prerequisites

Install:

- Python 3.11+
- MariaDB Server
- MongoDB Community Server

The course uses MariaDB for SQL work, so this repo stays with MariaDB rather than introducing another relational DBMS.

## 2. Dataset

Download **Pokemon TCG All Cards 1999-2023** from Kaggle and place the CSV at:

```text
data/pokemon-tcg-data-master 1999-2023.csv
```

The CSV is intentionally not versioned in this repository. The importer expects the 17,172-row, 29-column dataset used for this project.

## 3. Create Python environment

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set your MariaDB password.

Recommended default database names:

- MariaDB: `inf2003_pokemon`
- MongoDB: `inf2003_pokemon`

## 4. Bootstrap everything

Make sure MariaDB and MongoDB are running, then from the repository root:

```bash
python -m scripts.bootstrap
```

This recreates the MariaDB schema, imports the Pokémon catalogue into both databases, creates indexes, creates demo users, and seeds collection/wishlist overlap for trade-matching demonstrations.

> `bootstrap` recreates the project tables. Do not use it after you start keeping important manually-entered demo data unless you intend to reset the database.

## 5. Verify row counts

```bash
python -m scripts.verify_setup
```

Expected headline result:

```text
MariaDB cards             : 17172
MongoDB card_details      : 17172
```

## 6. Run the Flask app

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

## Important demo workflows

### Relational workflow

1. Open **Collection** and choose a user.
2. Add/update cards and mark some copies as tradeable.
3. Open **Wishlist** and add wanted cards.
4. Open **Trade Matches** to demonstrate the 5-table JOIN.
5. Open **Trades**, create a trade and complete it.
6. Completion validates ownership/tradeable quantities and updates both users inside one transaction.

### MongoDB workflow

Open **Analytics** to demonstrate that MongoDB is not just secondary card-detail storage:

- nested attack/ability keyword search
- attacks with numeric damage above a threshold
- weakness distribution using `$unwind` + `$group`
- legality aggregation
- average number of attacks by Pokémon type

This directly addresses Prof Lam's feedback that the nested structure should lead to useful MongoDB queries/aggregations.

## Repository structure

```text
INF2003-Pokemon-TCG/
├── app.py
├── config.py
├── db.py
├── requirements.txt
├── .env.example
├── schema/
├── scripts/
├── services/
├── templates/
├── static/
├── data/
└── docs/
```

## Next implementation targets

1. Run the bootstrap locally and fix any environment-specific connection issues.
2. Test the collection/wishlist workflow manually.
3. Demonstrate the 5-table trade match.
4. Test one successful and one failed/rolled-back trade completion.
5. Capture SQL query + output screenshots for the final report.
6. Capture Mongo aggregation + output screenshots.
7. Add `EXPLAIN` before/after an index for one performance comparison.
8. Improve UI only after the database workflows are stable.
