"""Four explicit providers. Irradiance-derived Open-Meteo is labelled as a local PV model."""
import math
import re
from datetime import datetime,timedelta,timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
import httpx

PROVIDERS={
 "vrm":{"name":"Victron VRM","family":"solcast","url":"https://vrm-api-docs.victronenergy.com/","account":True,"daily_limit":48,"hourly_limit":30},
 "forecast_solar":{"name":"Forecast.Solar","family":"forecast_solar","url":"https://forecast.solar/","account":False,"daily_limit":120,"hourly_limit":10},
 "solcast":{"name":"Solcast Hobbyist","family":"solcast","url":"https://docs.solcast.com.au/docs/section/rooftop-sites-hobbyist","account":True,"daily_limit":8,"hourly_limit":8},
 "open_meteo":{"name":"Open-Meteo · PV-Modell","family":"open_meteo","url":"https://open-meteo.com/en/docs","account":False,"daily_limit":120,"hourly_limit":30},
}

class ForecastError(Exception):
    def __init__(self,message,retry_after=3600):
        super().__init__(message);self.retry_after=retry_after


def nonnegative(value):
    if isinstance(value,bool):raise ValueError("Ungültiger Prognosewert.")
    value=float(value)
    if not math.isfinite(value) or value<0:raise ValueError("Ungültiger Prognosewert.")
    return value


def duration_seconds(value):
    match=re.fullmatch(r"PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?",value)
    if not match:raise ValueError("Ungültiges Prognoseintervall.")
    parts=[float(v or 0) for v in match.groups()];seconds=parts[0]*3600+parts[1]*60+parts[2]
    if not 0<seconds<=86400:raise ValueError("Ungültiges Prognoseintervall.")
    return seconds


def daily_intervals(intervals,tz):
    """Split interval kWh at local midnight, including 23/25 hour DST days."""
    zone=ZoneInfo(tz);days={}
    ordered=sorted(intervals)
    if any(a[1]>b[0]+.001 for a,b in zip(ordered,ordered[1:])):raise ValueError("Überlappende Prognoseintervalle.")
    for start,end,kwh in ordered:
        if not start<end:raise ValueError("Ungültiges Prognoseintervall.")
        kwh=nonnegative(kwh);left=start
        while left<end:
            local=datetime.fromtimestamp(left,zone);day=local.date()
            boundary=datetime.combine(day+timedelta(days=1),datetime.min.time(),zone).timestamp()
            right=min(end,boundary);entry=days.setdefault(day.isoformat(),{"kwh":0.,"intervals":[]})
            entry['kwh']+=kwh*(right-left)/(end-start);entry['intervals'].append((left,right));left=right
    for day,entry in days.items():
        date=datetime.fromisoformat(day).date();a=datetime.combine(date,datetime.min.time(),zone).timestamp();b=datetime.combine(date+timedelta(days=1),datetime.min.time(),zone).timestamp()
        covered=0.;last=None
        for left,right in sorted(entry.pop('intervals')):
            covered+=max(0,right-max(left,last if last is not None else left));last=max(right,last or right)
        entry['coverage']=min(1.,covered/(b-a));entry['complete']=entry['coverage']>=.98
        entry['kwh']=round(entry['kwh'],6)
    return days


def combine_days(parts):
    if not parts:return {}
    shared=set(parts[0])
    for part in parts[1:]:shared&=set(part)
    return {day:{"kwh":round(sum(part[day]['kwh'] for part in parts),6),"complete":all(part[day]['complete'] for part in parts),"coverage":min(part[day]['coverage'] for part in parts)} for day in sorted(shared)}


def parse_solcast(payload,tz):
    intervals=[];seen=set()
    for point in payload['forecasts']:
        stamp=datetime.fromisoformat(point['period_end'].replace('Z','+00:00'))
        if stamp.tzinfo is None:raise ValueError('Prognosezeitstempel benötigt Zeitzone.')
        end=stamp.timestamp();seconds=duration_seconds(point['period']);key=(end,seconds)
        if key in seen:continue
        seen.add(key);intervals.append((end-seconds,end,nonnegative(point['pv_estimate'])*seconds/3600))
    return daily_intervals(intervals,tz)


def parse_vrm(payload,tz):
    if payload.get('success') is False:raise ValueError("VRM-Prognose nicht verfügbar.")
    values=payload['records']['solar_yield_forecast']
    if not isinstance(values,list):raise ValueError("VRM-Prognose nicht verfügbar.")
    seen=set();intervals=[]
    for point in values:
        start=float(point[0])/1000
        if start in seen:continue
        seen.add(start)
        if point[1] is not None:intervals.append((start,start+3600,nonnegative(point[1])))
    return daily_intervals(intervals,tz)


