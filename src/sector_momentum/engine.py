"""Daily self-financing accounting, with month-end decisions and next-close trades."""
from __future__ import annotations
from dataclasses import dataclass
import json
import numpy as np
import pandas as pd
from .data import SECTORS, BENCHMARK, TICKERS, validate_calendar
from .signals import month_end_levels, momentum_scores, select_names, WINDOWS


@dataclass(frozen=True)
class Strategy:
    name: str
    signal: str | None = '12_1'
    top_n: int = 3
    buffer_rank: int | None = None
    sleeve_fraction: float = 1.0
    equal_weight: bool = False
    buy_hold_market: bool = False


@dataclass
class Backtest:
    nav: pd.Series
    weights: pd.DataFrame
    trades: pd.DataFrame
    decisions: pd.DataFrame
    daily_pnl: pd.DataFrame


def self_financing_trade(values: np.ndarray, cash: float, target: np.ndarray,
                         cost_rate: float) -> tuple[np.ndarray, float, float, float]:
    """Solve C=c*sum(abs(w*(V-C)-x)); cash is not a charged security trade.

    The cost rate applies to each dollar bought or sold, not to half-turnover.
    """
    values, target = np.asarray(values, float), np.asarray(target, float)
    if values.ndim != 1 or values.shape != target.shape:
        raise ValueError('Positions and targets must be equal-sized vectors.')
    if not np.isfinite(values).all() or not np.isfinite(target).all():
        raise ValueError('Positions and targets must be finite.')
    if (values < 0).any() or (target < 0).any() or cash < 0 or not np.isfinite(cash):
        raise ValueError('Only nonnegative long-only positions and cash are supported.')
    if not np.isclose(target.sum(), 1, atol=1e-12, rtol=0):
        raise ValueError('Target weights must sum to one.')
    if not 0 <= cost_rate < 1:
        raise ValueError('The per-side cost rate must be in [0,1).')
    wealth = float(values.sum() + cash)
    if wealth <= 0:
        raise ValueError('Positive pretrade wealth is required.')
    low, high = 0., wealth
    for _ in range(80):
        fee = (low + high) / 2
        residual = fee - cost_rate * np.abs(target * (wealth - fee) - values).sum()
        if residual > 0:
            high = fee
        else:
            low = fee
    fee = (low + high) / 2
    after = target * (wealth - fee)
    delta = after - values
    buys, sells = float(np.maximum(delta, 0).sum()), float(np.maximum(-delta, 0).sum())
    if not np.isclose(fee, cost_rate * (buys + sells), atol=1e-8 * wealth):
        raise ArithmeticError('Self-financing cost solver did not converge.')
    return after, fee, buys, sells


