const fs = require('fs');
const vm = require('vm');

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

function computeDelta(match, mapping, csData) {
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
    if (rc == null || dc == null) return null;
    lineup[i] = rc;
    roles[i] = r.role;
    lineup2[i] = dc;
    roles[i+5] = d.role;
  }
  let nb1 = 0, nb2 = 0;
  for (let i = 0; i < 5; i++) {
    const id1 = lineup[i];
    const id3 = lineup2[i];
    const wr1 = getWrFor(csData.heroes_roles_db_wr, id1, roles[i]);
    const wr2 = getWrFor(csData.heroes_roles_db_wr, id3, roles[i+5]);
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
    nb1 += wr1 + adv1;
    nb2 += wr2 + adv2;
  }
  return { lineup, lineup2, delta: nb1 - nb2 };
}

function toLinkString(heroes, lineup, lineup2) {
  const top = lineup.map(id => heroes[id]).join('/');
  const bot = lineup2.map(id => heroes[id]).join('/');
  const s = `#${top}/${bot}`.replace(/ /g, '_').replace(/\/+$/, '');
  return s;
}

function main() {
  const ids = process.argv.slice(2);
  if (ids.length === 0) {
    console.error('Usage: node print_links.js <matchId> [<matchId> ...]');
    process.exit(1);
  }
  const csData = loadCsData('/workspace/cs.json');
  const mapping = loadMapping('/workspace/heromapping.json');
  const stratz = loadStratz('/workspace/stratz_clean_96507.json');

  for (const id of ids) {
    const match = stratz[id];
    if (!match) continue;
    const comp = computeDelta(match, mapping, csData);
    if (!comp) continue;
    const link = toLinkString(csData.heroes, comp.lineup, comp.lineup2);
    console.log(id);
    console.log(link);
    console.log(comp.delta.toFixed(2));
  }
}

main();
