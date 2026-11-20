"""Streaming Extended-JSON backup/restore, including BSON types. Run with service stopped."""
import gzip
import json
import os
import sys
from pathlib import Path
from bson import json_util
from dotenv import load_dotenv
from pymongo import MongoClient


def run(action, folder):
    load_dotenv(os.getenv("ENERGIEBOARD_ENV", "/etc/energieboard/energieboard.env"), override=True)
    folder = Path(folder)
    client = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=10000)
    database = client[os.getenv("DB_NAME", "energieboard")]
    client.admin.command("ping")
    try:
        if action == "backup":
            folder.mkdir(mode=0o700, parents=True, exist_ok=False)
            manifest = []
            for index, name in enumerate(sorted(database.list_collection_names())):
                filename = f"{index}.jsonl.gz"
                count = 0
                with gzip.open(folder / filename, "wt", encoding="utf-8") as output:
                    for doc in database[name].find({}):
                        output.write(json_util.dumps(doc) + "\n")
                        count += 1
                indexes = [dict(index) for index in database[name].list_indexes()]
                manifest.append({"name": name, "file": filename, "count": count, "indexes": indexes})
            (folder / "manifest.json").write_text(json_util.dumps(manifest), encoding="utf-8")
        elif action == "restore":
            manifest = json_util.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            # Verify every backup stream before altering the database.
            for item in manifest:
                path = folder / item["file"]
                if path.parent.resolve() != folder.resolve():
                    raise ValueError("Ungültiger Sicherungspfad")
                with gzip.open(path, "rt", encoding="utf-8") as source:
                    count = sum(1 for line in source if isinstance(json_util.loads(line), dict))
                if count != item["count"]:
                    raise ValueError("Unvollständige Sicherung")
            for name in database.list_collection_names():
                database[name].drop()
            for item in manifest:
                batch = []
                with gzip.open(folder / item["file"], "rt", encoding="utf-8") as source:
                    for line in source:
                        batch.append(json_util.loads(line))
                        if len(batch) >= 1000:
                            database[item["name"]].insert_many(batch)
                            batch = []
                if batch:
                    database[item["name"]].insert_many(batch)
                elif item["name"] not in database.list_collection_names():
                    database.create_collection(item["name"])
                for index in item.get("indexes", []):
                    if index["name"] != "_id_":
                        options = {k:v for k,v in index.items() if k not in ("v", "key", "ns")}
                        database[item["name"]].create_index(list(index["key"].items()), **options)
        else:
            raise ValueError("backup oder restore angeben")
    finally:
        client.close()


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
