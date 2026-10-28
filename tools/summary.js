// Prints a Markdown summary of submitted game files (final scores, points, hand count),
// using the same scoring.js as the site. Used by the pull-request check so the reviewer
// sees the result without opening the JSON.
//   node tools/summary.js games/hanchan-01-*.json
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const lib = new Function(fs.readFileSync(path.join(root, 'scoring.js'), 'utf8') + '\nreturn { replay, roundLabel, WINDS };')();
const roster = JSON.parse(fs.readFileSync(path.join(root, 'roster.json'), 'utf8')).players;
const nameOf = id => (roster.find(p => p.id === id) || {}).name || id;
const fmt = v => (v > 0 ? '+' : '') + v.toFixed(1);

const out = [];
for (const f of process.argv.slice(2)) {
  const g = JSON.parse(fs.readFileSync(f, 'utf8'));
  const R = lib.replay(g);
  out.push(`### 第 ${g.no} 半庄 · ${path.basename(f)}`);
  out.push(`记录人：${g.scorer || '未填写'} · ${g.hands.length} 局${g.final ? ' · 终局点数为直接录入' : ''} · ${R.done ? '**已终局**' : `⚠️ **未终局**（停在 ${lib.roundLabel(R.r, R.h)}）`}`);
  out.push('', '| 座位 | 选手 | 终局点数 | 顺位 | 积分 |', '|---|---|--:|--:|--:|');
  g.seats.forEach((pid, i) => out.push(`| ${lib.WINDS[i]} | ${nameOf(pid)} | ${R.scores[i]} | ${R.rank[i] + 1} | ${fmt(R.pts[i])} |`));
  out.push('');
}
console.log(out.join('\n'));
