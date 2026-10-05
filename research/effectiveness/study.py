"""Frozen, retrospective sector-momentum environment tests; no parameter search."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import numpy as np
import pandas as pd
from sector_momentum.data import SECTORS, load_total_returns, validate_research_coverage
from sector_momentum.engine import Strategy, backtest, self_financing_trade
from sector_momentum.signals import month_end_levels, momentum_scores, select_names
from sector_momentum.evaluation import monthly_returns, summary_metrics

REPO=Path(__file__).resolve().parents[2]
OUT=REPO/'reports/local/effectiveness'
NAMES=list(SECTORS)
SEED=20261004
DRAWS=20000
HYPOTHESES=['H1_recovery','H2_agreement','H3_dispersion','H4_joint']

def hac_ols(y, x, lags=12):
    y,x=np.asarray(y,float),np.asarray(x,float)
    valid=np.isfinite(y)&np.isfinite(x).all(axis=1)
    y,x=y[valid],x[valid]
    n,k=x.shape
    if n<=k or np.linalg.matrix_rank(x)<k:
        return None
    coef=np.linalg.lstsq(x,y,rcond=None)[0]
    score=x*(y-x@coef)[:,None]
    meat=score.T@score
    for lag in range(1,min(lags,n-1)+1):
        cross=score[lag:].T@score[:-lag]
        meat+=(1-lag/(lags+1))*(cross+cross.T)
    bread=np.linalg.inv(x.T@x)
    covariance=bread@meat@bread*n/(n-k)
    se=np.sqrt(np.maximum(np.diag(covariance),0))
    p=np.array([math.erfc(abs(b/s)/math.sqrt(2)) if s>0 else (0. if b else 1.) for b,s in zip(coef,se)])
    return {'coef':coef,'se':se,'p':p,'n':n}

def holm(values):
    values=np.asarray(values,float)
    order=np.argsort(values)
    corrected=np.empty(len(values)); running=0.
    for i,j in enumerate(order):
        running=max(running,min(1.,values[j]*(len(values)-i)))
        corrected[j]=running
    return corrected

def block_indexes(n,block,draws=DRAWS,seed=SEED):
    rng=np.random.default_rng(seed)
    starts=rng.integers(0,n,size=(draws,(n+block-1)//block))
    return ((starts[:,:,None]+np.arange(block))%n).reshape(draws,-1)[:,:n]

def joint_ci(y,z,block,seed=SEED):
    """Resample aligned label/return blocks, retain both conditional means."""
    y,z=np.asarray(y,float),np.asarray(z,bool)
    idx=block_indexes(len(y),block,seed=seed)
    yy,zz=y[idx],z[idx]
    nt=zz.sum(axis=1); nf=len(y)-nt
    valid=(nt>0)&(nf>0)
    true=(yy*zz).sum(axis=1)[valid]/nt[valid]
    false=(yy*~zz).sum(axis=1)[valid]/nf[valid]
    return {'true':np.quantile(true,[.025,.975]).tolist(),
            'false':np.quantile(false,[.025,.975]).tolist(),
            'difference':np.quantile(true-false,[.025,.975]).tolist(),
            'valid_draws':int(valid.sum())}

def count_runs(z):
    z=np.asarray(z,bool)
    return int((z&np.r_[True,~z[:-1]]).sum())

def features(levels):
    monthly=month_end_levels(levels).copy()
    monthly.index=monthly.index.to_period('M')
    scores=momentum_scores(monthly[NAMES],'12_1')
    rows=[]
    for outcome in pd.period_range('2000-01','2025-12',freq='M'):
        signal=outcome-1
        s=scores.loc[signal]
        chosen=set(select_names(s))
        stability=np.nan
        if all(q in scores.index and scores.loc[q].notna().all() for q in [signal-1,signal-2]):
            previous=[set(select_names(scores.loc[q])) for q in [signal-1,signal-2]]
            stability=len(chosen.intersection(*previous))
        recent3=monthly.loc[signal,NAMES]/monthly.loc[signal-3,NAMES]-1
        market3=float(monthly.loc[signal,'SPY']/monthly.loc[signal-3,'SPY']-1)
        market24=float(monthly.loc[signal,'SPY']/monthly.loc[signal-24,'SPY']-1) if signal-24 in monthly.index else np.nan
        rows.append({'holding_month':str(outcome),'signal_month':str(signal),
                     'rank_agreement_3':float(s.rank().corr(recent3.rank())),
                     'signal_std':float(s.std(ddof=1)),
                     'stable_names_3_decisions':stability,
                     'market_past3':market3,'market_past24':market24,
                     'selected':','.join(sorted(chosen))})
    f=pd.DataFrame(rows).set_index('holding_month')
    f.index=pd.PeriodIndex(f.index,freq='M')
    threshold=float(f.loc['2000-01':'2009-12','signal_std'].median())
    f['H1_recovery']=(f.market_past24<0)&(f.market_past3>0)
    f['H2_agreement']=f.rank_agreement_3>=0
    f['H3_dispersion']=f.signal_std>threshold
    f['H4_joint']=f.H3_dispersion&(f.stable_names_3_decisions>=2)
    f['H1_valid']=f.market_past24.notna()
    f['H4_valid']=f.stable_names_3_decisions.notna()
    return f,threshold

def condition_rows(f,monthly):
    rows=[]; robustness=[]; loo=[]
    for cost in [0,5,10]:
        aligned=f.loc['2010-01':'2025-12'].copy()
        aligned['active']=monthly[f'MOM12_1_{cost}bps']-monthly[f'EW9_{cost}bps']
        aligned['market']=monthly.SPY_0bps
        sample_rows=[]
        for h in HYPOTHESES:
            y=aligned.active.to_numpy(); z=aligned[h].to_numpy(bool)
            x=np.column_stack([np.ones(len(y)),z])
            fit=hac_ols(y,x)
            favorite=~z if h=='H1_recovery' else z
            # A conditional mean is estimated on the whole calendar grid:
            # intercept-free indicator regression preserves lag spacing in HAC.
            groupfit=hac_ols(y*favorite,favorite[:,None].astype(float))
            control=hac_ols(y,np.column_stack([np.ones(len(y)),z,aligned.market,z*aligned.market]))
            row={'cost_bps':cost,'hypothesis':h,'months':len(y),'true_months':int(z.sum()),'false_months':int((~z).sum()),
                 'true_runs':count_runs(z),'false_runs':count_runs(~z),
                 'true_active_mean':float(y[z].mean()),'false_active_mean':float(y[~z].mean()),
                 'true_minus_false_mean':float(fit['coef'][1]),
                 'contrast_hac_se':float(fit['se'][1]),'contrast_hac_p':float(fit['p'][1]),
                 'favorite_mean':float(groupfit['coef'][0]),'favorite_hac_p':float(groupfit['p'][0]),
                 'market_control_state_coef':float(control['coef'][1]),
                 'market_control_state_hac_p':float(control['p'][1]),
                 'market_control_base_beta':float(control['coef'][2]),
                 'market_control_beta_difference':float(control['coef'][3])}
            if cost==5:
                for block in [6,12]:
                    cis=joint_ci(y,z,block)
                    for label in ['true','false','difference']:
                        row[f'{label}_block{block}_low'],row[f'{label}_block{block}_high']=cis[label]
                    row[f'block{block}_valid_draws']=cis['valid_draws']
                for label,subset in [('2010-2017',aligned.loc[:'2017-12']),('2018-2025',aligned.loc['2018-01':]),
                                     ('without_2022',aligned.loc[aligned.index.year!=2022])]:
                    yy,zz=subset.active.to_numpy(),subset[h].to_numpy(bool)
                    robustness.append({'hypothesis':h,'sample':label,'months':len(yy),'true_months':int(zz.sum()),
                                       'true_mean':float(yy[zz].mean()) if zz.any() else None,
                                       'false_mean':float(yy[~zz].mean()) if (~zz).any() else None,
                                       'true_minus_false_mean':float(yy[zz].mean()-yy[~zz].mean()) if zz.any() and (~zz).any() else None})
                for year in range(2010,2026):
                    sub=aligned.loc[aligned.index.year!=year]
                    zz=sub[h].to_numpy(bool); yy=sub.active.to_numpy()
                    favorite=~zz if h=='H1_recovery' else zz
                    loo.append({'hypothesis':h,'removed_year':year,'true_months':int(zz.sum()),
                                'difference':float(yy[zz].mean()-yy[~zz].mean()) if zz.any() and (~zz).any() else None,
                                'favorite_mean':float(yy[favorite].mean()) if favorite.any() else None})
            sample_rows.append(row)
        adjusted=holm([q[key] for q in sample_rows for key in ['contrast_hac_p','favorite_hac_p']])
        for i,q in enumerate(sample_rows):
            q['contrast_holm8_p']=float(adjusted[2*i]); q['favorite_holm8_p']=float(adjusted[2*i+1])
        rows.extend(sample_rows)
    return pd.DataFrame(rows),pd.DataFrame(robustness),pd.DataFrame(loo)

def gated_nav(levels, use_mom, cost=5, start='2010-01-01',end='2025-12-31'):
    """Daily next-close ledger, switching real security positions, no stitching."""
    monthly=month_end_levels(levels[NAMES].loc[:end])
    scores=momentum_scores(monthly,'12_1')
    baseline=monthly.loc[monthly.index.to_period('M')==pd.Timestamp(start).to_period('M')-1].index[0]
    schedule={}
    for signal in monthly.index[monthly.index>=baseline]:
        position=levels.index.searchsorted(signal,side='right')
        if position==len(levels) or levels.index[position]>pd.Timestamp(end):
            continue
        date=levels.index[position]; p=date.to_period('M')
        gate=bool(use_mom.loc[p])
        chosen=select_names(scores.loc[signal]) if gate else tuple(NAMES)
        target=pd.Series(0.,index=NAMES)
        target.loc[list(chosen)]=1/len(chosen)
        schedule[date]=(target.to_numpy(),gate,signal,chosen)
    dates=levels.loc[baseline:end].index
    arr=levels.loc[dates,NAMES].to_numpy()
    values=np.zeros(len(NAMES)); cash=1_000_000.; nav=[]; trades=[]; pnl=[]
    for i,date in enumerate(dates):
        daypnl=np.zeros(len(NAMES)); fee=0.
        if i:
            daypnl=values*(arr[i]/arr[i-1]-1); values+=daypnl
        if date in schedule:
            target,gate,signal,chosen=schedule[date]
            before=float(values.sum()+cash)
            values,fee,buys,sells=self_financing_trade(values,cash,target,cost/10000)
            cash=0.
            trades.append({'execution_date':date,'signal_date':signal,'use_momentum':gate,'selected':','.join(chosen),
                           'pretrade_nav':before,'posttrade_nav':float(values.sum()),'fee':fee,
                           'gross_traded':buys+sells,'half_gross_turnover':(buys+sells)/(2*before)})
        nav.append(float(values.sum()+cash)); pnl.append(np.r_[daypnl,-fee])
    nav=pd.Series(nav,index=dates)
    ledger=pd.DataFrame(pnl,index=dates,columns=NAMES+['COST'])
    if not np.allclose(ledger.iloc[1:].sum(axis=1),nav.diff().iloc[1:],rtol=1e-10,atol=1e-8):
        raise AssertionError('Gated daily dollar P&L does not reconcile to NAV.')
    return nav,pd.DataFrame(trades),ledger

def mean_ci(a,block):
    a=np.asarray(a,float)
    idx=block_indexes(len(a),block)
    return np.quantile(a[idx].mean(axis=1),[.025,.975])

def filters(levels,f):
    gates={'F1_avoid_recovery':~f.H1_recovery,'F2_rank_agreement':f.H2_agreement,
           'F3_joint':f.H4_joint,'MOM':pd.Series(True,index=f.index),'EW9':pd.Series(False,index=f.index)}
    rows=[]; inference=[]; summaries=[]; checks=[]; costs={}
    for cost in [0,5,10]:
        paths={}; tradepaths={}; monthpaths={}
        for label,gate in gates.items():
            nav,trades,ledger=gated_nav(levels,gate,cost)
            paths[label]=nav;tradepaths[label]=trades;monthpaths[label]=monthly_returns(nav)
            s=summary_metrics(nav)
            s.update({'filter':label,'cost_bps':cost,'total_return':float(nav.iloc[-1]/nav.iloc[0]-1),
                      'momentum_months':int(trades.use_momentum.sum()),'execution_months':len(trades),
                      'mode_switches':int(trades.use_momentum.ne(trades.use_momentum.shift()).iloc[1:].sum()),
                      'half_gross_turnover_sum':float(trades.half_gross_turnover.sum())})
            summaries.append(s)
            if cost==5:
                trades.to_csv(OUT/f'{label}_trades.csv',index=False)
                ledger.to_csv(OUT/f'{label}_daily_pnl.csv',index_label='date')
            if label in ['MOM','EW9']:
                spec=Strategy('audit',equal_weight=label=='EW9',signal=None if label=='EW9' else '12_1')
                original=backtest(levels,spec,cost,start='2010-01-01')
                if not nav.index.equals(original.nav.index):
                    raise AssertionError('Dates differ from original engine.')
                err=float(np.max(np.abs(nav/original.nav-1)))
                if err>1e-11:
                    raise AssertionError(f'Constant gate disagrees with original engine: {err}')
                checks.append({'gate':label,'cost_bps':cost,'max_relative_nav_error':err})
        monthly=pd.DataFrame(monthpaths)
        monthly.to_csv(OUT/f'filters_monthly_{cost}bps.csv',index_label='date')
        if cost==5:
            pd.DataFrame(paths).to_csv(OUT/'filters_daily_nav_5bps.csv',index_label='date')
        family=[]
        for label in [g for g in gates if g.startswith('F')]:
            for benchmark in ['EW9','MOM']:
                a=monthly[label]-monthly[benchmark]
                fit=hac_ols(a,np.ones((len(a),1)))
                row={'filter':label,'cost_bps':cost,'benchmark':benchmark,'months':len(a),
                     'mean_monthly_difference':float(a.mean()),'annualized_arithmetic_difference':float(a.mean()*12),
                     'hac_p':float(fit['p'][0]),'hac_se':float(fit['se'][0]),
                     'annualized_tracking_error':float(a.std(ddof=1)*np.sqrt(12))}
                if cost==5:
                    for block in [6,12]:
                        lo,hi=mean_ci(a,block)
                        row[f'block{block}_annualized_low']=float(lo*12);row[f'block{block}_annualized_high']=float(hi*12)
                family.append(row)
        adjusted=holm([q['hac_p'] for q in family])
        for row,p in zip(family,adjusted):
            row['holm6_p']=float(p)
        inference.extend(family)
        for period,start,end in [('2010-2017','2010-01-01','2017-12-31'),('2018-2025','2018-01-01','2025-12-31')]:
            for label in gates:
                # Slices retain inherited holdings and include the preceding month-end.
                n=paths[label]; before=n.loc[n.index<pd.Timestamp(start)].iloc[-1:]
                subset=pd.concat([before,n.loc[start:end]])
                rows.append({'sample':period,'filter':label,'cost_bps':cost,**summary_metrics(subset),
                             'total_return':float(subset.iloc[-1]/subset.iloc[0]-1)})
    pd.DataFrame(checks).to_csv(OUT/'ledger_validation.csv',index=False)
    return pd.DataFrame(summaries),pd.DataFrame(inference),pd.DataFrame(rows)

def main():
    global REPO,OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=REPO,help='sector-etf-momentum-review checkout with its saved raw prices')
    parser.add_argument('--out',type=Path,default=OUT,help='directory for generated research results')
    parser.add_argument('--prices',type=Path,help='saved ETF total-return CSV; default: REPO/data/raw/total_return.csv')
    parser.add_argument('--protocol',type=Path,help='frozen protocol; default: REPO/reports/effectiveness_snapshot/research_protocol_zh.md')
    args=parser.parse_args()
    REPO,OUT=args.repo.resolve(),args.out.resolve()
    prices=(args.prices or REPO/'data/raw/total_return.csv').resolve()
    protocol=(args.protocol or REPO/'reports/effectiveness_snapshot/research_protocol_zh.md').resolve()
    for required in [prices,protocol]:
        if not required.is_file():
            parser.error(f'Missing saved input: {required}; no data will be downloaded')
    OUT.mkdir(parents=True,exist_ok=True)
    if protocol != OUT/'research_protocol_zh.md':
        (OUT/'research_protocol_zh.md').write_bytes(protocol.read_bytes())
    levels=load_total_returns(prices)
    validate_research_coverage(levels)
    f,threshold=features(levels)
    # Recompute baselines from exactly the same input rather than rely on a
    # historical result cache that could diverge after a vendor data revision.
    baseline={}
    for cost in [0,5,10]:
        for label,spec in [('MOM12_1',Strategy('MOM12_1')),('EW9',Strategy('EW9',signal=None,equal_weight=True))]:
            baseline[f'{label}_{cost}bps']=monthly_returns(backtest(levels,spec,cost).nav)
    baseline['SPY_0bps']=monthly_returns(backtest(levels,Strategy('SPY',signal=None,buy_hold_market=True),0).nav)
    monthly=pd.DataFrame(baseline)
    monthly.to_csv(OUT/'recomputed_baseline_monthly.csv',index_label='date')
    monthly.index=monthly.index.to_period('M')
    f['active_net_5bps']=monthly.MOM12_1_5bps-monthly.EW9_5bps
    f.to_csv(OUT/'etf_monthly_features.csv',index_label='holding_month')
    cond,robustness,loo=condition_rows(f,monthly)
    cond.to_csv(OUT/'etf_condition_tests.csv',index=False)
    robustness.to_csv(OUT/'etf_condition_time_checks.csv',index=False)
    loo.to_csv(OUT/'etf_leave_one_year_out.csv',index=False)
    summaries,inference,periods=filters(levels,f)
    summaries.to_csv(OUT/'filter_summary.csv',index=False)
    inference.to_csv(OUT/'filter_inference.csv',index=False)
    periods.to_csv(OUT/'filter_time_checks.csv',index=False)
    meta={'classification':'retrospective frozen-family research, not untouched out-of-sample',
          'date':'2026-10-04','sample':'ETF inference2010-2025; thresholdcalibration2000-2009',
          'signal_std_threshold':threshold,'seed':SEED,'bootstrap_draws':DRAWS,'block_lengths':[6,12],
          'hypotheses':HYPOTHESES,'condition_pvalue_family_size':8,'filter_pvalue_family_size':6,
          'sha256':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in
                    [('prices',prices),('recomputed_monthly_returns',OUT/'recomputed_baseline_monthly.csv'),
                     ('engine',REPO/'src/sector_momentum/engine.py'),('signals',REPO/'src/sector_momentum/signals.py'),
                     ('protocol',OUT/'research_protocol_zh.md'),('script',Path(__file__))]}}
    (OUT/'etf_study_manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
    print('Threshold:',threshold)
    print(cond[cond.cost_bps==5].to_string(index=False))
    print(summaries[summaries.cost_bps==5].to_string(index=False))
    print(inference[inference.cost_bps==5].to_string(index=False))
    print(robustness.to_string(index=False))

if __name__=='__main__':
    main()
