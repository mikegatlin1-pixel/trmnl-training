from flask import Flask, Response
import requests, os, json, math, re
from pathlib import Path

app = Flask(__name__)

CLIENT_ID      = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET  = os.environ.get("STRAVA_CLIENT_SECRET")
REFRESH_TOKEN  = os.environ.get("STRAVA_REFRESH_TOKEN")
WEATHER_LAT    = os.environ.get("WEATHER_LAT", "34.85")
WEATHER_LON    = os.environ.get("WEATHER_LON", "-82.39")
WEEKLY_GOAL_MI = float(os.environ.get("WEEKLY_GOAL_MI", "20"))
TRAINING_PLAN_MD = os.environ.get(
    "TRAINING_PLAN_MD",
    "~/Desktop/TRMNL Dashboards/Strava Training/Workouts/training-plan.md"
)
RUNNING_COACH_DIR = os.environ.get(
    "RUNNING_COACH_DIR",
    "~/Library/Mobile Documents/com~apple~CloudDocs/RunningCoach"
)

import functools, time as _time

# ── Google Sheets plan loader ─────────────────────────────────────────────────

_plan_cache = {"data": None, "ts": 0}
_PLAN_TTL   = 300  # re-fetch every 5 min

def load_plan_from_sheets():
    """Fetch plan rows from Google Sheet. Returns None if not configured."""
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    sheet_id   = os.environ.get("GOOGLE_SHEET_ID")
    if not creds_json or not sheet_id:
        return None
    try:
        import json, gspread
        from google.oauth2.service_account import Credentials
        scopes  = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        creds   = Credentials.from_service_account_info(json.loads(creds_json), scopes=scopes)
        client  = gspread.authorize(creds)
        rows    = client.open_by_key(sheet_id).sheet1.get_all_records()
        plan    = []
        for r in rows:
            if not r.get("Date"):
                continue
            plan.append({
                "iso":    str(r["Date"]).strip(),
                "type":   str(r["Type"]).strip().lower(),
                "title":  str(r["Title"]).strip(),
                "detail": str(r["Detail"]).strip(),
                "dur":    str(r["Duration"]).strip(),
                "hr":     str(r.get("HR","")).strip().lower() in ("true","yes","1"),
            })
        return plan or None
    except Exception as e:
        print(f"[sheets] error: {e}")
        return None

def load_plan_from_markdown():
    """Load rows from a local markdown file. Returns None when empty/missing."""
    path = Path(TRAINING_PLAN_MD).expanduser()
    if not path.exists():
        return None

    plan = []
    line_re = re.compile(
        r"^\s*-\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)(?:\|\s*([^|]+))?\s*$"
    )
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            match = line_re.match(line)
            if not match:
                continue
            plan.append({
                "iso": match.group(1).strip(),
                "type": match.group(2).strip().lower(),
                "title": match.group(3).strip(),
                "detail": match.group(4).strip(),
                "dur": match.group(5).strip(),
                "hr": (match.group(6) or "").strip().lower() in ("hr", "true", "yes", "1"),
            })
        return sorted(plan, key=lambda row: row["iso"]) or None
    except Exception as e:
        print(f"[markdown-plan] error: {e}")
        return None

def infer_workout_type(title, detail=""):
    text = f"{title} {detail}".lower()
    if "strength" in text or "deadlift" in text or "squat" in text or "press" in text:
        return "strength"
    if "rest" in text or "off" in text:
        return "rest"
    if "walk" in text and "run" not in text:
        return "rest"
    if "social" in text or "upstate" in text or "group" in text:
        return "social"
    if "run" in text or "aerobic" in text or "trail" in text:
        return "run"
    return "rest"

def infer_duration(title, detail=""):
    text = f"{title} {detail}"
    ranges = re.findall(r"(\d+)\s*-\s*(\d+)\s*min", text, flags=re.I)
    if ranges:
        return f"{ranges[0][1]}m"
    minutes = re.findall(r"(\d+)\s*min", text, flags=re.I)
    if minutes:
        return f"{minutes[0]}m"
    return "--"

