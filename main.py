from flask import Flask, Response
import requests, os, json, math, re

app = Flask(__name__)

CLIENT_ID     = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("STRAVA_REFRESH_TOKEN")
WEATHER_LAT   = os.environ.get("WEATHER_LAT", "34.85")
WEATHER_LON   = os.environ.get("WEATHER_LON", "-82.39")
WEEKLY_GOAL_MI = float(os.environ.get("WEEKLY_GOAL_MI", "40"))

PLAN = [
  {"iso":"2026-04-27","name":"MON","type":"run","tag":"RUN","title":"Recovery Run","detail":"30 min · nasal breathing · parenting cap","hr":True,"dur":"30m"},
  {"iso":"2026-04-28","name":"TUE","type":"social","tag":"SOCIAL","title":"Upstate RC Social Run","detail":"Open HR · distance varies","hr":False,"dur":"~45m"},
  {"iso":"2026-04-29","name":"WED","type":"strength","tag":"STRENGTH","title":"Full Body B","detail":"Deadlift · Bench · Pull-ups · Assault Bike","hr":False,"dur":"60m"},
  {"iso":"2026-04-30","name":"THU","type":"run","tag":"RUN","title":"Base Run","detail":"30 min · strict aerobic cap","hr":True,"dur":"30m"},
  {"iso":"2026-05-01","name":"FRI","type":"rest","tag":"REST","title":"Rest & Review","detail":"Full rest · prep for long run","hr":False,"dur":"—"},
  {"iso":"2026-05-02","name":"SAT","type":"run","tag":"RUN","title":"Long Run","detail":"60-90 min easy · 10 min ankle warm-up","hr":True,"dur":"90m"},
  {"iso":"2026-05-03","name":"SUN","type":"strength","tag":"STRENGTH","title":"Full Body A","detail":"Squat · OHP · Row · Sandbag · Knees","hr":False,"dur":"60m"},
  {"iso":"2026-05-04","name":"MON","type":"run","tag":"RUN","title":"Recovery Run","detail":"30 min · nasal breathing · parenting cap","hr":True,"dur":"30m"},
  {"iso":"2026-05-05","name":"TUE","type":"social","tag":"SOCIAL","title":"Upstate RC Social Run","detail":"Open HR · push if you feel good","hr":False,"dur":"~45m"},
  {"iso":"2026-05-06","name":"WED","type":"strength","tag":"STRENGTH","title":"Full Body B","detail":"Deadlift · Bench · Pull-ups · Assault Bike","hr":False,"dur":"60m"},
  {"iso":"2026-05-07","name":"THU","type":"run","tag":"RUN","title":"Base Run","detail":"30 min · strict aerobic volume","hr":True,"dur":"30m"},
  {"iso":"2026-05-08","name":"FRI","type":"rest","tag":"REST","title":"Rest & Review","detail":"Full rest · prep for long run","hr":False,"dur":"—"},
  {"iso":"2026-05-09","name":"SAT","type":"run","tag":"RUN","title":"Long Run","detail":"60-90 min easy · ankle warm-up mandatory","hr":True,"dur":"90m"},
  {"iso":"2026-05-10","name":"SUN","type":"strength","tag":"STRENGTH","title":"Full Body A","detail":"Squat · OHP · Row · Sandbag · Knees","hr":False,"dur":"60m"},
  {"iso":"2026-05-11","name":"MON","type":"run","tag":"RUN","title":"Recovery Run","detail":"30 min · nasal breathing · parenting cap","hr":True,"dur":"30m"},
  {"iso":"2026-05-12","name":"TUE","type":"social","tag":"SOCIAL","title":"Upstate RC Social Run","detail":"Open HR · enjoy the group","hr":False,"dur":"~45m"},
  {"iso":"2026-05-13","name":"WED","type":"strength","tag":"STRENGTH","title":"Full Body B","detail":"Deadlift · Bench · Pull-ups · Assault Bike","hr":False,"dur":"60m"},
  {"iso":"2026-05-14","name":"THU","type":"run","tag":"RUN","title":"Base Run","detail":"30 min · strict aerobic volume","hr":True,"dur":"30m"},
  {"iso":"2026-05-15","name":"FRI","type":"rest","tag":"REST","title":"Rest & Review","detail":"Full rest · review the week","hr":False,"dur":"—"},
  {"iso":"2026-05-16","name":"SAT","type":"run","tag":"RUN","title":"Long Run","detail":"60-90 min easy · ankle warm-up mandatory","hr":True,"dur":"90m"},
  {"iso":"2026-05-17","name":"SUN","type":"strength","tag":"STRENGTH","title":"Full Body A","detail":"Squat · OHP · Row · Sandbag · Knees","hr":False,"dur":"60m"},
]

