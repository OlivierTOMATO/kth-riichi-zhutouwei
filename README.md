# 猪头位 · KTH 立直麻将公开赛

Site: https://oliviertomato.github.io/kth-riichi-zhutouwei/ (M.LEAGUE rules, 切上满贯).

**Season 2 (current).** Regular season: 20 hanchan, 6 players (Estelle is a backup) rotating in, so game counts
differ. Ranking uses 折算分 = average points per hanchan × 10. Players with at least 12 regular hanchan
qualify; the top 4 by 折算分 make the final table. The season-1 champion (CJ, `SEED`, called 「水牛位」 in season 2) is guaranteed a seat
if they played 12: outside the top 4, they replace 4th place and carry their own (possibly negative) points.
Backups never make the final table. Final table: 8 hanchan; total = 折算分 × ½ + final-table points.
All of these numbers live at the top of `scoring.js` (`TOTAL`, `MIN`, `NORM`, `CARRY`, `FINAL`, `PLAYOFF`, `SEED`, `SEED_TITLE`).

**Season 1 (archived at `/s1/`).** 20 regular hanchan, regular points scaled to 16 hanchan and carried in
full into 4 playoff hanchan. The archive keeps its own frozen `s1/index.html`, `s1/scoring.js` and
`s1/roster.json`; its games are the files in `games/` without a `"season"` field.

## How results get onto the site

1. A player opens **记录成绩** (`record.html`), records the hanchan hand by hand on one device,
   and presses **发给主办方** at the end. That makes a link with the whole hanchan packed into it
   (`record.html#g=…`), opens the phone's share sheet (WeChat etc.) or copies it. No account needed.
2. The organiser opens the link. The recorder shows a review page: final scores, points, hand log,
   and warnings (unknown player, not finished, already published). **发布到网站** opens GitHub with
   `games/hanchan-NN-….json` filled in; the organiser commits it.
3. **Deploy site** rebuilds `data.json` and publishes it.

Players with a GitHub account can still use **在 GitHub 提交**, which proposes the file as a pull
request; the **Check submitted game** workflow then shows the scores in the pull request's checks.

## Files

- `roster.json`: players (`id`, `name`). Game files refer to players by id.
- `games/*.json`: one file per hanchan with seats (东南西北), hand log, optional final scores.
  Season-2 games carry `"season": 2` (files `s2-….json`); files without it belong to season 1.
  Playoff games carry `"stage": "playoff"` (numbered 1-8 in season 2, 1-4 in season 1, files `playoff-NN-….json`).
  Casual games (娱乐局) carry `"stage": "casual"` (files `casual-NN-….json`): listed on the
  homepage in their own folded section, never counted in rankings or stats.
- `scoring.js`: M.LEAGUE scoring, shared by the homepage, the recorder and the check.
- `tools/build.py`: validates everything and writes `data.json` (`python3 tools/build.py`).
- `tools/summary.js`: Markdown result table for the pull-request check.
