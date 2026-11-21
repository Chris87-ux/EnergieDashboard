from pathlib import Path
import hashlib
import tarfile

root = Path(__file__).resolve().parent.parent
output = root / "outputs" / "Energieboard-LXC.tar.gz"
output.parent.mkdir(exist_ok=True)
excluded = {"node_modules", "__pycache__", ".venv", ".env"}
files = [root / name for name in ("README.md", "INSTALLATION.md", "PRUEFBERICHT.md", "DATENMODELL.md", "CHANGELOG.md", "CSV-IMPORT.md", "DOCKER.md", "Dockerfile", ".dockerignore", "compose.yaml", "compose.external.yaml", "docker.env.example", ".github/workflows/docker.yml", "VERSION")]
for folder in ("app", "deploy", "docs"):
    files.extend(path for path in (root / folder).rglob("*")
                 if path.is_file() and not path.name.startswith(".env") and not excluded.intersection(path.relative_to(root).parts))

with tarfile.open(output, "w:gz") as archive:
    directories = {parent for file in files for parent in file.relative_to(root).parents}
    for directory in sorted(directories, key=lambda path: (len(path.parts), path.as_posix())):
        name = "energieboard" if directory == Path(".") else "energieboard/" + directory.as_posix()
        info = tarfile.TarInfo(name)
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        info.uname = info.gname = "root"
        archive.addfile(info)
    for path in sorted(files):
        name = "energieboard/" + path.relative_to(root).as_posix()
        info = archive.gettarinfo(path, arcname=name)
        info.uid = info.gid = 0
        info.uname = info.gname = "root"
        info.mode = 0o755 if path.suffix == ".sh" else 0o644
        with path.open("rb") as content:
            archive.addfile(info, content)

with tarfile.open(output, "r:gz") as archive:
    for path in files:
        name = "energieboard/" + path.relative_to(root).as_posix()
        assert archive.extractfile(name).read() == path.read_bytes(), name
    assert archive.getmember("energieboard/deploy/install.sh").mode == 0o755
    assert archive.getmember("energieboard/app/frontend/dist/index.html").isfile()
    assert archive.getmember("energieboard/deploy/check.py").isfile()
    assert archive.getmember("energieboard/INSTALLATION.md").isfile()
    assert archive.getmember("energieboard/PRUEFBERICHT.md").isfile()
    assert b"derived_samples" in archive.extractfile("energieboard/app/backend/lib/topology.py").read()
    assert b"NodeOverview" in archive.extractfile("energieboard/app/frontend/src/pages/Dashboard.tsx").read()
    assert all(not Path(member.name).is_absolute() and ".." not in Path(member.name).parts for member in archive.getmembers())
    assert all(member.mode == 0o755 for member in archive.getmembers() if member.isdir())

# Copies live one level below the original documents on GitHub.
for source, target in (("INSTALLATION.md", "Installationsanleitung.md"), ("PRUEFBERICHT.md", "Pruefbericht.md")):
    content = (root / source).read_text(encoding="utf-8").replace("](docs/", "](../docs/")
    for document in root.glob("*.md"):
        content = content.replace("](" + document.name, "](../" + document.name)
    (output.parent / target).write_text(content, encoding="utf-8", newline="\n")
checksum = hashlib.sha256(output.read_bytes()).hexdigest()
(output.parent / "SHA256SUMS").write_text(f"{checksum}  {output.name}\n", encoding="ascii", newline="\n")
assert hashlib.sha256(output.read_bytes()).hexdigest() == (output.parent / "SHA256SUMS").read_text().split()[0]

print(f"LXC-Archiv: {len(files)} Dateien, {output.stat().st_size:,} Byte")
print(f"SHA-256: {checksum}")
