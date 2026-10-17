"""Fetch the full public Hexagon catalogue and save a timestamped snapshot.

Reads:  GET https://hexagonmath.org/api/v1/works (cursor-paginated JSON).
Writes: data/hexagon_works_<UTC date>.json  +  data/hexagon_works_latest.json

With --details (default on), also fetches each work's detail record
(GET /api/v1/works/<id>, same API) which carries the free-text provenance
statement absent from the list projection:
  data/hexagon_details_<UTC date>.json  +  data/hexagon_details_latest.json

Stdlib only. Run:  python scan_hexagon.py [--limit 100] [--out data]

The API rejects requests without a browser-like User-Agent (403), so we send
one. Anonymous reads are rate-limited; this script is sequential and sleeps
briefly between requests.
"""

import argparse
import datetime
import json
import pathlib
import time
import urllib.parse
import urllib.request

BASE = "https://hexagonmath.org/api/v1/works"
UA = "notes-research/1.0 (reproducible archive scan; contact via repo)"


def fetch_page(cursor, limit):
    url = BASE + f"?limit={limit}"
    if cursor:
        url += "&cursor=" + urllib.parse.quote(cursor)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def fetch_detail(versioned_id):
    url = f"https://hexagonmath.org/api/v1/works/{versioned_id}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["work"]


def load_detail_cache(outdir):
    '''Load previously fetched detail records from disk, keyed by versioned id.'''
    cache = {}
    paths = sorted(outdir.glob("hexagon_details_*.json"))
    # dated snapshots first, then latest (which overwrites with most recent)
    for p in paths:
        if p.name.endswith("_latest.json"):
            continue
        _ingest_detail_file(p, cache)
    latest = outdir / "hexagon_details_latest.json"
    if latest.exists():
        _ingest_detail_file(latest, cache)
    return cache


def _ingest_detail_file(path, cache):
    try:
        snap = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    for d in snap.get("works", []) or []:
        for key in (d.get("id"), d.get("identifier")):
            if key:
                cache[str(key).split("hexagon:")[-1]] = d
                cache["hexagon:" + str(key).split("hexagon:")[-1]] = d
        # also key by versioned id without prefix already handled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--out", default="data")
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--no-details", action="store_true",
                    help="skip per-work detail records (provenance statements)")
    ap.add_argument("--detail-sleep", type=float, default=0.3)
    args = ap.parse_args()

    here = pathlib.Path(__file__).resolve().parent
    outdir = here / args.out
    outdir.mkdir(parents=True, exist_ok=True)

    works = []
    cursor = None
    total = None
    while True:
        page = fetch_page(cursor, args.limit)
        works.extend(page["works"])
        total = page["page"].get("total", total)
        cursor = page["page"].get("next_cursor")
        print(f"fetched {len(works)}/{total} ...", flush=True)
        if not page["page"].get("has_more"):
            break
        time.sleep(args.sleep)

    stamp = datetime.datetime.now(datetime.timezone.utc)
    snapshot = {
        "fetched_at": stamp.isoformat(timespec="seconds"),
        "source": BASE,
        "total_reported": total,
        "n_works": len(works),
        "works": works,
    }
    day = stamp.strftime("%Y%m%d")
    dated = outdir / f"hexagon_works_{day}.json"
    latest = outdir / "hexagon_works_latest.json"
    dated.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False), encoding="utf-8")
    latest.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {dated} ({len(works)} works)")
    print(f"wrote {latest}")

    if not args.no_details:
        # Reuse detail records we already have on disk (keyed by versioned id)
        # so a re-run only fetches genuinely new/changed works.
        cache = load_detail_cache(outdir)
        details = []
        for i, w in enumerate(works):
            vid = (w.get("id") or "").split("hexagon:")[-1]
            cached = cache.get(vid) or cache.get("hexagon:" + vid)
            if cached is not None and not cached.get("detail_error"):
                details.append(cached)
                print(f"  detail {i + 1}/{len(works)} {vid} (cached)", flush=True)
                continue
            try:
                d = fetch_detail(vid)
            except Exception as e:  # keep going; record the miss
                print(f"  detail fetch failed for {vid}: {e}")
                d = {"identifier": w.get("identifier"), "detail_error": str(e)}
            details.append(d)
            print(f"  detail {i + 1}/{len(works)} {vid}", flush=True)
            time.sleep(args.detail_sleep)
        dsnap = {
            "fetched_at": stamp.isoformat(timespec="seconds"),
            "n_works": len(details),
            "works": details,
        }
        d_dated = outdir / f"hexagon_details_{day}.json"
        d_latest = outdir / "hexagon_details_latest.json"
        d_dated.write_text(json.dumps(dsnap, indent=1, ensure_ascii=False), encoding="utf-8")
        d_latest.write_text(json.dumps(dsnap, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {d_dated} ({len(details)} detail records)")
        print(f"wrote {d_latest}")


if __name__ == "__main__":
    main()
