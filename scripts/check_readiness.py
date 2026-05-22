from __future__ import annotations

import json

from quant_robot.data.readiness import check_parquet_readiness, check_tushare_readiness


def main() -> None:
    print(json.dumps({"tushare": check_tushare_readiness(), "parquet": check_parquet_readiness()}, indent=2))


if __name__ == "__main__":
    main()
