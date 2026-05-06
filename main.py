from flask import Flask, Response
import requests, os, json, math, re

app = Flask(__name__)

CLIENT_ID      = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET  = os.environ.get("STRAVA_CLIENT_SECRET")
REFRESH_TOKEN  = os.environ.get("STRAVA_REFRESH_TOKEN")
WEATHER_LAT    = os.environ.get("WEATHER_LAT", "34.85")
WEATHER_LON    = os.environ.get("WEATHER_LON", "-82.39")
WEEKLY_GOAL_MI = float(os.environ.get("WEEKLY_GOAL_MI", "20"))

PLAN = [
  {"iso":"2026-04-27","type":"run",     "title":"Recovery Run",         "detail":"30 min · nasal breathing","dur":"30m","hr":True},
  {"iso":"2026-04-28","type":"social",  "title":"Upstate RC Social Run","detail":"Open HR · distance varies","dur":"~45m","hr":False},
  {"iso":"2026-04-29","type":"strength","title":"Full Body B",           "detail":"Deadlift · Bench · Pull-ups · Assault Bike","dur":"60m","hr":False},
  {"iso":"2026-04-30","type":"run",     "title":"Base Run",             "detail":"30 min · strict aerobic","dur":"30m","hr":True},
  {"iso":"2026-05-01","type":"rest",    "title":"Rest & Review",        "detail":"Full rest · prep for long run","dur":"—","hr":False},
  {"iso":"2026-05-02","type":"run",     "title":"Long Run",             "detail":"60-90 min easy · ankle warm-up","dur":"90m","hr":True},
  {"iso":"2026-05-03","type":"strength","title":"Full Body A",           "detail":"Squat · OHP · Row · Sandbag","dur":"60m","hr":False},
  {"iso":"2026-05-04","type":"run",     "title":"Recovery Run",         "detail":"30 min · nasal breathing","dur":"30m","hr":True},
  {"iso":"2026-05-05","type":"social",  "title":"Upstate RC Social Run","detail":"Open HR · push if you feel good","dur":"~45m","hr":False},
  {"iso":"2026-05-06","type":"strength","title":"Full Body B",           "detail":"Deadlift · Bench · Pull-ups · Assault Bike","dur":"60m","hr":False},
  {"iso":"2026-05-07","type":"run",     "title":"Base Run",             "detail":"30 min · strict aerobic volume","dur":"30m","hr":True},
  {"iso":"2026-05-08","type":"rest",    "title":"Rest & Review",        "detail":"Full rest · prep for long run","dur":"—","hr":False},
  {"iso":"2026-05-09","type":"run",     "title":"Long Run",             "detail":"60-90 min easy · ankle warm-up","dur":"90m","hr":True},
  {"iso":"2026-05-10","type":"strength","title":"Full Body A",           "detail":"Squat · OHP · Row · Sandbag","dur":"60m","hr":False},
  {"iso":"2026-05-11","type":"run",     "title":"Recovery Run",         "detail":"30 min · nasal breathing","dur":"30m","hr":True},
  {"iso":"2026-05-12","type":"social",  "title":"Upstate RC Social Run","detail":"Open HR · enjoy the group","dur":"~45m","hr":False},
  {"iso":"2026-05-13","type":"strength","title":"Full Body B",           "detail":"Deadlift · Bench · Pull-ups · Assault Bike","dur":"60m","hr":False},
  {"iso":"2026-05-14","type":"run",     "title":"Base Run",             "detail":"30 min · strict aerobic volume","dur":"30m","hr":True},
  {"iso":"2026-05-15","type":"rest",    "title":"Rest & Review",        "detail":"Full rest · review the week","dur":"—","hr":False},
  {"iso":"2026-05-16","type":"run",     "title":"Long Run",             "detail":"60-90 min easy · ankle warm-up","dur":"90m","hr":True},
  {"iso":"2026-05-17","type":"strength","title":"Full Body A",           "detail":"Squat · OHP · Row · Sandbag","dur":"60m","hr":False},
]

