import tempfile
import unittest
from pathlib import Path
import pandas as pd
from sector_momentum.factors import parse_french_rf, load_rf


class FactorTests(unittest.TestCase):
    def test_percent_rf_only_and_ignore_annual_rows(self):
        text = 'Supplier notes\n,Mkt-RF,SMB,HML,RF\n200001, -4.74,5.6,-1.91,0.41\n200002,2.45,20.02,-9.53,0.43\nAnnual Factors\n2000,-10,1,2,6\n'
        rf = parse_french_rf(text)
        self.assertEqual(len(rf), 2)
        self.assertAlmostEqual(rf.loc['2000-01-31'], .0041)
        self.assertAlmostEqual(rf.loc['2000-02-29'], .0043)

    def test_rf_requires_complete_requested_months(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rf.csv'
            path.write_text('date,rf\n2000-01-31,0.0041\n')
            with self.assertRaises(ValueError):
                load_rf(path, pd.date_range('2000-01-31', periods=2, freq='ME'))

    def test_duplicate_and_missing_monthly_rf_are_rejected(self):
        for text in ['200001,1,2,3,-99.99', '200001,1,2,3,.4\n200001,1,2,3,.4']:
            with self.assertRaises(ValueError):
                parse_french_rf(text)


if __name__ == '__main__':
    unittest.main()
