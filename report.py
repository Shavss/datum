"""
report.py - the partner-facing deliverable.

run.py is the analyst's view: a console dump and 26 standalone figures. This is
the document a managing partner reads in twenty minutes. It assembles the six
figures that carry the argument and the live numbers behind them into one
self-contained HTML file, with the decision on the first page and the method and
the honesty-of-inputs split at the back.

    python report.py                        # default (dummy) data
    python report.py example_client/inputs.yaml

Writes datum_report.html. Open it in a browser and Print to PDF for the handover
copy. No new dependency: the figures are embedded as base64 so the file travels
as one artefact. Every number is read from the same engine run.py uses, so the
report is real the moment a real timesheet replaces the dummy one.
"""
import base64
import datetime as _dt
import html as _html
import sys

import theme
import bernstein as B
import rnm
import cost as C
import inputs as _inp
import views
from model import task_catalogue, task_future


def _b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _gbp(x):
    return f"&pound;{x:,.0f}"


def _pct(x, dp=0):
    return f"{x*100:.{dp}f}%"


# ---- the numbers, read from the engine -------------------------------------
def gather(cat):
    """Everything the narrative needs, computed once from the live engine."""
    rows = C.by_stage()
    base_cost = sum(r["cost"] for r in rows)
    total_hours = sum(r["hours"] for r in rows)
    t = C.totals()
    cv = C.conversion()

    routine = sum(r["effort"] for r in cat if r["auto"] >= 0.875)
    oversight = sum(r["effort"] for r in cat if 0.625 <= r["auto"] < 0.875)
    nonroutine = sum(r["effort"] for r in cat if r["auto"] < 0.375)
    middle = 1 - routine - oversight - nonroutine

    cur, fut = task_future(cat, 0.7)
    eff = {r["task"]: r["effort"] for r in cat}
    fut_by = {r["task"]: f for r, f in zip(cat, fut)}

    labels, k = rnm.grouping(rnm.ADJACENCIES["class"]())
    prof = rnm.cluster_profile(labels)
    order = sorted(prof, key=lambda c: -prof[c]["mean_auto"])
    role = ["Automate", "Augment", "Protect"]
    blocks = []
    for i, c in enumerate(order):
        members = prof[c]["members"]
        blocks.append(dict(
            name=role[i] if i < len(role) else f"block {c}",
            mean_auto=prof[c]["mean_auto"],
            effort=sum(eff[m] for m in members),
            freed=sum(eff[m] - fut_by[m] for m in members),
            members=members))

    return dict(
        rows=rows, base_cost=base_cost, total_hours=total_hours,
        totals=t, conversion=cv, adoption=C.ADOPTION,
        split=dict(routine=routine, oversight=oversight, middle=middle,
                   nonroutine=nonroutine),
        freed_frac=(cur.sum() - fut.sum()),
        blocks=blocks, labels=labels, k=k,
        warnings=getattr(C.INPUTS, "warnings", []), source=C.INPUTS.source)


# ---- the figures the partner sees ------------------------------------------
def key_figures(cat, g):
    """The six that carry the story, in narrative order, each with its caption."""
    return [
        (views.fig_opportunity_map(cat, g["labels"], g["k"]),
         "Where AI helps. Tasks placed by how automatable they are against how "
         "much effort they carry, grouped into the three blocks the firm's own "
         "data separates into: Automate, Augment, Protect."),
        (views.fig_readiness_map(),
         "Whether the tooling is there yet. The opportunity is only real where "
         "capable tooling already runs on project data; the rest is watch-and-wait "
         "or needs the firm's data in order first."),
        (views.fig_cost_saved(),
         "The measured cost base by stage (hours times band cost rate) and the "
         "releasable capacity on top. The cost base is arithmetic on the firm's "
         "timesheet; the released fraction is the labelled projection."),
        (views.fig_savings_bands(),
         "The business case as a band, never a single number: capacity released "
         "under low, expected and high adoption."),
        (views.fig_capacity_conversion(),
         "Released hours are not money until converted. The margin route avoids "
         "salary cost and needs fewer hours; the growth route re-sells the freed "
         "time as fee and needs a pipeline. Doing neither reabsorbs the time."),
        (views.fig_roadmap(),
         "The sequenced roadmap: act now where capable tooling runs on project "
         "data, watch where the value or the tooling is not there yet, and build "
         "foundations where the AI needs the firm's own data in order first."),
    ]


