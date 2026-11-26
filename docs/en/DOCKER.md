# First installation with Docker Compose

[Documentation](README.md) · [Direct LXC alternative](INSTALLATION.md) · [Getting started](GETTING-STARTED.md)

Run these commands on the **Linux Docker host**, for example a dedicated Debian VM on Proxmox. Do not run the LXC installer or updater inside the application container.

## 1. Host requirements

| Item | Requirement |
|---|---|
| Platform | Linux amd64 with Docker Engine and Compose plugin |
| Supplied host commands | Debian 12 or 13 |
| Compose | Current `docker compose` plugin, at least 2.20; not legacy v1 `docker-compose` |
| Starting allocation | 2 vCPU, 4 GB RAM, 32 GB SSD plus history/backups |
| Local MongoDB | AVX exposed in the guest CPU and a compatible kernel |
| Network | GitHub, Docker Hub, npm, PyPI and your measurement sources reachable |
| Privileges | Root or authorised Docker administrator |

On Proxmox, a dedicated VM is the documented Docker installation path. If supported by the host and your migration requirements, VM CPU type `host` can expose AVX; clusters need a compatible shared CPU type. Verify in the VM:

```bash
uname -m
grep -w avx /proc/cpuinfo
uname -r
```

The tested architecture is linux/amd64. Docker does not bypass database CPU/kernel limitations. Review [MongoDB production notes](https://www.mongodb.com/docs/manual/administration/production-notes/) for the deployed patch. Docker inside an LXC needs additional nesting/container configuration; that setup is outside this installation procedure.

## 2. Install Docker on a fresh Debian VM

Skip this section if Docker already works. Run as root on a fresh VM; for existing Docker/containerd packages follow the conflict guidance in the [official Debian instructions](https://docs.docker.com/engine/install/debian/):

```bash
apt-get update
apt-get install -y ca-certificates curl git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: $VERSION_CODENAME
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker version
docker compose version
```

Both the client and server should respond, and the Compose plugin should report its version. Docker daemon access grants substantial host privileges.

## 3. Download and start Energieboard

Use a new project directory on the Docker host:

```bash
mkdir -p /opt
cd /opt
git clone --branch v2.7.1 https://github.com/Chris87-ux/EnergieDashboard.git energieboard-docker
cd /opt/energieboard-docker
cp docker.env.example .env
```

Edit `.env` before starting if needed:

```dotenv
ENERGIEBOARD_VERSION=2.7.1
ENERGIEBOARD_PORT=8000
ENERGIEBOARD_BIND=0.0.0.0
```

`ENERGIEBOARD_VERSION` names the locally built image; the checked-out Git tag determines its contents. It does not download a new release by itself. `ENERGIEBOARD_PORT` sets the host port; `ENERGIEBOARD_BIND=127.0.0.1` restricts it to local access, suitable for a local reverse proxy. `0.0.0.0` exposes it on host interfaces subject to firewall configuration.

```bash
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
docker compose logs --tail=60 energieboard
curl -fsS http://127.0.0.1:8000/api/
```

Expect healthy application and MongoDB containers and API status `ok`, version `2.7.1`. Open `http://<DOCKER-HOST-IP>:8000/?lang=en`, substituting a changed host port when applicable.

## 4. Persistence and network access

The default Compose file uses a named MongoDB volume. Recreating the app container preserves this database. Keep the project name, volume, database name and URI consistent during updates. `docker compose down --volumes` deletes the local database volume: do not use it for a normal stop or update.

The app runs without root, with a read-only filesystem, temporary `/tmp`, dropped capabilities and a healthcheck. MongoDB is not published to the host by default. No global frontend/backend configuration needs rebuilding when you add a measurement.

Inside the app container, `localhost` is that container. Use LAN addresses for external sources. On supported Linux hosts `host.docker.internal` resolves through the supplied host-gateway mapping. Source firewalls must accept connections from the host/container network. A browser's access to a source does not prove that the app container can access it.

## 5. External MongoDB

Set in `.env`:

```dotenv
MONGO_URL=mongodb://192.168.10.20:27017
DB_NAME=energieboard
```

Use your actual URI, credentials and database. From the same project directory, consistently use the external Compose file:

```bash
docker compose -f compose.external.yaml config --quiet
docker compose -f compose.external.yaml up -d --build --wait --wait-timeout 180
docker compose -f compose.external.yaml ps
```

This starts only the app and does not create a local MongoDB volume. Switching to an external URI does not copy data. Restore a verified backup into the intended target if moving an existing installation.

## 6. Next steps

The app has no built-in authentication. Use trusted LAN access or an authenticated HTTPS reverse proxy. Continue with [Getting started](GETTING-STARTED.md), then [backup and Docker updates](OPERATIONS.md). Keep the Compose file and project identity consistent during all maintenance commands.
