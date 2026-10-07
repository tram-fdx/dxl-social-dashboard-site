#!/usr/bin/env python3
"""Rebuild data/funnel.json (DERIVED, never hand-edit) for funnel.html.
Inputs: data/hubspot/YYYY-MM-DD.json (immutable HubSpot snapshots, read live in the daily run),
        data/rollup.json (social), <seo repo>/data/rollup.json (GA4/GSC/Ahrefs).
Usage: python3 scripts/build_funnel.py --repo . --seo ../dxliving-seo-report
"""
import argparse, json, glob, os, datetime as dt, math

ap = argparse.ArgumentParser()
ap.add_argument('--repo', default='.')
ap.add_argument('--seo', required=True)
a = ap.parse_args()

snaps = sorted(glob.glob(os.path.join(a.repo, 'data', 'hubspot', '*.json')))
if not snaps:
    raise SystemExit('no hubspot snapshots')
hs_all = [json.load(open(p)) for p in snaps]
hs = hs_all[-1]
soc = json.load(open(os.path.join(a.repo, 'data', 'rollup.json')))['series']
seo = json.load(open(os.path.join(a.seo, 'data', 'rollup.json')))['series']

def pts(series, k):
    return {p['d']: p['v'] for p in series.get(k, {}).get('points', []) if p.get('v') is not None}

def last(series, k):
    p = [x for x in series.get(k, {}).get('points', []) if x.get('v') is not None]
    return {'d': p[-1]['d'], 'v': p[-1]['v']} if p else None

def monday(d):
    x = dt.date.fromisoformat(d)
    return (x - dt.timedelta(days=x.weekday())).isoformat()

day_keys = ['fb_views_day', 'ig_views_day', 'fb_visits_day', 'fb_interactions_day', 'ig_interactions_day', 'fb_video3s_day']
wk = {}
for k in day_keys:
    for d, v in pts(soc, k).items():
        w = monday(d)
        o = wk.setdefault(w, {})
        o[k] = o.get(k, 0) + v
        o.setdefault('_days_' + k, set()).add(d)

weeks = []
for i, w in enumerate(hs['weeks']):
    m = wk.get(w, {})
    ndays = len(m.get('_days_fb_views_day', set()))
    row = {
        'w': w,
        'mkt_days': ndays,
        'mkt': {
            'views': (m.get('fb_views_day', 0) + m.get('ig_views_day', 0)) if ndays else None,
            'fb_views': m.get('fb_views_day') if ndays else None,
            'ig_views': m.get('ig_views_day') if ndays else None,
            'fb_visits': m.get('fb_visits_day') if ndays else None,
            'interactions': (m.get('fb_interactions_day', 0) + m.get('ig_interactions_day', 0)) if ndays else None,
            'video3s': m.get('fb_video3s_day') if ndays else None,
        },
        'hs': {
            'deals_created': hs['deals_created']['n'][i],
            'deals_created_amt': hs['deals_created']['amount'][i],
            'won': hs['deals_won']['n'][i],
            'won_amt': hs['deals_won']['amount'][i],
            'lost': sum(hs['deals_lost'][k][i] for k in ('not_interested', 'inhouse', 'competitor', 'other')),
            'lost_not_interested': hs['deals_lost']['not_interested'][i],
            'lost_inhouse': hs['deals_lost']['inhouse'][i],
            'lost_competitor': hs['deals_lost']['competitor'][i],
            'contacts_offline': hs['contacts_created']['offline'][i],
            'contacts_direct': hs['contacts_created']['direct'][i],
            'meetings': hs['meetings'][i],
        },
    }
    weeks.append(row)

def pearson(x, y):
    n = len(x)
    if n < 5:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((v - mx) ** 2 for v in x)); sy = math.sqrt(sum((v - my) ** 2 for v in y))
    if sx == 0 or sy == 0:
        return None
    return round(sum((a_ - mx) * (b_ - my) for a_, b_ in zip(x, y)) / (sx * sy), 2)

full = [r for r in weeks if r['mkt_days'] == 7]
def corr(mk, hk, lag):
    xs, ys = [], []
    for i, r in enumerate(full):
        j = i + lag
        if j >= len(full):
            break
        xs.append(r['mkt'][mk]); ys.append(full[j]['hs'][hk])
    return {'r': pearson(xs, ys), 'n': len(xs)}

corrs = []
for mk in ('views', 'fb_visits', 'interactions'):
    for hk in ('deals_created', 'meetings', 'won'):
        corrs.append({'mkt': mk, 'hs': hk, 'lag0': corr(mk, hk, 0), 'lag1': corr(mk, hk, 1)})

w28 = {
    'social_views': None,
    'fb_views': last(soc, 'fb_views_28d'), 'ig_views': last(soc, 'ig_views_28d'),
    'yt_views': last(soc, 'yt_views_28d'), 'li_impressions': last(soc, 'li_impressions_28d'),
    'li_page_views': last(soc, 'li_page_views_28d'), 'fb_visits': last(soc, 'fb_visits_28d'),
    'fb_interactions': last(soc, 'fb_interactions_28d'),
    'ga4_sessions': last(seo, 'ga4_sessions'), 'ga4_users': last(seo, 'ga4_users'),
    'ga4_key_events': last(seo, 'ga4_key_events'), 'gsc_clicks': last(seo, 'gsc_clicks'),
    'gsc_impressions': last(seo, 'gsc_impressions'), 'ahrefs_ai_citations': last(seo, 'ahrefs_ai_citations'),
}
fb, ig, yt, li = (w28[k] for k in ('fb_views', 'ig_views', 'yt_views', 'li_impressions'))
if all(fb and ig and yt and li for _ in [0]):
    w28['social_views'] = {'d': fb['d'], 'v': fb['v'] + ig['v'] + yt['v'] + li['v']}

# 28-day HubSpot window (sum of the last 4 complete-or-partial weeks ending today is NOT used:
# 28d contact counts come straight from the snapshot query).
hist = [{'date': s['date'], 'open_pipeline': s['open_pipeline_new_work_flow'], 'lifecycle': s['lifecycle_contacts'],
         'contact_source_total': s['contact_source_total']} for s in hs_all]

out = {
    'kind': 'funnel', 'derived': True,
    'generated_at': dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z',
    'as_of': hs['date'], 'hubspot_provenance': hs['provenance'], 'anomalies': hs['anomalies'],
    'weeks': weeks, 'window28': w28, 'correlations': corrs, 'correlation_weeks': [r['w'] for r in full],
    'open_pipeline': hs['open_pipeline_new_work_flow'], 'pipeline_totals': hs['pipeline_totals'],
    'lifecycle': hs['lifecycle_contacts'], 'contact_source_total': hs['contact_source_total'],
    'deal_source_total': hs['deal_source_total'], 'contacts_28d_by_source': hs['contacts_28d_by_source'],
    'hubspot_history': hist,
}
json.dump(out, open(os.path.join(a.repo, 'data', 'funnel.json'), 'w'), indent=1, ensure_ascii=False)
print('weeks', len(weeks), 'full', len(full), 'snapshots', len(hs_all))
for c in corrs:
    print(c['mkt'], c['hs'], c['lag0'], c['lag1'])
