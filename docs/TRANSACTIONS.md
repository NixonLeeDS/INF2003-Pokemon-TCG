# Trade rules and transaction boundary

MariaDB remains the system of record. No additional entity is introduced.

| Current state | Action | Acting participant | Next state |
| --- | --- | --- | --- |
| PENDING | Accept | Recipient | ACCEPTED |
| PENDING | Reject | Recipient | REJECTED |
| PENDING or ACCEPTED | Cancel | Requester | CANCELLED |
| ACCEPTED | Complete | Either participant | COMPLETED |

All other transitions fail. Terminal states cannot be reopened or completed twice.
The acting user is explicitly selected for a localhost teaching demo, not authenticated.

Creation validates distinct users, both offers, positive integer quantities,
unique card IDs per owner, and currently tradeable stock before inserting the
header/items atomically. Offers do not reserve stock. Collection edits and other
trades can make an offer unavailable; acceptance is agreement, not a reservation.

Completion locks the trade header, item rows, and affected collection keys with
SELECT ... FOR UPDATE. Collection keys are acquired in sorted (user_id, card_id)
order. It checks both original offers before writes, subtracts outgoing stock and
tradeable stock, removes empty rows, credits received stock without marking new
copies tradeable, then marks the trade completed. All writes share one InnoDB
transaction. Any validation or database failure rolls it back and closes the
connection. A concurrent second completion waits on the header and then sees the
terminal state. Cancellation and acceptance lock the same header.

InnoDB may still select a deadlock victim, especially for missing destination rows
or concurrent collection CRUD. The exception path rolls back; retry the action
after refreshing. There is no automatic retry that could duplicate a submission.
Transactions cover MariaDB only. MongoDB card metadata is read-only during trades;
no cross-store atomicity is claimed. CSV imports into the two stores are separate
operations, so verify counts and IDs after import before demonstrating the app.

Collection updates replace quantities rather than incrementing them; quantity must
be positive and tradeable copies must be within owned copies. Use Remove to delete
a row. Wishlist priorities are 1–5. Foreign keys remain the final guard against
unknown users/cards. Database errors are logged server-side and translated to
friendly messages in the browser.
