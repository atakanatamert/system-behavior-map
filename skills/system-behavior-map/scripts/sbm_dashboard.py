#!/usr/bin/env python3
"""Iceberg dashboard for the system-behavior-map skill:
events -> behaviour over time -> structure -> mental models -> questions.

Usage:
    python3 -I sbm_dashboard.py data.json content.json out.html [stocks.svg loops.svg]

data.json    : output of sbm_extract.py
content.json : curated text (see templates/sbm_content.example.json)
Series keys available to charts: everything in data.json rows, plus derived
  src_kb:<component>, test_kb:<component>, md_kb:<component>, test_share:<component>,
  code_kb (all components), docs_kb (all markdown), added_deleted_ratio
"""
import json, sys, html, datetime as dt, re

data, content = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
out = sys.argv[3]
svg_stocks = open(sys.argv[4]).read() if len(sys.argv) > 4 else ""
svg_loops = open(sys.argv[5]).read() if len(sys.argv) > 5 else ""
S = data["series"]
REF = content.get("reference_date", S[0]["date"])
for s in S:  # derived series
    c = s["components"]; code = docs = 0
    for name in sorted(set(data.get("components", [])) | set(c)):
        v = c.get(name, {})
        s[f"src_kb:{name}"] = v.get("src", 0) / 1000; s[f"test_kb:{name}"] = v.get("test", 0) / 1000
        s[f"md_kb:{name}"] = v.get("md", 0) / 1000
        s[f"test_share:{name}"] = v.get("test", 0) / max(1, v.get("src", 0) + v.get("test", 0))
        code += v.get("src", 0) + v.get("test", 0); docs += v.get("md", 0)
    s["code_kb"], s["docs_kb"] = code / 1000, docs / 1000
    s["added_deleted_ratio"] = s["added"] / max(1, s["deleted"])
D = lambda s: dt.date.fromisoformat(s)
t0, t1 = D(S[0]["date"]), D(S[-1]["date"])
span = (t1 - t0).days
esc = html.escape

def inline_svg(svg, cls):
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = re.sub(r'(<svg[^>]*?)\swidth="[^"]*"\sheight="[^"]*"', r"\1", svg, count=1)
    return svg.replace("<svg ", f'<svg class="{cls}" ', 1)

# ---------- charts ----------
W, H, ML, MR, MT, MB = 300, 132, 38, 14, 10, 20
PW, PH = W - ML - MR, H - MT - MB
def xpos(d): return ML + PW * (D(d) - t0).days / span
def fmt(v, pct=False):
    if pct: return f"{v*100:.0f}%"
    if v >= 10000: return f"{v/1000:.1f}k"
    if v >= 1000: return f"{v:,.0f}"
    return f"{v:.0f}" if float(v).is_integer() else f"{v:.1f}"