def load_plan_from_running_coach():
    """Load weekly plans from RunningCoach/logs/plans/week_YYYY-WNN.md."""
    root = Path(RUNNING_COACH_DIR).expanduser()
    plans_dir = root / "logs" / "plans"
    if not plans_dir.exists():
        return None

    rows = []
    day_re = re.compile(r"^##\s+\w+\s+(\d{1,2})/(\d{1,2})\s+[-–—]\s+(.+?)\s*$")
    year_re = re.compile(r"week_(\d{4})-W\d+\.md$", re.I)

    try:
        for path in sorted(plans_dir.glob("week_*.md"))[-6:]:
            year_match = year_re.search(path.name)
            if not year_match:
                continue
            year = int(year_match.group(1))
            current = None
            details = []

            def flush_current():
                if not current:
                    return
                detail = " ".join(details).strip()
                detail = re.sub(r"\s+", " ", detail)
                title = current["title"]
                wtype = infer_workout_type(title, detail)
                rows.append({
                    "iso": current["iso"],
                    "type": wtype,
                    "title": title,
                    "detail": detail[:130] if detail else title,
                    "dur": infer_duration(title, detail),
                    "hr": "hr cap" in f"{title} {detail}".lower(),
                })

            for raw in path.read_text(encoding="utf-8").splitlines():
                match = day_re.match(raw)
                if match:
                    flush_current()
                    month = int(match.group(1))
                    day = int(match.group(2))
                    current = {
                        "iso": f"{year}-{month:02d}-{day:02d}",
                        "title": match.group(3).strip(),
                    }
                    details = []
                    continue
                if current and raw.strip() and not raw.startswith("#") and not raw.startswith("-"):
                    details.append(raw.strip())
            flush_current()

        return sorted(rows, key=lambda row: row["iso"]) or None
    except Exception as e:
        print(f"[running-coach-plan] error: {e}")
        return None

def get_plan():
    now = _time.time()
    if _plan_cache["data"] is None or now - _plan_cache["ts"] > _PLAN_TTL:
        fresh = load_plan_from_running_coach() or load_plan_from_markdown() or load_plan_from_sheets()
        if fresh is not None:
            _plan_cache["data"] = fresh
            _plan_cache["ts"]   = now
    return _plan_cache["data"] if _plan_cache["data"] is not None else PLAN

