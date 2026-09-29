#!/usr/bin/env python3
"""
Vlastní cloud pro FlashForge Creator 3 (náhrada za *.sz3dp.com).

Fáze 1 (CAPTURE): jen loguje vše, co tiskárna pošle, a vrací minimální
"success" odpověď. Z logů pak doladíme přesný formát odpovědí.

Tiskárna neověřuje TLS certifikát (SSL_VERIFYPEER/HOST = 0), takže stačí
self-signed cert a DNS přesměrování cloud.sz3dp.com -> IP tohoto serveru.

Spuštění:
    python3 ff_cloud.py            # HTTPS na 0.0.0.0:10443 (a HTTP na :8080)
Cert se vygeneruje sám do ./cert.pem/key.pem (potřebuje `openssl` v PATH).

Poslání příkazu tiskárně (vloží se do odpovědi na příští /printer/status):
    echo '{"Command":"pause","Data":{}}' > cmd.json
Podporované: newjob, pause, resume, opencamera, closecamera.
"""
import base64, json, os, socket, ssl, subprocess, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "requests.log")
CMD = os.path.join(HERE, "cmd.json")
CERT = os.path.join(HERE, "cert.pem")
KEY = os.path.join(HERE, "key.pem")
SNAP = os.path.join(HERE, "snapshot.jpg")

# posledni znamy stav tiskarny (sdileny mezi vlakny)
STATE = {"detail": {}, "snapshot": b"", "ip": ""}
PRINTER_PORT = 8899


def send_gcode(cmds, ip=None):
    """Prevezme rizeni (~M601), posle prikazy s ~ prefixem, uvolni (~M602).
    Vraci (ok, text). cmds = seznam retezcu bez ~ prefixu."""
    ip = ip or STATE.get("ip") or ""
    if not ip:
        return False, "nezname IP tiskarny (jeste neprisel status)"
    if isinstance(cmds, str):
        cmds = [cmds]
    seq = ["M601 S0"] + list(cmds) + ["M602"]
    out = []
    try:
        s = socket.create_connection((ip, PRINTER_PORT), timeout=5)
        s.settimeout(5)
        for c in seq:
            s.sendall(("~" + c + "\r\n").encode())
            time.sleep(0.05)
            try:
                data = s.recv(65536)
            except socket.timeout:
                data = b""
            out.append("> %s\n%s" % (c, data.decode("utf-8", "replace").strip()))
        s.close()
        log(">> 8899 %s: %s" % (ip, " | ".join(cmds)))
        return True, "\n".join(out)
    except Exception as e:
        log("!! 8899 chyba:", e)
        return False, "chyba spojeni s tiskarnou %s:%d (%s)" % (ip, PRINTER_PORT, e)


