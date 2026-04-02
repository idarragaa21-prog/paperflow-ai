import { describe, expect, it } from 'vitest';
import { calcORFrom2x2 } from './effectMath';

describe('effectMath.calcORFrom2x2', () => {
  it('calculates OR, log OR, SE, and 95% CI correctly for standard inputs', () => {
    // a=10, b=20, c=5, d=40
    // OR = (10*40) / (20*5) = 400 / 100 = 4
    // logOR = ln(4) ≈ 1.386
    // SE = sqrt(1/10 + 1/20 + 1/5 + 1/40) = sqrt(0.1 + 0.05 + 0.2 + 0.025) = sqrt(0.375) ≈ 0.612
    const result = calcORFrom2x2({
      a_events: 10,
      b_non_events: 20,
      c_events: 5,
      d_non_events: 40,
    });

    expect(result.ok).toBe(true);
    expect(result.or_value).toBe(4);
    expect(result.log_or).toBeCloseTo(Math.log(4), 4);
    expect(result.se_log_or).toBeCloseTo(Math.sqrt(0.375), 4);
    expect(result.ci_lower_95).toBeCloseTo(Math.exp(Math.log(4) - 1.96 * Math.sqrt(0.375)), 4);
    expect(result.ci_upper_95).toBeCloseTo(Math.exp(Math.log(4) + 1.96 * Math.sqrt(0.375)), 4);
  });

  it('returns missing cells error if any value is null', () => {
    const result = calcORFrom2x2({
      a_events: 10,
      b_non_events: null,
      c_events: 5,
      d_non_events: 40,
    });

    expect(result).toEqual({
      ok: false,
      reason: 'Missing cells (need a,b,c,d)',
      or_value: null,
      log_or: null,
      se_log_or: null,
      ci_lower_95: null,
      ci_upper_95: null,
    });
  });

  it('returns zeros/negatives error if any value is 0', () => {
    const result = calcORFrom2x2({
      a_events: 10,
      b_non_events: 20,
      c_events: 0,
      d_non_events: 40,
    });

    expect(result).toEqual({
      ok: false,
      reason: 'Zeros/negatives present (no correction applied)',
      or_value: null,
      log_or: null,
      se_log_or: null,
      ci_lower_95: null,
      ci_upper_95: null,
    });
  });

  it('returns zeros/negatives error if any value is negative', () => {
    const result = calcORFrom2x2({
      a_events: 10,
      b_non_events: -20,
      c_events: 5,
      d_non_events: 40,
    });

    expect(result).toEqual({
      ok: false,
      reason: 'Zeros/negatives present (no correction applied)',
      or_value: null,
      log_or: null,
      se_log_or: null,
      ci_lower_95: null,
      ci_upper_95: null,
    });
  });
});
