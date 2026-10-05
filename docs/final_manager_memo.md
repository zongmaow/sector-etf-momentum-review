# Final manager memo: sector momentum allocation

Review date: 2026-10-05. Hypothetical US equity mandate; historical market data with simulated holdings, close execution and costs.

**Decision: retain the existing SPY policy allocation and do not add the proposed 20% momentum sleeve on the current evidence.** Phase one is complete. This decision concerns a fixed nine-sector MOM12−1 rule, not all active management, all momentum strategies or a personal investment recommendation.

## Evidence for the decision

The primary strategy selects three of the nine original sector ETFs, targets equal weights monthly, observes month-end information and trades at the following session's close. The old portfolio earns execution-day returns. Formation costs are included, subsequent fees use actual buys and sells after drift, and final holdings are not liquidated.

| 2000–2025, 5 bps per side | Net CAGR | Daily maximum drawdown |
|---|---:|---:|
| Monthly EW9 | 8.68% | −53.29% |
| MOM12−1 | 8.32% | −46.20% |
| Buy-and-hold SPY | 8.02% | −55.19% |

Momentum beat SPY on full-period CAGR and had a shallower historical drawdown, but it did not establish net incremental value over the same-universe equal-weight alternative. Its annualized arithmetic mean active return versus EW9 was approximately −0.28 percentage points. The original six-month block interval was [−2.76, +2.05] percentage points (2,000 draws, seed 2026); the follow-up interval was [−2.62, +2.07] (20,000 draws, seed 20261004). Both cross zero. The [original snapshot](../reports/snapshot/analysis.json) and [follow-up protocol](../reports/effectiveness_snapshot/research_protocol_zh.md) retain their distinct settings; these are not CAGR intervals or future profit probabilities.

The 80% SPY / 20% momentum account earned 8.14% CAGR versus 8.17% for the 80% SPY / 20% EW9 account. Its tracking error against SPY was 1.60%, within an illustrative 2% budget. Passing the assumed risk budget does not establish a reason to spend it. EW9 is also a sector-weight and rebalancing choice; its historical win is insufficient grounds to replace the existing policy allocation.

## What the additional research changed

The [effectiveness study](../reports/effectiveness_snapshot/industry_rotation_effectiveness_zh.md) separates realized P&L from advance information. Across complete execution intervals, gross active return equals two-thirds of the selected-minus-omitted sector return spread. The reconciliation is precise, but the spread is only known after holding the portfolio. Average historical ranking IC was 0.00472, with a six-month block interval spanning zero. Removing trading costs did not establish a stable positive mean gross advantage.

Four limited conditions—recovery after a market decline, recent/medium-term ranking agreement, high signal dispersion and dispersion with stable membership—did not establish a reliable enablement rule. Three actual switching strategies, including cross-mode trades and fees, failed to improve original momentum CAGR. Those 2010–2025 comparisons form all portfolios from cash on a common date and are distinct from slices of the account formed in 2000. Multiple-test adjustment and sparse condition counts limit inference.

The [concentrated control](../reports/random_control_snapshot/README.md) compares momentum with fixed industry-identity random remappings that preserve its membership transitions, plus a monthly overlap-matched sensitivity. Every path incurs its own actual trading costs. Its historical distribution is a diagnostic of concentration and selection; differing sector risk exposures prevent treating a percentile as a valid alpha p-value or a future success probability.

At 5 bps, momentum CAGR's historical percentile is 54.81% under identity remapping and 56.18% under monthly overlap matching. Random median CAGRs are 8.15% and 8.14%, versus momentum's 8.32%. Its position remains near the middle at 0 and 10 bps. This provides no pronounced historical return advantage from the selected identities; it does not prove equality or ineffectiveness. Actual median half-gross turnover is approximately 2.7090 and 2.7087 versus momentum's 2.6976, with fees recomputed rather than imposed as equal.

Momentum's −46.20% drawdown is shallower than the random medians of −54.45% and −54.20%. A middle-ranked return is not a middle-ranked risk result, but this historical observation is not a future protection guarantee. Each group contains 4,096 simulated paths through the same market history, not independent market samples. Full metrics, cost scenarios and limitations are retained in the [result manifest](../reports/random_control_snapshot/summary.json).

French ten-industry research portfolios provide positive long-history evidence in a different universe, while the modern environment checks remain unconfirmed. SIC classification, underlying value weights, theoretical monthly formation and historical implementation differ from the ETF strategy. This evidence prevents the broad claim that industry momentum never works; it does not approve the proposed ETF sleeve.

## Reconsideration and research discipline

- Keep the present rules frozen and record information available at each decision, intended execution, estimated costs and subsequent observations. Only genuinely new data become prospective evidence.
- Seek independent-market or independently sourced replication with explicit classification and tradability limits; disclose failures and all tested conditions.
- Before inspecting new results, specify compensation for implementation burden, plausible costs and mandate risk constraints. Evaluate net value, adverse relative paths and concentrated exposures together; do not let one p-value or a retrospectively chosen cutoff decide adoption.
- Study economic persistence only after obtaining point-in-time earnings expectations, valuations or shock information and writing a new protocol. Repeatedly selecting thresholds from the same price history is not further validation.

Known limits include revised vendor adjustments, next-close fill proxies, flat fee scenarios, changing sector definitions, retrospective holdouts, and no institutional capacity, historical spread, tax or complete multifactor attribution model.***REMOVED***

Read the [final review in Chinese](final_review_zh.md) for the evidence map and conclusion boundaries. The unchanged [original generated memo](../reports/snapshot/manager_memo.md) remains part of the original snapshot provenance.
