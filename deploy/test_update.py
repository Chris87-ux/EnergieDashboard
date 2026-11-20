"""Fault-injection harness for update.sh. Isolated paths and mocked host commands.
Real tar, checksum, shell flow and app replacement; no host services are touched.
Set BASH_BIN on Windows. DB serialization is covered by integration_modular.py.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def unix(path):
    value = str(path).replace("\\", "/")
    return "/" + value[0].lower() + value[2:] if len(value)>1 and value[1]==":" else value


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    path.chmod(0o755)


def scenario(fail, corrupt=False):
    with tempfile.TemporaryDirectory(prefix="energieboard-update-") as name:
        folder=Path(name)
        for path in ("opt/energieboard/.venv/bin","etc/energieboard","etc/systemd/system","var/lock","tmp","mock","source"):
            folder.joinpath(path).mkdir(parents=True,exist_ok=True)
        write(folder/"database-state","original-data")
        write(folder/"opt/energieboard/old-version","original-app")
        write(folder/"etc/energieboard/energieboard.env","original-env")
        write(folder/"etc/systemd/system/energieboard.service","original-service")
        write(folder/"opt/energieboard/.venv/bin/python",'''#!/usr/bin/env bash
set -e
if [[ "$2" == backup ]]; then mkdir -p "$3"; cp "$TEST_SANDBOX/database-state" "$3/data";
elif [[ "$2" == restore ]]; then cp "$3/data" "$TEST_SANDBOX/database-state";
else exit 99; fi
''')
        archive=folder/"source/Energieboard-LXC.tar.gz"
        with tarfile.open(archive,"w:gz") as tar:
            for path,content in {
                "energieboard/deploy/install.sh":'''#!/usr/bin/env bash
set -e
echo migrated-data > "$TEST_SANDBOX/database-state"
echo new-service > "$TEST_SANDBOX/etc/systemd/system/energieboard.service"
echo new-app > "$TEST_SANDBOX/opt/energieboard/new-version"
if [[ "$TEST_FAIL" == yes ]]; then exit 42; fi
''',"energieboard/deploy/backup.py":"# The backup binary is a test fixture\n"}.items():
                payload=content.encode(); info=tarfile.TarInfo(path);info.size=len(payload);info.mode=0o755
                tar.addfile(info,io.BytesIO(payload))
        write(folder/"source/SHA256SUMS",hashlib.sha256(archive.read_bytes()).hexdigest()+"  Energieboard-LXC.tar.gz\n")
        if corrupt:
            write(folder/"source/SHA256SUMS","0"*64+"  Energieboard-LXC.tar.gz\n")
        write(folder/"source/commit.json",json.dumps({"sha":"a"*40}))
        write(folder/"mock/curl",'''#!/usr/bin/env bash
set -e
url="";output=""
while (( $# )); do
 case "$1" in -o) output="$2";shift 2;; --retry)shift 2;; http*)url="$1";shift;; *)shift;; esac
done
if [[ "$url" == *127.0.0.1* ]]; then exit 0; fi
file="${url##*/}"
if [[ "$url" == *api.github.com* ]]; then file=commit.json; fi
cp "$TEST_SANDBOX/source/$file" "$output"
''')
        write(folder/"mock/systemctl",'''#!/usr/bin/env bash
echo "$*" >> "$TEST_SANDBOX/systemctl.log"
''')
        write(folder/"mock/flock","#!/usr/bin/env bash\nexit 0\n")
        if os.name=="nt":
            write(folder/"mock/install",'''#!/usr/bin/env bash
set -e
if [[ "$1" == -d ]]; then shift 3; mkdir -p "$@";
else shift 2; cp "$@"; fi
''')
        # Git Bash has no Python3 command on some Windows hosts.
        if os.name=="nt":
            import sys
            write(folder/"mock/python3",f'#!/usr/bin/env bash\nexec "{unix(Path(sys.executable))}" "$@"\n')
        script=(ROOT/"deploy/update.sh").read_text(encoding="utf-8")
        script=script.replace("[[ $EUID == 0 ]]","[[ 1 == 1 ]]")
        for prefix in ("/opt","/etc","/var","/tmp"):
            script=script.replace(prefix,unix(folder)+prefix)
        script=script.replace("set -euo pipefail", 'set -euo pipefail\nexport PATH="$TEST_SANDBOX/mock:$PATH"\nhash -r', 1)
        write(folder/"update.sh",script)
        env={**os.environ,"TEST_SANDBOX":unix(folder),"TEST_FAIL":"yes" if fail else "no","PATH":str(folder/"mock")+os.pathsep+os.environ["PATH"]}
        result=subprocess.run([os.getenv("BASH_BIN","bash"),unix(folder/"update.sh")],env=env,capture_output=True,text=True,timeout=40)
        if corrupt:
            assert result.returncode!=0
            assert not (folder/"systemctl.log").exists()
            assert (folder/"database-state").read_text()=="original-data"
            assert (folder/"opt/energieboard/old-version").read_text()=="original-app"
        elif fail:
            assert result.returncode==42,(result.stdout,result.stderr,result.returncode)
            assert (folder/"database-state").read_text()=="original-data"
            assert (folder/"opt/energieboard/old-version").read_text()=="original-app"
            assert (folder/"etc/systemd/system/energieboard.service").read_text()=="original-service"
            assert "start energieboard.service" in (folder/"systemctl.log").read_text()
        else:
            assert result.returncode==0,(result.stdout,result.stderr)
            assert (folder/"opt/energieboard/INSTALLED_COMMIT").read_text().strip()=="a"*40
            assert (folder/"database-state").read_text().strip()=="migrated-data"
        assert (folder/"etc/energieboard/energieboard.env").read_text()=="original-env"
        print("Updater checksum rejection before service stop OK" if corrupt else "Updater rollback OK" if fail else "Updater successful replacement OK")


if __name__=="__main__":
    scenario(False)
    scenario(True)
    scenario(False, corrupt=True)
