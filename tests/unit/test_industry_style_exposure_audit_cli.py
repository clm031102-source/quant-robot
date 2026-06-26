import tempfile
import unittest
from pathlib import Path

from scripts.run_industry_style_exposure_audit import run_industry_style_exposure_audit_cli
from tests.unit.test_industry_style_exposure_audit import _sample_frames


class IndustryStyleExposureAuditCliTests(unittest.TestCase):
    def test_cli_reads_csv_inputs_and_writes_audit_packet(self) -> None:
        factors, labels, stock_basic, styles = _sample_frames(include_all_styles=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factors_path = root / "factors.csv"
            labels_path = root / "labels.csv"
            stock_basic_path = root / "stock_basic.csv"
            styles_path = root / "styles.csv"
            output_dir = root / "out"
            factors.to_csv(factors_path, index=False)
            labels.to_csv(labels_path, index=False)
            stock_basic.to_csv(stock_basic_path, index=False)
            styles.to_csv(styles_path, index=False)

            result = run_industry_style_exposure_audit_cli(
                factors_path=factors_path,
                labels_path=labels_path,
                stock_basic_path=stock_basic_path,
                style_factors_path=styles_path,
                output_dir=output_dir,
                min_dates=6,
                min_cross_section=12,
                min_residual_mean_ic=0.05,
                min_residual_ic_t_stat=1.0,
                min_residual_positive_rate=0.60,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_dir / "industry_style_exposure_audit.json").exists())
            self.assertTrue((output_dir / "factor_summary.csv").exists())


if __name__ == "__main__":
    unittest.main()