COACH_TIPS = {
    "run":      ("Stay patient on climbs and shorten your stride on descents. Build volume consistently.", "Aerobic Base", "Consistency > Intensity"),
    "social":   ("Group runs sharpen mental fitness. Stay aerobic and enjoy the company.", "Community Run", "Run Happy · Run Easy"),
    "strength": ("Move through full range of motion on every rep. Quality reps beat heavy weights.", "Strength & Mobility", "Form First · Always"),
    "rest":     ("Rest days are when your body adapts. Sleep well, eat well, and recover fully.", "Active Recovery", "Rest = Progress"),
}

# ── Strava ───────────────────────────────────────────────────────────────────

def get_access_token():
    r = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN, "grant_type": "refresh_token"
    })
    return r.json().get("access_token")

def get_strava_data():
    try:
        token = get_access_token()
        h = {"Authorization": f"Bearer {token}"}
        athlete = requests.get("https://www.strava.com/api/v3/athlete", headers=h).json()
        stats   = requests.get(f"https://www.strava.com/api/v3/athletes/{athlete['id']}/stats", headers=h).json()
        acts    = requests.get("https://www.strava.com/api/v3/athlete/activities?per_page=20", headers=h).json()
        return athlete, stats, acts, token
    except:
        return None, None, None, None

def get_activity_streams(act_id, token):
    try:
        r = requests.get(
            f"https://www.strava.com/api/v3/activities/{act_id}/streams",
            headers={"Authorization": f"Bearer {token}"},
            params={"keys": "altitude,distance", "key_by_type": "true"},
            timeout=4
        )
        d = r.json()
        return d.get("altitude", {}).get("data", []), d.get("distance", {}).get("data", [])
    except:
        return [], []

# ── Weather ──────────────────────────────────────────────────────────────────

def get_weather():
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": WEATHER_LAT, "longitude": WEATHER_LON,
                "current": "temperature_2m,weather_code,wind_speed_10m,wind_direction_10m,precipitation_probability",
                "temperature_unit": "fahrenheit", "wind_speed_unit": "mph"
            },
            timeout=4
        )
        c = r.json().get("current", {})
        return {
            "temp":    round(c.get("temperature_2m", 0)),
            "code":    c.get("weather_code", 0),
            "wind":    round(c.get("wind_speed_10m", 0)),
            "wind_dir": c.get("wind_direction_10m", 0),
            "precip":  c.get("precipitation_probability", 0),
        }
    except:
        return None

def weather_desc(code):
    if code == 0:   return "Clear"
    if code <= 3:   return "Partly Cloudy"
    if code <= 48:  return "Foggy"
    if code <= 55:  return "Drizzle"
    if code <= 65:  return "Rain"
    if code <= 75:  return "Snow"
    if code <= 82:  return "Showers"
    return "Storms"

def weather_icon(code):
    if code == 0:   return "&#9728;"   # ☀
    if code <= 3:   return "&#9925;"   # ⛅
    if code <= 48:  return "&#127787;" # 🌫
    if code <= 65:  return "&#127783;" # 🌧
    if code <= 75:  return "&#10052;"  # ❄
    return "&#9928;"                   # ⛈

def wind_dir_label(deg):
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(deg / 22.5) % 16]

# ── Unit helpers ─────────────────────────────────────────────────────────────

