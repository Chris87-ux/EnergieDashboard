# First installation in a Proxmox LXC

[Documentation](README.md) · [Docker alternative](DOCKER.md) · [First configuration](GETTING-STARTED.md)

This installs Energieboard directly as a systemd service in a **new Debian LXC**. Run application installation commands **inside the LXC**, not on the Proxmox host. For an existing installation, follow [Updates](OPERATIONS.md). Never extract a new archive over a running installation.

## 1. Requirements

| Item | Requirement |
|---|---|
| Guest | Debian **12 Bookworm**, **amd64**, running systemd |
| Container | Unprivileged LXC; root console access |
| Starting allocation | 2 vCPU, 4 GB RAM, 32 GB SSD, plus history/backup capacity |
| Network | Available LAN address, correct gateway and DNS; access to Internet and measurement sources |
| Local database | MongoDB 8.0; CPU exposing AVX and compatible Proxmox host kernel |
| External database | Reachable dedicated database; history calculations technically need MongoDB 5.0 or later; use a maintained supported release |

The direct installer targets Debian 12, including when the Proxmox host is newer. Debian 13 is not a supported target of this installer. LXC shares the host kernel. Check inside the container:

```bash
dpkg --print-architecture
cat /etc/os-release
grep -w avx /proc/cpuinfo
uname -r
```

Without AVX, use a suitable external database; Docker does not remove MongoDB CPU requirements. Compare your exact MongoDB patch and host kernel with [MongoDB production notes](https://www.mongodb.com/docs/manual/administration/production-notes/).

## 2. Create the container

In the Proxmox web interface:

1. Download the Debian 12 standard amd64 template from CT Templates on suitable storage.
2. Create CT, choose a free ID and hostname, set a root password or SSH key, and enable **Unprivileged container**.
3. Select the template and allocate at least 32 GiB disk, 2 cores and 4096 MiB RAM to start.
4. Attach the network interface to your actual LAN bridge, commonly `vmbr0`. Use a VLAN only when your network is configured for it.
5. Choose DHCP with a router reservation or a static address. For an actual /24 LAN, an example is `192.168.10.17/24`, gateway `192.168.10.1`. **A gateway is the router's IP, never the netmask `255.255.255.0`.** Use your own LAN prefix and gateway.
6. Set DNS, start the container, open Console and log in as root.
7. Optionally enable start at boot and configure Proxmox backups.

Docker is not needed for this path. For namespace/systemd issues consult the [Proxmox container documentation](https://pve.proxmox.com/pve-docs/chapter-pct.html); diagnose the issue before changing container privilege settings.

## 3. Check networking

Inside the LXC:

```bash
ip -4 addr show
ip -4 route show
getent ahostsv4 deb.debian.org
apt-get update
```

You need a LAN IPv4 address, a default route via the router, working DNS and downloadable package lists. If IPv6 resolves but has no working route, test IPv4 once:

```bash
apt-get -o Acquire::ForceIPv4=true update
```

This does not fix a missing IPv4 route. See [Troubleshooting](TROUBLESHOOTING.md). Allow inbound TCP 8000 only from the intended LAN. Installation/update needs DNS and outbound HTTP/HTTPS for package repositories, GitHub and PyPI. Source ports depend on your actual configuration: API ports often 8087/8123/7070, MQTT 1883 or TLS 8883, Modbus TCP 502, InfluxDB 8086.

## 4. Download and verify the release

As root **inside the new LXC**. Archive and checksum are pinned to the same release tag:

```bash
(
  set -e
  test ! -e /opt/energieboard || { echo 'Installation already exists: use the update guide.' >&2; exit 1; }
  apt-get update
  apt-get install -y ca-certificates curl
  download_dir="$(mktemp -d /tmp/energieboard-install.XXXXXXXX)"
  cd "$download_dir"
  release=v2.6.0
  basis="https://raw.githubusercontent.com/Chris87-ux/EnergieDashboard/$release/outputs"
  curl -fL --retry 3 "$basis/Energieboard-LXC.tar.gz" -o Energieboard-LXC.tar.gz
  curl -fL --retry 3 "$basis/SHA256SUMS" -o SHA256SUMS
  sha256sum -c SHA256SUMS
  mkdir -p /opt
  tar -xzf Energieboard-LXC.tar.gz -C /opt
)
```

Alternatively download `outputs/Energieboard-LXC.tar.gz` and `outputs/SHA256SUMS` from the same tag to `/root` on the Proxmox host. In the **host shell**, replace the CT ID:

```bash
CTID=123
pct push "$CTID" /root/Energieboard-LXC.tar.gz /tmp/Energieboard-LXC.tar.gz
pct push "$CTID" /root/SHA256SUMS /tmp/SHA256SUMS
pct enter "$CTID"
```

Then inside the LXC verify and extract the uploaded archive under `/opt` before installing:

```bash
cd /tmp
sha256sum -c SHA256SUMS
mkdir -p /opt
tar -xzf Energieboard-LXC.tar.gz -C /opt
```

## 5. Install

For local MongoDB, run inside the LXC:

```bash
bash /opt/energieboard/deploy/install.sh
```

The archive includes a built frontend. The installer installs the backend environment, database and systemd service, then checks readiness. It preserves an existing environment file. Application location is `/opt/energieboard`; environment file is `/etc/energieboard/energieboard.env`; service is `energieboard.service`.

For an **external** MongoDB, create the environment file first:

```bash
install -d -m 0700 /etc/energieboard
install -m 0600 /opt/energieboard/deploy/energieboard.env.example /etc/energieboard/energieboard.env
nano /etc/energieboard/energieboard.env
```

Set `MONGO_URL` to the reachable MongoDB URI and `DB_NAME` to your dedicated database. Include credentials/options appropriate to your server. Then:

```bash
bash /opt/energieboard/deploy/install.sh --external-mongo
```

This avoids installing a local database. A source or database on another machine must permit access from the LXC.

## 6. Verify and open

```bash
systemctl status energieboard --no-pager
journalctl -u energieboard -n 60 --no-pager
curl -fsS http://127.0.0.1:8000/api/
hostname -I
```

Expect an active service and JSON status `ok`, version `2.6.0`, schema `6`. Open `http://<LXC-IP>:8000/?lang=en`. The ready check quietly retries expected startup connection refusals; persistent failures show the last error and journal diagnostics.

Energieboard has no built-in login. Keep it on a trusted network or use a reverse proxy with authentication and HTTPS. Do not publish port 8000 directly to the Internet.

## 7. Commission and maintain

Continue with [Getting started](GETTING-STARTED.md). Create your actual data connections and measurements, then a grid connection. No demo values are installed. Enable recording and plan backups/history storage. For later releases use the [LXC updater](OPERATIONS.md), which preserves configuration and history.