# ── Hardcoded fallback plan ───────────────────────────────────────────────────

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
  {"iso":"2026-05-11","type":"run",     "title":"Completed: Indoor Run <138 HR", "detail":"Completed session from bridge week.","dur":"—","hr":True},
  {"iso":"2026-05-12","type":"social",  "title":"Completed: North Lake out and back", "detail":"Completed session from bridge week.","dur":"—","hr":False},
  {"iso":"2026-05-13","type":"rest",    "title":"Recovery / no prescribed training", "detail":"Recovery day from bridge week.","dur":"—","hr":False},
  {"iso":"2026-05-14","type":"rest",    "title":"Rest", "detail":"Blood donation day. No training.","dur":"—","hr":False},
  {"iso":"2026-05-15","type":"run",     "title":"Easy run", "detail":"25-35 min, RPE 3-4, HR cap 145. Keep it relaxed; this is a rhythm run, not a test.","dur":"35m","hr":True},
  {"iso":"2026-05-16","type":"rest",    "title":"Off or easy walk", "detail":"Optional 20-30 min walk only.","dur":"30m","hr":False},
  {"iso":"2026-05-17","type":"run",     "title":"Easy aerobic run", "detail":"40-55 min, RPE 3-4, HR cap 145-150. Road, trail, or Assault Runner.","dur":"55m","hr":True},
  {"iso":"2026-05-18","type":"strength","title":"Strength A", "detail":"Upper + trunk + lower patterning. 45-55 min, moderate only.","dur":"55m","hr":False},
  {"iso":"2026-05-19","type":"social",  "title":"Upstate RC trail run anchor", "detail":"Open terrain, controlled effort. Target 35-50 min, RPE 5-7, avoid racing climbs.","dur":"50m","hr":False},
  {"iso":"2026-05-20","type":"rest",    "title":"Rest or recovery walk", "detail":"Default rest if Tuesday felt hard. Optional 20 min recovery walk.","dur":"20m","hr":False},
  {"iso":"2026-05-21","type":"run",     "title":"Easy run", "detail":"25-35 min, RPE 3-4, HR cap 140-145. Assault Runner is fine; ignore pace.","dur":"35m","hr":True},
  {"iso":"2026-05-22","type":"strength","title":"Strength B", "detail":"Lower technique + posterior chain. 40-50 min, RPE 6-7, no grinders.","dur":"50m","hr":False},
  {"iso":"2026-05-23","type":"run",     "title":"Long easy run", "detail":"55-70 min, ideally rolling trail or road hills. RPE 3-4. Cap at 55 if flat.","dur":"70m","hr":False},
  {"iso":"2026-05-24","type":"rest",    "title":"Off or very easy", "detail":"Optional 20-30 min very easy only if the week feels smooth.","dur":"30m","hr":False},
  {"iso":"2026-05-25","type":"strength","title":"Strength A", "detail":"Upper + trunk + lower patterning, RPE 6-7.","dur":"55m","hr":False},
  {"iso":"2026-05-26","type":"social",  "title":"Upstate RC trail run anchor", "detail":"40-55 min, RPE 5-7. Run with the group, avoid racing climbs.","dur":"55m","hr":False},
  {"iso":"2026-05-27","type":"rest",    "title":"Rest or recovery walk", "detail":"Default rest if Tuesday felt hard or legs are sore.","dur":"30m","hr":False},
  {"iso":"2026-05-28","type":"run",     "title":"Easy run", "detail":"30-40 min, RPE 3-4, HR cap 145. Optional relaxed strides if fresh.","dur":"40m","hr":True},
  {"iso":"2026-05-29","type":"strength","title":"Strength B", "detail":"Lower technique + posterior chain. 40-50 min, RPE 6-7, no grinders.","dur":"50m","hr":False},
  {"iso":"2026-05-30","type":"run",     "title":"Long easy run", "detail":"60-75 min rolling trail or road hills. Keep HR mostly below 150.","dur":"75m","hr":True},
  {"iso":"2026-05-31","type":"rest",    "title":"Off or very easy", "detail":"Optional 20-30 min very easy if the week felt smooth.","dur":"30m","hr":False},
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
    start, end = date(2026, 4, 27), date(2026, 5, 18)
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
    for d in get_plan():
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
                f'stroke="#000" stroke-width="1"/>'
                f'<text x="{(width+36)//2}" y="{height//2+4}" text-anchor="middle" '
                f'font-size="9" fill="#000" font-family="IBM Plex Mono,monospace">no elevation data</text>'
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
             f'<path d="{path}" fill="#ccc" stroke="#000" stroke-width="1.2" stroke-linejoin="round"/>']

    for tick in ticks:
        yp  = py + ch - (tick - ticks[0]) / span * ch
        lbl = f"{int(tick):,} ft"
        parts.append(f'<line x1="{y_ax}" y1="{yp:.1f}" x2="{y_ax+cw}" y2="{yp:.1f}" '
                     f'stroke="#000" stroke-width="0.6" stroke-dasharray="2,3"/>')
        parts.append(f'<text x="{y_ax-3}" y="{yp+3.5:.1f}" font-size="8" fill="#000" '
                     f'text-anchor="end" font-family="IBM Plex Mono,monospace">{lbl}</text>')
    parts.append('</svg>')
    return ''.join(parts)

# ── SVG black fill helper (bypasses CSS background-color in headless renderers) ──

def svg_black_fill(w=800, h=44):
    """Returns an absolutely-positioned SVG rect that paints a solid black background.
    Must be the first child of a position:relative container."""
    return (f'<svg style="position:absolute;top:0;left:0;width:100%;height:100%;'
            f'z-index:0;display:block;overflow:hidden;" '
            f'viewBox="0 0 {w} {h}" preserveAspectRatio="none" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="#000000"/>'
            f'</svg>')

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/trmnl")
def trmnl():
    return Response(json.dumps({"markup": dashboard_html()}), mimetype="application/json")

