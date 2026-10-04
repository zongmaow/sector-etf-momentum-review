"""Month-end signals; window length and execution frequency are separate choices."""
from __future__ import annotations
import numpy as np
import pandas as pd

WINDOWS = {'12_1': (12, 1), '12_0': (12, 0), '1_0': (1, 0)}


def month_end_levels(levels: pd.DataFrame) -> pd.DataFrame:
    """Use the last observed session in each month, retaining its actual date."""
    if not levels.index.is_unique or not levels.index.is_monotonic_increasing:
        raise ValueError('Dates must be unique and increasing.')
    periods = levels.index.to_period('M')
    unique = periods.unique()
    if len(unique) > 1 and (np.diff(unique.asi8) != 1).any():
        raise ValueError('A whole calendar month is missing.')
    return levels.groupby(periods, sort=True).tail(1)


def momentum_scores(monthly: pd.DataFrame, signal: str) -> pd.DataFrame:
    """At month m: 12_1=P[m-1]/P[m-12]-1 (eleven monthly returns)."""
    if signal not in WINDOWS:
        raise ValueError(f'Unknown signal: {signal}')
    lookback, skip = WINDOWS[signal]
    return monthly.shift(skip).div(monthly.shift(lookback)).sub(1)


def select_names(scores: pd.Series, previous: tuple[str, ...] = (),
                 top_n: int = 3, buffer_rank: int | None = None) -> tuple[str, ...]:
    """Retain existing names ranked within the buffer, then fill by rank.

    Ties are broken alphabetically. Even retained names are reset to equal weight.
    """
    if scores.isna().any() or not np.isfinite(scores.to_numpy()).all():
        raise ValueError('A complete finite signal is required.')
    if not 1 <= top_n <= len(scores):
        raise ValueError('Invalid portfolio size.')
    if buffer_rank is not None and not top_n <= buffer_rank <= len(scores):
        raise ValueError('Buffer rank must lie between top_n and universe size.')
    ranked = sorted(scores.index, key=lambda name: (-scores[name], name))
    retained = [] if buffer_rank is None else [name for name in ranked[:buffer_rank] if name in previous]
    chosen = retained[:top_n]
    chosen.extend(name for name in ranked if name not in chosen)
    return tuple(chosen[:top_n])
