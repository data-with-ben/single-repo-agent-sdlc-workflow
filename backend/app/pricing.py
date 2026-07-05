"""Automated market maker pricing (SPEC.md Section 8).

Pure module, no I/O -- mirrors the shape of objective_engine.py and
team_scoring.py. Computing the actual rolling10DayAvgPersonalScore from
historical ObjectiveResult rows is explicitly out of scope here: fair_value
takes that rolling average as a plain float parameter, already computed by
whichever caller has DB access (the nightly reveal job, task-26).

SPEC.md Section 11 lists the exact BASE/K/spread and demand-pressure curve
as an open decision ("tune against seed"). This module resolves it with a
concrete, documented model:

- fair_value floors at 0.0 -- SPEC does not say prices can go negative, and
  a negative fair value would be nonsensical for a tradeable share.
- demand pressure is a single decaying scalar per consultant, updated by
  the caller once per trading day: decay_demand_pressure() first (for
  however many days elapsed since the last update), then
  apply_trade_pressure() for that day's net trade volume.
- decay_rate=0.8 and pressure_coefficient=0.01 are reasonable illustrative
  defaults, not empirically tuned against real seed trading data -- task-29
  (buy/sell execution) does not exist yet, so there is no real trade volume
  to tune against. Revisit once it lands.
- buy_price/sell_price can violate buyPrice >= sellPrice for large-magnitude
  demand pressure under the raw SPEC formulas (buyPrice - sellPrice =
  fairValue*spread + 2*demandPressure, which goes negative once
  demandPressure is negative enough). Resolved by flooring sell_price so it
  never exceeds buy_price.
"""

from dataclasses import dataclass

BASE = 2.0
K = 0.4
SPREAD = 0.06

DEFAULT_DECAY_RATE = 0.8
DEFAULT_PRESSURE_COEFFICIENT = 0.01


@dataclass
class PriceQuote:
    fair_value: float
    buy_price: float
    sell_price: float


def fair_value(rolling_avg_score: float) -> float:
    return max(0.0, BASE + K * rolling_avg_score)


def decay_demand_pressure(
    pressure: float, days_elapsed: int, decay_rate: float = DEFAULT_DECAY_RATE
) -> float:
    return pressure * decay_rate**days_elapsed


def apply_trade_pressure(
    pressure: float,
    net_shares: float,
    pressure_coefficient: float = DEFAULT_PRESSURE_COEFFICIENT,
) -> float:
    return pressure + net_shares * pressure_coefficient


def buy_price(fv: float, demand_pressure: float) -> float:
    return fv * (1 + SPREAD / 2) + demand_pressure


def sell_price(fv: float, demand_pressure: float) -> float:
    raw_sell = fv * (1 - SPREAD / 2) - demand_pressure
    return min(raw_sell, buy_price(fv, demand_pressure))


def price_quote(rolling_avg_score: float, demand_pressure: float) -> PriceQuote:
    fv = fair_value(rolling_avg_score)
    return PriceQuote(
        fair_value=fv,
        buy_price=buy_price(fv, demand_pressure),
        sell_price=sell_price(fv, demand_pressure),
    )
