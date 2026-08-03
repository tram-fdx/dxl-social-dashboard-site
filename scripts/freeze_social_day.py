#!/usr/bin/env python3
"""Freeze one day of the DXL social dashboard.

index.html is the live report of the newest scan; the date picker in it NAVIGATES,
it never recomputes. An older day is served by its own frozen copy under archive/.
This script makes that frozen copy correctly: it strips the picker (which would
404 on data/index.json from inside archive/), rewrites relative links, inserts the
archive banner, and registers the day in data/index.json.

Refuses to overwrite an existing archive file unless --force, and refuses to run at
all if data/<date>.json does not exist -- the JSON is the source of truth.

  python3 scripts/freeze_social_day.py --repo /tmp/socialrepo --date 2026-08-03 \
      --label-vi "..." --label-en "..." [--dry-run] [--force]
"""
import argparse, io, json, os, re, sys

BANNER = (
 '<div id="archive-banner" style="background:#fdf4e3;border-bottom:1px solid #f0dcb4;'
 'color:#b7791f;font-size:12.5px;padding:9px 18px;text-align:center;font-weight:600;'
 'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif">'
 '\U0001F5C3 Bản lưu ngày {vi} — dashboard này đã đóng băng, không cập nhật nữa. '
 '<a href="../index.html" style="color:#b4451f">Xem bản mới nhất</a> · '
 '<a href="../history.html" style="color:#b4451f">Lịch sử dữ liệu theo ngày</a>'
 '<span style="opacity:.6"> · </span>'
 'Archived copy of {en} — frozen, no longer updated.'
 '</div>')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True); ap.add_argument('--date', required=True)
    ap.add_argument('--label-vi', required=True); ap.add_argument('--label-en', required=True)
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--force', action='store_true')
    a = ap.parse_args()

    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', a.date):
        sys.exit('date must be YYYY-MM-DD')
    R = a.repo
    dj = os.path.join(R, 'data', a.date + '.json')
    if not os.path.exists(dj):
        sys.exit('refusing: %s does not exist. Write the day JSON first.' % dj)
    src = os.path.join(R, 'index.html')
    out = os.path.join(R, 'archive', a.date + '.html')
    if os.path.exists(out) and not a.force:
        sys.exit('refusing: %s already exists (use --force only to correct a bad freeze)' % out)

    html = io.open(src, encoding='utf-8').read()
    n0 = len(html)

    # 1. strip the picker section and the metastrip -- both depend on data/index.json
    html, nsec = re.subn(r'<section class="card" id="sec-filter">.*?</section>\s*', '', html, flags=re.S)
    html, nms = re.subn(r'<div class="metastrip" id="metastrip"></div>\s*', '', html)
    if nsec != 1:
        sys.exit('expected exactly 1 #sec-filter section, found %d' % nsec)

    # 2. rewrite links for a page that now lives one directory down
    links = 0
    for pat, rep in ((r'href="history\.html"', 'href="../history.html"'),
                     (r'href="index\.html"', 'href="../index.html"'),
                     (r'href="archive/', 'href="')):
        html, k = re.subn(pat, rep, html); links += k

    # 3. banner
    d = a.date.split('-')
    vi = '%s/%s/%s' % (d[2], d[1], d[0])
    en = a.date
    banner = BANNER.format(vi=vi, en=en)
    html, nb = re.subn(r'(<body[^>]*>)', lambda m: m.group(1) + banner, html, count=1)
    if nb != 1:
        sys.exit('could not find <body> to insert the banner after')

    # 4. manifest
    mf = os.path.join(R, 'data', 'index.json')
    man = json.load(io.open(mf, encoding='utf-8'))
    snaps = [s for s in man['snapshots'] if s['date'] != a.date]
    snaps.append({'date': a.date, 'data': 'data/%s.json' % a.date,
                  'report': 'archive/%s.html' % a.date,
                  'label_vi': a.label_vi, 'label_en': a.label_en})
    snaps.sort(key=lambda s: s['date'])
    prev_latest = man.get('latest')
    man['snapshots'] = snaps
    man['latest'] = max(s['date'] for s in snaps)

    print('freeze %s  (%s)' % (a.date, 'dry run' if a.dry_run else 'writing'))
    print('  source        index.html  %d bytes' % n0)
    print('  archive       archive/%s.html  %d bytes' % (a.date, len(html)))
    print('  picker        stripped #sec-filter (%d) + metastrip (%d), %d chars removed' % (nsec, nms, n0 - len(html) + len(banner)))
    print('  banner        inserted after <body>: %s / %s' % (vi, en))
    print('  links         rewritten: %d' % links)
    print('  manifest      latest %s -> %s, %d day(s) total' % (prev_latest, man['latest'], len(snaps)))
    if a.dry_run:
        print('\nnothing written. Re-run without --dry-run once the summary reads right.')
        return
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, 'w', encoding='utf-8').write(html)
    io.open(mf, 'w', encoding='utf-8').write(json.dumps(man, ensure_ascii=False, indent=2) + '\n')
    print('\nwrote archive/%s.html and data/index.json' % a.date)

if __name__ == '__main__':
    main()
