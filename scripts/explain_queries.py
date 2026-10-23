"""Read-only, reproducible SQL plan evidence. Run after importing data."""
import argparse
import json
from db import mysql_cursor
from services.query_demo import QUERIES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user-id', type=int, default=1)
    args = parser.parse_args()
    with mysql_cursor() as (_, cur):
        cur.execute('SELECT VERSION() AS version, @@sql_mode AS sql_mode')
        print(json.dumps(cur.fetchone(), default=str))
        cur.execute('SELECT COUNT(*) AS cards FROM cards')
        print(json.dumps(cur.fetchone()))
        queries = {
            'prefix_name': ("SELECT card_id, card_name FROM cards WHERE card_name LIKE %s", ('Pika%',)),
            'contains_name': ("SELECT card_id, card_name FROM cards WHERE card_name LIKE %s", ('%Pika%',)),
        }
        queries.update({key: (demo["sql"], (args.user_id,)) for key, demo in QUERIES.items()})
        for label, (query, params) in queries.items():
            cur.execute('EXPLAIN FORMAT=JSON ' + query, params)
            print('\n' + label)
            print(json.dumps(cur.fetchall(), indent=2, default=str))
            cur.execute(query, params)
            print('Sample rows:', json.dumps(cur.fetchmany(10), default=str))


if __name__ == '__main__':
    main()
