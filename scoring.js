// Scoring rules shared with the recorder page (M.LEAGUE, 切上满贯).
// Copied from the Claude recorder by sync.py — edit there, not here.
/* ---------- rules (M.LEAGUE) ---------- */
const WINDS = ['东','南','西','北'];
const UMA = [50, 10, -10, -30];            // 顺位点（1 位含头名奖励）
const START = 25000, RETURN = 30000, TOTAL = 16;
// 无数え役满：普通役 11 番以上按三倍满封顶；13/26/39 = 役满 / 复合役满
const HAN_OPTS = [[1,'1 番'],[2,'2 番'],[3,'3 番'],[4,'4 番'],[5,'满贯（5 番）'],[6,'跳满（6–7 番）'],[8,'倍满（8–10 番）'],[11,'三倍满（11 番以上）'],[13,'役满'],[26,'两倍役满（复合）'],[39,'三倍役满（复合）']];
const FU_OPTS = [20,25,30,40,50,60,70,80,90,100,110];
const TITLES = ['猪头位','猪头二号','猪头三号'];

const ceil100 = x => Math.ceil(x / 100) * 100;
function basePts(han, fu) {
  if (han >= 13) return 8000 * Math.floor(han / 13);
  if (han >= 11) return 6000;
  if (han >= 8) return 4000;
  if (han >= 6) return 3000;
  if (han >= 5) return 2000;
  const b = fu * Math.pow(2, han + 2);
  return b >= 1920 ? 2000 : b;                         // 切上满贯：4番30符 / 3番60符 记满贯
}
function fuError(kind, han, fu) {
  if (han >= 5) return '';
  if (fu === 20 && kind === 'ron') return '荣和没有 20 符（平和荣和是 30 符）';
  if (fu === 20 && han < 2) return '20 符自摸至少 2 番（平和 + 门前清自摸和）';
  if (fu === 25 && han < 2) return '25 符（七对子）至少 2 番';
  return '';
}
const roundLabel = (r, h) => `${WINDS[Math.floor(r / 4)]}${r % 4 + 1}局` + (h ? ` ${h}本场` : '');
const handName = hd => {
  if (hd.han >= 5) return HAN_OPTS.find(o => o[0] === hd.han)[1].replace(/（.*）/, '');
  return `${hd.han}番${hd.fu}符`;
};
// Splits `total` units evenly; the remainder goes to the seats closest to 起家.
function split(total, seats) {
  const q = Math.floor(total / seats.length), rem = total - q * seats.length, out = {};
  seats.slice().sort((a, b) => a - b).forEach((s, i) => out[s] = q + (i < rem ? 1 : 0));
  return out;
}

// Replays a game's hand log: scores, round, honba, riichi pot, per-hand deltas.
function replay(game) {
  const s = [START, START, START, START], pen = [0, 0, 0, 0];
  let r = 0, h = 0, pot = 0;
  const log = [];
  for (const hd of game.hands || []) {
    if (r > 7) break;
    const dealer = r % 4, d = [0, 0, 0, 0], label = roundLabel(r, h);
    let keep = false, draw = false, dealIn = null, value = 0;
    if (hd.kind !== 'manual') for (const i of hd.riichi || []) { d[i] -= 1000; pot += 1000; }
    if (hd.kind === 'ron' || hd.kind === 'tsumo') {
      const w = hd.winner, mult = w === dealer ? 6 : 4, b = basePts(hd.han, hd.fu);
      const p = hd.han >= 13 && hd.pao != null && hd.pao !== w && hd.pao !== hd.loser ? hd.pao : null;
      const pv = 8000 * mult;                          // 包牌只承担一个役满
      let tot = 0;
      if (hd.kind === 'ron') {
        const l = hd.loser;
        value = ceil100(b * mult);
        if (p != null) {                               // 荣和：放铳者与包牌者折半，本场由包牌者付
          const fromP = pv / 2 + 300 * h, fromL = value - pv / 2;
          d[p] -= fromP; d[l] -= fromL; tot = fromP + fromL;
          dealIn = { seat: l, points: fromL };
        } else {
          tot = value + 300 * h; d[l] -= tot;
          dealIn = { seat: l, points: tot };
        }
      } else {
        const tsumoAll = base => { for (let i = 0; i < 4; i++) if (i !== w) {
          const x = ceil100(base * (w === dealer || i === dealer ? 2 : 1)); d[i] -= x; tot += x; } };
        if (p != null) {                               // 自摸：包牌者全额（含本场），其余役满正常自摸
          d[p] -= pv + 300 * h; tot += pv + 300 * h;
          if (b > 8000) tsumoAll(b - 8000);
        } else {
          tsumoAll(b);
          for (let i = 0; i < 4; i++) if (i !== w) { d[i] -= 100 * h; tot += 100 * h; }
        }
        value = tot;
      }
      d[w] += tot + pot; pot = 0; keep = w === dealer;
    } else if (hd.kind === 'draw') {
      const t = hd.tenpai || [];
      if (t.length > 0 && t.length < 4)
        for (let i = 0; i < 4; i++) d[i] += t.includes(i) ? 3000 / t.length : -3000 / (4 - t.length);
      keep = t.includes(dealer); draw = true;
    } else if (hd.kind === 'manual') {
      for (let i = 0; i < 4; i++) { d[i] += +(hd.deltas || [])[i] || 0; pen[i] += +(hd.pen || [])[i] || 0; }
    }
    for (let i = 0; i < 4; i++) s[i] += d[i];
    log.push({ hd, label, dealer, d, dealIn, value, honba: h });
    if (hd.kind !== 'manual') {
      if (keep) h++;
      else { r++; h = draw ? h + 1 : 0; }
    }
  }
  let done = r > 7, scores = s.slice();
  if (Array.isArray(game.final) && game.final.length === 4) { scores = game.final.map(Number); done = true; pot = 0; }
  // 顺位：同点者平分该名次段的顺位点，端数归离起家近的人
  const order = [0, 1, 2, 3].sort((a, b) => scores[b] - scores[a] || a - b);
  const rank = [], umaU = [0, 0, 0, 0];
  for (let i = 0; i < 4;) {
    let j = i; while (j + 1 < 4 && scores[order[j + 1]] === scores[order[i]]) j++;
    const seats = order.slice(i, j + 1), sh = split(UMA.slice(i, j + 1).reduce((a, c) => a + c, 0) * 10, seats);
    seats.forEach(x => { rank[x] = i; umaU[x] = sh[x]; });
    i = j + 1;
  }
  if (done && pot) {                                   // 流局终局的供托归一位（同点平分）
    const tops = [0, 1, 2, 3].filter(x => rank[x] === 0), sh = split(pot / 100, tops);
    tops.forEach(x => scores[x] += sh[x] * 100); pot = 0;
  }
  const pts = scores.map((sc, i) => Math.round((sc - RETURN) / 100 + umaU[i] + pen[i] * 10) / 10);
  return { scores, rank, pts, pen, r, h, pot, dealer: r % 4, done, log };
}

