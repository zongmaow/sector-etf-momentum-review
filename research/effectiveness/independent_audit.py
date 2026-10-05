from pathlib import Path
import hashlib,json,math
import numpy as np
import pandas as pd
from sector_momentum.data import load_total_returns,SECTORS
from sector_momentum.engine import Strategy,backtest

import argparse

def main():
    parser=argparse.ArgumentParser(description='Independent numerical audit of regenerated effectiveness outputs')
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--prices',type=Path,help='saved ETF total-return CSV; default REPO/data/raw/total_return.csv')
    parser.add_argument('--out',type=Path,help='study.py output including full private trading ledgers')
    args=parser.parse_args()
    REPO=args.repo.resolve();OUT=(args.out or REPO/'reports/local/effectiveness').resolve()
    prices_path=(args.prices or REPO/'data/raw/total_return.csv').resolve()
    if not prices_path.is_file():
        parser.error(f'Missing saved input: {prices_path}; no data will be downloaded')
    levels=load_total_returns(prices_path)
    names=list(SECTORS)
    f=pd.read_csv(OUT/'etf_monthly_features.csv',index_col='holding_month')
    f.index=pd.PeriodIndex(f.index,freq='M')
    m=levels.groupby(levels.index.to_period('M')).last()
    feature_errors={}; selections=0; stable_errors=0
    manual_std=[]
    for outcome in f.index:
        signal=outcome-1
        scores=m.loc[signal-1,names]/m.loc[signal-12,names]-1
        recent=m.loc[signal,names]/m.loc[signal-3,names]-1
        manual={
          'rank_agreement_3':scores.rank().corr(recent.rank()),
          'signal_std':np.sqrt(((scores-scores.mean())**2).sum()/(len(names)-1)),
          'market_past3':m.loc[signal,'SPY']/m.loc[signal-3,'SPY']-1,
          'market_past24':m.loc[signal,'SPY']/m.loc[signal-24,'SPY']-1 if signal-24 in m.index else np.nan}
        for key,value in manual.items():
            actual=f.loc[outcome,key]
            if np.isnan(value):
                assert np.isnan(actual)
            else:
                feature_errors[key]=max(feature_errors.get(key,0),abs(value-actual))
        chosen=set(sorted(names,key=lambda s:(-scores[s],s))[:3])
        assert chosen==set(f.loc[outcome,'selected'].split(','));selections+=1
        if signal-14 in m.index:
            sets=[]
            for q in [signal,signal-1,signal-2]:
                ss=m.loc[q-1,names]/m.loc[q-12,names]-1
                sets.append(set(sorted(names,key=lambda s:(-ss[s],s))[:3]))
            assert len(set.intersection(*sets))==f.loc[outcome,'stable_names_3_decisions']
            stable_errors+=1
        manual_std.append(manual['signal_std'])
    threshold=float(pd.Series(manual_std,index=f.index).loc['2000':'2009'].median())
    mainf=f.loc['2010':'2025']
    assert mainf['H1_valid'].all() and mainf['H4_valid'].all()
    threshold_error=abs(threshold-json.loads((OUT/'etf_study_manifest.json').read_text())['signal_std_threshold'])
    for h,z in [('H1_recovery',(f.market_past24<0)&(f.market_past3>0)),('H2_agreement',f.rank_agreement_3>=0),('H3_dispersion',f.signal_std>threshold),('H4_joint',(f.signal_std>threshold)&(f.stable_names_3_decisions>=2))]:
        assert (f[h].values==z.values).all()

    # Independently mark-to-market accounting units, fixed-point cost calculation.
    nav_published=pd.read_csv(OUT/'filters_daily_nav_5bps.csv',index_col='date',parse_dates=True)
    trades_checks={}; portfolio_checks={}
    for label in ['F1_avoid_recovery','F2_rank_agreement','F3_joint','MOM','EW9']:
        trades=pd.read_csv(OUT/f'{label}_trades.csv',parse_dates=['execution_date','signal_date']).set_index('execution_date')
        assert len(trades)==192
        p=levels.loc[nav_published.index,names]
        units=np.zeros(9);cash=1e6;nav=[];feemax=0;turnmax=0;daypnlmax=0
        ledger=pd.read_csv(OUT/f'{label}_daily_pnl.csv',index_col='date',parse_dates=True)
        old_nav=1e6
        for i,(date,prices) in enumerate(p.iterrows()):
            prevalues=units*prices.to_numpy()
            before=prevalues.sum()+cash
            if date in trades.index:
                t=trades.loc[date]
                expect_exec=levels.index[levels.index.searchsorted(t.signal_date,side='right')]
                assert date==expect_exec and t.signal_date.to_period('M')==date.to_period('M')-1
                hold=date.to_period('M')
                expected_gate={'F1_avoid_recovery':not f.loc[hold,'H1_recovery'],'F2_rank_agreement':f.loc[hold,'H2_agreement'],'F3_joint':f.loc[hold,'H4_joint'],'MOM':True,'EW9':False}[label]
                assert bool(t.use_momentum)==expected_gate
                sel=set(t.selected.split(',')); assert sel==(set(f.loc[hold,'selected'].split(',')) if expected_gate else set(names))
                target=np.array([1/len(sel) if name in sel else 0 for name in names])
                fee=0.
                for _ in range(50):
                    fee=.0005*np.abs(target*(before-fee)-prevalues).sum()
                after=target*(before-fee)
                gross=np.abs(after-prevalues).sum()
                feemax=max(feemax,abs(fee-t.fee));turnmax=max(turnmax,abs(gross/(2*before)-t.half_gross_turnover))
                units=after/prices.to_numpy();cash=0.
            after_nav=(units*prices.to_numpy()).sum()+cash
            if i:
                daypnlmax=max(daypnlmax,abs(after_nav-old_nav-ledger.loc[date].sum()))
            nav.append(after_nav);old_nav=after_nav
        independent=pd.Series(nav,index=p.index)
        portfolio_checks[label]={'relative_nav_max_error':float((independent/nav_published[label]-1).abs().max()),'fee_dollar_max_error':float(feemax),'half_turnover_max_error':float(turnmax),'daily_pnl_dollar_max_error':float(daypnlmax)}

    # Independent full-calendar Newey-West covariance via double sum.
    raw=pd.read_csv(OUT/'recomputed_baseline_monthly.csv',index_col='date',parse_dates=True); raw.index=raw.index.to_period('M')
    condition=pd.read_csv(OUT/'etf_condition_tests.csv'); inference=pd.read_csv(OUT/'filter_inference.csv')
    hac_error=0;mean_error=0;holm_error=0
    for cost in [0,5,10]:
        rows=condition[condition.cost_bps==cost];pvals=[]
        y=(raw[f'MOM12_1_{cost}bps']-raw[f'EW9_{cost}bps']).loc['2010':'2025'].to_numpy()
        for _,r in rows.iterrows():
            z=mainf[r.hypothesis].to_numpy(bool)
            x=np.column_stack([np.ones(len(y)),z])
            coef=np.linalg.inv(x.T@x)@x.T@y
            scores=x*(y-x@coef)[:,None];n=len(y);kernel=np.maximum(0,1-np.abs(np.arange(n)[:,None]-np.arange(n)[None,:])/13)
            bread=np.linalg.inv(x.T@x); cov=bread@scores.T@kernel@scores@bread*n/(n-x.shape[1]);se=np.sqrt(cov[1,1]);pvalue=math.erfc(abs(coef[1]/se)/math.sqrt(2))
            hac_error=max(hac_error,abs(se-r.contrast_hac_se),abs(pvalue-r.contrast_hac_p));mean_error=max(mean_error,abs(coef[1]-(y[z].mean()-y[~z].mean())),abs(r.true_active_mean-y[z].mean()),abs(r.false_active_mean-y[~z].mean()))
            favorite=~z if r.hypothesis=='H1_recovery' else z
            xx=favorite.astype(float)[:,None];yy=y*favorite
            b=np.linalg.inv(xx.T@xx)@xx.T@yy;s=xx*(yy-xx@b)[:,None];bd=np.linalg.inv(xx.T@xx);v=bd@s.T@kernel@s@bd*n/(n-1);pgroup=math.erfc(abs(b[0]/np.sqrt(v[0,0]))/math.sqrt(2))
            hac_error=max(hac_error,abs(pgroup-r.favorite_hac_p))
            pvals.extend([pvalue,pgroup])
        order=np.argsort(pvals);ordered=np.array(pvals)[order];adjusted=np.maximum.accumulate(np.minimum(1,ordered*(8-np.arange(8))));unsort=np.empty(8);unsort[order]=adjusted
        observed=rows[['contrast_holm8_p','favorite_holm8_p']].to_numpy().ravel();holm_error=max(holm_error,float(np.max(np.abs(unsort-observed))))
        rr=inference[inference.cost_bps==cost]
        pp=rr.hac_p.to_numpy(); order=np.argsort(pp); adj=np.maximum.accumulate(np.minimum(1,pp[order]*(6-np.arange(6))));uns=np.empty(6);uns[order]=adj;holm_error=max(holm_error,float(np.max(np.abs(uns-rr.holm6_p.to_numpy()))))
        assert np.allclose(rr.annualized_arithmetic_difference,12*rr.mean_monthly_difference)

    # Confirm constant masks with published authoritative engine across costs.
    constant_checks=[]
    for cost in [0,5,10]:
        monthly=pd.read_csv(OUT/f'filters_monthly_{cost}bps.csv',index_col='date',parse_dates=True)
        for label in ['MOM','EW9']:
            nav=backtest(levels,Strategy('audit',equal_weight=label=='EW9',signal=None if label=='EW9' else '12_1'),cost,start='2010-01-01').nav
            mr=nav.resample(pd.offsets.MonthEnd()).last().pct_change().dropna()
            constant_checks.append({'cost':cost,'gate':label,'max_monthly_error':float((mr-monthly[label]).abs().max())})

    manifest=json.loads((OUT/'etf_study_manifest.json').read_text()); hash_checks={}
    for key,path in [('prices',prices_path),('protocol',OUT/'research_protocol_zh.md'),('script',Path(__file__).with_name('study.py'))]:
        hash_checks[key]=manifest['sha256'][key]==hashlib.sha256(path.read_bytes()).hexdigest()
    result={'feature_formula_max_errors':feature_errors,'selected_months_verified':selections,'three_way_intersections_verified':stable_errors,'threshold':threshold,'threshold_error':threshold_error,'all_primary_valid':True,'independent_ledgers':portfolio_checks,'hac_max_error':hac_error,'conditional_mean_max_error':mean_error,'holm_max_error':holm_error,'constant_engine_monthly_checks':constant_checks,'hash_matches':hash_checks,'bootstrap_empty_repetitions':[{"hypothesis":r.hypothesis,"block6_invalid":20000-int(r.block6_valid_draws),"block12_invalid":20000-int(r.block12_valid_draws)} for _,r in condition[condition.cost_bps==5].iterrows()]}
    (OUT/'independent_calculation_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
