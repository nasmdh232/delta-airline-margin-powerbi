"""Builds docs/*.png charts and docs/Delta_margin_analysis_summary.pdf (2 pages) from data/*.csv."""
import os, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
D = lambda n: os.path.join(ROOT, 'data', n)
OUT = os.path.join(ROOT, 'docs'); os.makedirs(OUT, exist_ok=True)
RED, NAVY, GOLD, GRAY, BLUE = '#C8102E', '#0B2545', '#E0A100', '#7A8699', '#3A7CC1'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#999', 'axes.titleweight': 'bold', 'axes.titlesize': 10, 'axes.titlelocation': 'left'})

q = pd.read_csv(D('v_quarterly.csv')); q = q[q.airline_id == 'DAL'].sort_values('period_end')
a = pd.read_csv(D('v_annual.csv')); a = a[a.airline_id == 'DAL'].sort_values('fiscal_year')
o = pd.read_csv(D('operating_metrics.csv')); o = o[o.airline_id == 'DAL'].sort_values('fiscal_year')
b = pd.read_csv(D('margin_bridge.csv'))
x = range(len(q)); xt = [i for i, l in enumerate(q.label) if l.startswith('Q1')]; xl = ['20' + q.label.iloc[i][-2:] for i in xt]

def save(fig, name): fig.savefig(os.path.join(OUT, name), dpi=200, bbox_inches='tight'); plt.close(fig)

# 1 margin bridge
fig, ax = plt.subplots(figsize=(4.6, 2.7))
labs = ['Fuel share\nof revenue', 'Labor share\nof revenue', 'Other costs\nincl. D&A']
vals = list(b.sort_values('order').pts)
bars = ax.bar(labs, vals, color=[GOLD if v > 0 else RED for v in vals], width=0.55)
for r, v in zip(bars, vals): ax.text(r.get_x() + r.get_width() / 2, v + (0.25 if v > 0 else -0.25), f'{v:+.1f} pts', ha='center', va='bottom' if v > 0 else 'top', fontweight='bold')
ax.axhline(0, color='#555', lw=0.8); ax.set_ylim(-5.5, 8.8); ax.set_ylabel('pts of revenue')
ax.set_title('Why margin moved +2.0 pts (FY22 to FY25)'); save(fig, 'margin_bridge.png')

# 2 fuel vs margin quarterly
fig, ax = plt.subplots(figsize=(4.6, 2.7))
ax.plot(x, q.fuel_pct_rev * 100, color=GOLD, lw=2, label='Fuel % of revenue'); ax.plot(x, q.operating_margin * 100, color=RED, lw=2, label='Operating margin')
ax.set_xticks(xt); ax.set_xticklabels(xl); ax.set_ylim(-40, 30); ax.axhline(0, color='#555', lw=0.6); ax.set_ylabel('%'); ax.legend(frameon=False, loc='lower right', fontsize=8)
ax.set_title('Fuel drives the margin, quarter by quarter'); save(fig, 'fuel_vs_margin.png')

# 3 unit economics
o2 = o.dropna(subset=['trasm_adjusted_cents'])
fig, ax = plt.subplots(figsize=(4.6, 2.7))
ax.plot(o2.fiscal_year, o2.trasm_adjusted_cents, color=RED, lw=2, marker='o', label='Adj. TRASM'); ax.plot(o.fiscal_year, o.casm_ex_cents, color=BLUE, lw=2, marker='o', label='CASM-Ex')
for _, r in o2.iterrows(): ax.text(r.fiscal_year, r.trasm_adjusted_cents + 0.35, f'{r.trasm_adjusted_cents:.2f}', ha='center', fontsize=7.5)
for _, r in o.iterrows(): ax.text(r.fiscal_year, r.casm_ex_cents - 0.9, f'{r.casm_ex_cents:.2f}', ha='center', fontsize=7.5)
ax.set_xticks(list(o.fiscal_year)); ax.set_ylim(10, 22); ax.set_ylabel('cents per ASM'); ax.legend(frameon=False, loc='center right', fontsize=8)
ax.set_title('Unit revenue flat, unit cost up'); save(fig, 'unit_economics.png')

# 4 balance sheet
fig, ax = plt.subplots(figsize=(4.6, 2.7))
bb = ax.bar(a.fiscal_year.astype(str), a.total_debt / 1e9, color=NAVY, width=0.55)
for r, d in zip(bb, a.debt_to_ebitda): ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.4, f'{d:.1f}x', ha='center', fontweight='bold')
ax.set_ylabel('Total debt, $B'); ax.set_ylim(0, 32); ax.set_title('Debt roughly halved (label = Debt / EBITDA)'); save(fig, 'balance_sheet.png')

# ---------- PDF ----------
S = lambda n, **k: ParagraphStyle(n, fontName=k.pop('fontName', 'Helvetica'), **k)
H1 = S('h1', fontName='Helvetica-Bold', fontSize=19, leading=22, textColor=colors.HexColor(NAVY))
SUB = S('sub', fontSize=9.5, leading=12.5, textColor=colors.HexColor('#444'))
H2 = S('h2', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor(RED), spaceBefore=6, spaceAfter=2)
BODY = S('b', fontSize=9.2, leading=12.4, textColor=colors.HexColor('#222'))
SMALL = S('s', fontSize=7.8, leading=10, textColor=colors.HexColor('#555'))
KV = S('kv', fontName='Helvetica-Bold', fontSize=16, leading=18, alignment=1, textColor=colors.HexColor(NAVY))
KC = S('kc', fontSize=7.2, leading=9, alignment=1, textColor=colors.HexColor('#555'))

