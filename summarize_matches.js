const fs = require('fs');
const vm = require('vm');

function loadCsData(csPath) {
  const code = fs.readFileSync(csPath, 'utf8');
  const sandbox = {};
  vm.createContext(sandbox);
  // Execute cs.json which defines heroes, win_rates, heroes_roles_db_wr, etc.
  vm.runInContext(code, sandbox, { filename: csPath, displayErrors: true });
  const result = {
    heroes: sandbox.heroes,
    win_rates: sandbox.win_rates,
    heroes_roles_db_wr: sandbox.heroes_roles_db_wr,
    heroes_wr: sandbox.heroes_wr,
    update_time: sandbox.update_time
  };
  if (!Array.isArray(result.heroes)) {
    throw new Error('Failed to load heroes from cs.json');
  }
  if (!Array.isArray(result.win_rates)) {
    throw new Error('Failed to load win_rates from cs.json');
  }
  // Normalize roles WR structure to match UI defaults if missing
  const roleKeys = ['carry','mid','offlane','softsupport','hardsupport'];
  if (typeof result.heroes_roles_db_wr !== 'object' || result.heroes_roles_db_wr === null) {
    result.heroes_roles_db_wr = {};
  }
  for (const role of roleKeys) {
    if (!result.heroes_roles_db_wr[role]) result.heroes_roles_db_wr[role] = {};
    if (!Array.isArray(result.heroes_roles_db_wr[role].wr)) {
      result.heroes_roles_db_wr[role].wr = new Array(result.heroes.length).fill(50);
    }
  }
  return result;
}

function loadMapping(path) {
  const raw = fs.readFileSync(path, 'utf8');
  const map = JSON.parse(raw);
  return map; // keys are Valve IDs as strings, values are cs indices
}

function loadStratz(path) {
  const raw = fs.readFileSync(path, 'utf8');
  const obj = JSON.parse(raw);
  return obj; // { matchId: { radiantWin, radiantRoles:[{heroId, role}x5], direRoles:[...] } }
}

function getWrFor(heroes_roles_db_wr, heroId, role) {
  const arr = heroes_roles_db_wr && heroes_roles_db_wr[role] && heroes_roles_db_wr[role].wr;
  const v = arr && arr[heroId] != null ? arr[heroId] : 50;
  const num = parseFloat(v);
  return Number.isFinite(num) ? num : 50;
}

function computeForMatch(match, mapping, csData) {
  const toCs = (vid) => {
    const v = mapping[String(vid)];
    return typeof v === 'number' ? v : null;
  };
  const lineup = new Array(5);
  const lineup2 = new Array(5);
  const roles = new Array(10);
  for (let i = 0; i < 5; i++) {
    const r = match.radiantRoles[i];
    const d = match.direRoles[i];
    if (!r || !d) return null;
    const rc = toCs(r.heroId);
    const dc = toCs(d.heroId);
    if (rc == null || dc == null) return null; // mapping missing
    lineup[i] = rc;
    roles[i] = r.role;
    lineup2[i] = dc;
    roles[i+5] = d.role;
  }

  // Per-slot winrate and advantage per UI logic
  const perSlot = [];
  let nb1 = 0;
  let nb2 = 0;

  for (let i = 0; i < 5; i++) {
    const id1 = lineup[i];
    const id3 = lineup2[i];

    const wr1 = getWrFor(csData.heroes_roles_db_wr, id1, roles[i]);
    const wr2 = getWrFor(csData.heroes_roles_db_wr, id3, roles[i+5]);

    let nb1a = 0;
    let nb2a = 0;
    for (let j = 0; j < 5; j++) {
      const id2 = lineup2[j];
      const id4 = lineup[j];
      if (id2 != null && csData.win_rates[id2] && csData.win_rates[id2][id1]) {
        const v = parseFloat(csData.win_rates[id2][id1][0]);
        if (Number.isFinite(v)) nb1a += v * -1; // mimic UI logic
      }
      if (id4 != null && csData.win_rates[id4] && csData.win_rates[id4][id3]) {
        const v = parseFloat(csData.win_rates[id4][id3][0]);
        if (Number.isFinite(v)) nb2a += v * -1; // mimic UI logic
      }
    }
    const adv1 = nb1a * -1; // displayed advantage
    const adv2 = nb2a * -1;

    nb1 += wr1 + adv1;
    nb2 += wr2 + adv2;

    perSlot.push({
      radiant: { id: id1, name: csData.heroes[id1], wr: wr1, adv: adv1, role: roles[i] },
      dire:    { id: id3, name: csData.heroes[id3], wr: wr2, adv: adv2, role: roles[i+5] }
    });
  }

  const delta = nb1 - nb2;

  return { lineup, lineup2, roles, perSlot, delta };
}

function pickRandomMatches(stratz, mapping, csData, count) {
  const keys = Object.keys(stratz);
  const selected = [];
  const tried = new Set();
  let guard = 0;
  while (selected.length < count && guard < keys.length * 5) {
    guard++;
    const idx = Math.floor(Math.random() * keys.length);
    const k = keys[idx];
    if (tried.has(k)) continue;
    tried.add(k);
    const comp = computeForMatch(stratz[k], mapping, csData);
    if (comp) selected.push({ matchId: k, data: comp });
  }
  return selected;
}

function main() {
  const csPath = '/workspace/cs.json';
  const mapPath = '/workspace/heromapping.json';
  const stratzPath = '/workspace/stratz_clean_96507.json';

  const csData = loadCsData(csPath);
  const mapping = loadMapping(mapPath);
  const stratz = loadStratz(stratzPath);

  const picks = pickRandomMatches(stratz, mapping, csData, 2);
  if (picks.length < 2) {
    console.error('Could not find two matches with complete mapping.');
    process.exit(1);
  }

  for (const pick of picks) {
    console.log(pick.matchId);
    console.log('Radiant:');
    for (let i = 0; i < 5; i++) {
      const r = pick.data.perSlot[i].radiant;
      console.log(`${r.name} - ${r.wr.toFixed(2)} + ${ (r.adv < 0 ? '-' : '') + Math.abs(r.adv).toFixed(2) } - ${r.role}`);
    }
    console.log('Dire:');
    for (let i = 0; i < 5; i++) {
      const d = pick.data.perSlot[i].dire;
      console.log(`${d.name} - ${d.wr.toFixed(2)} + ${ (d.adv < 0 ? '-' : '') + Math.abs(d.adv).toFixed(2) } - ${d.role}`);
    }
    console.log(pick.data.delta.toFixed(2));
  }
}

main();
