"""Tests for :mod:`clarion.metrics.stats`."""

import pytest

from clarion.metrics.stats import (
    Interval,
    bootstrap_mean,
    fisher_exact,
    mcnemar_test,
    paired_bootstrap,
    paired_permutation_test,
    required_sample_size,
    wilson_interval,
)


def test_bootstrap_mean_brackets_estimate():
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    interval = bootstrap_mean(values, resamples=2000, seed=42)
    assert interval.low <= interval.estimate <= interval.high
    assert interval.estimate == pytest.approx(5.5)
    assert interval.level == 0.95


def test_bootstrap_mean_empty_is_neutral():
    assert bootstrap_mean([], seed=1) == Interval(0.0, 0.0, 0.0, 0.95)


def test_paired_bootstrap_identical_systems():
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    interval, p = paired_bootstrap(a, a, resamples=1000, seed=7)
    assert interval.estimate == pytest.approx(0.0)
    assert abs(interval.low) < 0.5
    assert abs(interval.high) < 0.5
    assert p > 0.05


def test_paired_bootstrap_clearly_better():
    a = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0]
    b = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    interval, p = paired_bootstrap(a, b, resamples=1000, seed=7)
    assert interval.estimate > 0.0
    assert interval.low > 0.0
    assert p < 0.05


def test_paired_bootstrap_length_mismatch_raises():
    with pytest.raises(ValueError):
        paired_bootstrap([1.0, 2.0], [1.0], seed=1)


def test_paired_permutation_test_identical():
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert paired_permutation_test(a, a, resamples=2000, seed=3) == pytest.approx(1.0)


def test_paired_permutation_test_clearly_better():
    a = [11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0]
    b = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    assert paired_permutation_test(a, b, resamples=5000, seed=3) < 0.05


def test_wilson_interval_perfect_success_has_high_low():
    interval = wilson_interval(10, 10, level=0.95)
    assert interval.estimate == pytest.approx(1.0)
    assert interval.low > 0.5
    assert interval.high == pytest.approx(1.0)


def test_mcnemar_symmetric_near_1():
    assert mcnemar_test(100, 10, 10, 100) == pytest.approx(1.0)


def test_mcnemar_asymmetric_small():
    assert mcnemar_test(100, 15, 1, 100) < 0.05


def test_fisher_exact_matches_hand_computed_tables():
    """Values checked by hand, not by re-running the implementation.

    10/10 against 0/10: two tables out of C(20,10) = 184 756 are no more likely
    than the observed one, so p = 2/184756. Identical proportions give exactly 1.
    """
    assert fisher_exact(10, 0, 0, 10) == pytest.approx(2 / 184_756, rel=1e-12)
    assert fisher_exact(5, 5, 5, 5) == pytest.approx(1.0)
    assert fisher_exact(16, 10, 17, 9) == pytest.approx(1.0)
    assert fisher_exact(7, 10, 9, 8) == pytest.approx(0.7319, abs=5e-5)


def test_fisher_exact_is_not_the_observed_probability_times_the_table_count():
    """Regression guard for the defect this replaced.

    The working-copy test's combinatorial helper ignored the table it was asked
    for, so it summed the *observed* table's probability once per table: it
    reported 0.0129 for 9/48 against 0/48 (ten tables x 0.0012935) where the
    answer is 0.00259, and it could never report less than that product. Both
    halves of that are asserted here, because a future refactor could reintroduce
    one without the other.
    """
    p = fisher_exact(9, 39, 0, 48)
    assert p == pytest.approx(0.002587, abs=5e-6)
    assert p != pytest.approx(0.012935, abs=1e-6)
    assert p < 0.005, "the defective implementation returned 0.0129 here"

    # The upper bound the defect imposed: the observed probability times the
    # number of tables with these margins.
    from math import comb

    observed = comb(48, 9) / comb(96, 9)
    assert p < observed * 10, "p must be able to fall below observed x table count"


def test_fisher_exact_is_symmetric_in_the_table_and_in_its_axes():
    assert fisher_exact(9, 39, 0, 48) == pytest.approx(fisher_exact(0, 48, 9, 39))
    assert fisher_exact(9, 39, 0, 48) == pytest.approx(fisher_exact(39, 9, 48, 0))


def test_fisher_exact_rejects_negative_counts():
    with pytest.raises(ValueError):
        fisher_exact(-1, 5, 5, 5)


def test_fisher_exact_empty_table_is_neutral():
    assert fisher_exact(0, 0, 0, 0) == 1.0


def test_required_sample_size_positive_int():
    n = required_sample_size(1.0, 1.0, power=0.8, level=0.95)
    assert isinstance(n, int)
    assert n >= 1


def test_determinism():
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    i1 = bootstrap_mean(values, resamples=500, seed=123)
    i2 = bootstrap_mean(values, resamples=500, seed=123)
    assert i1 == i2

    p1 = paired_permutation_test(values, values, resamples=500, seed=123)
    p2 = paired_permutation_test(values, values, resamples=500, seed=123)
    assert p1 == p2