# ---- HTML assembly ---------------------------------------------------------
CSS = """
:root{--ink:#1a202c;--accent:#2b6cb0;--muted:#718096;--soft:#bee3f8;--grid:#e2e8f0;}
*{box-sizing:border-box;}
body{font-family:Georgia,'Times New Roman',serif;color:var(--ink);max-width:820px;
 margin:0 auto;padding:56px 48px;line-height:1.55;font-size:15px;}
h1{font-size:30px;margin:0 0 4px;letter-spacing:-.5px;}
h2{font-size:20px;margin:44px 0 6px;padding-top:18px;border-top:2px solid var(--grid);
 letter-spacing:-.3px;}
h3{font-size:15px;margin:22px 0 4px;color:var(--accent);font-variant:small-caps;
 letter-spacing:.4px;}
.sub{color:var(--muted);font-size:14px;margin:0 0 6px;}
.lead{font-size:16px;}
figure{margin:18px 0 6px;}
figure img{width:100%;border:1px solid var(--grid);border-radius:4px;}
figcaption{color:var(--muted);font-size:13px;margin-top:6px;font-style:italic;}
.decision{background:#f7fafc;border:1px solid var(--grid);border-left:4px solid var(--accent);
 border-radius:4px;padding:18px 22px;margin:18px 0;}
.kpis{display:flex;flex-wrap:wrap;gap:14px;margin:16px 0;}
.kpi{flex:1 1 150px;background:#f7fafc;border:1px solid var(--grid);border-radius:4px;
 padding:14px 16px;}
.kpi .n{font-size:24px;font-weight:bold;color:var(--accent);display:block;}
.kpi .l{font-size:12px;color:var(--muted);}
table{border-collapse:collapse;width:100%;font-size:13px;margin:14px 0;
 font-family:'Helvetica Neue',Arial,sans-serif;}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--grid);}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.4px;}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;}
.tag{display:inline-block;font-size:11px;font-family:'Helvetica Neue',Arial,sans-serif;
 padding:1px 7px;border-radius:3px;font-weight:600;}
.measured{background:#c6f6d5;color:#22543d;}
.elicited{background:#feebc8;color:#7b341e;}
.book{background:#bee3f8;color:#2a4365;}
.warn{background:#fff5f5;border:1px solid #fed7d7;color:#822727;padding:8px 14px;
 border-radius:4px;font-size:13px;margin:6px 0;}
.foot{color:var(--muted);font-size:12px;margin-top:48px;border-top:1px solid var(--grid);
 padding-top:14px;}
@media print{body{padding:0;max-width:none;}h2{break-before:auto;}figure{break-inside:avoid;}}
"""


def _block_table(blocks):
    head = ("<tr><th>Block</th><th class=n>Mean automatability</th>"
            "<th class=n>Share of effort</th><th class=n>Frees at 70%</th></tr>")
    body = "".join(
        f"<tr><td><b>{_html.escape(b['name'])}</b></td>"
        f"<td class=n>{b['mean_auto']:.2f}</td>"
        f"<td class=n>{_pct(b['effort'])}</td>"
        f"<td class=n>{_pct(b['freed'])}</td></tr>" for b in blocks)
    return f"<table>{head}{body}</table>"


def _cost_table(g):
    head = ("<tr><th>RIBA stage</th><th class=n>Hours</th><th class=n>Cost</th>"
            "<th class=n>Releasable</th></tr>")
    body = "".join(
        f"<tr><td>{_html.escape(r['stage'])}</td>"
        f"<td class=n>{r['hours']:,.0f}</td><td class=n>{_gbp(r['cost'])}</td>"
        f"<td class=n>{_pct(r['saved_frac'])}</td></tr>" for r in g["rows"])
    foot = (f"<tr><td><b>Total</b></td><td class=n><b>{g['total_hours']:,.0f}</b></td>"
            f"<td class=n><b>{_gbp(g['base_cost'])}</b></td><td class=n></td></tr>")
    return f"<table>{head}{body}{foot}</table>"


