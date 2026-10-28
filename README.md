# 猪头位 · KTH 立直麻将公开赛

Site: https://oliviertomato.github.io/kth-riichi-zhutouwei/ (M.LEAGUE rules, 切上满贯, 16 hanchan).

## How results get onto the site

1. A player opens **记录成绩** (`record.html`), records the hanchan hand by hand on one device,
   and presses **提交审核** at the end. GitHub opens with a new file `games/hanchan-NN-….json`
   already filled in; they propose it as a pull request (a free GitHub account is needed).
2. The **Check submitted game** workflow validates the file and shows the final scores and
   points in the pull request's checks summary.
3. The organiser reviews and merges. **Deploy site** rebuilds `data.json` and publishes it.

## Files

- `roster.json`: players (`id`, `name`). Game files refer to players by id.
- `games/*.json`: one file per hanchan with seats (东南西北), hand log, optional final scores.
- `scoring.js`: M.LEAGUE scoring, shared by the homepage, the recorder and the check.
- `tools/build.py`: validates everything and writes `data.json` (`python3 tools/build.py`).
- `tools/summary.js`: Markdown result table for the pull-request check.
