"""Dependency-free statistical tooling for comparing MT systems on paired samples.

Implements bootstrap confidence intervals, a paired bootstrap and a paired
permutation test for the mean difference between two systems, McNemar's exact
test and the Wilson score interval for pass-rate reporting, and a paired
t-test sample-size approximation. Only the standard library is used
(:mod:`random` and :mod:`math`); results are deterministic for a given seed.
"""

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "Interval",
    "bootstrap_mean",
    "mcnemar_test",
    "paired_bootstrap",
    "paired_permutation_test",
    "required_sample_size",
    "wilson_interval",
]


@dataclass(frozen=True)
class Interval:
    """A point estimate plus a confidence interval.

    Attributes:
        estimate: The point estimate (e.g. a mean or proportion).
        low: The lower confidence bound.
        high: The upper confidence bound.
        level: The confidence level of ``[low, high]``.
    """

    estimate: float
    low: float
    high: float
    level: float = 0.95


def _validate_bootstrap_args(resamples: int, level: float) -> None:
    """Validate shared bootstrap arguments."""
    if resamples < 1:
        raise ValueError("resamples must be a positive integer")
    if not 0.0 < level < 1.0:
        raise ValueError("level must be strictly between 0 and 1")


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    """Return the *q*-quantile of *sorted_values* by linear interpolation."""
    n = len(sorted_values)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_values[0]
    position = q * (n - 1)
    lower = int(position)
    upper = lower + 1
    fraction = position - lower
    if upper >= n:
        return float(sorted_values[n - 1])
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def _normal_ppf(p: float) -> float:
    """Return the inverse of the standard normal CDF (Acklam's approximation).

    Valid for ``0 < p < 1``; accurate to about 1e-9. Used to derive the
    z-critical values for confidence intervals and power analysis.
    """
    if p <= 0.0 or p >= 1.0:
        raise ValueError("p must be strictly between 0 and 1")
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    low = 0.02425
    high = 1.0 - low
    if p < low:
        q = math.sqrt(-2.0 * math.log(p))
        num = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
        den = (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        return num / den
    if p <= high:
        q = p - 0.5
        r = q * q
        num = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
        den = ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
        return num / den
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    num = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
    den = (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
    return -num / den


def bootstrap_mean(
    values: Sequence[float],
    *,
    resamples: int = 1000,
    level: float = 0.95,
    seed: int = 12345,
) -> Interval:
    """Return a bootstrap confidence interval for the mean of *values*.

    Uses the percentile bootstrap (Efron & Tibshirani, 1993): ``resamples``
    samples are drawn with replacement from *values*, the mean of each resample
    is computed, and the central ``level`` percentile interval is reported
    around the sample mean. Deterministic given *seed*. Returns a zero-width
    neutral interval when *values* is empty.
    """
    _validate_bootstrap_args(resamples, level)
    data = list(values)
    if not data:
        return Interval(0.0, 0.0, 0.0, level)

    rng = random.Random(seed)
    n = len(data)
    estimate = sum(data) / n
    means = [sum(rng.choices(data, k=n)) / n for _ in range(resamples)]
    means.sort()
    low = _percentile(means, (1.0 - level) / 2.0)
    high = _percentile(means, (1.0 + level) / 2.0)
    return Interval(estimate, low, high, level)


def paired_bootstrap(
    system_a: Sequence[float],
    system_b: Sequence[float],
    *,
    resamples: int = 1000,
    level: float = 0.95,
    seed: int = 12345,
) -> tuple[Interval, float]:
    """Bootstrap the mean paired difference ``a - b`` and test it against 0.

    Returns ``(interval, p_value)`` where *interval* is the percentile
    bootstrap interval of the mean difference and *p_value* is a two-sided
    bootstrap p-value. Pairs are resampled together (paired design); the
    p-value is ``2 * min(P(d* <= 0), P(d* >= 0))`` with a +1 count
    correction (Davison & Hinkley, 1997), capped at 1.0. Raises ValueError when
    the two systems have different lengths; returns a neutral
    ``(Interval(0,0,0,level), 1.0)`` for empty input.
    """
    _validate_bootstrap_args(resamples, level)
    a = list(system_a)
    b = list(system_b)
    if len(a) != len(b):
        raise ValueError("system_a and system_b must have equal length")
    n = len(a)
    if n == 0:
        return Interval(0.0, 0.0, 0.0, level), 1.0

    diffs = [x - y for x, y in zip(a, b, strict=True)]
    estimate = sum(diffs) / n
    rng = random.Random(seed)
    bootstrap_diffs = [sum(rng.choices(diffs, k=n)) / n for _ in range(resamples)]
    bootstrap_diffs.sort()
    low = _percentile(bootstrap_diffs, (1.0 - level) / 2.0)
    high = _percentile(bootstrap_diffs, (1.0 + level) / 2.0)

    leq = sum(1 for d in bootstrap_diffs if d <= 0.0)
    geq = sum(1 for d in bootstrap_diffs if d >= 0.0)
    p_lower = (leq + 1) / (resamples + 1)
    p_upper = (geq + 1) / (resamples + 1)
    p_value = min(1.0, 2.0 * min(p_lower, p_upper))
    return Interval(estimate, low, high, level), p_value


def paired_permutation_test(
    system_a: Sequence[float],
    system_b: Sequence[float],
    *,
    resamples: int = 10000,
    seed: int = 12345,
) -> float:
    """Two-sided paired permutation test for a zero mean difference.

    Under the null hypothesis that the two systems are exchangeable, the sign
    of each paired difference is randomly flipped with probability 1/2. The
    statistic is the mean difference; the p-value is the Monte Carlo fraction
    of ``resamples`` sign permutations whose absolute mean difference is at
    least the observed absolute mean difference (Good, 2005). Deterministic
    given *seed*. Raises ValueError on unequal lengths; returns 1.0 for empty
    input.
    """
    a = list(system_a)
    b = list(system_b)
    if len(a) != len(b):
        raise ValueError("system_a and system_b must have equal length")
    if resamples < 1:
        raise ValueError("resamples must be a positive integer")
    n = len(a)
    if n == 0:
        return 1.0

    diffs = [x - y for x, y in zip(a, b, strict=True)]
    observed = sum(diffs) / n
    rng = random.Random(seed)
    count = 0
    for _ in range(resamples):
        permuted = sum(d * rng.choice((1.0, -1.0)) for d in diffs) / n
        if abs(permuted) >= abs(observed):
            count += 1
    return count / resamples


def mcnemar_test(both_pass: int, only_a_pass: int, only_b_pass: int, both_fail: int) -> float:
    """Exact two-sided McNemar test p-value for paired pass/fail counts.

    Given the 2x2 table of paired outcomes (pass/fail for systems A and B), the
    test uses only the discordant cells ``only_a_pass`` and
    ``only_b_pass`` (McNemar, 1947). The p-value is the exact two-sided
    binomial tail ``2 * P(Binomial(n, 0.5) <= min(only_a_pass, only_b_pass))``
    with ``n = only_a_pass + only_b_pass``, capped at 1.0. The concordant
    cells are validated but do not enter the statistic. Returns 1.0 when there
    are no discordant pairs.
    """
    cells = (both_pass, only_a_pass, only_b_pass, both_fail)
    if any(c < 0 for c in cells):
        raise ValueError("cell counts must be non-negative")
    n_discordant = only_a_pass + only_b_pass
    if n_discordant == 0:
        return 1.0
    k = min(only_a_pass, only_b_pass)
    tail = sum(math.comb(n_discordant, i) for i in range(k + 1)) / (2**n_discordant)
    return min(1.0, 2.0 * tail)


def wilson_interval(successes: int, trials: int, *, level: float = 0.95) -> Interval:
    """Return the Wilson score interval for a binomial proportion.

    The estimate is the observed proportion ``successes / trials`` and the
    bounds are the Wilson (1927) score interval, which stays in [0, 1] and does
    not degenerate for 0 or 100% success. Returns a zero-width neutral interval
    when *trials* is 0.
    """
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("invalid success/trial counts")
    if not 0.0 < level < 1.0:
        raise ValueError("level must be strictly between 0 and 1")
    if trials == 0:
        return Interval(0.0, 0.0, 0.0, level)

    z = _normal_ppf((1.0 + level) / 2.0)
    p_hat = successes / trials
    denom = 1.0 + z * z / trials
    center = (p_hat + z * z / (2.0 * trials)) / denom
    half_width = (
        z * math.sqrt(p_hat * (1.0 - p_hat) / trials + z * z / (4.0 * trials * trials)) / denom
    )
    return Interval(p_hat, center - half_width, center + half_width, level)


def required_sample_size(
    effect: float, sd: float, *, power: float = 0.8, level: float = 0.95
) -> int:
    """Approximate the paired t-test sample size needed to detect *effect*.

    Returns the smallest integer n satisfying
    ``n >= ((z_{1-alpha/2} + z_{power}) * sd / effect)^2`` for a two-sided
    paired t-test (Cohen, 1988), where *sd* is the standard deviation of the
    paired differences and *effect* is the mean difference to detect (sign
    ignored). Raises ValueError for a zero effect or invalid power/level.
    """
    if effect == 0:
        raise ValueError("effect must be non-zero")
    if sd < 0:
        raise ValueError("sd must be non-negative")
    if not 0.0 < power < 1.0:
        raise ValueError("power must be strictly between 0 and 1")
    if not 0.0 < level < 1.0:
        raise ValueError("level must be strictly between 0 and 1")
    z_alpha = _normal_ppf((1.0 + level) / 2.0)
    z_power = _normal_ppf(power)
    n = ((z_alpha + z_power) * sd / abs(effect)) ** 2
    return max(1, math.ceil(n))
