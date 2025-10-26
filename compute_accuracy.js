const fs = require('fs');
const vm = require('vm');

const DELTA_THRESHOLDS = [5,10,15,20,25,30,35,40,45,50];
const POS_THRESHOLDS = [5,8,10];
const NEG_THRESHOLDS = [5,8,10];
const ROLES = ['carry','mid','offlane','softsupport','hardsupport'];

function loadCsData(csPath) {
  const code = fs.readFileSync(csPath, 'utf8');
  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(code, sandbox, { filename: csPath, displayErrors: true });
  const result = {
    heroes: sandbox.heroes,
    win_rates: sandbox.win_rates,
    heroes_roles_db_wr: sandbox.heroes_roles_db_wr,
  };
  if (!Array.isArray(result.heroes) || !Array.isArray(result.win_rates)) {
    throw new Error('Failed to load cs.json arrays');
  }
  // Ensure role WR arrays exist
  if (typeof result.heroes_roles_db_wr !== 'object' || result.heroes_roles_db_wr === null) {
    result.heroes_roles_db_wr = {};
  }
  for (const role of ROLES) {
    if (!result.heroes_roles_db_wr[role]) result.heroes_roles_db_wr[role] = {};
    if (!Array.isArray(result.heroes_roles_db_wr[role].wr)) {
      result.heroes_roles_db_wr[role].wr = new Array(result.heroes.length).fill(50);
    }
  }
  return result;
}

function loadMapping(path) {
  return JSON.parse(fs.readFileSync(path, 'utf8'));
}

function loadStratz(path) {
  return JSON.parse(fs.readFileSync(path, 'utf8'));
}

function getWrFor(heroes_roles_db_wr, heroId, role) {
  const arr = heroes_roles_db_wr && heroes_roles_db_wr[role] && heroes_roles_db_wr[role].wr;
  const v = arr && arr[heroId] != null ? arr[heroId] : 50;
  const num = parseFloat(v);
  return Number.isFinite(num) ? num : 50;
}

function canonicalRole(role) {
  if (!role) return null;
  const r = String(role).toLowerCase().replace(/\s+/g,'');
  if (ROLES.includes(r)) return r;
  // quick aliasing
  if (r === 'soft' || r === 'soft_support') return 'softsupport';
  if (r === 'hard' || r === 'hard_support') return 'hardsupport';
  return null;
}

function computeMatchStats(match, mapping, csData) {
  const toCs = (vid) => {
    const v = mapping[String(vid)];
    return typeof v === 'number' ? v : null;
  };
  const rItems = match.radiantRoles;
  const dItems = match.direRoles;
  if (!Array.isArray(rItems) || !Array.isArray(dItems) || rItems.length < 5 || dItems.length < 5) return null;

  const lineup = new Array(5);
  const lineup2 = new Array(5);
  const roleR = new Array(5);
  const roleD = new Array(5);

  for (let i = 0; i < 5; i++) {
    const r = rItems[i];
    const d = dItems[i];
    if (!r || !d) return null;
    const rc = toCs(r.heroId);
    const dc = toCs(d.heroId);
    if (rc == null || dc == null) return null;
    lineup[i] = rc;
    lineup2[i] = dc;
    const cr = canonicalRole(r.role);
    const cd = canonicalRole(d.role);
    if (!cr || !cd) return null;
    roleR[i] = cr;
    roleD[i] = cd;
  }

  // compute per-slot WR and advantage as per UI logic
  let nb1 = 0, nb2 = 0;
  const advR = new Array(5);
  const advD = new Array(5);

  for (let i = 0; i < 5; i++) {
    const id1 = lineup[i];
    const id3 = lineup2[i];
    const wr1 = getWrFor(csData.heroes_roles_db_wr, id1, roleR[i]);
    const wr2 = getWrFor(csData.heroes_roles_db_wr, id3, roleD[i]);

    let nb1a = 0, nb2a = 0;
    for (let j = 0; j < 5; j++) {
      const id2 = lineup2[j];
      const id4 = lineup[j];
      if (id2 != null && csData.win_rates[id2] && csData.win_rates[id2][id1]) {
        const v = parseFloat(csData.win_rates[id2][id1][0]);
        if (Number.isFinite(v)) nb1a += v * -1;
      }
      if (id4 != null && csData.win_rates[id4] && csData.win_rates[id4][id3]) {
        const v = parseFloat(csData.win_rates[id4][id3][0]);
        if (Number.isFinite(v)) nb2a += v * -1;
      }
    }
    const adv1 = nb1a * -1;
    const adv2 = nb2a * -1;
    advR[i] = adv1;
    advD[i] = adv2;
    nb1 += wr1 + adv1;
    nb2 += wr2 + adv2;
  }

  const delta = nb1 - nb2;
  return { delta, advR, advD, roleR, roleD, lineup, lineup2 };
}

