# 猪头位 · KTH 立直麻将公开赛

Site: https://oliviertomato.github.io/kth-riichi-zhutouwei/ (M.LEAGUE rules, 切上满贯, 16 hanchan).

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
- `scoring.js`: M.LEAGUE scoring, shared by the homepage, the recorder and the check.
- `tools/build.py`: validates everything and writes `data.json` (`python3 tools/build.py`).
- `tools/summary.js`: Markdown result table for the pull-request check.
