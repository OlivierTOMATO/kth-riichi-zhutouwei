"""Import a Mahjong Soul (雀魂) game into games/ from its Mortal review report.

Logging in to Mahjong Soul directly no longer works for third-party tools (the server answers
error 151 to every non-official client), so the game log comes from mjai.ekyu.moe instead:

  1. Record the game from the result screenshot first (final scores only), e.g. games/s2-hanchan-09-*.json.
  2. Submit the 雀魂 paipu link on https://mjai.ekyu.moe (KillerDucky view) and copy the report address.
  3. python3 tools/majsoul.py 'https://mjai.ekyu.moe/killerducky/?data=/report/<id>.json' --no 9

The report hides player names (Aさん…), so seats are matched to players through the final scores
already recorded in step 1. Every hand's point changes and each round's starting scores are checked
against the report; the file is only rewritten when everything matches. The report is cached in
majsoul/ (gitignored). The report also carries the Mortal rating of the seat that was reviewed.
"""
import argparse
import glob
import json
import math
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "majsoul"
SEASON = 2
LEVELS = {"満貫": 5, "跳満": 6, "倍満": 8, "三倍満": 11, "数え役満": 11}   # 无数え役满: 13+ han caps at 三倍满


def load_report(src):
    m = re.search(r"report/([0-9a-f]+)\.json", src)
    if m:
        path = CACHE / f"{m.group(1)}.json"
        if not path.exists():
            CACHE.mkdir(exist_ok=True)
            req = urllib.request.Request(f"https://mjai.ekyu.moe/report/{m.group(1)}.json",
                                         headers={"User-Agent": "kth-open-scoreboard"})
            path.write_bytes(urllib.request.urlopen(req, timeout=30).read())
        src = path
    return json.loads(Path(src).read_text())


