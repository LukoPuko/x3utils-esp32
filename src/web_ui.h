// The single-page web UI, served from flash. Vanilla JS + WebSocket so it works
// in any phone browser (Safari on iPhone included — no WebUSB, no app install).
#pragma once
#include <Arduino.h>

static const char INDEX_HTML[] PROGMEM = R"HTML(<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>x3utils ESP32</title>
<style>
:root{
  --bg:#0b0e14; --card:#141a26; --card2:#1b2333; --fg:#e6ecf5; --muted:#8aa0bd;
  --accent:#36d1dc; --accent2:#5b86e5; --ok:#3ad29f; --warn:#ffcc66; --bad:#ff6b6b;
  --line:#243049;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)}
.wrap{max-width:720px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:4px 0 2px;letter-spacing:.3px}
h1 span{background:linear-gradient(90deg,var(--accent),var(--accent2));-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--muted);font-size:12px;margin-bottom:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:14px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.pill{display:inline-flex;align-items:center;gap:6px;background:var(--card2);border:1px solid var(--line);border-radius:999px;padding:5px 11px;font-size:12px;color:var(--muted)}
.dot{width:9px;height:9px;border-radius:50%;background:var(--muted)}
.dot.ok{background:var(--ok)} .dot.bad{background:var(--bad)} .dot.busy{background:var(--warn)}
label.lbl{font-size:12px;color:var(--muted);display:block;margin:10px 0 5px}
select,input[type=text],input[type=password],input[type=number]{width:100%;background:var(--card2);color:var(--fg);
  border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:15px}
.seg{display:flex;background:var(--card2);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.seg button{flex:1;background:transparent;border:0;color:var(--muted);padding:10px;font-size:13px}
.seg button.on{background:linear-gradient(90deg,var(--accent),var(--accent2));color:#071019;font-weight:600}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:4px}
button.act{background:var(--card2);color:var(--fg);border:1px solid var(--line);border-radius:12px;padding:14px 10px;font-size:14px;font-weight:600;text-align:left;line-height:1.2}
button.act small{display:block;color:var(--muted);font-weight:400;font-size:11px;margin-top:3px}
button.act:active{transform:scale(.98)}
button.act:disabled{opacity:.45}
button.danger{border-color:#5a2230;background:#231016}
button.primary{border-color:#1d5a52;background:#0f2a27}
.bar{height:10px;background:var(--card2);border-radius:999px;overflow:hidden;border:1px solid var(--line);margin-top:10px}
.bar>div{height:100%;width:0;background:linear-gradient(90deg,var(--accent),var(--accent2));transition:width .15s}
#stage{font-size:13px;color:var(--muted);margin-top:8px;min-height:18px}
pre#log{background:#060910;border:1px solid var(--line);border-radius:10px;padding:10px;height:240px;overflow:auto;
  font:12px/1.4 ui-monospace,Menlo,Consolas,monospace;color:#bfe3ea;white-space:pre-wrap;word-break:break-word;margin:0}
.toast{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);background:var(--card2);border:1px solid var(--line);
  border-radius:10px;padding:11px 15px;font-size:13px;max-width:90%;box-shadow:0 8px 30px #0008;opacity:0;transition:opacity .2s;pointer-events:none}
.toast.show{opacity:1}
.toast.ok{border-color:var(--ok)} .toast.bad{border-color:var(--bad)}
.note{font-size:12px;color:var(--warn);background:#2a2411;border:1px solid #4a3f1a;border-radius:10px;padding:10px;margin-top:10px}
details summary{cursor:pointer;color:var(--muted);font-size:13px;padding:6px 0}
a.dl{display:inline-block;margin-top:8px;color:var(--accent);text-decoration:none;font-size:13px}
.hide{display:none}
hr{border:0;border-top:1px solid var(--line);margin:12px 0}
</style>
</head>
<body>
<div class="wrap">
  <h1><span>x3utils</span> · ESP32</h1>
  <div class="sub">Standalone ST-LINK-less flasher for AT32F415 X3 VCUs — controlled from this browser.</div>

  <div class="card">
    <div class="row" style="justify-content:space-between">
      <span class="pill"><span id="cdot" class="dot"></span><span id="cstate">idle</span></span>
      <span class="pill" id="tinfo">no target</span>
    </div>
    <label class="lbl">Connection mode</label>
    <div class="seg" id="modeSeg">
      <button data-mode="normal" class="on">Default SWD</button>
      <button data-mode="reset">Under-reset (nRST)</button>
      <button data-mode="race">Power-race</button>
    </div>
  </div>

  <div class="card hide" id="hwCard">
    <div class="row" style="justify-content:space-between">
      <strong style="font-size:14px">X3-Tuner</strong>
      <span class="pill"><span id="batTxt">battery —</span></span>
    </div>
    <div class="row" style="justify-content:space-between;margin-top:10px">
      <span class="pill"><span id="tdot" class="dot"></span><span id="vtgtTxt">VCU 3V3: —</span></span>
      <button class="act" id="tgtBtn" style="padding:9px 12px">VCU power ON</button>
    </div>
    <div class="sub" style="margin:8px 0 0">The tool can power the VCU itself (3.3 V, switched). It refuses when the VCU is already powered from another source. Power-race uses it automatically.</div>
  </div>

  <div class="card">
    <div class="grid">
      <button class="act" data-op="check">Check connection<small>read-only probe</small></button>
      <button class="act" data-op="dump">Backup 128 KB<small>full dump → download</small></button>
      <button class="act primary" data-op="flashFull">Backup + Flash<small>upload full .bin</small></button>
      <button class="act primary" data-op="flashSlot0">Flash slot 0<small>upload slot .bin</small></button>
      <button class="act" data-op="protectionCheck">Check protection<small>read-only FAP verdict</small></button>
      <button class="act danger" data-op="rescue">Unlock / Rescue<small>mass-erase, clears FAP</small></button>
    </div>
    <hr>
    <div class="row" style="justify-content:space-between">
      <strong style="font-size:14px">Make SHU compatible</strong>
      <select id="mcuModel" style="width:auto;min-width:120px"></select>
    </div>
    <div class="sub" style="margin:6px 0 0">Dumps, patches the chip's own firmware, flashes it back. Model is only needed for MCU firmware.</div>
    <button class="act" data-op="compat" style="width:100%;margin-top:10px">Run SHU compatible<small>factory firmware only — safety-gated</small></button>
    <input type="file" id="file" accept=".bin" class="hide">
    <a class="dl hide" id="dlBackup" href="/api/backup.bin">⬇ Download last backup (.bin)</a>
    <div class="note">⚠ This writes the VCU directly. Always keep a backup. Power the VCU from ONE source. Use 3.3 V logic only.</div>
  </div>

  <div class="card">
    <div class="row" style="justify-content:space-between">
      <strong style="font-size:14px">Console</strong>
      <button id="abort" class="act danger hide" style="padding:7px 12px">Abort</button>
    </div>
    <div class="bar"><div id="prog"></div></div>
    <div id="stage"></div>
    <pre id="log"></pre>
  </div>

  <div class="card">
    <details>
      <summary>Settings (WiFi · pins · SWD speed)</summary>
      <label class="lbl">WiFi mode</label>
      <div class="seg" id="wifiSeg">
        <button data-wifi="ap" class="on">Hotspot (AP)</button>
        <button data-wifi="sta">Join network</button>
      </div>
      <div id="apBox">
        <label class="lbl">Hotspot name</label><input type="text" id="apSsid">
        <label class="lbl">Hotspot password (≥8 chars, blank = open)</label><input type="text" id="apPass">
      </div>
      <div id="staBox" class="hide">
        <label class="lbl">Network SSID</label><input type="text" id="staSsid">
        <label class="lbl">Password</label><input type="password" id="staPass">
      </div>
      <div class="grid">
        <div><label class="lbl">SWCLK pin</label><input type="number" id="pinClk"></div>
        <div><label class="lbl">SWDIO pin</label><input type="number" id="pinDio"></div>
        <div><label class="lbl">nRST pin (-1 = none)</label><input type="number" id="pinRst"></div>
        <div><label class="lbl">SWD half-clock µs</label><input type="number" id="swdUs" min="0" max="20"></div>
      </div>
      <button class="act primary" id="saveCfg" style="width:100%;margin-top:12px">Save &amp; reboot</button>
      <div class="sub" style="margin-top:8px">After reboot, rejoin the hotspot (or your network) and open this page again.</div>
    </details>
  </div>
  <div class="sub" style="text-align:center">Derived from <b>x3utils</b> (MIT). The ESP32 is the programmer; no PC or ST-LINK needed.</div>
</div>
<div class="toast" id="toast"></div>

<script>
let mode="normal", busy=false, ws;
const $=s=>document.querySelector(s), logEl=$("#log");
function toast(msg,kind){const t=$("#toast");t.textContent=msg;t.className="toast show "+(kind||"");setTimeout(()=>t.className="toast",3200);}
function addLog(l){logEl.textContent+=l+"\n";logEl.scrollTop=logEl.scrollHeight;}
function setBusy(b){busy=b;document.querySelectorAll("button.act").forEach(x=>x.disabled=b);$("#abort").classList.toggle("hide",!b);
  $("#cdot").className="dot "+(b?"busy":"");$("#cstate").textContent=b?"working…":"idle";}

$("#modeSeg").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;
  mode=b.dataset.mode;$("#modeSeg").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x===b));});
$("#wifiSeg").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;
  const m=b.dataset.wifi;$("#wifiSeg").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x===b));
  $("#apBox").classList.toggle("hide",m!=="ap");$("#staBox").classList.toggle("hide",m!=="sta");});

