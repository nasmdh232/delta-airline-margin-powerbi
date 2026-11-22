#!/usr/bin/env python3
"""Generates Delta_Airline.pbip (TMDL semantic model + PBIR report) from data/*.csv.
Run from the project root:  python scripts/build_project.py
"""
import json, os, hashlib, shutil, uuid, textwrap
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
NAME = 'Delta_Airline'
SM = os.path.join(ROOT, NAME + '.SemanticModel')
RP = os.path.join(ROOT, NAME + '.Report')
DEFAULT_FOLDER = os.environ.get('DATA_FOLDER', r'C:\Delta_Airline\data' + '\\')

def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f: f.write(text)
def wj(path, obj): w(path, json.dumps(obj, indent=2))
def guid(seed): return str(uuid.UUID(hashlib.md5(seed.encode()).hexdigest()))
def vid(seed): return hashlib.sha1(seed.encode()).hexdigest()[:20]

# ---------------------------------------------------------------- semantic model
TABLES = {
 'dim_airline': ('dim_airline.csv', [('airline_id','string'),('name','string'),('cik','string'),('is_focus','int64')], 'One row per airline (Delta is the focus; United, American, Southwest are benchmarks).'),
 'dim_period': ('dim_period.csv', [('period_end','dateTime'),('fiscal_year','int64'),('fiscal_quarter','int64'),('label','string'),('qlabel','string')], 'One row per fiscal quarter, Q1 2021 to Q3 2026.'),
 'dim_year': ('dim_year.csv', [('fiscal_year','int64')], 'Fiscal years 2021-2026.'),
 'v_annual': ('v_annual.csv', [('airline_id','string'),('fiscal_year','int64'),('revenue','double'),('fuel_expense','double'),('labor_expense','double'),('d_and_a','double'),('operating_income','double'),('net_income','double'),('interest_expense','double'),('interest_basis','string'),('cfo','double'),('capex','double'),('free_cash_flow','double'),('ebitda','double'),('operating_margin','double'),('net_margin','double'),('fuel_pct_rev','double'),('labor_pct_rev','double'),('liquidity','double'),('total_debt','double'),('debt_to_ebitda','double'),('net_debt_to_ebitda','double'),('interest_coverage','double'),('equity','double'),('total_assets','double')], 'Annual income, cash-flow and balance-sheet facts with derived credit ratios (SEC XBRL).'),
 'v_quarterly': ('v_quarterly.csv', [('airline_id','string'),('fiscal_year','int64'),('fiscal_quarter','int64'),('label','string'),('period_end','dateTime'),('revenue','double'),('fuel_expense','double'),('labor_expense','double'),('d_and_a','double'),('operating_income','double'),('net_income','double'),('interest_expense','double'),('ebitda','double'),('operating_margin','double'),('net_margin','double'),('fuel_pct_rev','double'),('labor_pct_rev','double'),('cfo','double'),('capex','double'),('free_cash_flow','double'),('cash','double'),('st_investments','double'),('liquidity','double'),('current_assets','double'),('current_liabilities','double'),('equity','double'),('total_assets','double'),('total_debt','double')], 'Discrete quarterly facts derived from year-to-date XBRL values.'),
 'v_credit': ('v_credit.csv', [('airline_id','string'),('period_end','dateTime'),('label','string'),('ltm_revenue','double'),('ltm_ebitda','double'),('total_debt','double'),('liquidity','double'),('ltm_operating_margin','double'),('debt_to_ebitda','double'),('interest_coverage','double'),('net_debt_to_ebitda','double')], 'Trailing-twelve-month credit metrics per quarter end.'),
 'margin_bridge': ('margin_bridge.csv', [('driver','string'),('order','int64'),('pts','double')], 'Delta operating-margin bridge FY2022 to FY2025, in percentage points (fuel, labor, other costs).'),
 'operating_metrics': ('operating_metrics.csv', [('airline_id','string'),('fiscal_year','int64'),('asm_millions','double'),('rpm_millions','double'),('load_factor_pct','double'),('trasm_cents','double'),('trasm_adjusted_cents','double'),('casm_ex_cents','double'),('adj_trasm_minus_casm_ex_cents','double'),('source','string')], 'Delta operating statistics from earnings-release statistical summaries (ASM, RPM, TRASM, CASM-Ex).'),
}
KEYS = {('dim_airline','airline_id'),('dim_period','period_end'),('dim_year','fiscal_year')}
HIDDEN_KEYS = {'cik','is_focus','interest_basis','source','order'}
M_TYPE = {'string':'type text','int64':'Int64.Type','double':'type number','dateTime':'type date'}
FMT = {  # column formats
 'pts':'+0.0" pts";-0.0" pts"',
 'revenue':'$#,0','fuel_expense':'$#,0','labor_expense':'$#,0','d_and_a':'$#,0','operating_income':'$#,0','net_income':'$#,0','interest_expense':'$#,0','cfo':'$#,0','capex':'$#,0','free_cash_flow':'$#,0','ebitda':'$#,0','liquidity':'$#,0','total_debt':'$#,0','equity':'$#,0','total_assets':'$#,0','cash':'$#,0','st_investments':'$#,0','current_assets':'$#,0','current_liabilities':'$#,0','ltm_revenue':'$#,0','ltm_ebitda':'$#,0',
 'operating_margin':'0.0%','net_margin':'0.0%','fuel_pct_rev':'0.0%','labor_pct_rev':'0.0%','ltm_operating_margin':'0.0%',
 'debt_to_ebitda':'0.00"x"','net_debt_to_ebitda':'0.00"x"','interest_coverage':'0.0"x"',
 'period_end':'yyyy-mm-dd','fiscal_year':'0','fiscal_quarter':'0',
}
def q(n): return "'%s'" % n if any(c in n for c in " -.&") else n

def table_tmdl(t):
    f, cols, desc = TABLES[t]
    out = ['/// ' + desc, 'table ' + t, '\tlineageTag: ' + guid('t:' + t), '']
    for c, dt in cols:
        out.append('\tcolumn ' + q(c))
        out.append('\t\tdataType: ' + dt)
        if dt == 'dateTime': out.append('\t\tformatString: ' + FMT.get(c, 'General Date'))
        elif c in FMT: out.append('\t\tformatString: ' + FMT[c])
        if (t, c) in KEYS: out.append('\t\tisKey')
        if c in HIDDEN_KEYS: out.append('\t\tisHidden')
        out.append('\t\tlineageTag: ' + guid('c:%s.%s' % (t, c)))
        out.append('\t\tsummarizeBy: none')
        if (t, c) == ('dim_period', 'label'): out.append('\t\tsortByColumn: period_end')
        if (t, c) == ('dim_period', 'qlabel'): out.append('\t\tsortByColumn: fiscal_quarter')
        if (t, c) == ('margin_bridge', 'driver'): out.append('\t\tsortByColumn: order')
        out.append('\t\tsourceColumn: ' + c)
        if dt == 'dateTime': out += ['', '\t\tannotation UnderlyingDateTimeDataType = Date']
        out.append('')
    types = ', '.join('{"%s", %s}' % (c, M_TYPE[dt]) for c, dt in cols)
    out += ['\tpartition %s = m' % t, '\t\tmode: import', '\t\tsource =', '\t\t\t\tlet',
            '\t\t\t\t    Source = Csv.Document(File.Contents(DataFolder & "%s"), [Delimiter = ",", Columns = %d, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),' % (f, len(cols)),
            '\t\t\t\t    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),',
            '\t\t\t\t    Typed = Table.TransformColumnTypes(Promoted, {%s}, "en-US")' % types,
            '\t\t\t\tin', '\t\t\t\t    Typed', '']
    return '\n'.join(out)