PAGE = """<!doctype html><html lang=cs><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Creator 3</title>
<style>
:root{--bg:#0f1216;--card:#1a1f27;--fg:#e6e9ef;--mut:#8a93a3;--acc:#3ea6ff;--ok:#39d98a;--warn:#ffb020}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;padding:16px}
h1{font-size:18px;margin:0 0 12px}h1 small{color:var(--mut);font-weight:400}
.wrap{max-width:900px;margin:0 auto;display:grid;gap:16px;grid-template-columns:1fr}
@media(min-width:720px){.wrap{grid-template-columns:1.2fr 1fr}}
.card{background:var(--card);border-radius:12px;padding:14px}
img{width:100%;border-radius:8px;display:block;background:#000;min-height:120px}
.stat{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #262c36}
.stat:last-child{border:0}.k{color:var(--mut)}.v{font-weight:600}
.bar{height:10px;background:#262c36;border-radius:6px;overflow:hidden;margin:8px 0}
.bar>i{display:block;height:100%;background:var(--acc);width:0}
.badge{padding:2px 10px;border-radius:20px;font-size:13px;font-weight:600;background:#262c36}
.temps{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}
.temp{flex:1;min-width:90px;background:#12161c;border-radius:8px;padding:8px;text-align:center}
.temp b{font-size:20px}.temp span{color:var(--mut);font-size:12px}
table{width:100%;border-collapse:collapse;margin-top:6px;font-size:13px}
td{padding:4px 6px;border-bottom:1px solid #262c36}td:first-child{color:var(--mut)}
#off{color:var(--warn)}
.ctrl{grid-column:1/-1}
.grp{margin:10px 0}.grp>label{display:block;color:var(--mut);font-size:12px;margin-bottom:6px}
button{font:inherit;color:var(--fg);background:#262c36;border:0;border-radius:8px;
padding:9px 12px;cursor:pointer;margin:3px}button:hover{background:#323a47}
button.acc{background:var(--acc);color:#062338;font-weight:600}
button.stop{background:#e5484d;color:#fff;font-weight:700}
.pad{display:grid;grid-template-columns:repeat(3,52px);gap:4px;width:max-content}
.pad button{width:52px;height:44px;margin:0;padding:0}
.row{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
input[type=number]{width:64px;background:#12161c;border:1px solid #2c3542;color:var(--fg);
border-radius:6px;padding:7px}
input#raw{flex:1;min-width:160px;background:#12161c;border:1px solid #2c3542;color:var(--fg);
border-radius:6px;padding:8px;font-family:ui-monospace,monospace}
pre#reply{background:#0b0e12;border-radius:8px;padding:10px;max-height:150px;overflow:auto;
font-size:12px;color:var(--mut);white-space:pre-wrap;margin:8px 0 0}
.seg button{border-radius:6px}.seg button.on{background:var(--acc);color:#062338}
</style>
<div class=wrap>
 <div class=card><img id=cam src="/snapshot.jpg" alt="kamera"></div>
 <div class=card>
   <h1>FlashForge Creator 3 <small id=off></small></h1>
   <div class=stat><span class=k>Stav</span><span class="v badge" id=job>-</span></div>
   <div class=stat><span class=k>Průběh</span><span class=v id=prog>-</span></div>
   <div class=bar><i id=progbar></i></div>
   <div class=temps>
     <div class=temp><span>Tryska L</span><br><b id=t0>-</b></div>
     <div class=temp><span>Tryska P</span><br><b id=t1>-</b></div>
     <div class=temp><span>Podložka</span><br><b id=bed>-</b></div>
   </div>
   <div class=stat style=margin-top:8px><span class=k>Soubor</span><span class=v id=file>-</span></div>
   <div class=stat><span class=k>Filament</span><span class=v id=fil>-</span></div>
   <div class=stat><span class=k>IP</span><span class=v id=ip>-</span></div>
   <table id=all></table>
 </div>
 <div class="card ctrl">
   <h1>Ovládání</h1>
   <div class=row style=margin-bottom:8px>
     <button class=acc onclick="g(['G28'])">🏠 Domů</button>
     <button onclick="g(['M18'])">Motory OFF</button>
     <button onclick="g(['M106'])">Větrák ON</button>
     <button onclick="g(['M107'])">Větrák OFF</button>
     <button class=stop onclick="g(['M112'])">⛔ STOP</button>
   </div>
   <div class=grp>
     <label>Krok pohybu</label>
     <span class=seg id=step>
       <button data-s=0.1 onclick="setStep(this)">0.1</button>
       <button data-s=1 onclick="setStep(this)">1</button>
       <button data-s=10 class=on onclick="setStep(this)">10</button>
       <button data-s=50 onclick="setStep(this)">50</button>
     </span>
   </div>
   <div class=row style=gap:24px>
     <div>
       <label style=color:var(--mut);font-size:12px>X / Y</label>
       <div class=pad>
         <span></span><button onclick="jog('Y',1)">Y+</button><span></span>
         <button onclick="jog('X',-1)">X−</button><button onclick="g(['G28 X Y'])">⌂</button><button onclick="jog('X',1)">X+</button>
         <span></span><button onclick="jog('Y',-1)">Y−</button><span></span>
       </div>
     </div>
     <div>
       <label style=color:var(--mut);font-size:12px>Z</label>
       <div class=pad style=grid-template-columns:52px>
         <button onclick="jog('Z',1)">Z+</button>
         <button onclick="g(['G28 Z'])">⌂</button>
         <button onclick="jog('Z',-1)">Z−</button>
       </div>
     </div>
   </div>
   <div class=grp>
     <label>Teploty (°C)</label>
     <div class=row>
       Tryska L <input type=number id=tempL value=210>
       <button onclick="g(['M104 S'+val('tempL')+' T0'])">Nahřát L</button>
       Tryska P <input type=number id=tempR value=210>
       <button onclick="g(['M104 S'+val('tempR')+' T1'])">Nahřát P</button>
     </div>
     <div class=row style=margin-top:6px>
       Podložka <input type=number id=tempB value=50>
       <button onclick="g(['M140 S'+val('tempB')])">Nahřát</button>
       <button onclick="g(['M104 S0 T0','M104 S0 T1','M140 S0'])">Vychladit vše</button>
     </div>
   </div>
   <div class=grp>
     <label>Tisk</label>
     <button onclick="g(['M25'])">⏸ Pauza</button>
     <button onclick="g(['M24'])">▶ Pokračovat</button>
     <button class=stop onclick="if(confirm('Zrušit tisk?'))g(['M26'])">⏹ Zrušit</button>
   </div>
   <div class=grp>
     <label>Vlastní příkaz (bez ~, např. G1 X10 F3000)</label>
     <div class=row>
       <input id=raw placeholder="M119" onkeydown="if(event.key=='Enter')raw()">
       <button class=acc onclick="raw()">Odeslat</button>
     </div>
   </div>
   <pre id=reply>připraveno</pre>
 </div>
</div>
<script>
let STEP=10;
function setStep(b){STEP=parseFloat(b.dataset.s);
 document.querySelectorAll('#step button').forEach(x=>x.classList.remove('on'));b.classList.add('on');}
function val(id){return document.getElementById(id).value;}
async function g(cmds){
 const r=document.getElementById('reply');r.textContent='...';
 try{
  const res=await fetch('/control',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({cmds})});
  const j=await res.json();
  r.textContent=(j.ok?'':'CHYBA: ')+(j.reply||j.msg||'');
 }catch(e){r.textContent='chyba: '+e;}
}
function jog(ax,dir){const f=(ax=='Z')?600:3000;
 g(['G91','G1 '+ax+(dir*STEP)+' F'+f,'G90']);}
function raw(){const v=document.getElementById('raw').value.trim();if(v)g([v]);}
function t(a,i){a=a||[];return a[i]!=null?a[i]+'°C':'-'}
async function tick(){
 try{
  const d=await (await fetch('/state',{cache:'no-store'})).json();
  document.getElementById('off').textContent='';
  const job=d.JobStatus||'READY';
  document.getElementById('job').textContent=job;
  const p=Math.round(d.PrintProgress||0);
  document.getElementById('prog').textContent=p+' %';
  document.getElementById('progbar').style.width=p+'%';
  const ct=d.CurTemps||[],tt=d.TargetTemps||[];
  document.getElementById('t0').textContent=t(ct,0)+' / '+t(tt,0);
  document.getElementById('t1').textContent=t(ct,1)+' / '+t(tt,1);
  document.getElementById('bed').textContent=(d.PlatformCurTemp!=null?d.PlatformCurTemp+'°C':'-')+' / '+(d.PlatformTargetTemp||0)+'°C';
  document.getElementById('file').textContent=d.GcodeName||'-';
  document.getElementById('fil').textContent=(d.CumulativeFilament!=null?d.CumulativeFilament+' mm':'-');
  document.getElementById('ip').textContent=d.IPAddress||'-';
  const keys=Object.keys(d).sort();
  document.getElementById('all').innerHTML=keys.map(k=>'<tr><td>'+k+'</td><td>'+JSON.stringify(d[k])+'</td></tr>').join('');
 }catch(e){document.getElementById('off').textContent='(cloud neodpovida)';}
 document.getElementById('cam').src='/snapshot.jpg?'+Date.now();
}
tick();setInterval(tick,2000);
</script></html>"""


