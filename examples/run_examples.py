"""Check both exit codes and JSON reports for the documented commands."""

import json
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    checks = json.loads((root / "checks.json").read_bytes())
    for check in checks:
        command = [sys.executable, "-I", *check["args"]]
        result = subprocess.run(command, cwd=root, capture_output=True, timeout=15)
        if result.returncode != check["exit"] or result.stderr or json.loads(result.stdout) != check["report"]:
            raise SystemExit("Example failed " + check["args"][-1])
        print("PASS", check["args"][-1], "exit", result.returncode)


if __name__ == "__main__":
    main()