# measures: (name, dax, format, description)
B = 'DIVIDE(SUM(%s[%s]),1000000000)'
MEASURES = [
 # annual
 ('Revenue ($B)', B % ('v_annual','revenue'), '$#,0.0"B"', 'Total operating revenue, fiscal year.'),
 ('Operating Income ($B)', B % ('v_annual','operating_income'), '$#,0.0"B"', 'Operating income, fiscal year.'),
 ('Net Income ($B)', B % ('v_annual','net_income'), '$#,0.0"B"', 'Net income, fiscal year.'),
 ('EBITDA ($B)', B % ('v_annual','ebitda'), '$#,0.0"B"', 'Operating income plus D&A.'),
 ('Free Cash Flow ($B)', B % ('v_annual','free_cash_flow'), '$#,0.0"B"', 'Simple FCF = operating cash flow - capex.'),
 ('Operating Margin', 'DIVIDE(SUM(v_annual[operating_income]),SUM(v_annual[revenue]))', '0.0%', 'Operating income / revenue.'),
 ('Net Margin', 'DIVIDE(SUM(v_annual[net_income]),SUM(v_annual[revenue]))', '0.0%', 'Net income / revenue.'),
 ('Fuel % Revenue', 'DIVIDE(SUM(v_annual[fuel_expense]),SUM(v_annual[revenue]))', '0.0%', 'Fuel expense as share of revenue.'),
 ('Labor % Revenue', 'DIVIDE(SUM(v_annual[labor_expense]),SUM(v_annual[revenue]))', '0.0%', 'Salaries and related costs as share of revenue.'),
 ('Other Costs % Revenue', 'IF ( ISBLANK ( [Fuel % Revenue] ) || ISBLANK ( [Operating Margin] ), BLANK (), 1 - [Operating Margin] - [Fuel % Revenue] - [Labor % Revenue] )', '0.0%', 'All other operating costs incl. D&A, as share of revenue (residual).'),
 ('Total Debt ($B)', B % ('v_annual','total_debt'), '$#,0.0"B"', 'Long-term debt + finance leases, year end.'),
 ('Liquidity ($B)', B % ('v_annual','liquidity'), '$#,0.0"B"', 'Cash + short-term investments, year end (excludes undrawn revolver).'),
 ('Debt / EBITDA', 'DIVIDE(SUM(v_annual[total_debt]),SUM(v_annual[ebitda]))', '0.0"x"', 'Total debt / fiscal-year EBITDA.'),
 ('Interest Coverage', 'DIVIDE(SUM(v_annual[operating_income]),SUM(v_annual[interest_expense]))', '0.0"x"', 'Operating income / interest expense.'),
 # quarterly
 ('Qtr Revenue ($B)', B % ('v_quarterly','revenue'), '$#,0.0"B"', 'Discrete quarterly revenue.'),
 ('Qtr Operating Margin', 'DIVIDE(SUM(v_quarterly[operating_income]),SUM(v_quarterly[revenue]))', '0.0%', 'Discrete quarterly operating margin.'),
 ('Qtr Fuel % Revenue', 'DIVIDE(SUM(v_quarterly[fuel_expense]),SUM(v_quarterly[revenue]))', '0.0%', 'Discrete quarterly fuel share of revenue.'),
 ('Qtr Labor % Revenue', 'DIVIDE(SUM(v_quarterly[labor_expense]),SUM(v_quarterly[revenue]))', '0.0%', 'Discrete quarterly labor share of revenue.'),
 # credit (LTM)
 ('LTM Debt / EBITDA', 'AVERAGE(v_credit[debt_to_ebitda])', '0.0"x"', 'Total debt / trailing-12-month EBITDA (blank until 4 quarters of data exist).'),
 ('LTM Interest Coverage', 'AVERAGE(v_credit[interest_coverage])', '0.0"x"', 'LTM operating income / LTM interest expense.'),
 ('LTM Operating Margin', 'AVERAGE(v_credit[ltm_operating_margin])', '0.0%', 'Trailing-12-month operating margin.'),
 ('Liquidity Qtr-end ($B)', B % ('v_credit','liquidity'), '$#,0.0"B"', 'Cash + short-term investments at quarter end.'),
 ('Total Debt Qtr-end ($B)', B % ('v_credit','total_debt'), '$#,0.0"B"', 'Total debt at quarter end.'),
 # unit economics (Delta)
 ('Load Factor', 'DIVIDE(SUM(operating_metrics[rpm_millions]),SUM(operating_metrics[asm_millions]))', '0.0%', 'RPM / ASM (Delta).'),
 ('Adj. TRASM (cents)', 'AVERAGE(operating_metrics[trasm_adjusted_cents])', '0.00"¢"', 'Adjusted total revenue per available seat mile (Delta).'),
 ('CASM-Ex (cents)', 'AVERAGE(operating_metrics[casm_ex_cents])', '0.00"¢"', 'Unit cost excluding fuel, profit sharing and special items (Delta).'),
 ('Unit Margin Gap (cents)', 'AVERAGE(operating_metrics[adj_trasm_minus_casm_ex_cents])', '0.00"¢"', 'Adjusted TRASM minus CASM-Ex.'),
 ('ASM (billions)', 'DIVIDE(SUM(operating_metrics[asm_millions]),1000)', '#,0.0', 'Available seat miles, billions (Delta).'),
 ('Op Margin FY2022', 'CALCULATE([Operating Margin], dim_year[fiscal_year] = 2022)', '0.0%', 'Operating margin, FY2022.'),
 ('Op Margin FY2025', 'CALCULATE([Operating Margin], dim_year[fiscal_year] = 2025)', '0.0%', 'Operating margin, FY2025.'),
 ('Fuel % Rev FY2022', 'CALCULATE([Fuel % Revenue], dim_year[fiscal_year] = 2022)', '0.0%', 'Fuel share of revenue, FY2022.'),
 ('Fuel % Rev FY2025', 'CALCULATE([Fuel % Revenue], dim_year[fiscal_year] = 2025)', '0.0%', 'Fuel share of revenue, FY2025.'),
 ('Unit Gap FY2022', 'CALCULATE([Unit Margin Gap (cents)], dim_year[fiscal_year] = 2022)', '0.00"¢"', 'Adj. TRASM minus CASM-Ex, FY2022.'),
 ('Unit Gap FY2025', 'CALCULATE([Unit Margin Gap (cents)], dim_year[fiscal_year] = 2025)', '0.00"¢"', 'Adj. TRASM minus CASM-Ex, FY2025.'),
 ('Margin Change (pts)', 'SUM(margin_bridge[pts])', '+0.0" pts";-0.0" pts"', 'Contribution to the FY2022 to FY2025 margin change, percentage points.'),
 ('Margin at Fuel Shock', 'CALCULATE([Operating Margin], dim_year[fiscal_year] = 2025) - CALCULATE([Fuel % Revenue], dim_year[fiscal_year] = 2025) * MAX(\'Fuel Shock\'[Fuel Shock %]) / 100', '0.0%', 'FY2025 operating margin if fuel cost per unit changes by the shock %, no revenue pass-through (simple sensitivity).'),
 ('Debt / EBITDA FY2021', 'CALCULATE([Debt / EBITDA], dim_year[fiscal_year] = 2021)', '0.0"x"', 'Debt / EBITDA, FY2021.'),
 ('Debt / EBITDA FY2025', 'CALCULATE([Debt / EBITDA], dim_year[fiscal_year] = 2025)', '0.0"x"', 'Debt / EBITDA, FY2025.'),
]
def measures_tmdl():
    out = ['/// Calculation table: all report measures live here.', "table 'Key Measures'", '\tlineageTag: ' + guid('t:Measures'), '']
    for n, dax, fmt, desc in MEASURES:
        out += ['\t/// ' + desc, '\tmeasure %s = %s' % (q(n), dax), '\t\tformatString: ' + fmt, '\t\tlineageTag: ' + guid('m:' + n), '']
    out += ['\tcolumn Placeholder', '\t\tdataType: int64', '\t\tisHidden', '\t\tlineageTag: ' + guid('c:Measures.Placeholder'), '\t\tsummarizeBy: none', '\t\tsourceColumn: Placeholder', '',
            "\tpartition 'Key Measures' = m", '\t\tmode: import', '\t\tsource =', '\t\t\t\tlet', '\t\t\t\t    Source = #table(type table [Placeholder = Int64.Type], {{1}})', '\t\t\t\tin', '\t\t\t\t    Source', '']
    return '\n'.join(out)

