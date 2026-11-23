# Delta Air Lines: the margin gain was fuel, not efficiency (Power BI)

Power BI project (PBIP) analysing Delta Air Lines FY2021 to Q3 2026, with United, American and Southwest as peer benchmarks.

**Thesis:** Delta's operating margin rose from 7.2% to 9.2% (FY2022 to FY2025), but fuel explains +7.2 pts while labor and other costs took back 5.3 pts; unit margin fell from 6.68 to 5.70 cents; the lasting gain is the balance sheet (Debt/EBITDA 6.9x to 1.7x). Fuel is already reversing in 2026.

![Margin bridge](docs/margin_bridge.png) ![Fuel vs margin](docs/fuel_vs_margin.png)
![Unit economics](docs/unit_economics.png) ![Balance sheet](docs/balance_sheet.png)

Two-page summary: [docs/Delta_margin_analysis_summary.pdf](docs/Delta_margin_analysis_summary.pdf)

## Open it
1. Power BI Desktop: open `Delta_Airline.pbip` (enable *Power BI Project (.pbip) save option* in Preview features if prompted).
2. Set the data path: Transform data > Manage parameters > `DataFolder` = full path to this repo's `data\` folder with a trailing backslash (the default `C:\Delta_Airline\data\` is a placeholder).
3. Home > Refresh. Then File > Save as `.pbix` if you want a single file to share.

## Pages
1. **The thesis**: margin bridge, fuel vs margin by quarter, unit economics, fuel-shock stress test, balance sheet, peer leverage.
2. **Deep dive**: cost structure, margin vs peers, unit margin gap, leverage and coverage vs peers, load factor, annual table.
3. **Conclusion**: findings, what they mean, what to watch.
4. **Method & limits**: data, definitions, stress-test assumptions.

## Data model
![Data model](docs/data_model.png)

Full column list: [docs/data_dictionary.md](docs/data_dictionary.md)

## Data (`data/`)
SEC EDGAR XBRL company facts (10-K/10-Q); Delta operating statistics (ASM, RPM, TRASM, CASM-Ex) from earnings-release statistical summaries. Quarterly values are derived from year-to-date filings.

## Look and feel
The public repo ships without Delta logos or aircraft photos. To add them, put `delta_logo.png`, `delta_plane.jpg`, `delta_plane2.jpg` and `delta_wallpaper.jpg` in `assets/` (images you have the right to use) and re-run `python scripts/build_project.py`; they are embedded automatically.

## Regenerate
`python scripts/build_project.py` rebuilds the semantic model (TMDL) and report (PBIR) from `data/*.csv`.

## Definitions and limitations
EBITDA = operating income + D&A. Debt = long-term debt + finance leases. Liquidity = cash + short-term investments (excludes undrawn revolver). Coverage = operating income / interest. FCF = CFO - capex. Some interest data are missing for 2021 and quarterly 2021-2023; Delta capex Q2-Q3 2026 is blank in the source. Operating statistics cover Delta only. The stress test assumes no fare or capacity response, so it is an upper bound, not a forecast.


## Disclaimer
Independent analysis based on public filings. Not affiliated with or endorsed by Delta Air Lines. Delta name, logo and aircraft photos belong to their owners; the public repo ships without them.

`python scripts/make_summary.py` rebuilds the charts and the PDF summary in `docs/`.
