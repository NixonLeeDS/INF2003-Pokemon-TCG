# INF2003 Course Reference Materials

This directory documents the INF2003 lecture and lab materials used as conceptual references for the project.

> **Source files are intentionally not committed to this public repository.**
>
> Several supplied course PDFs are labelled **SIT Restricted** or **SIT Internal**. To avoid redistributing restricted teaching material, the repository stores only a topic index and project mapping. Keep the original PDFs/notebooks in your local course-material folder.

## Lecture references

| Reference | Main topic | Project relevance |
|---|---|---|
| Lec01 | Database and relational model | Relations, schemas, keys, CRUD, DBMS architecture |
| Lec02 | ER diagram and SQL Part 1 | Conceptual/logical design, entities, attributes, relationships, cardinalities |
| Lec03 | SQL Part 2 | DML, SELECT, filtering, aliases, joins, ordering and query construction |
| Lec04 | Database refinement | Redundancy, anomalies, functional dependencies and normalization |
| Lec05 | Relational algebra and query optimization | Relational operators, joins and query-planning concepts |
| Lec06 | Indexing | Index selection and retrieval-performance considerations |
| Lec07 | Transactions and concurrency | ACID, COMMIT/ROLLBACK, concurrency and transaction safety |

## Lab references

| Reference | Main topic | Project relevance |
|---|---|---|
| Lab01 | Python-based database operations | Python/database integration and CRUD |
| Lab02 | SQL basics in MariaDB | MariaDB setup, users, tables and CRUD |
| Lab03 | Complex SQL queries | Multi-relation queries, referential integrity, conditions and UNION |
| Lab04 | Student notebook | Additional practical database exercises |
| Lab W08 | Data I/O and visualization | Importing raw data into a DB and analysing query results |
| Lab W09 | SQL transactions | Concurrent sessions, COMMIT, ROLLBACK and SAVEPOINT |

## Local source files

The original source materials used when preparing this mapping include:

- `INF2003 Lec01(1).pdf`
- `INF2003 Lec02(1).pdf`
- `INF2003 Lec03(2).pdf`
- `INF2003 Lec04(2).pdf`
- `INF2003  Lec05.pdf`
- `INF2003 AY2627 T1 Lec 06 261016(3).pdf`
- `INF2003 AY2627 T1 Lec 07 261021.pdf`
- `INF2003_lab01(1).pdf`
- `INF2003_Lab01_student (1)(1).ipynb`
- `INF2003Lab02(2).pdf`
- `INF2003Lab03(2).pdf`
- `INF2003_Lab04_student(2).ipynb`
- `INF2003 AY2627 T1 Lab W08 261016(1).pdf`
- `INF2003 AY2627T1 Lab W9 261021.pdf`

Two exact duplicate uploads were omitted from this list:
- duplicate Lec07 PDF
- duplicate Lab03 PDF

## Project-facing summary

The project intentionally applies the course material rather than merely storing it:

- the ERD uses consistent entity/relationship/cardinality notation;
- the relational schema uses primary keys, foreign keys and integrity constraints;
- collection and wishlist operations demonstrate CRUD;
- trade matching demonstrates multi-table joins;
- the schema is normalized to reduce redundancy;
- indexes support frequently filtered/joined columns;
- trade completion is executed as an atomic transaction with rollback on failure;
- MongoDB is used for nested card structures and aggregation workloads.
