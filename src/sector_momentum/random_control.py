"""Retrospective, three-sector controls with the observed entry/exit schedule.

Industry-label permutations are diagnostics, not an exchangeable-asset null or
an alpha significance test. Every simulated portfolio pays its own cash costs.
"""
from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .data import SECTORS, load_total_returns, validate_calendar, validate_research_coverage
from .engine import Strategy, backtest, self_financing_trade
from .evaluation import monthly_returns, summary_metrics


@dataclass
class PathResults:
    metrics: pd.DataFrame
    monthly_nav: np.ndarray
    month_dates: pd.DatetimeIndex
    sample_nav: pd.DataFrame
    sample_trades: pd.DataFrame
    audit: dict


def _write_csv_archive(frame, path, **kwargs):
    """Keep complete path ledgers in a deterministic, lossless CSV archive."""
    raw = frame.to_csv(**kwargs).encode('utf-8')
    Path(path).write_bytes(gzip.compress(raw, mtime=0))


def _empirical_midrank(values, reference):
    """Fraction below the reference plus half the ties; larger is higher."""
    values = np.asarray(values)
    ties = np.isclose(values, reference, atol=1e-12, rtol=0)
    return float(((values < reference) & ~ties).mean() + .5 * ties.mean())


def _drawdown_episode(nav):
    drawdown = nav / nav.cummax() - 1
    trough = drawdown.idxmin()
    peak = nav.loc[:trough].idxmax()
    return {'max_drawdown': float(drawdown.loc[trough]),
            'peak_date': peak.date().isoformat(), 'trough_date': trough.date().isoformat()}


def remapped_targets(template: np.ndarray, draws: int = 4096, seed: int = 20261005):
    """Draw one fixed bijection per path; do not choose it from returns."""
    template = _template(template)
    _draws(draws)
    rng = np.random.default_rng(seed)
    permutations = np.array([rng.permutation(template.shape[1]) for _ in range(draws)])
    # The inverse indexes say which original identity occupies each new slot.
    inverse = np.argsort(permutations, axis=1)
    targets = template[:, inverse].transpose(1, 0, 2).copy()
    return targets, permutations


def overlap_matched_targets(template: np.ndarray, draws: int = 4096, seed: int = 20261006):
    """Match each month's number of retained names, without looking at returns."""
    template = _template(template)
    _draws(draws)
    rng = np.random.default_rng(seed)
    steps, names = template.shape
    result = np.zeros((draws, steps, names), dtype=bool)
    first = np.argsort(rng.random((draws, names)), axis=1)[:, :3]
    np.put_along_axis(result[:, 0], first, True, axis=1)
    for j in range(1, steps):
        keep = int(np.logical_and(template[j], template[j - 1]).sum())
        prior = result[:, j - 1]
        retained = np.argsort(np.where(prior, rng.random((draws, names)), np.inf), axis=1)[:, :keep]
        added = np.argsort(np.where(~prior, rng.random((draws, names)), np.inf), axis=1)[:, :3 - keep]
        np.put_along_axis(result[:, j], retained, True, axis=1)
        np.put_along_axis(result[:, j], added, True, axis=1)
    return result


def _draws(draws):
    if isinstance(draws, bool) or not isinstance(draws, (int, np.integer)) or draws < 1:
        raise ValueError('draws must be a positive integer')


def _template(template):
    template = np.asarray(template)
    if template.ndim != 2 or template.shape[0] < 1 or template.shape[1] != 9:
        raise ValueError('The template needs at least one decision and nine sectors.')
    if not np.isin(template, [0, 1]).all() or not (template.sum(axis=1) == 3).all():
        raise ValueError('Every template decision must select exactly three sectors.')
    return template.astype(bool)


