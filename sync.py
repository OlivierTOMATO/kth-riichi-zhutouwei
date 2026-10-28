"""Build data.json for the public scoreboard from an export of the recorder's database.

The recorder lives on claude.ai; Claude exports its `roster` and `games` collections
into .export/ (one JSON file per document), then this script keeps only the fields the
scoreboard needs and writes data.json.

    python3 sync.py            # reads .export/, writes data.json
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPORT = ROOT / ".export"
HAND_KEYS = {"kind", "winner", "loser", "han", "fu", "pao", "riichi", "tenpai", "deltas", "pen", "note"}


def seat_list(v):
    return [int(x) for x in v if isinstance(x, (int, float)) and 0 <= x <= 3] if isinstance(v, list) else []


def clean_hand(h):
    out = {k: h[k] for k in HAND_KEYS if k in h and h[k] is not None}
    for k in ("riichi", "tenpai"):
        if k in out:
            out[k] = seat_list(out[k])
    for k in ("deltas", "pen"):
        if k in out:
            out[k] = [float(x) if isinstance(x, (int, float)) else 0 for x in out[k]][:4]
    if "note" in out:
        out["note"] = str(out["note"])[:80]
    return out


def main():
    roster_file = EXPORT / "roster" / "main.json"
    if not roster_file.exists():
        sys.exit("missing .export/roster/main.json — export the recorder first")
    roster = [
        {"id": str(p["id"]), "name": str(p["name"])[:24]}
        for p in json.loads(roster_file.read_text()).get("players", [])
        if isinstance(p, dict) and "id" in p and "name" in p
    ]
    games = []
    for f in sorted((EXPORT / "games").glob("*.json")):
        g = json.loads(f.read_text())
        if not isinstance(g.get("seats"), list) or len(g["seats"]) != 4:
            continue
        final = g.get("final")
        games.append({
            "id": f.stem,
            "no": int(g.get("no", 0)),
            "table": str(g.get("table") or "")[:20],
            "seats": [str(s) for s in g["seats"]],
            "hands": [clean_hand(h) for h in g.get("hands", []) if isinstance(h, dict)],
            "final": [int(x) for x in final] if isinstance(final, list) and len(final) == 4 else None,
            "createdAt": g.get("createdAt", 0),
        })
    data = {"syncedAt": int(time.time() * 1000), "roster": roster, "games": games}
    (ROOT / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(f"data.json: {len(roster)} players, {len(games)} games, "
          f"{sum(len(g['hands']) for g in games)} hands")


if __name__ == "__main__":
    main()