COACH_TIPS = {
  "run":      ("Stay patient on climbs and shorten your stride on descents. Build volume consistently.", "Aerobic Base", "Consistency > Intensity"),
  "social":   ("Group runs sharpen mental fitness. Stay aerobic and enjoy the company.", "Community Run", "Run Happy · Run Easy"),
  "strength": ("Move through full range of motion on every rep. Quality reps beat heavy weights.", "Strength & Mobility", "Form First · Always"),
  "rest":     ("Rest days are when your body adapts. Sleep well, eat well, and recover fully.", "Active Recovery", "Rest = Progress"),
}

# ── SVG icon helpers ──────────────────────────────────────────────────────────

def _svg(body, w, h, vw, vh, sw=1.6, extra=""):
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {vw} {vh}" fill="none" '
            f'stroke="#000" stroke-width="{sw}" stroke-linecap="round" '
            f'stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg" {extra}>'
            f'{body}</svg>')

def icon_shoe(w=22, h=16):
    # simple side-view running shoe
    body = ('<path d="M2 12L2 9C2 7 4 6 6 6L12 6L14 3C15 2 17 2 18 3L19 6'
            'L21 6C23 6 24 8 24 10L24 11L22 12Z"/>'
            '<line x1="7" y1="6" x2="7" y2="4"/>')
    return _svg(body, w, h, 25, 14, sw=1.7)

def icon_kettlebell(w=18, h=22):
    body = ('<circle cx="9" cy="16" r="6"/>'
            '<path d="M5 10C5 6 7 4 9 4C11 4 13 6 13 10"/>'
            '<line x1="5" y1="10" x2="13" y2="10"/>')
    return _svg(body, w, h, 18, 24, sw=1.6)

def icon_stopwatch(w=15, h=17):
    body = ('<circle cx="8" cy="11" r="6"/>'
            '<path d="M8 7L8 11L11 13"/>'
            '<line x1="6" y1="1" x2="10" y2="1"/>'
            '<line x1="8" y1="1" x2="8" y2="4"/>')
    return _svg(body, w, h, 16, 19, sw=1.5)

def icon_clipboard(w=20, h=24):
    body = ('<rect x="3" y="4" width="16" height="19" rx="1"/>'
            '<path d="M8 4V2.5C8 1.7 8.7 1 9.5 1H12.5C13.3 1 14 1.7 14 2.5V4"/>'
            '<line x1="6" y1="10" x2="16" y2="10"/>'
            '<line x1="6" y1="14" x2="16" y2="14"/>'
            '<line x1="6" y1="18" x2="12" y2="18"/>')
    return _svg(body, w, h, 22, 26, sw=1.4)

def icon_mountain(w=28, h=20):
    body = '<path d="M1 20L10 4L16 12L20 8L31 20Z"/>'
    return _svg(body, w, h, 32, 22, sw=1.7)

def icon_sun(w=22, h=22):
    body = ('<circle cx="11" cy="11" r="4.5"/>'
            '<line x1="11" y1="1" x2="11" y2="4"/>'
            '<line x1="11" y1="18" x2="11" y2="21"/>'
            '<line x1="1" y1="11" x2="4" y2="11"/>'
            '<line x1="18" y1="11" x2="21" y2="11"/>'
            '<line x1="3.8" y1="3.8" x2="5.9" y2="5.9"/>'
            '<line x1="16.1" y1="16.1" x2="18.2" y2="18.2"/>'
            '<line x1="18.2" y1="3.8" x2="16.1" y2="5.9"/>'
            '<line x1="5.9" y1="16.1" x2="3.8" y2="18.2"/>')
    return _svg(body, w, h, 22, 22, sw=1.5)

def icon_partly_cloudy(w=26, h=20):
    body = ('<circle cx="9" cy="9" r="4"/>'
            '<line x1="9" y1="2" x2="9" y2="4"/>'
            '<line x1="9" y1="14" x2="9" y2="16"/>'
            '<line x1="2" y1="9" x2="4" y2="9"/>'
            '<line x1="14" y1="9" x2="16" y2="9"/>'
            '<path d="M22 17H13a4 4 0 0 1-.1-8 4.5 4.5 0 0 1 8.8 0A3 3 0 0 1 22 17Z"/>')
    return _svg(body, w, h, 26, 20, sw=1.4)

