"""Local, opt-in subscription usage pilot using documented statusLine JSON."""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time

PATH = Path.home() / ".synergia" / "quota-snapshot.json"
WINDOWS = ("five_hour", "seven_day")

def extract(payload, now):
    rate = payload.get("rate_limits") if isinstance(payload, dict) else None
    result = {"observed_at": int(now), "source": "claude_code_statusline", "windows": {}}
    for name in WINDOWS:
        w = rate.get(name) if isinstance(rate, dict) else None
        p = w.get("used_percentage") if isinstance(w, dict) else None
        reset = w.get("resets_at") if isinstance(w, dict) else None
        valid = (type(p) in (int, float) and math.isfinite(p) and 0 <= p <= 100
                 and type(reset) in (int, float) and math.isfinite(reset) and reset > now)
        result["windows"][name] = {"used_percentage": p, "resets_at": reset} if valid else None
    return result

def save(data):
    PATH.parent.mkdir(mode=0o700, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=PATH.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(temp, PATH)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def display(snapshot, now):
    stamp = snapshot.get("observed_at") if isinstance(snapshot, dict) else None
    if type(stamp) not in (int,float) or not 0 <= now - stamp <= 300:
        return "Synergia | quota unknown (stale or missing observation)"
    clean = extract({"rate_limits": snapshot.get("windows")}, now)["windows"]
    parts = []
    for name, label in zip(WINDOWS, ("5h", "7d")):
        w = clean[name]
        parts.append(label + ": " + (f'{w["used_percentage"]:g}% used' if w else "unknown"))
    return "Synergia | " + " | ".join(parts) + " (last observed)"

def self_test():
    n = 1000
    fixture = {"rate_limits":{"five_hour":{"used_percentage":20,"resets_at":2000},
                              "seven_day":{"used_percentage":35,"resets_at":3000}},
               "transcript_path":"/private/example","token":"not retained"}
    s = extract(fixture,n)
    assert set(s) == {"observed_at","source","windows"}
    assert "20% used" in display(s,n) and "35% used" in display(s,n)
    assert "stale" in display(s,1301)
    assert extract({},n)["windows"]["five_hour"] is None
    assert extract({"rate_limits":{"five_hour":{"used_percentage":0,"resets_at":999}}},n)["windows"]["five_hour"] is None
    assert extract({"rate_limits":{"five_hour":{"used_percentage":True,"resets_at":2000}}},n)["windows"]["five_hour"] is None
    print("Synthetic self-tests passed (not a live Claude test).")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--show",action="store_true")
    args=p.parse_args()
    if args.self_test:
        self_test()
        return
    now=time.time()
    if args.show:
        try:
            print(display(json.loads(PATH.read_text(encoding="utf-8")),now))
        except (OSError,ValueError):
            print("Synergia | quota unknown (no readable snapshot)")
        return
    try:
        data=extract(json.load(sys.stdin),now)
        save(data)
        print(display(data,now))
    except (OSError,ValueError,TypeError):
        print("Synergia | quota unknown (capture failed)")
if __name__=="__main__":
    main()