def chart(c):
    k1, k2, pct = c["key"], c.get("key2"), c.get("pct", False)
    ys = [s[k1] for s in S] + ([s[k2] for s in S] if k2 else [])
    ymax = max(ys) or 1
    ypos = lambda v: MT + PH - PH * v / ymax
    g = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="{esc(c["title"])}">']
    # gridlines: 2 hairlines
    for f in (0.5, 1.0):
        y = ypos(ymax * f); g.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML+PW}" y2="{y:.1f}" class="grid"/>')
        g.append(f'<text x="{ML-4}" y="{y+4:.1f}" class="tick" text-anchor="end">{fmt(ymax*f, pct)}</text>')
    g.append(f'<line x1="{ML}" y1="{MT+PH}" x2="{ML+PW}" y2="{MT+PH}" class="axis"/>')
    for m in content["structural_markers"]:
        x = xpos(m); g.append(f'<line x1="{x:.1f}" y1="{MT}" x2="{x:.1f}" y2="{MT+PH}" class="marker"/>')
    # x ticks: month starts
    d = dt.date(t0.year, t0.month, 1)
    while d <= t1:
        if d >= t0 and d.month in (1, 4, 7, 10):
            g.append(f'<text x="{xpos(d.isoformat()):.1f}" y="{H-6}" class="tick" text-anchor="middle">{d.strftime("%b %y")}</text>')
        d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    def series(key, cls, label):
        pts = [(xpos(s["date"]), ypos(s[key])) for s in S]
        if c["form"] == "bar":
            bw = max(2, min(6, PW / len(S) - 1.5))
            for (x, y), s in zip(pts, S):
                hgt = MT + PH - y
                g.append(f'<rect x="{x-bw/2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{hgt:.1f}" rx="1.5" class="{cls}"><title>{s["date"]}: {fmt(s[key])} {esc(c["unit"])}</title></rect>')
        else:
            path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            g.append(f'<path d="{path}" class="{cls} line"/>')
            for (x, y), s in zip(pts, S):
                g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" class="hit"><title>{s["date"]}: {fmt(s[key], pct)}{"" if pct else " " + esc(c["unit"])}{(" · " + label) if label else ""}</title></circle>')
            x, y = pts[-1]; g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" class="{cls} dot"/>')
            if label:
                dy = -6 if cls == "s1" else 12
                g.append(f'<text x="{x-6:.1f}" y="{y+dy:.1f}" class="dl" text-anchor="end">{esc(label)}</text>')
    series(k1, "s1", c.get("label1") if k2 else None)
    if k2: series(k2, "s2", c.get("label2"))
    g.append("</svg>")
    last = S[-1][k1]
    aug = next((s for s in S if s["date"] >= REF), S[0])
    if c["form"] == "bar":
        head, sub = fmt(sum(s[k1] for s in S)), "total; peak " + fmt(max(s[k1] for s in S)) + " in a week"
    else:
        delta = last - aug[k1]
        head = fmt(last, pct); sub = f"{'+' if delta >= 0 else '−'}{fmt(abs(delta), pct)} since {REF[5:]}"
        if k2 and not pct:
            a = sum(s[k1] for s in S if s["date"] >= REF); b = sum(s[k2] for s in S if s["date"] >= REF)
            head = f"{a/max(1,b):.1f}:1"; sub = f"{fmt(a)} {c.get('label1')} : {fmt(b)} {c.get('label2')}, since {REF[5:]}"
        if k2 and pct: head = f"{fmt(last, True)} / {fmt(S[-1][k2], True)}"; sub = f"{c.get('label1')} / {c.get('label2')}"
    return f'''<figure class="tile">
  <figcaption><span class="t">{esc(c["title"])}</span><span class="u">{esc(c["unit"])}</span></figcaption>
  <div class="head"><span class="n">{head}</span><span class="d">{esc(sub)}</span></div>
  {"".join(g)}
  <p class="read">{esc(c["reading"])}</p>
</figure>'''

# ---------- timeline ----------
def timeline():
    TW, TH, TL, TR = 1160, 110, 30, 30
    tx = lambda d: TL + (TW - TL - TR) * (D(d) - t0).days / span
    ev = sorted(content["events"], key=lambda e: e["date"])
    g = [f'<svg viewBox="0 0 {TW} {TH}" class="timeline" role="img" aria-label="Events">']
    base = 80
    g.append(f'<line x1="{TL}" y1="{base}" x2="{TW-TR}" y2="{base}" class="axis"/>')
    d = dt.date(t0.year, t0.month, 1)
    while d <= t1:
        if d >= t0:
            x = tx(d.isoformat()); g.append(f'<line x1="{x:.1f}" y1="{base-3}" x2="{x:.1f}" y2="{base+3}" class="axis"/>')
            if d.month % 2 == 0: g.append(f'<text x="{x:.1f}" y="{base+16}" class="tick" text-anchor="middle">{d.strftime("%b %y")}</text>')
        d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    # numbered marks; crowded dates stagger upward
    lastx = -999; lift = 0
    for i, e in enumerate(ev, 1):
        x = tx(e["date"])
        lift = (lift + 1) % 3 if x - lastx < 22 else 0
        lastx = x
        y = base - lift * 22
        if lift: g.append(f'<line x1="{x:.1f}" y1="{base}" x2="{x:.1f}" y2="{y+7}" class="stem"/>')
        shape = (f'<rect x="{x-8:.1f}" y="{y-8}" width="16" height="16" rx="2" transform="rotate(45 {x:.1f} {y})" class="ev-structure"/>'
                 if e["kind"] == "structure" else f'<circle cx="{x:.1f}" cy="{y}" r="9" class="ev-event"/>')
        g.append(f'<g class="ev">{shape}<text x="{x:.1f}" y="{y+3.5}" class="evn" text-anchor="middle">{i}</text><title>{e["date"]} — {esc(e["label"])}\n{esc(e["detail"])}</title></g>')
    g.append("</svg>")
    items = "".join(f'<li><span class="n {e["kind"]}">{i}</span><span class="dt">{e["date"][5:]}</span> {esc(e["label"])}</li>' for i, e in enumerate(ev, 1))
    return "".join(g) + f'<ol class="evlist">{items}</ol>'

