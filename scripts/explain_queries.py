"""Read-only, reproducible SQL plan evidence. Run after importing data."""
import argparse
import json
from db import mysql_cursor


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
            'trade_match': ("""SELECT wi.card_id, ci.user_id, ci.trade_quantity
                FROM wishlist_item wi JOIN collection_item ci
                ON ci.card_id=wi.card_id AND ci.trade_quantity>0 AND ci.user_id<>wi.user_id
                WHERE wi.user_id=%s""", (args.user_id,)),
            'rank_collections': ("""SELECT username, total_cards,
                DENSE_RANK() OVER (ORDER BY total_cards DESC) AS collection_rank
                FROM user_collection_summary ORDER BY collection_rank, username""", ()),
        }
        for label, (query, params) in queries.items():
            cur.execute('EXPLAIN FORMAT=JSON ' + query, params)
            print('\n' + label)
            print(json.dumps(cur.fetchall(), indent=2, default=str))
            cur.execute(query, params)
            print('Sample rows:', json.dumps(cur.fetchmany(10), default=str))


if __name__ == '__main__':
    main()
