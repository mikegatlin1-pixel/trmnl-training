from flask import Flask, Response
import requests, os, json, math, re

app = Flask(__name__)

CLIENT_ID     = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("STRAVA_REFRESH_TOKEN")
WEATHER_LAT   = os.environ.get("WEATHER_LAT", "34.85")
WEATHER_LON   = os.environ.get("WEATHER_LON", "-82.39")

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
        acts    = requests.get("https://www.strava.com/api/v3/athlete/activities?per_page=15", headers=h).json()
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
            "temp": round(c.get("temperature_2m", 0)),
            "code": c.get("weather_code", 0),
            "wind": round(c.get("wind_speed_10m", 0)),
            "wind_dir": c.get("wind_direction_10m", 0),
            "precip": c.get("precipitation_probability", 0),
        }
    except:
        return None

def weather_desc(code):
    if code == 0:       return "Clear"
    if code <= 3:       return "Partly Cloudy"
    if code <= 48:      return "Foggy"
    if code <= 55:      return "Drizzle"
    if code <= 65:      return "Rain"
    if code <= 75:      return "Snow"
    if code <= 82:      return "Showers"
    return "Storms"

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
    pct     = round(elapsed / total * 100, 1)
    wk      = min(4, math.ceil(elapsed / 7)) if elapsed > 0 else 1
    return pct, wk

def get_week_days():
    from datetime import date, timedelta
    today  = date.today()
    monday = today - timedelta(days=today.weekday())
    return [(monday + timedelta(days=i)).isoformat() for i in range(7)]

def day_symbol(dtype):
    if dtype == "run":      return "&#9675;"
    if dtype == "social":   return "&#9651;"
    if dtype == "strength": return "&#9632;"
    return "&mdash;"

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

# ── Polyline / map ───────────────────────────────────────────────────────────

def decode_polyline(encoded):
    points = []
    index, lat, lng = 0, 0, 0
    n = len(encoded)
    while index < n:
        for is_lng in (False, True):
            result, shift = 0, 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if is_lng: lng += delta
            else:      lat += delta
        points.append((lat / 1e5, lng / 1e5))
    return points

def polyline_to_svg_path(encoded, width, height, padding=10):
    if not encoded:
        return f'<text x="{width//2}" y="{height//2}" text-anchor="middle" font-size="10" fill="#bbb">No GPS data</text>'
    try:
        pts = decode_polyline(encoded)
        if len(pts) < 2:
            return ''
        lats = [p[0] for p in pts]
        lngs = [p[1] for p in pts]
        lat_span = max(lats) - min(lats) or 0.001
        lng_span = max(lngs) - min(lngs) or 0.001
        uw = width - 2 * padding
        uh = height - 2 * padding
        scale = min(uw / lng_span, uh / lat_span)
        pw = lng_span * scale
        ph = lat_span * scale
        ox = padding + (uw - pw) / 2
        oy = padding + (uh - ph) / 2
        coords = []
        for la, lo in pts:
            x = ox + (lo - min(lngs)) * scale
            y = oy + (max(lats) - la) * scale
            coords.append(f"{x:.1f},{y:.1f}")
        return (
            f'<polyline points="{" ".join(coords)}" fill="none" stroke="#111" '
            f'stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>'
        )
    except:
        return ''

