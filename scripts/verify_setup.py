"""Read-only checks for catalogue agreement and relational invariants."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pymysql import MySQLError
from pymongo.errors import PyMongoError
from db import mongo_database, mysql_connection

TABLES = ('sets', 'cards', 'card_type', 'users', 'collection_item', 'wishlist_item', 'trades', 'trade_item')
INVARIANTS = {
    'invalid collection quantities': 'SELECT COUNT(*) AS n FROM collection_item WHERE quantity<0 OR trade_quantity<0 OR trade_quantity>quantity',
    'invalid wishlist priorities': 'SELECT COUNT(*) AS n FROM wishlist_item WHERE priority NOT BETWEEN 1 AND 5',
    'invalid trade participants': 'SELECT COUNT(*) AS n FROM trades WHERE requester_id=recipient_id',
    'trade items owned by outsiders': '''SELECT COUNT(*) AS n FROM trade_item ti JOIN trades t ON t.trade_id=ti.trade_id
        WHERE ti.owner_id NOT IN (t.requester_id, t.recipient_id)''',
    'trades missing a participant offer': '''SELECT COUNT(*) AS n FROM (
        SELECT t.trade_id FROM trades t LEFT JOIN trade_item ti ON ti.trade_id=t.trade_id
        GROUP BY t.trade_id HAVING COUNT(DISTINCT ti.owner_id) <> 2
    ) incomplete''',
}


def catalogue_problems(sql_ids, mongo_ids, expected_cards=None):
    problems = []
    if not sql_ids:
        problems.append('MariaDB catalogue is empty.')
    if not mongo_ids:
        problems.append('MongoDB catalogue is empty.')
    if expected_cards is not None and len(sql_ids) != expected_cards:
        problems.append(f'Expected {expected_cards} MariaDB cards; found {len(sql_ids)}.')
    for label, ids in (('Missing MongoDB documents', sql_ids - mongo_ids),
                       ('MongoDB documents without SQL cards', mongo_ids - sql_ids)):
        if ids:
            sample = ', '.join(sorted(map(str, ids))[:10])
            problems.append(f'{label}: {len(ids)} (sample: {sample})')
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-cards', type=int, help='Optional expected count for the chosen dataset')
    args = parser.parse_args(argv)
    if args.expected_cards is not None and args.expected_cards < 1:
        parser.error('--expected-cards must be positive')
    problems = []
    sql_ids = mongo_ids = None
    try:
        conn = mysql_connection()
        try:
            with conn.cursor() as cur:
                for table in TABLES:
                    cur.execute(f'SELECT COUNT(*) AS n FROM {table}')
                    print(f'MariaDB {table:18s}: {cur.fetchone()["n"]}')
                cur.execute('SELECT card_id FROM cards')
                sql_ids = {row['card_id'] for row in cur.fetchall()}
                for label, query in INVARIANTS.items():
                    cur.execute(query)
                    count = cur.fetchone()['n']
                    if count:
                        problems.append(f'{label}: {count}')
        finally:
            conn.close()
    except MySQLError:
        problems.append('MariaDB checks failed. Check the service, schema and .env configuration.')
    # Always check MongoDB even when MariaDB is unavailable.
    try:
        client, database = mongo_database()
        try:
            mongo_ids = {row['_id'] for row in database.card_details.find({}, {'_id': 1})}
            print(f'MongoDB card_details       : {len(mongo_ids)}')
        finally:
            client.close()
    except PyMongoError:
        problems.append('MongoDB checks failed. Check the service and .env configuration.')
    if sql_ids is not None and mongo_ids is not None:
        problems.extend(catalogue_problems(sql_ids, mongo_ids, args.expected_cards))
    for problem in problems:
        print('FAIL:', problem)
    print('Verification FAILED.' if problems else 'Verification passed: catalogues agree and checked invariants hold.')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
