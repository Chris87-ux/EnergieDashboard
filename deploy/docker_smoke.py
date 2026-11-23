"""Run inside the built image; verifies DB persistence across app recreation."""
import os
import sys
import httpx

with httpx.Client(base_url="http://127.0.0.1:8000/api", timeout=10) as client:
    health=client.get("/").raise_for_status().json()
    assert health["status"]=="ok" and health["version"]=="2.5.0"
    assert os.getuid()!=0, "Runtime must not run as root"
    settings=client.get("/settings").raise_for_status().json()
    if sys.argv[1]=="create":
        settings["site_name"]="Docker persistence check"
        client.put("/settings",json=settings).raise_for_status()
        client.post("/flows",json={"kind":"grid","name":"Docker CI grid","grid_mode":"signed","datapoints":{"power_total":"ci.grid"}}).raise_for_status()
    else:
        assert settings["site_name"]=="Docker persistence check"
        assert any(flow["name"]=="Docker CI grid" for flow in client.get("/flows").raise_for_status().json())
    assert client.get("/live").status_code==200
    assert client.get("/config/csv").status_code==200
    html=httpx.get("http://127.0.0.1:8000/flow").raise_for_status().text
    assert 'id="root"' in html
print("Docker: health, non-root runtime, frontend, API and persistent configuration OK")