function main() {
  const csData = loadCsData('/workspace/cs.json');
  const mapping = loadMapping('/workspace/heromapping.json');
  const stratz = loadStratz('/workspace/stratz_clean_96507.json');

  const finalAcc = new Map();
  for (const t of DELTA_THRESHOLDS) finalAcc.set(t, { total: 0, correct: 0 });

  const rolePos = new Map();
  const roleNeg = new Map();
  for (const r of ROLES) {
    const m1 = new Map();
    const m2 = new Map();
    for (const t of POS_THRESHOLDS) m1.set(t, { total: 0, correct: 0 });
    for (const t of NEG_THRESHOLDS) m2.set(t, { total: 0, correct: 0 });
    rolePos.set(r, m1);
    roleNeg.set(r, m2);
  }

  // Per-hero advantage accuracy (+ thresholds use POS_THRESHOLDS, - thresholds use NEG_THRESHOLDS)
  // heroPos[h] and heroNeg[h] hold maps threshold -> { total, correct }
  const heroPos = [];
  const heroNeg = [];
  for (let h = 0; h < csData.heroes.length; h++) {
    const mPos = new Map();
    const mNeg = new Map();
    for (const t of POS_THRESHOLDS) mPos.set(t, { total: 0, correct: 0 });
    for (const t of NEG_THRESHOLDS) mNeg.set(t, { total: 0, correct: 0 });
    heroPos[h] = mPos;
    heroNeg[h] = mNeg;
  }

  const keys = Object.keys(stratz);
  let processed = 0, skipped = 0;

  for (const k of keys) {
    const match = stratz[k];
    const s = computeMatchStats(match, mapping, csData);
    if (!s) { skipped++; continue; }
    processed++;
    const radiantWin = !!match.radiantWin;

    // final delta thresholds
    const absDelta = Math.abs(s.delta);
    const pred = s.delta > 0; // true if Radiant predicted
    for (const t of DELTA_THRESHOLDS) {
      if (absDelta >= t) {
        const c = finalAcc.get(t);
        c.total += 1;
        c.correct += (radiantWin === pred) ? 1 : 0;
      }
    }

    // role positive thresholds and per-hero thresholds
    for (let i = 0; i < 5; i++) {
      const rRole = s.roleR[i];
      const dRole = s.roleD[i];
      const aR = s.advR[i];
      const aD = s.advD[i];
      const idR = s.lineup[i];
      const idD = s.lineup2[i];
      for (const t of POS_THRESHOLDS) {
        if (aR >= t) {
          const c = rolePos.get(rRole).get(t);
          c.total += 1;
          c.correct += radiantWin ? 1 : 0; // predict Radiant wins
          const h = heroPos[idR].get(t);
          h.total += 1;
          h.correct += radiantWin ? 1 : 0;
        }
        if (aD >= t) {
          const c = rolePos.get(dRole).get(t);
          c.total += 1;
          c.correct += (!radiantWin) ? 1 : 0; // predict Dire wins
          const h = heroPos[idD].get(t);
          h.total += 1;
          h.correct += (!radiantWin) ? 1 : 0;
        }
      }
      for (const t of NEG_THRESHOLDS) {
        if (aR <= -t) {
          const c = roleNeg.get(rRole).get(t);
          c.total += 1;
          c.correct += (!radiantWin) ? 1 : 0; // predict Radiant loses
          const h = heroNeg[idR].get(t);
          h.total += 1;
          h.correct += (!radiantWin) ? 1 : 0;
        }
        if (aD <= -t) {
          const c = roleNeg.get(dRole).get(t);
          c.total += 1;
          c.correct += radiantWin ? 1 : 0; // predict Dire loses
          const h = heroNeg[idD].get(t);
          h.total += 1;
          h.correct += radiantWin ? 1 : 0;
        }
      }
    }
  }

  const out = [];
  out.push(['category','subcategory','role','threshold','total','correct','accuracy'].join(','));

  for (const t of DELTA_THRESHOLDS) {
    const c = finalAcc.get(t);
    const acc = c.total > 0 ? (c.correct / c.total) : 0;
    out.push(['final_delta','', '', t, c.total, c.correct, acc.toFixed(4)].join(','));
  }

  for (const r of ROLES) {
    const m1 = rolePos.get(r);
    const m2 = roleNeg.get(r);
    for (const t of POS_THRESHOLDS) {
      const c = m1.get(t);
      const acc = c.total > 0 ? (c.correct / c.total) : 0;
      out.push(['role_advantage','positive', r, t, c.total, c.correct, acc.toFixed(4)].join(','));
    }
    for (const t of NEG_THRESHOLDS) {
      const c = m2.get(t);
      const acc = c.total > 0 ? (c.correct / c.total) : 0;
      out.push(['role_advantage','negative', r, t, c.total, c.correct, acc.toFixed(4)].join(','));
    }
  }

  // Append per-hero advantage rows
  for (let h = 0; h < csData.heroes.length; h++) {
    const name = csData.heroes[h];
    const mPos = heroPos[h];
    const mNeg = heroNeg[h];
    for (const t of POS_THRESHOLDS) {
      const c = mPos.get(t);
      const acc = c.total > 0 ? (c.correct / c.total) : 0;
      out.push(['hero_advantage','positive', name, t, c.total, c.correct, acc.toFixed(4)].join(','));
    }
    for (const t of NEG_THRESHOLDS) {
      const c = mNeg.get(t);
      const acc = c.total > 0 ? (c.correct / c.total) : 0;
      out.push(['hero_advantage','negative', name, t, c.total, c.correct, acc.toFixed(4)].join(','));
    }
  }

  const outPath = '/workspace/model_accuracy.csv';
  fs.writeFileSync(outPath, out.join('\n'), 'utf8');
  console.log(`Processed: ${processed}, Skipped: ${skipped}`);
  console.log(`Wrote CSV: ${outPath}`);
}

main();
