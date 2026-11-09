"""The look of the app: colours, CSS and small reusable components (cards, hero, stepper ...)."""
import html as _html

import streamlit as st

ACCENT = "#7C5CFF"
CYAN = "#00D4FF"
GREEN = "#2EE6A6"
AMBER = "#FFB020"
RED = "#FF5C7C"
TEXT = "#E8ECF8"
MUTED = "#9AA4C7"

PALETTES = {
    "dark": {
        "bg": "#0A0F1F", "glow1": "rgba(124,92,255,0.22)", "glow2": "rgba(0,212,255,0.14)",
        "header-bg": "rgba(10,15,31,0.72)", "header-border": "rgba(255,255,255,0.06)",
        "ink": "#FFFFFF", "text": "#E8ECF8", "muted": "#9AA4C7", "muted2": "#B5BEDD", "faint": "#7E89B0",
        "card-a": "rgba(255,255,255,0.075)", "card-b": "rgba(255,255,255,0.025)", "card-border": "rgba(255,255,255,0.09)",
        "card-shadow": "rgba(0,0,0,0.28)", "surface": "rgba(255,255,255,0.045)", "surface-border": "rgba(255,255,255,0.08)",
        "hero-a": "rgba(124,92,255,0.28)", "hero-b": "rgba(0,212,255,0.12)", "hero-c": "rgba(18,25,54,0.6)",
        "hero-border": "rgba(255,255,255,0.10)", "hero-shadow": "rgba(0,0,0,0.35)", "hero-p": "#C3CBE8",
        "kicker-fg": "#BBA9FF", "kicker-bg": "rgba(124,92,255,0.16)", "kicker-border": "rgba(124,92,255,0.4)",
        "chip-bg": "rgba(255,255,255,0.07)", "chip-border": "rgba(255,255,255,0.12)", "chip-fg": "#DCE3FF",
        "btn-bg": "rgba(255,255,255,0.06)", "btn-border": "rgba(255,255,255,0.14)",
        "track": "rgba(255,255,255,0.09)", "tab-bar": "rgba(255,255,255,0.04)", "tab-active": "rgba(124,92,255,0.25)",
        "step-bg": "rgba(255,255,255,0.04)", "step-n": "rgba(255,255,255,0.08)", "line": "rgba(255,255,255,0.12)",
        "ring-inner": "#0F1530", "empty-border": "rgba(255,255,255,0.18)", "empty-bg": "rgba(255,255,255,0.03)",
        "grad1": "#A78BFF", "grad2": "#00D4FF", "grad3": "#2EE6A6",
        "pv-bg": "rgba(124,92,255,0.2)", "pv-fg": "#C8BBFF", "pg-bg": "rgba(46,230,166,0.16)", "pg-fg": "#7DF3C9",
        "pa-bg": "rgba(255,176,32,0.16)", "pa-fg": "#FFD27A", "pc-bg": "rgba(0,212,255,0.16)", "pc-fg": "#7BE6FF",
        "stage-done": "#CFFFEA", "step-done": "#D9FFF1",
    },
    "light": {
        "bg": "#F3F5FB", "glow1": "rgba(124,92,255,0.13)", "glow2": "rgba(0,180,230,0.12)",
        "header-bg": "rgba(243,245,251,0.82)", "header-border": "rgba(20,30,80,0.08)",
        "ink": "#0F1537", "text": "#1B2142", "muted": "#5E678C", "muted2": "#454E73", "faint": "#7B84A8",
        "card-a": "#FFFFFF", "card-b": "#FFFFFF", "card-border": "rgba(20,30,80,0.10)",
        "card-shadow": "rgba(40,50,110,0.10)", "surface": "#FFFFFF", "surface-border": "rgba(20,30,80,0.10)",
        "hero-a": "rgba(124,92,255,0.17)", "hero-b": "rgba(0,180,230,0.10)", "hero-c": "rgba(255,255,255,0.85)",
        "hero-border": "rgba(20,30,80,0.10)", "hero-shadow": "rgba(40,50,110,0.14)", "hero-p": "#454E73",
        "kicker-fg": "#5B3FE0", "kicker-bg": "rgba(124,92,255,0.10)", "kicker-border": "rgba(124,92,255,0.35)",
        "chip-bg": "rgba(20,30,80,0.05)", "chip-border": "rgba(20,30,80,0.10)", "chip-fg": "#2B3560",
        "btn-bg": "#FFFFFF", "btn-border": "rgba(20,30,80,0.16)",
        "track": "rgba(20,30,80,0.09)", "tab-bar": "rgba(20,30,80,0.05)", "tab-active": "rgba(124,92,255,0.18)",
        "step-bg": "rgba(20,30,80,0.04)", "step-n": "rgba(20,30,80,0.08)", "line": "rgba(20,30,80,0.14)",
        "ring-inner": "#FFFFFF", "empty-border": "rgba(20,30,80,0.20)", "empty-bg": "rgba(255,255,255,0.6)",
        "grad1": "#6D4AFF", "grad2": "#0891B2", "grad3": "#0E9F6E",
        "pv-bg": "rgba(124,92,255,0.12)", "pv-fg": "#5B3FE0", "pg-bg": "rgba(14,159,110,0.12)", "pg-fg": "#0B7A55",
        "pa-bg": "rgba(245,159,0,0.15)", "pa-fg": "#9A5B00", "pc-bg": "rgba(8,145,178,0.12)", "pc-fg": "#06708A",
        "stage-done": "#0B7A55", "step-done": "#0B7A55",
    },
}

