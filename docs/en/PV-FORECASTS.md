# PV forecasts and evaluation

[Documentation](README.md) · [Deutsch](../PV-PROGNOSEN.md)

Available under **PV forecast** (`/prognose`) from 2.7. Sources are disabled initially. The server needs outbound HTTPS, a correct clock and recorded actual PV yield. These instructions assume **private use**. Check the current free-account conditions with each provider.

## Establish a reliable actual yield

Record DC power and preferably a cumulative PV energy counter under **Data acquisition**, then configure the corresponding DC MPPT. A dedicated PV inverter's AC yield is also suitable if the system is defined on the AC side.

Do **not** use a hybrid inverter's AC output as pure PV yield: it includes battery and possibly grid energy. Select separate MPPTs only when their physical measurement boundaries do not overlap. Do not select a total counter together with its component counters. Identical data point mappings are rejected; detecting physically overlapping meters remains your responsibility.

Cumulative energy counter differences take precedence over power integration. Training requires a fully completed day with complete energy and at least 98% time coverage. Missing history is not reconstructed.

## Configure a PV system

1. Choose **Add PV system**, enter a name, latitude, longitude and optional timezone. Blank timezone uses the system setting.
2. Select actual PV yield sources and their side: **DC**, **AC**, or intentionally **mixed**. For a Victron DC bus, MPPT yield is normally the appropriate reference.
3. Add each physical array's installed **kWp**, tilt and azimuth. South = 0°, east = −90°, west = 90°, north = ±180°. Horizontal tilt = 0°.
4. Set **Freeze start-of-day forecast at**, default **00:05 local time**. Responses must have arrived before this cutoff. A system first configured after the cutoff normally has no morning prediction on that first day.
5. Default training window: **45 days**; minimum: **7 valid days**. Open-Meteo's local model uses kWp × tilted irradiance × performance ratio, default 0.85. Adjust the ratio for the chosen measurement side. An optional AC limit caps the combined output of all arrays only when the actual measurement side is AC.
6. Optionally assign an enabled, recorded boolean **curtailment** measurement: 1 means curtailed. A day with any curtailment or incomplete curtailment history is excluded from training.
7. Enable and save the system, then add and enable forecast sources.

## Four sources

| Source | Configuration | Notes |
|---|---|---|
| Victron VRM | Personal access token and installation ID | Native PV forecast for an existing VRM installation. Configure location and yield history in VRM. Uses `X-Authorization: Token …`, not the deprecated Bearer login. |
| Forecast.Solar | No account for the public free API | Today and tomorrow; each configured array requires a request. Maintenance can affect availability. |
| Solcast Hobbyist | Private hobbyist account, token, one or two rooftop resource IDs | Typical provider allowance: ten requests per UTC day. Energieboard reserves at most **eight per token/UTC day**. Two rooftops need two requests per refresh. Other applications sharing your token consume additional provider allowance. |
| Open-Meteo | No token | Free weather API for private use; **locally modelled PV yield from irradiance**, not a native PV yield service. Shading, snow and real temperature losses are not fully represented. Attribution remains visible. |

Official references: [VRM API](https://vrm-api-docs.victronenergy.com/), [VRM forecast uses Solcast](https://professional.victronenergy.com/news/detail/212/), [Forecast.Solar](https://forecast.solar/), [Solcast Hobbyist](https://docs.solcast.com.au/docs/section/rooftop-sites-hobbyist), [Open-Meteo API](https://open-meteo.com/en/docs), [Open-Meteo usage conditions](https://open-meteo.com/en/pricing).

Scheduled refreshes run approximately every six hours; the scheduler checks every minute. Application limits also cap VRM at 48/day and 30/hour, Forecast.Solar at 120/day and 10/hour, and Open-Meteo at 120/day and 30/hour. These are local safeguards, not a guaranteed provider allowance. Manual refresh respects quotas, a 15-minute minimum interval and error backoff. HTTP 429 honours `Retry-After`. Failed requests also consume reservations. Persistent MongoDB counters survive restarts.

Tokens are used on the server and omitted from normal API responses and CSV. Blank token fields retain the stored token; use the explicit deletion checkbox to remove it. Full database backups contain credentials and need protected storage. Expose the dashboard only inside a trusted network or behind an authenticated reverse proxy.

## Calibration and fair comparisons

- At the cutoff, freeze the most recent **complete** daily forecast received before that time and no more than 18 hours old. Local day boundaries handle 23- and 25-hour daylight-saving days.
- Frozen forecasts never change. Later fetches may update **latest forecast** and **tomorrow** only. After downtime, only previously stored responses from before the cutoff can become morning predictions. Late forecasts are never backdated.
- At least ten minutes after the day ends, compare actual kWh against each original morning forecast. The closest absolute kWh error wins. Missing values are never treated as zero.
- The candidate multiplier uses the median of earlier actual/forecast ratios, shrinks towards 1 with little data, and is bounded to **0.5–1.5**. Forecasts below 0.1 kWh do not influence the multiplier.
- After at least seven suitable days, a candidate may be calculated. It is applied only after beating the original forecasts on at least seven **additional** days. Until then the original is used. If the candidate becomes worse, the multiplier returns to 1. With defaults, correction therefore starts after roughly 14 suitable days at the earliest.
- Lower past mean absolute errors receive more weight. A single voice is capped at 70% when multiple voices exist. Since VRM uses Solcast irradiance, VRM and Solcast are blended within one family before weighting that family against independent sources.
- Daily logs retain raw yield, candidate and applied factors, kWh offset, weights, training counts, actual yield and exclusion reasons. Offset = **original × (applied factor − 1)**; no constant night-time yield is invented. Geometry, measurement-side and relevant source changes establish a new training basis while retaining past logs.
- The displayed historical error range is the 80th percentile of absolute ensemble errors. It is **not a guaranteed 80% confidence interval**, nor a promise of improvement every day.

Exclude snow, maintenance, outages or unmeasured curtailment in **Daily comparison and model log**, with a reason. Every exclusion change is audited and affects future training only; previous forecasts remain unchanged. Exclusions can be removed. Do not compare incompatible measurement boundaries.

Provider rankings show MAE in kWh and the number of valid days. Rankings based on different numbers of days are only partly comparable. The blend's error is scored against frozen morning predictions, never retrospectively updated previews.

## Troubleshooting

**No morning forecast:** configured after cutoff, no complete response before cutoff, provider failure or cached data over 18 hours old. Wait for the next correctly prepared day.

**No actual yield or training days:** check recording, counters, units, timezone, measurement side and curtailment signal. Failure of one provider does not prevent others from being evaluated.

**No correction after one week:** initial days train the factor. It must then outperform the originals on subsequent days; missing/excluded days extend this period.
