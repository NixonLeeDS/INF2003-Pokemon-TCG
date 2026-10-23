import unittest
from unittest.mock import MagicMock, patch
from io import StringIO
from pathlib import Path
import pandas as pd
from scripts import import_data as importer
from scripts import bootstrap, verify_setup


def dataset(**updates):
    row = dict(id='base1-1', name='Example', set='Base Set', types="['Fire']")
    row.update(updates)
    return pd.DataFrame([row])


class ImportValidationTests(unittest.TestCase):
    def test_nested_arrays_and_dicts_do_not_use_array_truth_values(self):
        self.assertFalse(importer.missing(['Fire', 'Water']))
        self.assertEqual(importer.parse_nested(['Fire'], []), ['Fire'])
        self.assertEqual(importer.parse_nested({'standard': 'Legal'}, {}), {'standard': 'Legal'})
        self.assertTrue(importer.missing(float('nan')))

    def test_json_and_python_nested_literals(self):
        self.assertEqual(importer.parse_nested('[{"name":"Draw"}]'), [{'name': 'Draw'}])
        self.assertEqual(importer.parse_nested("[{'name': 'Draw'}]"), [{'name': 'Draw'}])
        importer.validate_dataset(dataset(abilities=[{'name': 'Draw'}]))
        importer.validate_dataset(dataset(abilities='None', ancientTrait='null'))

    def test_invalid_import_file_never_opens_a_database(self):
        with patch.object(importer, 'load_dataset', side_effect=ValueError('invalid CSV')), patch.object(importer, 'mysql_connection') as sql, patch.object(importer, 'mongo_database') as mongo:
            with self.assertRaises(ValueError):
                importer.main(Path('invalid.csv'))
            sql.assert_not_called()
            mongo.assert_not_called()

    def test_rejects_malformed_or_wrong_shaped_fields(self):
        for update in ({'types': 'not valid'}, {'types': '{}'}, {'attacks': '["wrong"]'},
                       {'legalities': '[]'}, {'name': ''}, {'id': ' base1-1'}, {'id': 'missingprefix'}):
            with self.subTest(update=update), self.assertRaisesRegex(ValueError, 'CSV row 2'):
                importer.validate_dataset(dataset(**update))

    def test_duplicate_ids_match_database_case_insensitivity(self):
        df = pd.concat([dataset(), dataset(id='BASE1-1')], ignore_index=True)
        with self.assertRaisesRegex(ValueError, 'Duplicate card ID'):
            importer.validate_dataset(df)

    def test_empty_and_missing_columns(self):
        for df in (pd.DataFrame(), pd.DataFrame(columns=['id', 'name', 'set'])):
            with self.assertRaises(ValueError):
                importer.validate_dataset(df)

    def test_preserves_card_number_as_text(self):
        csv = StringIO(dataset(set_num='001').to_csv(index=False))
        loaded = importer.load_dataset(csv)
        self.assertEqual(loaded.iloc[0]['set_num'], '001')

    def test_invalid_csv_does_not_drop_schema(self):
        with patch.object(bootstrap, 'DEFAULT_CSV') as path, patch.object(bootstrap, 'load_dataset', side_effect=ValueError('invalid')), patch.object(bootstrap, 'init_db') as init:
            path.is_file.return_value = True
            with self.assertRaises(ValueError):
                bootstrap.main()
            init.assert_not_called()

    def test_reimport_replaces_types_in_same_transaction(self):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        with patch.object(importer, 'mysql_connection', return_value=conn):
            importer.import_mariadb(dataset(types='[]'))
        deletes = [call for call in cur.execute.call_args_list if call.args[0].startswith('DELETE FROM card_type')]
        self.assertEqual(deletes[0].args[1], ['base1-1'])
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()

    def test_type_update_failure_rolls_back_catalogue(self):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.execute.side_effect = RuntimeError('simulated failure')
        with patch.object(importer, 'mysql_connection', return_value=conn), self.assertRaises(RuntimeError):
            importer.import_mariadb(dataset())
        conn.commit.assert_not_called()
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()


class VerificationTests(unittest.TestCase):
    def test_equal_counts_can_still_have_wrong_ids(self):
        problems = verify_setup.catalogue_problems({'a', 'b'}, {'a', 'c'})
        self.assertEqual(len(problems), 2)
        self.assertIn('Missing MongoDB documents', problems[0])
        self.assertIn('without SQL cards', problems[1])

    def test_empty_catalogues_fail(self):
        self.assertTrue(verify_setup.catalogue_problems(set(), set()))

    def test_count_expectation_optional(self):
        self.assertEqual(verify_setup.catalogue_problems({'a'}, {'a'}), [])
        self.assertTrue(verify_setup.catalogue_problems({'a'}, {'a'}, 17172))

    def test_outage_returns_failure_and_still_checks_other_store(self):
        from pymysql import OperationalError
        from pymongo.errors import ServerSelectionTimeoutError
        with patch.object(verify_setup, 'mysql_connection', side_effect=OperationalError('offline')), patch.object(verify_setup, 'mongo_database', side_effect=ServerSelectionTimeoutError('offline')) as mongo:
            self.assertEqual(verify_setup.main([]), 1)
        mongo.assert_called_once()


if __name__ == '__main__':
    unittest.main()
