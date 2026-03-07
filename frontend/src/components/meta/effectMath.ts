export type TwoByTwo = {
  a_events: number | null;
  b_non_events: number | null;
  c_events: number | null;
  d_non_events: number | null;
};

export type OrCalc = {
  ok: boolean;
  reason?: string;
  or_value: number | null;
  log_or: number | null;
  se_log_or: number | null;
  ci_lower_95: number | null;
  ci_upper_95: number | null;
};

export function calcORFrom2x2(x: TwoByTwo): OrCalc {
  const { a_events: a, b_non_events: b, c_events: c, d_non_events: d } = x;

  const nums = [a, b, c, d];
  if (nums.some((v) => v === null || v === undefined)) {
    return {
      ok: false,
      reason: 'Missing cells (need a,b,c,d)',
      or_value: null,
      log_or: null,
      se_log_or: null,
      ci_lower_95: null,
      ci_upper_95: null,
    };
  }

  if (a! <= 0 || b! <= 0 || c! <= 0 || d! <= 0) {
    return {
      ok: false,
      reason: 'Zeros/negatives present (no correction applied)',
      or_value: null,
      log_or: null,
      se_log_or: null,
      ci_lower_95: null,
      ci_upper_95: null,
    };
  }

  const orValue = (a! * d!) / (b! * c!);
  const logOr = Math.log(orValue);
  const se = Math.sqrt(1 / a! + 1 / b! + 1 / c! + 1 / d!);
  const z = 1.96;
  const lo = Math.exp(logOr - z * se);
  const hi = Math.exp(logOr + z * se);

  return {
    ok: true,
    or_value: orValue,
    log_or: logOr,
    se_log_or: se,
    ci_lower_95: lo,
    ci_upper_95: hi,
  };
}
