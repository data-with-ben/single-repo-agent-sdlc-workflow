import pytest

from app.pricing import (
    apply_trade_pressure,
    buy_price,
    decay_demand_pressure,
    fair_value,
    price_quote,
    sell_price,
)


class TestFairValue:
    def test_rises_with_rolling_avg_score(self):
        low = fair_value(0.0)
        high = fair_value(20.0)
        assert high > low

    def test_floors_at_zero_for_very_negative_scores(self):
        assert fair_value(-1000.0) == 0.0

    def test_deterministic(self):
        assert fair_value(12.5) == fair_value(12.5)


class TestPriceRisesWithScoreAndBuyPressure:
    def test_buy_price_rises_with_rolling_avg_score(self):
        low_score_quote = price_quote(rolling_avg_score=0.0, demand_pressure=0.0)
        high_score_quote = price_quote(rolling_avg_score=25.0, demand_pressure=0.0)
        assert high_score_quote.buy_price > low_score_quote.buy_price

    def test_buy_price_rises_with_positive_demand_pressure(self):
        no_pressure = price_quote(rolling_avg_score=15.0, demand_pressure=0.0)
        buy_pressure = price_quote(rolling_avg_score=15.0, demand_pressure=0.5)
        assert buy_pressure.buy_price > no_pressure.buy_price


class TestPriceFallsWithSellPressureAndPoorPerformance:
    def test_sell_price_falls_with_lower_rolling_avg_score(self):
        high_score_quote = price_quote(rolling_avg_score=25.0, demand_pressure=0.0)
        low_score_quote = price_quote(rolling_avg_score=0.0, demand_pressure=0.0)
        assert low_score_quote.sell_price < high_score_quote.sell_price

    def test_sell_price_falls_with_negative_demand_pressure(self):
        no_pressure = price_quote(rolling_avg_score=15.0, demand_pressure=0.0)
        sell_pressure = price_quote(rolling_avg_score=15.0, demand_pressure=-0.5)
        assert sell_pressure.sell_price < no_pressure.sell_price


class TestSpreadInvariant:
    @pytest.mark.parametrize(
        "demand_pressure",
        [-1000.0, -100.0, -10.0, -1.0, -0.1, 0.0, 0.1, 1.0, 10.0, 100.0, 1000.0],
    )
    @pytest.mark.parametrize("rolling_avg_score", [0.0, 5.0, 15.0, 30.0])
    def test_buy_price_always_gte_sell_price(self, demand_pressure, rolling_avg_score):
        quote = price_quote(rolling_avg_score, demand_pressure)
        assert quote.buy_price >= quote.sell_price

    def test_raw_formula_would_violate_invariant_without_the_clamp(self):
        # Sanity check that the test above is actually exercising the clamp,
        # not just confirming a naturally-safe formula: at a large enough
        # negative demand pressure, the raw (unclamped) formula does cross
        # over, proving sell_price's floor is load-bearing.
        fv = fair_value(15.0)
        pressure = -1000.0
        raw_sell = fv * (1 - 0.06 / 2) - pressure
        assert raw_sell > buy_price(fv, pressure)


class TestDeterminism:
    def test_price_quote_is_deterministic(self):
        first = price_quote(rolling_avg_score=18.0, demand_pressure=0.25)
        second = price_quote(rolling_avg_score=18.0, demand_pressure=0.25)
        assert first == second


class TestDemandPressureDecay:
    def test_decay_reduces_magnitude_over_time(self):
        pressure = 1.0
        decayed_1_day = decay_demand_pressure(pressure, days_elapsed=1)
        decayed_5_days = decay_demand_pressure(pressure, days_elapsed=5)
        assert 0 < decayed_5_days < decayed_1_day < pressure

    def test_zero_days_elapsed_leaves_pressure_unchanged(self):
        assert decay_demand_pressure(0.7, days_elapsed=0) == 0.7

    def test_decay_preserves_sign_for_negative_pressure(self):
        pressure = -1.0
        decayed = decay_demand_pressure(pressure, days_elapsed=3)
        assert -1.0 < decayed < 0.0

    def test_decays_toward_zero_over_a_long_horizon(self):
        pressure = 1.0
        decayed = decay_demand_pressure(pressure, days_elapsed=60)
        assert decayed == pytest.approx(0.0, abs=1e-4)

    def test_apply_trade_pressure_adds_net_buy_volume(self):
        pressure = 0.0
        updated = apply_trade_pressure(pressure, net_shares=10)
        assert updated > pressure

    def test_apply_trade_pressure_subtracts_net_sell_volume(self):
        pressure = 0.0
        updated = apply_trade_pressure(pressure, net_shares=-10)
        assert updated < pressure

    def test_decay_then_apply_across_multiple_days_does_not_accumulate_unboundedly(
        self,
    ):
        pressure = 0.0
        for _day in range(30):
            pressure = decay_demand_pressure(pressure, days_elapsed=1)
            pressure = apply_trade_pressure(pressure, net_shares=5)
        # A constant daily buy volume converges to a steady-state pressure
        # rather than growing without bound, since decay removes a fixed
        # fraction each day.
        steady_state = 5 * 0.01 / (1 - 0.8)
        assert pressure == pytest.approx(steady_state, rel=1e-2)


class TestBuyPriceAndSellPriceHelpers:
    def test_buy_price_matches_spec_formula(self):
        fv = 5.0
        pressure = 0.2
        expected = fv * (1 + 0.06 / 2) + pressure
        assert buy_price(fv, pressure) == pytest.approx(expected)

    def test_sell_price_matches_spec_formula_when_within_bounds(self):
        fv = 5.0
        pressure = 0.0
        expected = fv * (1 - 0.06 / 2) - pressure
        assert sell_price(fv, pressure) == pytest.approx(expected)
