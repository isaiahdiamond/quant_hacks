# Wall Street's Payroll

Pension funds and other big institutions have to trade at the end of every month to make payments and rebalance. That pushes prices around in a predictable way. This strategy trades against it using S&P 500 and Treasury futures.

Built for Gator Quant Hacks 2026. The full idea and rules are in [HYPOTHESIS.md](HYPOTHESIS.md).

## Run it

You need a Databento API key.

```bash
pip install -r requirements.txt
cp .env.example .env        # add your Databento key
python download.py
```

Then open `analysis.ipynb` for the in-sample results. `python oos.py` runs the out-of-sample test (only once).
