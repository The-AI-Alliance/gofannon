// serverTime normalises naive backend timestamps to UTC.
//
// The bug these guard against: the API emits `naive_utc_now().isoformat()`,
// which has no offset, and ECMA-262 parses an offset-less date-time as
// LOCAL time. A viewer in PDT then sees a run that started seven hours in
// the future. The parse also feeds staleness checks and duration maths, so
// it is not a display-only concern.
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest';
import { parseServerDate, ageMs, formatTimeAgo } from './serverTime';

describe('parseServerDate', () => {
  it('treats a timestamp with no offset as UTC', () => {
    const d = parseServerDate('2026-07-31T14:51:47.123456');
    expect(d.toISOString()).toBe('2026-07-31T14:51:47.123Z');
  });

  it('passes through a trailing Z untouched', () => {
    const d = parseServerDate('2026-07-31T14:51:47Z');
    expect(d.toISOString()).toBe('2026-07-31T14:51:47.000Z');
  });

  it.each([
    ['+02:00', '2026-07-31T12:51:47.000Z'],
    ['-07:00', '2026-07-31T21:51:47.000Z'],
  ])('respects an explicit %s offset', (offset, expected) => {
    expect(parseServerDate(`2026-07-31T14:51:47${offset}`).toISOString()).toBe(expected);
  });

  it('accepts an offset written without a colon', () => {
    expect(parseServerDate('2026-07-31T14:51:47+0200').toISOString())
      .toBe('2026-07-31T12:51:47.000Z');
  });

  it.each([null, undefined, '', 0, 42, {}, []])(
    'returns null rather than an Invalid Date for %p', (input) => {
      expect(parseServerDate(input)).toBeNull();
    },
  );

  it('returns null for a string that is not a date', () => {
    expect(parseServerDate('not-a-date')).toBeNull();
  });
});

describe('ageMs', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-07-31T15:00:00Z'));
  });
  afterEach(() => vi.useRealTimers());

  it('measures from a naive timestamp as UTC', () => {
    expect(ageMs('2026-07-31T14:59:00')).toBe(60_000);
  });

  it('returns null when the input is unusable', () => {
    expect(ageMs('')).toBeNull();
    expect(ageMs('nonsense')).toBeNull();
  });
});

describe('formatTimeAgo', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-07-31T15:00:00Z'));
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('returns an empty string when the input is unusable', () => {
    expect(formatTimeAgo(null)).toBe('');
  });

  it.each([
    ['2026-07-31T14:59:57', '3s ago'],
    ['2026-07-31T14:56:00', '4m ago'],
    ['2026-07-31T13:00:00', '2h ago'],
    ['2026-07-29T15:00:00', '2d ago'],
  ])('formats %s as %s', (iso, expected) => {
    expect(formatTimeAgo(iso)).toBe(expected);
  });

  it('clamps small clock skew to 0s rather than showing a negative age', () => {
    expect(formatTimeAgo('2026-07-31T15:00:05')).toBe('0s ago');
  });

  it('reports a large future timestamp as "just now" and warns', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    expect(formatTimeAgo('2026-07-31T22:00:00')).toBe('just now');
    expect(warn).toHaveBeenCalledWith(expect.stringContaining('in the future'));
  });
});
