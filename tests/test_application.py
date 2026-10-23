import unittest
from unittest.mock import MagicMock, patch
from services.validation import integer, parse_trade_items, transition
from services import relational as sql
from app import app


class ValidationTests(unittest.TestCase):
    def test_malformed_offers(self):
        for value in ('', 'a:0', 'a:-1', 'a:1,a:2', 'a:1,A:2', 'a', 'a:1,', ':2', 'a:1.2'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_trade_items(value)
        self.assertEqual(parse_trade_items(' base1-1:2, xy-2:1 '), [('base1-1', 2), ('xy-2', 1)])

    def test_integer_bounds(self):
        for value in (True, -1, '1.2', '2147483648', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                integer(value, 'Quantity')

    def test_transition_matrix(self):
        states = ('PENDING', 'ACCEPTED', 'REJECTED', 'CANCELLED', 'COMPLETED')
        allowed = {('PENDING', 'ACCEPTED', 2), ('PENDING', 'REJECTED', 2),
                   ('PENDING', 'CANCELLED', 1), ('ACCEPTED', 'CANCELLED', 1),
                   ('ACCEPTED', 'COMPLETED', 1), ('ACCEPTED', 'COMPLETED', 2)}
        for before in states:
            for after in states:
                for actor in (1, 2, 3):
                    trade = dict(status=before, requester_id=1, recipient_id=2)
                    with self.subTest(before=before, after=after, actor=actor):
                        if (before, after, actor) in allowed:
                            transition(trade, after, actor)
                        else:
                            with self.assertRaises(ValueError):
                                transition(trade, after, actor)

    @patch.object(sql, 'mysql_cursor')
    def test_invalid_crud_never_connects(self, cursor):
        for call in (lambda: sql.upsert_collection(1, 'a', 1, 2),
                     lambda: sql.upsert_collection(1, 'a', 0),
                     lambda: sql.upsert_wishlist(1, 'a', 6),
                     lambda: sql.remove_collection(0, 'a'),
                     lambda: sql.remove_wishlist(1, '')):
            with self.assertRaises(ValueError):
                call()
        cursor.assert_not_called()


class TransactionTests(unittest.TestCase):
    def connection(self, status='ACCEPTED'):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        trade = dict(status=status, requester_id=1, recipient_id=2)
        cur.fetchone.side_effect = [trade] + [dict(quantity=2, trade_quantity=1)] * 6
        cur.fetchall.return_value = [dict(owner_id=1, card_id='a', quantity=1), dict(owner_id=2, card_id='b', quantity=1)]
        return conn, cur

    def test_completion_commits_once_and_closes(self):
        conn, cur = self.connection()
        with patch.object(sql, 'mysql_connection', return_value=conn):
            sql.complete_trade(7, 2)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()
        self.assertTrue(any("status='COMPLETED'" in c.args[0] for c in cur.execute.call_args_list))

    def test_pending_cannot_complete(self):
        conn, _ = self.connection('PENDING')
        with patch.object(sql, 'mysql_connection', return_value=conn), self.assertRaises(ValueError):
            sql.complete_trade(7, 2)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    def test_shortage_rolls_back_before_inventory_writes(self):
        conn, cur = self.connection()
        cur.fetchone.side_effect = [dict(status='ACCEPTED', requester_id=1, recipient_id=2), None, None, None, None]
        with patch.object(sql, 'mysql_connection', return_value=conn), self.assertRaises(ValueError):
            sql.complete_trade(7, 2)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        self.assertFalse(any(c.args[0].strip().startswith(('UPDATE', 'INSERT', 'DELETE')) for c in cur.execute.call_args_list))

    def test_failure_after_first_debit_rolls_back(self):
        conn, cur = self.connection()
        def execute(statement, params=None):
            if statement.strip().startswith('INSERT INTO collection_item'):
                raise RuntimeError('simulated write failure')
        cur.execute.side_effect = execute
        with patch.object(sql, 'mysql_connection', return_value=conn), self.assertRaises(RuntimeError):
            sql.complete_trade(7, 1)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    def test_terminal_transition_rolls_back(self):
        conn, cur = self.connection('COMPLETED')
        with patch.object(sql, 'mysql_connection', return_value=conn), self.assertRaises(ValueError):
            sql.set_trade_status(7, 'ACCEPTED', 2)
        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()

    def test_self_trade_rejected_before_connect(self):
        with patch.object(sql, 'mysql_connection') as connect, self.assertRaises(ValueError):
            sql.create_trade(1, 1, [('a', 1)], [('b', 1)])
        connect.assert_not_called()


class WebTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY='test-secret')
        self.client = app.test_client()
        self.users = patch.object(sql, 'list_users', return_value=[])
        self.users.start()
        self.addCleanup(self.users.stop)

    def test_templates_compile(self):
        for name in app.jinja_env.list_templates():
            app.jinja_env.get_template(name)

    def test_csrf_required(self):
        with patch.object(sql, 'create_trade') as create:
            self.assertEqual(self.client.post('/trades', data={'action': 'create'}).status_code, 400)
            create.assert_not_called()

    def test_bad_user_has_friendly_error(self):
        response = self.client.get('/collection?user_id=oops')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'User must be a whole number', response.data)

    def test_unknown_action_never_writes(self):
        with self.client.session_transaction() as session:
            session['csrf_token'] = 'token'
        with patch.object(sql, 'upsert_collection') as update:
            response = self.client.post('/collection', data={'action': 'oops', 'csrf_token': 'token'})
            self.assertEqual(response.status_code, 302)
            update.assert_not_called()

    def test_trade_page_hides_terminal_actions(self):
        with patch.object(sql, 'list_trades', return_value=[dict(trade_id=1, status='COMPLETED', requester='a', recipient='b', item_lines=2)]):
            response = self.client.get('/trades')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'value="complete"', response.data)

    def test_database_errors_hide_internal_details(self):
        from pymysql import OperationalError
        with patch.object(sql, 'search_cards', side_effect=OperationalError('private-host-password')):
            with self.assertLogs(app.logger, level='ERROR'):
                response = self.client.get('/')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b'private-host-password', response.data)

    def test_status_checks_both_databases_when_down(self):
        from pymysql import OperationalError
        from pymongo.errors import ServerSelectionTimeoutError
        with patch('db.mysql_cursor', side_effect=OperationalError('offline')), patch('db.mongo_database', side_effect=ServerSelectionTimeoutError('offline')) as mongo:
            response = self.client.get('/health')
        self.assertEqual(response.status_code, 503)
        mongo.assert_called_once()
        self.assertIn(b'MongoDB', response.data)

    def test_missing_csv_does_not_drop_schema(self):
        from scripts import bootstrap
        with patch.object(bootstrap, 'DEFAULT_CSV') as path, patch.object(bootstrap, 'init_db') as init:
            path.is_file.return_value = False
            with self.assertRaises(SystemExit):
                bootstrap.main()
            init.assert_not_called()


if __name__ == '__main__':
    unittest.main()