def _rebalance(values, cash, target, rate):
    """Vector fixed-point solve, independently checked against the scalar solver.

    The fee map is a contraction with constant rate because target sums to one.
    The public simulation limits rates to 1%; eight iterations give sufficient
    precision, and the residual is explicitly checked rather than assumed.
    """
    wealth = values.sum(axis=1) + cash
    fee = np.zeros(len(values))
    if rate:
        for _ in range(8):
            fee = rate * np.abs(target * (wealth - fee)[:, None] - values).sum(axis=1)
    after = target * (wealth - fee)[:, None]
    gross = np.abs(after - values).sum(axis=1)
    residual = np.max(np.abs(fee - rate * gross) / wealth)
    financing_error = np.max(np.abs(after.sum(axis=1) + fee - wealth) / wealth)
    if residual > 1e-12 or financing_error > 1e-12:
        raise ArithmeticError('The batch self-financing solve failed its residual check.')
    return after, fee, gross, float(residual), float(financing_error)


def simulate_target_paths(levels: pd.DataFrame, executions: pd.DatetimeIndex,
                          targets: np.ndarray, baseline: pd.Timestamp,
                          cost_bps: float = 5, sample_paths: int = 3) -> PathResults:
    """Run batched long-only portfolios, preserving next-close accounting.

    levels starts at the preceding month-end cash baseline. targets has shape
    (path, execution, sector); each target holds three of the nine ETFs equally.
    Only a few daily paths are retained; all monthly paths enter the statistics.
    """
    validate_calendar(levels.index)
    prices = levels.loc[baseline:, list(SECTORS)].astype(float)
    arr = prices.to_numpy()
    if len(prices) < 3 or prices.index[0] != baseline or not np.isfinite(arr).all() or (arr <= 0).any():
        raise ValueError('Need finite positive levels and the preceding cash baseline.')
    executions = pd.DatetimeIndex(executions)
    if not executions.is_unique or not executions.is_monotonic_increasing or len(executions) == 0:
        raise ValueError('Need distinct increasing execution dates.')
    if not executions.isin(prices.index).all() or executions[0] != prices.index[1]:
        raise ValueError('The first trade must use the first session after baseline.')
    expected = prices.groupby(prices.index.to_period('M')).head(1).index[1:]
    if not executions.equals(expected):
        raise ValueError('Trades must use the first observed session of every holding month.')
    targets = np.asarray(targets)
    if targets.ndim != 3 or targets.shape[1:] != (len(executions), 9) or targets.shape[0] < 1:
        raise ValueError('Targets must have shape (positive paths, executions, nine sectors).')
    if not np.isin(targets, [0, 1]).all() or not (targets.sum(axis=2) == 3).all():
        raise ValueError('Every target needs exactly three binary selections.')
    if not np.isfinite(cost_bps) or not 0 <= cost_bps <= 100:
        raise ValueError('This batch solver supports per-side costs between 0 and 100bp.')
    if isinstance(sample_paths, bool) or not isinstance(sample_paths, (int, np.integer)) or sample_paths < 0:
        raise ValueError('sample_paths must be a nonnegative integer')
    count = len(targets)
    sample_count = min(sample_paths, count)
    target_weights = targets.astype(float) / 3
    values = np.zeros((count, 9))
    cash = np.ones(count)
    prior_nav = np.ones(count)
    peak = prior_nav.copy()
    drawdown = np.zeros(count)
    return_sum = np.zeros(count)
    return_square_sum = np.zeros(count)
    turnover = np.zeros(count)
    fee_fraction = np.zeros(count)
    execution_lookup = {date: j for j, date in enumerate(executions)}
    month_last = prices.groupby(prices.index.to_period('M')).tail(1).index
    monthly_lookup = set(month_last)
    months, month_rows, samples, trade_rows = [], [], [], []
    max_residual = max_financing = max_pnl = 0.
    for j, date in enumerate(prices.index):
        pnl = np.zeros(count)
        if j:
            change = values * (arr[j] / arr[j - 1] - 1)
            pnl = change.sum(axis=1)
            values += change
        fee = np.zeros(count)
        if date in execution_lookup:
            step = execution_lookup[date]
            before = values.sum(axis=1) + cash
            values, fee, gross, residual, financing = _rebalance(
                values, cash, target_weights[:, step], cost_bps / 10000)
            cash.fill(0.)
            fee_fraction += fee / before
            if step:
                turnover += gross / (2 * before)
            max_residual = max(max_residual, residual)
            max_financing = max(max_financing, financing)
            for path in range(sample_count):
                trade_rows.append({'path_id': path, 'execution_date': date,
                                   'selected': ','.join(np.array(SECTORS)[targets[path, step].astype(bool)]),
                                   'pretrade_nav': before[path], 'fee': fee[path],
                                   'gross_traded': gross[path], 'posttrade_nav': values[path].sum()})
        nav = values.sum(axis=1) + cash
        if j:
            change_error = np.max(np.abs(nav - prior_nav - pnl + fee) / prior_nav)
            max_pnl = max(max_pnl, float(change_error))
            daily_return = nav / prior_nav - 1
            return_sum += daily_return
            return_square_sum += daily_return ** 2
        peak = np.maximum(peak, nav)
        drawdown = np.minimum(drawdown, nav / peak - 1)
        if date in monthly_lookup:
            months.append(date)
            month_rows.append(nav.copy())
        samples.append(nav[:sample_count].copy())
        prior_nav = nav
    if max_pnl > 1e-12:
        raise ArithmeticError('Daily price P&L less fees did not reconcile to NAV.')
    observations = len(prices) - 1
    years = (prices.index[-1] - baseline).total_seconds() / (365.25 * 86400)
    if observations < 2 or years <= 0:
        raise ValueError('Need at least two daily investment returns.')
    variance = np.maximum((return_square_sum - return_sum ** 2 / observations) / (observations - 1), 0)
    metrics = pd.DataFrame({'path_id': np.arange(count), 'cagr': nav ** (1 / years) - 1,
                            'annualized_volatility': np.sqrt(variance * 252),
                            'max_drawdown': drawdown,
                            'annualized_half_gross_turnover_ex_initial': turnover / years,
                            'annualized_fee_fraction_including_initial': fee_fraction / years,
                            'total_return': nav - 1})
    return PathResults(metrics, np.array(month_rows), pd.DatetimeIndex(months),
                       pd.DataFrame(samples, index=prices.index), pd.DataFrame(trade_rows),
                       {'max_relative_fee_residual': max_residual,
                        'max_relative_self_financing_error': max_financing,
                        'max_relative_daily_pnl_error': max_pnl})