document.querySelectorAll("button.act[data-op]").forEach(btn=>btn.addEventListener("click",()=>{
  const op=btn.dataset.op;
  if(op==="flashFull"||op==="flashSlot0"){pickAndFlash(op);return;}
  startOp(op);
}));

function startOp(kind){
  if(busy)return;
  logEl.textContent="";$("#prog").style.width="0";$("#stage").textContent="";
  setBusy(true);
  fetch("/api/op",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({kind,mode,mcuModel:$("#mcuModel").value})})
    .then(r=>r.json()).then(j=>{if(!j.ok){setBusy(false);toast(j.why||"rejected","bad");}})
    .catch(e=>{setBusy(false);toast("request failed","bad");});
}

function pickAndFlash(kind){
  const f=$("#file");f.value="";
  f.onchange=()=>{const file=f.files[0];if(!file)return;
    const rd=new FileReader();
    rd.onload=()=>{
      logEl.textContent="";$("#prog").style.width="0";$("#stage").textContent="Uploading "+file.name+"…";setBusy(true);
      fetch("/api/upload",{method:"POST",headers:{"Content-Type":"application/octet-stream"},body:rd.result})
        .then(r=>r.json()).then(j=>{
          if(!j.ok){setBusy(false);toast(j.why||"upload failed","bad");return;}
          addLog("[upload] "+j.len+" bytes received");
          return fetch("/api/op",{method:"POST",headers:{"Content-Type":"application/json"},
            body:JSON.stringify({kind,mode})}).then(r=>r.json()).then(k=>{
              if(!k.ok){setBusy(false);toast(k.why||"rejected","bad");}});
        }).catch(()=>{setBusy(false);toast("upload failed","bad");});
    };
    rd.readAsArrayBuffer(file);
  };
  f.click();
}

