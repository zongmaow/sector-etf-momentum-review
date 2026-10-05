"""Retrospective, three-sector controls with the observed entry/exit schedule.

Industry-label permutations are diagnostics, not an exchangeable-asset null or
an alpha significance test. Every simulated portfolio pays its own cash costs.
"""
from __future__ import annotations

from dataclasses import dataclass
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
                trades.to_csv(out / f'{method}_sample_trades_5bps.csv', index=False)
            audits.append(audit)
            random_metrics = result.metrics.iloc[1:].copy()
            random_metrics['path_id'] -= 1
            monthly = result.monthly_nav[1:] / result.monthly_nav[:-1] - 1
            if len(monthly) != len(ew_monthly):
                raise AssertionError('Random and EW9 monthly return counts differ.')
            active = monthly[:, 1:] - ew_monthly[:, None]
            random_metrics['annualized_arithmetic_active_vs_ew9'] = active.mean(axis=0) * 12
            random_metrics['tracking_error_vs_ew9'] = active.std(axis=0, ddof=1) * np.sqrt(12)
            random_metrics.to_csv(out / f'{method}_{cost}bps_paths.csv', index=False, float_format='%.12g')
            original_active = float((monthly_returns(originals['MOM12_1'].nav).to_numpy() - ew_monthly).mean() * 12)
            record = {'method': method, 'cost_bps': cost, 'paths': draws,
                      'reference_metrics': base_metrics,
                      'original_annualized_arithmetic_active_vs_ew9': original_active,
                      'share_random_cagr_above_momentum': float((random_metrics.cagr > base_metrics['MOM12_1']['cagr']).mean()),
                      'share_random_cagr_above_ew9': float((random_metrics.cagr > base_metrics['EW9']['cagr']).mean()),
                      'share_random_cagr_above_spy': float((random_metrics.cagr > base_metrics['SPY']['cagr']).mean()),
                      'momentum_cagr_percentile_midrank': float((((random_metrics.cagr < base_metrics['MOM12_1']['cagr'])
                                                                  & ~np.isclose(random_metrics.cagr, base_metrics['MOM12_1']['cagr'], atol=1e-12, rtol=0)).sum()
                                                                 + .5 * np.isclose(random_metrics.cagr, base_metrics['MOM12_1']['cagr'], atol=1e-12, rtol=0).sum()) / draws),
                      'quantiles': {name: np.quantile(random_metrics[name], [.05, .5, .95]).tolist()
                                    for name in random_metrics.columns if name != 'path_id'}}
            for name, quantiles in record['quantiles'].items():
                summary_rows.append({'method': method, 'cost_bps': cost, 'metric': name,
                                     'p05': quantiles[0], 'p50': quantiles[1], 'p95': quantiles[2]})
            all_summaries.append(record)
    pd.DataFrame(np.array(SECTORS)[mappings], columns=SECTORS).assign(path_id=np.arange(draws)).to_csv(out / 'identity_mappings.csv', index=False)
    pd.DataFrame(summary_rows).to_csv(out / 'distribution_summary.csv', index=False, float_format='%.12g')
    pd.DataFrame(audits).to_csv(out / 'ledger_validation.csv', index=False, float_format='%.12g')
    pd.DataFrame(sample_curves).to_csv(out / 'example_daily_nav_5bps.csv', index_label='date', float_format='%.12g')
    price_hash = hashlib.sha256(Path(prices_path).read_bytes()).hexdigest()
    protocol = Path(__file__).resolve().parents[2] / 'research/random_control_protocol_zh.md'
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
    lines = ['# 随机三行业对照：集中持仓与行业身份选择', '',
             '本报告是已观察历史上的诊断；随机路径百分位不是未来盈利概率，也不是 alpha 显著性检验。', '',
             f"固定样本 2000–2025；每方案 {payload['draws_per_method']} 条路径；单边费用 0/5/10bp，以下主表为 5bp。",
             '', '| 方案 | 随机 CAGR 5/50/95 百分位 | 原动量 CAGR 历史百分位 | 随机超过 EW9 的比例 |',
             '|---|---|---:|---:|']
    names = {'identity_remap': '固定行业身份重映射（主方案）', 'overlap_matched': '逐月匹配名单重合（敏感性）'}
    for r in records:
        q = r['quantiles']['cagr']
        lines.append(f"| {names[r['method']]} | {q[0]:.2%} / {q[1]:.2%} / {q[2]:.2%} | {r['momentum_cagr_percentile_midrank']:.1%} | {r['share_random_cagr_above_ew9']:.1%} |")
    ref = records[0]['reference_metrics']
    lines += ['', f"同日重算基准净 CAGR：MOM12−1 {ref['MOM12_1']['cagr']:.2%}，EW9 {ref['EW9']['cagr']:.2%}，SPY {ref['SPY']['cagr']:.2%}。动量落后等权，但没有落后 SPY。", '',
              '## 方法与成本', '',
              '主方案每条路径只抽一次九行业双射，并在全期固定使用。它保留原动量的三个持仓、进出拓扑、名单相邻重合和选择频率的重命名版本。敏感性方案每期随机保留/新增与原动量相同数量的行业，改变长期行业偏好和共持结构。两者都没有用随后收益来选名单。', '',
              '名单数量匹配不等于金额换手匹配。以下均来自各路径真实漂移与自融资交易，不从原动量扣同一固定费用。年化费用负担为各次 fee/pretrade_NAV 之和除以实际经过年数，含初始建仓；它不等于 CAGR 的精确扣减。', '',
              '| 组合/方案 | 年化半边换手 5/50/95 百分位 | 年化费用负担 5/50/95 百分位 | 最大回撤 5/50/95 百分位 |',
              '|---|---|---|---|',
              f"| 原动量 | {ref['MOM12_1']['annualized_half_gross_turnover_ex_initial']:.2f} | {ref['MOM12_1']['annualized_fee_fraction_including_initial']:.2%} | {ref['MOM12_1']['max_drawdown']:.2%} |"]
    for r in records:
        a = r['quantiles']['annualized_half_gross_turnover_ex_initial']
        b = r['quantiles']['annualized_fee_fraction_including_initial']
        d = r['quantiles']['max_drawdown']
        lines.append(f"| {names[r['method']]} | {a[0]:.2f} / {a[1]:.2f} / {a[2]:.2f} | {b[0]:.2%} / {b[1]:.2%} / {b[2]:.2%} | {d[0]:.2%} / {d[1]:.2%} / {d[2]:.2%} |")
    lines += ['', '## 怎样解释', '',
              '原动量在随机分布中的位置回答：给定这段市场历史、三行业集中度以及原规则的进出节奏，其具体行业身份选择取得了什么历史位置。它不单独识别价格信号的经济因果；行业相关性、风险暴露和共持结构仍不同。', '',
              '若原规则没有明显高于这些随机集中路径，现有历史不足以把收益归功于有用排序。即使排名较高，也不能据此确认未来 alpha，因为行业身份不可交换、规则和历史已被观察，且路径共享同一市场。', '',
              '随机组合优于/劣于 EW9 的比例，不是主动投资普遍成功率。集中组合的复合收益还受波动、行业偏好、再平衡及成本影响。这里没有检验反转，也不能把动量结果取负。', '',
              '## 资料与复算', '',
              '- [计算前固定方案](../../research/random_control_protocol_zh.md)。',
              '- [完整结果与配置](summary.json)、[分布表](distribution_summary.csv)、[账本验证](ledger_validation.csv)。',
              '- `*_paths.csv` 披露所有随机路径在每个成本下的指标；`identity_mappings.csv` 保存固定映射。',
              '- `*_sample_trades_5bps.csv` 保存预定前两条随机路径交易；`example_daily_nav_5bps.csv` 保存各方案第一条路径净值。它们均未按表现挑选。', '',
              '在仓库根目录：', '', '```sh',
              'python -m sector_momentum random-control --prices data/raw/total_return.csv --out reports/random_local',
              '```', '', '本输入价格哈希：`' + payload['prices_sha256'] + '`。重新下载可能有供应商修订，需另记哈希。0/10bp 的全部结果见 CSV 和 JSON。', '']
    (out / 'README.md').write_text('\n'.join(lines))


def _plot(out, payload):
    import matplotlib.pyplot as plt
    records = [r for r in payload['results'] if r['cost_bps'] == 5]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    labels = {'identity_remap': 'Fixed industry-label remapping', 'overlap_matched': 'Monthly overlap-matched sampling'}
    for ax, r in zip(axes, records):
        frame = pd.read_csv(out / f"{r['method']}_5bps_paths.csv")
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
