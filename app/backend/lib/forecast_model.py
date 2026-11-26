"""Auditable day-ahead calibration. Never fit and score against the same day."""
import hashlib,json,math,statistics
from datetime import date,timedelta


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def site_revision(site,tz):
    return fingerprint({"latitude":site.latitude,"longitude":site.longitude,"arrays":sorted((p.kwp,p.tilt,p.azimuth) for p in site.arrays),"flows":sorted(site.actual_flow_ids),"side":site.measurement_side,"ratio":site.performance_ratio,"inverter":site.inverter_kw,"timezone":tz,"freeze":site.freeze_time,"curtailment":site.curtailment_point})


def provider_revision(provider):
    data={"kind":provider.kind,"site":provider.site_id,"vrm":provider.vrm_installation_id,"solcast":sorted(provider.solcast_resource_ids)}
    if provider.kind=="vrm":data["normalization_version"]=2
    return fingerprint(data)


def actual_signature(flows,points=None,extra_refs=()):
    keys=('power_total','power_l1','power_l2','power_l3','energy_total','energy_l1','energy_l2','energy_l3')
    mappings=sorted((f.id,f.power_unit,f.energy_unit,f.invert,f.power_phase_mode,f.energy_phase_mode,tuple((k,f.datapoints.get(k)) for k in keys)) for f in flows)
    refs={f.datapoints.get(k).removeprefix("point:") for f in flows for k in keys if f.datapoints.get(k).startswith("point:")}
    refs.update(ref.removeprefix("point:") for ref in extra_refs if ref.startswith("point:"))
    registry=[{k:v for k,v in p.items() if k not in ("_id","name","history_key","legacy_until")} for p in (points or []) if p["id"] in refs]
    return fingerprint({"flows":mappings,"measurements":sorted(registry,key=lambda p:p["id"])})


def eligible_history(records,site,target_day,as_of):
    earliest=(date.fromisoformat(target_day)-timedelta(days=site.training_days)).isoformat()
    def excluded_then(row):
        changes=[v for v in row.get('exclusion_log',[]) if v['changed_at']<=as_of]
        return max(changes,key=lambda v:v['changed_at'])['excluded'] if changes else row.get('excluded_at') is not None and row['excluded_at']<=as_of
    return [r for r in records if earliest<=r['day']<target_day and r.get('revision')==site.revision and r.get('base_eligible',r.get('eligible',False)) and r.get('evaluated_at',math.inf)<=as_of and not excluded_then(r) and r.get('actual_kwh') is not None]


def calibration(provider_id,revision,history,minimum):
    rows=[]
    for day in history:
        prediction=next((f for f in day.get('forecasts',[]) if f['provider_id']==provider_id and f.get('revision')==revision),None)
        if prediction:rows.append((day['actual_kwh'],prediction))
    ratios=[actual/p['raw_kwh'] for actual,p in rows if p['raw_kwh']>=.1]
    factor=1.
    if len(ratios)>=minimum:
        shrink=len(ratios)/(len(ratios)+minimum)
        factor=max(.5,min(1.5,1+(statistics.median(ratios)-1)*shrink))
    candidates=[(a,p) for a,p in rows if abs(p.get('candidate_factor',1)-1)>1e-6 and p.get('candidate_kwh') is not None]
    raw_candidate_mae=statistics.mean(abs(a-p['raw_kwh']) for a,p in candidates) if candidates else None
    candidate_mae=statistics.mean(abs(a-p['candidate_kwh']) for a,p in candidates) if candidates else None
    use_corrected=len(candidates)>=minimum and candidate_mae is not None and candidate_mae<raw_candidate_mae
    score=statistics.mean(abs(a-p.get('used_kwh',p['raw_kwh'])) for a,p in rows) if len(rows)>=minimum else None
    return {"candidate_factor":round(factor,6),"applied_factor":round(factor if use_corrected else 1.,6),"use_corrected":use_corrected,"training_days":len(rows),"ratio_days":len(ratios),"candidate_days":len(candidates),"raw_mae":statistics.mean(abs(a-p['raw_kwh']) for a,p in rows) if rows else None,"candidate_mae":candidate_mae,"raw_candidate_mae":raw_candidate_mae,"score":score}


