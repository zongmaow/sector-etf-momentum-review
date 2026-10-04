"""Fixed research comparisons, diagnostics, and a reviewable manager memo."""
from __future__ import annotations
import importlib.metadata
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .data import SECTORS, sha256_file, load_total_returns, validate_research_coverage
from .engine import Strategy, backtest
from .evaluation import summary_metrics, monthly_returns, active_stats, capm_hac, paired_block_bootstrap
from .factors import load_rf


def strategies(sleeve_fraction: float) -> list[Strategy]:
    return [Strategy('MOM12_1'), Strategy('MOM12_0', signal='12_0'),
            Strategy('MOM1', signal='1_0'), Strategy('BUFFER12_1', buffer_rank=4),
            Strategy('EW9', signal=None, equal_weight=True),
            Strategy('SPY', signal=None, buy_hold_market=True),
            Strategy('ACCOUNT_MOM20', sleeve_fraction=sleeve_fraction),
            Strategy('ACCOUNT_EW20', signal=None, equal_weight=True, sleeve_fraction=sleeve_fraction),
            Strategy('ACCOUNT_BUFFER20', buffer_rank=4, sleeve_fraction=sleeve_fraction),
            Strategy('ACCOUNT_MOM10', sleeve_fraction=sleeve_fraction / 2)]


def period_nav(nav: pd.Series, first: str, last: str) -> pd.Series:
    first_date = pd.Timestamp(first).to_period('M').start_time
    baseline = nav.index[nav.index < first_date][-1]
    return nav.loc[baseline:last]


def period_result(result, first: str, last: str) -> dict:
    nav = period_nav(result.nav, first, last)
    metrics = summary_metrics(nav)
    monthly = monthly_returns(nav)
    metrics['worst_rolling_12m_return'] = (float((1 + monthly).rolling(12).apply(np.prod, raw=True).sub(1).min())
                                          if len(monthly) >= 12 else None)
    trades = result.trades
    selected = trades.loc[(trades.execution_date >= nav.index[1]) & (trades.execution_date <= nav.index[-1])]
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    regular = selected.loc[~selected.initial_formation]
    metrics['annualized_half_gross_turnover_ex_initial'] = float(regular.half_gross_turnover.sum() / years)
    metrics['annualized_fee_fraction_including_initial'] = float((selected.fee / selected.pretrade_nav).sum() / years)
    metrics['initial_formation_fee_in_period'] = float(selected.loc[selected.initial_formation, 'fee'].sum())
    # Exact dollar P&L decomposition, including negative fee P&L. This is not factor attribution.
    pnl = result.daily_pnl.loc[nav.index[1]:nav.index[-1]].sum() / nav.iloc[0]
    metrics['total_return'] = float(nav.iloc[-1] / nav.iloc[0] - 1)
    metrics['pnl_return_decomposition'] = {name: float(value) for name, value in pnl.items()}
    return metrics


