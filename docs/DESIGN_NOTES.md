# Design Notes

## SQL / NoSQL split

### MariaDB

MariaDB is the system of record for strongly structured entities and transactional relationships:

- users
- sets
- cards
- card types
- collections
- wishlists
- trades
- trade items

This supports foreign keys, checks, joins and atomic trade operations.

### MongoDB

MongoDB stores variable/nested card structures that naturally vary between cards:

- abilities
- attacks and attack costs
- weaknesses/resistances
- retreat cost arrays
- legality object
- rules
- ancient traits
- evolution targets

The Mongo model is intentionally queried and aggregated rather than used only to render a detail page.

## Dataset transformation

Source CSV: 17,172 rows x 29 columns.

`set_id` is derived from the card ID prefix before the final hyphen. Example:

```text
base1-1 -> base1
sv4-266 -> sv4
```

This produces 157 stable set IDs. The source contains 156 unique display set names because `Shiny Vault` appears under two prefixes.