def m_to_mi(m):    return round(m / 1609.34, 1)
def m_to_ft(m):    return f"{round(m * 3.28084):,}"
def s_to_hr(s):    return round(s / 3600)
def s_to_pace(s):
    m = int(s // 60); sec = int(s % 60)
    return f"{m}:{sec:02d}"
def s_to_hm(s):
    h = int(s // 3600); m = int((s % 3600) // 60)
    return f"{h}h {m}m" if h else f"{m} min"
def parse_dur(dur):
    m = re.search(r'(\d+)', str(dur))
    return int(m.group(1)) if m else None

# ── Plan helpers ─────────────────────────────────────────────────────────────

def get_today_iso():
    from datetime import date
    return date.today().isoformat()

def get_today_label():
    from datetime import date
    d = date.today()
    days   = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
    months = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
    return f"{days[d.weekday()]} &middot; {months[d.month-1]} {d.day}, {d.year}"

def get_phase_info():
    from datetime import date
    start, end = date(2026, 4, 27), date(2026, 5, 24)
    today   = date.today()
    total   = (end - start).days
    elapsed = max(0, min((today - start).days, total))
    wk      = min(4, math.ceil(elapsed / 7)) if elapsed > 0 else 1
    return wk

def get_week_days():
    from datetime import date, timedelta
    today  = date.today()
    monday = today - timedelta(days=today.weekday())
    return [(monday + timedelta(days=i)).isoformat() for i in range(7)]

def get_week_mileage(acts, week_days_isos):
    if not acts or not isinstance(acts, list):
        return 0.0
    week_set = set(week_days_isos)
    total_m = 0.0
    for a in acts:
        if not isinstance(a, dict) or a.get("type") != "Run":
            continue
        act_date = a.get("start_date_local", "")[:10]
        if act_date in week_set:
            total_m += a.get("distance", 0)
    return round(total_m / 1609.34, 1)

def workout_emoji(wtype):
    if wtype in ("run", "social"): return "&#x1F45F;"   # 👟
    if wtype == "strength":        return "&#x1F3CB;"   # 🏋
    return "&#x1F4A4;"                                   # 💤

def workout_zone_tag(wtype, title=""):
    if wtype == "strength": return "GYM"
    if wtype == "rest":     return "REST"
    if wtype == "social":   return "OPEN"
    t = title.lower()
    if "long"     in t: return "ZONE 2"
    if "recovery" in t: return "ZONE 1"
    if "tempo"    in t: return "ZONE 3"
    if "interval" in t or "speed" in t: return "ZONE 5"
    return "ZONE 2"

def get_upcoming(today_iso, n=3):
    from datetime import date
    days_s   = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    months_s = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    result = []
    for d in PLAN:
        if d["iso"] > today_iso:
            dt  = date.fromisoformat(d["iso"])
            lbl = f"{days_s[dt.weekday()].upper()} &middot; {months_s[dt.month-1].upper()} {dt.day}"
            result.append({**d, "label": lbl})
            if len(result) >= n:
                break
    return result

# ── Elevation chart ───────────────────────────────────────────────────────────

def elevation_chart_svg(altitude, distance, width, height):
    if not altitude or len(altitude) < 3:
        return (f'<svg style="width:100%;height:{height}px;display:block;" '
                f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
                f'<text x="{width//2}" y="{height//2+4}" text-anchor="middle" '
                f'font-size="10" fill="#bbb" font-family="IBM Plex Mono,monospace">No elevation data</text>'
                f'</svg>')
    alt_ft = [a * 3.28084 for a in altitude]
    n = len(alt_ft)
    if n > 120:
        step     = max(1, n // 120)
        alt_ft   = alt_ft[::step]
        distance = (distance or [])[::step] if distance else list(range(0, n, step))
    if not distance:
        distance = list(range(len(alt_ft)))

    min_a, max_a = min(alt_ft), max(alt_ft)
    rng = max_a - min_a or 1

    rough = rng / 3
    mag   = 10 ** math.floor(math.log10(rough)) if rough > 0 else 1
    ns    = mag
    for m in [1, 2, 5, 10]:
        if mag * m >= rough:
            ns = mag * m
            break
    ax_min = math.floor(min_a / ns) * ns
    ax_max = math.ceil(max_a  / ns) * ns
    ticks  = []
    v = ax_min
    while v <= ax_max + 0.01:
        ticks.append(v)
        v += ns

    y_ax = 38
    px, py = 2, 4
    cw = width - y_ax - px
    ch = height - 2 * py
    span = (ticks[-1] - ticks[0]) or 1
    min_d, max_d = distance[0], distance[-1]
    ds = max_d - min_d or 1

    pts = []
    for i, a in enumerate(alt_ft):
        x = y_ax + (distance[i] - min_d) / ds * cw
        y = py + ch - (a - ticks[0]) / span * ch
        pts.append((x, y))

    bott = py + ch
    path = (
        f"M {pts[0][0]:.1f},{bott:.1f} "
        + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts)
        + f" L {pts[-1][0]:.1f},{bott:.1f} Z"
    )

    parts = [
        f'<svg style="width:100%;height:{height}px;display:block;" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        f'<path d="{path}" fill="#ddd" stroke="#333" stroke-width="1.2" stroke-linejoin="round"/>',
    ]
    for tick in ticks:
        yp  = py + ch - (tick - ticks[0]) / span * ch
        lbl = f"{int(tick):,} ft"
        parts.append(
            f'<line x1="{y_ax}" y1="{yp:.1f}" x2="{y_ax+cw}" y2="{yp:.1f}" '
            f'stroke="#bbb" stroke-width="0.7" stroke-dasharray="3,2"/>'
        )
        parts.append(
            f'<text x="{y_ax-3}" y="{yp+3:.1f}" font-size="8" fill="#888" '
            f'text-anchor="end" font-family="IBM Plex Mono,monospace">{lbl}</text>'
        )
    parts.append('</svg>')
    return ''.join(parts)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/trmnl")
def trmnl():
    html = dashboard_html()
    return Response(json.dumps({"markup": html}), mimetype="application/json")

@app.route("/")
def dashboard():
    return Response(dashboard_html(), mimetype="text/html")

def dashboard_html():
    today_iso   = get_today_iso()
    today_label = get_today_label()
    phase_wk    = get_phase_info()
    week_days   = get_week_days()

    # Today's plan
    today_plan = next((d for d in PLAN if d["iso"] == today_iso), None)
    if today_plan:
        t_title  = today_plan["title"]
        t_detail = today_plan["detail"]
        t_tag    = today_plan["tag"]
        t_dur    = today_plan["dur"]
        t_hr     = today_plan["hr"]
        t_type   = today_plan["type"]
    else:
        t_title, t_detail, t_tag = "Rest Day", "No workout today.", "REST"
        t_dur, t_hr, t_type = "—", False, "rest"

    t_dur_num     = parse_dur(t_dur)
    t_dur_display = f"{t_dur_num}" if t_dur_num else "—"
    t_emoji       = workout_emoji(t_type)

    zone_map  = {
        "run":      "AEROBIC BASE · Zone 2",
        "social":   "OPEN EFFORT · All Welcome",
        "strength": "STRENGTH · Garage Rack",
        "rest":     "FULL REST",
    }
    t_zone = zone_map.get(t_type, "")

    hr_note = "&#9829; HR cap 138 bpm · walk at 139" if t_hr else ""

    # Coach's tip
    tip_data    = COACH_TIPS.get(t_type, COACH_TIPS["rest"])
    coach_tip   = tip_data[0]
    focus_title = tip_data[1]
    focus_sub   = tip_data[2]

    # Strava
    athlete, stats, acts, token = get_strava_data()

    if stats and isinstance(acts, list) and acts:
        ytd       = stats.get("ytd_run_totals", {})
        ytd_mi    = m_to_mi(ytd.get("distance", 0))
        ytd_cnt   = ytd.get("count", 0)
        ytd_hr    = s_to_hr(ytd.get("moving_time", 0))
        ytd_ft    = m_to_ft(ytd.get("elevation_gain", 0))
        runs = [a for a in acts if isinstance(a, dict) and a.get("type") == "Run" and a.get("distance", 0) > 100]
        if runs:
            avg_pace_s = sum(r["moving_time"] / r["distance"] * 1609.34 for r in runs) / len(runs)
            ytd_pace   = s_to_pace(avg_pace_s)
            r5         = runs[:5]
            avg_mps    = sum(r["distance"] / r["moving_time"] for r in r5) / len(r5)
            vo2        = round(min(65, max(30, avg_mps * 60 * 0.2 + 3.5)), 1)
        else:
            ytd_pace = "—"; vo2 = 0
        last_run = next((a for a in acts if isinstance(a, dict) and a.get("type") == "Run" and a.get("distance", 0) > 100), None)
        week_mi   = get_week_mileage(acts, week_days)
    else:
        ytd_mi, ytd_cnt, ytd_hr, ytd_ft, ytd_pace = "—", "—", "—", "—", "—"
        vo2 = 0
        last_run  = None
        week_mi   = 0.0

    # Weekly mileage bar
    wm_pct     = min(100, round(week_mi / WEEKLY_GOAL_MI * 100, 1)) if WEEKLY_GOAL_MI > 0 else 0
    wm_fill_w  = round(wm_pct)
    wm_remain_w = 100 - wm_fill_w

    # Last run
    ELEV_W, ELEV_H = 272, 100
    if last_run:
        la_name  = last_run.get("name", "")[:28]
        la_raw_d = last_run.get("distance", 0)
        la_movt  = last_run.get("moving_time", 0)
        la_raw_e = last_run.get("total_elevation_gain", 0)
        la_dist_val  = str(m_to_mi(la_raw_d)) if la_raw_d > 100 else "—"
        la_dist_unit = "mi"
        la_elev_val  = f"{round(la_raw_e * 3.28084)}" if la_raw_e > 1 else "—"
        la_elev_unit = "ft"
        if la_raw_d > 100 and la_movt > 0:
            la_pace_val = s_to_pace(la_movt / la_raw_d * 1609.34)
            la_time_val = s_to_hm(la_movt)
        else:
            la_pace_val = "—"
            la_time_val = s_to_hm(la_movt)
        la_pace_unit = "/mi"
        la_time_unit = "min"

        alt_d, dist_d = [], []
        if token:
            alt_d, dist_d = get_activity_streams(last_run["id"], token)
        elev_svg = elevation_chart_svg(alt_d, dist_d, ELEV_W, ELEV_H)
    else:
        la_name = "No recent activity"
        la_dist_val, la_dist_unit = "—", "mi"
        la_pace_val, la_pace_unit = "—", "/mi"
        la_time_val, la_time_unit = "—", "min"
        la_elev_val, la_elev_unit = "—", "ft"
        elev_svg = elevation_chart_svg([], [], ELEV_W, ELEV_H)

    # Weather
    wx = get_weather()
    if wx:
        wx_temp  = f"{wx['temp']}&deg;F"
        wx_cond  = weather_desc(wx["code"]).upper()
        wx_icon  = weather_icon(wx["code"])
        wx_wind  = f"{wx['wind']} mph {wind_dir_label(wx['wind_dir'])}"
        wx_rain  = f"{wx['precip']}% RAIN"
    else:
        wx_temp, wx_cond, wx_icon = "—&deg;F", "—", "&#9728;"
        wx_wind, wx_rain = "—", "—"

    # Upcoming cards
    upcoming  = get_upcoming(today_iso, 3)
    up_cards  = ""
    for i, u in enumerate(upcoming, 1):
        emoji   = workout_emoji(u["type"])
        tag_lbl = workout_zone_tag(u["type"], u["title"])
        dur_n   = parse_dur(u["dur"])
        dur_s   = f"{dur_n} min" if dur_n else u["dur"]
        up_cards += f"""
        <div class="up-card">
          <div class="up-hdr">
            <div class="up-num">{i}</div>
            <div class="up-date">{u['label']}</div>
          </div>
          <div class="up-body">
            <span class="up-emoji">{emoji}</span>
            <span class="up-name">{u['title']}</span>
          </div>
          <div class="up-foot">
            <span class="up-dur">&#9201; {dur_s}</span>
            <span class="up-tag">{tag_lbl}</span>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@400;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:100%; height:480px; overflow:hidden; background:#fff; color:#000;
          font-family:'IBM Plex Mono',monospace; font-size:11px; }}
  .screen {{ width:100%; height:480px; display:grid;
             grid-template-rows:42px 1fr 82px 110px 44px;
             border:2px solid #000; overflow:hidden; }}
  .dv {{ background:#000; width:1px; align-self:stretch; }}

  /* ── Header ── */
  .header {{ background:#000; color:#fff; display:grid;
             grid-template-columns:1fr auto auto; align-items:center;
             padding:0 16px; gap:14px; }}
  .h-title {{ font-size:18px; font-weight:700; letter-spacing:0.05em;
              text-transform:uppercase; font-family:'IBM Plex Sans',sans-serif; }}
  .h-date  {{ font-size:11px; letter-spacing:0.06em; opacity:0.85; }}
  .h-week  {{ font-size:10px; letter-spacing:0.12em; border:1.5px solid #fff;
              padding:3px 10px; text-transform:uppercase; white-space:nowrap; }}

  /* ── Main row (3 cols) ── */
  .main {{ display:grid; grid-template-columns:300px 1px 220px 1px 1fr;
           border-bottom:1px solid #000; overflow:hidden; }}

  /* Last Run */
  .col-run {{ padding:9px 12px 6px; display:flex; flex-direction:column; overflow:hidden; }}
  .s-label {{ font-size:9px; letter-spacing:0.2em; text-transform:uppercase;
              color:#888; margin-bottom:5px; }}
  .act-name-row {{ display:flex; align-items:center; gap:8px; margin-bottom:6px; }}
  .act-emoji {{ font-size:22px; line-height:1; flex-shrink:0; }}
  .act-name  {{ font-size:16px; font-weight:700; font-family:'IBM Plex Sans',sans-serif;
                line-height:1.15; letter-spacing:-0.01em;
                white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .run-stats {{ display:grid; grid-template-columns:repeat(4,1fr);
                border:1px solid #000; flex-shrink:0; margin-bottom:6px; }}
  .rs {{ padding:4px 5px; border-right:1px solid #000; }}
  .rs:last-child {{ border-right:none; }}
  .rs-lbl {{ font-size:7px; letter-spacing:0.13em; text-transform:uppercase;
             color:#999; margin-bottom:2px; }}
  .rs-val {{ font-size:18px; font-weight:700; font-family:'IBM Plex Sans',sans-serif;
             line-height:1; letter-spacing:-0.02em; }}
  .rs-unit {{ font-size:9px; color:#777; display:block; margin-top:1px; }}
  .elev-box {{ flex:1; overflow:hidden; min-height:0; }}

  /* Today */
  .col-today {{ padding:9px 13px 8px; display:flex; flex-direction:column; overflow:hidden; }}
  .today-title-row {{ display:flex; align-items:flex-start; gap:8px; margin-bottom:5px; }}
  .today-emoji {{ font-size:22px; line-height:1; flex-shrink:0; margin-top:2px; }}
  .today-name  {{ font-size:17px; font-weight:700; font-family:'IBM Plex Sans',sans-serif;
                  line-height:1.15; letter-spacing:-0.02em; }}
  .dot-sep {{ border-top:1px dashed #bbb; margin:6px 0; }}
  .today-dur-row {{ display:flex; align-items:baseline; gap:5px; margin-bottom:3px; }}
  .dur-num  {{ font-size:44px; font-weight:700; font-family:'IBM Plex Sans',sans-serif;
               line-height:1; letter-spacing:-0.04em; }}
  .dur-unit {{ font-size:13px; color:#555; font-family:'IBM Plex Sans',sans-serif; }}
  .today-zone   {{ font-size:9px; letter-spacing:0.15em; text-transform:uppercase;
                  color:#777; margin-bottom:6px; }}
  .today-detail {{ font-size:10px; color:#444; line-height:1.55; flex:1; }}
  .today-hr     {{ font-size:10px; font-weight:600; margin-top:5px; color:#333; }}
  .today-tag    {{ display:inline-block; font-size:9px; font-weight:700;
                  letter-spacing:0.12em; text-transform:uppercase;
                  background:#000; color:#fff; padding:2px 7px; margin-top:6px; }}

  /* Coach's Tip */
  .col-coach {{ padding:9px 13px 8px; display:flex; flex-direction:column; overflow:hidden; }}
  .coach-body {{ display:flex; gap:9px; align-items:flex-start; flex:1; min-height:0; }}
  .coach-icon {{ font-size:26px; flex-shrink:0; line-height:1; }}
  .coach-tip  {{ font-size:11px; color:#222; line-height:1.55; }}
  .focus-row  {{ display:flex; align-items:flex-start; justify-content:space-between; gap:6px; }}
  .focus-text {{ }}
  .focus-title {{ font-size:13px; font-weight:700; font-family:'IBM Plex Sans',sans-serif;
                  letter-spacing:-0.01em; margin-bottom:2px; }}
  .focus-sub   {{ font-size:10px; color:#555; }}
  .focus-icon  {{ font-size:28px; line-height:1; flex-shrink:0; }}

  /* ── Weekly Mileage row ── */
  .wm-row {{ display:grid; grid-template-columns:220px 1fr;
             border-bottom:1px solid #000; overflow:hidden; }}
  .wm-left {{ padding:8px 16px; display:flex; flex-direction:column; justify-content:center; }}
  .wm-label {{ font-size:9px; letter-spacing:0.2em; text-transform:uppercase;
               color:#888; margin-bottom:3px; }}
  .wm-num-row {{ display:flex; align-items:baseline; gap:5px; }}
  .wm-num {{ font-size:28px; font-weight:700; font-family:'IBM Plex Sans',sans-serif;
             letter-spacing:-0.03em; line-height:1; }}
  .wm-of  {{ font-size:13px; color:#555; font-family:'IBM Plex Sans',sans-serif; }}
  .wm-pct {{ font-size:9px; letter-spacing:0.12em; text-transform:uppercase;
             color:#888; margin-top:3px; }}
  .wm-right {{ padding:10px 16px 8px; display:flex; flex-direction:column; justify-content:center; }}
  .wm-bar-outer {{ display:flex; height:22px; border:1.5px solid #000; overflow:hidden; margin-bottom:5px; }}
  .wm-bar-fill  {{ background:#000; height:100%; }}
  .wm-bar-remain {{ flex:1; height:100%;
    background-image:repeating-linear-gradient(-45deg,#aaa,#aaa 1px,#ddd 1px,#ddd 5px); }}
  .wm-scale {{ display:flex; justify-content:space-between;
               font-size:9px; color:#888; letter-spacing:0.05em; }}

  /* ── Info row (weather + upcoming) ── */
  .info-row {{ display:grid; grid-template-columns:196px 1px 1fr; overflow:hidden; }}

  /* Weather */
  .col-weather {{ padding:10px 14px; display:flex; flex-direction:column; justify-content:center; border-right:none; }}
  .wx-row1  {{ display:flex; align-items:baseline; gap:7px; margin-bottom:3px; }}
  .wx-icon  {{ font-size:24px; line-height:1; }}
  .wx-temp  {{ font-size:28px; font-weight:700; font-family:'IBM Plex Sans',sans-serif;
               letter-spacing:-0.03em; line-height:1; }}
  .wx-cond  {{ font-size:11px; font-weight:700; text-transform:uppercase;
               letter-spacing:0.1em; margin-bottom:4px; }}
  .wx-detail {{ font-size:10px; color:#555; line-height:1.6; }}
  .wx-wind-row {{ display:flex; align-items:center; gap:6px; font-size:10px; color:#555; }}

  /* Upcoming workouts */
  .col-upcoming {{ display:grid; grid-template-columns:repeat(3,1fr); overflow:hidden; }}
  .up-card {{ padding:8px 11px; border-right:1px solid #ccc;
              display:flex; flex-direction:column; overflow:hidden; }}
  .up-card:last-child {{ border-right:none; }}
  .up-hdr  {{ display:flex; align-items:center; gap:7px; margin-bottom:5px; }}
  .up-num  {{ width:18px; height:18px; background:#000; color:#fff;
              font-size:10px; font-weight:700; display:flex; align-items:center;
              justify-content:center; flex-shrink:0; }}
  .up-date {{ font-size:9px; letter-spacing:0.1em; text-transform:uppercase; color:#888; }}
  .up-body {{ display:flex; align-items:center; gap:7px; margin-bottom:5px; flex:1; }}
  .up-emoji {{ font-size:20px; line-height:1; flex-shrink:0; }}
  .up-name  {{ font-size:13px; font-weight:700; font-family:'IBM Plex Sans',sans-serif;
               line-height:1.2; letter-spacing:-0.01em; }}
  .up-foot  {{ display:flex; align-items:center; justify-content:space-between; gap:4px; }}
  .up-dur   {{ font-size:9px; color:#666; white-space:nowrap; overflow:hidden;
               text-overflow:ellipsis; }}
  .up-tag   {{ display:inline-block; font-size:8px; font-weight:700; letter-spacing:0.08em;
               background:#000; color:#fff; padding:2px 5px; text-transform:uppercase;
               white-space:nowrap; flex-shrink:0; }}

  /* ── YTD Banner ── */
  .ytd-banner {{ display:grid; grid-template-columns:repeat(5,1fr);
                 background:#000; color:#fff; }}
  .ytd-stat {{ display:flex; flex-direction:column; justify-content:center; align-items:center;
               padding:0 4px; border-right:1px solid #333; }}
  .ytd-stat:last-child {{ border-right:none; }}
  .ytd-label {{ font-size:7px; letter-spacing:0.15em; color:#888;
                text-transform:uppercase; margin-bottom:1px; }}
  .ytd-val {{ font-size:14px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; line-height:1; }}
  .ytd-sub {{ font-size:8px; color:#666; margin-top:1px; }}
</style>
</head>
<body>
<div class="screen">

  <!-- Header -->
  <div class="header">
    <div class="h-title">Training Snapshot</div>
    <div class="h-date">{today_label}</div>
    <div class="h-week">Week {phase_wk} / 4</div>
  </div>

  <!-- Main row -->
  <div class="main">

    <!-- LAST RUN -->
    <div class="col-run">
      <div class="s-label">Last Run</div>
      <div class="act-name-row">
        <span class="act-emoji">&#x1F45F;</span>
        <span class="act-name">{la_name}</span>
      </div>
      <div class="run-stats">
        <div class="rs">
          <div class="rs-lbl">Distance</div>
          <div class="rs-val">{la_dist_val}</div>
          <span class="rs-unit">{la_dist_unit}</span>
        </div>
        <div class="rs">
          <div class="rs-lbl">Avg Pace</div>
          <div class="rs-val">{la_pace_val}</div>
          <span class="rs-unit">{la_pace_unit}</span>
        </div>
        <div class="rs">
          <div class="rs-lbl">Moving Time</div>
          <div class="rs-val">{la_time_val}</div>
          <span class="rs-unit">{la_time_unit}</span>
        </div>
        <div class="rs">
          <div class="rs-lbl">Elev Gain</div>
          <div class="rs-val">{la_elev_val}</div>
          <span class="rs-unit">{la_elev_unit}</span>
        </div>
      </div>
      <div class="elev-box">{elev_svg}</div>
    </div>

    <div class="dv"></div>

    <!-- TODAY -->
    <div class="col-today">
      <div class="s-label">Today</div>
      <div class="today-title-row">
        <span class="today-emoji">{t_emoji}</span>
        <span class="today-name">{t_title}</span>
      </div>
      <div class="dot-sep"></div>
      <div class="today-dur-row">
        <span class="dur-num">{t_dur_display}</span>
        <span class="dur-unit">min</span>
      </div>
      <div class="today-zone">{t_zone}</div>
      <div class="dot-sep"></div>
      <div class="today-detail">{t_emoji} {t_detail}</div>
      {f'<div class="today-hr">{hr_note}</div>' if hr_note else ''}
      <div class="today-tag">{t_tag}</div>
    </div>

    <div class="dv"></div>

    <!-- COACH'S TIP -->
    <div class="col-coach">
      <div class="s-label">Coach&#x2019;s Tip</div>
      <div class="coach-body">
        <span class="coach-icon">&#x1F4CB;</span>
        <span class="coach-tip">{coach_tip}</span>
      </div>
      <div class="dot-sep"></div>
      <div class="s-label">Focus</div>
      <div class="focus-row">
        <div class="focus-text">
          <div class="focus-title">{focus_title}</div>
          <div class="focus-sub">{focus_sub}</div>
        </div>
        <span class="focus-icon">&#x26F0;&#xFE0F;</span>
      </div>
    </div>

  </div>

  <!-- Weekly Mileage -->
  <div class="wm-row">
    <div class="wm-left">
      <div class="wm-label">Weekly Mileage</div>
      <div class="wm-num-row">
        <span class="wm-num">{week_mi}</span>
        <span class="wm-of">/ {int(WEEKLY_GOAL_MI)} mi</span>
      </div>
      <div class="wm-pct">{wm_pct}% of goal</div>
    </div>
    <div class="wm-right">
      <div class="wm-bar-outer">
        <div class="wm-bar-fill" style="width:{wm_fill_w}%"></div>
        <div class="wm-bar-remain"></div>
      </div>
      <div class="wm-scale">
        <span>0 mi</span>
        <span>{int(WEEKLY_GOAL_MI / 2)} mi</span>
        <span>{int(WEEKLY_GOAL_MI)} mi</span>
      </div>
    </div>
  </div>

  <!-- Info row -->
  <div class="info-row">

    <!-- Weather -->
    <div class="col-weather">
      <div class="wx-row1">
        <span class="wx-icon">{wx_icon}</span>
        <span class="wx-temp">{wx_temp}</span>
      </div>
      <div class="wx-cond">{wx_cond}</div>
      <div class="wx-detail">{wx_rain}</div>
      <div class="wx-wind-row">&#x1F4A8; {wx_wind}</div>
    </div>

    <div class="dv"></div>

    <!-- Upcoming workouts (3 cards, no header label — self-evident) -->
    <div class="col-upcoming">
      {up_cards}
    </div>

  </div>

  <!-- YTD Banner -->
  <div class="ytd-banner">
    <div class="ytd-stat">
      <div class="ytd-label">Distance YTD</div>
      <div class="ytd-val">{ytd_mi} mi</div>
      <div class="ytd-sub">{ytd_cnt} runs</div>
    </div>
    <div class="ytd-stat">
      <div class="ytd-label">Time YTD</div>
      <div class="ytd-val">{ytd_hr} hr</div>
      <div class="ytd-sub">moving time</div>
    </div>
    <div class="ytd-stat">
      <div class="ytd-label">Avg Pace</div>
      <div class="ytd-val">{ytd_pace}</div>
      <div class="ytd-sub">min / mile</div>
    </div>
    <div class="ytd-stat">
      <div class="ytd-label">Elev Gain YTD</div>
      <div class="ytd-val">{ytd_ft} ft</div>
      <div class="ytd-sub">year to date</div>
    </div>
    <div class="ytd-stat">
      <div class="ytd-label">VO2max Est.</div>
      <div class="ytd-val">{vo2}</div>
      <div class="ytd-sub">mL/kg/min</div>
    </div>
  </div>

</div>
</body>
</html>"""

    return html

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
