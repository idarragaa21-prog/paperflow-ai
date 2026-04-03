import { describe, it, expect } from 'vitest';
import { calcORFrom2x2, type TwoByTwo } from './effectMath';

describe('calcORFrom2x2', () => {
  it('calculates OR correctly for standard inputs', () => {
    const input: TwoByTwo = {
      a_events: 10,
      b_non_events: 20,
      c_events: 5,
      d_non_events: 25,
    };
    const result = calcORFrom2x2(input);
    expect(result.ok).toBe(true);
    expect(result.or_value).toBe(2.5);
    expect(result.log_or).toBeCloseTo(0.916, 3);
    expect(result.se_log_or).toBeCloseTo(0.624, 3);
    expect(result.ci_lower_95).toBeCloseTo(0.735, 3);
    expect(result.ci_upper_95).toBeCloseTo(8.5, 1);
  });

  it('fails if there are null values', () => {
    const input: TwoByTwo = {
      a_events: 10,
      b_non_events: 20,
      c_events: null,
      d_non_events: 25,
    };
    const result = calcORFrom2x2(input);
    expect(result.ok).toBe(false);
    expect(result.reason).toBe('Missing cells (need a,b,c,d)');
    expect(result.or_value).toBeNull();
  });

  it('fails if there are zero values', () => {
    const input: TwoByTwo = {
      a_events: 10,
      b_non_events: 20,
      c_events: 0,
      d_non_events: 25,
    };
    const result = calcORFrom2x2(input);
    expect(result.ok).toBe(false);
    expect(result.reason).toBe('Zeros/negatives present (no correction applied)');
    expect(result.or_value).toBeNull();
  });

  it('fails if there are negative values', () => {
    const input: TwoByTwo = {
      a_events: 10,
      b_non_events: 20,
      c_events: -5,
      d_non_events: 25,
    };
    const result = calcORFrom2x2(input);
    expect(result.ok).toBe(false);
    expect(result.reason).toBe('Zeros/negatives present (no correction applied)');
    expect(result.or_value).toBeNull();
  });
});