def elevation_chart_svg(altitude, distance, width, height):
    """Elevation chart with y-axis labels (ft). altitude in meters."""
    if not altitude or len(altitude) < 3:
        return ''
    alt_ft = [a * 3.28084 for a in altitude]
    n = len(alt_ft)
    if n > 100:
        step = max(1, n // 100)
        alt_ft   = alt_ft[::step]
        distance = (distance or [])[::step] if distance else list(range(0, n, step))
    if not distance:
        distance = list(range(len(alt_ft)))

    min_a, max_a = min(alt_ft), max(alt_ft)
    rng = max_a - min_a or 1

    # Nice axis ticks
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

    y_ax = 36  # left margin for labels
    px, py = 2, 3
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
        if tick < ticks[0] - 0.01 or tick > ticks[-1] + 0.01:
            continue
        yp = py + ch - (tick - ticks[0]) / span * ch
        lbl = f"{int(tick):,} ft"
        parts.append(
            f'<line x1="{y_ax}" y1="{yp:.1f}" x2="{y_ax+cw}" y2="{yp:.1f}" '
            f'stroke="#ccc" stroke-width="0.7" stroke-dasharray="3,2"/>'
        )
        parts.append(
            f'<text x="{y_ax-3}" y="{yp+3:.1f}" font-size="8" fill="#888" '
            f'text-anchor="end" font-family="IBM Plex Mono,monospace">{lbl}</text>'
        )
    parts.append('</svg>')
    return ''.join(parts)

# ── Routes ───────────────────────────────────────────────────────────────────

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
    phase_pct, phase_wk = get_phase_info()
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

    t_dur_num = parse_dur(t_dur)
    t_dur_display = f"{t_dur_num}" if t_dur_num else "—"

    # Zone / effort context
    zone_map = {"run": "AEROBIC BASE · Zone 2", "social": "OPEN EFFORT", "strength": "GARAGE RACK", "rest": "FULL REST"}
    t_zone = zone_map.get(t_type, "")

    hr_note = "&#9829; HR CAP 138 bpm &middot; Walk at 139" if t_hr else ""

    # Week strip
    day_names = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
    week_cells = ""
    for i, iso in enumerate(week_days):
        plan     = next((d for d in PLAN if d["iso"] == iso), None)
        is_today = iso == today_iso
        is_past  = iso < today_iso
        dtype    = plan["type"] if plan else "rest"
        if is_today:
            bcls, content = "wd-today", day_symbol(dtype)
        elif is_past and plan and dtype != "rest":
            bcls, content = "wd-done", "&#10003;"
        elif dtype == "rest":
            bcls, content = "wd-rest", "&mdash;"
        else:
            bcls, content = "", day_symbol(dtype)
        week_cells += f'<div class="wd"><div class="wd-n">{day_names[i]}</div><div class="wd-b {bcls}">{content}</div></div>'

    # Upcoming (next 3 after today)
    upcoming = get_upcoming(today_iso, 3)

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
            vo2_pct    = round(min(100, vo2 / 50 * 100), 1)
        else:
            ytd_pace = "—"; vo2 = 0; vo2_pct = 0
        last_act = acts[0] if isinstance(acts[0], dict) else None
    else:
        ytd_mi, ytd_cnt, ytd_hr, ytd_ft, ytd_pace = "—", "—", "—", "—", "—"
        vo2, vo2_pct = 0, 0
        last_act = None

    # Last activity
    MAP_W, MAP_H = 272, 120
    if last_act:
        la_name    = last_act.get("name", "")[:26]
        la_type    = last_act.get("type", "")
        la_raw_d   = last_act.get("distance", 0)
        la_movt    = last_act.get("moving_time", 0)
        la_raw_e   = last_act.get("total_elevation_gain", 0)
        la_dist    = f"{m_to_mi(la_raw_d)} mi" if la_raw_d > 100 else "—"
        la_elev    = f"{m_to_ft(la_raw_e)} ft"  if la_raw_e > 1  else "—"
        if la_raw_d > 100 and la_movt > 0:
            la_pace = s_to_pace(la_movt / la_raw_d * 1609.34)
            la_time = s_to_hm(la_movt)
        else:
            la_pace = "—"; la_time = s_to_hm(la_movt)
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(last_act["start_date_local"].replace("Z", ""))
            la_date = dt.strftime("%a %b %-d")
        except:
            la_date = ""
        icon_map = {"Run":"&#9675;","Walk":"&#9675;","WeightTraining":"&#9632;","Workout":"&#9632;","Ride":"&#9651;"}
        la_icon = icon_map.get(la_type, "&#9651;")
        polyline  = last_act.get("map", {}).get("summary_polyline", "") or ""
        map_inner = polyline_to_svg_path(polyline, MAP_W, MAP_H) if polyline else (
            f'<text x="{MAP_W//2}" y="{MAP_H//2}" text-anchor="middle" font-size="10" fill="#bbb">No GPS data</text>'
        )
        elev_svg = ""
        if polyline and token:
            alt_d, dist_d = get_activity_streams(last_act["id"], token)
            if alt_d:
                elev_svg = elevation_chart_svg(alt_d, dist_d, MAP_W, 68)
    else:
        la_name, la_type, la_date, la_icon = "No recent activity", "", "", "&#9675;"
        la_dist, la_pace, la_time, la_elev = "—", "—", "—", "—"
        map_inner = f'<text x="{MAP_W//2}" y="{MAP_H//2}" text-anchor="middle" font-size="10" fill="#bbb">No data</text>'
        elev_svg = ""

    # Weather
    wx = get_weather()
    if wx:
        wx_temp  = f"{wx['temp']}&#176;F"
        wx_cond  = weather_desc(wx["code"]).upper()
        wx_wind  = f"{wx['wind']} mph {wind_dir_label(wx['wind_dir'])}"
        wx_rain  = f"{wx['precip']}% precip"
    else:
        wx_temp, wx_cond, wx_wind, wx_rain = "—&#176;F", "—", "—", "—"

    # Upcoming HTML (3 cards)
    up_cards = ""
    type_tag = {"run": "ZONE 2", "social": "OPEN", "strength": "GYM", "rest": "REST"}
    for u in upcoming:
        tag_lbl = type_tag.get(u["type"], "")
        dur_n   = parse_dur(u["dur"])
        dur_s   = f"{dur_n} min" if dur_n else u["dur"]
        icon    = {"run":"&#9675;","social":"&#9651;","strength":"&#9632;"}.get(u["type"], "&mdash;")
        up_cards += f"""
        <div class="up-card">
          <div class="up-day">{u['label']}</div>
          <div class="up-name">{icon} {u['title']}</div>
          <div class="up-dur">{dur_s}</div>
          <div class="up-tag">{tag_lbl}</div>
        </div>"""

    # Phase bar
    phase_bar_w = round(phase_pct)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@400;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:100%; height:480px; overflow:hidden; background:#fff; color:#000; font-family:'IBM Plex Mono',monospace; font-size:12px; }}
  .screen {{ width:100%; height:480px; display:grid; grid-template-rows:42px 1fr 112px 44px; border:2px solid #000; overflow:hidden; }}
  .dv {{ background:#000; width:1px; }}
  .dh {{ background:#000; height:1px; }}

  /* ── Header ── */
  .header {{ background:#000; color:#fff; display:grid; grid-template-columns:1fr auto auto; align-items:center; padding:0 16px; gap:16px; }}
  .h-title {{ font-size:17px; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; font-family:'IBM Plex Sans',sans-serif; }}
  .h-date {{ font-size:11px; letter-spacing:0.06em; opacity:0.85; }}
  .h-week {{ font-size:10px; letter-spacing:0.12em; border:1.5px solid #fff; padding:2px 9px; text-transform:uppercase; white-space:nowrap; }}

  /* ── Main row ── */
  .main {{ display:grid; grid-template-columns:300px 1px 222px 1px 1fr; overflow:hidden; }}

  /* Last Run */
  .col-run {{ padding:10px 12px 8px 12px; display:flex; flex-direction:column; overflow:hidden; }}
  .s-label {{ font-size:9px; letter-spacing:0.2em; text-transform:uppercase; color:#888; margin-bottom:5px; }}
  .act-name-row {{ display:flex; align-items:baseline; gap:7px; margin-bottom:7px; }}
  .act-icon {{ font-size:16px; flex-shrink:0; }}
  .act-name {{ font-size:15px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; line-height:1.1; letter-spacing:-0.01em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .run-stats {{ display:grid; grid-template-columns:repeat(4,1fr); border:1px solid #ddd; margin-bottom:7px; flex-shrink:0; }}
  .rs {{ padding:4px 6px; border-right:1px solid #ddd; }}
  .rs:last-child {{ border-right:none; }}
  .rs-lbl {{ font-size:8px; letter-spacing:0.12em; text-transform:uppercase; color:#999; margin-bottom:2px; }}
  .rs-val {{ font-size:13px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; line-height:1; }}
  .rs-unit {{ font-size:9px; color:#888; }}
  .map-box {{ border:1px solid #ddd; background:#f7f7f7; flex-shrink:0; overflow:hidden; margin-bottom:6px; }}
  .elev-box {{ flex:1; overflow:hidden; }}

  /* Today */
  .col-today {{ padding:10px 13px; display:flex; flex-direction:column; overflow:hidden; }}
  .today-name {{ font-size:18px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; line-height:1.1; letter-spacing:-0.02em; margin-bottom:7px; }}
  .today-dur-row {{ display:flex; align-items:baseline; gap:4px; margin-bottom:4px; }}
  .dur-num {{ font-size:46px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; line-height:1; letter-spacing:-0.04em; }}
  .dur-unit {{ font-size:14px; color:#555; font-family:'IBM Plex Sans',sans-serif; }}
  .today-zone {{ font-size:9px; letter-spacing:0.18em; text-transform:uppercase; color:#777; margin-bottom:10px; }}
  .today-detail {{ font-size:11px; color:#444; line-height:1.6; flex:1; }}
  .today-hr {{ font-size:11px; font-weight:700; margin-top:8px; }}
  .today-tag {{ display:inline-block; font-size:9px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; background:#000; color:#fff; padding:2px 7px; margin-top:8px; }}

  /* Right — phase + VO2 + week */
  .col-right {{ padding:10px 12px; display:flex; flex-direction:column; overflow:hidden; }}
  .prog-label {{ font-size:9px; letter-spacing:0.18em; text-transform:uppercase; color:#777; margin-bottom:4px; display:flex; align-items:center; gap:6px; }}
  .prog-label::after {{ content:''; flex:1; height:1px; background:#ddd; }}
  .prog-bar-track {{ height:8px; background:#eee; border:1px solid #ccc; margin-bottom:3px; overflow:hidden; }}
  .prog-bar-fill {{ height:100%; background:#000; }}
  .prog-meta {{ display:flex; justify-content:space-between; font-size:9px; color:#999; margin-bottom:10px; }}
  .vo2-num {{ font-size:28px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; letter-spacing:-0.03em; line-height:1; }}
  .vo2-unit {{ font-size:9px; color:#777; }}
  .vo2-bar-track {{ height:6px; background:#eee; border:1px solid #ccc; margin:4px 0 3px; overflow:hidden; position:relative; }}
  .vo2-bar-fill {{ height:100%; background:#000; }}
  .vo2-bar-target {{ position:absolute; right:0; top:-1px; bottom:-1px; width:2px; background:#555; }}
  .vo2-sub {{ font-size:9px; color:#888; margin-bottom:10px; }}
  .week-row {{ display:grid; grid-template-columns:repeat(7,1fr); gap:2px; margin-top:2px; }}
  .wd {{ display:flex; flex-direction:column; align-items:center; gap:2px; }}
  .wd-n {{ font-size:8px; font-weight:700; color:#888; letter-spacing:0.04em; }}
  .wd-b {{ width:24px; height:24px; border:1.5px solid #ccc; display:flex; align-items:center; justify-content:center; font-size:12px; background:#fff; }}
  .wd-today {{ border-color:#000; border-width:2.5px; }}
  .wd-done {{ border-color:#000; background:#000; color:#fff; font-size:11px; }}
  .wd-rest {{ border-color:#eee; background:#f8f8f8; color:#ccc; font-size:10px; }}

  /* ── Info row ── */
  .info-row {{ display:grid; grid-template-columns:196px 1px 1fr; border-top:1px solid #000; overflow:hidden; }}

  /* Weather */
  .col-weather {{ padding:10px 14px; display:flex; flex-direction:column; justify-content:center; }}
  .wx-temp {{ font-size:36px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; letter-spacing:-0.03em; line-height:1; }}
  .wx-cond {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; margin-top:3px; }}
  .wx-detail {{ font-size:10px; color:#666; margin-top:3px; line-height:1.5; }}

  /* Upcoming */
  .col-upcoming {{ padding:10px 0; display:flex; flex-direction:column; overflow:hidden; }}
  .up-head {{ font-size:9px; letter-spacing:0.2em; text-transform:uppercase; color:#888; padding:0 14px; margin-bottom:7px; }}
  .up-grid {{ display:grid; grid-template-columns:repeat(3,1fr); flex:1; }}
  .up-card {{ padding:4px 12px; border-right:1px solid #e0e0e0; display:flex; flex-direction:column; }}
  .up-card:last-child {{ border-right:none; }}
  .up-day {{ font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:#888; margin-bottom:3px; }}
  .up-name {{ font-size:12px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; line-height:1.2; margin-bottom:3px; }}
  .up-dur {{ font-size:10px; color:#666; margin-bottom:3px; }}
  .up-tag {{ display:inline-block; font-size:8px; font-weight:700; letter-spacing:0.1em; background:#000; color:#fff; padding:1px 5px; text-transform:uppercase; }}

  /* ── YTD Banner ── */
  .ytd-banner {{ display:grid; grid-template-columns:repeat(5,1fr); background:#000; color:#fff; border-top:none; }}
  .ytd-stat {{ display:flex; flex-direction:column; justify-content:center; align-items:center; padding:0 6px; border-right:1px solid #333; }}
  .ytd-stat:last-child {{ border-right:none; }}
  .ytd-label {{ font-size:8px; letter-spacing:0.15em; color:#888; text-transform:uppercase; margin-bottom:2px; }}
  .ytd-val {{ font-size:15px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; line-height:1; }}
  .ytd-sub {{ font-size:9px; color:#666; margin-top:1px; }}
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

  <!-- Main content -->
  <div class="main">

    <!-- LAST RUN -->
    <div class="col-run">
      <div class="s-label">Last Run</div>
      <div class="act-name-row">
        <span class="act-icon">{la_icon}</span>
        <span class="act-name">{la_name}</span>
      </div>
      <div class="run-stats">
        <div class="rs"><div class="rs-lbl">Distance</div><div class="rs-val">{la_dist}</div></div>
        <div class="rs"><div class="rs-lbl">Avg Pace</div><div class="rs-val">{la_pace}<span class="rs-unit"> /mi</span></div></div>
        <div class="rs"><div class="rs-lbl">Moving Time</div><div class="rs-val">{la_time}</div></div>
        <div class="rs"><div class="rs-lbl">Elev Gain</div><div class="rs-val">{la_elev}</div></div>
      </div>
      <div class="map-box">
        <svg style="width:100%;height:{MAP_H}px;display:block;"
             viewBox="0 0 {MAP_W} {MAP_H}" xmlns="http://www.w3.org/2000/svg"
             preserveAspectRatio="xMidYMid meet">
          <rect width="{MAP_W}" height="{MAP_H}" fill="#f7f7f7"/>
          {map_inner}
        </svg>
      </div>
      <div class="elev-box">{elev_svg}</div>
    </div>

    <div class="dv"></div>

    <!-- TODAY -->
    <div class="col-today">
      <div class="s-label">Today</div>
      <div class="today-name">{t_title}</div>
      <div class="today-dur-row">
        <span class="dur-num">{t_dur_display}</span>
        <span class="dur-unit">min</span>
      </div>
      <div class="today-zone">{t_zone}</div>
      <div class="today-detail">{t_detail}</div>
      {f'<div class="today-hr">&#9829; {hr_note}</div>' if hr_note else ''}
      <div class="today-tag">{t_tag}</div>
    </div>

    <div class="dv"></div>

    <!-- Phase + VO2 + Week -->
    <div class="col-right">
      <div class="prog-label">Phase 0 Progress</div>
      <div class="prog-bar-track"><div class="prog-bar-fill" style="width:{phase_bar_w}%"></div></div>
      <div class="prog-meta"><span>Apr 27</span><span>Wk {phase_wk} of 4 &middot; {phase_pct}%</span><span>May 24</span></div>

      <div class="prog-label">VO2max Est.</div>
      <span class="vo2-num">{vo2}</span> <span class="vo2-unit">mL/kg/min</span>
      <div class="vo2-bar-track">
        <div class="vo2-bar-fill" style="width:{vo2_pct}%"></div>
        <div class="vo2-bar-target"></div>
      </div>
      <div class="vo2-sub">{vo2} now &middot; 50.0 target</div>

      <div class="prog-label">This Week</div>
      <div class="week-row">{week_cells}</div>
    </div>

  </div>

  <!-- Info row -->
  <div class="info-row">

    <!-- Weather -->
    <div class="col-weather">
      <div class="wx-temp">{wx_temp}</div>
      <div class="wx-cond">{wx_cond}</div>
      <div class="wx-detail">{wx_wind}<br>{wx_rain}</div>
    </div>

    <div class="dv"></div>

    <!-- Upcoming workouts -->
    <div class="col-upcoming">
      <div class="up-head">Upcoming Workouts</div>
      <div class="up-grid">
        {up_cards}
      </div>
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