def icon_rain(w=22, h=22):
    body = ('<path d="M19 11H5a5 5 0 0 1-.1-10 6 6 0 0 1 11.8 0A4 4 0 0 1 19 11Z"/>'
            '<line x1="6" y1="16" x2="5" y2="20"/>'
            '<line x1="11" y1="16" x2="10" y2="20"/>'
            '<line x1="16" y1="16" x2="15" y2="20"/>')
    return _svg(body, w, h, 22, 22, sw=1.4)

def icon_wind(w=20, h=14):
    body = ('<path d="M2 3h11c2 0 3-1 3-2"/>'
            '<line x1="2" y1="7" x2="9" y2="7"/>'
            '<path d="M2 11h12c2 0 4 1 4 3"/>')
    return _svg(body, w, h, 22, 14, sw=1.4)

def wx_icon(code, w=24):
    if code == 0:   return icon_sun(w, w)
    if code <= 3:   return icon_partly_cloudy(w, int(w * 20 / 26))
    if code <= 65:  return icon_rain(w, w)
    return icon_partly_cloudy(w, int(w * 20 / 26))

def workout_icon(wtype, w=22):
    if wtype in ("run", "social"): return icon_shoe(w, int(w * 16 / 22))
    if wtype == "strength":        return icon_kettlebell(int(w * 18 / 22), w)
    return ""

# ── Strava ────────────────────────────────────────────────────────────────────

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

# ── Weather ───────────────────────────────────────────────────────────────────

def get_weather():
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": WEATHER_LAT, "longitude": WEATHER_LON,
            "current": "temperature_2m,weather_code,wind_speed_10m,wind_direction_10m,precipitation_probability",
            "temperature_unit": "fahrenheit", "wind_speed_unit": "mph"
        }, timeout=4)
        c = r.json().get("current", {})
        return {"temp": round(c.get("temperature_2m", 0)), "code": c.get("weather_code", 0),
                "wind": round(c.get("wind_speed_10m", 0)), "wind_dir": c.get("wind_direction_10m", 0),
                "precip": c.get("precipitation_probability", 0)}
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

def wind_dir_label(deg):
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(deg / 22.5) % 16]

# ── Unit helpers ──────────────────────────────────────────────────────────────

