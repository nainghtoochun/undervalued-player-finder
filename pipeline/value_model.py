"""Predict a fair market value from performance, age, position and league.

TODO week 3
- Target: log(market value at VALUATION_DATE).
- Features: xT p90, npxG p90, xA p90, minutes, age, age squared, position group, league.
- Model: start with ridge regression, then try gradient boosting. Use cross validation.
- value_gap_pct = (predicted - actual) / actual. Large positive gap = possible bargain.
- Backtest: did the top 50 "bargains" gain more value by BACKTEST_DATE than similar players?
"""
