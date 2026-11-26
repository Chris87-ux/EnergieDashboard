"""Run inside the built image; verifies DB persistence across app recreation."""
import os
import sys
import httpx

with httpx.Client(base_url="http://127.0.0.1:8000/api", timeout=10) as client:
    health=client.get("/").raise_for_status().json()
    assert health["status"]=="ok" and health["version"]=="2.7.1"
    assert os.getuid()!=0, "Runtime must not run as root"
    settings=client.get("/settings").raise_for_status().json()
    if sys.argv[1]=="create":
        settings["site_name"]="Docker persistence check"
        client.put("/settings",json=settings).raise_for_status()
        client.post("/flows",json={"kind":"grid","name":"Docker CI grid","grid_mode":"signed","datapoints":{"power_total":"ci.grid"}}).raise_for_status()
        grid=next(f for f in client.get('/flows').raise_for_status().json() if f['kind']=='grid')
        client.put('/charts/docker-chart',json={'name':'Persistent chart','series':[{'kind':'power','reference_id':grid['id']}]}).raise_for_status()
        pv=client.post('/flows',json={'name':'CI PV','category':'pv','direction':'in','datapoints':{'power_total':'ci.pv'}}).raise_for_status().json()
        client.put('/forecast/sites/docker-pv',json={'name':'Persistent PV','latitude':50,'longitude':10,'arrays':[{'kwp':5}],'actual_flow_ids':[pv['id']],'measurement_side':'ac'}).raise_for_status()
        client.put('/forecast/providers/docker-vrm',json={'name':'Persistent VRM','site_id':'docker-pv','kind':'vrm','token':'ci-persistence-only','vrm_installation_id':'12345'}).raise_for_status()
    else:
        assert settings["site_name"]=="Docker persistence check"
        assert any(flow["name"]=="Docker CI grid" for flow in client.get("/flows").raise_for_status().json())
        assert any(c['id']=='docker-chart' for c in client.get('/charts').raise_for_status().json())
        cfg=client.get('/forecast/config').raise_for_status().json()
        assert cfg['sites'][0]['id']=='docker-pv'
        assert cfg['providers'][0]['token_set'] and not cfg['providers'][0]['token']
    assert client.get("/live").status_code==200
    assert client.get("/config/csv").status_code==200
    html=httpx.get("http://127.0.0.1:8000/flow").raise_for_status().text
    assert 'id="root"' in html
print("Docker: health, non-root runtime, frontend, API and persistent configuration OK")
