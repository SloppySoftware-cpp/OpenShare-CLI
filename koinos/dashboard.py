"""Local-only prototype for authorized Linux compute resources; Python 3.10+."""
import argparse
import concurrent.futures
import datetime as dt
from usage_report import report as usage_report
import html
import json
import os
import re
import secrets
import shlex
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

REMOTE = """import json,time
def cpu():
    v=list(map(int,open('/proc/stat').readline().split()[1:9]))
    return sum(v),v[3]+v[4]
a,b=cpu()
time.sleep(0.5)
c,d=cpu()
m={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in open('/proc/meminfo'))}
print(json.dumps({'cpu':round(100*(1-(d-b)/max(1,c-a)),1),'ram':round(100*(1-m['MemAvailable']/m['MemTotal']),1)}))
"""
ALIAS = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,62}")
def load_resources(path):
    rows=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows,list) or not 1<=len(rows)<=30:
        raise ValueError("Configure 1 to 30 resources.")
    seen=set()
    for row in rows:
        if set(row)!={"name","ssh_alias"} or not isinstance(row["name"],str) or not 1<=len(row["name"])<=80 or not isinstance(row["ssh_alias"],str) or not ALIAS.fullmatch(row["ssh_alias"]) or row["ssh_alias"] in seen:
            raise ValueError("Invalid or duplicate resource; use name and a unique SSH alias only.")
        seen.add(row["ssh_alias"])
    return rows

def probe(row):
    try:
        p=subprocess.run(["ssh","-o","BatchMode=yes","-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=5",row["ssh_alias"],"python3 -c "+shlex.quote(REMOTE)],capture_output=True,text=True,timeout=10,check=True)
        m=json.loads(p.stdout)
        for k in ("cpu","ram"):
            if type(m[k]) not in (int,float) or not 0<=m[k]<=100:
                raise ValueError("Invalid metric")
        return m
    except (OSError,ValueError,KeyError,subprocess.SubprocessError):
        return None

def load_label(m):
    if m is None: return "Unknown / unreachable"
    return "Low load" if max(m["cpu"],m["ram"])<30 else "In use / higher load"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",default="resources.local.json")
    ap.add_argument("--demo",action="store_true")
    ap.add_argument("--analytics",action="store_true",help="Enable local administrator-only daily Console analytics page")
    args=ap.parse_args()
    rows=[{"name":"Demo compute A","ssh_alias":"demo-a"},{"name":"Demo compute B","ssh_alias":"demo-b"}] if args.demo else load_resources(args.config)
    token=secrets.token_urlsafe(32)
    origin="http://127.0.0.1:8765"
    class Handler(BaseHTTPRequestHandler):
        def respond(self,status,body):
            self.send_response(status)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Security-Policy","default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
        def valid_host(self):
            return self.headers.get("Host")=="127.0.0.1:8765"
        def do_GET(self):
            if self.valid_host() and self.path=="/analytics" and args.analytics and not args.demo:
                key=os.environ.get("ANTHROPIC_ADMIN_KEY")
                if not key: return self.respond(503,"Admin key not configured")
                day=(dt.datetime.now(dt.timezone.utc).date()-dt.timedelta(days=2)).isoformat()
                try:
                    result=usage_report(day,key)
                except (OSError,ValueError,KeyError,TypeError,ArithmeticError):
                    return self.respond(503,"Analytics unavailable. Check plan, key permissions and date.")
                rows_html="".join("<tr>"+"".join("<td>"+html.escape(str(r[k]))+"</td>" for k in ("actor","sessions","input_tokens","output_tokens","estimated_cost_usd"))+"</tr>" for r in result["rows"])
                return self.respond(200,'<!doctype html><meta charset="utf-8"><title>Koinos analytics</title><h1>Historical Claude Code activity</h1><p>UTC date: '+day+' | Remaining quota: unknown. Not live occupancy.</p><p><a href="/">Back</a></p><table border="1"><thead><tr><th>Actor</th><th>Sessions</th><th>Input tokens</th><th>Output tokens</th><th>Estimated USD</th></tr></thead><tbody>'+rows_html+'</tbody></table>')
            if not self.valid_host() or self.path!="/":
                return self.respond(404,"Not found")
            if args.demo:
                metrics=[{"cpu":12,"ram":23},{"cpu":81,"ram":64}]
            else:
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                    metrics=list(pool.map(probe,rows))
            body=[]
            for i,(row,m) in enumerate(zip(rows,metrics)):
                cpu,ram=("Unknown","Unknown") if m is None else (str(m["cpu"])+"%",str(m["ram"])+"%")
                connect=""
                if not args.demo and os.name=="nt" and m is not None:
                    connect=f'<form action="/connect" method="post"><input type="hidden" name="csrf" value="{token}"><button name="id" value="{i}">Connect SSH CLI</button></form>'
                body.append(f'<tr><td>{html.escape(row["name"])}</td><td>{cpu}</td><td>{ram}</td><td>{load_label(m)}</td><td>{connect}</td></tr>')
            mode="DEMO - sample data, connections disabled" if args.demo else "Live SSH samples - not Claude subscription quota"
            analytics_link='<p><a href="/analytics">Daily Claude Code analytics (admin workstation only)</a></p>' if args.analytics and not args.demo else ""
            sampled=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            self.respond(200,'<!doctype html><html><meta charset="utf-8"><title>Koinos</title><style>body{font:16px system-ui;max-width:1000px;margin:50px auto;padding:20px;color:#18253a;background:#f7f9fc}table{border-collapse:collapse;width:100%;background:white}td,th{text-align:left;padding:16px;border-bottom:1px solid #ddd}button,a{color:#16428c}button{padding:8px}</style><h1>KOINOS | Resource dashboard</h1><p>'+mode+' | Sampled '+sampled+'</p>'+analytics_link+'<p>Low load is a snapshot, not a reservation or permission to interrupt someone. Use only assigned SSH identities. Connect opens SSH, then run Claude under your own account.</p><p><a href="/">Refresh samples</a></p><table><thead><tr><th>Resource</th><th>CPU</th><th>RAM</th><th>Load</th><th>Action</th></tr></thead><tbody>'+''.join(body)+'</tbody></table></html>')
        def do_POST(self):
            if not self.valid_host() or self.path!="/connect" or self.headers.get("Origin")!=origin or args.demo or os.name!="nt":
                return self.respond(403,"Connection not permitted")
            try:
                n=int(self.headers.get("Content-Length","0"))
                if not 0<n<=2048: raise ValueError()
                form=parse_qs(self.rfile.read(n).decode("utf-8"),max_num_fields=4)
                if not secrets.compare_digest(form["csrf"][0],token): raise ValueError()
                i=int(form["id"][0])
                if not 0<=i<len(rows): raise ValueError()
                if probe(rows[i]) is None: return self.respond(409,"Host unavailable")
                subprocess.Popen(["ssh","-t","-o","StrictHostKeyChecking=yes",rows[i]["ssh_alias"]],creationflags=subprocess.CREATE_NEW_CONSOLE)
            except (OSError,ValueError,KeyError,IndexError):
                return self.respond(400,"Connection request failed")
            self.send_response(303)
            self.send_header("Location","/")
            self.end_headers()
    print("Koinos local prototype: "+origin)
    ThreadingHTTPServer(("127.0.0.1",8765),Handler).serve_forever()

if __name__=="__main__":
    main()
