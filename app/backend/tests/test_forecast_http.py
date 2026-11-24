import unittest
from datetime import datetime,timezone
from unittest.mock import patch
import httpx
from lib.forecast_providers import fetch_forecast,ForecastError
from models.forecast import ForecastSite,ForecastProvider

class ForecastHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_authentication_headers_fixed_hosts_and_request_reservations(self):
        now=datetime(2026,11,24,tzinfo=timezone.utc).timestamp()
        site=ForecastSite(name='PV',latitude=50,longitude=10,arrays=[{'kwp':2}],actual_flow_ids=['pv'])
        original=httpx.AsyncClient;requests=[];reserved=[]
        def handler(request):
            requests.append(request)
            if request.url.host=='vrmapi.victronenergy.com':return httpx.Response(200,json={'success':True,'records':{'solar_yield_forecast':[[now*1000,1]]}})
            if request.url.host=='api.solcast.com.au':return httpx.Response(200,json={'forecasts':[{'period_end':'2026-11-24T01:00:00Z','period':'PT60M','pv_estimate':1}]})
            if request.url.host=='api.forecast.solar':return httpx.Response(200,json={'result':{'watt_hours_day':{'2026-11-24':2000}}})
            return httpx.Response(200,json={'hourly':{'time':[now+3600],'global_tilted_irradiance':[500]}})
        def factory(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
        async def reserve(p,t):reserved.append(p.kind)
        with patch('lib.forecast_providers.httpx.AsyncClient',factory):
            for kind in ('vrm','solcast','forecast_solar','open_meteo'):
                p=ForecastProvider(name=kind,site_id='s',kind=kind,token='secret',vrm_installation_id='123',solcast_resource_ids=['roof'])
                self.assertTrue(await fetch_forecast(p,site,'UTC',now,reserve))
        self.assertEqual(len(reserved),4);self.assertEqual(len(requests),4)
        self.assertEqual(requests[0].headers['X-Authorization'],'Token secret')
        self.assertEqual(requests[1].headers['Authorization'],'Bearer secret')
        self.assertTrue(all('secret' not in str(r.url) for r in requests))
        self.assertTrue(all(r.url.scheme=='https' for r in requests))
    async def test_rate_limit_retry_and_errors_do_not_expose_secret(self):
        original=httpx.AsyncClient
        def factory(**kwargs):return original(transport=httpx.MockTransport(lambda r:httpx.Response(429,headers={'Retry-After':'7200'},text='private-secret')),**kwargs)
        site=ForecastSite(name='PV',latitude=50,longitude=10,arrays=[{'kwp':2}],actual_flow_ids=['pv'])
        p=ForecastProvider(name='S',site_id='s',kind='solcast',token='private-secret',solcast_resource_ids=['roof'])
        async def reserve(p,t):pass
        with patch('lib.forecast_providers.httpx.AsyncClient',factory):
            with self.assertRaises(ForecastError) as error:await fetch_forecast(p,site,'UTC',1,reserve)
        self.assertEqual(error.exception.retry_after,7200)
        self.assertNotIn('private-secret',str(error.exception))
    async def test_missing_resource_yield_is_not_a_zero_forecast(self):
        original=httpx.AsyncClient
        def factory(**kwargs):return original(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'forecasts':[]})),**kwargs)
        site=ForecastSite(name='PV',latitude=50,longitude=10,arrays=[{'kwp':2}],actual_flow_ids=['pv'])
        p=ForecastProvider(name='S',site_id='s',kind='solcast',token='token',solcast_resource_ids=['roof'])
        async def reserve(p,t):pass
        with patch('lib.forecast_providers.httpx.AsyncClient',factory):
            with self.assertRaises(ForecastError):await fetch_forecast(p,site,'UTC',1,reserve)
