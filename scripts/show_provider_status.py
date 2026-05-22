from __future__ import annotations

import json

from quant_robot.data.provider_status import build_provider_status


def main() -> None:
    print(json.dumps(build_provider_status(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
