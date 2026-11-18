"""Aurora-glass theme and dependency-free SVG visuals for PromoFinder Studio."""
import math


DIMS = [
    ("Hook", "hook_strength", "#5eead4"),
    ("Cliffhanger", "cliffhanger_strength", "#f472b6"),
    ("Clarity", "standalone_clarity", "#60a5fa"),
    ("Emotion", "emotional_impact", "#fbbf24"),
    ("Flow", "duration_and_flow", "#a78bfa"),
]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Sora:wght@500;600;700;800&display=swap');
:root{--ink:#f1f5ff;--muted:#9aa9c9;--line:rgba(190,210,255,.16);--glass:rgba(20,26,56,.55);
--cyan:#5eead4;--violet:#a78bfa;--pink:#f472b6;--blue:#60a5fa;--amber:#fbbf24;}
html,body,[class*="css"]{font-family:'Manrope',sans-serif;}
[data-testid="stAppViewContainer"]{color:var(--ink);background:#070a18;}
[data-testid="stAppViewContainer"]::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
background:radial-gradient(40% 38% at 12% 8%,rgba(96,165,250,.30),transparent 70%),
radial-gradient(34% 34% at 88% 14%,rgba(244,114,182,.22),transparent 70%),
radial-gradient(38% 40% at 70% 92%,rgba(94,234,212,.18),transparent 70%),
radial-gradient(34% 34% at 6% 88%,rgba(167,139,250,.24),transparent 70%);
animation:drift 22s ease-in-out infinite alternate;}
@keyframes drift{from{transform:translate3d(0,0,0) scale(1)}to{transform:translate3d(-1.5%,2%,0) scale(1.06)}}
@media (prefers-reduced-motion:reduce){[data-testid="stAppViewContainer"]::before{animation:none}}
[data-testid="stHeader"]{background:rgba(7,10,24,.4);backdrop-filter:blur(14px);}
[data-testid="stMainBlockContainer"]{max-width:1500px;padding-top:2.5rem;position:relative;z-index:1;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,rgba(22,28,62,.82),rgba(10,14,34,.9));
backdrop-filter:blur(24px);border-right:1px solid var(--line);}
[data-testid="stSidebar"] *{color:var(--ink);}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *{color:var(--muted);}
h1,h2,h3,h4{font-family:'Sora',sans-serif !important;letter-spacing:-.03em;color:#f6f8ff;}
p,li,label{color:#d5def5;}
a{color:var(--cyan) !important;}
code,pre{color:#d5e3ff !important;}
[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(255,255,255,.08),rgba(255,255,255,.025));
border:1px solid var(--line);border-radius:18px;padding:14px 18px;backdrop-filter:blur(18px);}
[data-testid="stMetricLabel"]{color:var(--muted) !important;}
[data-testid="stMetricValue"]{font-family:'Sora',sans-serif;}
div[data-testid="stVerticalBlockBorderWrapper"]>div{background:var(--glass);border:1px solid var(--line) !important;
border-radius:24px !important;backdrop-filter:blur(20px) saturate(140%);
box-shadow:0 24px 70px rgba(2,4,20,.45),inset 0 1px 0 rgba(255,255,255,.10);}
[data-baseweb="tab-list"]{gap:6px;padding:6px;border:1px solid var(--line);border-radius:16px;
background:rgba(255,255,255,.04);backdrop-filter:blur(16px);width:fit-content;}
[data-baseweb="tab"]{border-radius:11px;padding:10px 18px;background:transparent;}
[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(100deg,rgba(94,234,212,.22),rgba(167,139,250,.26));color:#fff !important;}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"]{display:none;}
[data-testid="stProgressBar"]>div>div{background:linear-gradient(90deg,var(--cyan),var(--blue),var(--violet),var(--pink));}
button[kind="primary"]{border:0 !important;color:#06101c !important;font-weight:800 !important;
background:linear-gradient(100deg,#5eead4,#60a5fa 50%,#c084fc) !important;box-shadow:0 10px 30px rgba(96,165,250,.35);}
button[kind="primary"]:hover{filter:brightness(1.1);}
button[kind="secondary"]{border:1px solid var(--line) !important;background:rgba(255,255,255,.05) !important;}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stSelectbox"] [role="combobox"]{
background:rgba(255,255,255,.06) !important;border:1px solid var(--line) !important;border-radius:12px !important;color:var(--ink) !important;}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:16px;overflow:hidden;}
[data-testid="stAlert"]{border-radius:16px;backdrop-filter:blur(12px);}
.hero{position:relative;isolation:isolate;overflow:hidden;box-sizing:border-box;width:100%;padding:30px 36px;margin:1.25rem 0 24px;border-radius:30px;
border:1px solid rgba(200,215,255,.22);background:linear-gradient(115deg,rgba(40,52,112,.62),rgba(70,36,100,.42) 60%,rgba(20,70,90,.45));
box-shadow:0 30px 80px rgba(2,4,24,.5),inset 0 1px 0 rgba(255,255,255,.16);backdrop-filter:blur(26px);}
.hero:before{content:'';position:absolute;width:340px;height:340px;right:-70px;top:-170px;border-radius:50%;
background:conic-gradient(from 90deg,#5eead4,#60a5fa,#c084fc,#f472b6,#5eead4);filter:blur(46px);opacity:.55;z-index:0;}
.hero-row{display:flex;align-items:center;gap:18px;position:relative;z-index:1;}
.brand{width:56px;height:56px;border-radius:18px;display:grid;place-items:center;font-size:1.7rem;color:#08121f;
background:linear-gradient(135deg,#5eead4,#a78bfa 60%,#f472b6);box-shadow:0 10px 30px rgba(167,139,250,.5);}
.hero h1{margin:0 !important;font-size:clamp(1.9rem,3.6vw,2.9rem) !important;
background:linear-gradient(95deg,#fff,#b9c8ff 55%,#8ff3e4);-webkit-background-clip:text;background-clip:text;color:transparent !important;}
.hero p{margin:.5rem 0 0;color:#b8c5e6;max-width:720px;position:relative;z-index:1;}
.chips{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap;position:relative;z-index:1;}
.chip{padding:5px 12px;border-radius:999px;font-size:.78rem;font-weight:600;border:1px solid var(--line);background:rgba(255,255,255,.06);color:#dbe5ff;}
.kpi{position:relative;overflow:hidden;padding:18px 20px;border-radius:22px;border:1px solid var(--line);
background:linear-gradient(150deg,rgba(255,255,255,.09),rgba(255,255,255,.02));backdrop-filter:blur(18px);}
.kpi:after{content:'';position:absolute;right:-30px;top:-30px;width:110px;height:110px;border-radius:50%;background:var(--c);filter:blur(34px);opacity:.38;}
.kpi .l{color:var(--muted);font-size:.8rem;font-weight:600;}
.kpi .v{font-family:'Sora',sans-serif;font-size:2.1rem;font-weight:700;line-height:1.15;margin:4px 0 10px;}
.kpi .bar{height:6px;border-radius:9px;background:rgba(255,255,255,.09);overflow:hidden;}
.kpi .bar i{display:block;height:100%;border-radius:9px;background:var(--c);}
.card-head{display:flex;align-items:center;gap:16px;}
.card-head .t{font-family:'Sora',sans-serif;font-weight:700;font-size:1.15rem;}
.card-head .s{color:var(--muted);font-size:.8rem;margin-top:2px;}
.micro{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:12px;}
.micro div{font-size:.68rem;color:var(--muted);}
.micro i{display:block;height:6px;border-radius:6px;margin-top:5px;background:rgba(255,255,255,.08);position:relative;overflow:hidden;}
.micro i b{position:absolute;inset:0 auto 0 0;border-radius:6px;}
.glass-box{padding:14px 16px;border-radius:16px;border:1px solid var(--line);background:rgba(255,255,255,.05);margin:8px 0 14px;}
.lbl{font-size:.74rem;font-weight:700;color:var(--cyan);margin-bottom:4px;}
.quote{border-left:3px solid var(--pink);padding-left:14px;color:#e6ecff;}
.strip{position:relative;height:30px;border-radius:10px;background:rgba(255,255,255,.07);border:1px solid var(--line);overflow:hidden;}
.strip i{position:absolute;top:3px;bottom:3px;border-radius:7px;background:linear-gradient(90deg,#5eead4,#a78bfa,#f472b6);box-shadow:0 0 14px rgba(167,139,250,.6);}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:.78rem;color:var(--muted);margin-top:6px;}
.legend span:before{content:'';display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--d);margin-right:6px;}
</style>
"""


def _h(markup):
    return "".join(line.strip() for line in markup.splitlines())


def grade_color(total):
    return "#5eead4" if total >= 80 else "#60a5fa" if total >= 65 else "#fbbf24" if total >= 50 else "#f472b6"


def hero():
    return _h("""<div class="hero"><div class="hero-row"><div class="brand">✦</div><div>
    <h1>PromoFinder Studio</h1></div></div>
    <p>Find the moment that makes someone stop scrolling. Run inference, inspect source-backed cuts, and compare promo rankings at a glance.</p>
    <div class="chips"><span class="chip">Generate</span><span class="chip">Validate</span>
    <span class="chip">Semantic review</span><span class="chip">Rank</span></div></div>""")


def kpi(label, value, color, pct=None):
    bar = '<div class="bar"><i style="width:{:.0f}%"></i></div>'.format(max(0, min(100, pct))) if pct is not None else ""
    return _h('<div class="kpi" style="--c:{}"><div class="l">{}</div><div class="v">{}</div>{}</div>'.format(
        color, label, value, bar))


def ring(value, maximum=100, size=120, label="", uid="r", color=None):
    color = color or grade_color(value * 100.0 / maximum)
    radius, stroke = size / 2 - 11, 11
    circ = 2 * math.pi * radius
    frac = max(0.0, min(1.0, value / float(maximum)))
    return _h("""<svg width="{s}" height="{s}" viewBox="0 0 {s} {s}" role="img" aria-label="score {v:.1f}">
    <defs><linearGradient id="g{u}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c}"/><stop offset="1" stop-color="#c084fc"/></linearGradient></defs>
    <circle cx="{h}" cy="{h}" r="{r}" fill="none" stroke="rgba(255,255,255,.09)" stroke-width="{w}"/>
    <circle cx="{h}" cy="{h}" r="{r}" fill="none" stroke="url(#g{u})" stroke-width="{w}" stroke-linecap="round"
    stroke-dasharray="{d:.1f} {circ:.1f}" transform="rotate(-90 {h} {h})" style="filter:drop-shadow(0 0 8px {c})"/>
    <text x="{h}" y="{ty}" text-anchor="middle" fill="#fff" font-family="Sora" font-weight="700" font-size="{fs}">{v:.1f}</text>
    <text x="{h}" y="{ly}" text-anchor="middle" fill="#9aa9c9" font-size="{ls}">{lab}</text></svg>""".format(
        s=size, h=size / 2, r=radius, w=stroke, c=color, u=uid, circ=circ, d=circ * frac, v=value,
        ty=size / 2 + size * .05, fs=int(size * .24), ly=size / 2 + size * .2, ls=int(size * .09), lab=label))


def radar(scores, size=250, uid="rd"):
    c, rad = size / 2, size / 2 - 42
    pts, grid, axes, labels = [], [], [], []
    for lvl in range(1, 6):
        ring_pts = " ".join("{:.1f},{:.1f}".format(
            c + rad * lvl / 5 * math.cos(math.radians(-90 + i * 72)),
            c + rad * lvl / 5 * math.sin(math.radians(-90 + i * 72))) for i in range(5))
        grid.append('<polygon points="{}" fill="none" stroke="rgba(190,210,255,.14)"/>'.format(ring_pts))
    for i, (name, key, color) in enumerate(DIMS):
        a = math.radians(-90 + i * 72)
        v = max(0.0, min(5.0, float(scores.get(key, 0) or 0)))
        pts.append("{:.1f},{:.1f}".format(c + rad * v / 5 * math.cos(a), c + rad * v / 5 * math.sin(a)))
        axes.append('<line x1="{}" y1="{}" x2="{:.1f}" y2="{:.1f}" stroke="rgba(190,210,255,.14)"/>'.format(
            c, c, c + rad * math.cos(a), c + rad * math.sin(a)))
        axes.append('<circle cx="{:.1f}" cy="{:.1f}" r="5" fill="{}" stroke="#0b1024" stroke-width="2"/>'.format(
            c + rad * v / 5 * math.cos(a), c + rad * v / 5 * math.sin(a), color))
        labels.append('<text x="{:.1f}" y="{:.1f}" text-anchor="middle" dominant-baseline="middle" fill="{}" font-size="11" font-weight="700">{}</text>'.format(
            c + (rad + 24) * math.cos(a), c + (rad + 24) * math.sin(a), color, name))
    return _h("""<svg width="100%" viewBox="0 0 {s} {s}" style="max-width:{s}px" role="img" aria-label="score radar">
    <defs><linearGradient id="{u}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5eead4" stop-opacity=".55"/>
    <stop offset="1" stop-color="#f472b6" stop-opacity=".5"/></linearGradient></defs>
    {g}{a}<polygon points="{p}" fill="url(#{u})" stroke="#c4b5fd" stroke-width="2" style="filter:drop-shadow(0 0 10px rgba(167,139,250,.7))"/>
    {l}</svg>""".format(s=size, u=uid, g="".join(grid), a="".join(axes), p=" ".join(pts), l="".join(labels)))


def dim_bars(scores):
    rows = []
    for name, key, color in DIMS:
        v = float(scores.get(key, 0) or 0)
        rows.append("""<div style="margin:9px 0"><div style="display:flex;justify-content:space-between;font-size:.82rem">
        <span style="color:{c};font-weight:700">{n}</span><span>{v:g}/5</span></div>
        <div style="height:9px;border-radius:9px;background:rgba(255,255,255,.08);margin-top:5px;overflow:hidden">
        <div style="width:{p:.0f}%;height:100%;border-radius:9px;background:linear-gradient(90deg,{c},rgba(255,255,255,.75));
        box-shadow:0 0 12px {c}"></div></div></div>""".format(c=color, n=name, v=v, p=v * 20))
    return _h("".join(rows))


def micro_bars(scores):
    cells = []
    for name, key, color in DIMS:
        v = float(scores.get(key, 0) or 0)
        cells.append('<div>{}<i><b style="width:{:.0f}%;background:{}"></b></i></div>'.format(name, v * 20, color))
    return _h('<div class="micro">{}</div>'.format("".join(cells)))


def promo_card_head(rank, subtitle, total, uid):
    return _h("""<div class="card-head">{r}<div><div class="t">Promo #{n}</div><div class="s">{s}</div></div></div>""".format(
        r=ring(total, 100, 92, "/100", uid), n=rank, s=subtitle))


def rank_chart(items):
    """items: list of (label, total_score)."""
    if not items:
        return ""
    rows = []
    for index, (label, score) in enumerate(items):
        color = grade_color(score)
        rows.append("""<div style="display:grid;grid-template-columns:150px 1fr 54px;gap:12px;align-items:center;margin:7px 0">
        <div style="font-size:.8rem;color:#c9d6f5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">#{i} {l}</div>
        <div style="height:14px;border-radius:9px;background:rgba(255,255,255,.07);overflow:hidden">
        <div style="width:{p:.1f}%;height:100%;border-radius:9px;background:linear-gradient(90deg,{c},#c084fc);box-shadow:0 0 14px {c}"></div></div>
        <div style="font-family:Sora;font-weight:700;text-align:right">{s:.1f}</div></div>""".format(
            i=index + 1, l=label, p=max(0, min(100, score)), c=color, s=score))
    return _h("".join(rows))


def avg_profile(all_scores):
    """Average radar-style bars across the shortlist."""
    if not all_scores:
        return ""
    avg = {key: sum(float(s.get(key, 0) or 0) for s in all_scores) / len(all_scores) for _, key, _ in DIMS}
    return radar(avg, 250, "avg")


def segment_strip(spans, total_blocks):
    """spans: list of (start_idx, end_idx) block indices."""
    if not total_blocks:
        return ""
    bars = "".join('<i style="left:{:.2f}%;width:{:.2f}%"></i>'.format(
        100.0 * start / total_blocks, max(1.2, 100.0 * (end - start + 1) / total_blocks))
        for start, end in spans)
    return _h('<div class="lbl">Where the cuts sit in the episode</div><div class="strip">{}</div>'.format(bars))


def history_chart(rows):
    """rows: chronological list of (run_id, valid, ranked)."""
    rows = rows[-12:]
    if not rows:
        return ""
    peak = max([max(valid, ranked) for _, valid, ranked in rows] + [1])
    width, height, pad = 760, 230, 34
    slot = (width - pad * 2) / float(len(rows))
    bar_width = min(26, slot / 3)
    parts = ['<defs><linearGradient id="hv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5eead4"/><stop offset="1" stop-color="#60a5fa"/></linearGradient>'
             '<linearGradient id="hr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f472b6"/><stop offset="1" stop-color="#a78bfa"/></linearGradient></defs>']
    for grid_line in range(5):
        y = pad + (height - pad * 2) * grid_line / 4.0
        parts.append('<line x1="{}" x2="{}" y1="{:.1f}" y2="{:.1f}" stroke="rgba(190,210,255,.1)"/>'.format(pad, width - pad, y, y))
    for index, (run_id, valid, ranked) in enumerate(rows):
        x = pad + slot * index + slot / 2
        for dx, value, fill in ((-bar_width - 2, valid, "hv"), (2, ranked, "hr")):
            bar_height = (height - pad * 2) * value / float(peak)
            parts.append('<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}" rx="6" fill="url(#{})"/>'.format(
                x + dx, height - pad - bar_height, bar_width, max(bar_height, 2), fill))
        parts.append('<text x="{:.1f}" y="{}" text-anchor="middle" fill="#9aa9c9" font-size="10">{}</text>'.format(
            x, height - 12, str(run_id)[-6:]))
    return _h('<svg width="100%" viewBox="0 0 {} {}" role="img" aria-label="promos per run">{}</svg>'
              '<div class="legend"><span style="--d:#5eead4">Valid promos</span><span style="--d:#f472b6">Ranked</span></div>'.format(
                  width, height, "".join(parts)))


def status_donut(parts, uid="dn"):
    """parts: list of (label, value, color)."""
    del uid
    total = sum(value for _, value, _ in parts) or 1
    radius, circumference, offset, arcs = 46, 2 * math.pi * 46, 0.0, []
    for label, value, color in parts:
        length = circumference * value / total
        arcs.append('<circle cx="60" cy="60" r="{}" fill="none" stroke="{}" stroke-width="14" stroke-dasharray="{:.1f} {:.1f}" '
                    'stroke-dashoffset="{:.1f}" transform="rotate(-90 60 60)"/>'.format(radius, color, length, circumference, -offset))
        offset += length
    legend = "".join('<span style="--d:{}">{} · {}</span>'.format(color, label, value)
                     for label, value, color in parts)
    return _h('<div style="display:flex;align-items:center;gap:18px"><svg width="120" height="120" viewBox="0 0 120 120">'
              '<circle cx="60" cy="60" r="46" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="14"/>{}'
              '<text x="60" y="66" text-anchor="middle" fill="#fff" font-family="Sora" font-weight="700" font-size="22">{}</text></svg>'
              '<div class="legend" style="flex-direction:column;gap:8px">{}</div></div>'.format(
                  "".join(arcs), int(sum(value for _, value, _ in parts)), legend))