def _scenario_table(g):
    head = ("<tr><th>Adoption</th><th class=n>Rate</th><th class=n>Hours released</th>"
            "<th class=n>Salaried cost</th><th class=n>% of base</th></tr>")
    rows = ""
    for k in ("low", "expected", "high"):
        d = g["totals"][k]
        rows += (f"<tr><td>{k.title()}</td><td class=n>{_pct(g['adoption'][k])}</td>"
                 f"<td class=n>{d['saved_hours']:,.0f}</td>"
                 f"<td class=n>{_gbp(d['saved_cost'])}</td>"
                 f"<td class=n>{_pct(d['saved_cost']/d['cost'])}</td></tr>")
    return f"<table>{head}{rows}</table>"


def build_html(cat, g, figs):
    s, cv = g["split"], g["conversion"]
    exp = g["totals"]["expected"]
    warn_html = "".join(
        f"<div class=warn>Data note: {_html.escape(w)}</div>" for w in g["warnings"])
    fig_blocks = "".join(
        f"<figure><img src='data:image/png;base64,{_b64(p)}'>"
        f"<figcaption>{_html.escape(cap)}</figcaption></figure>"
        for p, cap in figs)

    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<title>Datum diagnostic</title><style>{CSS}</style></head><body>

<h1>AI workflow diagnostic</h1>
<p class=sub>Prepared with Datum &nbsp;&middot;&nbsp; data source: {_html.escape(g['source'])}
 &nbsp;&middot;&nbsp; {_dt.date.today():%d %B %Y}</p>
{warn_html}

<div class=decision>
<p class=lead style="margin-top:0"><b>The decision.</b> The measured cost base across
the priority stages is <b>{_gbp(g['base_cost'])}</b> a year over {g['total_hours']:,.0f}
booked hours. At expected adoption the work could be delivered with about
<b>{exp['saved_hours']:,.0f} fewer hours</b>, worth <b>{_gbp(exp['saved_cost'])}</b> of
salaried capacity ({_pct(exp['saved_cost']/exp['cost'])} of the base). That capacity is
hours, not money. It books value only through the margin route ({_gbp(cv['margin_value'])}
of cost avoided) or the growth route ({_gbp(cv['growth_value'])} of extra fee). The
question this diagnostic puts to the partnership is which route to take, and in what
order to act.</p>
</div>

<div class=kpis>
<div class=kpi><span class=n>{_gbp(g['base_cost'])}</span><span class=l>measured cost base / year</span></div>
<div class=kpi><span class=n>{_pct(s['routine']+s['oversight'])}</span><span class=l>effort that is automatable (with oversight)</span></div>
<div class=kpi><span class=n>{_pct(s['nonroutine'])}</span><span class=l>judgement work to protect</span></div>
<div class=kpi><span class=n>{_pct(g['freed_frac'])}</span><span class=l>redeployable capacity at 70% adoption</span></div>
</div>

<h2>1 &nbsp; Where AI helps</h2>
<p>The firm's work is classified against Phil Bernstein's task framework
(<span class="tag book">read from the book</span> <i>Machine Learning: Architecture in
the Age of AI</i>, RIBA 2022) and grouped by how automatable it is. The grouping is not
imposed: it is derived from the firm's own task grid, and the data separates the practice
into three blocks rather than five.</p>
{_block_table(g['blocks'])}
<p>Roughly {_pct(s['routine'])} of effort is straightforwardly automatable, a further
{_pct(s['oversight'])} is automatable with human oversight, {_pct(s['middle'])} sits in the
augmentable middle, and {_pct(s['nonroutine'])} is judgement work to protect. The two
automatable figures are kept separate on purpose: collapsing them overstates what AI can
safely take on.</p>
{fig_blocks.split('</figure>')[0]}</figure>

