import unittest

import pandas as pd

from quant_robot.data.alfred_monthly_vintages import parse_alfred_monthly_vintages


class AlfredMonthlyVintageTests(unittest.TestCase):
    def parse(self, body: str, **kwargs: object) -> pd.DataFrame:
        options = {
            "series_id": "TEST",
            "vintage_dates": ["2020-01-31", "2020-02-29"],
            "observation_start": "2019-12-01",
            "observation_end": "2020-02-01",
        }
        options.update(kwargs)
        return parse_alfred_monthly_vintages(body.encode("utf-8"), **options)

    def test_preserves_versions_blank_cells_and_omitted_months(self) -> None:
        result = self.parse(
            "observation_date,TEST_20200131,TEST_20200229\n"
            "2019-12-01,10,11\n2020-01-01,,0\n"
        )
        self.assertEqual(len(result), 6)
        first = result[result["vintage_date"].eq(pd.Timestamp("2020-01-31"))]
        later = result[result["vintage_date"].eq(pd.Timestamp("2020-02-29"))]
        self.assertEqual(first.iloc[0]["value"], 10)
        self.assertEqual(later.iloc[0]["value"], 11)
        self.assertTrue(pd.isna(first.iloc[1]["value"]))
        self.assertTrue(first.iloc[1]["observation_row_present"])
        self.assertEqual(later.iloc[1]["value"], 0)
        self.assertTrue(pd.isna(first.iloc[2]["value"]))
        self.assertFalse(first.iloc[2]["observation_row_present"])

    def test_accepts_bom_reordered_columns_and_rows_without_mixing_vintages(self) -> None:
        result = self.parse(
            "\ufeffobservation_date,TEST_20200229,TEST_20200131\r\n"
            "2020-01-01,2,\r\n2019-12-01,3,-1\r\n"
        )
        self.assertEqual(result.iloc[0]["value"], -1)
        self.assertTrue(pd.isna(result.iloc[1]["value"]))
        self.assertEqual(result.iloc[3]["value"], 3)

    def test_header_only_remains_missing_not_zero_or_certified_absence(self) -> None:
        result = self.parse("observation_date,TEST_20200131,TEST_20200229\n")
        self.assertEqual(len(result), 6)
        self.assertTrue(result["value"].isna().all())
        self.assertFalse(result["observation_row_present"].any())

    def test_rejects_missing_extra_duplicate_or_wrong_series_vintages(self) -> None:
        for header in (
            "observation_date,TEST_20200131",
            "observation_date,TEST_20200131,TEST_20200229,TEST_20200331",
            "observation_date,TEST_20200131,TEST_20200131",
            "observation_date,OTHER_20200131,OTHER_20200229",
        ):
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, "columns"):
                self.parse(header + "\n")

    def test_rejects_duplicate_out_of_scope_and_non_monthly_observations(self) -> None:
        for body in (
            "2019-12-01,1,2\n2019-12-01,3,4\n",
            "2019-11-01,1,2\n",
            "2020-03-01,,\n",
            "2020-01-02,1,2\n",
            "20200101,1,2\n",
        ):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.parse("observation_date,TEST_20200131,TEST_20200229\n" + body)

    def test_rejects_values_for_observation_months_after_their_vintage(self) -> None:
        with self.assertRaisesRegex(ValueError, "future observation"):
            self.parse("observation_date,TEST_20200131,TEST_20200229\n2020-02-01,1,2\n")

    def test_rejects_nonfinite_nonnumeric_and_unrecognized_missing_tokens(self) -> None:
        for value in ("inf", "-inf", "NaN", "NA", ".", "1e999", "unknown"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "numeric"):
                self.parse(
                    "observation_date,TEST_20200131,TEST_20200229\n"
                    f"2019-12-01,{value},2\n"
                )

    def test_rejects_malformed_csv_row_width_or_quotes(self) -> None:
        for body in ("2019-12-01,1\n", "2019-12-01,1,2,3\n", '"2019-12-01,1,2\n'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.parse("observation_date,TEST_20200131,TEST_20200229\n" + body)

    def test_rejects_invalid_or_ambiguous_request_contract(self) -> None:
        for options in (
            {"vintage_dates": []},
            {"vintage_dates": ["2020-01-31", "2020-01-31"]},
            {"vintage_dates": "2020-01-31"},
            {"vintage_dates": ["20200131"]},
            {"observation_start": "2020-01-02"},
            {"observation_end": "2019-11-01"},
            {"series_id": ""},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.parse("observation_date,TEST_20200131,TEST_20200229\n", **options)

    def test_rejects_empty_or_non_utf8_input(self) -> None:
        with self.assertRaises(ValueError):
            self.parse("")
        with self.assertRaises(ValueError):
            parse_alfred_monthly_vintages(
                b"\xff", series_id="TEST", vintage_dates=["2020-01-31"],
                observation_start="2019-12-01", observation_end="2020-02-01",
            )


if __name__ == "__main__":
    unittest.main()