def backtest(levels: pd.DataFrame, strategy: Strategy, cost_bps: float = 5,
             start: str = '2000-01-01', end: str = '2025-12-31',
             initial_nav: float = 1_000_000.) -> Backtest:
    """Old holdings receive execution-day returns; new holdings start next day.

    Includes the last preceding month-end as a cash NAV baseline. Prices are
    adjusted-level return proxies, so units are accounting units, not ETF shares.
    The final portfolio is valued without liquidation.
    """
    validate_calendar(levels.index)
    levels = levels.loc[:pd.Timestamp(end), list(TICKERS)].astype(float)
    if not np.isfinite(levels.to_numpy()).all() or (levels.to_numpy() <= 0).any():
        raise ValueError('All adjusted levels must be finite and positive.')
    if not 0 <= strategy.sleeve_fraction <= 1 or initial_nav <= 0:
        raise ValueError('Invalid sleeve size or initial NAV.')
    if not 0 <= cost_bps < 10000:
        raise ValueError('Invalid cost in basis points.')
    monthly = month_end_levels(levels.loc[:, list(SECTORS)])
    start_date = pd.Timestamp(start)
    if start_date.day != 1 or start_date != start_date.normalize():
        raise ValueError('The backtest start must be the first calendar day of a month.')
    initial_month = start_date.to_period('M') - 1
    initial_dates = monthly.index[monthly.index.to_period('M') == initial_month]
    if len(initial_dates) != 1:
        raise ValueError('The preceding month-end observation is required.')
    baseline = initial_dates[0]
    if strategy.signal is not None and not strategy.equal_weight and not strategy.buy_hold_market:
        scores = momentum_scores(monthly, strategy.signal)
    else:
        scores = pd.DataFrame(0., index=monthly.index, columns=SECTORS)
    if scores.loc[baseline].isna().any():
        raise ValueError('Insufficient warm-up for the initial decision.')
    if not (levels.index > baseline).any():
        raise ValueError('No session is available after the first signal.')
    schedule = {}
    previous: tuple[str, ...] = ()
    decision_rows = []
    for signal_date in monthly.index[monthly.index >= baseline]:
        pos = levels.index.searchsorted(signal_date, side='right')
        if pos == len(levels):
            continue
        execution_date = levels.index[pos]
        if strategy.buy_hold_market and schedule:
            continue
        if strategy.buy_hold_market:
            chosen = (BENCHMARK,)
        elif strategy.equal_weight:
            chosen = SECTORS
        else:
            chosen = select_names(scores.loc[signal_date], previous, strategy.top_n, strategy.buffer_rank)
        previous_names = previous
        previous = chosen
        target = pd.Series(0., index=TICKERS)
        if strategy.buy_hold_market:
            target[BENCHMARK] = 1.
        else:
            target.loc[list(chosen)] = strategy.sleeve_fraction / len(chosen)
            target[BENCHMARK] = 1 - strategy.sleeve_fraction
        schedule[execution_date] = (signal_date, target.to_numpy(), chosen)
        rank_order = sorted(SECTORS, key=lambda name: (-scores.loc[signal_date, name], name))
        month_pos = monthly.index.get_loc(signal_date)
        endpoints = None
        if strategy.signal is not None and not strategy.equal_weight and not strategy.buy_hold_market:
            horizon, gap = WINDOWS[strategy.signal]
            endpoints = (monthly.index[month_pos-horizon], monthly.index[month_pos-gap])
        for name in SECTORS:
            decision_rows.append({'signal_date': signal_date, 'execution_date': execution_date,
                                  'ticker': name, 'score': float(scores.loc[signal_date, name]),
                                  'rank': rank_order.index(name) + 1,
                                  'signal_start': None if endpoints is None else endpoints[0],
                                  'signal_end': None if endpoints is None else endpoints[1],
                                  'previously_selected': name in previous_names,
                                  'selected': name in chosen, 'target_weight': float(target[name])})
    dates = levels.index[levels.index >= baseline]
    values = np.zeros(len(TICKERS))
    cash = float(initial_nav)
    nav_rows, weight_rows, trade_rows, pnl_rows = [], [], [], []
    for j, date in enumerate(dates):
        day_pnl = np.zeros(len(TICKERS))
        fee = 0.
        if j:
            day_pnl = values * ((levels.loc[date] / levels.loc[dates[j - 1]]).to_numpy() - 1)
            values += day_pnl
        if date in schedule:
            signal_date, target, chosen = schedule[date]
            pre_nav = float(values.sum() + cash)
            initial = bool(cash == initial_nav and values.sum() == 0)
            old = values.copy()
            values, fee, buys, sells = self_financing_trade(values, cash, target, cost_bps / 10000)
            cash = 0.
            trade_rows.append({'signal_date': signal_date, 'execution_date': date,
                               'initial_formation': initial, 'pretrade_nav': pre_nav,
                               'posttrade_nav': float(values.sum()), 'fee': fee,
                               'buys': buys, 'sells': sells,
                               'half_gross_turnover': (buys + sells) / (2 * pre_nav),
                               'selected': ','.join(chosen),
                               'pretrade_weight_hhi': float(np.square(old / pre_nav).sum()),
                               'pretrade_weights_json': json.dumps(dict(zip(TICKERS, (old/pre_nav).tolist()))),
                               'target_weights_json': json.dumps(dict(zip(TICKERS, target.tolist())))})
        nav = float(values.sum() + cash)
        pnl_rows.append(np.r_[day_pnl, -fee])
        nav_rows.append(nav)
        weight_rows.append(np.r_[values / nav, cash / nav])
    return Backtest(pd.Series(nav_rows, index=dates, name=strategy.name),
                    pd.DataFrame(weight_rows, index=dates, columns=list(TICKERS) + ['CASH']),
                    pd.DataFrame(trade_rows), pd.DataFrame(decision_rows),
                    pd.DataFrame(pnl_rows, index=dates, columns=list(TICKERS) + ['COST']))
