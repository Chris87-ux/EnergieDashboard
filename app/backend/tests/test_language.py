import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from lib.i18n import ENGLISH, english_requested, localise_payload, translate

class LanguageTests(unittest.IsolatedAsyncioTestCase):
    def test_language_negotiation(self):
        for header in ('en','en-GB,en;q=0.8,de;q=0.5','fr,en-US;q=0.9','de;q=0,en;q=1'):
            self.assertTrue(english_requested(header), header)
        for header in ('','de','en;q=0,de;q=1','de;q=0.9,en;q=0.2','fr','en;q=bad','en;q=2'):
            self.assertFalse(english_requested(header), header)

    def test_placeholders_preserve_names_and_source_paths(self):
        self.assertEqual(translate('Werkstatt: API-Wertpfad nicht verfügbar.'),'Werkstatt: API value path unavailable.')
        self.assertEqual(translate('Value error, Ein Speicher benötigt einen Leistungs- und einen SOC-Datenpunkt.'),'Value error, Battery storage requires power and SOC data points.')
        self.assertEqual(translate('3 Zähler-Reset(s) berücksichtigt'),'3 counter reset(s) accounted for')
        self.assertEqual(translate('Zählerdelta; Keine Zähler- oder Leistungsdaten'),'Counter delta; No counter or power data')

    def test_user_data_and_identifiers_are_not_translated(self):
        original={'name':'Speicher','site_name':'Mein Zuhause','id':'Heute','label':'Heute','extra':{'notes':'Speicher'},'power_w':1234.5,'datapoints':{'power_total':'point:Speicher'}}
        self.assertEqual(localise_payload(original,route='/api/flows'),original)
        payload={'errors':['Verbindung existiert nicht.'],'consumer_groups':[{'name':'Speicher','member_ids':['Heute'],'power_w':1234.5}]}
        translated=localise_payload(payload,route='/api/live')
        self.assertEqual(translated['errors'],['Connection does not exist.'])
        self.assertEqual(translated['consumer_groups'],payload['consumer_groups'])

    def test_derived_labels_only_change_suffix(self):
        payload={'flows':[{'flow_id':'n:rest_consumption','name':'Werkstatt · Restverbrauch','category':'custom','power_w':123}], 'storage_total':{'id':'aggregate','name':'Gesamtspeicher'}}
        result=localise_payload(payload,route='/api/live')
        self.assertEqual(result['flows'][0]['name'],'Werkstatt · Residual consumption')
        self.assertEqual(result['storage_total']['name'],'Combined storage')
        self.assertEqual(localise_payload({'flow_id':'battery:charge','name':'Utility · Laden','category':'battery'},route='/api/energy')['name'],'Utility · Charging')
        user={'flow_id':'custom:import','name':'Haus · Bezug','category':'consumer'}
        self.assertEqual(localise_payload(user,route='/api/live'),user)

    def test_catalogue_placeholder_parity(self):
        import re
        for source,target in ENGLISH.items():
            self.assertEqual(sorted(re.findall(r'\{\d+\}',source)),sorted(re.findall(r'\{\d+\}',target)),source)
            self.assertTrue(target.strip(),source)

    async def test_http_localisation_defaults_and_error_responses(self):
        from server import app
        from models.settings import AppSettings
        from routers import energy,consumer_groups
        with patch.object(energy,'load_settings',AsyncMock(return_value=AppSettings())), patch.object(consumer_groups,'db') as db:
            db.flows.find_one=AsyncMock(return_value=None)
            db.consumer_groups.delete_one=AsyncMock(return_value=type('Deleted',(),{'deleted_count':0})())
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                for lang,label,error in [('en','Today','Group not found.'),('de','Heute','Gruppe nicht gefunden.')]:
                    response=await client.get('/api/energy/presets',headers={'Accept-Language':lang})
                    self.assertEqual(response.status_code,200)
                    self.assertEqual(response.json()[0]['label'],label)
                    self.assertEqual(response.headers['content-language'],lang)
                    self.assertIn('Accept-Language',response.headers['vary'])
                    response=await client.delete('/api/consumer-groups/missing',headers={'Accept-Language':lang})
                    self.assertEqual(response.status_code,404)
                    self.assertEqual(response.json()['detail'],error)
                response=await client.put('/api/flows/invalid',headers={'Accept-Language':'en'},json={'name':'Speicher','kind':'storage'})
                self.assertEqual(response.status_code,422)
                self.assertIn('Battery storage requires power and SOC',response.json()['detail'][0]['msg'])
                self.assertEqual(response.json()['detail'][0]['input']['name'],'Speicher')
                response=await client.get('/api/energy/presets')
                self.assertEqual(response.json()[0]['label'],'Heute')