def base_pts(han, fu):
    if han >= 13: return 8000 * (han // 13)
    if han >= 11: return 6000
    if han >= 8: return 4000
    if han >= 6: return 3000
    if han >= 5: return 2000
    b = fu * 2 ** (han + 2)
    return 2000 if b >= 1920 else b


def hand_delta(hd, r, h, pot):
    """Point changes of one hand under the site's rules (mirror of scoring.js replay)."""
    dealer, d = r % 4, [0, 0, 0, 0]
    for i in hd.get("riichi", []):
        d[i] -= 1000; pot += 1000
    if hd["kind"] in ("ron", "tsumo"):
        w, b = hd["winner"], base_pts(hd["han"], hd["fu"])
        mult = 6 if w == dealer else 4
        p = hd.get("pao") if hd["han"] >= 13 and hd.get("pao") not in (None, w, hd.get("loser")) else None
        pv, tot = 8000 * mult, 0
        if hd["kind"] == "ron":
            l, v = hd["loser"], math.ceil(b * mult / 100) * 100
            if p is not None:
                fp, fl = pv // 2 + 300 * h, v - pv // 2
                d[p] -= fp; d[l] -= fl; tot = fp + fl
            else:
                tot = v + 300 * h; d[l] -= tot
        else:
            def all_pay(bb):
                nonlocal tot
                for i in range(4):
                    if i != w:
                        x = math.ceil(bb * (2 if w == dealer or i == dealer else 1) / 100) * 100
                        d[i] -= x; tot += x
            if p is not None:
                d[p] -= pv + 300 * h; tot += pv + 300 * h
                if b > 8000: all_pay(b - 8000)
            else:
                all_pay(b)
                for i in range(4):
                    if i != w: d[i] -= 100 * h; tot += 100 * h
        d[w] += tot + pot; pot = 0
        keep, draw = w == dealer, False
    else:
        t = hd["tenpai"]
        if 0 < len(t) < 4:
            for i in range(4): d[i] += 3000 // len(t) if i in t else -3000 // (4 - len(t))
        keep, draw = dealer in t, True
    r, h = (r, h + 1) if keep else (r + 1, h + 1 if draw else 0)
    return d, r, h, pot


def han_fu(info):
    """Tenhou-style agari info [who, from, pao, "30符2飜2000点", yaku...] -> (han, fu)."""
    s = info[3]
    m = re.match(r"(\d+)符(\d+)飜", s)
    if m:
        return int(m.group(2)), int(m.group(1))
    if "役満" in s and not s.startswith("数え役満"):
        return 13 * max(1, sum("役満" in y for y in info[4:])), 30
    for name in sorted(LEVELS, key=len, reverse=True):
        if s.startswith(name) or s.startswith("切り上げ" + name):
            return LEVELS[name], 30
    sys.exit(f"cannot read han/fu from {s!r}")


def convert(rep):
    kyokus = [k for part in rep["split_logs"] for k in part["log"]]
    riichi, cur = [], None                      # accepted riichi per kyoku, from the mjai event log
    for e in rep["mjai_log"]:
        if e["type"] == "start_kyoku":
            cur = []; riichi.append(cur)
        elif e["type"] == "reach_accepted":
            cur.append(e["actor"])
    if len(riichi) != len(kyokus):
        sys.exit(f"report has {len(kyokus)} hands but {len(riichi)} kyoku starts")
    hands, problems = [], []
    r = h = pot = 0
    s = [25000] * 4
    for n, k in enumerate(kyokus):
        (rr, hh, _), start, res = k[0], k[1], k[-1]
        if (rr, hh) != (r, h):
            problems.append(f"hand {n + 1}: report round {rr}/{hh}, site {r}/{h}")
        if list(start) != s:
            problems.append(f"hand {n + 1}: report start {start}, site {s}")
        if res[0] == "和了":
            if len(res) > 3:
                sys.exit(f"hand {n + 1}: double ron — the site plays 头跳; record it by hand")
            info = res[2]
            han, fu = han_fu(info)
            hd = {"kind": "tsumo" if info[0] == info[1] else "ron", "winner": info[0], "han": han, "fu": fu}
            if hd["kind"] == "ron":
                hd["loser"] = info[1]
            if han >= 13 and info[2] != info[0]:
                hd["pao"] = info[2]
        elif res[0] == "流局":
            dl = res[1] if len(res) > 1 else [0, 0, 0, 0]
            t = [i for i in range(4) if dl[i] > 0]
            if not t and n + 1 < len(kyokus):             # nobody or everybody tenpai: the dealer's renchan tells
                t = [0, 1, 2, 3] if kyokus[n + 1][0][0] == rr else []
            hd = {"kind": "draw", "tenpai": t}
        else:
            sys.exit(f"hand {n + 1}: {res[0]} (途中流局 etc.) — the site has none; record it by hand")
        hd["riichi"] = sorted(set(riichi[n]))
        before = pot
        d, r, h, pot = hand_delta(hd, r, h, pot)
        dl = res[1] if len(res) > 1 else [0, 0, 0, 0]
        want = [x - (1000 if i in hd["riichi"] else 0) for i, x in enumerate(dl)]  # report deltas exclude riichi deposits
        if d != want:
            problems.append(f"hand {n + 1}: site {d} vs report {want} (pot before {before})")
        s = [s[i] + d[i] for i in range(4)]
        hands.append(hd)
    if pot and r > 7:
        top = max(range(4), key=lambda i: (s[i], -i)); s[top] += pot
    return hands, s, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", help="mjai.ekyu.moe report address, or a saved report .json")
    ap.add_argument("--no", type=int, required=True, help="regular-season hanchan number already recorded with final scores")
    ap.add_argument("--stage", choices=["playoff", "casual"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rep = load_report(a.report)
    stage = a.stage or "hanchan"
    files = glob.glob(str(ROOT / f"games/s{SEASON}-{stage}-{a.no:02d}-*.json"))
    if len(files) != 1:
        sys.exit(f"need exactly one recorded game s{SEASON}-{stage}-{a.no:02d}-*.json with final scores, found {len(files)}")
    path = Path(files[0])
    g = json.loads(path.read_text())
    if not g.get("final"):
        sys.exit(f"{path.name} has no final scores to match seats against")
    by_score = {}
    for pid, sc in zip(g["seats"], g["final"]):
        by_score.setdefault(sc, []).append(pid)

    hands, final, problems = convert(rep)
    seats = []
    for sc in final:
        who = by_score.get(sc, [])
        if len(who) != 1:
            sys.exit(f"cannot tell who finished on {sc} (recorded finals {g['final']}, report finals {final})")
        seats.append(who[0])
    if len(set(seats)) != 4:
        sys.exit(f"seat matching is ambiguous: {seats}")

    names = {p["id"]: p["name"] for p in json.loads((ROOT / "roster.json").read_text())["players"]}
    pid = seats[rep["player_id"]] if 0 <= rep.get("player_id", -1) < 4 else None
    rating = (rep.get("review") or {}).get("rating")
    rv = rep.get("review") or {}
    print(f"seats 东南西北: {' / '.join(names[s] for s in seats)}; {len(hands)} hands; final {final}")
    if pid and rating is not None:
        print(f"Mortal: {names[pid]} rating {rating * 100:.1f}, match {rv.get('total_matches')}/{rv.get('total_reviewed')}")
    for p in problems:
        print("  CHECK:", p)
    if problems:
        sys.exit("not written: the report does not replay cleanly under the site's rules")
    g.update({"_players": " / ".join(names[s] for s in seats), "seats": seats, "final": None, "hands": hands})
    g["scorer"] = "雀魂牌谱（mjai.ekyu.moe 逐局）"
    if a.dry_run:
        print(json.dumps(g, ensure_ascii=False)[:400]); return
    path.write_text(json.dumps(g, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
