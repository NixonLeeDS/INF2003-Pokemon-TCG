import unittest
import sqlite3
from unittest.mock import MagicMock, patch
from pymysql import OperationalError
from app import app
from services import query_demo


class QueryDemoTests(unittest.TestCase):
    def test_unknown_query_rejected_before_connection(self):
        with patch.object(query_demo, 'mysql_cursor') as connect:
            with self.assertRaises(ValueError):
                query_demo.run_query('DROP TABLE cards', 1)
            connect.assert_not_called()

    def test_user_parameter_cannot_be_sql(self):
        with patch.object(query_demo, 'mysql_cursor') as connect:
            with self.assertRaises(ValueError):
                query_demo.run_query('collection_sets', '1 OR 1=1')
            connect.assert_not_called()

    def test_query_passes_user_as_bound_parameter(self):
        context = MagicMock()
        cur = MagicMock()
        context.__enter__.return_value = (MagicMock(), cur)
        cur.fetchall.return_value = [{'set_id': 'base1', 'owned_copies': 3}]
        with patch.object(query_demo, 'mysql_cursor', return_value=context):
            rows = query_demo.run_query('collection_sets', '17')
        self.assertEqual(rows, [{'set_id': 'base1', 'owned_copies': 3}])
        self.assertEqual(cur.execute.call_args.args[1], (17,))

    def test_page_renders_all_examples_including_empty_results(self):
        app.config.update(TESTING=True)
        client = app.test_client()
        with patch('services.relational.list_users', return_value=[dict(user_id=17, username='Demo')]), patch.object(query_demo, 'run_query', return_value=[]) as run:
            for key in query_demo.QUERIES:
                response = client.get('/query-demo', query_string={'query': key, 'user_id': 17})
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'No matching rows', response.data)
                run.assert_called_with(key, 17)

    def test_bad_query_has_friendly_400(self):
        with patch('services.relational.list_users', return_value=[]), patch.object(query_demo, 'mysql_cursor') as connect:
            response = app.test_client().get('/query-demo?query=unknown')
        self.assertEqual(response.status_code, 400)
        connect.assert_not_called()

    def test_outage_is_503(self):
        with patch('services.relational.list_users', return_value=[]), patch.object(query_demo, 'mysql_cursor', side_effect=OperationalError('offline')):
            with self.assertLogs(app.logger, level='ERROR'):
                response = app.test_client().get('/query-demo')
        self.assertEqual(response.status_code, 503)


class QuerySemanticsTests(unittest.TestCase):
    """Exercise relational results with SQLite; MariaDB plans still need live QA."""
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE users (user_id INTEGER PRIMARY KEY, username TEXT);
            CREATE TABLE sets (set_id TEXT PRIMARY KEY, set_name TEXT);
            CREATE TABLE cards (card_id TEXT PRIMARY KEY, set_id TEXT, card_name TEXT);
            CREATE TABLE collection_item (user_id INTEGER, card_id TEXT, quantity INTEGER,
                trade_quantity INTEGER, PRIMARY KEY (user_id, card_id));
            CREATE TABLE wishlist_item (user_id INTEGER, card_id TEXT, priority INTEGER);
            INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob');
            INSERT INTO sets VALUES ('a', 'Same Name'), ('b', 'Same Name');
            INSERT INTO cards VALUES ('a1', 'a', 'One'), ('a2', 'a', 'Two'), ('b1', 'b', 'Three');
            INSERT INTO collection_item VALUES (1, 'a1', 2, 1), (1, 'a2', 1, 0),
                (1, 'b1', 3, 3), (2, 'a1', 5, 0), (2, 'a2', 1, 1);
            INSERT INTO wishlist_item VALUES (1, 'a1', 5), (1, 'a2', 4), (1, 'b1', 3);
        """)

    def run_example(self, key, user=1):
        sql = query_demo.QUERIES[key]['sql'].replace('%s', '?')
        return [dict(row) for row in self.db.execute(sql, (user,))]

    def test_three_joins_preserve_set_identity_and_copy_totals(self):
        rows = self.run_example('collection_sets')
        self.assertEqual([(r['set_id'], r['unique_cards'], r['owned_copies'], r['tradeable_copies']) for r in rows],
                         [('a', 2, 3, 1), ('b', 1, 3, 3)])
        self.assertEqual(self.run_example('collection_sets', 99), [])

    def test_rank_ties_and_next_rank(self):
        rows = self.run_example('rank_sets')
        self.assertEqual([r['set_rank'] for r in rows], [1, 1])
        self.db.execute("UPDATE collection_item SET quantity=4 WHERE user_id=1 AND card_id='b1'")
        rows = self.run_example('rank_sets')
        self.assertEqual([(r['set_id'], r['set_rank']) for r in rows], [('b', 1), ('a', 2)])

    def test_anti_query_excludes_own_stock_and_untradeable_stock(self):
        rows = self.run_example('unavailable_wishes')
        self.assertEqual([r['card_id'] for r in rows], ['a1', 'b1'])


if __name__ == '__main__':
    unittest.main()