def independent_path_nav(levels, executions, targets, baseline, cost_bps):
    """Small scalar audit, using the original bisection fee solver."""
    prices = levels.loc[baseline:, list(SECTORS)]
    schedule = dict(zip(executions, targets))
    values = np.zeros(9)
    cash = 1.
    nav = []
    for j, date in enumerate(prices.index):
        if j:
            values *= (prices.iloc[j] / prices.iloc[j - 1]).to_numpy()
        if date in schedule:
            values, _, _, _ = self_financing_trade(values, cash, schedule[date].astype(float) / 3,
                                                   cost_bps / 10000)
            cash = 0.
        nav.append(values.sum() + cash)
    return pd.Series(nav, index=prices.index)


def run_random_controls(prices_path, out, draws=4096, seed=20261005, plots=True):
    """Generate the two fixed diagnostics, all costs and auditable results."""
    _draws(draws)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    levels = load_total_returns(prices_path)
    coverage = validate_research_coverage(levels)
    reference = backtest(levels, Strategy('MOM12_1'), 5)
    executions = pd.DatetimeIndex(reference.trades.execution_date)
    template = np.array([[ticker in names.split(',') for ticker in SECTORS]
                         for names in reference.trades.selected], dtype=bool)
    baseline = reference.nav.index[0]
    levels = levels.loc[:reference.nav.index[-1]]
    remapped, mappings = remapped_targets(template, draws, seed)
    matched = overlap_matched_targets(template, draws, seed + 1)
    sets = {'identity_remap': remapped, 'overlap_matched': matched}
    summary_rows, audits, all_summaries = [], [], []
    sample_curves = {}
    years = (reference.nav.index[-1] - baseline).days / 365.25
    for cost in (0, 5, 10):
        originals = {label: backtest(levels, spec, cost) for label, spec in {
            'MOM12_1': Strategy('MOM12_1'), 'EW9': Strategy('EW9', equal_weight=True, signal=None),
            'SPY': Strategy('SPY', buy_hold_market=True, signal=None)}.items()}
        base_metrics = {}
        for label, result in originals.items():
            stats = summary_metrics(result.nav)
            stats['annualized_half_gross_turnover_ex_initial'] = float(result.trades.half_gross_turnover.iloc[1:].sum() / years)
            stats['annualized_fee_fraction_including_initial'] = float((result.trades.fee / result.trades.pretrade_nav).sum() / years)
            base_metrics[label] = stats
        ew_monthly = monthly_returns(originals['EW9'].nav).to_numpy()
        for method, selections in sets.items():
            # The original path is an audit row, excluded from random distributions.
            targets = np.concatenate([template[None], selections])
            result = simulate_target_paths(levels, executions, targets, baseline, cost)
            original = originals['MOM12_1'].nav / originals['MOM12_1'].nav.iloc[0]
            identity_error = float(np.max(np.abs(result.sample_nav[0].to_numpy() / original.to_numpy() - 1)))
            if identity_error > 1e-11:
                raise AssertionError('Identity control did not reproduce the original daily ledger.')
            original_trades = originals['MOM12_1'].trades
            identity_trades = result.sample_trades.loc[result.sample_trades.path_id == 0]
            fee_error = float(np.max(np.abs(identity_trades.fee.to_numpy() - original_trades.fee.to_numpy() / 1_000_000)))
            turnover_error = float(np.max(np.abs(identity_trades.gross_traded.to_numpy() / (2 * identity_trades.pretrade_nav.to_numpy())
                                                 - original_trades.half_gross_turnover.to_numpy())))
            if max(fee_error, turnover_error) > 1e-11:
                raise AssertionError('Identity fees or turnover differ from the original ledger.')
            audit = {'method': method, 'cost_bps': cost, 'identity_daily_nav_relative_error': identity_error,
                     'identity_fee_normalized_error': fee_error, 'identity_turnover_error': turnover_error, **result.audit}
            if cost == 5:
                scalar = independent_path_nav(levels, executions, selections[0], baseline, cost)
                err = float(np.max(np.abs(result.sample_nav[1].to_numpy() / scalar.to_numpy() - 1)))
                if err > 1e-11:
                    raise AssertionError('Random batch path differs from the independent scalar ledger.')
                audit['first_random_scalar_daily_nav_relative_error'] = err
                sample_curves[f'{method}_path0'] = result.sample_nav[1]
                # At most two random examples, with identity row removed and ids restored.
                trades = result.sample_trades.loc[result.sample_trades.path_id > 0].copy()
                trades['path_id'] -= 1
                _write_csv_archive(trades, out / f'{method}_sample_trades_5bps.csv.gz', index=False)
            audits.append(audit)
            random_metrics = result.metrics.iloc[1:].copy()
            random_metrics['path_id'] -= 1
            monthly = result.monthly_nav[1:] / result.monthly_nav[:-1] - 1
            if len(monthly) != len(ew_monthly):
                raise AssertionError('Random and EW9 monthly return counts differ.')
            active = monthly[:, 1:] - ew_monthly[:, None]
            random_metrics['annualized_arithmetic_active_vs_ew9'] = active.mean(axis=0) * 12
            random_metrics['tracking_error_vs_ew9'] = active.std(axis=0, ddof=1) * np.sqrt(12)
            _write_csv_archive(random_metrics, out / f'{method}_{cost}bps_paths.csv.gz', index=False, float_format='%.12g')
            original_active = float((monthly_returns(originals['MOM12_1'].nav).to_numpy() - ew_monthly).mean() * 12)
            record = {'method': method, 'cost_bps': cost, 'paths': draws,
                      'reference_metrics': base_metrics,
                      'original_annualized_arithmetic_active_vs_ew9': original_active,
                      'share_random_cagr_above_momentum': float((random_metrics.cagr > base_metrics['MOM12_1']['cagr']).mean()),
                      'share_random_cagr_above_ew9': float((random_metrics.cagr > base_metrics['EW9']['cagr']).mean()),
                      'share_random_cagr_above_spy': float((random_metrics.cagr > base_metrics['SPY']['cagr']).mean()),
                      'momentum_cagr_percentile_midrank': _empirical_midrank(random_metrics.cagr, base_metrics['MOM12_1']['cagr']),
                      'momentum_shallower_drawdown_percentile_midrank': _empirical_midrank(random_metrics.max_drawdown, base_metrics['MOM12_1']['max_drawdown']),
                      'share_random_drawdown_shallower_than_momentum': float((random_metrics.max_drawdown > base_metrics['MOM12_1']['max_drawdown']).mean()),
                      'momentum_drawdown_episode': _drawdown_episode(originals['MOM12_1'].nav),
                      'quantiles': {name: np.quantile(random_metrics[name], [.05, .5, .95]).tolist()
                                    for name in random_metrics.columns if name != 'path_id'}}
            for name, quantiles in record['quantiles'].items():
                summary_rows.append({'method': method, 'cost_bps': cost, 'metric': name,
                                     'p05': quantiles[0], 'p50': quantiles[1], 'p95': quantiles[2]})
            all_summaries.append(record)
    _write_csv_archive(pd.DataFrame(np.array(SECTORS)[mappings], columns=SECTORS).assign(path_id=np.arange(draws)), out / 'identity_mappings.csv.gz', index=False)
    pd.DataFrame(summary_rows).to_csv(out / 'distribution_summary.csv', index=False, float_format='%.12g')
    pd.DataFrame(audits).to_csv(out / 'ledger_validation.csv', index=False, float_format='%.12g')
    _write_csv_archive(pd.DataFrame(sample_curves), out / 'example_daily_nav_5bps.csv.gz', index_label='date', float_format='%.12g')
    archives = []
    for path in sorted(out.glob('*.csv.gz')):
        raw = gzip.decompress(path.read_bytes())
        archives.append({'file': path.name, 'decompressed_csv_sha256': hashlib.sha256(raw).hexdigest(),
                         'csv_bytes': len(raw), 'archive_bytes': path.stat().st_size})
    (out / 'storage_manifest.json').write_text(json.dumps({'format': 'UTF-8 CSV, gzip with mtime=0',
        'all_cost_levels_retained_bps': [0, 5, 10], 'files': archives}, indent=2) + '\n')
    price_hash = hashlib.sha256(Path(prices_path).read_bytes()).hexdigest()
    protocol = Path(__file__).resolve().parents[2] / 'research/random_control_protocol.md'
    payload = {'study': 'Retrospective matched-concentration diagnostics; not an alpha significance test',
               'generated_at_utc': datetime.now(timezone.utc).isoformat(),
               'start': '2000-01-01', 'end': '2025-12-31', 'prices_sha256': price_hash,
               'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'protocol_sha256': hashlib.sha256(protocol.read_bytes()).hexdigest() if protocol.exists() else None,
               'numpy_version': np.__version__, 'pandas_version': pd.__version__, 'coverage': coverage,
               'seeds': {'identity_remap': seed, 'overlap_matched': seed + 1}, 'draws_per_method': draws,
               'random_generator': 'numpy.default_rng / PCG64',
               'protocol_defaults_used': bool(draws == 4096 and seed == 20261005),
               'unique_identity_mappings': len(np.unique(mappings, axis=0)),
               'selection_sha256': {method: hashlib.sha256(t.tobytes()).hexdigest() for method, t in sets.items()},
               'all_concentration_and_overlap_checks': bool(all(
                   (t.sum(axis=2) == 3).all() and
                   (np.logical_and(t[:, 1:], t[:, :-1]).sum(axis=2) == np.logical_and(template[1:], template[:-1]).sum(axis=1)).all()
                   for t in sets.values())), 'results': all_summaries,
               'limits': ['Assets are not exchangeable; empirical percentiles are not alpha p-values.',
                          'All history had already been viewed; no prospective validation is claimed.',
                          'Holdings overlap is matched, monetary turnover and risk exposures are not.',
                          'Fees are recomputed per path; random paths are not independent historical market observations.']}
    if not payload['all_concentration_and_overlap_checks']:
        raise AssertionError('Random selections failed concentration or overlap checks.')
    snapshot = Path(__file__).resolve().parents[2] / 'reports/snapshot/analysis.json'
    if snapshot.exists():
        payload['input_matches_original_snapshot'] = json.loads(snapshot.read_text()).get('prices_sha256') == price_hash
    (out / 'summary.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    _write_report(out, payload)
    if plots:
        _plot(out, payload)
    return payload


def _write_report(out, payload):
    records = [r for r in payload['results'] if r['cost_bps'] == 5]
    lines = ['# Three-sector random controls: concentration and industry selection', '',
             'This is a diagnostic on previously observed history. Path percentiles are neither future profit probabilities nor alpha significance tests.', '',
             f"Fixed sample: 2000–2025; {payload['draws_per_method']} paths per method; 0/5/10bp per side. The main tables below use 5bp.", '',
             '| Method | Random CAGR P05 / P50 / P95 | Momentum CAGR historical percentile | Momentum shallower-drawdown percentile | Share beating EW9 |',
             '|---|---|---:|---:|---:|']
    names = {'identity_remap': 'Fixed industry-label remapping (primary)',
             'overlap_matched': 'Monthly overlap-matched sampling (sensitivity)'}
    for r in records:
        q = r['quantiles']['cagr']
        lines.append(f"| {names[r['method']]} | {q[0]:.2%} / {q[1]:.2%} / {q[2]:.2%} | {r['momentum_cagr_percentile_midrank']:.1%} | {r['momentum_shallower_drawdown_percentile_midrank']:.1%} | {r['share_random_cagr_above_ew9']:.1%} |")
    ref = records[0]['reference_metrics']
    lines += ['', f"Reference net CAGRs recomputed on the same dates: MOM12−1 {ref['MOM12_1']['cagr']:.2%}, EW9 {ref['EW9']['cagr']:.2%}, SPY {ref['SPY']['cagr']:.2%}.", '',
              '## Methods and costs', '',
              'The primary method draws one nine-sector bijection per path and keeps it fixed throughout the sample. It preserves three holdings, entry/exit topology, adjacent membership overlap and a relabeled version of the original selection frequencies. The sensitivity method randomly retains and adds the same numbers of sectors each month, changing long-run sector preferences and co-holding structure. Neither uses subsequent returns to choose its labels.', '',
              'Matching membership counts does not match dollar turnover. Each path uses its own weight drift, self-financing trades and cash fees. Annualized fee burden is the sum of fee/pretrade_NAV divided by elapsed years, including formation; it is not the exact reduction in CAGR.', '',
              '| Portfolio/method | Annualized half-gross turnover P05 / P50 / P95 | Annualized fee burden P05 / P50 / P95 | Maximum drawdown P05 / P50 / P95 |',
              '|---|---|---|---|',
              f"| Original momentum | {ref['MOM12_1']['annualized_half_gross_turnover_ex_initial']:.2f} | {ref['MOM12_1']['annualized_fee_fraction_including_initial']:.2%} | {ref['MOM12_1']['max_drawdown']:.2%} |"]
    for r in records:
        a = r['quantiles']['annualized_half_gross_turnover_ex_initial']
        b = r['quantiles']['annualized_fee_fraction_including_initial']
        d = r['quantiles']['max_drawdown']
        lines.append(f"| {names[r['method']]} | {a[0]:.2f} / {a[1]:.2f} / {a[2]:.2f} | {b[0]:.2%} / {b[1]:.2%} / {b[2]:.2%} | {d[0]:.2%} / {d[1]:.2%} / {d[2]:.2%} |")
    episode = records[0]['momentum_drawdown_episode']
    cagr_ranks = ' / '.join(f"{r['momentum_cagr_percentile_midrank']:.1%}" for r in records)
    risk_ranks = ' / '.join(f"{r['momentum_shallower_drawdown_percentile_midrank']:.1%}" for r in records)
    lines += ['', '## Assess returns and drawdowns separately', '',
              f"In primary / sensitivity order, momentum CAGR percentiles are {cagr_ranks}; shallower-drawdown percentiles are {risk_ranks}. Maximum drawdown was {episode['max_drawdown']:.2%}, from the {episode['peak_date']} peak to the {episode['trough_date']} trough. A higher drawdown percentile means a shallower historical loss, not a probability of future protection.",
              'The return result does not erase this historical risk advantage. However, full-period maximum drawdown is determined by one deepest peak-to-trough episode, here in the 2008–2009 financial crisis. Persistence across different crises and later periods has not been established, so this observation does not establish dependable protection or an enablement condition.', '',
              '## Interpretation', '',
              'The percentile describes the historical position of the chosen industry identities, conditional on this market history, three-sector concentration and the original entry/exit schedule. It does not separately identify the economic cause of the price signal: sector correlations, exposures and co-holding structures still differ.', '',
              'A rule near the middle of these concentrated controls does not provide strong historical evidence of useful ranking. Even a high percentile would not establish future alpha: sectors are not exchangeable, the rule and history were already observed, and all paths share one market history.', '',
              'The share of random portfolios beating EW9 is not the general success rate of active investing. Compound returns also depend on volatility, sector preferences, rebalancing and costs. Reversal is not tested here and cannot be inferred by negating momentum returns.', '',
              '## Files and reproduction', '',
              '- [Methods and timing record](../../research/random_control_protocol.md). The protocol and first results were published together; this remains a retrospective diagnostic.',
              '- [Complete results and settings](summary.json), [distribution table](distribution_summary.csv), [ledger validation](ledger_validation.csv).',
              '- `*_paths.csv.gz` disclose every random path at each cost; `identity_mappings.csv.gz` retains the fixed mappings.',
              '- `*_sample_trades_5bps.csv.gz` retain the first two prespecified random trading paths; `example_daily_nav_5bps.csv.gz` retains the first path from each method. Examples were not selected for performance.',
              '- The [storage manifest](storage_manifest.json) records decompressed CSV hashes. `pandas.read_csv` reads `.csv.gz` directly; gzip can also decompress it. All 0/5/10bp results remain available.', '',
              'Run from the repository root:', '', '```sh',
              'python -m sector_momentum random-control --prices data/raw/total_return.csv --out reports/random_local',
              '```', '', 'Saved price SHA-256: `' + payload['prices_sha256'] + '`. A later vendor download may revise history and needs its own hash. Complete 0/10bp results are retained in CSV and JSON.', '']
    (out / 'README.md').write_text('\n'.join(lines))


def _plot(out, payload):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    records = [r for r in payload['results'] if r['cost_bps'] == 5]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    labels = {'identity_remap': 'Fixed industry-label remapping', 'overlap_matched': 'Monthly overlap-matched sampling'}
    for ax, r in zip(axes, records):
        frame = pd.read_csv(out / f"{r['method']}_5bps_paths.csv.gz")
        ax.hist(frame.cagr * 100, bins=35, color='#7e9db5', edgecolor='white')
        for label, color in [('MOM12_1', '#a44535'), ('EW9', '#23694a'), ('SPY', '#66519d')]:
            ax.axvline(r['reference_metrics'][label]['cagr'] * 100, color=color, label=label, linewidth=1.7)
        ax.set_title(labels[r['method']])
        ax.set_xlabel('Net CAGR (%)')
        ax.legend(frameon=False, fontsize=8)
    axes[0].set_ylabel('Random paths')
    fig.suptitle('2000–2025, three-sector controls, 5bp per side\nHistorical diagnostics; not future probabilities', fontsize=11)
    fig.tight_layout()
    fig.savefig(out / 'cagr_distribution.png', dpi=170)
    plt.close(fig)
