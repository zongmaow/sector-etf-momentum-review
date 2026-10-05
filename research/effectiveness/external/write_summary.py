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
        "# 十行业历史组合的外部验证",
        "",
        "研究日期：2026-10-04。数据来自Kenneth French官方的202608 CRSP版本，研究回报严格截断到2025年12月。",
        "",
        "本次验证未找到一个能够跨时期、跨行业池稳定确认的事前有效环境。十行业组合的长期净主动收益平均为正，但早期和同期区间单独估计仍有明显不确定性。尤其不能将同一种名字的‘行业动量’，当成在任何行业分类和投资工具上都具有相同收益的策略。",
        "",
        "## 数据与可比边界",
        "",
        "使用官方10行业**价值加权**月度回报。官方每年6月末按当时可得的SIC行业代码分组，并计算随后一年回报；这是研究股票组合，不是SPDR ETF，也不是ETF成立之前的模拟前身。[官方构造说明](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_10_ind_port.html)",
        "",
        "股票在每个行业内按价值加权。本研究另外在10个行业之间构建EW10：每月行业各占10%；动量组合每月前三行业各占1/3。**EW10并不是原始文件中‘Average Equal Weighted Returns’那张股票等权行业回报表。** 解析脚本只读第一张月度价值加权回报表，并拒绝缺失值标记−99.99/−999。",
        "",
        "French会重新构造并修订历史回报。2025年起的下载版本基于CRSP CIZ，月度回报由每日回报复合、分红于除息日再投资；它与早期FIZ的数据版本存在口径差别。本次保存原始ZIP、说明、哈希和数据版本，没有宣称其为逐时点完整保存的数据。[官方数据说明](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)",
        "",
        "## 不改变的策略规则",
        "",
        "持有月t在t−1月末形成目标，信号为t−12至t−2的11个月累计回报，跳过最近的t−1月。排序并列时按行业名字排序，前三行业各占1/3。基准同池10行业每月等权。只做多，无现金择时，不优化回看期、阈值、选行业数量或样本区间。",
        "",
        "月度数据只能进行月末理论成交，不能复刻原ETF账本的次交易日收盘执行。实际月内权重随收益漂移，再按月调整；外层买卖均计单边5bp，费用满足C=c×sum(abs(w×(V−C)−x))的自融资方程。该统一成本只是研究假设，无法代表1960年代股票篮子的真实交易成本，且未测量底层股票调整成本、基金费用和冲击成本。",
        "",
        "1960年1月从现金建仓，首笔成本进入首月回报；完整账本连续运行到2025年，2000年及其他子区间不重置账户、不重复收建仓费，结束时不收清仓费。",
        "",
        "## 基本收益结果",
        "",
        "下表主动收益是净月度MOM−EW10均值×12，区间单位为年化算术收益百分点；CAGR另列，不能将两者互换。三个基础样本的HAC12均值检验额外做Holm三检验校正。",
        "",
        "| 样本 | MOM CAGR | EW10 CAGR | 年化主动均值 | 6月区块95%区间 | 12月区块95%区间 | HAC12原始p | Holm3 p |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in basic["primary_periods"]:
        lines.append(f"| {r['period']} | {pct(r['mom_cagr'])} | {pct(r['ew10_cagr'])} | {pct(r['annualized_arithmetic_active'])} | {ci(r['bootstrap']['6']['ci95_annualized_arithmetic'])} | {ci(r['bootstrap']['12']['ci95_annualized_arithmetic'])} | {r['mean_hac12_asymptotic_normal_p']:.4f} | {r['mean_hac12_holm3_p']:.4f} |")
    lines += [
        "",
        "全1960–2025样本的两种区块区间为正，但不能只选择这个最有利的合并口径：两个事先明确的分区间均有跨零区间，合并均值的Holm3 p也没有低于0.05。这提供‘长期行业动量可能有正收益’的样本支持，而不是在任意行业ETF上可直接采用的确定结论。",
        "",
        "1960–1999是位于ETF产品历史之外的迁移检查，并非无人观察过的真正前瞻样本；2000–2025则是同一时代的不同分类研究组合。投资工具、行业定义、构成股票、交易时点和股票权重均改变，无法把差异只归因于行业数量。",
        "",
        "## 四个冻结的事前条件",
        "",
        "H1：截至信号月，市场过去24个月累计回报<0、最近3个月>0；市场用French Mkt−RF加回RF的总回报。H2：行业最近3个月回报与MOM12−1信号的Spearman相关≥0。H3：行业MOM信号的样本标准差高于固定校准期中位数。H4：H3成立，且本次和前两次前三行业集合的交集至少有两个。全部仅使用交易前信息。",
        "",
        f"1960–1999的H3/H4阈值由1950–1959的120个决策确定，为{pct(conditions['calibration']['early']['signal_std_median'])}；2000–2025阈值由1960–1999的480个决策确定，为{pct(conditions['calibration']['late']['signal_std_median'])}。这是11个月累计信号的横截面标准差，不是月度回报波动率。阈值未用条件收益挑选。",
        "",
        "主检验是两组均值差，HAC Bartlett核固定滞后12月、n/(n−2)修正，渐近正态双侧p；预期有利组均值用完整月历上的y×I对I无截距回归、n/(n−1)修正，避免压缩入选月份后错误地当作连续月份。每个样本族固定8项Holm校正：四个条件差异和四个预期有利组均值对0检验。H1有利组是条件不成立；其余为条件成立。",
        "",
        "6/12月循环区块联合抽样标签和结果，均为20,000次、seed=20261004。以下条件均值是特定月份的平均主动收益×12，并不表示这些条件一定持续整年，或未来会赚取表中数值。",
    ]
    for sample in ("1960-01 to 1999-12", "2000-01 to 2025-12", "2000-01 to 2012-12", "2013-01 to 2025-12"):
        lines += ["", f"### {sample}", "",
                  "| 假说 | 成立月数/连续段 | 不成立月数/连续段 | 成立主动均值 | 不成立主动均值 | 成立−不成立 | 差异Holm8 p | 6月区块差异区间 | 12月区块差异区间 | 有利组Holm8 p |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in conditions["primary_and_halves"]:
            if r["sample"] != sample:
                continue
            lines.append(f"| {r['hypothesis']} | {r['true_months']}/{r['true_contiguous_episodes']} | {r['false_months']}/{r['false_contiguous_episodes']} | {pct(r['true_mean_active_ann'])} | {pct(r['false_mean_active_ann'])} | {pct(r['difference_true_minus_false_ann'])} | {r['difference_holm8_p']:.4f} | {ci(r['bootstrap']['6']['difference_true_minus_false_ci95_ann'])} | {ci(r['bootstrap']['12']['difference_true_minus_false_ci95_ann'])} | {r['expected_favorable_mean_holm8_p']:.4f} |")
    lines += [
        "",
        "### 什么证据最值得保留",
        "",
        "1960–1999的H1成立月份明显落后，不依赖选用6月或12月区块长度，差异Holm8 p≈0.0043。但这只有15个月，全部位于1970–1976年，虽然计数为5个连续状态段，不能视作5场独立危机；也未满足至少24个月的本轮报告门槛。有利补集均值Holm8 p≈0.0893，没有同时确认正收益。2000–2025 H1差异区间跨零，前后两个半样本的差异方向还反转，因此不能把这个早期事实推广为稳定的事前开关。",
        "",
        "H2近期与中期排名一致，并未带来更好收益；同期10行业的条件差异反而是负数。这个反例说明，‘排名看起来一致’和‘旧赢家将在未来继续赢’是不同信息。不能事后反转H2方向、把排名不一致改成推荐规则。",
        "",
        "H3机会较大在两个外部大样本的差异都为正，但区间宽、Holm不显著；H4加入过去领先者稳定没有带来确定的提升。过去的分化和过去的稳定都没有自动解决未来延续的问题。",
        "",
        "逐年剔除结果保存在leave_one_year_out.csv，固定标签和阈值不重算，仅描述条件均值方向，不在删除后跨年空档上计算HAC。2000–2025剔除2022后，H1/H2/H3/H4的差异分别为−2.00、−7.25、+0.93、+0.41个百分点/年；这不会把任何未确认假说变成已确认结论。",
        "",
        "市场辅助回归固定为active=const+Z+M+Z×M，同时给出两种状态的截距与β差；同期市场仅用于描述暴露，不是可交易的未来输入。β差与条件均值差不是同一量，截距变化也不构成因果证明。完整数值保存于conditional_results.json。",
        "",
        "## 复算与检查",
        "",
        "analyze_external.py读取原始月度价值加权行业表、构造固定信号和自融资账本；analyze_conditions.py按冻结条件推断；write_summary.py从JSON生成本文。",
        "",
        "检查包括：完整月份无缺口、缺失标记拒绝、每个持有月11个月信号与直接复合结果一致、最近被跳过月份/未来回报改变不影响当前信号、EW10的权重漂移与独立计算一致、首笔建仓费用解析解一致、每月净值变化与行业盈亏减费用一致、每月费用等于买卖总额×单边成本。原始和生成文件哈希见provenance.json。",
        "",
        "comparison_returns.csv是1960–2025连续账本的MOM12_1、EW10和净active月回报，可用于与ETF同月配对比较；该比较是迁移差异描述，不能隔离行业定义或行业数量的单一影响。",
    ]
    (ROOT / "external_validation_zh.md").write_text("\n".join(lines) + "\n")
    manifest = json.loads((ROOT / "provenance.json").read_text())
    manifest["sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.iterdir()
                          if p.name != "provenance.json" and p.suffix in (".zip", ".csv", ".html", ".py", ".json", ".md")}
    (ROOT / "provenance.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

if __name__=='__main__':
    main()
