"""Database-independent rules shared by routes and services."""
import re


def integer(value, label, minimum=1, maximum=2147483647):
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)):
        raise ValueError(f"{label} must be a whole number.")
    result = int(value)
    if not minimum <= result <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return result


def card_identifier(value):
    value = (value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", value):
        raise ValueError("Enter a valid card ID (up to 48 letters, numbers, hyphens or underscores).")
    return value


def trade_items(items):
    if not items or len(items) > 100:
        raise ValueError("Each participant must offer 1 to 100 card lines.")
    result = [(card_identifier(card), integer(qty, "Quantity")) for card, qty in items]
    if len({card.casefold() for card, _ in result}) != len(result):
        raise ValueError("Combine duplicate card IDs into one quantity.")
    return result


def parse_trade_items(text):
    try:
        parts = [part.strip().rsplit(":", 1) for part in (text or "").split(",")]
        return trade_items([(card.strip(), qty.strip()) for card, qty in parts])
    except (TypeError, ValueError) as exc:
        raise ValueError("Use unique card_id:quantity entries, separated by commas, with positive quantities.") from exc


def transition(trade, status, actor_id):
    actor_id = integer(actor_id, "Acting user")
    requester, recipient = trade["requester_id"], trade["recipient_id"]
    rules = {
        "ACCEPTED": ({"PENDING"}, {recipient}),
        "REJECTED": ({"PENDING"}, {recipient}),
        "CANCELLED": ({"PENDING", "ACCEPTED"}, {requester}),
        "COMPLETED": ({"ACCEPTED"}, {requester, recipient}),
    }
    if status not in rules:
        raise ValueError("Unknown trade action.")
    states, actors = rules[status]
    if actor_id not in actors:
        raise ValueError("This user cannot perform that trade action.")
    if trade["status"] not in states:
        raise ValueError(f"Trade cannot change from {trade['status']} to {status}.")
