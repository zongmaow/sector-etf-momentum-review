"""Ex-post diagnostics: publish the complete search grid, not just its winners."""
from __future__ import annotations
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .data import SECTORS, BENCHMARK, TICKERS, _validate_levels, load_total_returns, normalize_yfinance, sha256_file, validate_research_coverage
from .engine import Strategy, backtest
from .reporting import period_result

EXTRA_SECTORS = ('XLRE', 'XLC')
UNIVERSE11 = SECTORS + EXTRA_SECTORS
EXPLORATION_START = '2020-01-01'
EXTRA_WARMUP = '2018-12-31'
END = '2025-12-31'
SOURCES = {
    'XLRE': 'https://www.ssga.com/us/en/individual/etfs/state-street-real-estate-select-sector-spdr-etf-xlre',
    'XLC': 'https://www.ssga.com/us/en/individual/etfs/state-street-communication-services-select-sector-spdr-etf-xlc'}


def download_expanded(prices_path: str | Path, output_dir: str | Path) -> Path:
    """Add only the two missing ETF products; retain the original nine snapshot."""
    import yfinance as yf
    base = load_total_returns(prices_path).loc[EXTRA_WARMUP:END]
    raw = yf.download(list(EXTRA_SECTORS), start=EXTRA_WARMUP, end='2026-01-01',
                      auto_adjust=False, back_adjust=False, actions=True, repair=False,
                      keepna=True, ignore_tz=True, group_by='column', threads=False, progress=False)
    extra = normalize_yfinance(raw, EXTRA_SECTORS)
    fields = {'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Dividends', 'Stock Splits'}
    for ticker in EXTRA_SECTORS:
        if not fields.issubset(set(raw.xs(ticker, axis=1, level=1).columns)):
            raise ValueError(f'Missing supplier fields for {ticker}.')
    if not extra.index.equals(base.index):
        raise ValueError('Extra ETF dates must exactly match the saved base snapshot.')
    combined = pd.concat([base, extra], axis=1).loc[:, list(UNIVERSE11) + [BENCHMARK]]
    validate_research_coverage(combined, EXTRA_WARMUP, END)
    directory = Path(output_dir); directory.mkdir(parents=True, exist_ok=True)
    raw.to_csv(directory / 'raw_extra_yahoo.csv', index_label='date', float_format='%.17g')
    path = directory / 'universe11.csv'
    combined.to_csv(path, index_label='date', float_format='%.17g')
    manifest = {'source': 'Yahoo Finance via yfinance', 'downloaded_at_utc': datetime.now(timezone.utc).isoformat(),
                'yfinance_version': yf.__version__, 'base_prices_sha256': sha256_file(prices_path),
                'combined_prices_sha256': sha256_file(path), 'extra_raw_sha256': sha256_file(directory / 'raw_extra_yahoo.csv'),
                'warmup_start': EXTRA_WARMUP, 'research_start': EXPLORATION_START, 'research_end': END,
                'new_tickers': list(EXTRA_SECTORS), 'product_sources': SOURCES,
                'options': {'auto_adjust': False, 'actions': True, 'repair': False, 'keepna': True},
                'note': 'No backfilled pre-inception history. Original nine levels are unchanged. This is an exploratory universe sensitivity test, not a revised primary hypothesis.'}
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return path


def load_expanded(path: str | Path) -> pd.DataFrame:
    expected = {'date', *UNIVERSE11, BENCHMARK}
    with Path(path).open(newline='') as stream:
        header = next(csv.reader(stream), [])
    if len(set(header)) != len(header) or set(header) != expected:
        raise ValueError('Expanded CSV requires date plus exactly eleven sector ETFs and SPY.')
    frame = pd.read_csv(path, index_col='date', parse_dates=True, float_precision='round_trip')
    return _validate_levels(frame, UNIVERSE11 + (BENCHMARK,))


def window_grid(first_year: int = 2000, last_year: int = 2025) -> list[dict]:
    """All years, five disjoint five-year blocks, final remainder, all 36m windows."""
    rows = [{'kind': 'calendar_year', 'start': f'{year}-01-01', 'end': f'{year}-12-31'}
            for year in range(first_year, last_year + 1)]
    for year in range(first_year, last_year + 1, 5):
        last = min(year + 4, last_year)
        rows.append({'kind': 'five_year_block' if last == year + 4 else 'remaining_years',
                     'start': f'{year}-01-01', 'end': f'{last}-12-31'})
    months = pd.period_range(f'{first_year}-01', f'{last_year}-12', freq='M')
    for i in range(len(months) - 35):
        rows.append({'kind': 'rolling_36m', 'start': str(months[i].start_time.date()),
                     'end': str(months[i + 35].end_time.date())})
    return rows


