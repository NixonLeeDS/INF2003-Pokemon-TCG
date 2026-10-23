# Final submission evidence checklist

Status: evidence below must be collected against the actual imported database.
Do not treat mock-based test success as a live integration or performance result.

## Reproduce

- [ ] Set `.env`, start MariaDB and MongoDB, import the documented dataset.
- [ ] Run `python -m scripts.verify_setup`; record server versions and card counts.
- [ ] Run `python -m scripts.seed_demo_data` on a disposable demo instance. Record
      the printed user IDs and offered card pair. Reseeding overwrites demo quantities.
- [ ] Run `python -m unittest discover -s tests -v` and retain output.

## Transaction demonstration

- [ ] Screenshot both collections before a trade, including tradeable quantities.
- [ ] Create using the seed's printed pair, accept as recipient, complete as either.
- [ ] Screenshot both collections afterward: outgoing decreases, incoming increases,
      received copies are not newly tradeable; status is COMPLETED.
- [ ] Repeat completion via POST; verify rejection and unchanged balances.
- [ ] Create two accepted offers competing for one tradeable copy. Complete them
      concurrently in separate sessions. Verify at most one succeeds, nonnegative
      balances, one completed status and conservation of total copies per card.
- [ ] Reduce offered stock before completing; verify failure leaves both collections
      and the trade status unchanged. Cancel the stale offer as requester.
- [ ] Reject wrong actors, negative/zero quantities, duplicate lines and self-trades.

## SQL plans and MongoDB evidence

Run `python -m scripts.explain_queries --user-id <seed-user-id>` and retain output.
Record MariaDB version, SQL mode, dataset size, chosen keys, access type, estimated
rows and actual returned rows. Compare prefix (`Pika%`) with contains (`%Pika%`)
search; a leading wildcard generally prevents a B-tree range lookup. Do not claim
an index speedup merely because an index exists. The matching plan demonstrates
wishlist/collection keys; reciprocal matching and set completion use the same
SQL as the application.
Small seeded tables may rationally use scans. Do not fabricate timings.

Run `mongosh "mongodb://127.0.0.1:27017/inf2003_pokemon" --file scripts/mongo_evidence.js`.
Record index inventory, unwind/group results and executionStats (winning plan,
keys/documents examined, returned count). Type aggregation counts a multi-type card
once in each type; weakness counts deduplicate each card's weakness types. Damage
analytics extract the first numeric component of damage strings, not guaranteed
battle damage (e.g. conditional multipliers are not evaluated).

## Screenshot slots

Save real screenshots under `docs/screenshots/` before replacing these slots with
image links. Keep credentials and local environment values out of screenshots.

| Filename to capture | Evidence |
| --- | --- |
| 01-status.png | Both databases connected, populated counts |
| 02-catalogue.png | Combined filters and card detail |
| 03-matches.png | Reciprocal match from deterministic seed |
| 04-trade-before.png | Quantities before completion |
| 05-trade-after.png | Completed state and changed balances |
| 06-validation.png | Friendly rejected input or stale offer |
| 07-analytics.png | SQL summary and nested Mongo aggregations |
| 08-query-plans.png | Actual SQL/Mongo plan evidence |
| 09-sql-demo.png | Actual matching, completion and unavailable-wishlist results |

- [ ] Check architecture and ERD still describe Flask + MariaDB + MongoDB and eight entities.
- [ ] Review README setup on a fresh environment; bootstrap is destructive.
- [ ] Confirm `.env` and private keys are ignored and absent from tracked files.
- [ ] Replace screenshot slots only after capturing evidence; no fabricated screenshots.
