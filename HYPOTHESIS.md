# Hypothesis: Wall Street's Payroll

Big institutions have to trade at the end of every month on a fixed schedule, whatever the price. Two forces drive this.

Cash needs. Pension funds, insurers and mutual funds make payments around the turn of the month. They sell stocks in the days before month-end to raise cash and reinvest at the start of the new month.

> Etula, Rinne, Suominen & Vaittinen. Dash for Cash. Review of Financial Studies, 2020.

Rebalancing. Funds with a fixed stock/bond mix, like 60/40, sell whatever went up during the month and buy whatever went down. The authors estimate this costs them about $16 billion a year.

> Harvey, Mazzoleni & Melone. The Unintended Consequences of Rebalancing. NBER Working Paper 33554, 2025.

These trades push prices away from fair value for a few days, then prices revert. We take the other side.

Who's on the other side: institutions trading on a calendar for payments and rebalancing. Why it persists: their trading is set by obligations and policy, not by short-term prices.

What's new: each paper studies one force. In some months the two forces push stocks the same way, in others they conflict. We only trade stocks when they agree. We also test whether each effect survived after its paper was published, since both papers' data ends before our out-of-sample period.

## Data

E-mini S&P 500 (ES) and 10-year Treasury note (ZN) futures from Databento (CME Globex), June 2010 to October 2026. Russell 2000 (RTY) futures for one robustness check.

Front-month contracts. Databento prices are not adjusted for rolls, so returns are never computed across a roll.

Daily prices built from hourly bars: the decision price is 4 pm New York time, the trade price is 10 am the next day.

## Rules

Let T be the last trading day of the month.

Signal. At 4 pm on T-4, take this month's ES return minus this month's ZN return, measured from the last close of the previous month. Positive means stocks beat bonds, so rebalancers will sell stocks and buy bonds. Negative means bonds beat stocks, so rebalancers will buy stocks and sell bonds.

Month-end, 10 am T-3 to 10 am T+1. Long ZN if the signal is positive, short ZN if negative. Long ES if the signal is negative, because rebalancing buying and the end of cash-needs selling point the same way. Flat ES if the signal is positive, because the two forces conflict.

New month, 10 am T+1 to 10 am T+4. Long ES. Payments are done and cash is reinvested.

All other days: no position.

Sizing. Each position is scaled so the instrument runs at 10% annual volatility, using the previous 60 days of daily returns. Leverage per instrument is capped at 3x.

Costs. 1 bp per side for ES and 2 bp per side for ZN, roughly one tick plus commission at current contract sizes. Every result is also shown at double costs.

## Variants

These are all the versions we will test.

1. Primary: the rules above.
2. Cash needs only: long ES from 10 am T-3 to 10 am T+4. No bonds.
3. Rebalancing only: month-end window only. Short ES and long ZN when the signal is positive, the reverse when negative.
4. No gate: positions from 2 and 3 added together.

The primary was chosen before seeing any results. Before this hypothesis we tested and dropped Kalman-filter pairs trading on AI stocks and on crypto. Those count toward our total number of trials.

## Predictions

1. The primary has a positive Sharpe after costs in-sample.
2. The primary beats both single-force versions (2 and 3).
3. Months where the forces agree earn more than months where they conflict.
4. Quarter-ends show a bigger effect than other month-ends.
5. RTY shows at least as large an effect as ES, since it's a thinner market.
6. The strategy beats random holding windows of the same length in at least 95% of 1,000 simulations.
7. Moving each window one day earlier or later still works. If only the exact days work, we got lucky.

## Out-of-sample

The holdout is the most recent 20% of the data or 2 years, whichever is shorter: October 2024 to October 2026. It is run once, after everything above is fixed, and reported whatever the result. It contains only about 24 month-ends, so we report it with confidence intervals and expect them to be wide.

We reject the hypothesis if the primary's in-sample Sharpe is zero or negative, if it doesn't beat random holding windows, or if the edge disappears at double costs.