$("#abort").addEventListener("click",()=>fetch("/api/abort",{method:"POST"}));

function onEvent(e){
  if(e.type==="log")addLog(e.text);
  else if(e.type==="stage"){$("#stage").textContent=e.text;addLog("» "+e.text);}
  else if(e.type==="progress"){const p=e.total?Math.round(e.done*100/e.total):0;$("#prog").style.width=p+"%";
    $("#stage").textContent=(e.phase||"")+" "+p+"%";}
  else if(e.type==="done"){setBusy(false);$("#prog").style.width=e.ok?"100%":$("#prog").style.width;
    addLog((e.ok?"✓ ":"✗ ")+e.text);toast(e.text,e.ok?"ok":"bad");refreshStatus();}
}

function connectWS(){
  ws=new WebSocket("ws://"+location.host+"/ws");
  ws.onmessage=m=>{try{onEvent(JSON.parse(m.data));}catch(_){}};
  ws.onclose=()=>setTimeout(connectWS,1500);
}

let tgtOn=false;
function refreshStatus(){
  fetch("/api/status").then(r=>r.json()).then(j=>{
    $("#tinfo").textContent=j.target||"no target";
    $("#dlBackup").classList.toggle("hide",!j.haveBackup);
    if(j.target&&j.target!=="no target"&&!busy){$("#cdot").className="dot ok";}
    const hw=j.hasTgtPower||j.vbat!==undefined;
    $("#hwCard").classList.toggle("hide",!hw);
    if(!hw)return;
    $("#batTxt").textContent=(j.vbat!==undefined?("battery "+j.bat+"% · "+(j.vbat/1000).toFixed(2)+" V"):"battery —")+(j.usb?" · USB ⚡":"");
    tgtOn=!!j.tgtPower;
    const v=j.vtgt!==undefined?(j.vtgt/1000).toFixed(2)+" V":"—";
    $("#vtgtTxt").textContent="VCU 3V3: "+v+(tgtOn?" (from tool)":(j.vtgt>1000?" (external)":""));
    $("#tdot").className="dot "+(j.vtgt>1000?"ok":"");
    $("#tgtBtn").textContent=tgtOn?"VCU power OFF":"VCU power ON";
    $("#tgtBtn").classList.toggle("danger",tgtOn);
  }).catch(()=>{});
}
$("#tgtBtn").addEventListener("click",()=>{
  fetch("/api/target",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({on:!tgtOn})})
    .then(r=>r.json()).then(j=>{if(!j.ok)toast(j.why||"refused","bad");refreshStatus();})
    .catch(()=>toast("request failed","bad"));
});
setInterval(()=>{if(!document.hidden)refreshStatus();},3000);