def outcome(strategy_return: float, benchmark_return: float) -> str:
    profit = 'profit' if strategy_return > 0 else ('loss' if strategy_return < 0 else 'flat')
    relative = 'outperform' if strategy_return > benchmark_return else ('underperform' if strategy_return < benchmark_return else 'tie')
    return profit + '_' + relative


def compare_window(results: dict, window: dict) -> dict:
    first, last = pd.Timestamp(window['start']), pd.Timestamp(window['end'])
    if first.day != 1 or not last.is_month_end or first != first.normalize() or last != last.normalize() or first > last:
        raise ValueError('Diagnostic windows must start at month-open and end at calendar month-end.')
    for result in results.values():
        if first.to_period('M') <= result.nav.index[0].to_period('M') or last.to_period('M') > result.nav.index[-1].to_period('M'):
            raise ValueError('Requested diagnostic window exceeds the available ledger.')
    metrics = {name: period_result(result, window['start'], window['end']) for name, result in results.items()}
    mom, ew, spy = metrics['MOM12_1'], metrics['EW'], metrics['SPY']
    return {**window, 'mom_total_return': mom['total_return'], 'ew_total_return': ew['total_return'],
            'spy_total_return': spy['total_return'], 'mom_cagr': mom['cagr'], 'ew_cagr': ew['cagr'],
            'spy_cagr': spy['cagr'], 'active_total_vs_ew': mom['total_return'] - ew['total_return'],
            'active_total_vs_spy': mom['total_return'] - spy['total_return'],
            'cagr_difference_vs_ew': mom['cagr'] - ew['cagr'], 'cagr_difference_vs_spy': mom['cagr'] - spy['cagr'],
            'mom_max_drawdown': mom['max_drawdown'], 'outcome_vs_ew': outcome(mom['total_return'], ew['total_return'])}


def reset_generated_outputs(directory: Path) -> None:
    """Remove this module's old outputs while retaining unrelated user files."""
    names = ['all_windows.csv', 'calendar_years.csv', 'annual_sector_contributions.csv',
             'universe_comparisons.csv', 'universe_annual_contributions.csv',
             'universe_holdings_comparison.csv', 'universe_selection_counts.csv',
             'exploration.json', 'regime_comparison_zh.md', 'period_comparison.png']
    names += [f'{label}_{strategy}_trades.csv' for label in ['nine', 'eleven'] for strategy in ['MOM12_1', 'EW', 'SPY']]
    for name in names:
        path = directory / name
        if path.is_file():
            path.unlink()


