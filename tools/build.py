"""Build the scoreboard's data.json from roster.json + games/*.json.

    python3 tools/build.py                 # validate, write ./data.json
    python3 tools/build.py --out _site     # validate, write _site/ (used by the Pages workflow)
    python3 tools/build.py --check FILE..  # validate only (used on pull requests)
    python3 tools/build.py --import-export # copy a Claude-recorder export (.export/) into roster.json + games/

Every game file is one hanchan, in the same shape the recorder page submits:
    {"no": 1, "table": "", "seats": [4 player ids, 东南西北], "hands": [...], "final": null|[4 scores],
     "createdAt": ms, "scorer": "who recorded it"}
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ["index.html", "record.html", "scoring.js"]
KINDS = {"ron", "tsumo", "draw", "manual"}
HANS = {1, 2, 3, 4, 5, 6, 8, 11, 13, 26, 39}
FUS = {20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 110}
TOTAL = 16


class Bad(Exception):
    pass


def seat(v, what):
    if not isinstance(v, int) or not 0 <= v <= 3:
        raise Bad(f"{what} must be a seat 0-3, got {v!r}")
    return v


def seats(v, what):
    if not isinstance(v, list):
        raise Bad(f"{what} must be a list")
    out = sorted({seat(x, what) for x in v})
    return out


def clean_hand(h, i):
    where = f"hand {i + 1}"
    if not isinstance(h, dict) or h.get("kind") not in KINDS:
        raise Bad(f"{where}: kind must be one of {sorted(KINDS)}")
    k = h["kind"]
    out = {"kind": k}
    if k in ("ron", "tsumo"):
        out["winner"] = seat(h.get("winner"), f"{where} winner")
        if k == "ron":
            out["loser"] = seat(h.get("loser"), f"{where} loser")
            if out["loser"] == out["winner"]:
                raise Bad(f"{where}: winner and loser are the same seat")
        if h.get("han") not in HANS:
            raise Bad(f"{where}: han must be one of {sorted(HANS)}")
        out["han"] = h["han"]
        fu = h.get("fu", 30)
        if fu not in FUS:
            raise Bad(f"{where}: fu must be one of {sorted(FUS)}")
        out["fu"] = fu
        if h.get("pao") is not None:
            out["pao"] = seat(h["pao"], f"{where} pao")
    if k == "draw":
        out["tenpai"] = seats(h.get("tenpai", []), f"{where} tenpai")
    if k != "manual":
        out["riichi"] = seats(h.get("riichi", []), f"{where} riichi")
    else:
        for key in ("deltas", "pen"):
            v = h.get(key, [0, 0, 0, 0])
            if not isinstance(v, list) or len(v) != 4 or not all(isinstance(x, (int, float)) for x in v):
                raise Bad(f"{where}: {key} must be 4 numbers")
            out[key] = v
        if h.get("note"):
            out["note"] = str(h["note"])[:80]
    return out


def clean_game(g, roster_ids, gid):
    if not isinstance(g, dict):
        raise Bad("not a JSON object")
    no = g.get("no")
    if not isinstance(no, int) or not 1 <= no <= TOTAL:
        raise Bad(f"no must be 1-{TOTAL}")
    s = g.get("seats")
    if not isinstance(s, list) or len(s) != 4 or len(set(s)) != 4:
        raise Bad("seats must list 4 different player ids")
    unknown = [p for p in s if p not in roster_ids]
    if unknown:
        raise Bad(f"unknown player ids {unknown}; known: {sorted(roster_ids)}")
    final = g.get("final")
    if final is not None:
        if not isinstance(final, list) or len(final) != 4 or not all(isinstance(x, int) for x in final):
            raise Bad("final must be null or 4 integer scores")
        if sum(final) != 100000:
            raise Bad(f"final scores add up to {sum(final)}, not 100000")
    hands = g.get("hands", [])
    if not isinstance(hands, list):
        raise Bad("hands must be a list")
    return {
        "id": gid,
        "no": no,
        "table": str(g.get("table") or "")[:20],
        "seats": s,
        "hands": [clean_hand(h, i) for i, h in enumerate(hands)],
        "final": final,
        "createdAt": g.get("createdAt") if isinstance(g.get("createdAt"), (int, float)) else 0,
        "scorer": str(g.get("scorer") or "")[:40],
    }


def load_roster():
    r = json.loads((ROOT / "roster.json").read_text())
    players = [{"id": str(p["id"]), "name": str(p["name"])[:24], **({"backup": True} if p.get("backup") else {})}
               for p in r["players"]]
    return players, {p["id"] for p in players}


def load_games(roster_ids, files=None):
    games, errors = [], []
    for f in files or sorted((ROOT / "games").glob("*.json")):
        f = Path(f)
        try:
            games.append(clean_game(json.loads(f.read_text()), roster_ids, f.stem))
        except (Bad, json.JSONDecodeError) as e:
            errors.append(f"{f.name}: {e}")
    return games, errors


def import_export():
    """Copy a Claude-recorder export (.export/roster, .export/games) into the repo's source files."""
    exp = ROOT / ".export"
    r = json.loads((exp / "roster" / "main.json").read_text())
    (ROOT / "roster.json").write_text(json.dumps({"players": r["players"]}, ensure_ascii=False, indent=1) + "\n")
    (ROOT / "games").mkdir(exist_ok=True)
    n = 0
    for f in sorted((exp / "games").glob("*.json")) if (exp / "games").exists() else []:
        g = json.loads(f.read_text())
        g.pop("updatedAt", None)
        g.setdefault("scorer", "Claude 记分台")
        (ROOT / "games" / f"claude-{f.stem}.json").write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n")
        n += 1
    print(f"imported roster ({len(r['players'])} players) and {n} games from .export/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".")
    ap.add_argument("--check", nargs="*")
    ap.add_argument("--import-export", action="store_true")
    a = ap.parse_args()
    if a.import_export:
        import_export()
    roster, ids = load_roster()
    games, errors = load_games(ids, a.check or None)
    for e in errors:
        print("ERROR", e, file=sys.stderr)
    if errors:
        sys.exit(1)
    if a.check is not None:
        print(f"ok: {len(games)} game file(s) valid")
        return
    out = (ROOT / a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if out != ROOT:
        for name in STATIC:
            shutil.copy(ROOT / name, out / name)
    data = {"syncedAt": int(time.time() * 1000), "roster": roster, "games": games}
    (out / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"data.json: {len(roster)} players, {len(games)} games, {sum(len(g['hands']) for g in games)} hands -> {out}")


if __name__ == "__main__":
    main()