def relabel():
    import csv
    def lab(fy, q): return 'Q%s %s' % (q, str(fy)[2:])
    pth = lambda n: os.path.join(ROOT, 'data', n)
    per = list(csv.DictReader(open(pth('dim_period.csv'))))
    m = {}
    for r in per:
        r['label'] = lab(r['fiscal_year'], r['fiscal_quarter']); r['qlabel'] = 'Q%s' % r['fiscal_quarter']; m[r['period_end']] = r['label']
    def dump(n, rows):
        with open(pth(n), 'w', newline='') as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator='\n'); wr.writeheader(); wr.writerows(rows)
    dump('dim_period.csv', per)
    for n in ('v_quarterly.csv', 'v_credit.csv'):
        rows = list(csv.DictReader(open(pth(n))))
        for r in rows: r['label'] = m[r['period_end']]
        dump(n, rows)

def make_bridge():
    import csv
    rows = {(r['airline_id'], r['fiscal_year']): r for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'v_annual.csv')))}
    a, b = rows[('DAL', '2022')], rows[('DAL', '2025')]
    f = lambda r, k: float(r[k])
    fuel = (f(a, 'fuel_pct_rev') - f(b, 'fuel_pct_rev')) * 100
    labor = (f(a, 'labor_pct_rev') - f(b, 'labor_pct_rev')) * 100
    total = (f(b, 'operating_margin') - f(a, 'operating_margin')) * 100
    other = total - fuel - labor
    with open(os.path.join(ROOT, 'data', 'margin_bridge.csv'), 'w', newline='') as fh:
        fh.write('driver,order,pts\n')
        for i, (d, v) in enumerate([('Fuel (lower % of revenue)', fuel), ('Labor (higher % of revenue)', labor), ('Other costs incl. D&A', other)]):
            fh.write('%s,%d,%.4f\n' % (d, i + 1, v))

def shock_tmdl():
    return '\n'.join(['/// Fuel-price shock values (%) for the stress-test chart.', "table 'Fuel Shock'", '\tlineageTag: ' + guid('t:FuelShock'), '',
        "\tcolumn 'Fuel Shock %'", '\t\tdataType: int64', '\t\tformatString: +0"%";-0"%";0"%"', '\t\tlineageTag: ' + guid('c:FuelShock'), '\t\tsummarizeBy: none', '\t\tsourceColumn: [Value]', '',
        "\tpartition 'Fuel Shock' = calculated", '\t\tmode: import', '\t\tsource = GENERATESERIES(-20, 40, 10)', ''])

