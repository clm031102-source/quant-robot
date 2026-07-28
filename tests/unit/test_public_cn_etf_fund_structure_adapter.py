from __future__ import annotations

import io
import json
import unittest

import pandas as pd

from quant_robot.data.adapters.public_cn_etf_fund_structure import (
    ProviderResponseError,
    parse_eastmoney_nav_javascript,
    parse_sse_share_response,
    parse_szse_share_workbook,
)


class PublicCnEtfFundStructureAdapterTests(unittest.TestCase):
    def test_parse_sse_share_response_normalizes_units_and_filters_requested_date(self) -> None:
        payload = {
            "result": [
                {
                    "NUM": "1",
                    "SEC_CODE": "510300",
                    "SEC_NAME": "沪深300ETF",
                    "ETF_TYPE": "单市",
                    "STAT_DATE": "2024-06-28",
                    "TOT_VOL": "123.45",
                },
                {
                    "NUM": "2",
                    "SEC_CODE": "not-a-code",
                    "SEC_NAME": "bad",
                    "ETF_TYPE": "单市",
                    "STAT_DATE": "2024-06-28",
                    "TOT_VOL": "99",
                },
            ]
        }

        frame = parse_sse_share_response(payload, requested_date="2024-06-28")

        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.loc[0, "symbol"], "510300.SH")
        self.assertEqual(frame.loc[0, "asset_id"], "CN_ETF_XSHG_510300")
        self.assertEqual(frame.loc[0, "exchange"], "SSE")
        self.assertAlmostEqual(frame.loc[0, "total_share"], 1_234_500.0)
        self.assertEqual(frame.loc[0, "share_source"], "sse_official_etf_scale")
        self.assertEqual(str(frame.loc[0, "date"]), "2024-06-28")

    def test_parse_sse_share_response_rejects_date_mismatch_and_duplicates(self) -> None:
        row = {
            "NUM": "1",
            "SEC_CODE": "510300",
            "SEC_NAME": "沪深300ETF",
            "ETF_TYPE": "单市",
            "STAT_DATE": "2024-06-27",
            "TOT_VOL": "123.45",
        }
        with self.assertRaisesRegex(ProviderResponseError, "requested date"):
            parse_sse_share_response({"result": [row]}, requested_date="2024-06-28")

        row["STAT_DATE"] = "2024-06-28"
        with self.assertRaisesRegex(ProviderResponseError, "duplicate"):
            parse_sse_share_response({"result": [row, dict(row)]}, requested_date="2024-06-28")

    def test_parse_szse_share_workbook_normalizes_rows(self) -> None:
        raw = pd.DataFrame(
            {
                "日期": ["2024-06-27", "2024-06-28", "footer"],
                "基金代码": [159919, 159919, "说明"],
                "基金简称": ["沪深300ETF", "沪深300ETF", "说明"],
                "基金规模(份)": ["1,234,500", "1,250,000", ""],
            }
        )
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            raw.to_excel(writer, index=False)

        frame = parse_szse_share_workbook(buffer.getvalue())

        self.assertEqual(len(frame), 2)
        self.assertEqual(frame["symbol"].unique().tolist(), ["159919.SZ"])
        self.assertEqual(frame["asset_id"].unique().tolist(), ["CN_ETF_XSHE_159919"])
        self.assertEqual(frame["exchange"].unique().tolist(), ["SZSE"])
        self.assertEqual(frame["total_share"].tolist(), [1_234_500.0, 1_250_000.0])
        self.assertEqual(frame["share_source"].unique().tolist(), ["szse_official_fund_scale"])

    def test_parse_szse_share_workbook_rejects_missing_schema_and_duplicates(self) -> None:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame({"wrong": [1]}).to_excel(writer, index=False)
        with self.assertRaisesRegex(ProviderResponseError, "schema"):
            parse_szse_share_workbook(buffer.getvalue())

        duplicate = pd.DataFrame(
            {
                "日期": ["2024-06-28", "2024-06-28"],
                "基金代码": [159919, 159919],
                "基金简称": ["a", "a"],
                "基金规模(份)": [1.0, 1.0],
            }
        )
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            duplicate.to_excel(writer, index=False)
        with self.assertRaisesRegex(ProviderResponseError, "duplicate"):
            parse_szse_share_workbook(buffer.getvalue())

    def test_parse_eastmoney_nav_javascript_uses_named_json_assignment(self) -> None:
        rows = [
            {"x": 1719504000000, "y": 3.4874, "equityReturn": 0.29, "unitMoney": ""},
            {"x": 1719417600000, "y": 3.4772, "equityReturn": -0.68, "unitMoney": ""},
            {"x": 1577750400000, "y": 1.0, "equityReturn": 0.0, "unitMoney": ""},
        ]
        javascript = (
            "var unrelated = 1;\n"
            f"var Data_netWorthTrend = {json.dumps(rows)};\n"
            "var Data_ACWorthTrend = [];\n"
        )

        frame = parse_eastmoney_nav_javascript(
            javascript,
            symbol="510300.SH",
            start_date="2024-06-27",
            end_date="2024-06-28",
        )

        self.assertEqual(len(frame), 2)
        self.assertEqual(frame["symbol"].unique().tolist(), ["510300.SH"])
        self.assertEqual(frame["asset_id"].unique().tolist(), ["CN_ETF_XSHG_510300"])
        self.assertEqual(frame["exchange"].unique().tolist(), ["SSE"])
        self.assertEqual(frame["nav"].tolist(), [3.4772, 3.4874])
        self.assertEqual(frame["nav_source"].unique().tolist(), ["eastmoney_fund_detail_history"])
        self.assertEqual([str(value) for value in frame["date"]], ["2024-06-27", "2024-06-28"])

    def test_parse_eastmoney_nav_javascript_rejects_missing_or_duplicate_values(self) -> None:
        with self.assertRaisesRegex(ProviderResponseError, "Data_netWorthTrend"):
            parse_eastmoney_nav_javascript(
                "var somethingElse = [];",
                symbol="510300.SH",
                start_date="2024-01-01",
                end_date="2024-06-28",
            )

        rows = [
            {"x": 1719504000000, "y": 3.4874},
            {"x": 1719504000000, "y": 3.4874},
        ]
        with self.assertRaisesRegex(ProviderResponseError, "duplicate"):
            parse_eastmoney_nav_javascript(
                f"var Data_netWorthTrend = {json.dumps(rows)};",
                symbol="510300.SH",
                start_date="2024-01-01",
                end_date="2024-06-28",
            )

    def test_parsers_retain_non_positive_numeric_observations_for_quality_gate(self) -> None:
        shares = parse_sse_share_response(
            {
                "result": [
                    {
                        "SEC_CODE": "510300",
                        "STAT_DATE": "2024-06-28",
                        "TOT_VOL": "0",
                    }
                ]
            },
            requested_date="2024-06-28",
        )
        self.assertEqual(shares["total_share"].tolist(), [0.0])

        nav = parse_eastmoney_nav_javascript(
            'var Data_netWorthTrend = [{"x": 1719504000000, "y": 0}];',
            symbol="510300.SH",
            start_date="2024-01-01",
            end_date="2024-06-28",
        )
        self.assertEqual(nav["nav"].tolist(), [0.0])


if __name__ == "__main__":
    unittest.main()