<h2>2 &nbsp; Whether the tooling is ready</h2>
<p>Being automatable in principle is not the same as having tooling that works on the
firm's projects today. The readiness map separates the opportunity that is live now from
the opportunity that waits on better tooling or on the firm's own data.</p>
{fig_blocks.split('</figure>')[1]}</figure>

<h2>3 &nbsp; The measured cost base</h2>
<p>Cost per stage is hours times band cost rate, summed over the people who booked to the
stage. <span class="tag measured">measured</span> This is arithmetic on the firm's
timesheet, not a model.</p>
{_cost_table(g)}
{fig_blocks.split('</figure>')[2]}</figure>

<h2>4 &nbsp; The business case, as a band</h2>
<p>The releasable fraction of each stage is automatability times tool autonomy, taken up
by an adoption rate. <span class="tag elicited">elicited</span> Autonomy and adoption are
elicited in the workshop, so the case is reported as a band under low, expected and high
adoption, never as a single number.</p>
{_scenario_table(g)}
{fig_blocks.split('</figure>')[3]}</figure>

<h2>5 &nbsp; The conversion decision</h2>
<p>Released capacity is hours. It becomes value only through one of two routes, each with a
precondition.</p>
<div class=kpis>
<div class=kpi><span class=n>{_gbp(cv['margin_value'])}</span><span class=l>Margin route: salary cost avoided. Needs fewer hours booked. In the firm's control.</span></div>
<div class=kpi><span class=n>{_gbp(cv['growth_value'])}</span><span class=l>Growth route: freed time re-sold as fee. Worth more per hour, needs a pipeline.</span></div>
</div>
{fig_blocks.split('</figure>')[4]}</figure>

<h2>6 &nbsp; The sequenced roadmap</h2>
<p>What to do, and in what order. The honest conclusion is that the cognitive and agentic
tooling, the upper rungs with the most value, run on the firm's own structured data. The
firm cannot reach them without that data in a usable state, which is where the
needs-foundations lane and the data-readiness recommendation begin.</p>
{fig_blocks.split('</figure>')[5]}</figure>

<h2>Method and the honesty of inputs</h2>
<p>Three kinds of input go into this diagnostic, and the report states which is which
throughout.</p>
<p><span class="tag measured">measured</span> The cost base and the effort shares come from
the firm's timesheet and salary-cost band rates. These are arithmetic, not estimates.</p>
<p><span class="tag book">read from the book</span> The task classes and the proposed AI
applications come from Bernstein's published framework, so they carry his reasoning and
should be checked against the source.</p>
<p><span class="tag elicited">elicited</span> The tool autonomy, the adoption bands and the
work-flow between stages are elicited in a workshop. This is structured judgement made
comparable, which is the method working as intended, not a gap in it.</p>
<p>The classification sits under Bernstein's task framework; the grouping and the systemic
analysis use Eber's platform-oriented management (Cross-Impact higher order and
equilibrium). Freed capacity is always reported as redeployable into non-routine work, not
as a fee saving, to stay clear of the productivity-fee trap.</p>

<p class=foot>Datum &middot; quantitative workflow diagnostic for architecture and
engineering practices. Figures and numbers generated from the engine on
{_dt.date.today():%d %B %Y}. Data source: {_html.escape(g['source'])}. This is a structured
AI-readiness diagnostic; the soft inputs are elicited and labelled as such.</p>
</body></html>"""


def main():
    if len(sys.argv) > 1:
        C.set_inputs(_inp.load_inputs(sys.argv[1]))
    theme.apply_theme()
    cat = task_catalogue()
    g = gather(cat)
    figs = key_figures(cat, g)
    html = build_html(cat, g, figs)
    out = "datum_report.html"
    with open(out, "w") as f:
        f.write(html)
    print(f"wrote {out}  (data source: {g['source']})")
    print(f"  measured cost base: GBP {g['base_cost']/1e6:.2f}M/year")
    print(f"  released at expected adoption: {g['totals']['expected']['saved_hours']:,.0f} h")
    print(f"  open in a browser and Print to PDF for the handover copy")


if __name__ == "__main__":
    main()
