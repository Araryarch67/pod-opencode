"""Verify pod-opencode runtime prerequisites. Usage: python scripts/check-env.py"""

import shutil
import subprocess
import sys


def main() -> int:
    ok = True
    print(f"python: {sys.version.split()[0]} (need >=3.10)")
    if sys.version_info < (3, 10):
        print("  FAIL: Python too old")
        ok = False
    java = shutil.which("java")
    print(f"java: {java or 'NOT FOUND'} (need JRE 8+)")
    if not java:
        ok = False
    else:
        r = subprocess.run(["java", "-version"], capture_output=True, text=True)
        print(
            "  " + (r.stderr.strip() or r.stdout.strip()).splitlines()[0]
            if (r.stderr or r.stdout)
            else "  (no version output)"
        )
    pod = shutil.which("pod-opencode")
    print(f"pod-opencode: {pod or 'NOT ON PATH'}")
    if not pod:
        print(
            "  hint: git clone https://github.com/Araryarch67/pod-opencode.git && cd pod-opencode && pip install -e ."
        )
        ok = False
    else:
        r = subprocess.run(["pod-opencode", "--help"], capture_output=True, text=True)
        print(f"  CLI responds: {r.returncode == 0}")
        ok = ok and r.returncode == 0
    print("OK" if ok else "MISSING PREREQUISITES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
