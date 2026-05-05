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
        acts    = requests.get("https://www.strava.com/api/v3/athlete/activities?per_page=30", headers=headers).json()
        return athlete, stats, acts
    except:
        return None, None, None

def meters_to_miles(m): return round(m / 1609.34, 1)
def meters_to_feet(m):  return f"{round(m * 3.28084):,}"
def sec_to_hours(s):    return round(s / 3600)
def sec_to_minsec(s):
    m = int(s // 60); sec = int(s % 60)
    return f"{m}:{sec:02d}"

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
    if dtype == "run":      return "&#9675;"   # circle = run
    if dtype == "social":   return "&#9651;"   # triangle = social
    if dtype == "strength": return "&#9632;"   # square = strength
    return "&mdash;"

def build_html():
    return dashboard_html()

@app.route("/trmnl")
def trmnl():
    import json
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

    # Today's workout
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
        today_detail = "Rest or check your Bevel plan."
        today_tag    = "REST"
        today_dur    = "&mdash;"
        today_hr     = False
        today_type   = "rest"

    # Week strip HTML
    day_names = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
    week_strip_html = ""
    for i, iso in enumerate(week_days):
        plan    = next((d for d in PLAN if d["iso"] == iso), None)
        is_today = iso == today_iso
        is_past  = iso < today_iso
        dtype   = plan["type"] if plan else "rest"
        dur     = plan["dur"]  if plan else "&mdash;"

        if is_today:
            box_class = "wd-today"
            content   = day_symbol(dtype)
        elif is_past and plan and dtype != "rest":
            box_class = "wd-done"
            content   = "&#10003;"
        elif dtype == "rest":
            box_class = "wd-rest"
            content   = "&mdash;"
        else:
            box_class = ""
            content   = day_symbol(dtype)

        week_strip_html += f"""
        <div class="week-day">
          <div class="wd-name">{day_names[i]}</div>
          <div class="wd-box {box_class}">{content}</div>
          <div class="wd-dur">{dur}</div>
        </div>"""

    # Strava data
    athlete, stats, acts = get_strava_data()

    if stats and acts:
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

        recent3 = [a for a in acts if isinstance(a, dict)][:3]
        recent_html = ""
        for a in recent3:
            atype = a.get("type", "")
            if atype in ("Run", "Walk"):   icon = "&#9675;"
            elif atype in ("WeightTraining","Workout"): icon = "&#9632;"
            else:                           icon = "&#9651;"
            dist  = f"{meters_to_miles(a.get('distance',0))} mi" if a.get("distance",0) > 100 else "&mdash;"
            hr    = f"{round(a['average_heartrate'])} bpm" if a.get("average_heartrate") else atype
            name  = a.get("name","")[:18]
            time  = sec_to_minsec(a.get("moving_time", 0))
            from datetime import datetime
            try:
                dt   = datetime.fromisoformat(a["start_date_local"].replace("Z",""))
                date_str = dt.strftime("%a %b %-d")
            except:
                date_str = ""
            recent_html += f"""
            <div class="recent-item">
              <div class="ri-left"><span class="ri-icon">{icon}</span>
                <div><div class="ri-name">{name}</div><div class="ri-sub">{date_str} &middot; {hr}</div></div>
              </div>
              <div class="ri-right"><div class="ri-dist">{dist}</div><div class="ri-time">{time}</div></div>
            </div>"""
    else:
        dist_mi, act_count, hours, elev_ft = "—", "—", "—", "—"
        pace_str, vo2, vo2_pct, vo2_goal   = "—", "—", 0, "50.0 target"
        recent_html = '<div style="font-size:8px;color:#999">No Strava data</div>'

    hr_block = '<div class="hr-alert">&#9829; CAP: 138 bpm &middot; Walk at 139</div>' if today_hr else ""
    strength_tag = '<span class="tag tag-outline">GARAGE RACK</span>' if today_type == "strength" else ""
    aerobic_tag  = '<span class="tag tag-outline">AEROBIC BASE</span>' if today_type == "run" else ""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:800px; height:480px; overflow:hidden; background:#fff; color:#000; font-family:'IBM Plex Mono',monospace; font-size:12px; }}
  .screen {{ width:800px; height:480px; display:grid; grid-template-rows:40px 1fr 50px; border:2px solid #000; }}
  .header {{ display:grid; grid-template-columns:auto 1fr auto auto; align-items:center; gap:14px; padding:0 14px; border-bottom:2px solid #000; background:#000; color:#fff; }}
  .strava-mark {{ font-size:11px; font-weight:700; letter-spacing:0.15em; display:flex; align-items:center; gap:5px; }}
  .header-title {{ font-size:11px; font-weight:600; letter-spacing:0.04em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .header-phase {{ font-size:9px; letter-spacing:0.1em; border:1px solid #fff; padding:1px 7px; text-transform:uppercase; white-space:nowrap; }}
  .header-date {{ font-size:10px; letter-spacing:0.08em; opacity:0.7; white-space:nowrap; }}
  .body {{ display:grid; grid-template-columns:296px 1px 210px 1px 1fr; overflow:hidden; }}
  .divider-v {{ background:#000; width:1px; }}
  .divider-h {{ background:#000; height:1px; }}
  .col-left {{ display:grid; grid-template-rows:1fr 1px 94px; overflow:hidden; }}
  .today-panel {{ padding:11px 13px; display:flex; flex-direction:column; justify-content:space-between; overflow:hidden; }}
  .today-eyebrow {{ font-size:9px; letter-spacing:0.2em; text-transform:uppercase; color:#666; margin-bottom:3px; }}
  .today-title {{ font-size:24px; font-weight:700; line-height:1.05; letter-spacing:-0.02em; font-family:'IBM Plex Sans',sans-serif; margin-bottom:5px; }}
  .today-detail {{ font-size:11px; color:#333; line-height:1.55; }}
  .today-tags {{ display:flex; gap:5px; margin-top:7px; flex-wrap:wrap; }}
  .tag {{ font-size:9px; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; border:1.5px solid #000; padding:2px 6px; }}
  .tag-filled {{ background:#000; color:#fff; }}
  .tag-outline {{ background:#fff; color:#000; }}
  .hr-alert {{ display:flex; align-items:center; gap:5px; margin-top:7px; font-size:11px; font-weight:700; }}
  .week-strip {{ padding:7px 13px; display:flex; flex-direction:column; justify-content:center; gap:4px; }}
  .week-strip-label {{ font-size:9px; letter-spacing:0.14em; text-transform:uppercase; color:#888; }}
  .week-days {{ display:grid; grid-template-columns:repeat(7,1fr); gap:3px; }}
  .week-day {{ display:flex; flex-direction:column; align-items:center; gap:2px; }}
  .wd-name {{ font-size:8px; font-weight:700; letter-spacing:0.06em; color:#777; }}
  .wd-box {{ width:30px; height:30px; border:1.5px solid #bbb; display:flex; align-items:center; justify-content:center; font-size:15px; background:#fff; }}
  .wd-today {{ border-color:#000; border-width:2.5px; }}
  .wd-done {{ border-color:#000; background:#000; color:#fff; font-size:13px; }}
  .wd-rest {{ border-color:#ddd; background:#f5f5f5; font-size:10px; color:#999; }}
  .wd-dur {{ font-size:8px; color:#999; text-align:center; }}
  .col-mid {{ padding:11px 13px; display:flex; flex-direction:column; }}
  .col-label {{ font-size:9px; letter-spacing:0.18em; text-transform:uppercase; color:#777; margin-bottom:8px; display:flex; align-items:center; gap:6px; }}
  .col-label::after {{ content:''; flex:1; height:1px; background:#ddd; }}
  .strava-stat {{ display:flex; flex-direction:column; padding:7px 0; border-bottom:1px solid #ebebeb; flex:1; justify-content:center; }}
  .strava-stat:last-child {{ border-bottom:none; }}
  .ss-label {{ font-size:9px; letter-spacing:0.1em; text-transform:uppercase; color:#999; margin-bottom:1px; }}
  .ss-value {{ font-size:21px; font-weight:700; letter-spacing:-0.02em; font-family:'IBM Plex Sans',sans-serif; line-height:1; }}
  .ss-sub {{ font-size:9px; color:#777; margin-top:1px; }}
  .col-right {{ padding:11px 13px; display:flex; flex-direction:column; gap:10px; overflow:hidden; }}
  .vo2-num {{ font-size:34px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; letter-spacing:-0.03em; line-height:1; }}
  .vo2-unit {{ font-size:10px; color:#777; margin-left:3px; }}
  .bar-track {{ height:7px; background:#eee; border:1px solid #ccc; margin-top:5px; position:relative; overflow:hidden; }}
  .bar-fill {{ height:100%; background:#000; }}
  .bar-target {{ position:absolute; right:0; top:-1px; bottom:-1px; width:2px; background:#555; }}
  .bar-labels {{ display:flex; justify-content:space-between; margin-top:3px; font-size:8.5px; color:#999; }}
  .phase-bar-track {{ height:9px; background:#eee; border:1px solid #ccc; overflow:hidden; margin-top:5px; }}
  .phase-bar-fill {{ height:100%; background:#000; }}
  .phase-meta {{ display:flex; justify-content:space-between; margin-top:3px; font-size:8.5px; color:#999; }}
  .recent-item {{ display:flex; align-items:center; justify-content:space-between; padding:4px 0; border-bottom:1px solid #efefef; font-size:10px; }}
  .recent-item:last-child {{ border-bottom:none; }}
  .ri-left {{ display:flex; align-items:center; gap:5px; }}
  .ri-icon {{ font-size:12px; }}
  .ri-name {{ font-weight:600; font-size:10px; }}
  .ri-sub {{ font-size:8.5px; color:#999; }}
  .ri-right {{ text-align:right; }}
  .ri-dist {{ font-weight:700; font-size:10px; }}
  .ri-time {{ font-size:8.5px; color:#999; }}
  .footer {{ display:grid; grid-template-columns:repeat(4,1fr); border-top:2px solid #000; }}
  .footer-cell {{ display:flex; align-items:center; gap:7px; padding:0 12px; border-right:1px solid #ccc; }}
  .footer-cell:last-child {{ border-right:none; }}
  .fc-icon {{ font-size:14px; flex-shrink:0; }}
  .fc-label {{ font-size:8.5px; text-transform:uppercase; letter-spacing:0.1em; color:#888; margin-bottom:1px; }}
  .fc-val {{ font-size:12px; font-weight:700; font-family:'IBM Plex Sans',sans-serif; line-height:1.1; }}
  .fc-sub {{ font-size:8.5px; color:#777; }}
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
    <div class="col-left">
      <div class="today-panel">
        <div>
          <div class="today-eyebrow">Today's Workout</div>
          <div class="today-title">{today_title}</div>
          <div class="today-detail">{today_detail}</div>
          <div class="today-tags">
            <span class="tag tag-filled">{today_tag}</span>
            <span class="tag tag-outline">{today_dur}</span>
            {aerobic_tag}
            {strength_tag}
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

    <div class="col-mid">
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
    </div>

    <div class="divider-v"></div>

    <div class="col-right">
      <div>
        <div class="col-label">VO2max Estimate</div>
        <span class="vo2-num">{vo2}</span><span class="vo2-unit">mL/kg/min</span>
        <div class="bar-track">
          <div class="bar-fill" style="width:{vo2_pct}%"></div>
          <div class="bar-target"></div>
        </div>
        <div class="bar-labels"><span>{vo2} current</span><span>{vo2_goal}</span></div>
      </div>
      <div>
        <div class="col-label">Phase 0 Progress</div>
        <div class="phase-bar-track"><div class="phase-bar-fill" style="width:{phase_pct}%"></div></div>
        <div class="phase-meta"><span>Apr 27</span><span>WK {phase_wk} OF 4</span><span>May 24</span></div>
      </div>
      <div style="flex:1">
        <div class="col-label">Recent Activities</div>
        {recent_html}
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
    <div class="footer-cell">
      <div class="fc-icon">&#9675;</div>
      <div>
        <div class="fc-label">Season Goal</div>
        <div class="fc-val">50k Trail</div>
        <div class="fc-sub">Upstate Running Club</div>
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
