import tempfile
import unittest
from pathlib import Path
import app

class TrackerTests(unittest.TestCase):
    def test_database_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            original = app.DB
            app.DB = Path(directory) / 'test.db'
            try:
                app.initialize()
                item = dict(kind='expense', amount='125.50', category='Food', description='<Lunch>', day='2026-10-27')
                values = app.validate(item)
                self.assertEqual(values[1],12550)
                with app.connect() as db:
                    row_id = db.execute('INSERT INTO transactions(kind,amount,category,description,day) VALUES(?,?,?,?,?)',values).lastrowid
                    rows = db.execute('SELECT * FROM transactions').fetchall()
                    html = app.page(rows,'2026-10')
                    self.assertIn('&lt;Lunch&gt;',html)
                    self.assertIn('125.50',html)
                    db.execute('UPDATE transactions SET amount=? WHERE id=?',(15000,row_id))
                    self.assertEqual(db.execute('SELECT amount FROM transactions').fetchone()[0],15000)
                    db.execute('DELETE FROM transactions WHERE id=?',(row_id,))
                    self.assertEqual(db.execute('SELECT count(*) FROM transactions').fetchone()[0],0)
                for bad in ['0','-1','NaN','Infinity','1.001']:
                    with self.assertRaises(ValueError): app.validate(dict(item,amount=bad))
            finally:
                app.DB = original

if __name__ == '__main__':
    unittest.main()