def parse_forecast_solar(payload,tz):
    values=payload['result']['watt_hours_day']
    out={}
    for day,value in values.items():
        datetime.strptime(day,'%Y-%m-%d');out[day]={"kwh":nonnegative(value)/1000,"complete":True,"coverage":1.}
    return out


def parse_open_meteo_arrays(payloads,site,tz):
    planes=[]
    for payload,plane in zip(payloads,site.arrays):
        hourly=payload['hourly'];times=hourly['time'];radiation=hourly['global_tilted_irradiance']
        if len(times)!=len(radiation):raise ValueError("Unvollständige Wetterprognose.")
        values={}
        for stamp,value in zip(times,radiation):
            if value is not None:values[float(stamp)]=nonnegative(value)/1000*plane.kwp*site.performance_ratio
        planes.append(values)
    if len(planes)!=len(site.arrays):raise ValueError("Unvollständige Wetterprognose.")
    shared=set(planes[0])
    for plane in planes[1:]:shared&=set(plane)
    intervals=[]
    for end in sorted(shared):
        power_kw=sum(plane[end] for plane in planes)
        if site.measurement_side=='ac' and site.inverter_kw is not None:power_kw=min(power_kw,site.inverter_kw)
        intervals.append((end-3600,end,power_kw))
    return daily_intervals(intervals,tz)


async def fetch_forecast(provider,site,tz,now,reserve):
    parts=[]
    async with httpx.AsyncClient(timeout=httpx.Timeout(15,connect=5),follow_redirects=False,headers={"Accept":"application/json","User-Agent":"Energieboard PV forecast"}) as client:
        async def get(url,params=None,headers=None):
            await reserve(provider,now)
            try:
                response=await client.get(url,params=params,headers=headers)
                if response.status_code>=300:
                    retry=3600
                    if response.status_code==429:
                        raw=response.headers.get('Retry-After','')
                        try:retry=max(60,float(raw))
                        except ValueError:
                            try:retry=max(60,parsedate_to_datetime(raw).timestamp()-now)
                            except (ValueError,TypeError):pass
                    raise ForecastError("Prognoseanbieter meldet HTTP "+str(response.status_code)+".",min(retry,86400))
                if len(response.content)>2_000_000:raise ForecastError("Prognoseantwort ist zu groß.")
                return response.json()
            except httpx.HTTPError as exc:
                raise ForecastError("Prognoseanbieter nicht erreichbar.") from exc
        try:
            if provider.kind=='vrm':
                zone=ZoneInfo(tz);date=datetime.fromtimestamp(now,zone).date();a=datetime.combine(date,datetime.min.time(),zone).timestamp();b=datetime.combine(date+timedelta(days=3),datetime.min.time(),zone).timestamp()
                data=await get('https://vrmapi.victronenergy.com/v2/installations/'+provider.vrm_installation_id+'/stats',{"start":int(a),"end":int(b),"type":"forecast","interval":"hours"},{"X-Authorization":"Token "+provider.token})
                parts.append(parse_vrm(data,tz))
            elif provider.kind=='solcast':
                for resource in provider.solcast_resource_ids:
                    data=await get('https://api.solcast.com.au/rooftop_sites/'+resource+'/forecasts',{"format":"json"},{"Authorization":"Bearer "+provider.token})
                    parts.append(parse_solcast(data,tz))
            elif provider.kind=='forecast_solar':
                for plane in site.arrays:
                    path='/estimate/'+ '/'.join(map(str,(site.latitude,site.longitude,plane.tilt,plane.azimuth,plane.kwp)))
                    parts.append(parse_forecast_solar(await get('https://api.forecast.solar'+path),tz))
            else:
                payloads=[]
                for plane in site.arrays:
                    data=await get('https://api.open-meteo.com/v1/forecast',{"latitude":site.latitude,"longitude":site.longitude,"hourly":"global_tilted_irradiance","tilt":plane.tilt,"azimuth":plane.azimuth,"timeformat":"unixtime","timezone":"UTC","past_days":1,"forecast_days":3})
                    payloads.append(data)
                parts.append(parse_open_meteo_arrays(payloads,site,tz))
            result=combine_days(parts)
            if not result:raise ForecastError("Keine vollständigen gemeinsamen Prognosedaten verfügbar.")
            return result
        except ForecastError:raise
        except (KeyError,ValueError,TypeError,IndexError,OverflowError) as exc:
            raise ForecastError("Prognoseantwort konnte nicht ausgewertet werden.") from exc
