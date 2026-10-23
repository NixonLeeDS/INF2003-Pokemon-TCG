from __future__ import annotations

import re

from db import mongo_database


def card_detail(card_id):
    client, db = mongo_database()
    try:
        return db.card_details.find_one({"_id": card_id})
    finally:
        client.close()


def nested_keyword_search(keyword, limit=50):
    """Useful nested-text search across attack and ability content."""
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    client, db = mongo_database()
    try:
        cursor = db.card_details.find(
            {
                "$or": [
                    {"attacks.name": pattern},
                    {"attacks.text": pattern},
                    {"abilities.name": pattern},
                    {"abilities.text": pattern},
                ]
            },
            {"name": 1, "set_name": 1, "types": 1, "attacks": 1, "abilities": 1},
        ).limit(limit)
        return list(cursor)
    finally:
        client.close()


def cards_with_attack_damage_at_least(min_damage=100, card_type=None, limit=50):
    """Nested query using $expr to convert string damage values such as '120' where possible."""
    match = {"attacks": {"$ne": []}}
    if card_type:
        match["types"] = card_type
    pipeline = [
        {"$match": match},
        {"$unwind": "$attacks"},
        {"$addFields": {
            "damage_match": {
                "$regexFind": {"input": {"$ifNull": ["$attacks.damage", ""]}, "regex": "[0-9]+"}
            }
        }},
        {"$addFields": {
            "numeric_damage": {
                "$convert": {"input": "$damage_match.match", "to": "int", "onError": None, "onNull": None}
            }
        }},
        {"$match": {"numeric_damage": {"$gte": int(min_damage)}}},
        {"$project": {"name": 1, "set_name": 1, "types": 1, "attack": "$attacks", "numeric_damage": 1}},
        {"$sort": {"numeric_damage": -1, "name": 1}},
        {"$limit": int(limit)},
    ]
    client, db = mongo_database()
    try:
        return list(db.card_details.aggregate(pipeline))
    finally:
        client.close()


def weakness_distribution(limit=20):
    pipeline = [
        {"$project": {"weakness_types": {"$setUnion": [{"$ifNull": ["$weaknesses.type", []]}, []]}}},
        {"$unwind": "$weakness_types"},
        {"$group": {"_id": "$weakness_types", "card_count": {"$sum": 1}}},
        {"$sort": {"card_count": -1, "_id": 1}},
        {"$limit": int(limit)},
    ]
    client, db = mongo_database()
    try:
        return list(db.card_details.aggregate(pipeline))
    finally:
        client.close()


def legality_distribution():
    pipeline = [
        {"$project": {
            "standard": {"$ifNull": ["$legalities.standard", "Not specified"]},
            "expanded": {"$ifNull": ["$legalities.expanded", "Not specified"]},
        }},
        {"$group": {
            "_id": {"standard": "$standard", "expanded": "$expanded"},
            "card_count": {"$sum": 1},
        }},
        {"$sort": {"card_count": -1}},
    ]
    client, db = mongo_database()
    try:
        return list(db.card_details.aggregate(pipeline))
    finally:
        client.close()


def average_attack_count_by_type():
    pipeline = [
        {"$unwind": "$types"},
        {"$project": {"type": "$types", "attack_count": {"$size": {"$ifNull": ["$attacks", []]}}}},
        {"$group": {"_id": "$type", "avg_attacks": {"$avg": "$attack_count"}, "cards": {"$sum": 1}}},
        {"$sort": {"avg_attacks": -1, "cards": -1}},
    ]
    client, db = mongo_database()
    try:
        return list(db.card_details.aggregate(pipeline))
    finally:
        client.close()
