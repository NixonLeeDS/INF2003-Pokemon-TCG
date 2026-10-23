# Prof Lam fast review

> The project direction is strong.
>
> Implement the collection/trading workflow early because it exercises the most meaningful relational relationships and transaction rules.
>
> For MongoDB, ensure the nested card structure leads to useful queries or aggregations rather than merely serving as secondary card-detail storage.

## How the implementation responds

### Relational

- Collection CRUD
- Wishlist CRUD
- 5-table trade matching
- Reciprocal trade matching
- Trades and trade items
- Atomic trade completion with row locks, validation, COMMIT/ROLLBACK

### MongoDB

- Nested keyword search in attacks/abilities
- High-damage attack query
- Weakness distribution aggregation
- Legality aggregation
- Average attack count by type
