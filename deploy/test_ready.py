"""Readiness retry tests with mocked curl/systemctl, no host service changes."""
import os
from pathlib import Path
import subprocess
import tempfile
from test_update import unix,write

ROOT=Path(__file__).resolve().parent.parent


def scenario(always_fails=False):
    with tempfile.TemporaryDirectory(prefix="energieboard-ready-") as name:
        folder=Path(name)
        write(folder/"mock/curl",'''#!/usr/bin/env bash
count=0
if [[ -f "$TEST_SANDBOX/count" ]]; then read -r count < "$TEST_SANDBOX/count"; fi
count=$((count+1))
printf '%s\\n' "$count" > "$TEST_SANDBOX/count"
if [[ "$TEST_FAIL" == yes ]] || (( count < 3 )); then echo "curl: (7) connection refused" >&2; exit 7; fi
exit 0
''')
        write(folder/"mock/systemctl","#!/usr/bin/env bash\nexit 0\n")
        source=(ROOT/"deploy/wait_ready.sh").read_text(encoding="utf-8")
        source=source.replace("set -euo pipefail",'set -euo pipefail\nexport PATH="$TEST_SANDBOX/mock:$PATH"\nhash -r',1)
        write(folder/"ready.sh",source)
        result=subprocess.run([os.getenv("BASH_BIN","bash"),unix(folder/"ready.sh"),"4","0"],capture_output=True,text=True,
            env={**os.environ,"TEST_SANDBOX":unix(folder),"TEST_FAIL":"yes" if always_fails else "no"},timeout=15)
        if always_fails:
            assert result.returncode==1,(result.stdout,result.stderr)
            assert "Startfrist" in result.stderr and "curl: (7)" in result.stderr
        else:
            assert result.returncode==0,(result.stdout,result.stderr)
            assert not result.stderr,result.stderr
            assert (folder/"count").read_text().strip()=="3"
        print("Readiness timeout surfaces final error OK" if always_fails else "Readiness waits without transient curl noise OK")


if __name__=="__main__":
    scenario();scenario(True)
