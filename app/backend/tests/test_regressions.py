import unittest
from unittest.mock import AsyncMock, patch

import numpy as np
from pydantic import ValidationError

from lib.energy import counter_delta, power_integral
from lib.sources import LiveSource, _v2_query, iob_base
from models.flow import Flow
from models.settings import AppSettings
from routers.energy import _live_flow, _summary
from routers import settings


class EnergyBoundaryTests(unittest.TestCase):
    def test_counter_excludes_energy_before_start(self):
        result = counter_delta(np.array([0, 60, 120]), np.array([1000, 1001, 1002]), 60, 120, 120)
        self.assertEqual(result.kwh, 1)

    def test_stale_counter_boundary_is_a_gap(self):
        result = counter_delta(np.array([-86400, 30, 60]), np.array([1000, 1100, 1101]), 0, 60, 60)
        self.assertEqual(result.kwh, 1)
        self.assertFalse(result.complete)
        self.assertEqual(result.gaps, [(0, 30)])

    def test_counter_and_power_clip_both_boundaries(self):
        times = np.array([0, 100])
        counter = counter_delta(times, np.array([100, 110]), 25, 75, 120)
        power = power_integral(times, np.array([1000, 1000]), 25, 75, 120)
        self.assertEqual(counter.kwh, 5)
        self.assertAlmostEqual(power.kwh, 1000 * 50 / 3.6e6)
        self.assertEqual(power.coverage, 1)

    def test_counter_reset_and_jitter(self):
        reset = counter_delta(np.array([0, 60, 120]), np.array([90, 100, 5]), 0, 120, 120)
        self.assertEqual(reset.kwh, 15)
        self.assertEqual(reset.resets, 1)
        jitter = counter_delta(np.array([0, 60, 120]), np.array([1000, 999.9, 1001]), 0, 120, 120)
        self.assertEqual(jitter.kwh, 1)
        self.assertEqual(jitter.resets, 0)

    def test_no_overlap_produces_no_result(self):
        self.assertIsNone(power_integral(np.array([0, 10]), np.array([100, 100]), 20, 40, 120))
        self.assertIsNone(counter_delta(np.array([0, 10]), np.array([100, 101]), 20, 40, 120))

    def test_missing_grid_does_not_imply_autarky(self):
        flow = Flow(name="Verbraucher")
        live = _live_flow(flow, lambda key, raw=False: 300 if key == "power_total" else None)
        summary = _summary([live])
        self.assertIsNone(summary.grid_import_w)
        self.assertIsNone(summary.autarky_pct)
        self.assertEqual(summary.consumption_w, 300)

    def test_invalid_connection_input_and_ipv6(self):
        with self.assertRaises(ValidationError):
            AppSettings(iobroker={"host": "http://192.168.1.20:8087"})
        with self.assertRaises(ValidationError):
            AppSettings(influx={"url": "localhost:8086"})
        config = AppSettings(iobroker={"host": "[::1]"})
        self.assertEqual(iob_base(config), "http://[::1]:8087")


class ConnectorRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_reports_database_failure(self):
        from types import SimpleNamespace
        from fastapi import HTTPException
        from pymongo.errors import ServerSelectionTimeoutError
        import server

        unavailable = SimpleNamespace(command=AsyncMock(side_effect=ServerSelectionTimeoutError("offline")))
        with patch.object(server, "db", unavailable):
            with self.assertRaises(HTTPException) as caught:
                await server.root()
        self.assertEqual(caught.exception.status_code, 503)

    async def test_recorder_fills_internal_influx_gap(self):
        flow = Flow(name="Verbraucher", datapoints={"power_total": "p"})
        source = LiveSource(AppSettings(influx={"enabled": True}))
        with patch("lib.sources.influx_series", AsyncMock(return_value=[(0, 100), (120, 300)])), \
             patch("lib.sources.mongo_series", AsyncMock(return_value=[(0, 900), (60, 200), (120, 900)])):
            times, values = await source.series(flow, "power_total", 0, 180, 60, "mean")
        self.assertEqual(list(times), [0, 60, 120])
        self.assertEqual(list(values), [100, 200, 300])

    async def test_nearest_counter_boundary_wins(self):
        flow = Flow(name="Zähler", datapoints={"energy_total": "e"})
        source = LiveSource(AppSettings(influx={"enabled": True}))
        with patch("lib.sources.influx_series", AsyncMock(return_value=[(60, 110)])), \
             patch("lib.sources.influx_last_before", AsyncMock(return_value=(-9000, 1))), \
             patch("lib.sources.mongo_series", AsyncMock(return_value=[(30, 105)])), \
             patch("lib.sources.mongo_last_before", AsyncMock(return_value=(-10, 100))):
            times, _ = await source.series(flow, "energy_total", 0, 120, 30, "last")
        self.assertEqual(list(times), [-10, 30, 60])

    async def test_influx_v2_missing_bucket_is_reported(self):
        config = AppSettings(influx={"enabled": True, "version": "v2"})
        with patch.object(settings, "load_settings", AsyncMock(return_value=config)), \
             patch.object(settings, "_v2_query", AsyncMock(side_effect=RuntimeError("bucket not found"))):
            result = await settings.test_influx(config)
        self.assertFalse(result.ok)

    async def test_influx_v2_csv_repeated_headers(self):
        import httpx

        payload = (
            "#datatype,string,long,dateTime:RFC3339,double\n"
            ",result,table,_time,_value\n,,0,2026-11-19T00:00:00Z,10\n\n"
            ",result,table,_time,_value\n,,1,2026-11-19T00:01:00Z,20\n"
        )
        response = httpx.Response(200, text=payload, request=httpx.Request("POST", "http://test/api/v2/query"))
        client = AsyncMock()
        client.post.return_value = response
        with patch("lib.sources.httpx.AsyncClient") as factory:
            factory.return_value.__aenter__ = AsyncMock(return_value=client)
            factory.return_value.__aexit__ = AsyncMock(return_value=False)
            rows = await _v2_query(AppSettings(), "query")
        self.assertEqual([row["_value"] for row in rows], ["10", "20"])

    async def test_influx_v2_csv_runtime_error(self):
        import httpx

        response = httpx.Response(
            200, text='error,reference\n"query failed",123\n',
            request=httpx.Request("POST", "http://test/api/v2/query"),
        )
        client = AsyncMock()
        client.post.return_value = response
        with patch("lib.sources.httpx.AsyncClient") as factory:
            factory.return_value.__aenter__ = AsyncMock(return_value=client)
            factory.return_value.__aexit__ = AsyncMock(return_value=False)
            with self.assertRaisesRegex(RuntimeError, "query failed"):
                await _v2_query(AppSettings(), "query")