def run_research(prices_path: str | Path, out: str | Path, config_path: str | Path,
                 rf_path: str | Path | None = None, demo: bool = False, plots: bool = True) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    config = json.loads(Path(config_path).read_text())
    if not pd.Timestamp(config['end']).is_month_end:
        raise ValueError('The research end must be a completed calendar month-end.')
    if config['sleeve_fraction'] != .2:
        raise ValueError('Version 0.1 freezes the named account sleeves at 20% (and 10%).')
    if 0 not in config['cost_bps_per_side'] or config['primary_cost_bps'] not in config['cost_bps_per_side']:
        raise ValueError('Include the zero-cost market proxy and the primary cost scenario.')
    levels = load_total_returns(prices_path)
    coverage = validate_research_coverage(levels, config['data_start'], config['end'])
    periods = {'full': [config['start'], config['end']], **config['time_splits']}
    results, monthly_frames, rows, episode_rows = {}, {}, [], []
    for bps in config['cost_bps_per_side']:
        for spec in strategies(config['sleeve_fraction']):
            key = f'{spec.name}_{bps}bps'
            result = backtest(levels, spec, bps, config['start'], config['end'], config['initial_nav'])
            results[key] = result
            monthly_frames[key] = monthly_returns(result.nav)
            for period, (first, last) in periods.items():
                metrics = period_result(result, first, last)
                rows.append({'strategy': spec.name, 'cost_bps': bps, 'period': period,
                             **{k: v for k, v in metrics.items() if k != 'pnl_return_decomposition'}})
            for episode, (first, last) in config['episodes'].items():
                metrics = period_result(result, first, last)
                episode_rows.append({'strategy': spec.name, 'cost_bps': bps, 'episode': episode,
                                     **{k: v for k, v in metrics.items() if k != 'pnl_return_decomposition'},
                                     **{'contribution_' + k: v for k, v in metrics['pnl_return_decomposition'].items()}})
            if bps == config['primary_cost_bps']:
                directory = out / 'audit' / spec.name
                directory.mkdir(parents=True, exist_ok=True)
                result.weights.to_csv(directory / 'daily_weights.csv', index_label='date')
                result.daily_pnl.to_csv(directory / 'daily_pnl_dollars.csv', index_label='date')
                result.trades.to_csv(directory / 'trades.csv', index=False)
                result.decisions.to_csv(directory / 'decisions.csv', index=False)
    monthly = pd.DataFrame(monthly_frames)
    monthly.to_csv(out / 'monthly_returns.csv', index_label='date', float_format='%.17g')
    pd.DataFrame({key: result.nav for key, result in results.items()}).to_csv(out / 'daily_nav.csv', index_label='date')
    summary = pd.DataFrame(rows)
    summary.to_csv(out / 'summary.csv', index=False)
    pd.DataFrame(episode_rows).to_csv(out / 'episodes.csv', index=False)
    rf = None if rf_path is None else load_rf(rf_path, monthly.index)
    primary_cost = config['primary_cost_bps']
    stats = {}
    for period, (first, last) in periods.items():
        sample = monthly.loc[first:last]
        pairs = [('MOM12_1', 'EW9'), ('MOM12_1', 'SPY'), ('BUFFER12_1', 'MOM12_1'),
                 ('MOM12_0', 'MOM12_1'), ('MOM1', 'MOM12_1'),
                 ('ACCOUNT_MOM20', 'SPY'), ('ACCOUNT_EW20', 'SPY'),
                 ('ACCOUNT_MOM20', 'ACCOUNT_EW20'), ('ACCOUNT_BUFFER20', 'ACCOUNT_MOM20'), ('ACCOUNT_MOM10', 'SPY')]
        stats[period] = {}
        for strategy, benchmark in pairs:
            a, b = sample[f'{strategy}_{primary_cost}bps'], sample[f'{benchmark}_{primary_cost}bps']
            active = active_stats(a, b)
            rolling_difference = ((1 + a).rolling(12).apply(np.prod, raw=True) -
                                  (1 + b).rolling(12).apply(np.prod, raw=True))
            active['worst_rolling_12m_active_return'] = float(rolling_difference.min())
            stats[period][f'{strategy}_vs_{benchmark}'] = {
                'active': active,
                'paired_block_bootstrap': paired_block_bootstrap(a - b, config['bootstrap_block_months'],
                                                               config['bootstrap_draws'], config['bootstrap_seed'])}
        for name in ['MOM12_1', 'EW9', 'BUFFER12_1']:
            stats[period][name + '_market_regression'] = capm_hac(sample[f'{name}_{primary_cost}bps'],
                                                               sample['SPY_0bps'], rf,
                                                               config['hac_lags'])
    versions = {}
    for library in ['numpy', 'pandas', 'exchange_calendars', 'yfinance', 'matplotlib']:
        try:
            versions[library] = importlib.metadata.version(library)
        except importlib.metadata.PackageNotFoundError:
            versions[library] = 'not installed'
    metadata = {'data_kind': 'SYNTHETIC DEMONSTRATION' if demo else 'supplier historical adjusted-level proxy',
                'config': config, 'config_sha256': sha256_file(config_path),
                'prices_sha256': sha256_file(prices_path), 'coverage': coverage, 'library_versions': versions,
                'rf_sha256': None if rf_path is None else sha256_file(rf_path),
                'market_regression': 'SPY total return less French RF' if rf is not None else 'SPY total return, RF explicitly assumed zero; not a fully specified CAPM',
                'stats': stats,
                'limitations': ['Retrospective known-history splits; no genuinely untouched prospective sample.',
                                'EW9 comparison mixes selection and concentration; market regression does not identify causality.',
                                'Supplier-adjusted levels are reinvestment proxies, not independently rebuilt tradable cash-flow accounts.',
                                'Flat trading costs are scenarios, not historical spread/impact estimates.',
                                'ETF position weights are not look-through constituent concentration.',
                                'No multi-factor model or matched-concentration random portfolio control in version 0.1.']}
    (out / 'analysis.json').write_text(json.dumps(metadata, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    write_memo(out, summary, metadata, demo)
    if plots:
        plot_results(out, results, monthly, primary_cost, demo)
    return metadata


def write_memo(out: Path, summary: pd.DataFrame, metadata: dict, demo: bool) -> None:
    cost = metadata['config']['primary_cost_bps']
    table = summary[(summary.cost_bps == cost) & (summary.period == 'full')]
    lines = ['# Sector ETF momentum: investment review', '',
             '**SYNTHETIC DATA: no investment conclusion may be drawn.**' if demo else
             'Historical research using supplier-adjusted ETF levels; simulated holdings and execution.', '',
             'Decision: does a fixed sector momentum rule justify an active allocation after costs?', '',
             '| Portfolio | CAGR | Volatility | Max drawdown | Annual half-gross turnover* |',
             '|---|---:|---:|---:|---:|']
    for row in table.itertuples():
        lines.append(f'| {row.strategy} | {row.cagr:.2%} | {row.annualized_volatility:.2%} | {row.max_drawdown:.2%} | {row.annualized_half_gross_turnover_ex_initial:.2f} |')
    primary = metadata['stats']['full']['MOM12_1_vs_EW9']
    ci = primary['paired_block_bootstrap']['ci95_annualized_arithmetic']
    active = primary['active']
    acct = metadata['stats']['full']['ACCOUNT_MOM20_vs_SPY']['active']
    final = metadata['stats']['final_historical']['MOM12_1_vs_EW9']
    final_ci = final['paired_block_bootstrap']['ci95_annualized_arithmetic']
    lines += ['', f'*Initial formation is excluded from turnover but included in net returns. Costs are {cost} bps per side. SPY is buy-and-hold; account sleeves rebalance monthly.*', '',
              f'Primary mean active return vs EW9 (arithmetic annualization): {active["annualized_arithmetic_active"]:.2%}; TE {active["tracking_error_ann"]:.2%}; IR {active["information_ratio"]:.2f}.',
              f'Circular-block 95% interval for annualized mean active return: [{ci[0]:.2%}, {ci[1]:.2%}]. This is not an interval for CAGR.',
              f'Final historical period interval: [{final_ci[0]:.2%}, {final_ci[1]:.2%}].',
              f'80% SPY / 20% momentum account TE vs SPY: {acct["tracking_error_ann"]:.2%}; illustrative budget {metadata["config"]["account_te_budget_vs_spy"]:.2%}.', '',
              '## Manager interpretation', '']
    if demo:
        lines.append('This run validates the pipeline only. Replace the synthetic fixture with documented real data before evaluating the hypothesis.')
    else:
        if ci[0] > 0 and final_ci[0] > 0 and acct['tracking_error_ann'] <= metadata['config']['account_te_budget_vs_spy']:
            lines.append('The fixed primary rule passes these historical gates. It merits a prospective paper-trading review; these tests do not establish causal alpha or authorize a live allocation.')
        elif active['annualized_arithmetic_active'] > 0:
            lines.append('The primary rule has positive average historical active return, but the uncertainty, period stability, or account risk gate is insufficient. The evidence does not justify automatic adoption.')
        else:
            lines.append('The primary rule does not improve average net return over EW9 in this snapshot. Do not select a different window just because it wins this table; secondary variants require a new prospective test.')
    lines += ['', 'The full account must be compared with both SPY and an 80% SPY / 20% EW9 account. Their difference helps isolate the implemented selection rule from the decision to add a sector sleeve.', '',
              'The buffer changes both trading and holdings. Compare its gross and net outcomes before attributing an improvement to cost savings. See summary.csv, episodes.csv, and analysis.json for fixed window/cost/time comparisons.', '',
              'The four historical episodes are explanations of failure or resilience, not four separate experiments used to choose the rule. Daily dollar P&L records reconcile sector gains, SPY gains and fees to total wealth changes.', '',
              'Known limits: revised Yahoo adjustments; synthetic next-close fills; no taxes, spreads by date, market impact, or institutional capacity test; changing sector definitions; nine historical products omit today’s separate real-estate and communication ETFs; retrospective holdout; no multi-factor or matched-concentration random controls.', '',
              'Generated from the saved input and config hashes recorded in analysis.json.']
    (out / 'manager_memo.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def plot_results(out: Path, results: dict, monthly: pd.DataFrame, cost: int, demo: bool) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 160})
    title_prefix = 'SYNTHETIC DEMO — ' if demo else ''
    names = ['MOM12_1', 'EW9', 'SPY', 'BUFFER12_1']
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for name in names:
        nav = results[f'{name}_{cost}bps'].nav
        axes[0].plot(nav.index, nav / nav.iloc[0], label=name, linewidth=1.3)
        axes[1].plot(nav.index, nav / nav.cummax() - 1, linewidth=1)
    axes[0].set_yscale('log'); axes[0].set_ylabel('Wealth (log scale)'); axes[0].legend(ncol=4)
    axes[1].set_ylabel('Drawdown'); fig.suptitle(title_prefix + f'Fixed sector ETF rules, {cost} bps per side')
    fig.tight_layout(); fig.savefig(out / 'wealth_drawdown.png'); plt.close(fig)
    weights = results[f'MOM12_1_{cost}bps'].weights[list(SECTORS)]
    weights = weights.groupby(weights.index.to_period('M')).tail(1)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.stackplot(weights.index, weights.to_numpy().T, labels=SECTORS, alpha=.85)
    ax.set_ylim(0, 1); ax.set_ylabel('ETF weights'); ax.legend(ncol=9, fontsize=8, loc='upper center', bbox_to_anchor=(.5, -.08))
    ax.set_title(title_prefix + 'Holdings: monthly observed weights after daily drift')
    fig.tight_layout(); fig.savefig(out / 'holdings.png'); plt.close(fig)