def build_model():
    relabel(); make_bridge()
    shutil.rmtree(SM, ignore_errors=True)
    wj(os.path.join(SM, 'definition.pbism'), {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json", "version": "4.2", "settings": {"qnaEnabled": True}})
    wj(os.path.join(SM, '.platform'), {"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json", "metadata": {"type": "SemanticModel", "displayName": NAME}, "config": {"version": "2.0", "logicalId": guid('sm:' + NAME)}})
    d = os.path.join(SM, 'definition')
    w(os.path.join(d, 'database.tmdl'), '/// Delta Air Lines deep dive - margin drivers and credit strength.\ndatabase\n\tcompatibilityLevel: 1702\n\n')
    order = list(TABLES) + ['Fuel Shock', 'Key Measures', 'DataFolder']
    w(os.path.join(d, 'model.tmdl'), '/// Delta Air Lines deep dive: SEC XBRL financials FY2021-Q3 2026 for Delta, United, American and Southwest, plus Delta operating statistics.\nmodel %s\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n\tsourceQueryCulture: en-US\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\nannotation PBI_QueryOrder = %s\n\nannotation __PBI_TimeIntelligenceEnabled = 0\n\n%s\n\nref cultureInfo en-US\n\n' % (NAME, json.dumps(order), '\n'.join('ref table ' + q(t) for t in list(TABLES) + ['Fuel Shock', 'Key Measures'])))
    w(os.path.join(d, 'expressions.tmdl'), '/// Absolute path (with trailing backslash) of the folder holding the CSV files. Update it if the project folder moves.\nexpression DataFolder = "%s" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n\tlineageTag: %s\n\n\tannotation PBI_ResultType = Text\n\n' % (DEFAULT_FOLDER, guid('expr:DataFolder')))
    rels = [('v_annual','airline_id','dim_airline','airline_id'),('v_quarterly','airline_id','dim_airline','airline_id'),('v_credit','airline_id','dim_airline','airline_id'),('operating_metrics','airline_id','dim_airline','airline_id'),
            ('v_annual','fiscal_year','dim_year','fiscal_year'),('operating_metrics','fiscal_year','dim_year','fiscal_year'),
            ('v_quarterly','period_end','dim_period','period_end'),('v_credit','period_end','dim_period','period_end'),('dim_period','fiscal_year','dim_year','fiscal_year')]
    w(os.path.join(d, 'relationships.tmdl'), '\n'.join("relationship %s\n\tfromColumn: %s.%s\n\ttoColumn: %s.%s\n" % (guid('r:%s.%s>%s.%s' % r), r[0], r[1], r[2], r[3]) for r in rels))
    for t in TABLES: w(os.path.join(d, 'tables', t + '.tmdl'), table_tmdl(t))
    w(os.path.join(d, 'tables', 'Measures.tmdl'), measures_tmdl())
    w(os.path.join(d, 'tables', 'Fuel Shock.tmdl'), shock_tmdl())
    w(os.path.join(d, 'cultures', 'en-US.tmdl'), 'cultureInfo en-US\n')

# ---------------------------------------------------------------- report
SCH = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'
S_PAGE, S_VIS, S_PAGES, S_REP, S_VER = SCH+'page/2.1.0/schema.json', SCH+'visualContainer/2.9.0/schema.json', SCH+'pagesMetadata/1.1.0/schema.json', SCH+'report/3.3.0/schema.json', SCH+'versionMetadata/1.0.0/schema.json'
W_, H_ = 1920, 1080
T = dict(page='#07090D', card='#121B2D', border='#22304A', text='#E8EDF5', muted='#8FA0B8', red='#F0455A', navy='#5B9BD5', gray='#8FA0B8', blue='#5B9BD5', gold='#F2B544')
AIR = {'DAL': T['red'], 'UAL': T['navy'], 'AAL': T['gray'], 'LUV': T['gold']}
AIRNAME = {'Delta Air Lines': T['red'], 'United Airlines Holdings': T['navy'], 'American Airlines Group': T['gray'], 'Southwest Airlines': T['gold']}
lit = lambda v: {'expr': {'Literal': {'Value': v}}}
st = lambda s: lit("'%s'" % str(s).replace("'", "''"))
nm = lambda n: lit('%sD' % n)
it = lambda n: lit('%sL' % n)
bo = lambda b: lit('true' if b else 'false')
fl = lambda c: {'solid': {'color': st(c)}}
def Mz(n): return {'Measure': {'Expression': {'SourceRef': {'Entity': 'Key Measures'}}, 'Property': n}}
def Cz(t, c): return {'Column': {'Expression': {'SourceRef': {'Entity': t}}, 'Property': c}}
def ent(f): k = f.get('Measure') or f.get('Column'); return k['Expression']['SourceRef']['Entity'], k['Property']
def proj(f, label=None, active=False):
    e, p = ent(f); d = {'field': f, 'queryRef': '%s.%s' % (e, p), 'nativeQueryRef': p}
    if label: d['displayName'] = label
    if active: d['active'] = True
    return d
def role(*fs): return {'projections': [proj(*f) if isinstance(f, tuple) else proj(f) for f in fs]}
AIRLINE = Cz('dim_airline', 'name'); YEAR = Cz('dim_year', 'fiscal_year'); QLBL = [Cz('dim_period', 'fiscal_year'), Cz('dim_period', 'qlabel')]; QEND = Cz('dim_period', 'period_end')

def chrome(title, alt, sub=None):
    v = {'background': [{'properties': {'show': bo(True), 'color': fl(T['card']), 'transparency': nm(22)}}],
         'border': [{'properties': {'show': bo(True), 'color': fl(T['border']), 'radius': nm(8), 'width': nm(1)}}],
         'padding': [{'properties': {'top': nm(14), 'bottom': nm(14), 'left': nm(16), 'right': nm(16)}}],
         'general': [{'properties': {'altText': st(alt)}}],
         'title': [{'properties': {'show': bo(True), 'text': st(title), 'fontSize': nm(14), 'bold': bo(True), 'fontColor': fl(T['text'])}}]}
    if sub: v['subTitle'] = [{'properties': {'show': bo(True), 'text': st(sub), 'fontSize': nm(11), 'fontColor': fl(T['muted'])}}]
    return v
axis = lambda: [{'properties': {'labelColor': fl(T['muted']), 'fontSize': nm(10), 'gridlineShow': bo(False)}}]
vaxis = lambda: [{'properties': {'labelColor': fl(T['muted']), 'fontSize': nm(10), 'gridlineShow': bo(True), 'gridlineColor': fl('#22304A'), 'labelDisplayUnits': nm(1)}}]
legend = lambda show=True: [{'properties': {'show': bo(show), 'position': st('Top'), 'fontSize': nm(11), 'labelColor': fl(T['muted'])}}]
labels = lambda show, extra=None: [{'properties': dict({'show': bo(show), 'fontSize': nm(11), 'color': fl(T['text']), 'labelDisplayUnits': nm(1)}, **(extra or {}))}]
def fills(pairs, ent_='Key Measures'):  # [(measure, color)]
    return [{'properties': {'fill': fl(c)}, 'selector': {'metadata': '%s.%s' % (ent_, m)}} for m, c in pairs]
def airline_fills():
    return [{'properties': {'fill': fl(c)}, 'selector': {'data': [{'scopeId': {'Comparison': {'ComparisonKind': 0, 'Left': {'Column': {'Expression': {'SourceRef': {'Entity': 'dim_airline'}}, 'Property': 'name'}}, 'Right': {'Literal': {'Value': "'%s'" % n}}}}}]}} for n, c in AIRNAME.items()]
line_w = lambda wd=2.25: [{'properties': {'strokeWidth': nm(wd), 'showMarker': bo(False), 'lineChartType': st('linear')}}]

def textbox(paras):
    return {'visualType': 'textbox', 'objects': {'general': [{'properties': {'paragraphs': paras}}]},
            'visualContainerObjects': {'background': [{'properties': {'show': bo(False)}}], 'border': [{'properties': {'show': bo(False)}}], 'padding': [{'properties': {k: nm(0) for k in ('top','bottom','left','right')}}]}}
def run(v, size='11pt', color=None, bold=False): return {'value': v, 'textStyle': {'fontFamily': 'Segoe UI Semibold' if bold else 'Segoe UI', 'fontSize': size, 'color': color or T['text']}}
def para(*runs): return {'textRuns': list(runs), 'horizontalTextAlignment': 'left'}
def title_box(t, sub): return textbox([para(run(t, '28pt', bold=True)), para(run(sub, '12pt', T['muted']))])
def card_box(paras, alt):
    v = textbox(paras)
    v['visualContainerObjects'] = {'background': [{'properties': {'show': bo(True), 'color': fl(T['card']), 'transparency': nm(22)}}], 'border': [{'properties': {'show': bo(True), 'color': fl(T['border']), 'radius': nm(8), 'width': nm(1)}}],
        'padding': [{'properties': {'top': nm(14), 'bottom': nm(14), 'left': nm(18), 'right': nm(18)}}], 'general': [{'properties': {'altText': st(alt)}}]}
    return v
def slicer(field, header, mode='Dropdown'):
    return {'visualType': 'slicer', 'query': {'queryState': {'Values': role(field)}},
            'objects': {'data': [{'properties': {'mode': st(mode)}}], 'header': [{'properties': {'show': bo(True), 'text': st(header), 'fontColor': fl(T['muted']), 'textSize': nm(9)}}], 'items': [{'properties': {'fontColor': fl(T['text']), 'background': fl(T['card']), 'textSize': nm(10)}}]},
            'visualContainerObjects': {'background': [{'properties': {'show': bo(True), 'color': fl(T['card']), 'transparency': nm(22)}}], 'border': [{'properties': {'show': bo(True), 'color': fl(T['border']), 'radius': nm(8), 'width': nm(1)}}],
                'padding': [{'properties': {k: nm(6) for k in ('top','bottom','left','right')}}], 'general': [{'properties': {'altText': st(header + ' slicer')}}]}}
def kpis(measures, alt, cols):
    return {'visualType': 'cardVisual', 'query': {'queryState': {'Data': role(*[(Mz(m[0]), m[1]) for m in measures])}},
        'objects': {'value': [{'properties': {'fontSize': nm(28), 'fontColor': fl(T['text']), 'fontFamily': st('Segoe UI Semibold'), 'labelDisplayUnits': nm(1)}, 'selector': {'id': 'default'}}],
                    'label': [{'properties': {'fontSize': nm(11), 'fontColor': fl(T['muted']), 'textWrap': bo(True)}, 'selector': {'id': 'default'}}],
                    'padding': [{'properties': {'paddingUniform': it(8)}, 'selector': {'id': 'default'}}],
                    'layout': [{'properties': {'paddingUniform': it(0), 'columnCount': it(cols), 'autoGrid': bo(False)}, 'selector': {'id': 'default'}}],
                    'fillCustom': [{'properties': {'show': bo(True), 'fillColor': fl(T['card']), 'transparency': nm(22)}, 'selector': {'id': 'default'}}],
                    'accentBar': [{'properties': {'show': bo(True), 'position': st('Left'), 'color': fl(T['red']), 'width': nm(4)}, 'selector': {'id': 'default'}}],
                    'outline': [{'properties': {'show': bo(True), 'color': fl(T['border'])}, 'selector': {'id': 'default'}}]},
        'visualContainerObjects': {'background': [{'properties': {'show': bo(False)}}], 'border': [{'properties': {'show': bo(False)}}], 'padding': [{'properties': {k: nm(0) for k in ('top','bottom','left','right')}}],
                                   'title': [{'properties': {'show': bo(False)}}], 'general': [{'properties': {'altText': st(alt)}}]}}
def img(name, alt, scaling='Fit'):
    return {'visualType': 'image', 'objects': {'general': [{'properties': {'imageUrl': {'expr': {'ResourcePackageItem': {'PackageName': 'RegisteredResources', 'PackageType': 1, 'ItemName': name}}}}}],
            'imageScaling': [{'properties': {'imageScalingType': st(scaling)}}]},
            'visualContainerObjects': {'background': [{'properties': {'show': bo(False)}}], 'border': [{'properties': {'show': bo(False)}}], 'general': [{'properties': {'altText': st(alt)}}]}}
def find_asset(stem):
    import glob
    g = sorted(glob.glob(os.path.join(ROOT, 'assets', stem + '.*')))
    return g[0] if g else None
def sort_q(field, d='Ascending'): return {'sort': [{'field': field, 'direction': d}], 'isDefaultSort': False}
def chart(vt, cat, ys, title, alt, sub=None, series=None, colors=None, y2=None, data_labels=False, sort=None, extra_obj=None):
    cats = cat if isinstance(cat, list) else [cat]
    qs = {'Category': {'projections': [proj(c, active=True) for c in cats]}, 'Y': role(*ys)}
    if series: qs['Series'] = {'projections': [proj(series, active=True)]}
    if y2: qs['Y2'] = role(*y2)
    q_ = {'queryState': qs}
    q_['sortDefinition'] = {'sort': [{'field': f, 'direction': 'Ascending'} for f in cats], 'isDefaultSort': False} if (len(cats) > 1 and not sort) else sort_q(sort or cats[0])
    obj = {'legend': legend(bool(series) or len(ys) > 1), 'labels': labels(data_labels), 'categoryAxis': axis() if len(cats) == 1 else [{'properties': dict(axis()[0]['properties'], concatenateLabels=bo(False))}], 'valueAxis': vaxis()}
    if vt == 'lineChart': obj['lineStyles'] = line_w()
    if colors: obj['dataPoint'] = colors
    if extra_obj: obj.update(extra_obj)
    return {'visualType': vt, 'query': q_, 'objects': obj, 'visualContainerObjects': chrome(title, alt, sub)}
def table(cols, title, alt, sub=None, sort=None):
    qs = {'Values': {'projections': [proj(c[0], c[1]) if isinstance(c, tuple) else proj(c) for c in cols]}}
    v = {'visualType': 'tableEx', 'query': {'queryState': qs}, 'objects': {
        'columnHeaders': [{'properties': {'fontColor': fl(T['text']), 'backColor': fl('#1A2740'), 'bold': bo(True), 'fontSize': nm(11)}}],
        'values': [{'properties': {'fontColorPrimary': fl(T['text']), 'backColorPrimary': fl(T['card']), 'backColorSecondary': fl('#0F1829'), 'fontColorSecondary': fl(T['text']), 'fontSize': nm(11)}}],
        'total': [{'properties': {'totals': bo(False)}}],
        'grid': [{'properties': {'gridHorizontal': bo(True), 'gridHorizontalColor': fl(T['border']), 'gridVertical': bo(False)}}]},
        'visualContainerObjects': chrome(title, alt, sub)}
    if sort: v['query']['sortDefinition'] = sort_q(sort)
    return v

def delta_filter(name):
    cond = {'In': {'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': 'd'}}, 'Property': 'name'}}],
                   'Values': [[{'Literal': {'Value': "'Delta Air Lines'"}}]]}}
    flt = {'Version': 2, 'From': [{'Name': 'd', 'Entity': 'dim_airline', 'Type': 0}], 'Where': [{'Condition': cond}]}
    return {'filters': [{'name': name, 'field': Cz('dim_airline', 'name'), 'type': 'Categorical', 'howCreated': 'User', 'filter': flt}]}
