"""Configurable read-only HTTP GET adapter. Templates are data, never shell commands."""
import asyncio
from urllib.parse import quote
import httpx
from lib.acquisition import numeric


def extract(value, path):
    if not path:return value
    keys=path[1:].split("/") if path.startswith("/") else path.split(".")
    for key in keys:
        if path.startswith("/"):key=key.replace("~1","/").replace("~0","~")
        value=value[int(key)] if isinstance(value,list) else value[key]
    return value


def request_path(connection, points):
    return connection.api_path.replace("{addresses}",",".join(quote(p.address,safe="._-:") for p in points)).replace("{address}",quote(points[0].address,safe=""))


async def read_api(connection, points):
    host="["+connection.host+"]" if ":" in connection.host else connection.host
    base=("https" if connection.tls else "http")+f"://{host}:{connection.port}"
    headers={};auth=None
    if connection.api_auth=="bearer" and connection.token:headers["Authorization"]="Bearer "+connection.token
    elif connection.api_auth=="header" and connection.token:headers[connection.api_token_header]=connection.token
    elif connection.api_auth=="basic":auth=httpx.BasicAuth(connection.username,connection.password)
    batches=[points[i:i+40] for i in range(0,len(points),40)] if "{addresses}" in connection.api_path else [[p] for p in points]
    requests={}
    for batch in batches:requests.setdefault(request_path(connection,batch),[]).extend(batch)
    out={p.id:None for p in points};errors=[];limit=asyncio.Semaphore(4)
    async with httpx.AsyncClient(timeout=connection.timeout_s,headers=headers,auth=auth,follow_redirects=False) as client:
        async def fetch(path, group):
            async with limit:
                try:
                    response=await client.get(base+path)
                    response.raise_for_status()
                    try:data=response.json()
                    except ValueError:data=response.text.strip()
                    by_id={str(item["id"]):item for item in data if isinstance(item,dict) and "id" in item} if isinstance(data,list) else data
                    for point in group:
                        try:
                            if connection.api_response_format=="iobroker_bulk":
                                item=by_id.get(point.address) if isinstance(by_id,dict) and "id" not in by_id else by_id
                                value=extract(item,point.json_path or connection.api_json_path)
                            else:
                                item=extract(data,connection.api_json_path)
                                path=point.json_path or (point.address if connection.api_preset=="evcc" else "")
                                value=extract(item,path)
                            out[point.id]=numeric(value)
                        except (ValueError,KeyError,IndexError,TypeError):
                            errors.append(f"{point.name}: API-Wertpfad nicht verfügbar.")
                except httpx.HTTPStatusError as exc:
                    errors.append(f"{connection.name}: HTTP {exc.response.status_code} für {len(group)} Messpunkt(e).")
                except (httpx.HTTPError,ValueError):
                    errors.append(f"{connection.name}: API-Verbindung fehlgeschlagen ({len(group)} Messpunkte). Host, TLS, Timeout und Anmeldung prüfen.")
        await asyncio.gather(*(fetch(path,group) for path,group in requests.items()))
    return out,errors