def run_exploration(prices_path: str | Path, out: str | Path,
                    expanded_path: str | Path | None = None, plots: bool = True) -> dict:
    directory = Path(out); directory.mkdir(parents=True, exist_ok=True)
    levels = load_total_returns(prices_path)
    coverage = validate_research_coverage(levels)
    expanded, extra_coverage, extra_hash = None, None, None
    if expanded_path is not None:
        expanded = load_expanded(expanded_path)
        extra_coverage = validate_research_coverage(expanded, EXTRA_WARMUP, END)
        # Keep identical base market paths. A vendor revision must not masquerade as a universe effect.
        saved_base = levels.loc[EXTRA_WARMUP:END, list(TICKERS)]
        if not expanded.loc[EXTRA_WARMUP:END, list(TICKERS)].equals(saved_base):
            raise ValueError('Expanded input must reuse the original nine ETFs and SPY exactly.')
        extra_hash = sha256_file(expanded_path)
    specs = [Strategy('MOM12_1'), Strategy('EW', signal=None, equal_weight=True),
             Strategy('SPY', signal=None, buy_hold_market=True)]
    original = {spec.name: backtest(levels, spec, 5) for spec in specs}
    grid = pd.DataFrame([compare_window(original, window) for window in window_grid()])
    reset_generated_outputs(directory)
    grid.to_csv(directory / 'all_windows.csv', index=False, float_format='%.17g')
    annual = grid.loc[grid.kind == 'calendar_year'].copy()
    annual.to_csv(directory / 'calendar_years.csv', index=False, float_format='%.17g')
    rolling = grid.loc[grid.kind == 'rolling_36m']
    sector_rows = []
    for row in annual.to_dict('records'):
        metrics = period_result(original['MOM12_1'], row['start'], row['end'])
        weights = original['MOM12_1'].weights.loc[row['start']:row['end']]
        for ticker, contribution in metrics['pnl_return_decomposition'].items():
            sector_rows.append({'start': row['start'], 'end': row['end'], 'ticker': ticker,
                                'pnl_return_contribution': contribution,
                                'average_daily_portfolio_weight': float(weights[ticker].mean()) if ticker in weights else None})
    pd.DataFrame(sector_rows).to_csv(directory / 'annual_sector_contributions.csv', index=False)
    comparisons = []
    expanded_contributions, common_mom_results, selection_counts = [], {}, []
    if expanded is not None:
        common_window = {'kind': 'common_history', 'start': EXPLORATION_START, 'end': END}
        for label, universe in [('nine', SECTORS), ('eleven', UNIVERSE11)]:
            common = {spec.name: backtest(expanded, spec, 5, EXPLORATION_START, END, universe=universe) for spec in specs}
            common_mom_results[label] = common['MOM12_1']
            for ticker in universe:
                decisions = common['MOM12_1'].decisions
                chosen = decisions[(decisions.ticker == ticker) & decisions.selected]
                selection_counts.append({'universe': label, 'ticker': ticker, 'selected_monthly_executions': len(chosen),
                                         'total_monthly_executions': len(common['MOM12_1'].trades)})
            comparisons.append({'universe': label, **compare_window(common, common_window)})
            for spec_name, result in common.items():
                result.trades.to_csv(directory / f'{label}_{spec_name}_trades.csv', index=False)
            # Publish the entire common history, not just the extended universe's best year.
            for window in window_grid(2020, 2025):
                comparisons.append({'universe': label, **compare_window(common, window)})
                if window['kind'] == 'calendar_year':
                    metrics = period_result(common['MOM12_1'], window['start'], window['end'])
                    for ticker, contribution in metrics['pnl_return_decomposition'].items():
                        expanded_contributions.append({'universe': label, **window, 'ticker': ticker,
                                                       'pnl_return_contribution': contribution})
        pd.DataFrame(comparisons).to_csv(directory / 'universe_comparisons.csv', index=False, float_format='%.17g')
        pd.DataFrame(expanded_contributions).to_csv(directory / 'universe_annual_contributions.csv', index=False)
        pd.DataFrame(selection_counts).to_csv(directory / 'universe_selection_counts.csv', index=False)
        nine = common_mom_results['nine'].trades.set_index('execution_date')['selected']
        eleven = common_mom_results['eleven'].trades.set_index('execution_date')['selected']
        switches = pd.concat([nine.rename('nine_selected'), eleven.rename('eleven_selected')], axis=1)
        switches['added'] = switches.apply(lambda row: ','.join(sorted(set(row.eleven_selected.split(','))-set(row.nine_selected.split(',')))), axis=1)
        switches['removed'] = switches.apply(lambda row: ','.join(sorted(set(row.nine_selected.split(','))-set(row.eleven_selected.split(',')))), axis=1)
        switches.to_csv(directory / 'universe_holdings_comparison.csv')
    summary = {'analysis_type': 'EX POST EXPLORATORY DIAGNOSTIC; not new out-of-sample confirmation',
               'fixed_rule': 'MOM12_1, top3, next-close execution, 5bps per side; no signal tuning',
               'window_grid': {'years': 26, 'disjoint_five_year_blocks': 5, 'remainder': '2025', 'overlapping_36m_windows': len(rolling)},
               'rolling_descriptive_counts': {'profitable': int((rolling.mom_total_return > 0).sum()),
                                              'outperform_ew': int((rolling.active_total_vs_ew > 0).sum()),
                                              'outperform_spy': int((rolling.active_total_vs_spy > 0).sum())},
               'primary_prices_sha256': sha256_file(prices_path), 'expanded_prices_sha256': extra_hash,
               'primary_coverage': coverage, 'expanded_coverage': extra_coverage,
               'source_files_sha256': {path.name: sha256_file(path) for path in sorted(Path(__file__).parent.glob('*.py'))},
               'selection_notice': 'Highlighted examples and extrema are chosen after observing this full grid. Overlapping windows are dependent; counts are not independent success probabilities. Periods are not tradable advance-known regimes.',
               'universe_notice': 'Eleven-sector comparison starts Jan2020 after warm-up; both universes are newly formed from cash on the same date and use the same engine, costs and base snapshot. It is separate from slices of the continuous Jan2000 original path.',
               'product_sources': SOURCES}
    (directory / 'exploration.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    write_exploration_note(directory, grid, pd.DataFrame(sector_rows), pd.DataFrame(comparisons), summary,
                           pd.DataFrame(expanded_contributions), pd.DataFrame(selection_counts))
    if plots:
        plot_exploration(directory, annual, rolling)
    return summary


