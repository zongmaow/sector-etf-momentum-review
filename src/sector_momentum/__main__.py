from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .data import download_yahoo, TICKERS
from .factors import download_rf
from .reporting import run_research


def main() -> None:
    parser = argparse.ArgumentParser(description='Cost-aware sector ETF momentum review')
    commands = parser.add_subparsers(dest='command', required=True)
    download = commands.add_parser('download', help='Download vendor data and French monthly RF')
    download.add_argument('--out', default='data/raw')
    download.add_argument('--start', default='1998-12-31')
    download.add_argument('--end', default='2026-01-01', help='Exclusive supplier end date')
    run = commands.add_parser('run', help='Run fixed research rules and create reports')
    run.add_argument('--prices', required=True)
    run.add_argument('--rf', help='Optional monthly decimal RF CSV (date,rf)')
    run.add_argument('--out', default='reports/local')
    run.add_argument('--config', default='research_config.json')
    run.add_argument('--no-plots', action='store_true')
    explore = commands.add_parser('explore', help='Publish full ex-post window grid and optional eleven-sector sensitivity')
    explore.add_argument('--prices', required=True)
    explore.add_argument('--out', default='reports/exploration')
    extra = explore.add_mutually_exclusive_group()
    extra.add_argument('--expanded-prices', help='Saved twelve-column ETF input: eleven sectors and SPY')
    extra.add_argument('--download-extra', action='store_true', help='Download XLRE/XLC and retain the base snapshot')
    explore.add_argument('--no-plots', action='store_true')
    demo = commands.add_parser('demo', help='Synthetic pipeline demo, not historical performance')
    demo.add_argument('--out', default='reports/demo')
    demo.add_argument('--config', default='research_config.json')
    demo.add_argument('--no-plots', action='store_true')
    args = parser.parse_args()
    if args.command == 'download':
        levels = download_yahoo(args.out, args.start, args.end)
        rf = download_rf(args.out)
        print(f'Saved {len(levels)} adjusted-level dates and {len(rf)} RF months. Inputs are not filled.')
    elif args.command == 'run':
        run_research(args.prices, args.out, args.config, args.rf, plots=not args.no_plots)
        print(f'Reports saved to {args.out}; read manager_memo.md and analysis.json.')
    elif args.command == 'explore':
        from .exploration import download_expanded, run_exploration
        expanded = args.expanded_prices
        if args.download_extra:
            expanded = download_expanded(args.prices, Path(args.prices).parent / 'extended')
        run_exploration(args.prices, args.out, expanded, plots=not args.no_plots)
        print(f'Ex-post exploration saved to {args.out}; all tested windows are disclosed.')
    else:
        import exchange_calendars as xcals
        config = json.loads(Path(args.config).read_text())
        calendar = xcals.get_calendar('XNYS', start=config['data_start'], end=config['end'])
        dates = calendar.sessions_in_range(config['data_start'], config['end'])
        if dates.tz is not None:
            dates = dates.tz_localize(None)
        rng = np.random.default_rng(2026)
        market = rng.normal(.0002, .009, size=(len(dates), 1))
        shocks = market + rng.normal(0, .006, size=(len(dates), len(TICKERS)))
        frame = pd.DataFrame(100 * np.exp(np.cumsum(shocks, axis=0)), index=dates, columns=TICKERS)
        directory = Path('data/demo'); directory.mkdir(parents=True, exist_ok=True)
        path = directory / 'SYNTHETIC_levels.csv'
        frame.to_csv(path, index_label='date', float_format='%.17g')
        run_research(path, args.out, args.config, demo=True, plots=not args.no_plots)
        print(f'SYNTHETIC demo saved to {args.out}. This is not a backtest of real ETFs.')


if __name__ == '__main__':
    main()
