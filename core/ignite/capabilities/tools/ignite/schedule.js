'use strict';

// API
// parseAt(iso) → { ms, offset }
// parseDuration(text) → milliseconds; units s|m|h|d, fixed elapsed time
// cadenceSpec({ at, cron, every, tz }) → { cadence, timezone, nextAt }
// nextOccurrence(cadence, timezone, fromMs) → epoch ms, or null for a spent one-shot
// FIXED_TZ — timezone column for --every (not an IANA zone)

const WEEK = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
const UNIT = { s: 1000, m: 60_000, h: 3_600_000, d: 86_400_000 };
const FIXED_TZ = 'fixed';
const YEAR_MS = 366 * 24 * 60 * 60 * 1000;

function parseAt(iso) {
  if (typeof iso !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(iso)) {
    throw new Error('--at requires an ISO datetime with a numeric offset or Z');
  }
  const ms = Date.parse(iso);
  if (Number.isNaN(ms)) throw new Error(`bad --at datetime: ${iso}`);
  return { ms, offset: iso.endsWith('Z') ? 'Z' : iso.slice(-6) };
}

function parseDuration(text) {
  const match = /^(\d+)(s|m|h|d)$/.exec(text || '');
  if (!match || match[1] === '0') throw new Error('--every requires a duration like 30s, 5m, 2h, 1d');
  return Number(match[1]) * UNIT[match[2]];
}

function parseField(raw, min, max, dow = false) {
  if (raw === '*') return { values: fill(min, max), star: true };
  const values = new Set();
  for (const part of raw.split(',')) {
    if (!part) throw new Error(`bad cron field: ${raw}`);
    const [span, stepRaw] = part.split('/');
    if (part.split('/').length > 2) throw new Error(`bad cron field: ${raw}`);
    const step = stepRaw === undefined ? 1 : Number(stepRaw);
    if (!Number.isInteger(step) || step < 1) throw new Error(`bad cron field: ${raw}`);
    let lo;
    let hi;
    if (span === '*') {
      lo = min;
      hi = max;
    } else if (span.includes('-')) {
      const bits = span.split('-');
      if (bits.length !== 2) throw new Error(`bad cron field: ${raw}`);
      lo = Number(bits[0]);
      hi = Number(bits[1]);
    } else {
      lo = hi = Number(span);
    }
    const cap = dow ? 7 : max;
    if (!Number.isInteger(lo) || !Number.isInteger(hi) || lo > hi || lo < min || hi > cap) {
      throw new Error(`bad cron field: ${raw}`);
    }
    for (let n = lo; n <= hi; n += step) values.add(dow && n === 7 ? 0 : n);
  }
  return { values, star: false };
}

function fill(min, max) {
  const values = new Set();
  for (let n = min; n <= max; n++) values.add(n);
  return values;
}

function parseCron(expr) {
  const fields = String(expr || '').trim().split(/\s+/);
  if (fields.length !== 5) throw new Error('cron must be a 5-field expression');
  return {
    minute: parseField(fields[0], 0, 59),
    hour: parseField(fields[1], 0, 23),
    dom: parseField(fields[2], 1, 31),
    month: parseField(fields[3], 1, 12),
    dow: parseField(fields[4], 0, 6, true),
  };
}

function assertZone(tz) {
  if (!tz || tz === FIXED_TZ) throw new Error('cron requires --tz <IANA zone>');
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: tz });
  } catch {
    throw new Error(`unknown timezone: ${tz}`);
  }
}

function zonedParts(ms, tz) {
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,
    hourCycle: 'h23',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    weekday: 'short',
  });
  const parts = {};
  for (const part of fmt.formatToParts(new Date(ms))) {
    if (part.type !== 'literal') parts[part.type] = part.value;
  }
  let hour = Number(parts.hour);
  if (hour === 24) hour = 0;
  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    hour,
    minute: Number(parts.minute),
    second: Number(parts.second),
    weekday: WEEK[parts.weekday],
  };
}