def normalise_weights(scores,epsilon=.1,cap=.7):
    if not scores:return {}
    known=[s for s in scores.values() if s is not None]
    neutral=statistics.median(known) if known else 1.
    raw={key:1/(epsilon+(score if score is not None else neutral)) for key,score in scores.items()}
    total=sum(raw.values());weights={key:value/total for key,value in raw.items()}
    if len(weights)>1:
        dominant=max(weights,key=weights.get)
        if weights[dominant]>cap:
            remaining=sum(value for key,value in weights.items() if key!=dominant)
            weights={key:(cap if key==dominant else value*(1-cap)/remaining) for key,value in weights.items()}
    return weights


def build_prediction(site,day,as_of,estimates,records):
    history=eligible_history(records,site,day,as_of);forecasts=[]
    for estimate in estimates:
        if not estimate.get('complete') or estimate.get('raw_kwh') is None:continue
        raw=estimate['raw_kwh'];model=calibration(estimate['provider_id'],estimate['revision'],history,site.minimum_training_days)
        forecasts.append({**estimate,**model,"candidate_kwh":round(raw*model['candidate_factor'],6),"used_kwh":round(raw*model['applied_factor'],6),"offset_kwh":round(raw*(model['applied_factor']-1),6)})
    mode=site.weighting_mode
    cap=site.max_auto_weight_pct/100
    for f in forecasts:
        group=f.get('dependency_group','auto')
        f['effective_group']=(f['family'] if group=='auto' else group) if site.group_correlated_sources and group!='independent' else '__provider__:'+f['provider_id']
    if mode in ('equal','manual'):
        weights={f['provider_id']:(f.get('manual_weight',1.) if mode=='manual' else 1.) for f in forecasts}
        total=sum(weights.values())
        for f in forecasts:f['weight']=weights[f['provider_id']]/total if total else 0.
    else:
        families={f['effective_group'] for f in forecasts};within={};family_scores={}
        for family in sorted(families):
            members=[f for f in forecasts if f['effective_group']==family]
            within[family]=normalise_weights({f['provider_id']:f['score'] for f in members},cap=cap)
            known=[f['score'] for f in members if f['score'] is not None]
            family_scores[family]=statistics.mean(known) if known else None
        family_weights=normalise_weights(family_scores,cap=cap)
        for f in forecasts:f['weight']=family_weights[f['effective_group']]*within[f['effective_group']][f['provider_id']]
    available=any(f['weight']>0 for f in forecasts)
    raw=sum(f['raw_kwh']*f['weight'] for f in forecasts) if available else None
    used=sum(f['used_kwh']*f['weight'] for f in forecasts) if available else None
    past_errors=sorted(abs(r['actual_kwh']-r['ensemble_kwh']) for r in history if r.get('ensemble_kwh') is not None)
    spread=past_errors[min(len(past_errors)-1,math.ceil(.8*len(past_errors))-1)] if len(past_errors)>=site.minimum_training_days else None
    return {"forecasts":forecasts,"raw_ensemble_kwh":raw,"ensemble_kwh":used,"error_spread_kwh":spread,"training_days":len(history),"algorithm":"day-ahead-v2","weighting":{"mode":mode,"group_correlated_sources":site.group_correlated_sources,"max_auto_weight_pct":site.max_auto_weight_pct},"weighting_note":"Alle verfügbaren Quellen haben Gewicht 0." if forecasts and not available else ""}


def evaluate_prediction(record,actual,complete,reason=None):
    result={"actual_kwh":actual,"base_eligible":bool(complete and actual is not None and record.get('forecasts') and not reason),"quality_reason":reason or ("Messhistorie unvollständig." if not complete else "Keine Tagesanfangsprognose verfügbar." if not record.get('forecasts') else "")}
    result['eligible']=result['base_eligible'] and record.get('excluded_at') is None
    rows=record.get('forecasts',[])
    if complete and actual is not None:
        result['errors']=[{"provider_id":f['provider_id'],"raw_error":actual-f['raw_kwh'],"raw_absolute_error":abs(actual-f['raw_kwh']),"used_error":actual-f['used_kwh'],"used_absolute_error":abs(actual-f['used_kwh']),"candidate_absolute_error":abs(actual-f['candidate_kwh'])} for f in rows]
        result['winner_provider_id']=min(rows,key=lambda f:abs(actual-f['raw_kwh']))['provider_id'] if rows else None
        result['ensemble_absolute_error']=abs(actual-record['ensemble_kwh']) if record.get('ensemble_kwh') is not None else None
        result['raw_ensemble_absolute_error']=abs(actual-record['raw_ensemble_kwh']) if record.get('raw_ensemble_kwh') is not None else None
    return result
