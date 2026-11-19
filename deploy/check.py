"""Check the unpacked release and MongoDB before starting the Linux service."""

import asyncio
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv("/etc/energieboard/energieboard.env", override=True)
load_dotenv(ROOT / "app/backend/.env")
sys.path.insert(0, str(ROOT / "app/backend"))

from lib.db import client, db, ensure_indexes  # noqa: E402


async def check() -> None:
    try:
        index = ROOT / "app/frontend/dist/index.html"
        html = index.read_text(encoding="utf-8")
        assets = re.findall(r'["\'](/assets/[^"\']+)["\']', html)
        if 'id="root"' not in html or not assets:
            raise RuntimeError("Die gebaute Oberfläche ist unvollständig.")
        for asset in assets:
            path = index.parent / asset.lstrip("/")
            if not path.is_file():
                raise RuntimeError(f"Frontend-Datei fehlt: {asset}")
        info = await client.admin.command("buildInfo")
        if info["versionArray"][0] < 5:
            raise RuntimeError("MongoDB ab Version 5.0 ist für die Historienberechnung erforderlich.")
        await db.command("ping")
        await ensure_indexes()
        print(f"Vorprüfung OK. Python {sys.version.split()[0]}, MongoDB {info['version']}, Oberfläche vollständig.")
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(check())
    except Exception as exc:
        print(f"Vorprüfung fehlgeschlagen: {exc}", file=sys.stderr)
        sys.exit(1)
