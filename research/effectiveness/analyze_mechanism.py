"""Read-only forensic attribution of the fixed MOM12-1 rule.

No strategy parameters, prices or repository files are changed. Execution
interval diagnostics use information after execution only as explanations.
"""
from pathlib import Path
import json
import sys
import math
import hashlib
import numpy as np
import pandas as pd

import argparse

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    repo_default=Path(__file__).resolve().parents[2]
    parser.add_argument('--repo',type=Path,default=repo_default)
    parser.add_argument('--prices',type=Path,help='saved ETF total-return CSV; default REPO/data/raw/total_return.csv')
    parser.add_argument('--risk-free',type=Path,help='saved monthly risk-free CSV; default REPO/data/raw/risk_free.csv')
    parser.add_argument('--baseline-dir',type=Path,help='original engine output with daily_nav.csv and audit/; default REPO/reports/local')
    parser.add_argument('--out',type=Path,help='generated mechanism directory; default REPO/reports/local/effectiveness/mechanism')
    args=parser.parse_args()
    REPO=args.repo.resolve()
    prices_path=(args.prices or REPO/'data/raw/total_return.csv').resolve()
    rf_path=(args.risk_free or REPO/'data/raw/risk_free.csv').resolve()
    baseline=(args.baseline_dir or REPO/'reports/local').resolve()
    OUT=(args.out or REPO/'reports/local/effectiveness/mechanism').resolve()
    required=[prices_path,rf_path,baseline/'daily_nav.csv']
    required += [baseline/'audit'/name/file for name in ['MOM12_1','EW9'] for file in ['trades.csv','daily_pnl_dollars.csv']]
    required += [baseline/'audit/MOM12_1/decisions.csv']
    for path in required:
        if not path.is_file():
            parser.error(f'Missing saved input: {path}; no data will be downloaded')
    OUT.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(REPO/'src'))
    from sector_momentum.evaluation import capm_hac, paired_block_bootstrap
    SECTORS = ['XLK','XLF','XLE','XLY','XLP','XLV','XLI','XLB','XLU']
    prices = pd.read_csv(prices_path, index_col=0, parse_dates=True)
    nav = pd.read_csv(baseline/'daily_nav.csv', index_col=0, parse_dates=True)
    monthly = nav.resample('ME').last().pct_change().dropna()
    rf = pd.read_csv(rf_path,index_col=0,parse_dates=True)['rf']
    trades = {name: pd.read_csv(baseline/f'audit/{name}/trades.csv',parse_dates=['signal_date','execution_date']) for name in ['MOM12_1','EW9']}
    decisions = pd.read_csv(baseline/'audit/MOM12_1/decisions.csv',parse_dates=['signal_date','execution_date'])
    pnl = {name: pd.read_csv(baseline/f'audit/{name}/daily_pnl_dollars.csv',index_col=0,parse_dates=True) for name in trades}
    assert len(trades['MOM12_1'])==312
    assert len(monthly)==312
    rows=[]
    sector_rows=[]
    for i in range(311):
        m = trades['MOM12_1'].iloc[i]
        mn = trades['MOM12_1'].iloc[i+1]
        e = trades['EW9'].iloc[i]
        en = trades['EW9'].iloc[i+1]
        assert m.execution_date == e.execution_date and mn.execution_date == en.execution_date
        forward = prices.loc[mn.execution_date, SECTORS]/prices.loc[m.execution_date, SECTORS]-1
        selected = m.selected.split(',')
        omitted = [j for j in SECTORS if j not in selected]
        selected_mean = float(forward.loc[selected].mean())
        omitted_mean = float(forward.loc[omitted].mean())
        ew_mean = float(forward.mean())
        spread = selected_mean-omitted_mean
        mom_cost = m.fee/m.pretrade_nav
        ew_cost = e.fee/e.pretrade_nav
        mom_net=(1-mom_cost)*(1+selected_mean)-1
        ew_net=(1-ew_cost)*(1+ew_mean)-1
        audited_mom=mn.pretrade_nav/m.pretrade_nav-1
        audited_ew=en.pretrade_nav/e.pretrade_nav-1
        decision = decisions[decisions.execution_date == m.execution_date].set_index('ticker')
        scores=decision.loc[SECTORS,'score']
        past_ranks=scores.rank(method='average')
        future_ranks=forward.rank(method='average')
        ic=float(past_ranks.corr(future_ranks))
        nextleaders = list(forward.sort_values(ascending=False).index[:3])
        overlap = len(set(selected).intersection(nextleaders))
        indicator=pd.Series([int(j in selected) for j in SECTORS],index=SECTORS)
        binary_alignment=float(indicator.corr(forward))
        dispersion=float(forward.std(ddof=0))
        active = mom_net-ew_net
        fee_drag = mom_cost*(1+selected_mean)-ew_cost*(1+ew_mean)
        rows.append(dict(signal_date=m.signal_date,execution_date=m.execution_date,end_date=mn.execution_date,
            year=m.execution_date.year, selected=m.selected, forward_selected=selected_mean,forward_omitted=omitted_mean,
            forward_all9=ew_mean,selection_spread=spread, gross_selection_active=selected_mean-ew_mean,
            mom_net=mom_net,ew_net=ew_net,net_active=active,relative_fee_drag=fee_drag,
            future_rank_ic=ic,future_top3_overlap=overlap,forward_dispersion=dispersion,
            future_binary_alignment=binary_alignment,
            dispersion_alignment_error=selected_mean-ew_mean-math.sqrt(2)*dispersion*binary_alignment,
            market_forward=float(prices.loc[mn.execution_date,'SPY']/prices.loc[m.execution_date,'SPY']-1),
            audit_mom_error=mom_net-audited_mom,audit_ew_error=ew_net-audited_ew,
            bridge_error=active-((2/3)*spread-fee_drag)))
        sector_rows.append({**{'execution_date':m.execution_date},**{j:((1/3 if j in selected else 0)-1/9)*float(forward[j]) for j in SECTORS}})
    intervals = pd.DataFrame(rows).set_index('execution_date')
    sector_intervals=pd.DataFrame(sector_rows).set_index('execution_date')
    assert intervals[['audit_mom_error','audit_ew_error','bridge_error','dispersion_alignment_error']].abs().max().max()<1e-10
    intervals.to_csv(OUT/'execution_intervals.csv',float_format='%.12g')
    sector_intervals.to_csv(OUT/'interval_sector_gross_active.csv',float_format='%.12g')

    # Exact calendar monthly and yearly P&L attribution: each account has its own
    # beginning NAV; contribution sums equal the difference of simple returns.
    monthly_contrib={}
    annual_contrib={}
    for name in trades:
        col=name+'_5bps'
        period_nav = nav[col].resample('ME').last()
        monthly_contrib[name] = pnl[name].resample('ME').sum().div(period_nav.shift(),axis=0).dropna()
        year_nav=nav[col].resample('YE').last()
        annual_contrib[name]=pnl[name].resample('YE').sum().div(year_nav.shift(),axis=0).dropna()
    active_contrib=monthly_contrib['MOM12_1']-monthly_contrib['EW9']
    active_year=annual_contrib['MOM12_1']-annual_contrib['EW9']
    calendar_active=monthly.MOM12_1_5bps-monthly.EW9_5bps
    assert np.max(np.abs(active_contrib.sum(axis=1)-calendar_active))<1e-10
    assert np.max(np.abs(active_year.sum(axis=1)-(nav.MOM12_1_5bps.resample('YE').last().pct_change()-nav.EW9_5bps.resample('YE').last().pct_change()).dropna()))<1e-10
    active_contrib.to_csv(OUT/'calendar_month_active_attribution.csv',float_format='%.12g')
    active_year.to_csv(OUT/'calendar_year_active_attribution.csv',float_format='%.12g')

    def boot(values, block=6):
        return paired_block_bootstrap(values,block_size=block,draws=20000,seed=20261004)

    def conditional_boot(frame, mask_column, value_column, block=6, draws=20000):
        arr=frame[[mask_column,value_column]].to_numpy()
        n=len(arr); rng=np.random.default_rng(20261004)
        means=[]
        for batch in range(20):
            starts=rng.integers(0,n,size=(draws//20,math.ceil(n/block)))
            ids=((starts[:,:,None]+np.arange(block))%n).reshape(draws//20,-1)[:,:n]
            samples=arr[ids]
            mask=samples[:,:,0].astype(bool)
            values=samples[:,:,1]
            pos=np.sum(np.where(mask,values,0),axis=1)/np.sum(mask,axis=1)
            neg=np.sum(np.where(~mask,values,0),axis=1)/np.sum(~mask,axis=1)
            means.append(np.column_stack([pos,neg,pos-neg]))
        result=np.concatenate(means)
        return {'positive_ci95':np.quantile(result[:,0],[.025,.975]).tolist(),
                'negative_ci95':np.quantile(result[:,1],[.025,.975]).tolist(),
                'difference_ci95':np.quantile(result[:,2],[.025,.975]).tolist(),
                'block':block,'draws':draws}

    stats={
        'input_sha256':{str(path):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [prices_path,baseline/'daily_nav.csv',
                         baseline/'audit/MOM12_1/trades.csv',baseline/'audit/EW9/trades.csv',
                         baseline/'audit/MOM12_1/decisions.csv',rf_path]},
        'observations':{'calendar_months':312,'complete_execution_intervals':311,
                        'interval_start':str(intervals.index[0].date()),'interval_end':str(intervals.end_date.iloc[-1].date()),
                        'partial_final_interval_excluded':str(trades['MOM12_1'].execution_date.iloc[-1].date())},
        'audit_max_errors':intervals[['audit_mom_error','audit_ew_error','bridge_error']].abs().max().to_dict(),
        'interval_summary':{k:boot(intervals[k]) for k in ['selection_spread','gross_selection_active','net_active','future_rank_ic']},
        'calendar_summary':{str(b):boot(calendar_active,b) for b in [3,6,12]},
        'calendar_gross_active':boot(monthly.MOM12_1_0bps-monthly.EW9_0bps),
        'calendar_extra_cost_ann':float(12*((monthly.MOM12_1_0bps-monthly.EW9_0bps)-calendar_active).mean()),
        'calendar_net_win_months':int((calendar_active>0).sum()),
        'calendar_profitable_months':int((monthly.MOM12_1_5bps>0).sum()),
        'interval_rank_ic_positive_months':int((intervals.future_rank_ic>0).sum()),
        'interval_gross_selection_positive_months':int((intervals.gross_selection_active>0).sum()),
        'capm_mom':capm_hac(monthly.MOM12_1_5bps,monthly.SPY_0bps,rf,lags=6),
        'capm_ew9':capm_hac(monthly.EW9_5bps,monthly.SPY_0bps,rf,lags=6),
        'active_on_market_hac':capm_hac(calendar_active,monthly.SPY_0bps,lags=6),
        'active_on_excess_market_hac':capm_hac(calendar_active,monthly.SPY_0bps-rf,lags=6),
        'interval_sector_mean_active_ann':(12*sector_intervals.mean()).to_dict(),
        'calendar_sector_mean_active_ann':(12*active_contrib.mean()).to_dict(),
    }
    # Rank IC is a dimensionless correlation, not a return to annualize.
    stats['interval_summary']['future_rank_ic'].pop('annualized_arithmetic_mean')
    stats['interval_summary']['future_rank_ic'].pop('ci95_annualized_arithmetic')
    for col in ['market_forward','future_rank_ic']:
        temp=intervals[[col,'net_active']].copy();temp['positive']=temp[col]>0
        stats['condition_'+col]={**conditional_boot(temp,'positive','net_active'),
            'n_positive':int(temp.positive.sum()),'n_nonpositive':int((~temp.positive).sum()),
            'positive_mean':float(temp.loc[temp.positive,'net_active'].mean()),
            'nonpositive_mean':float(temp.loc[~temp.positive,'net_active'].mean())}
    stats['future_top3_overlap']={str(o):{'n':int(len(g)),'gross_mean':float(g.gross_selection_active.mean()),'net_mean':float(g.net_active.mean())} for o,g in intervals.groupby('future_top3_overlap')}
    stats['future_top3_overlap_mean']=boot(intervals.future_top3_overlap)
    stats['future_top3_overlap_mean'].pop('annualized_arithmetic_mean')
    stats['future_top3_overlap_mean'].pop('ci95_annualized_arithmetic')
    stats['leave_one_year_out_calendar']={str(year):float(calendar_active[calendar_active.index.year!=year].mean()*12) for year in range(2000,2026)}
    stats['leave_one_year_out_rank_ic']={str(year):float(intervals.loc[intervals.year!=year,'future_rank_ic'].mean()) for year in range(2000,2026)}
    stats['leave_one_year_out_spread_ann']={str(year):float(12*intervals.loc[intervals.year!=year,'selection_spread'].mean()) for year in range(2000,2026)}
    stats['rank_ic_ex_2022']=boot(intervals.loc[intervals.year!=2022,'future_rank_ic'])
    stats['rank_ic_ex_2022'].pop('annualized_arithmetic_mean')
    stats['rank_ic_ex_2022'].pop('ci95_annualized_arithmetic')
    stats['spread_ex_2022']=boot(intervals.loc[intervals.year!=2022,'selection_spread'])
    stats['calendar_ex_2022']=boot(calendar_active[calendar_active.index.year!=2022])
    stats['calendar_leave_2022_2005']=boot(calendar_active[~calendar_active.index.year.isin([2005,2022])])
    stats['calendar_sector_ex_2022_ann']=(12*active_contrib.loc[active_contrib.index.year!=2022].mean()).to_dict()

    cases={}
    for year in [2002,2005,2006,2009,2011,2013,2022,2023]:
        y=active_year.loc[active_year.index.year==year].iloc[0]
        group=intervals.loc[intervals.year==year]
        whole_etf=prices.loc[str(year),SECTORS].iloc[-1]/prices.loc[prices.index.year<year,SECTORS].iloc[-1]-1
        cases[str(year)]={
           'net_strategy_return':float(annual_contrib['MOM12_1'].loc[annual_contrib['MOM12_1'].index.year==year].iloc[0].sum()),
           'net_ew9_return':float(annual_contrib['EW9'].loc[annual_contrib['EW9'].index.year==year].iloc[0].sum()),
           'exact_calendar_active':float(y.sum()),
           'exact_active_sector_contributions':y.to_dict(),
           'exact_strategy_sector_contributions':annual_contrib['MOM12_1'].loc[annual_contrib['MOM12_1'].index.year==year].iloc[0].to_dict(),
           'whole_year_etf_returns':whole_etf.to_dict(),
           'mean_interval_rank_ic':float(group.future_rank_ic.mean()),
           'mean_interval_spread':float(group.selection_spread.mean()),
           'execution_selected':{str(d.date()):r.selected for d,r in group.iterrows()},
        }
    stats['cases']=cases
    with open(OUT/'mechanism_statistics.json','w') as f:
        json.dump(stats,f,indent=2)
    print(json.dumps({k:v for k,v in stats.items() if k not in ['cases','leave_one_year_out_calendar']},indent=2))

if __name__=='__main__':
    main()
