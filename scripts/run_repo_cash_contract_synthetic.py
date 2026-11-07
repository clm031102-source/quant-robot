"""Write one fixed artificial repo demonstration; accepts no input data path."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform

from quant_robot.research import repo_cash_contract as model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=False)
    fixture = model.synthetic_fixture()
    result = model.run_synthetic_contract(fixture)
    refs = {}
    for name, value in (("fixture.json", fixture), ("result.json", result)):
        data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
        with (out / name).open("xb") as handle:
            handle.write(data)
        refs[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    runtime = {"module_file": str(Path(model.__file__).resolve()),
               "module_sha256": hashlib.sha256(Path(model.__file__).read_bytes()).hexdigest(),
               "python": platform.python_version(), "source_nature": "artificial_only",
               "financial_studies": 0, "qualified": False, "real_forward": 0, "outputs": refs}
    with (out / "runtime.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(runtime, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"output_dir": str(out.resolve()), "source_nature": "artificial_only",
                      "module_file": runtime["module_file"], "qualified": False}))


if __name__ == "__main__":
    main()