GRID = 16
def rect(x, y, w_, h_): return dict(x=x, y=y, width=w_, height=h_)
FOOT = 'Sources: SEC EDGAR XBRL company facts (10-K/10-Q) and Delta earnings-release statistical summaries. EBITDA = operating income + D&A; debt = long-term debt + finance leases; liquidity = cash + short-term investments. Quarterly values derived from YTD filings.'
WALL = None
def page(pid, name, visuals, nav_key, delta_only=False):
    d = os.path.join(RP, 'definition', 'pages', pid)
    vis = list(visuals) + [('footnote', rect(24, 1052, 1872, 22), textbox([para(run(FOOT, '9pt', '#6F819B'))]))]
    for i, (key, pos, v) in enumerate(vis):
        n = vid(pid + key)
        vj = {'$schema': S_VIS, 'name': n, 'position': dict(pos, z=(i + 1) * 1000, tabOrder=(i + 1) * 1000), 'visual': v}
        if key.endswith('_delta'): vj['filterConfig'] = delta_filter('F' + vid('f' + n))
        wj(os.path.join(d, 'visuals', n, 'visual.json'), vj)
    pj = {'$schema': S_PAGE, 'name': pid, 'displayName': name, 'displayOption': 'FitToPage', 'height': H_, 'width': W_,
        'objects': {'background': [{'properties': dict({'color': fl(T['page']), 'transparency': nm(0)}, **({'image': {'image': {'name': st(os.path.basename(WALL)), 'scaling': st('Fill'), 'url': {'expr': {'ResourcePackageItem': {'PackageName': 'RegisteredResources', 'PackageType': 1, 'ItemName': os.path.basename(WALL)}}}}}} if WALL else {}))}], 'outspace': [{'properties': {'color': fl('#07090D'), 'transparency': nm(0)}}]}}
    if delta_only: pj['filterConfig'] = delta_filter('F' + vid('pf' + pid))
    wj(os.path.join(d, 'page.json'), pj)