loops_html = "".join(f'<li><span class="chip {l["kind"]}">{l["id"]}</span><b>{esc(l["name"])}</b> <span class="path">{esc(l["path"])}</span><span class="st">{esc(l["status"])}</span></li>' for l in content["loops"])
mm_html = "".join(f'<tr><td class="b">{esc(m["belief"])}</td><td class="ev">{esc(m["evidence"])}</td><td>{esc(m["note"])}</td></tr>' for m in content["mental_models"])
lev_html = "".join(f'<li class="{"hi" if hi else ""}"><span class="num">{n}</span><b>{esc(name)}</b><span>{esc(what)}</span></li>' for n, name, what, hi in content["leverage"])
q_html = "".join(f"<li>{esc(q)}</li>" for q in content["questions"])
ev_rows = "".join(f'<tr><td>{e["date"]}</td><td>{"◆" if e["kind"]=="structure" else "●"}</td><td>{esc(e["label"])}</td><td>{esc(e["detail"])}</td></tr>' for e in content["events"])
charts_html = "".join(chart(c) for c in content["charts"])
diagrams_html = ""
if svg_stocks or svg_loops:
    diagrams_html = ('<div class="tabs">'
        '<input type="radio" name="dg" id="dg1" checked><label for="dg1">Stocks and flows</label>'
        '<input type="radio" name="dg" id="dg2"><label for="dg2">Causal loops</label>'
        f'<div class="pane" id="p1">{inline_svg(svg_stocks, "diagram") if svg_stocks else ""}</div>'
        f'<div class="pane" id="p2">{inline_svg(svg_loops, "diagram") if svg_loops else ""}</div></div>')
last = S[-1]

page = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(content["title"])}</title>
<style>
:root{{color-scheme:light;--surface:#fcfcfb;--surface-2:#f3f2ee;--line:#e4e2dc;--ink:#0b0b0b;--ink-2:#52514e;--ink-3:#8a8880;--s1:#2a78d6;--s2:#eb6834;--r:#8b1a1a;--b:#1f4e79;--mark:#c9c6bd}}
@media (prefers-color-scheme:dark){{:root{{color-scheme:dark;--surface:#1a1a19;--surface-2:#242422;--line:#363632;--ink:#f0efec;--ink-2:#c3c2b7;--ink-3:#8f8e85;--s1:#3987e5;--s2:#d95926;--r:#c94b4b;--b:#4f86bd;--mark:#4a4944}}
 .diagram{{filter:invert(.92) hue-rotate(180deg)}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--surface);color:var(--ink);font:14px/1.45 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}}
main{{max-width:1200px;margin:0 auto;padding:20px}}
h1{{font-size:22px;margin:0 0 4px}}.sub{{color:var(--ink-2);margin:0 0 6px;max-width:900px}}.meta{{color:var(--ink-3);font-size:12px;margin:0 0 18px}}
section{{border-top:1px solid var(--line);padding:16px 0 8px}}
.layer{{display:flex;align-items:baseline;gap:12px;margin:0 0 10px}}.layer h2{{font-size:15px;margin:0;white-space:nowrap;text-transform:uppercase;letter-spacing:.04em}}.layer .q{{color:var(--ink-2);font-size:13px}}
.depth{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;background:var(--s1);opacity:var(--o,1);vertical-align:-1px}}
svg{{display:block;width:100%;height:auto}}
.timeline .axis,.chart .axis{{stroke:var(--ink-3);stroke-width:1}}.stem{{stroke:var(--line);stroke-width:1}}
.ev-event{{fill:var(--ink)}}.ev-structure{{fill:var(--s1)}}.ev:hover rect,.ev:hover circle{{stroke:var(--ink);stroke-width:2}}
.evn{{font-size:10px;font-weight:700;fill:#fff;pointer-events:none}}.timeline{{max-height:120px}}ol.evlist{{list-style:none;margin:6px 0 0;padding:0;columns:4;column-gap:18px;font-size:12px}}ol.evlist li{{break-inside:avoid;padding:2px 0;display:flex;gap:6px;align-items:baseline}}ol.evlist .n{{flex:none;display:inline-block;width:18px;height:18px;line-height:18px;border-radius:50%;text-align:center;color:#fff;font-size:10px;font-weight:700;background:var(--ink)}}ol.evlist .n.structure{{background:var(--s1);border-radius:3px}}ol.evlist .dt{{color:var(--ink-3);font-family:ui-monospace,Menlo,monospace;font-size:10.5px;flex:none}}.tick{{font-size:10px;fill:var(--ink-3)}}
.legend{{font-size:12px;color:var(--ink-2);display:flex;gap:18px;flex-wrap:wrap;margin:2px 0 0}}.legend i{{display:inline-block;width:9px;height:9px;margin-right:5px;vertical-align:-1px}}
.legend .c{{border-radius:50%;background:var(--ink)}}.legend .d{{transform:rotate(45deg);background:var(--s1)}}.legend .m{{width:2px;height:12px;background:var(--mark);vertical-align:-2px}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}@media(max-width:900px){{.grid{{grid-template-columns:repeat(2,1fr)}}}}
.tile{{margin:0;padding:10px 10px 6px;background:var(--surface-2);border-radius:6px}}
.tile figcaption{{display:flex;justify-content:space-between;align-items:baseline;gap:6px}}.tile .t{{font-weight:600;font-size:13px}}.tile .u{{color:var(--ink-3);font-size:11px;text-align:right}}
.tile .head{{display:flex;align-items:baseline;gap:8px;margin:2px 0 2px}}.tile .n{{font-size:22px;font-weight:600;letter-spacing:-.01em}}.tile .d{{color:var(--ink-2);font-size:11.5px}}
.chart .grid{{stroke:var(--line);stroke-width:1}}.chart .marker{{stroke:var(--mark);stroke-width:1.5}}
.s1{{fill:var(--s1);stroke:var(--s1)}}.s2{{fill:var(--s2);stroke:var(--s2)}}.line{{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}}.dot{{stroke:var(--surface-2);stroke-width:2}}
.hit{{fill:transparent;stroke:none}}.hit:hover{{fill:var(--ink);fill-opacity:.12}}.dl{{font-size:10px;fill:var(--ink-2)}}
.read{{margin:4px 0 0;font-size:12px;color:var(--ink-2)}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}@media(max-width:900px){{.two{{grid-template-columns:1fr}}}}
.diagram{{border:1px solid var(--line);border-radius:6px;background:#fff;max-width:1000px;margin:0 auto}}.tabs input{{position:absolute;opacity:0;pointer-events:none}}.tabs label{{display:inline-block;padding:4px 12px;border:1px solid var(--line);border-radius:14px;font-size:12.5px;color:var(--ink-2);cursor:pointer;margin:0 6px 8px 0}}.tabs input:checked+label{{background:var(--ink);color:var(--surface);border-color:var(--ink)}}.pane{{display:none}}#dg1:checked~#p1,#dg2:checked~#p2{{display:block}}
ul.loops{{list-style:none;padding:0;margin:0;columns:2;column-gap:24px}}ul.loops li{{break-inside:avoid;padding:4px 0;font-size:13px}}
.chip{{display:inline-block;color:#fff;font-weight:700;font-size:11px;border-radius:50%;width:26px;height:26px;line-height:26px;text-align:center;margin-right:8px}}.chip.R{{background:var(--r)}}.chip.B{{background:var(--b)}}
.path{{color:var(--ink-2);margin-left:6px}}.st{{display:block;color:var(--ink-3);font-size:11.5px;margin-left:34px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:5px 8px;border-top:1px solid var(--line);vertical-align:top;text-align:left}}td.b{{font-weight:600;width:34%}}td.ev{{color:var(--ink-3);font-family:ui-monospace,Menlo,monospace;font-size:11.5px;width:26%}}
ol.lev{{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(11,1fr);gap:4px}}ol.lev li{{background:var(--surface-2);border-radius:4px;padding:6px;font-size:11px;min-height:96px}}ol.lev li.hi{{outline:2px solid var(--s2)}}
ol.lev .num{{display:block;color:var(--ink-3);font-size:10px}}ol.lev b{{display:block;margin:2px 0}}ol.lev span:last-child{{color:var(--ink-2)}}
ol.q{{margin:0;padding-left:20px;columns:2;column-gap:28px}}ol.q li{{break-inside:avoid;margin:0 0 6px;font-size:13px}}
details{{margin:8px 0}}summary{{cursor:pointer;color:var(--ink-2);font-size:13px}}
.hyp{{background:var(--surface-2);border-left:3px solid var(--s2);padding:8px 12px;margin:10px 0 0;font-size:13px}}
footer{{color:var(--ink-3);font-size:11.5px;padding:14px 0}}
</style></head><body><main>
<h1>{esc(content["title"])}</h1>
<p class="sub">{esc(content["subtitle"])}</p>
<p class="meta">Repo at <code>{data["head"]}</code> · {S[-1]["date"]} · {len(S)} weekly snapshots from git history · all numbers [seen] unless marked [inferred] · hover any mark for the detail</p>

<section>
 <div class="layer"><h2><span class="depth" style="--o:.35"></span>1 · Events</h2><span class="q">What happened? The visible surface. ◆ a rule, loop or boundary changed · ● something happened</span></div>
 {timeline()}
 <details><summary>All {len(content["events"])} events with their evidence</summary><table>{ev_rows}</table></details>
</section>

<section>
 <div class="layer"><h2><span class="depth" style="--o:.6"></span>2 · Behaviour over time</h2><span class="q">What patterns? Weekly snapshots, {S[0]["date"]} → {S[-1]["date"]}. {esc(content.get("markers_caption", "Vertical marks: the structural events."))}</span></div>
 <div class="grid">{charts_html}</div>
</section>

<section>
 <div class="layer"><h2><span class="depth" style="--o:.8"></span>3 · Structure</h2><span class="q">Why these patterns? Stocks, flows and the loops that connect them. Solid is [seen]; dashed is [inferred].</span></div>
 {diagrams_html}
 <details open><summary>The eight loops</summary><ul class="loops">{loops_html}</ul></details>
</section>

<section>
 <div class="layer"><h2><span class="depth"></span>4 · Mental models</h2><span class="q">What holds the structure in place? Rules and beliefs the repo embodies, stated or not.</span></div>
 <table><tr><th>Belief or rule</th><th>Where it is written</th><th>What it does</th></tr>{mm_html}</table>
 <p class="q" style="margin:14px 0 6px;color:var(--ink-2)">Leverage points, weakest → strongest (Meadows). Outlined rungs are where this system's behaviour actually comes from.</p>
 <ol class="lev">{lev_html}</ol>
</section>

<section>
 <div class="layer"><h2>Questions the repo cannot answer</h2><span class="q">Each one, if answered, changes what to build next.</span></div>
 <ol class="q">{q_html}</ol>
 <p class="hyp"><b>Hypothesis to test.</b> {esc(content["hypothesis"])}</p>
</section>
<footer>Generated from <code>git ls-tree</code> at the last commit of each ISO week, plus <code>git log --numstat</code> between snapshots. No checkout, read-only. Companion text: SYSTEM_BEHAVIOR.md. Made with the system-behavior-map skill.</footer>
</main></body></html>'''
open(out, "w").write(page)
print("wrote", out, len(page) // 1000, "KB")