def m_to_mi(m):  return round(m / 1609.34, 1)
def m_to_ft(m):  return f"{round(m * 3.28084):,}"
def s_to_hr(s):  return round(s / 3600)
def s_to_pace(s):
    m = int(s // 60); sec = int(s % 60)
    return f"{m}:{sec:02d}"
def s_to_mmss(s):
    m = int(s // 60); sec = int(s % 60)
    return f"{m}:{sec:02d}"
def s_to_hm(s):
    h = int(s // 3600); m = int((s % 3600) // 60)
    return f"{h}h {m}m" if h else f"{m} min"
def parse_dur(dur):
    m = re.search(r'(\d+)', str(dur))
    return int(m.group(1)) if m else None

# ── Plan helpers ──────────────────────────────────────────────────────────────

def get_today_iso():
    from datetime import date
    return date.today().isoformat()

def get_today_label():
    from datetime import date
    d = date.today()
    days   = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
    months = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
    return f"{days[d.weekday()]} &bull; {months[d.month-1]} {d.day}, {d.year}"

def get_phase_wk():
    from datetime import date
    start, end = date(2026, 4, 27), date(2026, 5, 24)
    today   = date.today()
    total   = (end - start).days
    elapsed = max(0, min((today - start).days, total))
    return min(4, math.ceil(elapsed / 7)) if elapsed > 0 else 1

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
        if a.get("start_date_local", "")[:10] in week_set:
            total_m += a.get("distance", 0)
    return round(total_m / 1609.34, 1)

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
            lbl = f"{days_s[dt.weekday()].upper()} &bull; {months_s[dt.month-1].upper()} {dt.day}"
            result.append({**d, "label": lbl})
            if len(result) >= n:
                break
    return result

# ── Elevation chart SVG ───────────────────────────────────────────────────────

def elevation_chart_svg(altitude, distance, width, height):
    if not altitude or len(altitude) < 3:
        return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
                f'xmlns="http://www.w3.org/2000/svg">'
                f'<line x1="36" y1="{height-4}" x2="{width-2}" y2="{height-4}" '
                f'stroke="#ccc" stroke-width="1"/>'
                f'<text x="{(width+36)//2}" y="{height//2+4}" text-anchor="middle" '
                f'font-size="9" fill="#bbb" font-family="IBM Plex Mono,monospace">no elevation data</text>'
                f'</svg>')

    alt_ft = [a * 3.28084 for a in altitude]
    n = len(alt_ft)
    if n > 120:
        step = max(1, n // 120)
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

    y_ax = 36; px = 2; py = 3
    cw = width - y_ax - px
    ch = height - 2 * py
    span = (ticks[-1] - ticks[0]) or 1
    min_d = distance[0]; max_d = distance[-1]
    ds = max_d - min_d or 1

    pts = []
    for i, a in enumerate(alt_ft):
        x = y_ax + (distance[i] - min_d) / ds * cw
        y = py + ch - (a - ticks[0]) / span * ch
        pts.append((x, y))

    bott = py + ch
    path = (f"M {pts[0][0]:.1f},{bott} "
            + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts)
            + f" L {pts[-1][0]:.1f},{bott} Z")

    parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
             f'xmlns="http://www.w3.org/2000/svg">',
             f'<path d="{path}" fill="#ddd" stroke="#444" stroke-width="1.2" stroke-linejoin="round"/>']

    for tick in ticks:
        yp  = py + ch - (tick - ticks[0]) / span * ch
        lbl = f"{int(tick):,} ft"
        parts.append(f'<line x1="{y_ax}" y1="{yp:.1f}" x2="{y_ax+cw}" y2="{yp:.1f}" '
                     f'stroke="#bbb" stroke-width="0.8" stroke-dasharray="3,2"/>')
        parts.append(f'<text x="{y_ax-3}" y="{yp+3.5:.1f}" font-size="8" fill="#888" '
                     f'text-anchor="end" font-family="IBM Plex Mono,monospace">{lbl}</text>')
    parts.append('</svg>')
    return ''.join(parts)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/trmnl")
def trmnl():
    return Response(json.dumps({"markup": dashboard_html()}), mimetype="application/json")

@app.route("/")
def dashboard():
    return Response(dashboard_html(), mimetype="text/html")

def dashboard_html():
    today_iso   = get_today_iso()
    today_label = get_today_label()
    phase_wk    = get_phase_wk()
    week_days   = get_week_days()

    # Today's plan
    today_plan = next((d for d in PLAN if d["iso"] == today_iso), None)
    if today_plan:
        t_type, t_title, t_detail = today_plan["type"], today_plan["title"], today_plan["detail"]
        t_dur, t_hr = today_plan["dur"], today_plan["hr"]
    else:
        t_type, t_title, t_detail = "rest", "Rest Day", "No workout scheduled."
        t_dur, t_hr = "—", False

    t_dur_num  = parse_dur(t_dur)
    t_dur_disp = str(t_dur_num) if t_dur_num else "—"
    t_icon_svg = workout_icon(t_type, 22)

    zone_map = {
        "run":      "AEROBIC BASE · ZONE 2",
        "social":   "OPEN EFFORT",
        "strength": "STRENGTH FOCUS",
        "rest":     "FULL REST",
    }
    t_zone = zone_map.get(t_type, "")
    hr_note = "HR cap 138 bpm · walk at 139" if t_hr else ""

    # Coach's tip
    tip_data    = COACH_TIPS.get(t_type, COACH_TIPS["rest"])
    coach_tip, focus_title, focus_sub = tip_data

    # Strava
    athlete, stats, acts, token = get_strava_data()

    if stats and isinstance(acts, list) and acts:
        ytd      = stats.get("ytd_run_totals", {})
        ytd_mi   = m_to_mi(ytd.get("distance", 0))
        ytd_cnt  = ytd.get("count", 0)
        ytd_hr   = s_to_hr(ytd.get("moving_time", 0))
        ytd_ft   = m_to_ft(ytd.get("elevation_gain", 0))
        runs     = [a for a in acts if isinstance(a, dict) and a.get("type") == "Run" and a.get("distance", 0) > 100]
        if runs:
            avg_pace_s = sum(r["moving_time"] / r["distance"] * 1609.34 for r in runs) / len(runs)
            ytd_pace   = s_to_pace(avg_pace_s)
            r5         = runs[:5]
            avg_mps    = sum(r["distance"] / r["moving_time"] for r in r5) / len(r5)
            vo2        = round(min(65, max(30, avg_mps * 60 * 0.2 + 3.5)), 1)
        else:
            ytd_pace = "—"; vo2 = 0
        last_run = next((a for a in acts if isinstance(a, dict) and a.get("type") == "Run" and a.get("distance", 0) > 100), None)
        week_mi  = get_week_mileage(acts, week_days)
    else:
        ytd_mi, ytd_cnt, ytd_hr, ytd_ft, ytd_pace = "—", "—", "—", "—", "—"
        vo2 = 0; last_run = None; week_mi = 0.0

    wm_pct      = min(100, round(week_mi / WEEKLY_GOAL_MI * 100)) if WEEKLY_GOAL_MI > 0 else 0
    goal_int    = int(WEEKLY_GOAL_MI)
    wm_tick_labels = [str(int(i * WEEKLY_GOAL_MI / 4)) for i in range(4)] + [f"{goal_int} mi"]
    wm_ticks_html  = "".join(
        f'<div class="wm-tick"><span class="wm-tick-lbl">{lbl}</span></div>'
        for lbl in wm_tick_labels
    )

    # Last run
    ELEV_W, ELEV_H = 268, 88
    if last_run:
        la_name    = last_run.get("name", "Activity")[:28]
        la_raw_d   = last_run.get("distance", 0)
        la_movt    = last_run.get("moving_time", 0)
        la_raw_e   = last_run.get("total_elevation_gain", 0)
        la_dist    = str(m_to_mi(la_raw_d)) if la_raw_d > 100 else "—"
        la_elev    = str(round(la_raw_e * 3.28084)) if la_raw_e > 1 else "—"
        la_pace    = s_to_pace(la_movt / la_raw_d * 1609.34) if la_raw_d > 100 and la_movt > 0 else "—"
        la_time    = s_to_mmss(la_movt) if la_movt > 0 else "—"
        alt_d, dist_d = get_activity_streams(last_run["id"], token) if token else ([], [])
        elev_svg   = elevation_chart_svg(alt_d, dist_d, ELEV_W, ELEV_H)
    else:
        la_name = "No recent run"
        la_dist = la_pace = la_time = la_elev = "—"
        elev_svg = elevation_chart_svg([], [], ELEV_W, ELEV_H)

    # Weather
    wx = get_weather()
    if wx:
        wx_temp = f"{wx['temp']}&deg;F"
        wx_cond = weather_desc(wx["code"]).upper()
        wx_svg  = wx_icon(wx["code"], 24)
        wx_wind = f"{wx['wind']} mph {wind_dir_label(wx['wind_dir'])}"
        wx_rain = f"{wx['precip']}% RAIN"
    else:
        wx_temp, wx_cond, wx_wind, wx_rain = "&mdash;&deg;F", "&mdash;", "", "&mdash;"
        wx_svg = icon_sun(24, 24)

    # Upcoming cards
    upcoming = get_upcoming(today_iso, 3)
    up_cards = ""
    for i, u in enumerate(upcoming, 1):
        ico   = workout_icon(u["type"], 24)
        tag   = workout_zone_tag(u["type"], u["title"])
        dur_n = parse_dur(u["dur"])
        dur_s = f"{dur_n} min" if dur_n else u["dur"]
        up_cards += f"""<div class="up-card">
  <div class="up-hdr"><span class="up-num">{i}</span><span class="up-date">{u['label']}</span></div>
  <div class="up-icon">{ico}</div>
  <div class="up-name">{u['title']}</div>
  <div class="up-foot">
    <span class="up-dur">{icon_stopwatch(13,15)} {dur_s}</span>
    <span class="up-tag">{tag}</span>
  </div>
</div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@400;700&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
body{{width:100%;height:480px;overflow:hidden;background:#fff;color:#000;
     font-family:'IBM Plex Mono',monospace;font-size:11px}}
svg{{display:inline-block;vertical-align:middle;flex-shrink:0}}

/* Screen grid: header | main | weekly-mi | info | ytd */
.screen{{width:100%;height:480px;display:grid;
         grid-template-rows:42px 1fr 80px 118px 44px;
         border:2px solid #000;overflow:hidden}}
.dv{{width:1px;background:#000;align-self:stretch}}

/* ── HEADER ── */
.hdr{{background:#000 !important;color:#fff !important;display:flex;align-items:center;
      padding:0 16px;gap:12px;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.hdr-title{{font-size:18px;font-weight:700;letter-spacing:0.05em;
            text-transform:uppercase;font-family:'IBM Plex Sans',sans-serif;flex:1}}
.hdr-date{{font-size:11px;letter-spacing:0.06em;opacity:.85;white-space:nowrap}}
.hdr-week{{font-size:10px;letter-spacing:0.12em;border:1.5px solid #fff;
           padding:3px 10px;text-transform:uppercase;white-space:nowrap}}

/* ── MAIN (3 cols) ── */
.main{{display:grid;grid-template-columns:310px 1px 210px 1px 1fr;
       border-bottom:1px solid #000;overflow:hidden}}

/* Last Run */
.col-run{{padding:9px 12px 6px;display:flex;flex-direction:column;overflow:hidden}}
.s-lbl{{font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:#888;margin-bottom:4px}}
.act-row{{display:flex;align-items:center;gap:8px;margin-bottom:6px}}
.act-name{{font-size:21px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
           line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.stats-grid{{display:grid;grid-template-columns:repeat(4,1fr);
             border:1px solid #000;flex-shrink:0;margin-bottom:6px}}
.st{{padding:4px 6px;border-right:1px solid #000}}
.st:last-child{{border-right:none}}
.st-lbl{{font-size:7px;letter-spacing:.12em;text-transform:uppercase;color:#999;margin-bottom:1px}}
.st-val{{font-size:20px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
         line-height:1;letter-spacing:-.02em}}
.st-unit{{font-size:9px;color:#777;display:block;margin-top:1px}}
.elev-box{{overflow:hidden;flex-shrink:0}}

/* Today */
.col-today{{padding:9px 12px 7px;display:flex;flex-direction:column;overflow:hidden}}
.today-title{{display:flex;align-items:flex-start;gap:7px;margin-bottom:4px}}
.today-name{{font-size:17px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
             line-height:1.15;letter-spacing:-.02em}}
.dsep{{border-top:1px dashed #bbb;margin:5px 0}}
.dur-row{{display:flex;align-items:baseline;gap:4px;margin-bottom:3px}}
.dur-num{{font-size:44px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
          line-height:1;letter-spacing:-.04em}}
.dur-unit{{font-size:13px;color:#555;font-family:'IBM Plex Sans',sans-serif}}
.t-zone{{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:#777;margin-bottom:5px}}
.t-detail{{font-size:10px;color:#444;line-height:1.55;flex:1}}
.t-hr{{font-size:9px;color:#333;margin-top:4px}}
.t-tag{{display:inline-block;font-size:9px;font-weight:700;letter-spacing:.1em;
        text-transform:uppercase;background:#000;color:#fff;padding:2px 7px;margin-top:5px}}

/* Coach's Tip */
.col-coach{{padding:9px 12px 7px;display:flex;flex-direction:column;overflow:hidden}}
.coach-body{{display:flex;gap:9px;align-items:flex-start;flex:1;min-height:0;margin-bottom:4px}}
.coach-text{{font-size:11px;color:#222;line-height:1.55}}
.focus-row{{display:flex;align-items:flex-end;justify-content:space-between;gap:4px}}
.focus-title{{font-size:13px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
              letter-spacing:-.01em;margin-bottom:2px}}
.focus-sub{{font-size:10px;color:#555}}

/* ── WEEKLY MILEAGE ── */
.wm-row{{display:grid;grid-template-columns:210px 1fr;
         border-bottom:1px solid #000;overflow:hidden}}
.wm-left{{padding:7px 16px;display:flex;flex-direction:column;justify-content:center}}
.wm-lbl{{font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:#888;margin-bottom:3px}}
.wm-nums{{display:flex;align-items:baseline;gap:4px;line-height:1}}
.wm-num{{font-size:28px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;letter-spacing:-.03em}}
.wm-goal{{font-size:13px;color:#555;font-family:'IBM Plex Sans',sans-serif}}
.wm-pct{{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:#888;margin-top:3px}}
.wm-right{{padding:10px 16px 6px;display:flex;flex-direction:column;justify-content:center}}
.wm-bar{{display:flex;height:24px;border:1.5px solid #000;overflow:hidden;margin-bottom:3px}}
.wm-fill{{background:#000;height:100%}}
.wm-remain{{flex:1;height:100%;
  background:repeating-linear-gradient(-45deg,#aaa,#aaa 1px,#ddd 1px,#ddd 5px)}}
.wm-scale{{display:flex;justify-content:space-between}}
.wm-tick{{display:flex;flex-direction:column;align-items:center;gap:1px}}
.wm-tick::before{{content:'';width:1px;height:5px;background:#999;display:block}}
.wm-tick-lbl{{font-size:8px;color:#888}}

/* ── INFO ROW ── */
.info-row{{display:grid;grid-template-columns:190px 1px 1fr;overflow:hidden}}

/* Weather */
.col-wx{{padding:7px 14px 8px;display:flex;flex-direction:column;justify-content:flex-start}}
.wx-top{{display:flex;align-items:center;gap:8px;margin-bottom:4px}}
.wx-temp{{font-size:28px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
          letter-spacing:-.03em;line-height:1}}
.wx-cond{{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
          margin-bottom:4px}}
.wx-detail{{font-size:10px;color:#555;line-height:1.7}}
.wx-wind-row{{display:flex;align-items:center;gap:6px;font-size:10px;color:#555;margin-top:2px}}

/* Upcoming */
.col-up-wrap{{display:flex;flex-direction:column;overflow:hidden}}
.up-head{{font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:#888;
          padding:5px 11px 4px;border-bottom:1px solid #ccc;flex-shrink:0}}
.col-up{{display:grid;grid-template-columns:repeat(3,1fr);flex:1;overflow:hidden}}
.up-card{{padding:6px 11px 5px;border-right:1px solid #999;
          display:flex;flex-direction:column;overflow:hidden}}
.up-card:last-child{{border-right:none}}
.up-hdr{{display:flex;align-items:center;gap:6px;margin-bottom:6px}}
.up-num{{width:18px;height:18px;background:#000;color:#fff;font-size:10px;
         font-weight:700;display:flex;align-items:center;justify-content:center;
         flex-shrink:0;font-family:'IBM Plex Mono',monospace}}
.up-date{{font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#333}}
.up-icon{{margin-bottom:4px}}
.up-name{{font-size:16px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
          line-height:1.2;letter-spacing:-.01em;flex:1;margin-bottom:4px}}
.up-foot{{display:flex;align-items:center;justify-content:space-between;gap:4px}}
.up-dur{{display:flex;align-items:center;gap:4px;font-size:9px;color:#555;
         white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.up-tag{{display:inline-block;font-size:8px;font-weight:700;letter-spacing:.08em;
         background:#000;color:#fff;padding:2px 5px;text-transform:uppercase;
         white-space:nowrap;flex-shrink:0}}

/* ── YTD BANNER ── */
.ytd{{display:grid;grid-template-columns:repeat(5,1fr);background:#000;color:#fff}}
.yt{{display:flex;flex-direction:column;justify-content:center;align-items:center;
     border-right:1px solid #333;padding:0 4px}}
.yt:last-child{{border-right:none}}
.yt-lbl{{font-size:7px;letter-spacing:.14em;color:#888;text-transform:uppercase;margin-bottom:1px}}
.yt-val{{font-size:14px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;line-height:1}}
.yt-sub{{font-size:8px;color:#666;margin-top:1px}}
</style>
</head>
<body>
<div class="screen">

<div class="hdr">
  <div class="hdr-title">Training Snapshot</div>
  <div class="hdr-date">{today_label}</div>
  <div class="hdr-week">Week {phase_wk} / 4</div>
</div>

<div class="main">

  <!-- LAST RUN -->
  <div class="col-run">
    <div class="s-lbl">Last Run</div>
    <div class="act-row">
      {icon_shoe(22, 16)}
      <span class="act-name">{la_name}</span>
    </div>
    <div class="stats-grid">
      <div class="st"><div class="st-lbl">Distance</div><div class="st-val">{la_dist}</div><span class="st-unit">mi</span></div>
      <div class="st"><div class="st-lbl">Avg Pace</div><div class="st-val">{la_pace}</div><span class="st-unit">/mi</span></div>
      <div class="st"><div class="st-lbl">Moving Time</div><div class="st-val">{la_time}</div><span class="st-unit">min</span></div>
      <div class="st"><div class="st-lbl">Elev Gain</div><div class="st-val">{la_elev}</div><span class="st-unit">ft</span></div>
    </div>
    <div class="elev-box">{elev_svg}</div>
  </div>

  <div class="dv"></div>

  <!-- TODAY -->
  <div class="col-today">
    <div class="s-lbl">Today</div>
    <div class="today-title">
      {t_icon_svg}
      <span class="today-name">{t_title}</span>
    </div>
    <div class="dsep"></div>
    <div class="dur-row">
      <span class="dur-num">{t_dur_disp}</span>
      <span class="dur-unit">min</span>
    </div>
    <div class="t-zone">{t_zone}</div>
    <div class="dsep"></div>
    <div class="t-detail">{t_icon_svg} {t_detail}</div>
    {f'<div class="t-hr">{hr_note}</div>' if hr_note else ''}
    <div class="t-tag">{t_type.upper()}</div>
  </div>

  <div class="dv"></div>

  <!-- COACH'S TIP -->
  <div class="col-coach">
    <div class="s-lbl">Coach&#8217;s Tip</div>
    <div class="dsep"></div>
    <div class="coach-body">
      {icon_clipboard(20, 24)}
      <span class="coach-text">{coach_tip}</span>
    </div>
    <div class="dsep"></div>
    <div class="s-lbl">Focus</div>
    <div class="focus-row">
      <div>
        <div class="focus-title">{focus_title}</div>
        <div class="focus-sub">{focus_sub}</div>
      </div>
      {icon_mountain(28, 20)}
    </div>
  </div>

</div>

<!-- WEEKLY MILEAGE -->
<div class="wm-row">
  <div class="wm-left">
    <div class="wm-lbl">Weekly Mileage</div>
    <div class="wm-nums">
      <span class="wm-num">{week_mi}</span>
      <span class="wm-goal">/ {goal_int} mi</span>
    </div>
    <div class="wm-pct">{wm_pct}% of goal</div>
  </div>
  <div class="wm-right">
    <div class="wm-bar">
      <div class="wm-fill" style="width:{wm_pct}%"></div>
      <div class="wm-remain"></div>
    </div>
    <div class="wm-scale">{wm_ticks_html}</div>
  </div>
</div>

<!-- INFO ROW -->
<div class="info-row">

  <div class="col-wx">
    <div class="s-lbl" style="margin-bottom:5px">Weather</div>
    <div class="wx-top">{wx_svg}<span class="wx-temp">{wx_temp}</span></div>
    <div class="wx-cond">{wx_cond}</div>
    <div class="wx-detail">{wx_rain}</div>
    <div class="wx-wind-row">{icon_wind(18, 12)} {wx_wind}</div>
  </div>

  <div class="dv"></div>

  <div class="col-up-wrap">
    <div class="up-head">Upcoming Workouts</div>
    <div class="col-up">{up_cards}</div>
  </div>

</div>

<!-- YTD BANNER -->
<div class="ytd">
  <div class="yt"><div class="yt-lbl">Distance YTD</div><div class="yt-val">{ytd_mi} mi</div><div class="yt-sub">{ytd_cnt} runs</div></div>
  <div class="yt"><div class="yt-lbl">Time YTD</div><div class="yt-val">{ytd_hr} hr</div><div class="yt-sub">moving time</div></div>
  <div class="yt"><div class="yt-lbl">Avg Pace</div><div class="yt-val">{ytd_pace}</div><div class="yt-sub">min / mile</div></div>
  <div class="yt"><div class="yt-lbl">Elev Gain YTD</div><div class="yt-val">{ytd_ft} ft</div><div class="yt-sub">year to date</div></div>
  <div class="yt"><div class="yt-lbl">VO2max Est.</div><div class="yt-val">{vo2}</div><div class="yt-sub">mL/kg/min</div></div>
</div>

</div>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