CSS_TEMPLATE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root { __VARS__ }
@supports (color: light-dark(white, black)) { :root { __ADAPTIVE__ } }

html, body, [class*="css"], .stApp { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }

.stApp {
  background:
    radial-gradient(900px 500px at 8% -5%, var(--glow1), transparent 60%),
    radial-gradient(800px 480px at 100% 0%, var(--glow2), transparent 55%),
    var(--bg);
}
header[data-testid="stHeader"] { background: var(--header-bg); backdrop-filter: blur(14px); border-bottom: 1px solid var(--header-border); }
footer, [data-testid="stDecoration"], [data-testid="stAppDeployButton"] { visibility: hidden; height: 0; }   /* the main menu stays: it holds the theme setting */
header[data-testid="stHeader"] [data-testid="stTopNavLink"] { border-radius: 10px; font-weight: 600; }
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1240px; }
h1, h2, h3 { letter-spacing: -0.02em; }
h2 { font-weight: 700; }

.hero { position: relative; padding: 46px 44px; border-radius: 28px; overflow: hidden; margin-bottom: 26px;
  background: linear-gradient(135deg, var(--hero-a), var(--hero-b) 60%, var(--hero-c));
  border: 1px solid var(--hero-border); box-shadow: 0 24px 80px var(--hero-shadow); animation: rise .6s ease both; }
.hero:before { content: ""; position: absolute; width: 380px; height: 380px; right: -90px; top: -120px; border-radius: 50%;
  background: radial-gradient(circle, var(--glow2), transparent 65%); filter: blur(8px); animation: float 9s ease-in-out infinite; }
.hero .kicker { display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
  color: var(--kicker-fg); background: var(--kicker-bg); border: 1px solid var(--kicker-border); padding: 6px 12px; border-radius: 999px; }
