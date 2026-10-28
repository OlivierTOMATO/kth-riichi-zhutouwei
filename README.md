# 猪头位 · KTH 立直麻将公开赛

Public, read-only scoreboard for the KTH Riichi Open (M.LEAGUE rules, 切上满贯, 16 hanchan).

- Scores are recorded live on the Claude recorder page; this site shows a synced copy.
- `data.json` holds the players and the hand log of every hanchan; `scoring.js` turns it
  into scores, points and the leaderboard (same code as the recorder).
- To update: export the recorder's `roster` and `games` collections into `.export/`,
  run `python3 sync.py`, commit and push.