def status_page():
    return PAGE
# cloud.sz3dp.com = 443, hz.sz3dp.com = 11002, update.sz3dp.com = 10443
HTTPS_PORTS = [443, 11002, 10443]
HTTP_PORTS = [80, 8080]


def log(*a):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), " ".join(str(x) for x in a))
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def ensure_cert():
    if os.path.exists(CERT) and os.path.exists(KEY):
        return
    log("Generuji self-signed certifikat pro cloud.sz3dp.com ...")
    subprocess.check_call([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", KEY, "-out", CERT, "-days", "3650",
        "-subj", "/CN=cloud.sz3dp.com",
        "-addext", "subjectAltName=DNS:cloud.sz3dp.com,DNS:hz.sz3dp.com,"
                   "DNS:update.sz3dp.com,DNS:update.cn.sz3dp.com",
    ])


def pop_command():
    """Vrati naplanovany prikaz (a smaze ho), nebo None."""
    if not os.path.exists(CMD):
        return None
    try:
        with open(CMD) as f:
            data = json.load(f)
        os.remove(CMD)
        log(">>> posilam tiskarne prikaz:", data)
        return data
    except Exception as e:
        log("chyba cteni cmd.json:", e)
        return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _read_body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(n) if n else b""

    def _send_json(self, obj, code=200):
        self._send_bytes(json.dumps(obj).encode(), "application/json", code)

    def _send_bytes(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _handle(self):
        body = self._read_body()
        path = self.path

        # nase vlastni API (tiskarna vola jen POST na /printer/* a /update)
        u = urlparse(path)
        if u.path == "/control":
            # ovladani tiskarny pres 8899. ?cmd=G28  nebo telo {"cmds":[...]}
            q = parse_qs(u.query)
            cmds = q.get("cmd") or q.get("cmds")
            if not cmds:
                try:
                    cmds = json.loads(body.decode()).get("cmds")
                except Exception:
                    cmds = None
            if not cmds:
                return self._send_json({"ok": False, "msg": "chybi cmd"}, 400)
            ok, txt = send_gcode(cmds)
            return self._send_json({"ok": ok, "reply": txt})

        if self.command == "GET":
            if u.path == "/state":
                d = dict(STATE.get("detail", {})); d["_ip"] = STATE.get("ip", "")
                return self._send_json(d)
            if u.path.startswith("/snapshot"):
                return self._send_bytes(STATE.get("snapshot", b""), "image/jpeg")
            if u.path == "/" or u.path.startswith("/index"):
                return self._send_bytes(status_page().encode(), "text/html")

        # zkus rozparsovat telo
        try:
            req = json.loads(body.decode("utf-8", "replace"))
        except Exception:
            req = {}

        # ze statusu vytahni snapshot (kamera) + Detail (telemetrie),
        # snapshot z logu odstran (je obri)
        if isinstance(req, dict) and "status" in path:
            snap = req.get("Snapshot", "")
            if snap:
                try:
                    STATE["snapshot"] = base64.b64decode(snap)
                    with open(SNAP, "wb") as f:
                        f.write(STATE["snapshot"])
                except Exception as e:
                    log("snapshot decode chyba:", e)
            detail = req.get("Detail", {})
            if detail:
                STATE["detail"] = detail
                if detail.get("IPAddress"):
                    STATE["ip"] = detail["IPAddress"]
                try:
                    with open(os.path.join(HERE, "status.json"), "w") as f:
                        json.dump(detail, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        # zaloguj telo (snapshot zkraceny)
        logreq = dict(req) if isinstance(req, dict) else req
        if isinstance(logreq, dict) and logreq.get("Snapshot"):
            logreq["Snapshot"] = "<%d B jpeg>" % len(logreq["Snapshot"])
        try:
            pretty = json.dumps(logreq, ensure_ascii=False, indent=2)
        except Exception:
            pretty = repr(body[:400])
        # status neloguj cely porad dokola, jen strucne
        if "status" in path:
            d = req.get("Detail", {}) if isinstance(req, dict) else {}
            log("POST /printer/status  Job=%r Prog=%s Temps=%s Plat=%s snap=%dB"
                % (d.get("JobStatus", ""), d.get("PrintProgress"),
                   d.get("CurTemps"), d.get("PlatformCurTemp"),
                   len(STATE.get("snapshot", b""))))
        else:
            log(self.command, path, "\n", pretty)

        # --- minimalni odpovedi (doladime z logu) ---
        # POZOR: tiskarna povazuje za uspech ErrorCode == 200 (overeno v kodu
        # registerPrinter: `cmp r3, #200`), nikoli 0.
        OK = 200
        resp = {"ErrorCode": OK, "Message": "OK"}

        if "update" in path:
            # kontrola firmwaru -> rekni "zadna aktualizace" (zadne balicky)
            resp = {"ErrorCode": OK, "Message": "OK",
                    "SessionID": req.get("SessionID", "")}

        elif "register" in path:
            # Overeno v registerPrinter: uspech = ErrorCode==200 A v odpovedi
            # MUSI byt RegistrationCode (string), jinak "no RegistrationCode"
            # a tiskarna registraci opakuje. AuthToken + PrinterName volitelne.
            token = "LOCALCLOUD-" + str(req.get("SN", "printer"))
            resp = {
                "ErrorCode": OK,
                "Message": "OK",
                "RegistrationCode": req.get("RegistrationCode", ""),
                "AuthToken": token,
                "PrinterName": req.get("PrinterName", "") or "Creator3",
            }

        elif "status" in path:
            # do odpovedi lze vlozit prikaz pro tiskarnu
            cmd = pop_command()
            resp = {"ErrorCode": OK, "Message": "OK"}
            if cmd:
                resp["Command"] = cmd.get("Command", "")
                resp["Data"] = cmd.get("Data", {})

        self._send_json(resp)

    do_POST = _handle
    do_GET = _handle
    do_PUT = _handle

    def log_message(self, *a):
        pass  # vlastni logovani


def make_ctx():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT, KEY)
    # tiskarna ma stary openssl 1.0.2 -> povol i starsi TLS
    try:
        ctx.minimum_version = ssl.TLSVersion.MINIMUM_SUPPORTED
    except Exception:
        pass
    try:
        ctx.set_ciphers("DEFAULT@SECLEVEL=0")  # kvuli starym cipherum tiskarny
    except Exception:
        pass
    return ctx


def serve(port, https):
    try:
        httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    except PermissionError:
        log("!! port %d vyzaduje root (spust pres sudo), preskakuji" % port)
        return
    except OSError as e:
        log("!! port %d nelze otevrit (%s), preskakuji" % (port, e))
        return
    if https:
        httpd.socket = make_ctx().wrap_socket(httpd.socket, server_side=True)
    log("%s listen 0.0.0.0:%d" % ("HTTPS" if https else "HTTP ", port))
    httpd.serve_forever()


def main():
    ensure_cert()
    import threading
    started = 0
    for p in HTTP_PORTS:
        threading.Thread(target=serve, args=(p, False), daemon=True).start()
        started += 1
    for p in HTTPS_PORTS[:-1]:
        threading.Thread(target=serve, args=(p, True), daemon=True).start()
        started += 1
    log("Cekam na tiskarnu. DNS: cloud.sz3dp.com + hz.sz3dp.com -> IP tohoto stroje.")
    log("Pozn.: porty 443/80 vyzaduji sudo. Bez nej pouzij aspon 10443/8080.")
    # posledni port drzime v hlavnim vlakne
    serve(HTTPS_PORTS[-1], True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
