from flask import Flask, Response
import requests, os, json, math

app = Flask(__name__)

CLIENT_ID     = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("STRAVA_REFRESH_TOKEN")

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

def get_access_token():
    r = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    })
    return r.json().get("access_token")

def get_strava_data():
    try:
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        athlete = requests.get("https://www.strava.com/api/v3/athlete", headers=headers).json()
        stats   = requests.get(f"https://www.strava.com/api/v3/athletes/{athlete['id']}/stats", headers=headers).json()
        acts    = requests.get("https://www.strava.com/api/v3/athlete/activities?per_page=15", headers=headers).json()
        return athlete, stats, acts, token
    except:
        return None, None, None, None

def meters_to_miles(m): return round(m / 1609.34, 1)
def meters_to_feet(m):  return f"{round(m * 3.28084):,}"
def sec_to_hours(s):    return round(s / 3600)
def sec_to_minsec(s):
    m = int(s // 60); sec = int(s % 60)
    return f"{m}:{sec:02d}"
def sec_to_hm(s):
    h = int(s // 3600); m = int((s % 3600) // 60)
    return f"{h}h {m}m" if h else f"{m} min"

def get_today_iso():
    from datetime import date
    return date.today().isoformat()

def get_today_label():
    from datetime import date
    d = date.today()
    days   = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    return f"{days[d.weekday()].upper()} &middot; {months[d.month-1].upper()} {d.day}"

def get_phase_info():
    from datetime import date
    start = date(2026, 4, 27)
    end   = date(2026, 5, 24)
    today = date.today()
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

def get_next_strength(today_iso):
    future = [d for d in PLAN if d["iso"] >= today_iso and d["type"] == "strength"]
    if future:
        from datetime import date
        d    = date.fromisoformat(future[0]["iso"])
        days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        return f"{days[d.weekday()]} &middot; {future[0]['title']}", future[0]["detail"].split("·")[0].strip()
    return "—", "—"

def day_symbol(dtype):
    if dtype == "run":      return "&#9675;"
    if dtype == "social":   return "&#9651;"
    if dtype == "strength": return "&#9632;"
    return "&mdash;"

# ── Polyline / map helpers ──────────────────────────────────────────────────

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
            if is_lng:
                lng += delta
            else:
                lat += delta
        points.append((lat / 1e5, lng / 1e5))
    return points

def polyline_to_svg_path(encoded, width, height, padding=12):
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
        for lat, lng in pts:
            x = ox + (lng - min(lngs)) * scale
            y = oy + (max(lats) - lat) * scale
            coords.append(f"{x:.1f},{y:.1f}")
        return (
            f'<polyline points="{" ".join(coords)}" '
            f'fill="none" stroke="#111" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )
    except:
        return ''

def get_activity_streams(act_id, token):
    try:
        r = requests.get(
            f"https://www.strava.com/api/v3/activities/{act_id}/streams",
            headers={"Authorization": f"Bearer {token}"},
            params={"keys": "altitude,distance", "key_by_type": "true"},
            timeout=4
        )
        data = r.json()
        return data.get("altitude", {}).get("data", []), data.get("distance", {}).get("data", [])
    except:
        return [], []

def elevation_chart_svg(altitude, distance, width, height):
    if not altitude or len(altitude) < 3:
        return ''
    n = len(altitude)
    if n > 100:
        step = max(1, n // 100)
        altitude = altitude[::step]
        distance = distance[::step] if distance else list(range(0, n, step))
    if not distance:
        distance = list(range(len(altitude)))
    min_alt, max_alt = min(altitude), max(altitude)
    alt_span = max_alt - min_alt or 1
    min_d, max_d = distance[0], distance[-1]
    dist_span = max_d - min_d or 1
    px, py = 2, 3
    w, h = width - 2 * px, height - 2 * py
    pts = []
    for i, alt in enumerate(altitude):
        x = px + (distance[i] - min_d) / dist_span * w
        y = py + h - (alt - min_alt) / alt_span * h
        pts.append((x, y))
    path = (
        f"M {pts[0][0]:.1f},{py+h} "
        + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts)
        + f" L {pts[-1][0]:.1f},{py+h} Z"
    )
    return (
        f'<svg style="width:100%;height:{height}px;display:block;" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
        f'<path d="{path}" fill="#ddd" stroke="#444" stroke-width="1.2" stroke-linejoin="round"/>'
        f'</svg>'
    )

# ── Routes ──────────────────────────────────────────────────────────────────

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
    next_str, next_str_sub = get_next_strength(today_iso)

    today_plan = next((d for d in PLAN if d["iso"] == today_iso), None)
    if today_plan:
        today_title  = today_plan["title"]
        today_detail = today_plan["detail"]
        today_tag    = today_plan["tag"]
        today_dur    = today_plan["dur"]
        today_hr     = today_plan["hr"]
        today_type   = today_plan["type"]
    else:
        today_title  = "No workout scheduled"
        today_detail = "Rest or check your plan."
        today_tag    = "REST"
        today_dur    = "&mdash;"
        today_hr     = False
        today_type   = "rest"

    day_names = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
    week_strip_html = ""
    for i, iso in enumerate(week_days):
        plan     = next((d for d in PLAN if d["iso"] == iso), None)
        is_today = iso == today_iso
        is_past  = iso < today_iso
        dtype    = plan["type"] if plan else "rest"
        dur      = plan["dur"]  if plan else "&mdash;"
        if is_today:
            box_class, content = "wd-today", day_symbol(dtype)
        elif is_past and plan and dtype != "rest":
            box_class, content = "wd-done", "&#10003;"
        elif dtype == "rest":
            box_class, content = "wd-rest", "&mdash;"
        else:
            box_class, content = "", day_symbol(dtype)
        week_strip_html += f"""
        <div class="week-day">
          <div class="wd-name">{day_names[i]}</div>
          <div class="wd-box {box_class}">{content}</div>
          <div class="wd-dur">{dur}</div>
        </div>"""

    athlete, stats, acts, token = get_strava_data()

    # YTD stats
    if stats and isinstance(acts, list) and acts:
        ytd       = stats.get("ytd_run_totals", {})
        dist_mi   = meters_to_miles(ytd.get("distance", 0))
        act_count = ytd.get("count", 0)
        hours     = sec_to_hours(ytd.get("moving_time", 0))
        elev_ft   = meters_to_feet(ytd.get("elevation_gain", 0))

        runs = [a for a in acts if isinstance(a, dict) and a.get("type") == "Run" and a.get("distance", 0) > 100]
        if runs:
            avg_pace_s = sum(r["moving_time"] / r["distance"] * 1609.34 for r in runs) / len(runs)
            pace_str   = sec_to_minsec(avg_pace_s)
            recent5    = runs[:5]
            avg_mps    = sum(r["distance"] / r["moving_time"] for r in recent5) / len(recent5)
            vo2        = round(min(65, max(30, avg_mps * 60 * 0.2 + 3.5)), 1)
            vo2_pct    = round(min(100, vo2 / 50 * 100), 1)
            vo2_diff   = round(50 - vo2, 1)
            vo2_goal   = f"50.0 target &middot; {vo2_diff} to go" if vo2_diff > 0 else "50.0 &#10003; reached!"
        else:
            pace_str = "&mdash;"
            vo2, vo2_pct, vo2_goal = 0, 0, "50.0 target"

        last_act = acts[0] if isinstance(acts[0], dict) else None
    else:
        dist_mi, act_count, hours, elev_ft = "—", "—", "—", "—"
        pace_str, vo2, vo2_pct, vo2_goal   = "—", 0, 0, "50.0 target"
        last_act = None

    # Last activity
    MAP_W, MAP_H = 276, 128
    if last_act:
        la_name  = last_act.get("name", "")[:24]
        la_type  = last_act.get("type", "")
        la_raw_d = last_act.get("distance", 0)
        la_movt  = last_act.get("moving_time", 0)
        la_elev_raw = last_act.get("total_elevation_gain", 0)

        la_dist_str = f"{meters_to_miles(la_raw_d)} mi" if la_raw_d > 100 else "—"
        la_elev_str = f"{meters_to_feet(la_elev_raw)} ft" if la_elev_raw > 1 else "—"

        if la_raw_d > 100 and la_movt > 0:
            la_pace_str   = sec_to_minsec(la_movt / la_raw_d * 1609.34)
            la_pace_label = "Pace /mi"
        else:
            la_pace_str   = sec_to_hm(la_movt)
            la_pace_label = "Duration"

        from datetime import datetime
        try:
            dt = datetime.fromisoformat(last_act["start_date_local"].replace("Z", ""))
            la_date = dt.strftime("%a %b %-d")
        except:
            la_date = ""

        icon_map = {"Run":"&#9675;","Walk":"&#9675;","WeightTraining":"&#9632;","Workout":"&#9632;","Ride":"&#9651;"}
        la_icon = icon_map.get(la_type, "&#9651;")

        polyline = last_act.get("map", {}).get("summary_polyline", "") or ""
        map_svg_inner = polyline_to_svg_path(polyline, MAP_W, MAP_H) if polyline else (
            f'<text x="{MAP_W//2}" y="{MAP_H//2}" text-anchor="middle" font-size="10" fill="#bbb">No GPS data</text>'
        )

        elev_chart_html = ""
        if polyline and token:
            alt_data, dist_data = get_activity_streams(last_act["id"], token)
            if alt_data:
                chart = elevation_chart_svg(alt_data, dist_data, MAP_W, 44)
                if chart:
                    elev_chart_html = f'<div class="elev-label">Elevation Profile</div>{chart}'
    else:
        la_name, la_type, la_date, la_icon = "No data", "", "", "&#9675;"
        la_dist_str, la_pace_str, la_elev_str = "—", "—", "—"
        la_pace_label = "Pace /mi"
        map_svg_inner = f'<text x="{MAP_W//2}" y="{MAP_H//2}" text-anchor="middle" font-size="10" fill="#bbb">No data</text>'
        elev_chart_html = ""

    hr_block     = '<div class="hr-alert">&#9829; CAP: 138 bpm &middot; Walk at 139</div>' if today_hr else ""
    strength_tag = '<span class="tag tag-outline">GARAGE RACK</span>' if today_type == "strength" else ""
    aerobic_tag  = '<span class="tag tag-outline">AEROBIC BASE</span>' if today_type == "run" else ""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:100%; height:480px; overflow:hidden; background:#fff; color:#000; font-family:'IBM Plex Mono',monospace; font-size:13px; }}
  .screen {{ width:100%; height:480px; display:grid; grid-template-rows:40px 1fr 52px; border:2px solid #000; }}

  .header {{ display:grid; grid-template-columns:auto 1fr auto auto; align-items:center; gap:14px; padding:0 14px; border-bottom:2px solid #000; background:#000; color:#fff; }}
  .strava-mark {{ font-size:12px; font-weight:700; letter-spacing:0.15em; display:flex; align-items:center; gap:5px; }}
  .header-title {{ font-size:12px; font-weight:600; letter-spacing:0.04em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .header-phase {{ font-size:10px; letter-spacing:0.1em; border:1px solid #fff; padding:1px 7px; text-transform:uppercase; white-space:nowrap; }}
  .header-date {{ font-size:11px; letter-spacing:0.08em; opacity:0.7; white-space:nowrap; }}

  .body {{ display:grid; grid-template-columns:232px 1px 298px 1px 1fr; overflow:hidden; }}
  .divider-v {{ background:#000; }}
  .divider-h {{ background:#000; height:1px; }}

  /* Left — Today + Week */
  .col-left {{ display:grid; grid-template-rows:1fr 1px 96px; overflow:hidden; }}
  .today-panel {{ padding:11px 13px; display:flex; flex-direction:column; justify-content:space-between; overflow:hidden; }}
  .today-eyebrow {{ font-size:11px; letter-spacing:0.2em; text-transform:uppercase; color:#666; margin-bottom:3px; }}
  .today-title {{ font-size:23px; font-weight:700; line-height:1.05; letter-spacing:-0.02em; font-family:'IBM Plex Sans',sans-serif; margin-bottom:5px; }}
  .today-detail {{ font-size:12px; color:#333; line-height:1.5; }}
  .today-tags {{ display:flex; gap:5px; margin-top:7px; flex-wrap:wrap; }}
  .tag {{ font-size:10px; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; border:1.5px solid #000; padding:2px 6px; }}
  .tag-filled {{ background:#000; color:#fff; }}
  .tag-outline {{ background:#fff; color:#000; }}
  .hr-alert {{ display:flex; align-items:center; gap:5px; margin-top:7px; font-size:12px; font-weight:700; }}
  .week-strip {{ padding:7px 13px; display:flex; flex-direction:column; justify-content:center; gap:4px; }}
  .week-strip-label {{ font-size:10px; letter-spacing:0.14em; text-transform:uppercase; color:#888; }}
  .week-days {{ display:grid; grid-template-columns:repeat(7,1fr); gap:2px; }}
  .week-day {{ display:flex; flex-direction:column; align-items:center; gap:2px; }}
  .wd-name {{ font-size:9px; font-weight:700; letter-spacing:0.06em; color:#777; }}
  .wd-box {{ width:27px; height:27px; border:1.5px solid #bbb; display:flex; align-items:center; justify-content:center; font-size:14px; background:#fff; }}
  .wd-today {{ border-color:#000; border-width:2.5px; }}
  .wd-done {{ border-color:#000; background:#000; color:#fff; font-size:13px; }}
  .wd-rest {{ border-color:#ddd; background:#f5f5f5; font-size:11px; color:#999; }}
  .wd-dur {{ font-size:9px; color:#999; text-align:center; }}

  /* Middle — Last Activity */
  .col-mid {{ padding:10px 12px; display:flex; flex-direction:column; overflow:hidden; }}
  .col-label {{ font-size:10px; letter-spacing:0.18em; text-transform:uppercase; color:#777; margin-bottom:5px; display:flex; align-items:center; gap:6px; }}
  .col-label::after {{ content:''; flex:1; height:1px; background:#ddd; }}
  .la-header {{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:5px; overflow:hidden; }}
  .la-name {{ font-size:13px; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .la-meta {{ font-size:10px; color:#888; flex-shrink:0; margin-left:8px; }}
  .activity-map {{ border:1px solid #ddd; background:#f6f6f6; overflow:hidden; margin-bottom:5px; flex-shrink:0; }}
  .la-stats {{ display:grid; grid-template-columns:repeat(3,1fr); border:1px solid #e4e4e4; flex-shrink:0; margin-bottom:5px; }}
  .la-stat {{ padding:5px 4px; text-align:center; border-right:1px solid #e4e4e4; }}
  .la-stat:last-child {{ border-right:none; }}
  .la-stat-label {{ font-size:9px; text-transform:uppercase; letter-spacing:0.1em; color:#999; margin-bottom:2px; }}
  .la-stat-val {{ font-size:15px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; line-height:1.1; }}
  .elev-label {{ font-size:9px; letter-spacing:0.15em; text-transform:uppercase; color:#999; margin-bottom:3px; }}

  /* Right — YTD + VO2max */
  .col-right {{ padding:10px 11px 10px 13px; display:flex; flex-direction:column; overflow:hidden; }}
  .strava-stat {{ display:flex; flex-direction:column; padding:5px 0; border-bottom:1px solid #ebebeb; flex:1; justify-content:center; }}
  .strava-stat:last-child {{ border-bottom:none; }}
  .ss-label {{ font-size:10px; letter-spacing:0.1em; text-transform:uppercase; color:#999; margin-bottom:1px; }}
  .ss-value {{ font-size:20px; font-weight:700; letter-spacing:-0.02em; font-family:'IBM Plex Sans',sans-serif; line-height:1; }}
  .ss-sub {{ font-size:10px; color:#777; margin-top:1px; }}
  .vo2-section {{ margin-top:7px; flex-shrink:0; }}
  .vo2-num {{ font-size:30px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; letter-spacing:-0.03em; line-height:1; }}
  .vo2-unit {{ font-size:10px; color:#777; margin-left:3px; }}
  .bar-track {{ height:6px; background:#eee; border:1px solid #ccc; margin-top:5px; position:relative; overflow:hidden; }}
  .bar-fill {{ height:100%; background:#000; }}
  .bar-target {{ position:absolute; right:0; top:-1px; bottom:-1px; width:2px; background:#555; }}
  .bar-labels {{ display:flex; justify-content:space-between; margin-top:3px; font-size:9px; color:#999; }}

  /* Footer — 3 cells */
  .footer {{ display:grid; grid-template-columns:repeat(3,1fr); border-top:2px solid #000; }}
  .footer-cell {{ display:flex; align-items:center; gap:7px; padding:0 12px; border-right:1px solid #ccc; overflow:hidden; }}
  .footer-cell:last-child {{ border-right:none; }}
  .fc-icon {{ font-size:15px; flex-shrink:0; }}
  .fc-label {{ font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#888; margin-bottom:1px; }}
  .fc-val {{ font-size:13px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; line-height:1.1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .fc-sub {{ font-size:10px; color:#777; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
</style>
</head>
<body>
<div class="screen">

  <div class="header">
    <div class="strava-mark">
      <svg width="13" height="13" viewBox="0 0 24 24">
        <path d="M10.5 4L6 14h3.5L10.5 4z" fill="#fff"/>
        <path d="M10.5 4L15 14h-3.5L10.5 4z" fill="#fff" opacity="0.45"/>
        <path d="M15 14l-1.75 3.5L11.5 14H15z" fill="#fff"/>
        <path d="M15 14l1.75 3.5L18.5 14H15z" fill="#fff" opacity="0.4"/>
      </svg>
      STRAVA
    </div>
    <div class="header-title">Aerobic Base &amp; Strength Foundation &mdash; Phase 0 &middot; 138 bpm cap</div>
    <div class="header-phase">WK {phase_wk} / 4</div>
    <div class="header-date">{today_label}</div>
  </div>

  <div class="body">

    <!-- Left: Today + Week -->
    <div class="col-left">
      <div class="today-panel">
        <div>
          <div class="today-eyebrow">Today's Workout</div>
          <div class="today-title">{today_title}</div>
          <div class="today-detail">{today_detail}</div>
          <div class="today-tags">
            <span class="tag tag-filled">{today_tag}</span>
            <span class="tag tag-outline">{today_dur}</span>
            {aerobic_tag}{strength_tag}
          </div>
          {hr_block}
        </div>
      </div>
      <div class="divider-h"></div>
      <div class="week-strip">
        <div class="week-strip-label">This Week</div>
        <div class="week-days">{week_strip_html}</div>
      </div>
    </div>

    <div class="divider-v"></div>

    <!-- Middle: Last Activity -->
    <div class="col-mid">
      <div class="col-label">Last Activity</div>
      <div class="la-header">
        <div class="la-name">{la_icon} {la_name}</div>
        <div class="la-meta">{la_date}</div>
      </div>
      <div class="activity-map">
        <svg style="width:100%;height:{MAP_H}px;display:block;"
             viewBox="0 0 {MAP_W} {MAP_H}"
             xmlns="http://www.w3.org/2000/svg"
             preserveAspectRatio="xMidYMid meet">
          <rect width="{MAP_W}" height="{MAP_H}" fill="#f6f6f6"/>
          {map_svg_inner}
        </svg>
      </div>
      <div class="la-stats">
        <div class="la-stat">
          <div class="la-stat-label">Distance</div>
          <div class="la-stat-val">{la_dist_str}</div>
        </div>
        <div class="la-stat">
          <div class="la-stat-label">{la_pace_label}</div>
          <div class="la-stat-val">{la_pace_str}</div>
        </div>
        <div class="la-stat">
          <div class="la-stat-label">Elevation</div>
          <div class="la-stat-val">{la_elev_str}</div>
        </div>
      </div>
      {elev_chart_html}
    </div>

    <div class="divider-v"></div>

    <!-- Right: YTD + VO2max -->
    <div class="col-right">
      <div class="col-label">Strava YTD</div>
      <div class="strava-stat">
        <div class="ss-label">Distance</div>
        <div class="ss-value">{dist_mi} mi</div>
        <div class="ss-sub">{act_count} runs year to date</div>
      </div>
      <div class="strava-stat">
        <div class="ss-label">Time</div>
        <div class="ss-value">{hours} hr</div>
        <div class="ss-sub">moving time</div>
      </div>
      <div class="strava-stat">
        <div class="ss-label">Avg Pace</div>
        <div class="ss-value">{pace_str}</div>
        <div class="ss-sub">min / mile</div>
      </div>
      <div class="strava-stat">
        <div class="ss-label">Elev Gain</div>
        <div class="ss-value">{elev_ft}</div>
        <div class="ss-sub">feet YTD</div>
      </div>
      <div class="vo2-section">
        <div class="col-label">VO2max Est.</div>
        <span class="vo2-num">{vo2}</span><span class="vo2-unit">mL/kg/min</span>
        <div class="bar-track">
          <div class="bar-fill" style="width:{vo2_pct}%"></div>
          <div class="bar-target"></div>
        </div>
        <div class="bar-labels"><span>{vo2} now</span><span>{vo2_goal}</span></div>
      </div>
    </div>

  </div>

  <div class="footer">
    <div class="footer-cell">
      <div class="fc-icon">&#9829;</div>
      <div>
        <div class="fc-label">HR Cap &middot; All Runs</div>
        <div class="fc-val">138 bpm</div>
        <div class="fc-sub">Walk at 139 &mdash; no ego</div>
      </div>
    </div>
    <div class="footer-cell">
      <div class="fc-icon">&#9632;</div>
      <div>
        <div class="fc-label">Next Strength</div>
        <div class="fc-val">{next_str}</div>
        <div class="fc-sub">{next_str_sub}</div>
      </div>
    </div>
    <div class="footer-cell">
      <div class="fc-icon">&#9651;</div>
      <div>
        <div class="fc-label">Long Run</div>
        <div class="fc-val">Sat &middot; 90 min</div>
        <div class="fc-sub">10 min ankle warm-up</div>
      </div>
    </div>
  </div>

</div>
</body>
</html>"""

    return html

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
