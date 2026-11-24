# Appliance cycles and status

[Documentation](README.md) · [Deutsch](../GERAETEZYKLEN.md)

From 2.7, washing machines, dryers and dishwashers can count completed cycles. The concept follows [ioBroker device-reminder](https://github.com/Xenon-s/ioBroker.device-reminder): power thresholds, start/stop confirmation and a moving average. Detection runs inside Energieboard; installing the adapter is unnecessary. It neither controls appliances nor sends messages.

## Configuration

1. Add the appliance's measured active power under **Data acquisition**. Check scaling and W/kW units. Enable recording; prefer 5–10-second sampling and a matching source update rate. Infrequent source updates cannot reliably capture short state changes.
2. Open **Configuration → Edit device → Appliance cycles** and enable detection. Only ordinary consumers support tracking, not nodes, generators or storage.
3. Choose washing machine, dryer or dishwasher. Profiles are **starting values**. Washing machine defaults: start above 10 W for 60 s, end at or below 5 W for 600 s, moving window 120 s, minimum runtime 300 s. Dishwasher end confirmation defaults to 900 s because quiet phases can be longer.
4. Adjust using a complete test cycle. Standby ≤ stop < start. Set stop confirmation longer than normal pauses. Too short creates extra cycles; too long delays the finished indication.
5. For a reliable run signal choose **Boolean signal**, map a measurement or reuse the device's RUN mapping. 1 = running, 0 = stopped. Boolean tracking counts direct state transitions; delays, moving windows and minimum runtime apply to power mode.
6. Check **Device status** (`/geraete`). The main dashboard also shows enabled tracking; `/flow` remains an energy-only embed.

## States and counting

| State | Meaning |
|---|---|
| Off / Ready | Idle below standby/stop thresholds |
| Starting | Start threshold reached, confirmation pending |
| Running | Confirmed operation |
| Paused | Temporarily low power within a cycle |
| Finished | Stop confirmed by timing and moving average |
| Unknown | Missing/stale observations or recording disabled |

Only a **confirmed completion** increases today/month/total counts. The end timestamp is the beginning of the quiet stop period, excluding confirmation delay from runtime. Acknowledging Finished changes the display only.

Short spikes below minimum runtime do not count. A cycle already running when tracking starts is marked **Start not observed** and does not count. Large observation gaps interrupt a cycle rather than fabricate a completion. The gap threshold is the maximum of 30 seconds and three recorder intervals. Smaller missing sections reset stop confirmation timers.

State and a stable cycle ID persist in MongoDB. A short restart continues tracking; longer downtime marks it incomplete. Retrying a completion cannot double-count its unique ID. Relevant threshold or mapping changes during a cycle mark it reconfigured. Name/colour edits retain tracking state.

Runtime alarms warn without stopping the cycle. History shows outcome, timing and kWh when recorded energy is sufficient; an asterisk marks incomplete energy. Disabling tracking or deleting configuration retains past events. Retain device configuration if you need historical status charts.

## Charts and API

Recorded numeric states: 0 Off, 1 Ready, 2 Running, 3 Paused, 4 Finished, 5 Unknown, 6 Starting. Charts can compare status and cumulative completed cycles with power. There is no reconstructed history before recording began.

API: `GET /api/cycles/presets`, `GET /api/cycles/status`, `GET /api/cycles/{device_id}/events?limit=20`, `POST /api/cycles/{device_id}/ack` with `{}`. Device configuration uses `cycle_tracking`; the complete schema is available at `/api/schemas/flow`.
