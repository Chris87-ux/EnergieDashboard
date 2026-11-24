# Getting started and commissioning

[Documentation](README.md) · [Data acquisition](DATA-ACQUISITION.md)

## 1. Open the application and set the language

Open `http://<SERVER-IP>:8000/`. Choose **English** in the header, or open `/?lang=en`. Switching language reloads the page after confirmation, so save edits first. Your language choice belongs to this browser and does not change the system time zone or other users' preferences.

## 2. Check system settings

Under **System & LXC**, set the site name, your actual time zone, live refresh and gap threshold. Enable the recording service and choose its interval. Live refresh controls screen updates; recorder interval controls historical samples. Changing one does not replace the other. Configure InfluxDB only when you want to read existing compatible history; the local recorder works without InfluxDB.

## 3. Create one connection and measurement

Under **Data acquisition → Add connection**, choose API / HTTP, MQTT or Modbus TCP. For an API choose a preset (ioBroker, Home Assistant, evcc or Generic API) and enter the actual host, port and credentials. The preset fills editable defaults; it does not discover your devices or install a server.

Create a measurement with a descriptive name, stable ID, address/topic/register, unit, factor and offset. Verify its raw and converted readings under Measurements and diagnostics. A measurement alone does not create a device card. See [source-specific instructions](DATA-ACQUISITION.md).

## 4. Configure the mandatory grid connection

Under Configuration, create type **Grid connection**, at the top level, on AC. Assign signed power (positive import, negative export unless inverted) or the supported separate directional values. Optional cumulative import/export energy counters take priority for period energy. Assign grid frequency here, not to an arbitrary generator. At least one active grid connection must remain.

Confirm that the permanent grid tile shows import/export, current frequency and daily energy. Check a known import and, where possible, an export situation before adding more equipment.

## 5. Add devices and nodes

Create a measured section as a node, then connect its child consumers/producers using the Connection field. A metered node creates residual consumption/production channels and reconciles measured children. Use nested nodes for nested electrical sections. Enter three-phase total power as the whole device; missing phases are split symmetrically. Use actual phase measurements when available.

For a device with only RUN, assign the RUN signal and fixed running watts. The recorder uses the observed state intervals to estimate kWh. Unobserved past runtime cannot be reconstructed.

Add storage and hybrids using [their dedicated guide](STORAGE-AND-HYBRID.md). Batteries are separate from the main overview balance. For optional cross-node summaries, create [consumer groups](CONSUMER-GROUPS.md).

## 6. Verify the installation

- Compare each source value, unit and sign with the original system.
- Verify that a known active load appears and stops correctly.
- Check node meter, children and residual; do not count parent meters and their children as independent site loads.
- Confirm production excludes grid import and battery discharge.
- Leave the recorder running, then inspect Today and the energy balance. Initial daily history is incomplete until enough real data exists.
- Check SOC, reserve, capacity and charging/discharging direction for each battery.
- Test the embedded `/flow?lang=en` view and mobile display if required.
- Export configuration CSV and take a full database backup.

Missing values mean unknown, not zero. Resolve diagnostics before adding dozens of measurements. Keep IDs stable when renaming devices or changing a source. See [Troubleshooting](TROUBLESHOOTING.md) and [Operations](OPERATIONS.md).
