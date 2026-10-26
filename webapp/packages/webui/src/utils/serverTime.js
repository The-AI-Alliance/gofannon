// webapp/packages/webui/src/utils/serverTime.js
//
// The backend stores timestamps with `naive_utc_now()` — a NAIVE datetime,
// so `.isoformat()` emits "2026-07-31T14:51:47.123456" with no timezone
// suffix.
//
// ECMA-262 says a date-time string WITHOUT an offset is parsed as LOCAL
// time. So `new Date(startedAt)` reads a UTC instant as though it were
// local, and every derived figure is wrong by the viewer's UTC offset.
// In PDT (UTC-7) that surfaces as a run appearing to start seven hours in
// the future — the "-25176s ago" on the home page.
//
// This is not a display-only problem: the same parse feeds staleness
// checks, duration maths and sort order.
//
// Fix: treat a string with no offset as UTC, which is what the backend
// meant. Strings that DO carry an offset (or a trailing Z) are passed
// through untouched, so this stays correct if the backend is ever changed
// to emit timezone-aware timestamps.

/** Does this ISO string already carry a timezone? */
function hasTimezone(iso) {
  // Trailing Z, or ±HH:MM / ±HHMM after the time portion.
  return /(?:Z|[+-]\d{2}:?\d{2})$/.test(iso);
}

/**
 * Parse a timestamp from the API into a Date.
 *
 * Returns null for empty/invalid input rather than an Invalid Date, so
 * callers can branch on it instead of propagating NaN into arithmetic.
 */
export function parseServerDate(iso) {
  if (!iso || typeof iso !== 'string') return null;
  const normalised = hasTimezone(iso) ? iso : `${iso}Z`;
  const d = new Date(normalised);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Milliseconds since `iso`. Returns null when the input is unusable. */
export function ageMs(iso) {
  const d = parseServerDate(iso);
  return d === null ? null : Date.now() - d.getTime();
}

/**
 * "3s ago" / "4m ago" / "2h ago".
 *
 * Clamps negative ages to "just now": a few seconds of clock skew between
 * the API host and the browser is normal and should not render as a
 * negative duration. A LARGE negative value means the timezone bug above
 * has returned, so it is worth noticing rather than hiding — hence the
 * console warning.
 */
export function formatTimeAgo(iso) {
  const ms = ageMs(iso);
  if (ms === null) return '';
  const diff = ms / 1000;
  if (diff < -60) {
    console.warn(
      `serverTime: timestamp ${iso} is ${Math.round(-diff)}s in the future — ` +
      'timezone handling may be wrong.',
    );
    return 'just now';
  }
  if (diff < 60) return `${Math.max(0, Math.round(diff))}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

export default { parseServerDate, ageMs, formatTimeAgo };