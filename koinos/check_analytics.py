"""Check access to an official Claude analytics endpoint without printing secrets or user data."""
import argparse
import datetime
import json
import os
import urllib.error
import urllib.parse
import urllib.request

def main():
    p=argparse.ArgumentParser()
    p.add_argument("kind",choices=["console","enterprise"])
    p.add_argument("--date",default=(datetime.datetime.now(datetime.timezone.utc).date()-datetime.timedelta(days=2)).isoformat())
    args=p.parse_args()
    day=datetime.date.fromisoformat(args.date).isoformat()
    if args.kind=="console":
        env="ANTHROPIC_ADMIN_KEY"
        path="/v1/organizations/usage_report/claude_code"
        query={"starting_at":day}
    else:
        env="ANTHROPIC_ANALYTICS_KEY"
        path="/v1/organizations/analytics/users"
        query={"date":day}
    key=os.environ.get(env)
    if not key: p.error("Set "+env+" securely in your local environment.")
    req=urllib.request.Request("https://api.anthropic.com"+path+"?"+urllib.parse.urlencode(query),headers={"x-api-key":key,"anthropic-version":"2026-10-21"})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:
            data=json.load(r)
            print("HTTP",r.status,"; analytics endpoint accessible.")
            print("Response keys:",", ".join(data.keys()) if isinstance(data,dict) else type(data).__name__)
            if isinstance(data,dict) and isinstance(data.get("data"),list):
                print("Rows on first page:",len(data["data"]))
            print("Historical activity only; this does not establish remaining subscription quota.")
    except urllib.error.HTTPError as e:
        print("HTTP",e.code,"; verify plan, key scope, API version and date. No user data printed.")
        raise SystemExit(1)
    except (OSError,ValueError):
        print("Network or response error.")
        raise SystemExit(1)
if __name__=="__main__":
    main()