.hero h1 { font-size: clamp(32px, 5vw, 54px); line-height: 1.05; margin: 18px 0 14px 0; font-weight: 800; color: var(--ink); }
.hero h1 .grad { background: linear-gradient(90deg, var(--grad1), var(--grad2) 55%, var(--grad3)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.hero p { font-size: 17px; color: var(--hero-p); max-width: 720px; margin: 0 0 22px 0; line-height: 1.6; }
.chips { display: flex; flex-wrap: wrap; gap: 10px; }
.chip { font-size: 12.5px; font-weight: 600; color: var(--chip-fg); padding: 7px 13px; border-radius: 999px; background: var(--chip-bg); border: 1px solid var(--chip-border); }

.page-title { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin: 4px 0 20px 0; animation: rise .5s ease both; }
.page-title h1 { margin: 0; font-size: 34px; font-weight: 800; color: var(--ink); }
.page-title p { margin: 4px 0 0 0; color: var(--muted); font-size: 15px; }

.section { margin: 30px 0 12px 0; }
.section h3 { margin: 0; font-size: 20px; font-weight: 700; color: var(--ink); }
.section p { margin: 3px 0 0 0; color: var(--muted); font-size: 14px; }

.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin: 6px 0 8px 0; }
.kpi { position: relative; padding: 18px 18px 16px 18px; border-radius: 20px; overflow: hidden;
  background: linear-gradient(160deg, var(--card-a), var(--card-b)); border: 1px solid var(--card-border); box-shadow: 0 10px 34px var(--card-shadow);
  transition: transform .2s ease, border-color .2s ease; animation: rise .55s ease both; }
.kpi:hover { transform: translateY(-3px); border-color: rgba(124,92,255,0.55); }
.kpi .icon { width: 34px; height: 34px; border-radius: 11px; display: grid; place-items: center; font-weight: 800; font-size: 16px; color: #fff; margin-bottom: 12px; }
.kpi .label { font-size: 12.5px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); }
.kpi .value { font-size: 30px; font-weight: 800; color: var(--ink); margin-top: 4px; letter-spacing: -0.02em; }
.kpi .sub { font-size: 12.5px; color: var(--muted); margin-top: 4px; }
.kpi.violet .icon { background: linear-gradient(135deg,#7C5CFF,#A78BFF); }
.kpi.cyan .icon { background: linear-gradient(135deg,#00B7E6,#00D4FF); }
.kpi.green .icon { background: linear-gradient(135deg,#17C58C,#2EE6A6); }
.kpi.amber .icon { background: linear-gradient(135deg,#F59E0B,#FFB020); }
.kpi.red .icon { background: linear-gradient(135deg,#F0446A,#FF5C7C); }

.insights { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
.insight { padding: 18px 20px; border-radius: 18px; background: var(--surface); border: 1px solid var(--surface-border);
  border-left: 4px solid #7C5CFF; box-shadow: 0 8px 24px var(--card-shadow); animation: rise .6s ease both; }
.insight.good { border-left-color: #2EE6A6; } .insight.warn { border-left-color: #FFB020; } .insight.info { border-left-color: #00B7E6; }
.insight .t { font-weight: 700; color: var(--ink); font-size: 16px; margin-bottom: 5px; }
.insight .d { color: var(--muted2); font-size: 14px; line-height: 1.55; }

.features { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin: 8px 0 26px 0; }
.feature { padding: 20px; border-radius: 20px; background: var(--surface); border: 1px solid var(--surface-border); box-shadow: 0 8px 24px var(--card-shadow); transition: transform .2s ease, border-color .2s; }
.feature:hover { transform: translateY(-3px); border-color: rgba(0,180,230,0.55); }
.feature .big { font-size: 26px; font-weight: 800; background: linear-gradient(90deg,var(--grad1),var(--grad2)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.feature .t { font-weight: 700; color: var(--ink); margin: 6px 0 4px 0; }
.feature .d { color: var(--muted); font-size: 13.5px; line-height: 1.5; }

.stepper { display: flex; align-items: center; gap: 10px; margin: 8px 0 20px 0; flex-wrap: wrap; }
.step { display: flex; align-items: center; gap: 10px; padding: 9px 16px 9px 10px; border-radius: 999px; font-size: 14px; font-weight: 600;
  color: var(--faint); background: var(--step-bg); border: 1px solid var(--surface-border); }
.step .n { width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; font-size: 13px; font-weight: 800; background: var(--step-n); }
.step.active { color: var(--ink); border-color: rgba(124,92,255,0.7); background: rgba(124,92,255,0.16); }
.step.active .n { background: linear-gradient(135deg,#7C5CFF,#00B7E6); color: #fff; }
.step.done { color: var(--step-done); border-color: rgba(46,230,166,0.5); }
.step.done .n { background: #2EE6A6; color: #06281D; }
.step-line { height: 2px; width: 28px; background: var(--line); border-radius: 2px; }

.stages { display: grid; gap: 8px; margin-top: 10px; }
.stage { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-radius: 12px; font-size: 14.5px; background: var(--step-bg); color: var(--faint); }
.stage .dot { width: 12px; height: 12px; border-radius: 50%; background: var(--line); flex: none; }
.stage.active { color: var(--ink); background: rgba(124,92,255,0.14); } .stage.active .dot { background: #7C5CFF; box-shadow: 0 0 0 5px rgba(124,92,255,0.25); animation: pulse 1.2s infinite; }
.stage.done { color: var(--stage-done); } .stage.done .dot { background: #2EE6A6; }

.pill { display: inline-block; padding: 4px 11px; border-radius: 999px; font-size: 12px; font-weight: 700; margin-right: 6px; }
.pill.violet { background: var(--pv-bg); color: var(--pv-fg); } .pill.green { background: var(--pg-bg); color: var(--pg-fg); }
.pill.amber { background: var(--pa-bg); color: var(--pa-fg); } .pill.cyan { background: var(--pc-bg); color: var(--pc-fg); }
.empty { text-align: center; padding: 64px 24px; border-radius: 24px; border: 1px dashed var(--empty-border); background: var(--empty-bg); }
.empty .t { font-size: 22px; font-weight: 800; color: var(--ink); margin-bottom: 8px; } .empty .d { color: var(--muted); max-width: 520px; margin: 0 auto; line-height: 1.6; }
.ring-wrap { display: grid; place-items: center; padding: 8px 0; }
.ring { width: 200px; height: 200px; border-radius: 50%; display: grid; place-items: center;
  background: conic-gradient(var(--c) calc(var(--p) * 1%), var(--track) 0); box-shadow: 0 0 60px var(--glow); }
.ring .inner { width: 156px; height: 156px; border-radius: 50%; background: var(--ring-inner); display: grid; place-items: center; text-align: center; }
.ring .num { font-size: 40px; font-weight: 800; color: var(--ink); line-height: 1; } .ring .cap { font-size: 12px; color: var(--muted); margin-top: 4px; letter-spacing: .06em; text-transform: uppercase; }
.verdict { text-align: center; font-weight: 700; font-size: 17px; margin-top: 8px; }
.theme-hint { color: var(--muted); font-size: 13px; margin: -10px 0 18px 2px; }

div[class*="st-key-card"] { background: linear-gradient(160deg, var(--card-a), var(--card-b)); border: 1px solid var(--card-border);
  border-radius: 22px; padding: 18px 20px 12px 20px; box-shadow: 0 12px 40px var(--card-shadow); }
div[class*="st-key-card"] h4 { margin: 0 0 2px 0; font-size: 16px; font-weight: 700; color: var(--ink); }
div[class*="st-key-card-report"] h1 { font-size: 26px; margin-top: 4px; }
div[class*="st-key-card-report"] h2 { font-size: 19px; margin-top: 18px; color: var(--pv-fg); }
div[class*="st-key-card-report"] table { font-size: 14px; }
.card-sub { color: var(--muted); font-size: 13px; margin: 0 0 6px 0; }

.stButton > button, .stDownloadButton > button, .stLinkButton > a { border-radius: 14px; font-weight: 700; padding: .65rem 1.3rem; border: 1px solid var(--btn-border);
  background: var(--btn-bg); color: var(--ink); transition: all .2s ease; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color: #7C5CFF; transform: translateY(-1px); background: rgba(124,92,255,0.14); }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] { background: linear-gradient(135deg, #7C5CFF, #00B7E6); border: none; color: #fff; box-shadow: 0 10px 30px rgba(124,92,255,0.4); }
.stButton > button[kind="primary"]:hover { filter: brightness(1.1); background: linear-gradient(135deg, #8B6EFF, #00C8F5); }
[data-testid="stFileUploaderDropzone"] { border-radius: 20px; border: 2px dashed rgba(124,92,255,0.55); background: rgba(124,92,255,0.07); padding: 28px; }
[data-testid="stFileUploaderDropzone"]:hover { background: rgba(124,92,255,0.13); }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid var(--surface-border); }
.stTabs [data-baseweb="tab-list"] { gap: 6px; background: var(--tab-bar); padding: 5px; border-radius: 14px; }
.stTabs [data-baseweb="tab"] { border-radius: 10px; padding: 8px 16px; font-weight: 600; }
.stTabs [aria-selected="true"] { background: var(--tab-active); }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
[data-testid="stExpander"] { border-radius: 16px; border: 1px solid var(--surface-border); background: var(--step-bg); }
[data-baseweb="select"] > div { border-radius: 12px; }
[data-testid="stSlider"] [role="slider"] { background: #7C5CFF; }
.stProgress > div > div > div > div { background: linear-gradient(90deg, #7C5CFF, #00B7E6); }

@keyframes rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(24px); } }
@keyframes pulse { 0%,100% { box-shadow: 0 0 0 4px rgba(124,92,255,0.25); } 50% { box-shadow: 0 0 0 9px rgba(124,92,255,0.05); } }
@media (max-width: 700px) { .hero { padding: 28px 22px; } .block-container { padding-left: 1rem; padding-right: 1rem; } }
</style>
"""



def current_mode():
    """'light' or 'dark', whichever theme this visitor is using (system setting or the Settings menu)."""
    try:
        return "light" if st.context.theme.get("type") == "light" else "dark"
    except Exception:
        return "dark"


def inject_css(mode="dark"):
    """Static colours for the detected mode, plus light-dark() colours that flip instantly when the theme changes."""
    static = " ".join(f"--{name}: {value};" for name, value in PALETTES[mode].items())
    adaptive = " ".join(f"--{name}: light-dark({PALETTES['light'][name]}, {PALETTES['dark'][name]});"
                        for name in PALETTES["dark"])
    st.markdown(CSS_TEMPLATE.replace("__VARS__", static).replace("__ADAPTIVE__", adaptive), unsafe_allow_html=True)


WATCHER_JS = """
<script>
(function () {
  const app = document.querySelector('.stApp');
  if (!app || window.__clickpulseWatcher) return;
  window.__clickpulseWatcher = true;
  let last = getComputedStyle(app).colorScheme;
  const check = () => {
    const now = getComputedStyle(app).colorScheme;
    if (now === last) return;
    last = now;                      // the visitor switched between light and dark: rerun once so charts and logo follow
    setTimeout(() => document.body.dispatchEvent(new KeyboardEvent('keydown',
      {key: 'r', code: 'KeyR', keyCode: 82, which: 82, bubbles: true})), 200);
  };
  new MutationObserver(check).observe(app, {attributes: true, attributeFilter: ['style', 'class']});
  setInterval(check, 800);
})();
</script>
"""


def inject_theme_watcher():
    """Rerun the app once when the theme changes. If this Streamlit version cannot run it, nothing breaks."""
    try:
        st.html(WATCHER_JS, unsafe_allow_javascript=True)
    except TypeError:
        pass


def _h(text):
    return _html.escape(str(text))


def html(markup):
    st.markdown(markup, unsafe_allow_html=True)


def hero(kicker, title_html, subtitle, chips=()):
    chip_html = "".join(f'<span class="chip">{_h(c)}</span>' for c in chips)
    html(f'<div class="hero"><span class="kicker">{_h(kicker)}</span><h1>{title_html}</h1><p>{_h(subtitle)}</p>'
         f'<div class="chips">{chip_html}</div></div>')


def page_title(title, subtitle="", pills=()):
    pill_html = "".join(f'<span class="pill {tone}">{_h(text)}</span>' for text, tone in pills)
    html(f'<div class="page-title"><div><h1>{_h(title)}</h1><p>{_h(subtitle)}</p></div><div>{pill_html}</div></div>')


def section(title, subtitle=""):
    sub = f"<p>{_h(subtitle)}</p>" if subtitle else ""
    html(f'<div class="section"><h3>{_h(title)}</h3>{sub}</div>')


def kpi_grid(items):
    """items: list of dicts with label, value, sub (optional), tone (violet/cyan/green/amber/red), icon."""
    cards = []
    for i, item in enumerate(items):
        sub = f'<div class="sub">{_h(item["sub"])}</div>' if item.get("sub") else ""
        length = len(str(item["value"]))
        size = "20px" if length > 14 else ("24px" if length > 9 else "")
        value_style = f' style="font-size:{size}"' if size else ""
        cards.append(f'<div class="kpi {item.get("tone", "violet")}" style="animation-delay:{i * 0.06:.2f}s">'
                     f'<div class="icon">{_h(item.get("icon", "#"))}</div><div class="label">{_h(item["label"])}</div>'
                     f'<div class="value"{value_style}>{_h(item["value"])}</div>{sub}</div>')
    html('<div class="kpis">' + "".join(cards) + "</div>")


def insight_grid(insights):
    cards = [f'<div class="insight {_h(i["tone"])}" style="animation-delay:{n * 0.07:.2f}s">'
             f'<div class="t">{_h(i["title"])}</div><div class="d">{_h(i["text"])}</div></div>'
             for n, i in enumerate(insights)]
    html('<div class="insights">' + "".join(cards) + "</div>")


def feature_grid(items):
    cards = [f'<div class="feature"><div class="big">{_h(big)}</div><div class="t">{_h(title)}</div>'
             f'<div class="d">{_h(text)}</div></div>' for big, title, text in items]
    html('<div class="features">' + "".join(cards) + "</div>")


def stepper(active):
    """active: 1, 2 or 3. Earlier steps are shown as done."""
    labels = ["Upload", "Check your data", "Analyse"]
    parts = []
    for number, label in enumerate(labels, start=1):
        state = "done" if number < active else ("active" if number == active else "")
        mark = "&#10003;" if state == "done" else str(number)
        parts.append(f'<div class="step {state}"><span class="n">{mark}</span>{_h(label)}</div>')
    html('<div class="stepper">' + '<div class="step-line"></div>'.join(parts) + "</div>")


def stages_html(stages, fraction):
    """stages: list of (label, starts_at_fraction). Returns the progress list as HTML."""
    active_index = max(i for i, (_, start) in enumerate(stages) if start <= fraction)
    rows = []
    for i, (label, _) in enumerate(stages):
        state = "done" if (i < active_index or fraction >= 1.0) else ("active" if i == active_index else "")
        rows.append(f'<div class="stage {state}"><span class="dot"></span>{_h(label)}</div>')
    return '<div class="stages">' + "".join(rows) + "</div>"


def empty_state(title, text):
    html(f'<div class="empty"><div class="t">{_h(title)}</div><div class="d">{_h(text)}</div></div>')


def probability_ring(probability):
    """A glowing ring that shows a purchase probability."""
    percent = round(probability * 100)
    if probability >= 0.6:
        colour, glow, verdict = GREEN, "rgba(46,230,166,0.35)", "Likely to buy"
    elif probability >= 0.4:
        colour, glow, verdict = AMBER, "rgba(255,176,32,0.30)", "Could go either way"
    else:
        colour, glow, verdict = RED, "rgba(255,92,124,0.30)", "Likely to abandon"
    html(f'<div class="ring-wrap"><div class="ring" style="--p:{percent};--c:{colour};--glow:{glow}">'
         f'<div class="inner"><div><div class="num">{percent}%</div><div class="cap">purchase chance</div></div></div></div></div>'
         f'<div class="verdict" style="color:{colour}">{verdict}</div>')


def card_title(title, subtitle=""):
    html(f"<h4>{_h(title)}</h4>" + (f'<div class="card-sub">{_h(subtitle)}</div>' if subtitle else ""))
