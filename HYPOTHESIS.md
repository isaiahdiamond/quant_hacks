# Hypothesis: Wall Street's Payroll

Big institutions have to trade at the end of every month on a fixed schedule, whatever the price. Two things drive this.

The first is cash needs. Pension funds, insurers and mutual funds make payments around the turn of the month, so they sell stocks in the days before month-end to raise cash and reinvest once the new month starts.

> Etula, Rinne, Suominen & Vaittinen. Dash for Cash. Review of Financial Studies, 2020.

The second is rebalancing. Funds that hold a fixed mix of stocks and bonds, like 60/40, sell whatever went up during the month and buy whatever went down. The authors put the cost of this to those funds at about $16 billion a year.

> Harvey, Mazzoleni & Melone. The Unintended Consequences of Rebalancing. NBER Working Paper 33554, 2025.

Both kinds of trading push prices away from fair value for a few days, and then prices come back. We take the other side.

The other side is an institution trading on a calendar, for payments and for policy, not on price. That is also why we expect the effect to last: the trades are set by obligations, not by what looks cheap this week.

Each of the two papers studies one force on its own. In some months the forces push stocks the same way and in others they work against each other, so we only trade stocks when they agree. We also test whether each effect survived its own publication, since both papers' data ends before our out-of-sample period.

## Data

E-mini S&P 500 (ES) and 10-year Treasury note (ZN) futures from Databento, CME Globex, June 2010 to October 2026. We also pull Russell 2000 (RTY) futures for one robustness check.

We use front-month contracts. Databento does not adjust prices for rolls, so we never compute a return across one.

Daily prices come from hourly bars. The decision price is 4 pm New York time and the trade price is 10 am the next day.

## Rules

Let T be the last trading day of the month.

Signal. At 4 pm on T-4 we take this month's ES return minus this month's ZN return, both measured from the previous month's last close. A positive number means stocks beat bonds, so rebalancers will sell stocks and buy bonds. A negative number means the reverse.

Month-end, 10 am T-3 to 10 am T+1. We go long ZN if the signal is positive and short ZN if it is negative. We go long ES only if the signal is negative, because that is when rebalancing buying and the end of cash-needs selling point the same way. If the signal is positive the two forces conflict, so we stay flat ES.

New month, 10 am T+1 to 10 am T+4. Long ES. Payments are done and the cash is being reinvested.

All other days: no position.

Sizing. We scale each position so the instrument runs at 10% annual volatility, using the previous 60 days of daily returns. Leverage is capped at 3x per instrument.

Costs. 1 bp per side for ES and 2 bp per side for ZN, which is roughly one tick plus commission at current contract sizes. Every result is also shown at double these costs.

## Variants

These are all the versions we will test.

1. Primary. The rules above.
2. Cash needs only. Long ES from 10 am T-3 to 10 am T+4, no bonds.
3. Rebalancing only. The month-end window alone: short ES and long ZN when the signal is positive, the reverse when it is negative.
4. No gate. The cash needs and rebalancing positions added together.

We chose the primary before seeing any results. Before this hypothesis we tested and dropped Kalman-filter pairs trading on AI stocks and on crypto, and those count toward our total number of trials.

## Predictions

1. The primary has a positive Sharpe after costs in-sample.
2. The primary beats the cash-needs-only and rebalancing-only versions.
3. Months where the forces agree earn more than months where they conflict.
4. Quarter-ends show a bigger effect than other month-ends.
5. RTY shows at least as large an effect as ES, since it is a thinner market.
6. The strategy beats random holding windows of the same length in at least 95% of 1,000 simulations.
7. Moving each window a day earlier or later still works. If only the exact days work, we got lucky.

## Out-of-sample

The holdout is the most recent 20% of the data, or 2 years, whichever is shorter. That gives us October 2024 to October 2026. We run it once, after everything above is fixed, and we report it whatever it says. It holds only about 24 month-ends, so we report confidence intervals with it and expect them to be wide.

## When we reject it

We reject the hypothesis if the primary's in-sample Sharpe is zero or negative, if it does not beat random holding windows, or if the edge disappears at double costs.
