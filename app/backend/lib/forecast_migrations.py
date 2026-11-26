"""Audited repair of VRM Wh values mislabelled as kWh by release 2.7.0."""
from copy import deepcopy
import time
from lib.db import db
from lib.forecast_model import provider_revision,evaluate_prediction
from models.forecast import ForecastProvider

CALCULATION_FIELDS=('forecasts','raw_ensemble_kwh','ensemble_kwh','error_spread_kwh','errors','winner_provider_id','ensemble_absolute_error','raw_ensemble_absolute_error')

def corrected_day(document,vrm_ids,now):
    row=deepcopy(document)
    affected=[f for f in row.get('forecasts',[]) if (f.get('provider_kind')=='vrm' or f['provider_id'] in vrm_ids) and f.get('normalization_version',1)<2]
    if not affected:return None
    row['vrm_unit_correction_original']={key:deepcopy(document[key]) for key in CALCULATION_FIELDS if key in document}
    for forecast in affected:
        for key in ('raw_kwh','used_kwh','candidate_kwh','offset_kwh'):
            if forecast.get(key) is not None:forecast[key]/=1000
        forecast.update(normalization_version=2,provider_kind='vrm')
        # Old error statistics came from the wrong unit; do not show them as valid.
        for key in ('score','raw_mae','candidate_mae','raw_candidate_mae'):forecast[key]=None
    forecasts=row['forecasts'];positive=any(f.get('weight',0)>0 for f in forecasts)
    for result,source in (('raw_ensemble_kwh','raw_kwh'),('ensemble_kwh','used_kwh')):
        row[result]=sum(f[source]*f.get('weight',0) for f in forecasts) if positive else None
    row['error_spread_kwh']=None
    if row.get('actual_kwh') is not None and ('errors' in row or row.get('ensemble_absolute_error') is not None):
        evaluated=evaluate_prediction(row,row['actual_kwh'],True)
        for key in ('errors','winner_provider_id','ensemble_absolute_error','raw_ensemble_absolute_error'):
            if key in evaluated:row[key]=evaluated[key]
    row['vrm_unit_correction']={'version':2,'at':now,'factor':.001,'provider_ids':[f['provider_id'] for f in affected]}
    return row

async def repair_vrm_units():
    providers=[ForecastProvider(**p) for p in await db.forecast_providers.find({'kind':'vrm'},{'_id':0}).to_list()]
    ids={p.id for p in providers};now=time.time()
    for p in providers:
        revision=provider_revision(p)
        # A parser revision deliberately starts fresh VRM calibration. Frozen
        # records retain their original provider revision and observed weights.
        await db.forecast_providers.update_one({'id':p.id},{'$set':{'revision':revision}})
        if p.revision!=revision:
            await db.forecast_state.update_one({'id':p.id},{'$set':{'next_at':0}},upsert=True)
        query={'provider_id':p.id,'normalization_version':{'$ne':2}}
        async for snapshot in db.forecast_snapshots.find(query):
            snapshot['vrm_unit_correction_original']={'raw_kwh':snapshot['raw_kwh'],'revision':snapshot.get('revision')}
            snapshot.update(raw_kwh=snapshot['raw_kwh']/1000,normalization_version=2,provider_kind='vrm',revision=revision,vrm_unit_correction={'version':2,'at':now,'factor':.001})
            await db.forecast_snapshots.replace_one({'_id':snapshot['_id'],'normalization_version':{'$ne':2}},snapshot)
    async for row in db.forecast_days.find({'$or':[{'forecasts.provider_id':{'$in':sorted(ids)}},{'forecasts.provider_kind':'vrm'}]}):
        repaired=corrected_day(row,ids,now)
        if repaired is not None:await db.forecast_days.replace_one({'_id':row['_id']},repaired)