@app.route("/")
def dashboard():
    return Response(dashboard_html(), mimetype="text/html")

@app.route("/health")
def health():
    payload = {
        "ok": True,
        "service": "trmnl-strava-dashboard",
        "plan_rows_loaded": len(get_plan()),
    }
    return Response(json.dumps(payload), mimetype="application/json")

@app.route("/plan-health")
def plan_health():
    from datetime import date, timedelta
    plan = get_plan()
    today = date.today()
    horizon = today + timedelta(days=10)
    upcoming = [
        row for row in plan
        if today.isoformat() <= row.get("iso", "") <= horizon.isoformat()
    ]
    payload = {
        "ok": bool(upcoming),
        "today": today.isoformat(),
        "horizon": horizon.isoformat(),
        "plan_rows_loaded": len(plan),
        "upcoming_rows": len(upcoming),
        "running_coach_dir": str(Path(RUNNING_COACH_DIR).expanduser()),
        "items": upcoming[:10],
    }
    return Response(json.dumps(payload, indent=2), mimetype="application/json")

def dashboard_html():
    today_iso   = get_today_iso()
    today_label = get_today_label()
    phase_wk    = get_phase_wk()
    week_days   = get_week_days()

    # Today's plan
    today_plan = next((d for d in get_plan() if d["iso"] == today_iso), None)
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
        "run":      "AEROBIC BASE &bull; ZONE 2",
        "social":   "OPEN EFFORT",
        "strength": "STRENGTH FOCUS",
        "rest":     "FULL REST",
    }
    t_zone = zone_map.get(t_type, "")
    hr_note = "HR cap 138 bpm &bull; walk at 139" if t_hr else ""

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
        f'<div class="wm-tick"><svg width="1" height="5" viewBox="0 0 1 5" xmlns="http://www.w3.org/2000/svg"><rect width="1" height="5" fill="#000"/></svg><span class="wm-tick-lbl">{lbl}</span></div>'
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
  <div class="up-hdr">
    <span class="up-num">
      <svg viewBox="0 0 18 18" width="18" height="18" xmlns="http://www.w3.org/2000/svg"><rect width="18" height="18" fill="#000"/><text x="9" y="13" text-anchor="middle" font-size="10" font-weight="700" fill="#fff" font-family="IBM Plex Mono,monospace">{i}</text></svg>
    </span>
    <span class="up-date">{u['label']}</span>
  </div>
  <div class="up-icon">{ico}</div>
  <div class="up-name">{u['title']}</div>
  <div class="up-foot">
    <span class="up-dur">{icon_stopwatch(13,15)} {dur_s}</span>
    <span class="up-tag">
      <svg viewBox="0 0 60 16" width="60" height="16" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg"><rect width="60" height="16" fill="#000"/><text x="30" y="12" text-anchor="middle" font-size="8" font-weight="700" fill="#fff" font-family="IBM Plex Mono,monospace">{tag}</text></svg>
    </span>
  </div>