function loadSettings(){
  fetch("/api/settings").then(r=>r.json()).then(j=>{
    $("#apSsid").value=j.apSsid||"";$("#apPass").value=j.apPass||"";
    $("#staSsid").value=j.staSsid||"";$("#staPass").value=j.staPass||"";
    $("#pinClk").value=j.pinClk;$("#pinDio").value=j.pinDio;$("#pinRst").value=j.pinRst;$("#swdUs").value=j.swdUs;
    const m=j.wifi||"ap";$("#wifiSeg").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x.dataset.wifi===m));
    $("#apBox").classList.toggle("hide",m!=="ap");$("#staBox").classList.toggle("hide",m!=="sta");
    (j.mcuModels||[]).forEach(mo=>{const o=document.createElement("option");o.value=mo;o.textContent=mo.toUpperCase();$("#mcuModel").appendChild(o);});
  }).catch(()=>{});
}

$("#saveCfg").addEventListener("click",()=>{
  const wifi=$("#wifiSeg").querySelector("button.on").dataset.wifi;
  const body={wifi,apSsid:$("#apSsid").value,apPass:$("#apPass").value,staSsid:$("#staSsid").value,staPass:$("#staPass").value,
    pinClk:+$("#pinClk").value,pinDio:+$("#pinDio").value,pinRst:+$("#pinRst").value,swdUs:+$("#swdUs").value};
  fetch("/api/settings",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
    .then(r=>r.json()).then(j=>{toast(j.ok?"Saved — rebooting…":"save failed",j.ok?"ok":"bad");});
});

connectWS();loadSettings();refreshStatus();
</script>
</body></html>)HTML";
