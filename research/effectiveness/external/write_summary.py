"""Render transparent external-validation tables from stored numerical results."""
from pathlib import Path
import json
import hashlib

import argparse

def main():
    parser=argparse.ArgumentParser(description='Render the French validation memo from regenerated numerical summaries')
    parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[3]/'reports/local/effectiveness/external')
    args=parser.parse_args();ROOT=args.out.resolve()
    basic = json.loads((ROOT / "basic_summary.json").read_text())
    conditions = json.loads((ROOT / "conditional_results.json").read_text())

    def pct(x):
        return f"{100*x:.2f}%"

    def ci(values):
        return f"[{100*values[0]:.2f}, {100*values[1]:.2f}]"

    lines = [
        "# External validation with ten historical industry portfolios",
        "",
        "Study date: 2026-10-04. The data use Kenneth French's official 202608 CRSP vintage; research returns are strictly truncated at December 2025.",
        "",
        "This validation did not identify a reliably confirmed ex-ante favorable environment across periods and industry universes. Mean long-run net active returns are positive for the ten-industry portfolios, but separate estimates for the earlier and contemporary periods remain substantially uncertain. The label 'industry momentum' does not imply the same returns across different industry classifications and investment instruments.",
        "",
        "## Data and limits to comparability",
        "",
        "The study uses the official monthly **value-weighted** returns for ten industries. At each June-end, the official construction groups stocks using SIC industry codes available at that time and calculates returns for the following year. These are research stock portfolios, rather than SPDR ETFs or simulated pre-inception histories of those ETFs. [Official construction](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_10_ind_port.html)",
        "",
        "Stocks are value-weighted within each industry. This study separately constructs EW10 across the ten industries, assigning 10% to each industry every month; the momentum portfolio assigns 1/3 to each of the top three industries. **EW10 is not the source file's 'Average Equal Weighted Returns' table, which equal-weights stocks within industries.** The parser reads only the first monthly value-weighted return table and rejects the missing-value sentinels -99.99/-999.",
        "",
        "French reconstructs and revises historical returns. Download vintages from 2025 onward use CRSP CIZ: monthly returns compound daily returns, with dividends reinvested on ex-dividend dates. This differs from the earlier FIZ format. The study retains the original ZIP, documentation, hashes and data vintage; it does not claim to preserve a complete point-in-time history. [Official data notes](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)",
        "",
        "## Unchanged strategy rules",
        "",
        "Targets for holding month t are formed at the end of month t-1. The signal compounds the 11 months from t-12 through t-2, skipping the most recent month, t-1. Industry names break ranking ties; each of the top three industries receives 1/3. The benchmark equal-weights the same ten industries monthly. The strategy is long-only, with no cash timing and no optimization of lookback, thresholds, number of selected industries or sample periods.",
        "",
        "Monthly data permit only theoretical month-end execution; they cannot reproduce the original ETF ledger's next-session close execution. Weights drift with returns within each month and are then rebalanced monthly. Purchases and sales of the industry baskets each incur 5bp per side, with costs satisfying the self-financing equation C=c×sum(abs(w×(V−C)−x)). This uniform cost is a research assumption, rather than an estimate of actual 1960s stock-basket trading costs. Underlying stock-rebalancing costs, fund expenses and market impact are not measured.",
        "",
        "The portfolio is formed from cash in January 1960, with formation costs included in the first month's return. The ledger runs continuously through 2025; the account is not reset and formation costs are not charged again at 2000 or other subperiod boundaries. No liquidation fee is charged at the end.",
        "",
        "## Baseline return results",
        "",
        "Active return below is the mean net monthly MOM−EW10 return multiplied by 12. Interval endpoints are annualized arithmetic-return percentage points. CAGR is reported separately and is not interchangeable with this measure. The HAC12 mean tests for the three baseline samples also receive a three-test Holm adjustment.",
        "",
        "| Sample | MOM CAGR | EW10 CAGR | Annualized mean active return | 6-month block 95% interval | 12-month block 95% interval | Raw HAC12 p | Holm3 p |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in basic["primary_periods"]:
        lines.append(f"| {r['period']} | {pct(r['mom_cagr'])} | {pct(r['ew10_cagr'])} | {pct(r['annualized_arithmetic_active'])} | {ci(r['bootstrap']['6']['ci95_annualized_arithmetic'])} | {ci(r['bootstrap']['12']['ci95_annualized_arithmetic'])} | {r['mean_hac12_asymptotic_normal_p']:.4f} | {r['mean_hac12_holm3_p']:.4f} |")
    lines += [
        "",
        "Both block intervals are positive for the full 1960–2025 sample, but this favorable pooled result should not be selected in isolation. Each of the two prespecified subperiods has an interval crossing zero, and the pooled mean's Holm3 p is not below 0.05. The sample supports the possibility of positive long-run industry-momentum returns; it does not establish a result that can be adopted directly for any industry ETF.",
        "",
        "The 1960–1999 period is a transfer check outside the ETF product history, rather than a genuinely unseen prospective sample. The 2000–2025 period uses research portfolios from the same era but a different classification. Investment instruments, industry definitions, constituent stocks, execution timing and stock weights all change; differences cannot be attributed solely to the number of industries.",
        "",
        "## Four frozen ex-ante conditions",
        "",
        "H1: through the signal month, the market's cumulative past-24-month return is <0 and its recent three-month return is >0; market total return is French Mkt−RF with RF added back. H2: the Spearman correlation between industry recent-three-month returns and the MOM12−1 signal is ≥0. H3: the sample standard deviation of industry MOM signals exceeds the fixed calibration-period median. H4: H3 holds, and the intersection of the current and two preceding top-three sets contains at least two industries. All conditions use only information available before trading.",
        "",
        f"For 1960–1999, the H3/H4 threshold is {pct(conditions['calibration']['early']['signal_std_median'])}, calibrated on 120 decisions from 1950–1959. For 2000–2025, it is {pct(conditions['calibration']['late']['signal_std_median'])}, calibrated on 480 decisions from 1960–1999. These are cross-sectional standard deviations of the 11-month cumulative signal, rather than monthly return volatility. Thresholds were not selected using conditional returns.",
        "",
        "The primary test is the difference between group means, using a Bartlett HAC kernel with a fixed 12-month lag, the n/(n−2) correction and two-sided asymptotic-normal p-values. The expected-favorable-group mean uses a no-intercept regression of y×I on I over the complete monthly calendar, with the n/(n−1) correction; this avoids incorrectly treating selected, compressed months as consecutive observations. Each sample family has a fixed eight-test Holm adjustment: four condition contrasts and four tests of expected-favorable-group means against zero. H1's favorable group is the condition-false group; for the other hypotheses it is the condition-true group.",
        "",
        "The 6/12-month circular blocks jointly resample labels and outcomes, using 20,000 draws each and seed=20261004. Conditional means below are the selected months' average active returns multiplied by 12. They do not imply that a condition persists for a full year or that future returns will equal the table values.",
    ]
    for sample in ("1960-01 to 1999-12", "2000-01 to 2025-12", "2000-01 to 2012-12", "2013-01 to 2025-12"):
        lines += ["", f"### {sample}", "",
                  "| Hypothesis | True months/episodes | False months/episodes | True mean active return | False mean active return | True−false | Contrast Holm8 p | 6-month block contrast interval | 12-month block contrast interval | Favorable-group Holm8 p |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in conditions["primary_and_halves"]:
            if r["sample"] != sample:
                continue
            lines.append(f"| {r['hypothesis']} | {r['true_months']}/{r['true_contiguous_episodes']} | {r['false_months']}/{r['false_contiguous_episodes']} | {pct(r['true_mean_active_ann'])} | {pct(r['false_mean_active_ann'])} | {pct(r['difference_true_minus_false_ann'])} | {r['difference_holm8_p']:.4f} | {ci(r['bootstrap']['6']['difference_true_minus_false_ci95_ann'])} | {ci(r['bootstrap']['12']['difference_true_minus_false_ci95_ann'])} | {r['expected_favorable_mean_holm8_p']:.4f} |")
    lines += [
        "",
        "### Evidence worth retaining",
        "",
        "H1-true months underperformed markedly in 1960–1999, regardless of whether 6-month or 12-month blocks are used; the contrast's Holm8 p≈0.0043. However, there are only 15 such months, all in 1970–1976. The five contiguous state episodes cannot be treated as five independent crises, and the condition falls short of this study's reporting threshold of at least 24 months. The favorable complement's mean has Holm8 p≈0.0893, so positive returns were not simultaneously confirmed. In 2000–2025, the H1 contrast intervals cross zero, and the contrast changes direction between the two halves. This early observation therefore cannot be generalized into a stable ex-ante switch.",
        "",
        "H2 agreement between recent and intermediate-term rankings did not deliver better returns; the contemporary ten-industry condition contrast is negative. This counterexample distinguishes apparent agreement in rankings from evidence that past winners will continue to win. Reversing H2 after seeing the results and recommending ranking disagreement would not be justified.",
        "",
        "H3 greater opportunity has a positive contrast in both broad external samples, but intervals are wide and the Holm-adjusted tests are not significant. Adding past-leader stability in H4 did not establish an improvement. Neither past dispersion nor past stability automatically resolves the question of future persistence.",
        "",
        "Leave-one-year-out results are stored in leave_one_year_out.csv. Frozen labels and thresholds are not recomputed; these results describe conditional-mean directions only, without calculating HAC across gaps left by deleted years. Excluding 2022 from 2000–2025 gives H1/H2/H3/H4 contrasts of −2.00, −7.25, +0.93 and +0.41 percentage points per year, respectively. This does not turn any unconfirmed hypothesis into a confirmed result.",
        "",
        "The supplementary market regression is fixed as active=const+Z+M+Z×M and reports the two states' intercepts and beta difference. The contemporaneous market is used only to describe exposure, rather than as a tradable future input. The beta difference and conditional-mean difference are distinct quantities; an intercept change is not causal evidence. Complete results are stored in conditional_results.json.",
        "",
        "## Reproduction and checks",
        "",
        "analyze_external.py reads the source monthly value-weighted industry table and constructs the fixed signal and self-financing ledger. analyze_conditions.py applies inference to the frozen conditions. write_summary.py generates this memo from JSON.",
        "",
        "Checks cover complete monthly coverage without gaps; rejection of missing-value sentinels; agreement between each holding month's 11-month signal and direct compounding; invariance of the current signal to changes in the skipped recent month or future returns; agreement between EW10 weight drift and independent calculation; agreement with the analytical solution for initial formation costs; reconciliation of monthly NAV changes to industry P&L less costs; and equality of monthly costs to gross purchases plus sales multiplied by the per-side rate. Source and generated-file hashes are in provenance.json.",
        "",
        "comparison_returns.csv contains MOM12_1, EW10 and net active monthly returns from the continuous 1960–2025 ledger, allowing paired comparisons with ETF returns for the same months. Such comparisons describe transfer differences; they cannot isolate the effect of industry definitions or industry count.",
    ]
    (ROOT / "external_validation.md").write_text("\n".join(lines) + "\n")
    manifest = json.loads((ROOT / "provenance.json").read_text())
    manifest["sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.iterdir()
                          if p.name != "provenance.json" and p.suffix in (".zip", ".csv", ".html", ".py", ".json", ".md")}
    (ROOT / "provenance.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

if __name__=='__main__':
    main()