function tzOffsetMs(utcMs, tz) {
  const p = zonedParts(utcMs, tz);
  return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second) - utcMs;
}

function sameLocal(ms, y, mo, d, h, mi, tz) {
  const p = zonedParts(ms, tz);
  return p.year === y && p.month === mo && p.day === d && p.hour === h && p.minute === mi && p.second === 0;
}

function instantsForLocal(y, mo, d, h, mi, tz) {
  const guess = Date.UTC(y, mo - 1, d, h, mi, 0) - tzOffsetMs(Date.UTC(y, mo - 1, d, h, mi, 0), tz);
  const found = [];
  for (const delta of [0, -3_600_000, 3_600_000, -7_200_000, 7_200_000]) {
    const t = guess + delta;
    if (sameLocal(t, y, mo, d, h, mi, tz) && !found.includes(t)) found.push(t);
  }
  found.sort((a, b) => a - b);
  return found;
}

function addDays(y, mo, d, n) {
  const dt = new Date(Date.UTC(y, mo - 1, d + n));
  return { year: dt.getUTCFullYear(), month: dt.getUTCMonth() + 1, day: dt.getUTCDate() };
}

function dateMatches(cron, y, mo, d) {
  if (!cron.month.values.has(mo)) return false;
  const weekday = new Date(Date.UTC(y, mo - 1, d)).getUTCDay();
  const dom = cron.dom.values.has(d);
  const dow = cron.dow.values.has(weekday);
  if (!cron.dom.star && !cron.dow.star) return dom || dow;
  return dom && dow;
}

function nextCron(expr, tz, fromMs) {
  assertZone(tz);
  const cron = parseCron(expr);
  const start = zonedParts(fromMs, tz);
  const limit = fromMs + YEAR_MS;
  for (let offset = 0; offset < 366; offset++) {
    const day = addDays(start.year, start.month, start.day, offset);
    if (!dateMatches(cron, day.year, day.month, day.day)) continue;
    for (const hour of [...cron.hour.values].sort((a, b) => a - b)) {
      for (const minute of [...cron.minute.values].sort((a, b) => a - b)) {
        for (const instant of instantsForLocal(day.year, day.month, day.day, hour, minute, tz)) {
          if (instant > fromMs && instant <= limit) return instant;
        }
      }
    }
  }
  throw new Error('no cron occurrence within a year');
}

function nextOccurrence(cadence, timezone, fromMs) {
  if (cadence.startsWith('every:')) {
    if (timezone !== FIXED_TZ) throw new Error('--every is a fixed-interval and does not take --tz');
    return fromMs + parseDuration(cadence.slice('every:'.length));
  }
  if (cadence.startsWith('at:')) return null;
  if (cadence.startsWith('cron:')) return nextCron(cadence.slice('cron:'.length), timezone, fromMs);
  throw new Error(`unknown cadence: ${cadence}`);
}

function cadenceSpec({ at, cron, every, tz }) {
  const chosen = [at, cron, every].filter((value) => value != null);
  if (chosen.length !== 1) {
    throw new Error('schedule requires exactly one of --at, --cron, or --every; a recurring schedule requires a cadence');
  }
  if (at != null) {
    if (tz) throw new Error('--at carries its offset; do not also pass --tz');
    const parsed = parseAt(at);
    return { cadence: `at:${at}`, timezone: parsed.offset, nextAt: parsed.ms };
  }
  if (cron != null) {
    if (!tz) throw new Error('cron requires --tz <IANA zone>');
    if (every != null) throw new Error('schedule requires exactly one cadence');
    assertZone(tz);
    parseCron(cron);
    return { cadence: `cron:${cron.trim()}`, timezone: tz, nextAt: null };
  }
  if (tz) throw new Error('--every is a fixed-interval and does not take --tz');
  parseDuration(every);
  return { cadence: `every:${every}`, timezone: FIXED_TZ, nextAt: null };
}

module.exports = { FIXED_TZ, nextCron, nextOccurrence, cadenceSpec };