def img(n, w=3.55 * inch):
    from PIL import Image as PI
    iw, ih = PI.open(os.path.join(OUT, n)).size; return Image(os.path.join(OUT, n), width=w, height=w * ih / iw)

def kpis(items):
    t = Table([[Paragraph(v, KV) for v, _ in items], [Paragraph(c, KC) for _, c in items]], colWidths=[1.75 * inch] * len(items))
    t.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#CCC')), ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#DDD')), ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F6F8FB')), ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
    return t

def pair(a_, b_):
    t = Table([[img(a_), img(b_)]], colWidths=[3.65 * inch, 3.65 * inch]); t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)])); return t

GH = os.environ.get('GITHUB_URL', '')
doc = SimpleDocTemplate(os.path.join(OUT, 'Delta_margin_analysis_summary.pdf'), pagesize=letter, leftMargin=0.6 * inch, rightMargin=0.6 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                        title="Delta's margin gain was fuel, not efficiency", author='Nathan Dao (Gia Nam Dao)')
st = []
st += [Paragraph("Delta's margin gain was fuel, not efficiency", H1), Spacer(1, 3),
       Paragraph('A Power BI analysis of Delta Air Lines, FY2021 to Q3 2026, with United, American and Southwest as peer benchmarks. Source: SEC EDGAR filings and Delta earnings releases.', SUB), Spacer(1, 8),
       kpis([('7.2% to 9.2%', 'Operating margin, FY22 to FY25'), ('+7.2 pts', 'From lower fuel share of revenue'), ('6.68 to 5.70 cents', 'Unit margin gap (adj. TRASM - CASM-Ex)'), ('6.9x to 1.7x', 'Debt / EBITDA, FY21 to FY25')]), Spacer(1, 8),
       pair('margin_bridge.png', 'fuel_vs_margin.png'),
       Paragraph('The finding', H2),
       Paragraph('Delta\'s operating margin rose 2.0 points (7.2% to 9.2%) between FY2022 and FY2025. Fuel fell from 22.7% to 15.5% of revenue, which alone is worth +7.2 points. Labor (-4.1 pts) and other costs (-1.1 pts) gave back 5.3 points. Adjusted unit revenue was flat (19.55 to 19.56 cents) while unit cost excluding fuel rose (12.87 to 13.86 cents), so the unit margin gap narrowed. The profit improvement came mostly from a cost Delta does not control.', BODY),
       Paragraph('Why it matters now', H2),
       Paragraph('Fuel is already reversing: it reached 20.8% and 21.6% of revenue in Q2 and Q3 2026, against 15.5% in FY2025. A simple stress test (FY2025 margin minus fuel share times the price shock, no fare or capacity response) puts the cost of each +10% in fuel price at about 1.5 points of operating margin. It is an upper bound, not a forecast.', BODY),
       PageBreak()]
st += [Paragraph('Evidence: unit economics and balance sheet', H2), pair('unit_economics.png', 'balance_sheet.png'),
       Paragraph('What the data says', H2),
       Paragraph('<b>1. Margin.</b> +2.0 pts overall: fuel +7.2, labor -4.1, other -1.1.<br/><b>2. Unit economics got worse, not better.</b> The unit margin gap fell from 6.68 to 5.70 cents (peak 6.93 in 2023).<br/><b>3. The lasting gain is the balance sheet.</b> Total debt fell from $26.9B to $14.1B, Debt / EBITDA from 6.9x to 1.7x, and interest coverage reached 8.6x in FY2025. Liquidity is $4.3B at FY2025 year-end (excluding the undrawn revolver), below $11.3B in FY2021.', BODY),
       Paragraph('What to watch next', H2),
       Paragraph('Q4 2026 fuel share of revenue and whether operating margin falls back toward the FY2022 level (7.2%); whether CASM-Ex keeps rising faster than adjusted TRASM; and how much of the balance-sheet cushion is used if fuel stays high.', BODY),
       Paragraph('Method and limits', H2),
       Paragraph('EBITDA = operating income + D&amp;A. Total debt = long-term debt + finance leases. Liquidity = cash + short-term investments. Coverage = operating income / interest expense. FCF = operating cash flow - capex. Quarterly values are derived from year-to-date filings (Q2 = 6M - 3M, Q3 = 9M - 6M, Q4 = FY - 9M). Interest data are missing for some airlines in 2021 and for quarters in 2021 to 2023; Delta capex for Q2 and Q3 2026 is blank in the source; operating statistics cover Delta only. Fuel share of revenue mixes fuel price and fare effects; because unit revenue was flat, the fuel-cost decline is the main driver, but it is not a pure price effect.', BODY),
       Spacer(1, 6),
       Paragraph('<b>Nathan Dao</b> (Gia Nam Dao) | Finance and Information &amp; Decision Sciences, University of Illinois Chicago' + (f' | Code and data: {GH}' if GH else ''), SMALL),
       Paragraph('Independent analysis of public filings. Not affiliated with or endorsed by Delta Air Lines. Not investment advice.', SMALL)]
doc.build(st); print('built', len(st))
