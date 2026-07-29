from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from quant_robot.factors.etf_delayed_nav_premium_innovation import (
    DIRECT_EXPOSURE_NAMES,
    FACTOR_NAME,
)
from quant_robot.ops.cn_etf_delayed_nav_premium_prescreen import (
    STAGE,
    summarize_cn_etf_delayed_nav_premium_prescreen,
)


class CnEtfDelayedNavPremiumPrescreenTests(unittest.TestCase):
    def test_wrapper_freezes_h1_h5_and_small_capital_cost_contract(self):
        with patch(
            "quant_robot.ops.cn_etf_delayed_nav_premium_prescreen."
            "summarize_cn_etf_dynamic_peer_dislocation_prescreen",
            return_value={"stage": STAGE, "status": "fixture"},
        ) as summarize:
            result = summarize_cn_etf_delayed_nav_premium_prescreen(
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
            )

        self.assertEqual(result["stage"], STAGE)
        kwargs = summarize.call_args.kwargs
        self.assertEqual(kwargs["candidate_name"], FACTOR_NAME)
        self.assertEqual(kwargs["direct_exposure_names"], DIRECT_EXPOSURE_NAMES)
        self.assertEqual(kwargs["horizons"], (1, 5))
        self.assertEqual(kwargs["primary_horizon"], 1)
        self.assertEqual(kwargs["diagnostic_horizon"], 5)
        self.assertEqual(kwargs["one_way_costs_bps"], (10.5, 26.6666666667, 60.0))
        self.assertEqual(kwargs["required_positive_net_spread_bps"], 10.5)
        self.assertEqual(kwargs["position_value_cny"], 1000.0)
        self.assertEqual(kwargs["max_one_way_participation_rate"], 0.01)


if __name__ == "__main__":
    unittest.main()