def build_report():
    shutil.rmtree(RP, ignore_errors=True)
    wj(os.path.join(RP, 'definition.pbir'), {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json", "version": "4.0", "datasetReference": {"byPath": {"path": "../%s.SemanticModel" % NAME}}})
    wj(os.path.join(RP, '.platform'), {"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json", "metadata": {"type": "Report", "displayName": NAME}, "config": {"version": "2.0", "logicalId": guid('rp:' + NAME)}})
    base = '/mnt/user-data/uploads/GDP_Project/WorldEconomyExplorer.Report/StaticResources/SharedResources/BaseThemes/Fluent2-CY26SU10.json'
    if os.path.exists(base):
        os.makedirs(os.path.join(RP, 'StaticResources/SharedResources/BaseThemes'), exist_ok=True)
        shutil.copy(base, os.path.join(RP, 'StaticResources/SharedResources/BaseThemes/Fluent2-CY26SU10.json'))
    ver = {"visual": "2.11.0", "report": "3.4.0", "page": "2.3.1"}
    wj(os.path.join(RP, 'definition', 'report.json'), {"$schema": S_REP, "themeCollection": {"baseTheme": {"name": "Fluent2-CY26SU10", "reportVersionAtImport": ver, "type": "SharedResources"}},
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [{"name": "Fluent2-CY26SU10", "path": "BaseThemes/Fluent2-CY26SU10.json", "type": "BaseTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized", "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True, "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}})
    wj(os.path.join(RP, 'definition', 'version.json'), {"$schema": S_VER, "version": "2.0.0"})
    P = {k: vid('page3:' + k) for k in ('thesis', 'deep', 'concl', 'method')}
    LOGO, PLANE, PLANE2 = find_asset('delta_logo'), find_asset('delta_plane'), find_asset('delta_plane2')
    RES = []
    global WALL
    WALL = find_asset('delta_wallpaper')
    for a in (LOGO, PLANE, PLANE2, WALL):
        if a:
            os.makedirs(os.path.join(RP, 'StaticResources', 'RegisteredResources'), exist_ok=True)
            shutil.copy(a, os.path.join(RP, 'StaticResources', 'RegisteredResources', os.path.basename(a)))
            RES.append({'name': os.path.basename(a), 'path': os.path.basename(a), 'type': 'Image'})
    if RES:
        rj = os.path.join(RP, 'definition', 'report.json'); rep = json.load(open(rj))
        rep['resourcePackages'].append({'name': 'RegisteredResources', 'type': 'RegisteredResources', 'items': RES}); wj(rj, rep)
    logo_v = [('logo', rect(1796, 18, 100, 80), img(os.path.basename(LOGO), 'Delta Air Lines logo'))] if LOGO else []
    HDR = lambda t, sub: logo_v + [('title', rect(24, 16, 1760, 84), title_box(t, sub))]
    Y1, Y2, Y3 = 108, 216, 640
    # page 1: the thesis on one screen
    page(P['thesis'], '1 The thesis', HDR("Delta's margin gain was fuel, not efficiency", 'Operating margin rose from 7.2% to 9.2% (FY2022 to FY2025) while unit economics weakened; fuel is already reversing part of it in 2026.') + [
        ('kpis_delta', rect(24, Y1, 1872, 96), kpis([('Op Margin FY2022', 'Operating margin FY22'), ('Op Margin FY2025', 'Operating margin FY25'), ('Fuel % Rev FY2022', 'Fuel % revenue FY22'), ('Fuel % Rev FY2025', 'Fuel % revenue FY25'), ('Unit Gap FY2022', 'TRASM - CASM-Ex FY22'), ('Unit Gap FY2025', 'TRASM - CASM-Ex FY25'), ('Debt / EBITDA FY2021', 'Debt / EBITDA FY21'), ('Debt / EBITDA FY2025', 'Debt / EBITDA FY25')], 'Delta headline numbers.', 8)),
        ('bridge', rect(24, Y2, 520, 412), chart('clusteredColumnChart', Cz('margin_bridge', 'driver'), [(Mz('Margin Change (pts)'), 'Change in margin')], '1. Why margin moved +2.0 pts', 'Contribution of fuel, labor and other costs to the change in Delta operating margin FY2022 to FY2025.', 'Points of revenue, FY22 to FY25; positive = helped', colors=fills([('Margin Change (pts)', T['red'])]), data_labels=True)),
        ('qtr_delta', rect(560, Y2, 820, 412), chart('lineChart', QLBL, [(Mz('Qtr Fuel % Revenue'), 'Fuel % of revenue'), (Mz('Qtr Operating Margin'), 'Operating margin')], '2. Fuel drives the margin, quarter by quarter', 'Delta quarterly fuel share of revenue and operating margin.', 'Fuel hit 20.8% and 21.6% of revenue in Q2 and Q3 2026', colors=fills([('Qtr Fuel % Revenue', T['gold']), ('Qtr Operating Margin', T['red'])]))),
        ('unit_delta', rect(1396, Y2, 500, 412), chart('lineChart', YEAR, [(Mz('Adj. TRASM (cents)'), 'Adj. TRASM'), (Mz('CASM-Ex (cents)'), 'CASM-Ex')], '3. Unit revenue flat, unit cost up', 'Delta adjusted TRASM and CASM-Ex in cents by year.', 'Cents per available seat mile', colors=fills([('Adj. TRASM (cents)', T['red']), ('CASM-Ex (cents)', T['blue'])]), data_labels=True)),
        ('shock_delta', rect(24, Y3, 520, 400), chart('lineChart', Cz('Fuel Shock', 'Fuel Shock %'), [(Mz('Margin at Fuel Shock'), 'FY2025 operating margin')], '4. Stress test: margin vs fuel-price shock', 'Delta FY2025 operating margin if fuel cost changes by the percent on the axis.', 'FY25 margin minus fuel share x shock; no fare pass-through', colors=fills([('Margin at Fuel Shock', T['red'])]), data_labels=True)),
        ('liq_delta', rect(560, Y3, 820, 400), chart('lineChart', QLBL, [(Mz('Liquidity Qtr-end ($B)'), 'Liquidity'), (Mz('Total Debt Qtr-end ($B)'), 'Total debt')], '5. Balance sheet: debt roughly halved', 'Delta quarter-end liquidity and total debt in billions.', '$ billions; debt/EBITDA 6.9x in FY21 to 1.7x in FY25', colors=fills([('Liquidity Qtr-end ($B)', T['blue']), ('Total Debt Qtr-end ($B)', T['red'])]))),
        ('peers', rect(1396, Y3, 500, 400), chart('clusteredColumnChart', AIRLINE, [(Mz('Debt / EBITDA FY2025'), 'Debt / EBITDA FY2025')], '6. Peer check: leverage FY2025', 'FY2025 debt to EBITDA for Delta, United, American and Southwest.', 'Total debt / EBITDA', colors=fills([('Debt / EBITDA FY2025', T['gray'])]), data_labels=True, sort=Mz('Debt / EBITDA FY2025'))),
    ], 'thesis', delta_only=False)
    # page 2: deep dive
    X = [24, 632, 1352]; WD = [592, 704, 544]
    page(P['deep'], '2 Deep dive', HDR('Deep dive: costs, unit economics, credit and peers', 'Every chart behind the thesis: cost structure, unit margin gap, load factor, leverage and coverage against peers, and the annual table.') + [
        ('cost_delta', rect(X[0], Y1, WD[0], 324), chart('columnChart', YEAR, [(Mz('Fuel % Revenue'), 'Fuel'), (Mz('Labor % Revenue'), 'Labor'), (Mz('Other Costs % Revenue'), 'Other incl. D&A'), (Mz('Operating Margin'), 'Operating margin')], 'Cost structure and margin (Delta)', 'Delta fuel, labor, other cost share and operating margin by year.', '% of revenue', colors=fills([('Fuel % Revenue', T['gold']), ('Labor % Revenue', T['blue']), ('Other Costs % Revenue', T['gray']), ('Operating Margin', T['red'])]), data_labels=True)),
        ('opm', rect(X[1], Y1, WD[1], 324), chart('lineChart', YEAR, [(Mz('Operating Margin'), 'Operating margin')], 'Operating margin vs peers', 'Operating margin by airline and year.', 'Annual', series=AIRLINE, colors=airline_fills())),
        ('gap_delta', rect(X[2], Y1, WD[2], 324), chart('clusteredColumnChart', YEAR, [(Mz('Unit Margin Gap (cents)'), 'Adj. TRASM - CASM-Ex')], 'Unit margin gap (Delta)', 'Gap between adjusted TRASM and CASM-Ex by year.', 'Cents per ASM; peak 6.93 in 2023', colors=fills([('Unit Margin Gap (cents)', T['red'])]), data_labels=True)),
        ('lev', rect(24, 448, 720, 324), chart('lineChart', QLBL, [(Mz('LTM Debt / EBITDA'), 'Debt / LTM EBITDA')], 'Leverage (LTM) vs peers', 'Debt to LTM EBITDA by quarter and airline.', 'Debt / LTM EBITDA, x; axis capped at 15x (American peaked near 67x in Q1 22)', series=AIRLINE, colors=airline_fills(), extra_obj={'valueAxis': [{'properties': {'labelColor': fl(T['muted']), 'fontSize': nm(10), 'gridlineShow': bo(True), 'gridlineColor': fl('#22304A'), 'labelDisplayUnits': nm(1), 'start': nm(0), 'end': nm(15)}}]})),
        ('cov', rect(760, 448, 720, 324), chart('lineChart', QLBL, [(Mz('LTM Interest Coverage'), 'Interest coverage')], 'Interest coverage (LTM) vs peers', 'LTM interest coverage by quarter and airline.', 'Operating income / interest, x', series=AIRLINE, colors=airline_fills())),
        ('lf_delta', rect(1496, 448, 400, 324), chart('lineChart', YEAR, [(Mz('Load Factor'), 'Load factor')], 'Load factor (Delta)', 'Delta load factor by year.', 'RPM / ASM', colors=fills([('Load Factor', T['blue'])]), data_labels=True)),
        ('tbl_delta', rect(24, 788, 1400, 252), table([(YEAR, 'Year'), Mz('Revenue ($B)'), Mz('Operating Margin'), Mz('Net Margin'), Mz('Fuel % Revenue'), Mz('Labor % Revenue'), Mz('Total Debt ($B)'), Mz('Liquidity ($B)'), Mz('Debt / EBITDA'), Mz('Interest Coverage'), Mz('Free Cash Flow ($B)')], 'Delta annual summary', 'Annual table of Delta revenue, margins, cost shares, debt, liquidity, leverage, coverage and free cash flow.', sort=YEAR)),
        ('tbl_note', rect(1440, 788, 456, 252), card_box([para(run('Reading the table', '15pt', T['red'], bold=True)), para(run(' ', '4pt')),
            para(run('Debt / EBITDA fell from 6.9x (2021) to 1.7x (2025); interest coverage rose from 1.5x to 8.6x.', '11pt', T['text'])), para(run(' ', '4pt')),
            para(run('Free cash flow went from about zero in 2021 and 2022 to $3.8B in 2025.', '11pt', T['text'])), para(run(' ', '4pt')),
            para(run('Operating margin peaked at 9.7% in 2024 and slipped to 9.2% in 2025: fuel share fell again (17.1% to 15.5%) but labor share kept rising (26.2% to 27.6%).', '11pt', T['text']))], 'Reading notes for the annual table.')),
    ], 'deep')
    # page 3: conclusion
    hh = lambda t: para(run(t, '20pt', T['red'], bold=True))
    bp = lambda t: [para(run(t, '18pt', T['text'])), para(run(' ', '10pt'))]
    c1 = [hh('What the data says')] + bp('1. Margin rose 2.0 pts (7.2% to 9.2%, FY22 to FY25). Fuel fell from 22.7% to 15.5% of revenue (+7.2 pts); labor (-4.1 pts) and other costs (-1.1 pts) gave most of it back.') \
        + bp('2. Unit economics got worse, not better. Adjusted TRASM was flat (19.55 to 19.56 cents) while CASM-Ex rose from 12.87 to 13.86 cents, so the unit margin gap fell from 6.68 to 5.70 cents.') \
        + bp('3. The lasting gain is the balance sheet. Total debt fell from $26.9B to $14.1B, Debt/EBITDA from 6.9x to 1.7x, and interest coverage reached 8.6x in FY2025.')
    c2 = [hh('What it means')] + bp('Most of the profit improvement came from a cost Delta does not control. When fuel was cheap, margin rose; the underlying cost and unit-revenue position did not improve.') \
        + bp('Fuel is already reversing. It reached 20.8% and 21.6% of revenue in Q2 and Q3 2026, against 15.5% in FY2025.') \
        + bp('Stress test: at the FY2025 mix, every +10% in fuel price costs about 1.5 pts of operating margin if fares and capacity do not respond. That is an upper bound, not a forecast.')
    c3 = [hh('What to watch next')] + bp('Q4 2026 fuel share of revenue, and whether operating margin falls back toward the FY2022 level (7.2%).') \
        + bp('CASM-Ex: whether unit cost keeps rising faster than adjusted TRASM, which would keep squeezing the unit margin gap.') \
        + bp('The cushion: Debt/EBITDA at 1.7x and coverage at 8.6x leave room to absorb a fuel shock, but liquidity is $4.3B at FY2025 year-end (excluding the undrawn revolver), well below $11.3B in FY2021.')
    def big(num, cap, col):
        return card_box([para(run(num, '30pt', col, bold=True)), para(run(cap, '12pt', T['muted']))], cap)
    kx = [24, 502, 980, 1458]; kw = 438
    page(P['concl'], '3 Conclusion', HDR('Conclusion: the margin gain was fuel, and fuel is turning', 'What the analysis shows, what it means, and what would change the view.') + [
        ('k1', rect(kx[0], 108, kw, 112), big('+7.2 pts', 'Margin from lower fuel share of revenue (FY22 to FY25)', T['gold'])),
        ('k2', rect(kx[1], 108, kw, 112), big('-5.3 pts', 'Given back through labor and other costs', T['red'])),
        ('k3', rect(kx[2], 108, kw, 112), big('6.68 to 5.70', 'Unit margin gap, cents per ASM (FY22 to FY25)', T['text'])),
        ('k4', rect(kx[3], 108, 438, 112), big('6.9x to 1.7x', 'Debt / EBITDA (FY21 to FY25)', T['blue'])),
        ('c1', rect(24, 236, 600, 540), card_box(c1, 'Key findings.')),
        ('c2', rect(660, 236, 600, 540), card_box(c2, 'What the findings mean.')),
        ('c3', rect(1296, 236, 600, 540), card_box(c3, 'What to watch next.')),
        ('bottom', rect(24, 792, 1872, 236), card_box([para(run('Bottom line', '18pt', T['red'], bold=True)), para(run(' ', '8pt')), para(run("Delta's profit improvement came mostly from cheaper fuel, not from a better cost or unit-revenue position. Its lasting gain is a much stronger balance sheet, and that is what cushions the 2026 fuel reversal.", '24pt', T['text'], bold=True))], 'Bottom line of the analysis.')),
    ], 'concl')
    # page 3: method
    import re
    h = lambda t: para(run(t, '16pt', T['red'], bold=True))
    def b(t):
        out = []
        for sent in re.split(r'(?<=\.)\s+(?=[A-Z])', t):
            out += [para(run(sent, '13pt', T['text'])), para(run(' ', '6pt'))]
        return out
    gap = lambda: [para(run(' ', '10pt'))]
    paras = [h('Data')] + b('SEC EDGAR XBRL company facts (10-K, 10-Q) for Delta, United, American and Southwest; Delta operating statistics (ASM, RPM, TRASM, CASM-Ex) from earnings-release statistical summaries. Quarterly values are derived from year-to-date filings (Q2 = 6M - 3M, Q3 = 9M - 6M, Q4 = FY - 9M).') + gap() \
        + [h('Definitions')] + b('EBITDA = operating income + D&A. Total debt = long-term debt + finance leases. Liquidity = cash + short-term investments (excludes undrawn revolver). Coverage = operating income / interest expense. FCF = operating cash flow - capex.') + gap() \
        + [h('Stress test')] + b('Margin at shock = FY2025 operating margin - (FY2025 fuel share of revenue x shock %). It assumes no fare or capacity response, so it is an upper bound on the damage, not a forecast.') + gap() \
        + [h('Limitations')] + b('Interest data missing for some airlines in 2021 and quarterly 2021-2023; Delta capex Q2-Q3 2026 blank in the source. Operating statistics cover Delta only. Not investment advice.') + gap() \
        + [h('Author')] + b('Dao Gia Nam (Nathan Dao)') + b('Independent analysis based on public filings. Not affiliated with or endorsed by Delta Air Lines. Delta name, logo and aircraft photos belong to their owners.')
    page(P['method'], '4 Method & limits', logo_v + [
        ('title', rect(24, 16, 1400, 84), title_box('Method & limits', 'Data, definitions and what this analysis does not claim.')),
        ('method', rect(24, 108, 1100 if PLANE else 1872, 920), card_box(paras, 'Method, definitions and limitations.')),
    ] + ([('plane', rect(1140, 108, 756, 452), img(os.path.basename(PLANE), 'Delta Air Lines aircraft landing', 'Fill'))] if PLANE else []) + ([('plane2', rect(1140, 576, 756, 452), img(os.path.basename(PLANE2), 'Delta Air Lines Airbus in flight', 'Fill'))] if PLANE2 else []), 'method')
    wj(os.path.join(RP, 'definition', 'pages', 'pages.json'), {'$schema': S_PAGES, 'pageOrder': [P[k] for k in ('thesis', 'deep', 'concl', 'method')], 'activePageName': P['thesis']})

def build_pbip():
    wj(os.path.join(ROOT, NAME + '.pbip'), {"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0", "artifacts": [{"report": {"path": NAME + ".Report"}}], "settings": {"enableAutoRecovery": True}})
    w(os.path.join(ROOT, '.gitignore'), '**/.pbi/localSettings.json\n**/.pbi/cache.abf\n')

if __name__ == '__main__':
    build_model(); build_report(); build_pbip()
    print('built', NAME)