</div>"""

    # Black fill SVGs for header and YTD
    hdr_bg  = svg_black_fill(800, 42)
    ytd_bg  = svg_black_fill(800, 44)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@400;700&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:100%;height:480px;overflow:hidden;background:#fff;color:#000;
     font-family:'IBM Plex Mono',monospace;font-size:11px}}
svg{{display:inline-block;vertical-align:middle;flex-shrink:0}}

/* Screen grid */
.screen{{width:100%;height:480px;display:grid;
         grid-template-rows:42px 1fr 80px 118px 44px;
         border:2px solid #000;overflow:hidden}}
.dv{{width:1px;background:#000;align-self:stretch}}

/* ── HEADER — black via SVG rect, not CSS background ── */
.hdr{{position:relative;color:#fff;display:flex;align-items:center;
      padding:0 16px;gap:12px}}
.hdr-title{{position:relative;z-index:1;font-size:18px;font-weight:700;
            letter-spacing:0.05em;text-transform:uppercase;
            font-family:'IBM Plex Sans',sans-serif;flex:1}}
.hdr-date{{position:relative;z-index:1;font-size:11px;letter-spacing:0.06em;
           opacity:.85;white-space:nowrap}}
.hdr-week{{position:relative;z-index:1;font-size:10px;letter-spacing:0.12em;
           border:1.5px solid #fff;padding:3px 10px;
           text-transform:uppercase;white-space:nowrap}}

/* ── MAIN (3 cols) ── */
.main{{display:grid;grid-template-columns:310px 1px 210px 1px 1fr;
       border-bottom:1px solid #000;overflow:hidden}}

/* Last Run */
.col-run{{padding:9px 12px 6px;display:flex;flex-direction:column;overflow:hidden}}
.s-lbl{{font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:#000;font-weight:700;margin-bottom:4px}}
.act-row{{display:flex;align-items:center;gap:8px;margin-bottom:6px}}
.act-name{{font-size:21px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
           line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.stats-grid{{display:grid;grid-template-columns:repeat(4,1fr);
             border:1px solid #000;flex-shrink:0;margin-bottom:6px}}
.st{{padding:4px 6px;border-right:1px solid #000}}
.st:last-child{{border-right:none}}
.st-lbl{{font-size:7px;letter-spacing:.12em;text-transform:uppercase;color:#000;margin-bottom:1px}}
.st-val{{font-size:20px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
         line-height:1;letter-spacing:-.02em}}
.st-unit{{font-size:9px;color:#000;display:block;margin-top:1px}}
.elev-box{{overflow:hidden;flex-shrink:0}}

/* Today */
.col-today{{padding:9px 12px 7px;display:flex;flex-direction:column;overflow:hidden}}
.today-title{{display:flex;align-items:flex-start;gap:7px;margin-bottom:4px}}
.today-name{{font-size:17px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
             line-height:1.15;letter-spacing:-.02em}}
.dsep{{border-top:1px solid #000;margin:5px 0}}
.dur-row{{display:flex;align-items:baseline;gap:4px;margin-bottom:3px}}
.dur-num{{font-size:44px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
          line-height:1;letter-spacing:-.04em}}
.dur-unit{{font-size:13px;color:#000;font-family:'IBM Plex Sans',sans-serif}}
.t-zone{{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:#000;margin-bottom:5px}}
.t-detail{{font-size:10px;color:#000;line-height:1.55;flex:1}}
.t-hr{{font-size:9px;color:#000;margin-top:4px}}
.t-tag{{display:inline-block;margin-top:5px}}

/* Coach's Tip */
.col-coach{{padding:9px 12px 7px;display:flex;flex-direction:column;overflow:hidden}}
.coach-body{{display:flex;gap:9px;align-items:flex-start;flex:1;min-height:0;margin-bottom:4px}}
.coach-text{{font-size:11px;color:#000;line-height:1.55}}
.focus-row{{display:flex;align-items:flex-end;justify-content:space-between;gap:4px}}
.focus-title{{font-size:13px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
              letter-spacing:-.01em;margin-bottom:2px}}
.focus-sub{{font-size:10px;color:#000}}

/* ── WEEKLY MILEAGE ── */
.wm-row{{display:grid;grid-template-columns:210px 1fr;
         border-bottom:1px solid #000;overflow:hidden}}
.wm-left{{padding:7px 16px;display:flex;flex-direction:column;justify-content:center}}
.wm-lbl{{font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:#000;font-weight:700;margin-bottom:3px}}
.wm-nums{{display:flex;align-items:baseline;gap:4px;line-height:1}}
.wm-num{{font-size:28px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;letter-spacing:-.03em}}
.wm-goal{{font-size:13px;color:#000;font-family:'IBM Plex Sans',sans-serif}}
.wm-pct{{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:#000;margin-top:3px}}
.wm-right{{padding:10px 16px 6px;display:flex;flex-direction:column;justify-content:center}}
.wm-bar{{display:flex;height:24px;border:1.5px solid #000;overflow:hidden;margin-bottom:3px}}
.wm-fill{{height:100%;display:block}}
.wm-remain{{flex:1;height:100%}}
.wm-scale{{display:flex;justify-content:space-between}}
.wm-tick{{display:flex;flex-direction:column;align-items:center;gap:1px}}
.wm-tick-lbl{{font-size:8px;color:#000;font-weight:600}}

/* ── INFO ROW ── */
.info-row{{display:grid;grid-template-columns:190px 1px 1fr;overflow:hidden}}

/* Weather */
.col-wx{{padding:7px 14px 8px;display:flex;flex-direction:column;justify-content:flex-start}}
.wx-top{{display:flex;align-items:center;gap:8px;margin-bottom:4px}}
.wx-temp{{font-size:28px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
          letter-spacing:-.03em;line-height:1}}
.wx-cond{{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
          margin-bottom:4px}}
.wx-detail{{font-size:10px;color:#000;line-height:1.7}}
.wx-wind-row{{display:flex;align-items:center;gap:6px;font-size:10px;color:#000;margin-top:2px}}

/* Upcoming */
.col-up-wrap{{display:flex;flex-direction:column;overflow:hidden}}
.up-head{{font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:#000;font-weight:700;
          padding:5px 11px 4px;border-bottom:1px solid #000;flex-shrink:0}}
.col-up{{display:grid;grid-template-columns:repeat(3,1fr);flex:1;overflow:hidden}}
.up-card{{padding:6px 11px 5px;border-right:1px solid #000;
          display:flex;flex-direction:column;overflow:hidden}}
.up-card:last-child{{border-right:none}}
.up-hdr{{display:flex;align-items:center;gap:6px;margin-bottom:6px}}
.up-num{{flex-shrink:0;line-height:0}}
.up-date{{font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#000}}
.up-icon{{margin-bottom:4px}}
.up-name{{font-size:16px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;
          line-height:1.2;letter-spacing:-.01em;flex:1;margin-bottom:4px}}
.up-foot{{display:flex;align-items:center;justify-content:space-between;gap:4px}}
.up-dur{{display:flex;align-items:center;gap:4px;font-size:9px;color:#000;
         white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.up-tag{{line-height:0;flex-shrink:0}}

/* ── YTD BANNER — black via SVG rect, not CSS background ── */
.ytd{{position:relative;display:grid;grid-template-columns:repeat(5,1fr);color:#fff}}
.yt{{position:relative;z-index:1;display:flex;flex-direction:column;
     justify-content:center;align-items:center;
     border-right:1px solid #fff;padding:0 4px}}
.yt:last-child{{border-right:none}}
.yt-lbl{{font-size:7px;letter-spacing:.14em;color:#fff;text-transform:uppercase;margin-bottom:1px}}
.yt-val{{font-size:14px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;line-height:1}}
.yt-sub{{font-size:8px;color:#fff;margin-top:1px}}
</style>
</head>
<body>
<div class="screen">

<!-- HEADER: black background via inline SVG rect (CSS background-color stripped by e-ink renderer) -->
<div class="hdr">
  {hdr_bg}
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
    <div class="t-tag">
      <svg viewBox="0 0 80 18" width="80" height="18" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg"><rect width="80" height="18" fill="#000"/><text x="40" y="13" text-anchor="middle" font-size="9" font-weight="700" fill="#fff" font-family="IBM Plex Mono,monospace">{t_type.upper()}</text></svg>
    </div>
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
      <svg class="wm-fill" viewBox="0 0 400 24" width="{wm_pct}%" height="100%" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg"><rect width="400" height="24" fill="#000"/></svg>
      <svg class="wm-remain" viewBox="0 0 100 24" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg"><defs><pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><line x1="0" y1="0" x2="0" y2="5" stroke="#000" stroke-width="1.5"/></pattern></defs><rect width="100" height="24" fill="url(#hatch)"/></svg>
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

<!-- YTD BANNER: black background via inline SVG rect -->
<div class="ytd">
  {ytd_bg}
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
