# Troubleshooting

[Documentation](README.md) · [Data acquisition](DATA-ACQUISITION.md) · [Backups and updates](OPERATIONS.md)

## Network and apt

Inside the LXC inspect `ip -4 addr show`, `ip -4 route show` and `getent ahostsv4 deb.debian.org`. A default route must point to the actual router IP, not a netmask such as 255.255.255.0. Match the LAN prefix and VLAN/bridge. DNS success alone does not prove routing works. `apt-get -o Acquire::ForceIPv4=true update` can diagnose broken IPv6 but cannot repair a missing IPv4 route. Repository Release-file errors after network failures do not justify disabling signature checks.

## App does not start or port 8000 is unavailable

LXC: inspect `systemctl status energieboard --no-pager` and `journalctl -u energieboard -n 60 --no-pager`, then local `curl -fsS http://127.0.0.1:8000/api/`. Docker: inspect `docker compose ps` and `docker compose logs --tail=100 energieboard`. Use the external Compose file if that is your installation variant.

Check MongoDB URI/name, database reachability, disk space, AVX availability for a local database and kernel compatibility. A temporary initial connection refusal is retried by the readiness helper; a final timeout is a real failure to diagnose. A local API that works while LAN access fails points to bind address, host/LXC firewall, routing or proxy configuration.

## MongoDB or missing history

The health endpoint reports 503 when the database cannot be reached. Check the actual database process/URI and permissions. Recorded energy needs real historical samples. Newly installed systems cannot show a complete day immediately. Enable the recorder, verify its last run, and wait for sufficient data. InfluxDB is optional history input and does not replace the local recorder automatically.

If everything appears empty after an update, first check DB_NAME, MONGO_URL, Compose project and volume. A different empty database looks like a new installation. Do not recreate all devices before verifying identity. Downgrade only with a matching backup and code version.

## API missing readings

Check protocol API / HTTP, preset, actual port, relative GET path and response base. HTTP 401/403 usually means missing/wrong credentials or source permissions. For 3xx configure the final endpoint; redirects are not followed. Confirm the requested entity/state field from the source response. Home Assistant can return unknown/unavailable; evcc fields may change by version. These are unknown readings, not zero.

Bearer input takes the token without the word Bearer. Custom-header input is sent unchanged. Blank secret fields keep stored values; Delete saved token removes it. HTTPS needs a trusted certificate. The app server/container must reach the source, independently of your browser.

## MQTT stale or missing

Verify broker host/port, TLS, credentials/ACLs, exact topic and JSON path. No wildcards are supported. Staleness starts at reception; a change-only publisher needs periodic publication/heartbeat. Retained does not guarantee the source is online. A publisher timestamp or LWT is not separately evaluated by this version.

## Modbus unreasonable values

Verify device Unit ID, zero-based address, FC03/04, signed/unsigned type, byte and word order, scale and unit against the manufacturer's map. Huge numbers often indicate decoding/address errors. If only some registers fail, verify their validity rather than changing working ones. Long timeouts across many registers slow the acquisition cycle.

## Balance or phases incorrect

Compare units and signs first. A three-phase total is whole-device power, divided by three for calculated symmetric phases. Do not provide the whole total as one phase when the device is meant to have separate phase values. Real measured phases take priority. Verify node boundaries, parent-child relationships and active state; residuals reconcile the section meter with known children.

Grid import is not production, export is not house consumption, and battery charging is not an ordinary house load. Hybrid AC-Out may include pass-through; use AC-Out minus AC-In when required. Without assigned MPPTs, hybrid production is an explicitly marked estimate. Efficiency above 100%, contradictory signs or tiny power is unavailable rather than clipped to a plausible value. See [Storage and hybrid](STORAGE-AND-HYBRID.md).

Self-sufficiency/self-consumption use Today or selected period, so incomplete history affects them. They are not instantaneous power ratios. Missing required values stay unavailable.

## Devices hidden, nodes or groups missing

The zero filter requires continuous readings strictly between −1 and +1 W for the configured duration; Show inactive reveals filtered entries. Negative production with a larger magnitude must remain visible. Disabled nodes remove descendants from active evaluation. Click a node to navigate its children.

Create groups under Configuration and explicitly assign each normal consumer. Node membership alone is not group membership. Missing active readings make group totals unknown/incomplete; disabled members do not count. Remove all device assignments, including disabled ones, before deleting a group.

## English or embedding not applied

Use the header selector or `?lang=en`. Changing language reloads after confirmation; dismissing keeps current edits/language. URL language overrides the saved preference for that page. Blocked localStorage still allows explicit URL selection. Direct API clients should send `Accept-Language: en`; absent/unsupported preference defaults to German. User names and IDs are deliberately not translated.

For iframe embedding use `/flow?lang=en`. Serve the app with HTTPS inside an HTTPS parent, and check reverse-proxy authentication/frame policies. The iframe has no settings navigation.

## GitHub Docker checks

Inspect the first failing step of the run for the correct commit. A historical failed run remains red after later fixes. The LXC updater/readiness harnesses run on the Linux runner, not in the read-only/noexec app container. Removing meaningful checks is not a repair. The current [test report](TEST-REPORT.md) identifies the validated source and limits.