def write_exploration_note(directory: Path, grid: pd.DataFrame, contributions: pd.DataFrame,
                           universes: pd.DataFrame, metadata: dict, expanded_contributions: pd.DataFrame,
                           selection_counts: pd.DataFrame) -> None:
    annual = grid[grid.kind == 'calendar_year'].set_index('start')
    lines = ['# 同一规则在不同区间与行业环境中的表现', '',
             '本页属于事后探索。主规则、九行业全样本结论和成本口径保持不变；完整结果见 all_windows.csv。所有数字使用单边 5 bp，分红已经包含在供应商调整价代理中。', '',
             '## 赚钱与跑赢基准是两个问题', '',
             '| 年份 | 策略净累计收益 | EW9 | SPY | 观察 |', '|---|---:|---:|---:|---|']
    for year in [2022, 2011, 2006, 2002]:
        row = annual.loc[f'{year}-01-01']
        label = {'profit_outperform': '赚钱且跑赢EW9', 'profit_underperform': '赚钱但落后EW9',
                 'loss_outperform': '亏钱但比EW9少亏', 'loss_underperform': '亏钱且落后EW9'}.get(row.outcome_vs_ew, row.outcome_vs_ew)
        lines.append(f'| {year} | {row.mom_total_return:.2%} | {row.ew_total_return:.2%} | {row.spy_total_return:.2%} | {label} |')
    lines += ['', '这四个年份是在查看全部 26 个完整日历年之后选出的说明例子，不是事前独立检验。较基准少亏也不能称为绝对盈利。', '',
              '## 行业贡献为什么会变', '',
              '| 区间与持仓 | 对策略累计收益的贡献 | 解读 |', '|---|---:|---|']
    for year, ticker, explanation in [(2005, 'XLE', '当年持有能源的损益贡献为正'),
                                      (2013, 'XLV', '医疗持仓贡献为正'), (2013, 'XLY', '可选消费持仓贡献为正'),
                                      (2020, 'XLK', '科技持仓贡献为正，仍须与宽基比较'),
                                      (2022, 'XLE', '同一能源产品的持有期贡献为正'),
                                      (2023, 'XLE', '下一年同一能源产品的持有期贡献转负')]:
        selected = contributions[(contributions.start == f'{year}-01-01') & (contributions.ticker == ticker)]
        value = selected.iloc[0].pnl_return_contribution
        lines.append(f'| {year} / {ticker} | {100*value:+.2f} 个百分点 | {explanation} |')
    lines += ['', '贡献按该年起始组合 NAV 归一：实际模拟持有期美元 P&L / 年初 NAV。它包含买入、卖出与权重路径，不能当作该 ETF 整年买入持有收益，也不是行业的因果 alpha。交易费用在 COST 中另列，行业贡献与 COST 之和对账到策略该年净收益。', '',
              '这些差异说明，同一个规则在不同的行业领先与反转路径中会有不同结果；并未建立能够事前识别这些环境的交易信号。', '',
              '## 连续区间的完整对照', '',
              '| 完整日历区间 | 策略 CAGR | EW9 CAGR | SPY CAGR |', '|---|---:|---:|---:|']
    for row in grid[grid.kind.isin(['five_year_block', 'remaining_years'])].itertuples():
        lines.append(f'| {row.start[:4]}–{row.end[:4]} | {row.mom_cagr:.2%} | {row.ew_cagr:.2%} | {row.spy_cagr:.2%} |')
    rolling = grid[grid.kind == 'rolling_36m']
    best = rolling.loc[rolling.cagr_difference_vs_ew.idxmax()]
    worst = rolling.loc[rolling.cagr_difference_vs_ew.idxmin()]
    counts = metadata['rolling_descriptive_counts']
    lines += ['', f'全部 {len(rolling)} 个三年滚动窗口中，策略绝对盈利 {counts["profitable"]} 个，跑赢 EW9 {counts["outperform_ew"]} 个，跑赢 SPY {counts["outperform_spy"]} 个。窗口高度重叠，这些是样本描述，不能当作独立成功率或未来概率。', '',
              f'事后相对 EW9 最有利的三年窗口：{best.start[:7]} 至 {best.end[:7]}，CAGR 为 {best.mom_cagr:.2%} 对 {best.ew_cagr:.2%}；最不利的窗口：{worst.start[:7]} 至 {worst.end[:7]}，为 {worst.mom_cagr:.2%} 对 {worst.ew_cagr:.2%}。完整窗口均披露，不因突出窗口而改写主样本结论。', '',
              '## 加入房地产与通信服务', '',
              '[XLRE](https://www.ssga.com/us/en/individual/etfs/state-street-real-estate-select-sector-spdr-etf-xlre) 于 2015 年成立，[XLC](https://www.ssga.com/us/en/individual/etfs/state-street-communication-services-select-sector-spdr-etf-xlc) 于 2018 年成立。不能将它们的基金历史回填至 2000 年。比较采用 2018-12-31 起的预热数据，九行业与十一行业均在 2020 年首交易日收盘从现金建仓，并回测至 2025 年末。', '',
              '保持 MOM12−1、前三等权、执行时点与费用相同。各自使用 EW9 / EW11 基准，因为扩大行业池也改变了等权基准与暴露。', '']
    if universes.empty:
        lines.append('此次未提供扩展行业输入，尚未计算十一行业对照。')
    else:
        lines += ['| 2020–2025 新建账户 | 策略 CAGR | 对应等权 CAGR | SPY CAGR |', '|---|---:|---:|---:|']
        for row in universes[universes.kind == 'common_history'].itertuples():
            lines.append(f'| {row.universe} | {row.mom_cagr:.2%} | {row.ew_cagr:.2%} | {row.spy_cagr:.2%} |')
        lines += ['', '完整共同区间、年度及全部三年滚动结果见 universe_comparisons.csv。这个比较检验产品池敏感性，不支持“挑一组历史赢家行业就证明策略有效”。', '',
                  '| 新行业与年份 | 对十一行业策略当年收益的贡献 |', '|---|---:|']
        for year, ticker in [(2020, 'XLC'), (2021, 'XLC'), (2021, 'XLRE'), (2022, 'XLRE')]:
            row = expanded_contributions[(expanded_contributions.universe == 'eleven') &
                                         (expanded_contributions.start == f'{year}-01-01') &
                                         (expanded_contributions.ticker == ticker)].iloc[0]
            lines.append(f'| {year} / {ticker} | {100*row.pnl_return_contribution:+.2f} 个百分点 |')
        for ticker in EXTRA_SECTORS:
            row = selection_counts[(selection_counts.universe == 'eleven') & (selection_counts.ticker == ticker)].iloc[0]
            lines.append(f'\n{ticker} 在 {row.total_monthly_executions} 次月度执行中入选 {row.selected_monthly_executions} 次。')
        lines += ['', '新增行业的贡献也会转负；十一行业策略在 2021 和 2023 年仍落后于 EW11。新增 ETF 的贡献不等于扩展池的净改善，因为它同时替换了旧行业持仓。完整贡献与替换路径见 universe_annual_contributions.csv 和 universe_holdings_comparison.csv。']
    lines += ['', '## 可以据此判断什么', '',
              '现在可以观察规则如何在盈利、亏损、追上基准与落后基准之间变化，并审查具体持仓的贡献。要把这些描述变成“只在有利环境交易”，还需要事前可观测的环境定义、新规则和真正后续的验证；本次没有增加择时条件或将选中年份包装成新样本外结果。', '',
              '原始九行业的 2000–2025 主结论仍保留。代码和全部探索网格使有利与不利例子都可复算。']
    (directory / 'regime_comparison_zh.md').write_text('\n'.join(lines) + '\n')


def plot_exploration(directory: Path, annual: pd.DataFrame, rolling: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(11, 7))
    x = np.arange(len(annual)); width = .27
    for j, (column, label) in enumerate([('mom_total_return', 'MOM12-1'), ('ew_total_return', 'EW9'), ('spy_total_return', 'SPY')]):
        axes[0].bar(x + (j-1)*width, annual[column]*100, width, label=label)
    axes[0].set_xticks(x, annual.start.str[:4], rotation=60); axes[0].axhline(0, color='black', lw=.6)
    axes[0].set_ylabel('Net calendar-year return (%)'); axes[0].legend(ncol=3)
    dates = pd.to_datetime(rolling.end)
    axes[1].plot(dates, rolling.cagr_difference_vs_ew*100, label='vs EW9')
    axes[1].plot(dates, rolling.cagr_difference_vs_spy*100, label='vs SPY')
    axes[1].axhline(0, color='black', lw=.6); axes[1].set_ylabel('36-month CAGR difference (pp)'); axes[1].legend()
    fig.suptitle('Ex-post diagnostics: fixed rule, full window grid, 5 bps per side')
    fig.tight_layout(); fig.savefig(directory / 'period_comparison.png', dpi=160); plt.close(fig)
