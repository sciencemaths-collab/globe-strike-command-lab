#!/usr/bin/env python3
"""
Globe Strike Command Lab v4

Upgrades:
- location aware geocoding for countries, cities, towns, regions, and raw lat/lon
- right-side interceptor control panel
- realistic time toggle (actual-ish flight time instead of compressed playback)
- predictive intercept planning using the attacker's forecast trajectory
- visible defense guidance line from interceptor launch site to incoming projectile
- clearer HUD with geo / spatial / timing data
"""

import html
import http.server
import json
import os
import re
import socket
import threading
import time
import urllib.parse
import urllib.request
import webbrowser

try:
    import pycountry
except ImportError:
    pycountry = None

try:
    from countryinfo import CountryInfo
except ImportError:
    CountryInfo = None

HTML_TEMPLATE = r'''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Globe Strike Command Lab v4</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:#020711;color:#9fb3c8;font-family:ui-monospace,Menlo,Consolas,monospace}
    .wrap{max-width:1880px;margin:0 auto;padding:12px}
    h1{text-align:center;font-size:30px;font-weight:900;background:linear-gradient(135deg,#ff6a00,#ffd248);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
    .sub{text-align:center;font-size:10px;color:#3d5169;letter-spacing:3px;margin:4px 0 14px}
    .row{display:grid;grid-template-columns:340px minmax(680px,1fr) 340px;gap:12px;align-items:start}
    .stack{display:flex;flex-direction:column;gap:10px}
    .pnl{background:rgba(5,12,24,.94);border:1px solid #1c2f46;border-radius:16px;padding:14px;box-shadow:0 18px 36px rgba(0,0,0,.22)}
    .pnl h3{font-size:10px;color:#ff9852;letter-spacing:2px;margin-bottom:8px}
    label{font-size:10px;color:#61748a;display:block;margin-bottom:4px}
    label span{color:#ffd68a;font-weight:700}
    input[type=text], select{width:100%;background:#08111d;border:1px solid #21344a;border-radius:9px;color:#c9dbef;padding:9px 10px;font-size:12px;font-family:inherit;outline:none}
    input[type=text]:focus, select:focus{border-color:#5f86b3}
    input[type=range]{width:100%;accent-color:#ff914d}
    input[type=checkbox]{accent-color:#ff914d}
    .chkrow{display:flex;align-items:flex-start;gap:8px;margin-top:8px;font-size:10px;color:#6a7e96}
    .hint{font-size:9px;color:#405266;line-height:1.35;margin-top:4px}
    .modes{display:grid;grid-template-columns:1fr 1fr;gap:6px}
    .modes button,.smallbtn,.btn,.btn-cam{font-family:inherit}
    .modes button{padding:8px 0;font-size:10px;font-weight:800;border-radius:8px;border:1px solid #203149;background:#0c1524;color:#66788f;cursor:pointer;text-transform:uppercase;transition:.15s}
    .modes button.active.m-ballistic{color:#ff6f3b;background:#ff6f3b16;border-color:#ff6f3b5c}
    .modes button.active.m-guided{color:#ff4ec8;background:#ff4ec816;border-color:#ff4ec85c}
    .modes button.active.m-cruise{color:#40d6ff;background:#40d6ff16;border-color:#40d6ff5c}
    .modes button.active.m-evasive{color:#67ff7a;background:#67ff7a16;border-color:#67ff7a5c}
    .grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .btns{display:flex;gap:6px}
    .btn{padding:11px 12px;font-size:12px;font-weight:900;border-radius:10px;border:none;cursor:pointer;transition:.15s;flex:1;text-align:center}
    .btn:hover,.smallbtn:hover,.btn-cam:hover{filter:brightness(1.12);transform:translateY(-1px)}
    .btn-fire{background:linear-gradient(135deg,#ff5f00,#ffcc44);color:#160b00}
    .btn-clear{background:#1b2a3d;color:#d5e2ef}
    .btn-random{background:#0f1a2a;color:#c6d6e7}
    .smallbtn{padding:8px 10px;font-size:10px;font-weight:800;border-radius:9px;border:1px solid #22344c;background:#0c1625;color:#93abc5;cursor:pointer}
    .smallbtn.active{background:#10304a;border-color:#7fc6ff55;color:#e8f7ff}
    .statgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
    .stat{background:#08111d;border:1px solid #1b2e44;border-radius:12px;padding:10px;text-align:center}
    .stat .num{font-size:22px;font-weight:900;color:#ff9955}
    .stat .lbl{font-size:8px;color:#516274;letter-spacing:2px}
    .cnv-wrap{position:relative;border-radius:14px;overflow:hidden;background:#00040a;min-height:720px;box-shadow:inset 0 0 0 1px rgba(112,146,188,.08)}
    #globe{display:block;width:100%;height:720px}
    #hud{position:absolute;left:12px;top:12px;background:rgba(0,0,0,.72);border:1px solid rgba(112,146,188,.16);border-radius:11px;padding:10px 14px;font-size:11px;line-height:1.7;color:#d5e4f1;max-width:390px;backdrop-filter:blur(2px)}
    #hud .status{font-size:12px;font-weight:900;margin-bottom:4px}
    #hud .val{color:#ffd48a}
    #hud .warn{color:#ff8e7d}
    #hud .ok{color:#86ffbb}
    .view-tip{position:absolute;left:12px;bottom:12px;max-width:360px;background:rgba(0,0,0,.58);border:1px solid rgba(112,146,188,.14);border-radius:10px;padding:8px 10px;font-size:10px;color:#8db0d4;backdrop-filter:blur(2px)}
    .view-tip b{color:#e6f4ff}
    .canvas-tools{position:absolute;right:12px;bottom:12px;display:flex;flex-direction:column;gap:8px;align-items:flex-end;z-index:9}
    .tool-row{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
    .btn-cam{padding:8px 10px;border-radius:10px;border:1px solid #203149;background:#0c1524;color:#8fb0cf;cursor:pointer;font-weight:800;font-size:10px;transition:.15s}
    .btn-cam.active{background:#10304a;border-color:#82caff55;color:#edf8ff}
    .cam-pad{display:grid;grid-template-columns:repeat(3,36px);grid-template-rows:repeat(2,36px);gap:4px;background:rgba(4,10,18,.66);padding:6px;border:1px solid rgba(90,132,180,.16);border-radius:12px}
    .cam-pad .btn-cam{padding:0;min-width:36px;height:36px;line-height:36px;font-size:14px}
    .sug-box{position:absolute;top:100%;left:0;right:0;background:#08111d;border:1px solid #22344c;border-radius:0 0 10px 10px;z-index:20;max-height:220px;overflow:auto;box-shadow:0 14px 28px rgba(0,0,0,.34)}
    .sug-box div{padding:7px 10px;cursor:pointer;color:#b0d0ef;font-size:11px;border-top:1px solid rgba(34,52,76,.32)}
    .sug-box div:first-child{border-top:none}
    .sug-box div:hover,.sug-box div.active{background:#1a2e45;color:#f0f8ff}
    .sug-box small{display:block;color:#5f7894;font-size:9px;margin-top:2px}
    .preview-note{margin-top:8px;padding:8px 10px;border:1px solid #17324f;border-radius:10px;background:rgba(8,18,28,.7);font-size:10px;color:#87a9cb;line-height:1.45}
    .preview-note b{color:#e6f4ff}
    #log{max-height:220px;overflow-y:auto;font-size:10px}
    #log div{padding:3px 0;border-bottom:1px solid #0c1520}
    .fire-entry{color:#ff9a57}.warn-entry{color:#d8a05b}.info-entry{color:#6e95bf}.good-entry{color:#89f0b3}.bad-entry{color:#ff8e88}
    .tag{display:inline-block;padding:2px 7px;border-radius:999px;border:1px solid #22344c;background:#0c1625;color:#a7c4df;font-size:9px;margin-right:4px;margin-top:4px}
    .mini{font-size:9px;color:#5e7288}
    .chart-wrap{background:#07101a;border:1px solid #1b2e44;border-radius:12px;padding:10px}
    #engagementChart{width:100%;height:180px;display:block;background:linear-gradient(180deg,rgba(8,17,29,.35),rgba(2,8,14,.75));border-radius:10px}
    .kpi-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:8px}
    .kpi{background:#08111d;border:1px solid #1b2e44;border-radius:10px;padding:8px;text-align:center}
    .kpi .v{font-size:16px;font-weight:900;color:#e6f4ff}
    .kpi .t{font-size:8px;color:#607286;letter-spacing:1.6px}
    @media (max-width: 1400px){
      .row{grid-template-columns:320px minmax(620px,1fr) 320px}
      .cnv-wrap{min-height:660px}#globe{height:660px}
    }
    @media (max-width: 1120px){
      .row{grid-template-columns:1fr}
      .cnv-wrap{min-height:480px}#globe{height:480px}
    }
  </style>
</head>
<body>
<div class="wrap">
  <h1>GLOBE STRIKE COMMAND LAB</h1>
  <div class="sub">WGS-84 • J2 GRAVITY • US STD ATMO 1976 • MACH-CD DRAG • TRUE PN • SEEKER LOGIC • RAID ALLOCATOR • V10</div>
  <div class="row">
    <div class="stack">
      <div class="pnl">
        <h3>ATTACK PANEL · SIDE A</h3>
        <label>LAUNCH FROM</label>
        <div style="position:relative">
          <input type="text" id="fromC" value="Washington, D.C." autocomplete="off" list="placePool" placeholder="Country, state, city, region, or lat,lon">
          <div class="sug-box" id="fromSug"></div>
        </div>
        <label style="margin-top:6px">TARGET</label>
        <div style="position:relative">
          <input type="text" id="toC" value="Moscow" autocomplete="off" list="placePool" placeholder="Country, state, city, region, or lat,lon">
          <div class="sug-box" id="toSug"></div>
        </div>
        <div class="hint">You can type <span style="color:#8ed6ff">Coram, New York</span>, <span style="color:#8ed6ff">Accra</span>, <span style="color:#8ed6ff">Texas</span>, <span style="color:#8ed6ff">Ghana</span>, or raw coordinates like <span style="color:#8ed6ff">40.8687,-72.9996</span>.</div>
        <div style="margin-top:6px"><label>WEAPON SYSTEM <span id="weaponCountry" style="color:#ffd68a"></span></label>
        <select id="weaponSelect" style="width:100%;background:#08111d;border:1px solid #21344a;border-radius:9px;color:#c9dbef;padding:8px 10px;font-size:11px;font-family:inherit;outline:none"><option value="">— Custom (sliders) —</option></select>
        <div id="weaponDesc" class="hint" style="margin-top:4px;color:#6eb5ff"></div>
        <div id="weaponSpecs" style="margin-top:3px;font-size:9px;color:#8da5bb"></div></div>
      <div id="attackResolved" class="preview-note"><b>GEO RESOLUTION</b><br>Waiting for attack-side place resolution.</div>
      </div>

      <div class="pnl">
        <h3>OFFENSIVE FLIGHT MODEL</h3>
        <div class="modes">
          <button class="active m-ballistic" data-mode="ballistic">Ballistic</button>
          <button data-mode="guided">Guided</button>
          <button data-mode="cruise">Cruise</button>
          <button data-mode="evasive">Evasive</button>
        </div>
        <div id="modeDesc" style="font-size:9px;color:#53667b;margin-top:6px;line-height:1.5">Range-matched ballistic loft with gravity and atmosphere shaping.</div>
        <div class="chkrow"><input type="checkbox" id="speedHold" checked><div>Maintain commanded Mach<div class="hint">Uses bounded propulsion and local speed of sound, not instant velocity jumps.</div></div></div>
        <div class="chkrow"><input type="checkbox" id="realisticMode"><div>Realistic mode<div class="hint">Uses near-real flight duration instead of cinematic time compression. Good for reviewers checking timing logic.</div></div></div>
      </div>

      <div class="pnl">
        <label>ATTACK MACH <span id="machLabel">Mach 20.0</span> <span id="mphLabel" class="mini">(≈ 15,224 mph @ sea level)</span></label>
        <input type="range" id="machSlider" min="1" max="60" value="20" step="0.5">
        <label style="margin-top:6px">LOFT / ELEVATION <span id="angleLabel">35°</span></label>
        <input type="range" id="angleSlider" min="1" max="85" value="35">
        <label style="margin-top:6px">EVASIVENESS <span id="evasionLabel">0.50</span></label>
        <input type="range" id="evasionSlider" min="0.00" max="1.00" value="0.50" step="0.05">
        <div class="preview-note" id="previewNote"><b>LIVE PREVIEW</b><br>Drag Mach, elevation, or evasiveness to refresh the ghost path, peak altitude, ETA, and predicted defense window before launch.</div>
      </div>

      <div class="btns">
        <button class="btn btn-fire" id="btnFire">FIRE ATTACK</button>
        <button class="btn btn-random" id="btnRandom">RANDOM</button>
      </div>
      <div class="btns"><button class="btn btn-clear" id="btnClear">CLEAR ALL</button></div>

      <div class="pnl">
        <div class="statgrid">
          <div class="stat"><div class="num" id="shotCount">0</div><div class="lbl">ATTACKS</div></div>
          <div class="stat"><div class="num" id="killCount">0</div><div class="lbl">INTERCEPTS</div></div>
          <div class="stat"><div class="num" id="activeThreatCount">0</div><div class="lbl">ACTIVE THREATS</div></div>
          <div class="stat"><div class="num" id="activeDefenseCount">0</div><div class="lbl">ACTIVE DEFENSE</div></div>
        </div>
      </div>
    </div>

    <div class="stack">
      <div class="pnl" style="padding:8px">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:0 8px 6px;flex-wrap:wrap">
          <h3 style="margin:0">WORLD VIEW</h3>
          <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end">
            <button class="smallbtn active" id="btnRotate" type="button">AUTO SPIN: ON</button>
            <button class="smallbtn active" id="btnFollow" type="button">FOLLOW ACTIVE: ON</button>
            <button class="smallbtn" id="btnCenterThreat" type="button">CENTER THREAT</button>
            <button class="smallbtn" id="btnCenterDefense" type="button">CENTER DEFENSE</button>
          </div>
        </div>
        <div class="cnv-wrap">
          <canvas id="globe"></canvas>
          <div id="hud"><div class="status" style="color:#7d8ea4">READY</div>Resolve locations and launch.</div>
          <div class="view-tip"><b>VIEW</b><br>Drag to orbit. Scroll to zoom. In realistic mode the missile and interceptor run in near-real time, so the camera follow is gentler and the timing becomes physically legible.</div>
          <div class="canvas-tools">
            <div class="tool-row">
              <button class="btn-cam" id="camReset" type="button">RESET</button>
              <button class="btn-cam" id="camZoomIn" type="button">ZOOM +</button>
              <button class="btn-cam" id="camZoomOut" type="button">ZOOM −</button>
            </div>
            <div class="cam-pad">
              <div></div><button class="btn-cam" id="camUp" type="button">↑</button><div></div>
              <button class="btn-cam" id="camLeft" type="button">←</button><button class="btn-cam" id="camCenter" type="button">◎</button><button class="btn-cam" id="camRight" type="button">→</button>
              <div></div><button class="btn-cam" id="camDown" type="button">↓</button><div></div>
            </div>
          </div>
        </div>
      </div>

      <div class="pnl">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap">
          <div>
            <div style="font-size:8px;color:#354657;letter-spacing:2px">FLIGHT / DEFENSE LOG</div>
            <div class="mini">attack line = orange / pink / blue / green, defense line = cyan</div>
          </div>
          <div>
            <span class="tag">WGS-84</span><span class="tag">J2</span><span class="tag">ATMO-76</span><span class="tag">TPN</span>
          </div>
        </div>
        <div id="log">
          <div class="info-entry">Command Lab v4 online. WGS-84 + J2 + US Std Atmo 1976 + Mach-Cd + TPN. Attack and defense panels are decoupled so reviewers can test both sides independently.</div>
        </div>
      </div>
      <div class="pnl">
        <h3>ENGAGEMENT ANALYTICS</h3>
        <div class="chart-wrap">
          <canvas id="engagementChart" width="620" height="180"></canvas>
        </div>
        <div class="kpi-grid">
          <div class="kpi"><div class="v" id="attackSuccessRate">0%</div><div class="t">ATTACK SUCCESS</div></div>
          <div class="kpi"><div class="v" id="interceptSuccessRate">0%</div><div class="t">INTERCEPT SUCCESS</div></div>
          <div class="kpi"><div class="v" id="avgPkLive">0%</div><div class="t">LIVE P(HIT)</div></div>
        </div>
        <div class="preview-note" id="engagementSummary"><b>ENGAGEMENT MEMORY</b><br>Resolved outcomes stay here until you press <span style="color:#ffd48a">CLEAR ALL</span>. The bars separate leakage from successful defense while the live probability reflects current kinematics, sensor quality, and target evasiveness.</div>
      </div>
    </div>

    <div class="stack">
      <div class="pnl">
        <h3>INTERCEPT PANEL · SIDE B</h3>
        <label>DEFENSE SITE</label>
        <div style="position:relative">
          <input type="text" id="interceptFrom" value="Moscow" autocomplete="off" list="placePool" placeholder="City, state, country, or lat,lon">
          <div class="sug-box" id="interceptSug"></div>
        </div>
        <div class="grid2" style="margin-top:8px">
          <div>
            <label>LAUNCH POLICY</label>
            <select id="interceptPolicy">
              <option value="auto-target">Auto from target city</option>
              <option value="manual">Manual defense site</option>
              <option value="off">Defense off</option>
            </select>
          </div>
          <div>
            <label>REACTION DELAY <span id="delayLabel">45 s</span></label>
            <input type="range" id="delaySlider" min="0" max="600" value="45" step="5">
          </div>
        </div>
        <div id="defenseResolved" class="preview-note"><b>DEFENSE RESOLUTION</b><br>Waiting for defense-side place resolution.</div>
      </div>

      <div class="pnl">
        <div class="grid2" style="margin-bottom:8px">
          <div>
            <label>BATTERIES <span id="batteryCountLabel">1</span></label>
            <input type="range" id="batteryCountSlider" min="1" max="6" value="1" step="1">
          </div>
          <div>
            <label>SALVO SPACING <span id="salvoSpacingLabel">8 s</span></label>
            <input type="range" id="salvoSpacingSlider" min="0" max="60" value="8" step="1">
          </div>
        </div>
        <label>INTERCEPTOR MACH <span id="defMachLabel">Mach 12.0</span></label>
        <input type="range" id="defMachSlider" min="1" max="35" value="12" step="0.5">
        <label style="margin-top:6px">INTERCEPT ALTITUDE BIAS <span id="defAltLabel">35 mi</span></label>
        <input type="range" id="defAltSlider" min="5" max="120" value="35" step="1">
        <label style="margin-top:6px">GUIDANCE AGGRESSION <span id="aggrLabel">0.70</span></label>
        <input type="range" id="aggrSlider" min="0.1" max="1.0" value="0.7" step="0.05">
        <div class="chkrow"><input type="checkbox" id="allowRetarget" checked><div>Retarget during flight<div class="hint">Interceptor keeps recomputing the aim point if the attacker weaves or the original intercept point becomes stale.</div></div></div>
      </div>

      <div class="pnl">
        <h3>DEFENSE SUMMARY</h3>
        <div id="interceptSummary" class="preview-note"><b>PREDICTIVE WINDOW</b><br>No attack preview yet, so no intercept solution has been plotted.</div>
        <div id="defenseActivation" style="margin-top:8px;display:none"><label>NATIONAL AIR DEFENSE <span id="defCountryName" style="color:#86ffbb"></span></label>
        <button id="btnActivateDefense" class="btn btn-fire" style="width:100%;margin-top:4px;background:linear-gradient(135deg,#0078ff,#00d4ff);font-size:11px;padding:9px" type="button">AIR DEFENSE STANDBY / BOOST</button>
        <div id="defLayers" style="margin-top:5px;font-size:9px;color:#8db0d4;line-height:1.5"></div></div>
      <div class="hint">A valid defense plan needs both spatial reach and temporal reach: the interceptor must be able to get to the same 3D neighborhood before the incoming shot gets there.</div>
      </div>

      <div class="pnl"><h3>PHYSICS TELEMETRY</h3><div class="preview-note" style="font-size:9px"><b>REAL-TIME</b><br><span id="ptDrag">Cd — · Drag —</span><br><span id="ptGrav">g — m/s² · J2 Δg —</span><br><span id="ptAtmo">ρ — · T — K · a — m/s</span><br><span id="ptHeat">q̇ — W/cm²</span></div></div>
      <div class="btns">
        <button class="btn btn-random" id="btnMirrorDefense">COPY TARGET → DEFENSE</button>
      </div>
    </div>
  </div>
</div>
<datalist id="placePool">__DATALIST_OPTIONS__</datalist>

<script>
// V45 SUPER PRELUDE
window.NODE_BIND = window.NODE_BIND || {};
window.SIM32 = window.SIM32 || {active:false, mode:'duel', sides:{A:[],B:[]}, allyLedger:{A:[],B:[]}, history:[]};
window.AI33 = window.AI33 || {enabled:false,busy:false,lastCall:0,cadenceMs:12000,plan:null,cfg:null};
var NODE_BIND = window.NODE_BIND;
var SIM32 = window.SIM32;
var AI33 = window.AI33;
var resolveSeedPlaceFast = window.resolveSeedPlaceFast || function(){ return null; };
var loop = window.loop || function(){};
var drawGlobe = window.drawGlobe || function(){};
var drawAllShots = window.drawAllShots || function(){};
var updateHud = window.updateHud || function(){};
var updateEngagementPanel = window.updateEngagementPanel || function(){};
var updateFinalPanel = window.updateFinalPanel || function(){};
var updateV31Panel = window.updateV31Panel || function(){};
var drawAttackLine = window.drawAttackLine || function(){};
var drawProjectileTrace = window.drawProjectileTrace || function(){};
var threatPriorityScore = window.threatPriorityScore || function(){ return 0; };
var computeSeekerState = window.computeSeekerState || function(){ return {}; };
var registerAttackOutcome = window.registerAttackOutcome || function(){};
var registerInterceptorOutcome = window.registerInterceptorOutcome || function(){};
var fireProjectile = window.fireProjectile || function(){ return null; };
var configurePayloadForAttack = window.configurePayloadForAttack || function(){};
var spawnPayloadChildren = window.spawnPayloadChildren || function(){ return []; };
var activateNationalDefense = window.activateNationalDefense || function(){};
var resetCampaignState = window.resetCampaignState || function(){};
var getCountryState = window.getCountryState || function(){ return {}; };
var defenseNodeScore = window.defenseNodeScore || function(){ return 0; };
var autoDefenseSweep = window.autoDefenseSweep || function(){};
var domainProfile = window.domainProfile || function(){ return {}; };
var launchProjectedAttack = window.launchProjectedAttack || function(){ return null; };
var currentDomainBalance = window.currentDomainBalance || function(){ return {}; };
var drawMultiDomainOverlay = window.drawMultiDomainOverlay || function(){};
var updateDomainMetrics = window.updateDomainMetrics || function(){};
var drawCampaignTheaterOverlay = window.drawCampaignTheaterOverlay || function(){};
var chooseDefenseNodeForThreat = window.chooseDefenseNodeForThreat || function(){ return null; };
var chooseCounterstrikeOrigin = window.chooseCounterstrikeOrigin || function(country, enemyCountry, incomingAttack){ return null; };
var chooseCounterstrikeTarget = window.chooseCounterstrikeTarget || function(country, enemyCountry){ return null; };
var scheduleCounterstrike = window.scheduleCounterstrike || function(){};
var sim32UpdateRoom = window.sim32UpdateRoom || function(){};
var sim32Tick = window.sim32Tick || function(){};
var sim32TryJoin = window.sim32TryJoin || function(){ return null; };
var getCityDefenseNodes = window.getCityDefenseNodes || function(country, fallbackPlace){
  var out=[];
  if (fallbackPlace && fallbackPlace.lat != null) out.push({name:(fallbackPlace.name||country||'Sector'), lat:+fallbackPlace.lat, lon:+fallbackPlace.lon, kind:'manual site', provider:'runtime', weight:0.9});
  return out;
};
var getCityDefenseNode = window.getCityDefenseNode || function(country, fallbackPlace, threat){
  var nodes = getCityDefenseNodes(country, fallbackPlace) || [];
  return nodes.length ? nodes[0] : (fallbackPlace || (resolveSeedPlaceFast ? resolveSeedPlaceFast(country) : null));
};
window.NODE_BIND = NODE_BIND;
window.SIM32 = SIM32;
window.AI33 = AI33;
window.resolveSeedPlaceFast = resolveSeedPlaceFast;
window.loop = loop;
window.drawGlobe = drawGlobe;
window.drawAllShots = drawAllShots;
window.updateHud = updateHud;
window.updateEngagementPanel = updateEngagementPanel;
window.updateFinalPanel = updateFinalPanel;
window.updateV31Panel = updateV31Panel;
window.drawAttackLine = drawAttackLine;
window.drawProjectileTrace = drawProjectileTrace;
window.threatPriorityScore = threatPriorityScore;
window.computeSeekerState = computeSeekerState;
window.registerAttackOutcome = registerAttackOutcome;
window.registerInterceptorOutcome = registerInterceptorOutcome;
window.fireProjectile = fireProjectile;
window.configurePayloadForAttack = configurePayloadForAttack;
window.spawnPayloadChildren = spawnPayloadChildren;
window.activateNationalDefense = activateNationalDefense;
window.resetCampaignState = resetCampaignState;
window.getCountryState = getCountryState;
window.defenseNodeScore = defenseNodeScore;
window.autoDefenseSweep = autoDefenseSweep;
window.domainProfile = domainProfile;
window.launchProjectedAttack = launchProjectedAttack;
window.currentDomainBalance = currentDomainBalance;
window.drawMultiDomainOverlay = drawMultiDomainOverlay;
window.updateDomainMetrics = updateDomainMetrics;
window.drawCampaignTheaterOverlay = drawCampaignTheaterOverlay;
window.chooseDefenseNodeForThreat = chooseDefenseNodeForThreat;
window.chooseCounterstrikeOrigin = chooseCounterstrikeOrigin;
window.chooseCounterstrikeTarget = chooseCounterstrikeTarget;
window.scheduleCounterstrike = scheduleCounterstrike;
window.sim32UpdateRoom = sim32UpdateRoom;
window.sim32Tick = sim32Tick;
window.sim32TryJoin = sim32TryJoin;
window.getCityDefenseNodes = getCityDefenseNodes;
window.getCityDefenseNode = getCityDefenseNode;
window.addEventListener('error', function(ev){ try{ console.warn('V45 caught error', ev && ev.message); }catch(_e){} });
</script>
<script>
// V44 EARLY STABILITY PRELUDE
var NODE_BIND = window.NODE_BIND || (window.NODE_BIND = {});
var SIM32 = window.SIM32 || (window.SIM32 = {active:false, mode:'duel', sides:{A:[],B:[]}, allyLedger:{A:[],B:[]}, history:[]});
var AI33 = window.AI33 || (window.AI33 = {enabled:false,busy:false,lastCall:0,cadenceMs:12000,plan:null,cfg:null});
function getCityDefenseNodes(country, fallbackPlace){
  if (window.getCityDefenseNodes && window.getCityDefenseNodes !== getCityDefenseNodes) return window.getCityDefenseNodes(country, fallbackPlace);
  var out=[];
  if (fallbackPlace && fallbackPlace.lat != null) out.push({name:(fallbackPlace.name||country||'Sector'), lat:+fallbackPlace.lat, lon:+fallbackPlace.lon, kind:'manual site', provider:'runtime', weight:0.9});
  return out;
}
function getCityDefenseNode(country, fallbackPlace, threat){
  var nodes = getCityDefenseNodes(country, fallbackPlace) || [];
  return nodes.length ? nodes[0] : (fallbackPlace || (window.resolveSeedPlaceFast ? window.resolveSeedPlaceFast(country) : null));
}
function chooseCounterstrikeOrigin(country, enemyCountry, incomingAttack){
  return getCityDefenseNode(country, window.resolveSeedPlaceFast ? window.resolveSeedPlaceFast(country) : null, incomingAttack);
}
function chooseCounterstrikeTarget(country, enemyCountry, incomingAttack){
  if (incomingAttack && incomingAttack.fromLL) return {lat:incomingAttack.fromLL[0], lon:incomingAttack.fromLL[1], name:enemyCountry||'Target'};
  return (window.resolveSeedPlaceFast ? window.resolveSeedPlaceFast(enemyCountry || country) : null) || {lat:0, lon:0, name:enemyCountry||country||'Target'};
}
function sim32TryJoin(side){ if (window.sim32TryJoin && window.sim32TryJoin !== sim32TryJoin) return window.sim32TryJoin(side); return null; }
window.NODE_BIND = NODE_BIND;
window.SIM32 = SIM32;
window.AI33 = AI33;
window.getCityDefenseNodes = window.getCityDefenseNodes || getCityDefenseNodes;
window.getCityDefenseNode = window.getCityDefenseNode || getCityDefenseNode;
window.chooseCounterstrikeOrigin = window.chooseCounterstrikeOrigin || chooseCounterstrikeOrigin;
window.chooseCounterstrikeTarget = window.chooseCounterstrikeTarget || chooseCounterstrikeTarget;
window.sim32TryJoin = window.sim32TryJoin || sim32TryJoin;
</script>
<script>
const PLACE_SEED = __PLACE_SEED_JSON__;
const RAD = Math.PI / 180;
const RE_M = 6371000.0;
const MU = 3.986004418e14;
const OMEGA_E = 7.2921159e-5;
const GAMMA = 1.4;
const R_AIR = 287.05287;
const MODE_COLORS = {ballistic:'#ff6f3b',guided:'#ff4ec8',cruise:'#40d6ff',evasive:'#67ff7a'};
const MODE_DESC = {
  ballistic:'Range-matched ballistic loft with gravity and atmosphere shaping.',
  guided:'Powered great-circle guidance with altitude loft and target convergence.',
  cruise:'Powered lower-altitude cruise-like path with strong speed hold.',
  evasive:'Guided flight with cross-track weave and retarget-friendly defense challenge.'
};

class V3 {
  constructor(x=0,y=0,z=0){this.x=x;this.y=y;this.z=z;}
  clone(){return new V3(this.x,this.y,this.z)}
  add(v){return new V3(this.x+v.x,this.y+v.y,this.z+v.z)}
  sub(v){return new V3(this.x-v.x,this.y-v.y,this.z-v.z)}
  scale(s){return new V3(this.x*s,this.y*s,this.z*s)}
  addSelf(v){this.x+=v.x;this.y+=v.y;this.z+=v.z;return this}
  scaleSelf(s){this.x*=s;this.y*=s;this.z*=s;return this}
  dot(v){return this.x*v.x+this.y*v.y+this.z*v.z}
  cross(v){return new V3(this.y*v.z-this.z*v.y, this.z*v.x-this.x*v.z, this.x*v.y-this.y*v.x)}
  len(){return Math.hypot(this.x,this.y,this.z)}
  norm(){const l=this.len()||1;return new V3(this.x/l,this.y/l,this.z/l)}
}
function clamp(x,a,b){return Math.max(a,Math.min(b,x))}
function lerp(a,b,t){return a+(b-a)*t}
function ll2v(lat,lon,r=1){
  const p=(90-lat)*RAD, t=(lon+180)*RAD;
  return new V3(-r*Math.sin(p)*Math.cos(t), r*Math.cos(p), r*Math.sin(p)*Math.sin(t));
}
function v2ll(v){
  const r=v.len()||1;
  const lat=90-Math.acos(clamp(v.y/r,-1,1))/RAD;
  let lon=-(Math.atan2(-v.z,-v.x)/RAD)-180;
  lon=((lon+540)%360)-180;
  return [lat,lon];
}
function slerpUnit(u,v,t){
  const dot=clamp(u.dot(v),-1,1);
  const th=Math.acos(dot);
  if(th<1e-8) return u.clone();
  const s=Math.sin(th);
  return u.scale(Math.sin((1-t)*th)/s).add(v.scale(Math.sin(t*th)/s));
}
function tangToward(curU,targetU){
  const n=curU.cross(targetU); const t=n.cross(curU); const L=t.len();
  return L>1e-10 ? t.scale(1/L) : new V3(0,0,0);
}
function gcDistMeters(a,b){
  const lat1=a[0]*RAD, lat2=b[0]*RAD, dlon=(b[1]-a[1])*RAD;
  const c=Math.acos(clamp(Math.sin(lat1)*Math.sin(lat2)+Math.cos(lat1)*Math.cos(lat2)*Math.cos(dlon),-1,1));
  return RE_M*c;
}
function gcDistMiles(a,b){ return gcDistMeters(a,b)*0.00062137119224; }

function offsetLatLon(lat, lon, bearingDeg, distKm){
  const br=bearingDeg*RAD, ad=(distKm*1000)/RE_M;
  const p1=lat*RAD, l1=lon*RAD;
  const sp2=Math.sin(p1)*Math.cos(ad)+Math.cos(p1)*Math.sin(ad)*Math.cos(br);
  const p2=Math.asin(clamp(sp2,-1,1));
  const y=Math.sin(br)*Math.sin(ad)*Math.cos(p1);
  const x=Math.cos(ad)-Math.sin(p1)*Math.sin(p2);
  let l2=l1+Math.atan2(y,x);
  l2=((l2+Math.PI*3)%(Math.PI*2))-Math.PI;
  return {lat:p2/RAD, lon:l2/RAD};
}
function inferCountryFromPlaceName(name){
  if(!name) return '';
  const raw=(''+name).trim();
  const lowered=raw.toLowerCase();
  const countries=(typeof ARSENAL_COUNTRIES!=='undefined' && ARSENAL_COUNTRIES && ARSENAL_COUNTRIES.length)?ARSENAL_COUNTRIES:Object.keys(ARSENAL||{});
  for(let i=0;i<countries.length;i++){
    const c=countries[i];
    if(lowered===c.toLowerCase()) return c;
  }
  const sorted=countries.slice().sort((a,b)=>b.length-a.length);
  for(let i=0;i<sorted.length;i++){
    const c=sorted[i], lc=c.toLowerCase();
    if(lowered.endsWith(', '+lc) || lowered.includes(', '+lc+',')) return c;
  }
  const ar=getArsenalForPlace ? getArsenalForPlace(raw) : null;
  return ar && ar.country ? ar.country : '';
}
function isaSpeedOfSound(alt){
  alt=Math.max(0,alt); let T;
  if(alt<11000) T=288.15-0.0065*alt;
  else if(alt<20000) T=216.65;
  else T=216.65;
  return Math.sqrt(GAMMA*R_AIR*T);
}
function airDensity(alt){ alt=Math.max(0,alt); if(alt>90000) return 0; return 1.225*Math.exp(-alt/8500.0); }
function bearingUnit(lat,lon,az){
  const up=ll2v(lat,lon,1).norm();
  const north=ll2v(Math.min(89.999,lat+0.1),lon,1).sub(up).norm();
  const east=ll2v(lat,lon+0.1,1).sub(up).norm();
  return north.scale(Math.cos(az)).add(east.scale(Math.sin(az))).norm();
}
function wrapPi(x){ while(x>Math.PI)x-=Math.PI*2; while(x<-Math.PI)x+=Math.PI*2; return x; }
function angleBetweenUnit(a,b){ return Math.acos(clamp(a.dot(b),-1,1)); }

function miles(m){ return m*0.00062137119224; }
function vecToLatLonAlt(pos){
  const r=pos.len()||RE_M;
  const u=pos.scale(1/r);
  const ll=v2ll(u);
  return {ll, alt:Math.max(0,r-RE_M)};
}

class Projectile {
  constructor(fromLL,toLL,cmdMach,elevDeg,mode,opts={}){
    this.kind=opts.kind||'attack';
    this.fromName=opts.fromName||''; this.toName=opts.toName||'';
    this.fromLL=[fromLL[0],fromLL[1]]; this.toLL=[toLL[0],toLL[1]];
    this.mode=mode; this.cmdMach=cmdMach; this.elevDeg=elevDeg;
    this.cruiseAltMi=opts.cruiseAltMi ?? 40; this.evasiveness=opts.evasiveness ?? 0.5;
    this.realistic=!!opts.realistic; this.speedHold = opts.speedHold !== false;
    this.fromU=ll2v(this.fromLL[0],this.fromLL[1],1).norm();
    this.toU=ll2v(this.toLL[0],this.toLL[1],1).norm();
    this.routeTheta=Math.max(1e-6, Math.acos(clamp(this.fromU.dot(this.toU),-1,1)));
    this.routeLen=RE_M*this.routeTheta;
    this.t=0; this.dt=0.05; this.progress=0; this.alive=true; this.destroyed=false; this.destroyReason='';
    this.impactPosU=null; this.impactAge=0; this.age=0; this.intercepted=false;
    const a0=isaSpeedOfSound(0); this.cmdAirspeed0=this.cmdMach*a0;
    this.alongSpeed=Math.max(260,this.cmdAirspeed0*0.88);
    this.elevFrac=Math.max(0, Math.sin(this.elevDeg*RAD));
    const vertGain=this.mode==='ballistic'?0.76:(this.mode==='cruise'?0.22:(this.mode==='evasive'?0.28:0.34));
    this.vertSpeed=Math.max(0,this.cmdAirspeed0*this.elevFrac*vertGain);
    this.alt=30.0;
    if(this.mode==='ballistic'){
      const timeAngle=lerp(0.96,1.34,this.elevFrac);
      const nominalAlong=Math.max(260,this.cmdAirspeed0*(0.84-0.18*this.elevFrac));
      this.ballisticTimeSec=clamp((this.routeLen/nominalAlong)*timeAngle,220,18000);
      this.ballisticClosureGain=lerp(0.45,0.88,this.elevFrac);
      this.alongSpeed=Math.max(this.routeLen/this.ballisticTimeSec*1.1, this.alongSpeed*(0.92-0.08*this.elevFrac));
    } else { this.ballisticTimeSec=0; this.ballisticClosureGain=0; }
    const estFlight=this.routeLen/Math.max(250,this.cmdAirspeed0*0.90);
    const desiredWatch= this.realistic ? estFlight : clamp(4.5 + gcDistMiles(this.fromLL,this.toLL)/2600,4.5,9.5);
    const simSecPerRealSec = this.realistic ? 1 : clamp(estFlight/desiredWatch,10,900);
    this.stepsPerFrame=clamp(Math.round(simSecPerRealSec/(60*this.dt)),1,180);
    this.trail=[]; this.maxTrail=1200; this._trailSkip=0; this.trailEvery=3; this.prevPos=this.rEcef(); this.currVel=new V3(0,0,0); this._pushTrail();
  }
  cloneForForecast(){
    return new Projectile(this.fromLL,this.toLL,this.cmdMach,this.elevDeg,this.mode,{cruiseAltMi:this.cruiseAltMi,evasiveness:this.evasiveness,realistic:this.realistic,speedHold:this.speedHold,kind:this.kind});
  }
  gravityAtAlt(alt){ return MU/Math.pow(RE_M+Math.max(0,alt),2); }
  currentCenterU(){ return slerpUnit(this.fromU,this.toU,clamp(this.progress,0,1)); }
  currentU(){ return this.currentPathU(); }
  currentTangentU(){ return tangToward(this.currentCenterU(), this.toU); }
  currentSideU(){ const c=this.currentCenterU(), t=this.currentTangentU(); const s=t.cross(c); return s.len()>1e-9 ? s.norm() : new V3(0,0,0); }
  lateralOffsetAngle(){
    if(this.mode!=='evasive') return 0;
    const frac=clamp(this.progress,0,1), cycles=clamp(2+this.routeLen/2500000,2,7), maxOffsetM=lerp(12000,85000,clamp(this.evasiveness,0,1));
    const window=Math.sin(Math.PI*frac);
    return (maxOffsetM/RE_M)*window*Math.sin(frac*cycles*Math.PI*2+this.t*(0.35+0.8*this.evasiveness));
  }
  currentPathU(){
    const c=this.currentCenterU(), s=this.currentSideU(), off=this.lateralOffsetAngle();
    if(Math.abs(off)<1e-9 || s.len()<1e-9) return c;
    return c.add(s.scale(off)).norm();
  }
  rEcef(){ return this.currentPathU().scale(RE_M+Math.max(0,this.alt)); }
  distToTargetMeters(){ return Math.max(0,(1-clamp(this.progress,0,1))*this.routeLen); }
  cmdAltMeters(frac){
    frac=clamp(frac,0,1); const arch=Math.sin(Math.PI*frac);
    if(this.mode==='cruise') return clamp(this.cruiseAltMi*1609.344,300,38000);
    const elevFrac=Math.pow(Math.max(0,Math.sin(this.elevDeg*RAD)),1.10);
    if(this.mode==='guided'){
      const base=6000+0.010*this.routeLen+this.cmdMach*700, angleBoost=lerp(2000,85000,elevFrac), peak=clamp(base+angleBoost,14000,210000);
      return peak*Math.pow(arch,1.08);
    }
    if(this.mode==='evasive'){
      const base=5000+0.008*this.routeLen+this.cmdMach*450, angleBoost=lerp(1500,55000,elevFrac), peak=clamp(base+angleBoost,12000,145000);
      return peak*Math.pow(arch,1.04);
    }
    const g0=this.gravityAtAlt(0), rawPeak=Math.pow(this.cmdAirspeed0*Math.sin(this.elevDeg*RAD),2)/(2*Math.max(1e-6,g0));
    const peakScale=0.035+0.045*elevFrac, rangeBoost=this.routeLen*(0.0015+0.0030*elevFrac), peak=clamp(rawPeak*peakScale+rangeBoost,3000,170000);
    return peak*Math.pow(arch,1.12);
  }
  _pushTrail(){ this.trail.push(this.rEcef().scale(1/RE_M)); if(this.trail.length>this.maxTrail) this.trail.shift(); }
  getState(){ return {pos:this.rEcef(), alt:this.alt, t:this.t, progress:this.progress, ll:this.getLatLon(), vel:this.currVel.clone()}; }
  markDestroyed(reason='destroyed'){ this.alive=false; this.destroyed=true; this.destroyReason=reason; this.intercepted=true; this.impactPosU=this.currentPathU().clone(); }
  updateScalarStep(){
    const frac=clamp(this.progress,0,1), altCmd=this.cmdAltMeters(frac), g=this.gravityAtAlt(this.alt), rho=airDensity(this.alt), aSound=isaSpeedOfSound(this.alt), vCmd=this.cmdMach*aSound;
    const powered=(this.mode!=='ballistic') || this.speedHold;
    const dragK=this.mode==='ballistic'?1.55e-5:1.15e-5; const aDrag=dragK*rho*this.alongSpeed*this.alongSpeed;
    let aProp=0; if(powered){ const tau=this.mode==='cruise'?1.2:1.6, aMax=this.mode==='cruise'?55:70; aProp=clamp((vCmd-this.alongSpeed)/tau,-aMax,aMax); }
    const slopePenalty=Math.max(0,this.vertSpeed)*(this.mode==='ballistic'?0.012:0.018);
    let alongAccel=aProp-aDrag-slopePenalty;
    if(this.mode==='ballistic' && !powered){
      const remainingTime=Math.max(this.dt, this.ballisticTimeSec-this.t), closureNeed=this.distToTargetMeters()/remainingTime;
      alongAccel += clamp((closureNeed-this.alongSpeed)*this.ballisticClosureGain,-18,34);
    }
    this.alongSpeed=clamp(this.alongSpeed+alongAccel*this.dt,160,Math.max(220,vCmd*1.18));
    let kp=0.012, kd=0.30, aVertMax=95;
    if(this.mode==='cruise'){ kp=0.018; kd=0.42; aVertMax=65; }
    else if(this.mode==='ballistic'){ kp=0.013; kd=0.22; aVertMax=88; }
    const altErr=altCmd-this.alt; let aVert=kp*altErr-kd*this.vertSpeed-g*0.90; if(powered) aVert += g*0.96; aVert=clamp(aVert,-aVertMax,aVertMax);
    this.vertSpeed=clamp(this.vertSpeed+aVert*this.dt,-2400,2400); this.alt=Math.max(0,this.alt+this.vertSpeed*this.dt);
    const surfaceScale=RE_M+this.alt, ds=this.alongSpeed*this.dt;
    this.progress += ds/Math.max(1,surfaceScale*this.routeTheta);
    this.t += this.dt; this.age++;
    if(this.progress>=1){
      this.progress=1;
      if(this.mode==='ballistic' && !powered && this.alt>0){ this.vertSpeed=Math.min(this.vertSpeed,-Math.max(220,this.alt*0.03)); this.alt=Math.max(0,this.alt+this.vertSpeed*this.dt); }
      if(this.alt<=1800 || powered || (this.mode==='ballistic' && this.t>=this.ballisticTimeSec*1.04)){
        this.alt=0; this.impactPosU=this.toU.clone(); this.alive=false;
      }
    }
  }
  update(){
    if(!this.alive){ if(this.impactPosU) this.impactAge++; return; }
    for(let i=0;i<this.stepsPerFrame && this.alive;i++){
      const before=this.rEcef();
      this.updateScalarStep();
      const after=this.rEcef();
      this.currVel=after.sub(before).scale(1/this.dt);
      this.prevPos=after.clone();
      this._trailSkip++; if(this._trailSkip>=(this.trailEvery||2)){ this._trailSkip=0; this._pushTrail(); }
      if(this.age>2000000){ this.alive=false; this.impactPosU=this.currentPathU(); break; }
    }
  }
  getLatLon(){ return v2ll(this.currentPathU()); }
  getEtaSec(){ return this.distToTargetMeters()/Math.max(1,this.alongSpeed); }
  getAirspeed(){ return Math.hypot(this.alongSpeed,this.vertSpeed); }
  getMach(){ return this.getAirspeed()/Math.max(1e-6, isaSpeedOfSound(this.alt)); }
}

class Interceptor {
  constructor(fromLL,target,opts={}){
    this.kind='interceptor';
    this.fromLL=[fromLL[0],fromLL[1]]; this.fromName=opts.fromName||'';
    this.linkTarget=target; this.launchDelay=opts.delaySec||0; this.timeSinceLaunch=0; this.launched=this.launchDelay<=0;
    this.cmdMach=opts.cmdMach||12; this.altBiasM=(opts.altBiasMi||35)*1609.344; this.aggression=opts.aggression||0.7;
    this.allowRetarget=opts.allowRetarget!==false; this.realistic=!!opts.realistic;
    this.fromU=ll2v(this.fromLL[0],this.fromLL[1],1).norm();
    this.t=0; this.dt=0.05; this.age=0; this.alive=true; this.hit=false; this.missed=false; this.destroyReason='';
    this.impactPosU=null; this.impactAge=0; this.trail=[]; this.maxTrail=1000; this._trailSkip=0; this.trailEvery=3;
    const est=(this.linkTarget&&this.linkTarget.getEtaSec)?Math.max(1,this.linkTarget.getEtaSec()):600;
    const simSecPerRealSec=this.realistic?1:clamp(est/7,10,700);
    this.stepsPerFrame=clamp(Math.round(simSecPerRealSec/(60*this.dt)),1,160);
    const a0=isaSpeedOfSound(0); this.targetAirspeed=this.cmdMach*a0; this.speed=Math.max(300,this.targetAirspeed*0.82); this.vertSpeed=80;
    this.aimLL=opts.aimLL?[opts.aimLL[0],opts.aimLL[1]]:(target&&target.toLL?[target.toLL[0],target.toLL[1]]:[fromLL[0],fromLL[1]]);
    this.aimAlt=opts.aimAltM||this.altBiasM;
    this.solution=opts.solution||null;
    this.systemName=opts.systemName||'Interceptor';
    this.tier=opts.tier||'custom';
    this.pkBase=clamp(opts.pkBase==null?0.72:opts.pkBase,0.05,0.995);
    this.sensorQuality=clamp(opts.sensorQuality==null?(0.72+0.18*this.aggression):opts.sensorQuality,0.35,0.99);
    this.killRadiusBase=opts.killRadiusBase||null;
    this.rng=Math.random;
    this.doctrine=opts.doctrine||null;
    this.defenderCountry=opts.defenderCountry||'';
    this.salvoIndex=opts.salvoIndex||0;
    this.salvoCount=Math.max(1, opts.salvoCount||1);
    this.concurrentChannels=opts.concurrentChannels||tierChannelCount(this.tier);
    this.reloadElasticity=opts.reloadElasticity==null?0.7:opts.reloadElasticity;
    this.seekerType=opts.seekerType||inferSeekerType(this.systemName,this.tier);
    this.seekerProfile=Object.assign({}, getSeekerProfile(this.seekerType));
    this.trackingQuality=0;
    this.failureMode='';
    this.raidRole=opts.raidRole||'primary';
    this.doctrineFactor=doctrineScore(this.doctrine);
    this.saturationPenalty=1;
    this.saturationBurden=0;
    this.navConstant=opts.navConstant||clamp(2.5+2.2*this.aggression,2.5,5.5);
    this.leadGain=opts.leadGain||0.9;
    this.alt=30;
    this.pos=this.fromU.scale(RE_M+this.alt);
    const aimU=ll2v(this.aimLL[0],this.aimLL[1],1).norm();
    const tangent0=tangToward(this.fromU,aimU);
    this.vel=tangent0.len()>1e-9?tangent0.scale(this.speed):bearingUnit(this.fromLL[0],this.fromLL[1],0).scale(this.speed);
    this.currVel=this.vel.clone();
    this.lastLOSRate=0; this.closestApproach=1e99; this.timeToGo=null;
    this._pushTrail();
  }
  getAimState(){
    if(this.allowRetarget && this.linkTarget && this.linkTarget.alive){
      const st=this.linkTarget.getState();
      const rel=st.pos.sub(this.pos);
      const dist=Math.max(1,rel.len());
      const ownSpd=Math.max(250,this.vel.len());
      const closingRef=Math.max(150, ownSpd + Math.max(0,st.vel.len())*0.35);
      const leadT=clamp(dist/closingRef,0,220);
      const leadPos=st.pos.add(st.vel.scale(leadT*this.leadGain));
      const lead=vecToLatLonAlt(leadPos);
      return {ll:lead.ll, alt:Math.max(500,lead.alt), pos:leadPos, actualPos:st.pos, actualVel:st.vel};
    }
    const u=ll2v(this.aimLL[0],this.aimLL[1],1).norm();
    const pos=u.scale(RE_M+this.aimAlt);
    return {ll:this.aimLL, alt:this.aimAlt, pos, actualPos:pos, actualVel:new V3(0,0,0)};
  }
  currentU(){ return this.pos.norm(); }
  rEcef(){ return this.pos.clone(); }
  _pushTrail(){ this.trail.push(this.pos.scale(1/RE_M)); if(this.trail.length>this.maxTrail) this.trail.shift(); }
  markDone(reason='complete'){ this.alive=false; this.destroyReason=reason; this.impactPosU=this.currentU().clone(); }
  updateScalarStep(){
    if(!this.launched){ this.timeSinceLaunch+=this.dt; this.t+=this.dt; if(this.timeSinceLaunch>=this.launchDelay) this.launched=true; return; }
    const aim=this.getAimState();
    const rel=aim.actualPos.sub(this.pos);
    const range=Math.max(1,rel.len());
    this.closestApproach=Math.min(this.closestApproach,range);
    const los=rel.scale(1/range);
    const relVel=(aim.actualVel||new V3(0,0,0)).sub(this.vel);
    const closing=-relVel.dot(los);
    const lateral=relVel.sub(los.scale(relVel.dot(los)));
    const losRate=lateral.len()/range;
    this.lastLOSRate=losRate;
    this.timeToGo=range/Math.max(1,closing+1);

    const atmo=usAtmo76(this.alt);
    const vMag=Math.max(1,this.vel.len());
    const mach=vMag/Math.max(1,atmo.a);
    const cd=dragCd(mach);
    const dragMag=0.5*cd*0.18*atmo.rho*vMag*vMag;
    const dragAcc=this.vel.scale(-dragMag/Math.max(1,vMag*950));
    const speedErr=this.targetAirspeed-vMag;
    const thrustAcc=this.vel.norm().scale(clamp(speedErr/1.05,-130,130));

    const pnAccMag=clamp(this.navConstant*Math.max(0,closing)*losRate*(0.65+0.6*this.aggression),0,420);
    const lateralDir=lateral.len()>1e-6?lateral.norm():aim.pos.sub(this.pos).norm().sub(this.vel.norm().scale(aim.pos.sub(this.pos).norm().dot(this.vel.norm()))).norm();
    const pnAcc=lateralDir.len()>1e-6?lateralDir.scale(pnAccMag):new V3(0,0,0);

    const altCmd=Math.max(900, aim.alt + this.altBiasM*(0.10+0.25*Math.sin(Math.PI*clamp(1-range/Math.max(1,(this.solution?this.solution.straight:range*1.4)),0,1))));
    const up=this.currentU();
    const radialSpeed=this.vel.dot(up);
    const altErr=altCmd-this.alt;
    const verticalAcc=up.scale(clamp(0.011*altErr - 0.55*radialSpeed + 12*(0.45+this.aggression), -220, 220));
    const gravity=up.scale(-gravJ2(this.alt, vecToLatLonAlt(this.pos).ll[0]*RAD));

    let acc=dragAcc.add(thrustAcc).add(pnAcc).add(verticalAcc).add(gravity);
    const accMag=acc.len();
    if(accMag>520) acc=acc.scale(520/accMag);
    this.vel=this.vel.add(acc.scale(this.dt));
    const newSpeed=this.vel.len();
    if(newSpeed<220) this.vel=this.vel.norm().scale(220);
    this.pos=this.pos.add(this.vel.scale(this.dt));
    const r=this.pos.len()||RE_M;
    this.alt=Math.max(0,r-RE_M);
    const unit=this.pos.scale(1/r);
    if(this.alt<10) this.pos=unit.scale(RE_M+10), this.alt=10;
    // keep velocity roughly tangent plus allowed climb component
    const radialComp=unit.scale(this.vel.dot(unit));
    const tangential=this.vel.sub(radialComp);
    const maxRadial=Math.max(350, this.speed*0.55);
    const clampedRadial=unit.scale(clamp(radialComp.len()*(radialComp.dot(unit)>=0?1:-1),-maxRadial,maxRadial));
    this.vel=tangential.add(clampedRadial);
    this.speed=this.vel.len();
    this.currVel=this.vel.clone();
    this.t+=this.dt; this.age++;

    const actualPos=aim.actualPos||aim.pos;
    const actualRange=this.pos.sub(actualPos).len();
    const targetMach=(this.linkTarget && this.linkTarget.getMach)?this.linkTarget.getMach():0;
    const targetEvasion=this.linkTarget && (this.linkTarget.evasiveness??this.linkTarget.evasion)!=null?(this.linkTarget.evasiveness??this.linkTarget.evasion):0.15;
    const targetMode=this.linkTarget && this.linkTarget.mode ? this.linkTarget.mode : 'ballistic';
    const kinematicTightness=clamp(1 - actualRange/Math.max(1,this.closestApproach*1.35 + 12000), 0, 1);
    const closingFactor=clamp((closing+250)/2200, 0.12, 1.15);
    const altitudeFactor=clamp(1 - Math.abs(this.alt-aim.alt)/Math.max(20000, this.altBiasM + 50000), 0.2, 1.0);
    const maneuverPenalty=clamp(1 - 0.42*targetEvasion - 0.018*Math.max(0,targetMach-3), 0.12, 1.0);
    const sensorFactor=clamp(this.sensorQuality*(0.72 + 0.28*altitudeFactor), 0.2, 1.05);
    const doctrineShot=clamp(0.78 + 0.26*(this.doctrine&&this.doctrine.shotDiscipline!=null?this.doctrine.shotDiscipline:0.8), 0.68, 1.05);
    const doctrineC2=clamp(0.80 + 0.24*(this.doctrine&&this.doctrine.c2!=null?this.doctrine.c2:0.8), 0.72, 1.06);
    const doctrineSense=clamp(0.78 + 0.24*(this.doctrine&&this.doctrine.sensorFusion!=null?this.doctrine.sensorFusion:0.8), 0.68, 1.06);
    const raidState=computeRaidAssignmentState(this.linkTarget, this);
    const saturationState=computeSaturationState(this.linkTarget, this, raidState);
    this.raidRole=raidState.role;
    this.saturationBurden=saturationState.burden;
    this.saturationPenalty=saturationState.penalty;
    const doctrineFactor=clamp(this.doctrineFactor * doctrineShot * doctrineC2 * doctrineSense * raidState.commandFactor, 0.58, 1.16);
    const seekerState=computeSeekerState(this, {range:actualRange, closing, aimAlt:aim.alt, targetAlt:this.linkTarget?this.linkTarget.alt:aim.alt, targetMach, targetEvasion, targetMode, kinematicTightness, altitudeFactor, sensorFactor});
    this.trackingQuality=seekerState.tracking;
    const pkNow=clamp(this.pkBase * closingFactor * altitudeFactor * maneuverPenalty * sensorFactor * doctrineFactor * this.saturationPenalty * seekerState.pkFactor * (0.45 + 0.7*kinematicTightness), 0.01, 0.995);
    this.pkNow=pkNow;
    const killRadiusNominal=this.killRadiusBase || clamp(9000 + 14000*this.pkBase + 6000*this.aggression, 8000, 32000);
    const killRadius=killRadiusNominal * clamp((0.72 + 0.45*kinematicTightness + 0.18*sensorFactor) * (0.90 + 0.12*this.doctrineFactor) * (0.92 + 0.10*this.saturationPenalty) * seekerState.radiusFactor, 0.35, 1.45);
    if(this.linkTarget && this.linkTarget.alive && actualRange<killRadius){
      if(this.rng() < pkNow){ this.failureMode=''; this.hit=true; this.markDone('hit'); this.linkTarget.markDestroyed('intercepted'); return; }
      this.failureMode=seekerState.failureMode || 'kinematic miss';
      this.missed=true; this.markDone('no-kill-window'); return;
    }
    const diverging = this.age>30 && closing< -80 && actualRange>this.closestApproach*1.18;
    const overshot = this.timeToGo!=null && this.timeToGo<1.2 && actualRange>killRadius*2.4;
    if(diverging || overshot || this.age>1800000 || this.alt>1800000){ this.missed=true; this.markDone(diverging?'miss-diverge':(overshot?'miss-overshoot':'timeout')); return; }
  }
  update(){
    if(!this.alive){ if(this.impactPosU) this.impactAge++; return; }
    for(let i=0;i<this.stepsPerFrame && this.alive;i++){
      this.updateScalarStep();
      this._trailSkip++; if(this._trailSkip>=(this.trailEvery||2)){ this._trailSkip=0; this._pushTrail(); }
    }
  }
}

const canvas=document.getElementById('globe');
const ctx=canvas.getContext('2d');
let W=800,H=600,CX=400,CY=300,GLOBE_R=240,rotX=-0.23,rotY=0.55,zoom=1;
let dragging=false,lastMX=0,lastMY=0,autoRotate=true,followShot=true,worldFeatures=null;
let projectiles=[], interceptors=[], previewProjectile=null, previewSolution=null, previewDirty=true, previewKey='', fireBusy=false;
const loggedEvents=new Set();
let curMode='ballistic', curMach=20.0, curAngle=35, cruiseAltMi=40, evasiveness=0.5;
let shots=0, kills=0;
const metrics={resolvedAttacks:0, leakedAttacks:0, interceptedAttacks:0, failedInterceptShots:0, successfulInterceptShots:0, livePkSamples:[], doctrineSamples:[], saturationSamples:[], trackingSamples:[], attackRecords:[], failureTally:{}, seekerUsage:{}};
function safeMean(arr){ return arr&&arr.length?arr.reduce((a,b)=>a+b,0)/arr.length:0; }
function doctrineScore(d){
  if(!d) return 0.82;
  return clamp(
    0.24*(d.c2||0.8)+
    0.18*(d.sensorFusion||0.8)+
    0.18*(d.training||0.8)+
    0.12*(d.maintenance||0.8)+
    0.16*(d.shotDiscipline||0.8)+
    0.12*(d.raidCapacityNorm||0.8), 0.55, 1.08
  );
}
function tierChannelCount(tier){
  if(tier==='exo') return 2;
  if(tier==='high-endo') return 3;
  if(tier==='endo') return 4;
  if(tier==='point') return 6;
  return 3;
}
const SEEKER_DB={
  hitToKill:{label:'Hit-to-kill', baseTrack:0.92, radiusFactor:0.82, exoBonus:1.14, lowAltPenalty:0.72, evasivePenalty:0.70, cruiseBonus:0.88, ballisticBonus:1.08, hypersonicPenalty:0.80, fail:['track break','divert shortfall','seeker gate loss']},
  activeRadar:{label:'Active radar', baseTrack:0.86, radiusFactor:1.00, exoBonus:0.96, lowAltPenalty:0.86, evasivePenalty:0.82, cruiseBonus:1.00, ballisticBonus:0.98, hypersonicPenalty:0.88, fail:['terminal radar break','ECM / clutter','late basket collapse']},
  semiActiveRadar:{label:'Semi-active radar', baseTrack:0.81, radiusFactor:1.04, exoBonus:0.90, lowAltPenalty:0.84, evasivePenalty:0.80, cruiseBonus:0.97, ballisticBonus:0.96, hypersonicPenalty:0.84, fail:['illumination loss','track handoff slip','command lag']},
  commandGuided:{label:'Command guided', baseTrack:0.76, radiusFactor:1.08, exoBonus:0.78, lowAltPenalty:0.90, evasivePenalty:0.74, cruiseBonus:0.94, ballisticBonus:0.90, hypersonicPenalty:0.74, fail:['uplink break','command latency','radar update drop']},
  ir:{label:'Infrared', baseTrack:0.78, radiusFactor:0.93, exoBonus:1.00, lowAltPenalty:0.82, evasivePenalty:0.83, cruiseBonus:0.92, ballisticBonus:1.02, hypersonicPenalty:0.86, fail:['thermal decoy / bloom','background clutter','angle-off loss']}
};
function inferSeekerType(systemName,tier){
  const n=(systemName||'').toLowerCase();
  if(/sm-3|gbi|arrow 3|thaad|hq-19|nudol|pdv/.test(n)) return 'hitToKill';
  if(/patriot|arrow 2|davids sling|sea viper|aster|s-400|s-500|hq-9|sky bow|pac-3/.test(n)) return 'activeRadar';
  if(/iron dome|pantsir|crotale|akash|nasams|iris-t|camm|sky sabre|km-sam|hisar|buk/.test(n)) return 'commandGuided';
  if(/ir/.test(n)) return 'ir';
  if(tier==='exo') return 'hitToKill';
  if(tier==='point') return 'commandGuided';
  return 'activeRadar';
}
function getSeekerProfile(type){ return SEEKER_DB[type] || SEEKER_DB.activeRadar; }
function computeRaidAssignmentState(target, interceptor){
  const aliveThreats=projectiles.filter(p=>p.alive);
  const doctrine=interceptor&&interceptor.doctrine ? interceptor.doctrine : {raidCapacity:3, concurrentChannels:4, shotDiscipline:0.75};
  const threatScores=aliveThreats.map(p=>({
    target:p,
    score: threatPriorityScore(p, interceptor)
  })).sort((a,b)=>b.score-a.score);
  const sameTarget=interceptors.filter(i=>i.alive && i.launched && i.linkTarget===target).length;
  const targetIdx=Math.max(0, threatScores.findIndex(t=>t.target===target));
  const raidCapacity=Math.max(1, doctrine.raidCapacity||3);
  const maxPrimary=Math.max(1, Math.ceil((doctrine.concurrentChannels||4)/Math.max(1, Math.min(aliveThreats.length||1, raidCapacity))));
  const role=sameTarget < maxPrimary ? 'primary' : (sameTarget < maxPrimary+1 ? 'support' : 'excess');
  const queuePenalty=clamp(1 - 0.08*Math.max(0,targetIdx-raidCapacity+1), 0.70, 1.0);
  const commandFactor=clamp(queuePenalty * (role==='primary'?1:(role==='support'?0.95:0.84)) * (0.88+0.16*(doctrine.shotDiscipline||0.75)), 0.66, 1.08);
  return {role,targetIdx,maxPrimary,queuePenalty,commandFactor,aliveThreats:aliveThreats.length||1};
}
function threatPriorityScore(p, interceptor){
  if(!p) return 0;
  const eta=p.getEtaSec?p.getEtaSec():9999;
  const dist=(interceptor && interceptor.fromLL)?gcDistMeters(interceptor.fromLL, p.getState().ll):p.distToTargetMeters?p.distToTargetMeters():0;
  const modeFactor=p.mode==='ballistic'?1.18:(p.mode==='evasive'?1.14:(p.mode==='guided'?1.06:0.96));
  const speedFactor=0.75 + 0.02*Math.min(25, p.getMach?p.getMach():0);
  return modeFactor * speedFactor * (1.35/(0.25+Math.max(0.15, eta/2400))) * (1.2/(0.4+Math.max(0.2, dist/400000)));
}
function computeSaturationState(target, interceptor, raidState){
  const aliveThreats=projectiles.filter(p=>p.alive).length || 1;
  const sameTarget=interceptors.filter(i=>i.alive && i.launched && i.linkTarget===target).length || 1;
  const launchedTotal=interceptors.filter(i=>i.alive && i.launched).length || 1;
  const doctrine=interceptor&&interceptor.doctrine ? interceptor.doctrine : {raidCapacity:3, concurrentChannels:4, reloadElasticity:0.7};
  const raidCapacity=Math.max(1, doctrine.raidCapacity||3);
  const concurrent=Math.max(1, (doctrine.concurrentChannels||4) + tierChannelCount(interceptor&&interceptor.tier));
  const salvoCount=Math.max(1, interceptor&&interceptor.salvoCount||1);
  const salvoIndex=Math.max(0, interceptor&&interceptor.salvoIndex||0);
  const overRaid=Math.max(0, aliveThreats-raidCapacity)/raidCapacity;
  const overChannel=Math.max(0, sameTarget-concurrent)/concurrent;
  const globalOvercommit=Math.max(0, launchedTotal - concurrent*Math.max(1,aliveThreats))/Math.max(1, concurrent*Math.max(1,aliveThreats));
  const shotCrowding=Math.max(0, sameTarget-1)/Math.max(1, concurrent*1.5);
  const ripplePenalty=Math.max(0, salvoCount-concurrent)/Math.max(1, concurrent*2.2) + salvoIndex/Math.max(4, concurrent*2.5);
  const queuePenalty=Math.max(0, (raidState&&raidState.targetIdx!=null?raidState.targetIdx:0) - raidCapacity + 1)/raidCapacity;
  const rolePenalty=(raidState&&raidState.role==='excess')?0.22:((raidState&&raidState.role==='support')?0.08:0.0);
  const reloadElasticity=clamp(doctrine.reloadElasticity==null?0.7:doctrine.reloadElasticity,0.35,1.0);
  const burden=clamp(0.45*overRaid + 0.75*overChannel + 0.30*shotCrowding + 0.30*ripplePenalty + 0.55*globalOvercommit + 0.25*queuePenalty + rolePenalty, 0, 2.6);
  const penalty=clamp(1 - (0.22+0.14*(1-reloadElasticity))*Math.sqrt(burden), 0.34, 1.0);
  return {aliveThreats,sameTarget,raidCapacity,concurrent,burden,penalty,globalOvercommit};
}
function computeSeekerState(interceptor, geom){
  const p=interceptor.seekerProfile || SEEKER_DB.activeRadar;
  const altMi=(geom.targetAlt||0)*0.00062137119224;
  const mode=geom.targetMode||'ballistic';
  let track=p.baseTrack;
  track*=0.76 + 0.24*geom.sensorFactor;
  track*=0.72 + 0.28*geom.kinematicTightness;
  track*=0.74 + 0.26*clamp((geom.closing+180)/1800,0.15,1.1);
  if(mode==='ballistic') track*=p.ballisticBonus||1;
  if(mode==='cruise') track*=p.cruiseBonus||1;
  if(mode==='evasive') track*=p.evasivePenalty||0.82;
  if(geom.targetMach>8) track*=p.hypersonicPenalty||0.86;
  if(altMi<1.2) track*=p.lowAltPenalty||0.84;
  if(altMi>55) track*=p.exoBonus||1;
  track*=clamp(1 - 0.22*geom.targetEvasion, 0.55, 1.0);
  const tracking=clamp(track, 0.18, 1.18);
  let failureMode='';
  if(tracking<0.45){
    const failList=p.fail||['seeker break'];
    failureMode=failList[Math.floor(Math.min(failList.length-1, Math.random()*failList.length))];
  }
  return {tracking, pkFactor:clamp(0.55 + 0.70*tracking, 0.18, 1.24), radiusFactor:clamp(p.radiusFactor*(0.72 + 0.36*tracking), 0.30, 1.22), failureMode};
}


const $=id=>document.getElementById(id);
const hud=$('hud'), logEl=$('log'), shotCount=$('shotCount'), killCount=$('killCount'), activeThreatCount=$('activeThreatCount'), activeDefenseCount=$('activeDefenseCount');
const engagementChart=$('engagementChart'), attackSuccessRateEl=$('attackSuccessRate'), interceptSuccessRateEl=$('interceptSuccessRate'), avgPkLiveEl=$('avgPkLive'), engagementSummary=$('engagementSummary');
const fromInput=$('fromC'), toInput=$('toC'), interceptInput=$('interceptFrom');
const attackResolved=$('attackResolved'), defenseResolved=$('defenseResolved'), interceptSummary=$('interceptSummary');

function resize(){
  const pr=window.devicePixelRatio||1, parent=canvas.parentElement, rect=parent.getBoundingClientRect(), w=rect.width||window.innerWidth;
  if(!w || w<50){ setTimeout(resize,50); return; }
  W=w; H=Math.min(720, Math.max(460, W*0.68));
  canvas.width=Math.floor(W*pr); canvas.height=Math.floor(H*pr); canvas.style.width=W+'px'; canvas.style.height=H+'px';
  ctx.setTransform(pr,0,0,pr,0,0); CX=W/2; CY=H/2; GLOBE_R=Math.min(W,H)*0.38*zoom;
}
function project(v){
  let x=v.x*Math.cos(rotY)-v.z*Math.sin(rotY), z=v.x*Math.sin(rotY)+v.z*Math.cos(rotY), y=v.y;
  let y2=y*Math.cos(rotX)-z*Math.sin(rotX), z2=y*Math.sin(rotX)+z*Math.cos(rotX);
  return {x:CX+x*GLOBE_R,y:CY-y2*GLOBE_R,z:z2,visible:z2>=0};
}
function projectLL(lat,lon,r=1){ return project(ll2v(lat,lon,r)); }
function dist2(a,b){ const dx=a.x-b.x, dy=a.y-b.y; return dx*dx+dy*dy; }
function drawSegmentedPolyline(points, visibleWanted, opts={}){
  if(points.length<2) return; ctx.save(); ctx.strokeStyle=opts.strokeStyle||'#fff'; ctx.lineWidth=opts.lineWidth||1; ctx.setLineDash(opts.dash||[]); ctx.globalAlpha=opts.alpha ?? 1; ctx.beginPath();
  let started=false, prev=null;
  for(const p of points){
    if(p.visible===visibleWanted){ const jumpBad=prev && dist2(prev,p) > (GLOBE_R*0.32)*(GLOBE_R*0.32); if(!started||jumpBad){ ctx.moveTo(p.x,p.y); started=true; } else ctx.lineTo(p.x,p.y); }
    else started=false; prev=p;
  }
  ctx.stroke(); ctx.restore();
}
function drawGlobe(){
  ctx.clearRect(0,0,W,H);
  const bg=ctx.createRadialGradient(CX,CY,GLOBE_R*0.4,CX,CY,GLOBE_R*2.0); bg.addColorStop(0,'#04111d'); bg.addColorStop(1,'#000308'); ctx.fillStyle=bg; ctx.fillRect(0,0,W,H);
  ctx.fillStyle='#fff'; for(let i=0;i<220;i++){ const sx=(Math.sin(i*127.1+i*i*0.03)*0.5+0.5)*W, sy=(Math.cos(i*311.7+i*0.07)*0.5+0.5)*H; ctx.globalAlpha=0.08+((i*73)%100)/200; ctx.fillRect(sx,sy,1,1); } ctx.globalAlpha=1;
  const atm=ctx.createRadialGradient(CX,CY,GLOBE_R*0.95,CX,CY,GLOBE_R*1.23); atm.addColorStop(0,'rgba(30,100,220,0.18)'); atm.addColorStop(0.58,'rgba(18,70,170,0.08)'); atm.addColorStop(1,'transparent'); ctx.fillStyle=atm; ctx.beginPath(); ctx.arc(CX,CY,GLOBE_R*1.2,0,Math.PI*2); ctx.fill();
  const oc=ctx.createRadialGradient(CX-GLOBE_R*0.28,CY-GLOBE_R*0.34,GLOBE_R*0.08,CX,CY,GLOBE_R); oc.addColorStop(0,'#14355a'); oc.addColorStop(0.55,'#0b2646'); oc.addColorStop(1,'#051224'); ctx.fillStyle=oc; ctx.beginPath(); ctx.arc(CX,CY,GLOBE_R,0,Math.PI*2); ctx.fill();
  ctx.save(); ctx.beginPath(); ctx.arc(CX,CY,GLOBE_R,0,Math.PI*2); ctx.clip();
  for(let lat=-80; lat<=80; lat+=20){ const pts=[]; for(let lon=-180; lon<=180; lon+=2) pts.push(projectLL(lat,lon,1.001)); drawSegmentedPolyline(pts,true,{strokeStyle:'rgba(34,74,110,0.28)',lineWidth:0.6}); }
  for(let lon=-180; lon<180; lon+=20){ const pts=[]; for(let lat=-88; lat<=88; lat+=2) pts.push(projectLL(lat,lon,1.001)); drawSegmentedPolyline(pts,true,{strokeStyle:'rgba(34,74,110,0.22)',lineWidth:0.5}); }
  if(worldFeatures){
    for(const poly of worldFeatures){ const pts=[]; for(let i=0;i<poly.length;i++){ const [lon,lat]=poly[i]; pts.push(projectLL(lat,lon,1.0016)); } drawSegmentedPolyline(pts,true,{strokeStyle:'rgba(128,190,150,0.34)',lineWidth:1.1,alpha:0.95}); }
  }
  ctx.restore(); ctx.strokeStyle='rgba(155,220,255,0.12)'; ctx.lineWidth=2.2; ctx.beginPath(); ctx.arc(CX,CY,GLOBE_R,0,Math.PI*2); ctx.stroke();
}
function drawPulse(pr, color, r1=10, r2=4, alpha=1){
  if(!pr.visible) return; ctx.save(); ctx.globalAlpha=alpha*0.22; ctx.fillStyle=color; ctx.beginPath(); ctx.arc(pr.x,pr.y,r1,0,Math.PI*2); ctx.fill(); ctx.globalAlpha=alpha; ctx.fillStyle='#fff'; ctx.beginPath(); ctx.arc(pr.x,pr.y,r2,0,Math.PI*2); ctx.fill(); ctx.restore();
}
function drawGreatCircle(fromLL,toLL,col){ const a=ll2v(fromLL[0],fromLL[1],1).norm(), b=ll2v(toLL[0],toLL[1],1).norm(), pts=[]; for(let i=0;i<=280;i++) pts.push(project(slerpUnit(a,b,i/280).scale(1.003))); drawSegmentedPolyline(pts,true,{strokeStyle:col,lineWidth:2,alpha:0.26}); drawSegmentedPolyline(pts,false,{strokeStyle:'#fff',lineWidth:1.2,alpha:0.12,dash:[6,6]}); }
function drawProjectileTrace(p,col){ const pts=p.trail.map(v=>project(v)); drawSegmentedPolyline(pts,true,{strokeStyle:col,lineWidth:1.8,alpha:0.58}); drawSegmentedPolyline(pts,false,{strokeStyle:col,lineWidth:1.3,alpha:0.18,dash:[6,6]}); }
function drawAttackLine(p,col){
  const src=[project(ll2v(p.fromLL[0],p.fromLL[1],1.003))]; const tr=p.trail; const keep=Math.min(tr.length,520); for(let i=Math.max(0,tr.length-keep); i<tr.length; i++) src.push(project(tr[i])); if(p.alive) src.push(project(p.rEcef().scale(1/RE_M))); else if(p.impactPosU) src.push(project(p.impactPosU.scale(1.002)));
  drawSegmentedPolyline(src,true,{strokeStyle:col,lineWidth:7.8,alpha:0.24}); drawSegmentedPolyline(src,true,{strokeStyle:'#ffffff',lineWidth:3.2,alpha:0.96}); drawSegmentedPolyline(src,false,{strokeStyle:'#ffffff',lineWidth:2.2,alpha:0.32,dash:[8,6]});
}
function drawInterceptorLine(intc){
  const pts=intc.trail.map(v=>project(v)); drawSegmentedPolyline(pts,true,{strokeStyle:'#38e2ff',lineWidth:6.5,alpha:0.18}); drawSegmentedPolyline(pts,true,{strokeStyle:'#9ef4ff',lineWidth:2.8,alpha:0.95}); drawSegmentedPolyline(pts,false,{strokeStyle:'#9ef4ff',lineWidth:1.6,alpha:0.26,dash:[7,6]});
  if(intc.launched && intc.linkTarget && intc.linkTarget.alive){
    const a=project(intc.rEcef().scale(1/RE_M)), b=project(intc.linkTarget.rEcef().scale(1/RE_M));
    drawSegmentedPolyline([a,b],true,{strokeStyle:'#44f4ff',lineWidth:2.0,alpha:0.55,dash:[6,4]});
    drawSegmentedPolyline([a,b],false,{strokeStyle:'#ffffff',lineWidth:1.2,alpha:0.16,dash:[6,6]});
  }
}
function drawPreviewShot(p, solution){
  if(!p || !p.trail || p.trail.length<2) return; const col=MODE_COLORS[p.mode]||'#fff'; const pts=p.trail.map(v=>project(v));
  drawSegmentedPolyline(pts,true,{strokeStyle:col,lineWidth:3.2,alpha:0.18,dash:[10,6]}); drawSegmentedPolyline(pts,true,{strokeStyle:'#fff',lineWidth:1.3,alpha:0.62,dash:[10,6]});
  if(p.previewPeakU){ const pr=project(p.previewPeakU.scale((RE_M+Math.max(0,p.previewPeakAlt||0))/RE_M)); drawPulse(pr,'#88ddff',9,2.6,pr.visible?0.95:0.35); }
  if(solution && solution.targetState){
    const su=ll2v(solution.targetState.ll[0],solution.targetState.ll[1],1).norm().scale((RE_M+solution.targetState.alt)/RE_M), sp=project(su), dp=project(ll2v(solution.fromLL[0],solution.fromLL[1],1.006));
    drawPulse(dp,'#44f5ff',8,3.4,1); drawPulse(sp,'#44f5ff',10,3.6,0.8); drawSegmentedPolyline([dp,sp],true,{strokeStyle:'#44f5ff',lineWidth:2.0,alpha:0.4,dash:[6,4]});
  }
}
function drawAllShots(){
  for(const p of projectiles){ const col=MODE_COLORS[p.mode]||'#ff9955'; drawGreatCircle(p.fromLL,p.toLL,col); drawProjectileTrace(p,col); drawAttackLine(p,col); const fp=projectLL(p.fromLL[0],p.fromLL[1],1.006), tp=projectLL(p.toLL[0],p.toLL[1],1.006); drawPulse(fp,'#59ff96',10,4,0.9); drawPulse(tp,p.intercepted?'#49f8ff':'#ff6d6d',10,4,0.9); if(p.alive){ drawPulse(project(p.rEcef().scale(1/RE_M)), col, 16, 4.8, 1); } else if(p.impactPosU && p.impactAge<260){ drawPulse(project(p.impactPosU.scale(1.003)), p.intercepted?'#49f8ff':'#ff6d6d', 14, 4.2, 0.9); } }
  for(const i of interceptors){ const dp=projectLL(i.fromLL[0],i.fromLL[1],1.006); drawPulse(dp,'#44f5ff',10,4,0.9); drawInterceptorLine(i); if(i.launched && i.alive) drawPulse(project(i.rEcef().scale(1/RE_M)),'#44f5ff',14,4.2,1); else if(i.impactPosU && i.impactAge<240) drawPulse(project(i.impactPosU.scale(1.003)), i.hit?'#8affd5':'#9deaff', 12, 3.8, 0.9); }
}

fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json').then(r=>r.json()).then(topo=>{
  const obj=topo.objects.countries, {scale:s, translate:tr}=topo.transform;
  const arcs=topo.arcs.map(arc=>{ let x=0,y=0; return arc.map(([dx,dy])=>{ x+=dx; y+=dy; return [x*s[0]+tr[0], y*s[1]+tr[1]]; }); });
  const res=i=>i>=0?arcs[i]:arcs[~i].slice().reverse(); const ring=ids=>{ let c=[]; ids.forEach(id=>{ const a=res(id); c=c.length ? c.concat(a.slice(1)) : c.concat(a); }); return c; };
  worldFeatures=obj.geometries.map(g=>g.type==='Polygon'?g.arcs.map(ring):g.type==='MultiPolygon'?g.arcs.map(p=>p.map(ring)).flat():[]).flat();
}).catch(()=>{ worldFeatures=null; });

function escapeHtml(s){ return String(s).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
function normalizePlaceKey(raw){ return String(raw||'').trim().toLowerCase().replace(/\s+/g,' '); }
function parseLatLon(raw){ const m=String(raw||'').match(/^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/); if(!m) return null; const lat=parseFloat(m[1]), lon=parseFloat(m[2]); if(!(lat>=-90&&lat<=90&&lon>=-180&&lon<=180)) return null; return {name:lat.toFixed(4)+', '+lon.toFixed(4), lat, lon, provider:'manual', kind:'coordinates'}; }
async function fetchJson(url){ const res=await fetch(url,{headers:{'Accept':'application/json'}}); const data=await res.json().catch(()=>({})); if(!res.ok) throw new Error(data.error || ('Request failed ('+res.status+')')); return data; }
async function resolvePlace(raw){ const direct=parseLatLon(raw); if(direct) return direct; const data=await fetchJson('/api/geocode?q='+encodeURIComponent(raw)); if(!data.result) throw new Error('Could not resolve place.'); return data.result; }
function resolveSeedPlaceFast(raw){ const direct=parseLatLon(raw); if(direct) return direct; const q=normalizePlaceKey(raw); if(!q) return null; const exact=PLACE_SEED.find(item=>normalizePlaceKey(item.name)===q&&item.lat!=null); if(exact) return exact; return PLACE_SEED.find(item=>normalizePlaceKey(item.name).startsWith(q)&&item.lat!=null) || null; }
function getSeedMatches(raw, limit=8){ const q=normalizePlaceKey(raw); if(!q) return PLACE_SEED.filter(p=>p.priority).sort((a,b)=>(a.priority||999)-(b.priority||999)).slice(0,limit); const exact=[], starts=[], contains=[]; for(const item of PLACE_SEED){ const nk=normalizePlaceKey(item.name); if(nk===q) exact.push(item); else if(nk.startsWith(q)) starts.push(item); else if(nk.includes(q)) contains.push(item); } return exact.concat(starts,contains).slice(0,limit); }
function addLog(msg, cls='info-entry'){ const d=document.createElement('div'); d.className=cls; d.textContent='['+new Date().toLocaleTimeString()+'] '+msg; logEl.appendChild(d); logEl.scrollTop=logEl.scrollHeight; }
function shortPlaceName(p){ const nm=(p&&p.name)?p.name:''; return nm.split(',')[0].trim() || nm; }
function describeResolved(place){
  if(!place) return 'unresolved';
  const parts=[place.name, place.kind||'place', place.provider||'source', place.lat!=null ? place.lat.toFixed(4)+'°' : '', place.lon!=null ? place.lon.toFixed(4)+'°' : ''].filter(Boolean);
  return parts.join(' • ');
}
function syncResolvedBoxes(){
  const a=resolveSeedPlaceFast(fromInput.value), b=resolveSeedPlaceFast(toInput.value), d=resolveSeedPlaceFast(interceptInput.value);
  attackResolved.innerHTML='<b>GEO RESOLUTION</b><br>Launch: '+escapeHtml(describeResolved(a))+'<br>Target: '+escapeHtml(describeResolved(b));
  defenseResolved.innerHTML='<b>DEFENSE RESOLUTION</b><br>Site: '+escapeHtml(describeResolved(d));
}
function renderSuggestions(input, sugEl, items, state){
  state.items=items||[]; if(!state.items.length){ state.active=-1; sugEl.innerHTML=''; sugEl.style.display='none'; return; }
  if(state.active<0) state.active=0; if(state.active>=state.items.length) state.active=state.items.length-1;
  sugEl.innerHTML=state.items.slice(0,10).map((item,idx)=>{ const label=escapeHtml(item.name||item.display||item.label||''), meta=[item.kind,item.provider].filter(Boolean).map(escapeHtml).join(' · '); return `<div class="${idx===state.active?'active':''}" data-idx="${idx}"><span>${label}</span>${meta?`<small>${meta}</small>`:''}</div>`; }).join('');
  sugEl.style.display='block'; sugEl.querySelectorAll('div').forEach(div=>{ div.onmousedown=(ev)=>{ ev.preventDefault(); const item=state.items[+div.dataset.idx]; input.value=item.name||item.display||item.label||''; sugEl.innerHTML=''; sugEl.style.display='none'; markPreviewDirty(); syncResolvedBoxes(); }; });
}
function setupSuggest(input, sugEl){
  const state={items:[],active:-1,timer:null,seq:0}; const closeBox=()=>{ state.items=[]; state.active=-1; sugEl.innerHTML=''; sugEl.style.display='none'; };
  const refresh=(forceRemote=false)=>{ const raw=input.value.trim(); const direct=parseLatLon(raw); const merged=[], seen=new Set(); if(direct){ merged.push(direct); seen.add(normalizePlaceKey(direct.name)); } for(const item of getSeedMatches(raw, raw?8:10)){ const k=normalizePlaceKey(item.name); if(!seen.has(k)){ seen.add(k); merged.push(item); } } state.active=merged.length?0:-1; renderSuggestions(input,sugEl,merged,state); if(state.timer) clearTimeout(state.timer); if((!raw||raw.length<2||direct)&&!forceRemote) return; const mySeq=++state.seq; state.timer=setTimeout(async()=>{ try{ const data=await fetchJson('/api/suggest?q='+encodeURIComponent(raw)); if(mySeq!==state.seq) return; for(const item of (data.results||[])){ const k=normalizePlaceKey(item.name); if(!seen.has(k)){ seen.add(k); merged.push(item); } } renderSuggestions(input,sugEl,merged,state); }catch(_e){} }, forceRemote?0:220); };
  input.addEventListener('focus',()=>refresh(false)); input.addEventListener('click',()=>refresh(false)); input.addEventListener('input',()=>{ refresh(false); markPreviewDirty(); syncResolvedBoxes(); }); input.addEventListener('change',()=>{ markPreviewDirty(); syncResolvedBoxes(); });
  input.addEventListener('keydown',e=>{ if(!state.items.length) return; if(e.key==='ArrowDown'||e.key==='ArrowUp'){ e.preventDefault(); state.active = state.active<0?0:(state.active + (e.key==='ArrowDown'?1:-1)+state.items.length)%state.items.length; sugEl.querySelectorAll('div').forEach((div,idx)=>div.classList.toggle('active', idx===state.active)); const activeEl=sugEl.querySelector('div.active'); if(activeEl) activeEl.scrollIntoView({block:'nearest'}); return; } if(e.key==='Enter'&&state.active>=0){ e.preventDefault(); const item=state.items[state.active]; input.value=item.name||item.display||item.label||''; closeBox(); markPreviewDirty(); syncResolvedBoxes(); return; } if(e.key==='Escape') closeBox(); });
  input.addEventListener('blur',()=>setTimeout(closeBox,160));
}
setupSuggest(fromInput,$('fromSug')); setupSuggest(toInput,$('toSug')); setupSuggest(interceptInput,$('interceptSug')); syncResolvedBoxes();

function setMode(mode){ curMode=mode; document.querySelectorAll('.modes button').forEach(b=>{ b.classList.remove('active','m-ballistic','m-guided','m-cruise','m-evasive'); if(b.dataset.mode===curMode) b.classList.add('active','m-'+curMode); }); $('modeDesc').textContent=MODE_DESC[curMode]; markPreviewDirty(); }
document.querySelectorAll('.modes button').forEach(btn=>btn.onclick=()=>setMode(btn.dataset.mode));
$('machSlider').oninput=()=>{ curMach=+$('machSlider').value; $('machLabel').textContent='Mach '+curMach.toFixed(1); const mph=(curMach*isaSpeedOfSound(0))*2.2369362921; $('mphLabel').textContent='(≈ '+Math.round(mph).toLocaleString()+' mph @ sea level)'; markPreviewDirty(); };
$('angleSlider').oninput=()=>{ curAngle=+$('angleSlider').value; $('angleLabel').textContent=curAngle+'°'; markPreviewDirty(); };
$('evasionSlider').oninput=()=>{ evasiveness=+$('evasionSlider').value; $('evasionLabel').textContent=evasiveness.toFixed(2); markPreviewDirty(); };
$('delaySlider').oninput=()=>{ $('delayLabel').textContent=$('delaySlider').value+' s'; markPreviewDirty(); };
$('defMachSlider').oninput=()=>{ $('defMachLabel').textContent='Mach '+(+$('defMachSlider').value).toFixed(1); markPreviewDirty(); };
$('defAltSlider').oninput=()=>{ $('defAltLabel').textContent=$('defAltSlider').value+' mi'; markPreviewDirty(); };
$('aggrSlider').oninput=()=>{ $('aggrLabel').textContent=(+$('aggrSlider').value).toFixed(2); markPreviewDirty(); };
$('batteryCountSlider').oninput=()=>{ $('batteryCountLabel').textContent=$('batteryCountSlider').value; markPreviewDirty(); };
$('salvoSpacingSlider').oninput=()=>{ $('salvoSpacingLabel').textContent=$('salvoSpacingSlider').value+' s'; markPreviewDirty(); };
['speedHold','realisticMode','interceptPolicy','allowRetarget'].forEach(id=>$(id).addEventListener('change',()=>markPreviewDirty()));
$('btnMirrorDefense').onclick=()=>{ interceptInput.value=toInput.value; markPreviewDirty(); syncResolvedBoxes(); addLog('Defense site copied from target.', 'info-entry'); };

function getDefenseSiteFast(toPlace){ if($('interceptPolicy').value==='auto-target' && toPlace) return {name:toPlace.name, lat:toPlace.lat, lon:toPlace.lon, provider:toPlace.provider, kind:toPlace.kind}; return resolveSeedPlaceFast(interceptInput.value); }
function planIntercept(attack, defensePlace){
  if(!attack || !defensePlace || $('interceptPolicy').value==='off') return null;
  const delaySec=+$('delaySlider').value, cmdMach=+$('defMachSlider').value, altBiasMi=+$('defAltSlider').value, aggression=+$('aggrSlider').value;
  const a0=isaSpeedOfSound(0), interceptorNominal=Math.max(280, cmdMach*a0*0.90), fromLL=[defensePlace.lat, defensePlace.lon], forecast=attack.cloneForForecast();
  const defensePos=ll2v(fromLL[0],fromLL[1],1).norm().scale(RE_M+30);
  let best=null;
  for(let k=0;k<4200 && forecast.alive;k++){
    forecast.update();
    if(forecast.t < delaySec) continue;
    const state=forecast.getState(), [lat,lon]=state.ll, targetLL=[lat,lon];
    const surface=gcDistMeters(fromLL,targetLL);
    const straight=state.pos.sub(defensePos).len();
    const climbPenalty=Math.abs(state.alt-altBiasMi*1609.344)/(1800+cmdMach*80);
    const pathNeed=Math.max(surface*0.82, straight*1.04);
    const needed=pathNeed/Math.max(250,interceptorNominal) + climbPenalty;
    const available=Math.max(0, forecast.t-delaySec);
    const terminalBonus = clamp((200000-straight)/200000, -0.5, 0.5);
    const closureScore=available-needed+terminalBonus+0.35*aggression;
    const candidate={targetState:{ll:targetLL,alt:state.alt,t:forecast.t}, available, needed, closureScore, fromLL, delaySec, cmdMach, altBiasMi, aggression, straight, surface};
    if(closureScore >= 0.75){ best=candidate; break; }
    if(!best || closureScore > best.closureScore) best=candidate;
  }
  return best;
}
function markPreviewDirty(){ previewDirty=true; }
function rebuildPreview(){
  previewDirty=false; previewProjectile=null; previewSolution=null;
  const from=resolveSeedPlaceFast(fromInput.value), to=resolveSeedPlaceFast(toInput.value); if(!from||!to||from.lat==null||to.lat==null) return; if(Math.abs(from.lat-to.lat)<1e-7&&Math.abs(from.lon-to.lon)<1e-7) return;
  const real=$('realisticMode').checked, speedHold=$('speedHold').checked, defense=getDefenseSiteFast(to);
  const key=[normalizePlaceKey(from.name),normalizePlaceKey(to.name),curMode,curMach.toFixed(2),curAngle.toFixed(2),evasiveness.toFixed(2), real?'R':'C', speedHold?'1':'0', normalizePlaceKey(defense?defense.name:''), $('interceptPolicy').value, $('delaySlider').value, $('defMachSlider').value, $('defAltSlider').value, $('aggrSlider').value, $('batteryCountSlider').value, $('salvoSpacingSlider').value, $('allowRetarget').checked?'1':'0'].join('|');
  if(previewKey===key && previewProjectile) return; previewKey=key;
  const p=new Projectile([from.lat,from.lon],[to.lat,to.lon],curMach,curAngle,curMode,{fromName:from.name,toName:to.name,cruiseAltMi,evasiveness,realistic:real,speedHold});
  let peak=p.alt, peakFrac=p.progress, guard=0; while(p.alive && guard<1000){ p.update(); if(p.alt>peak){ peak=p.alt; peakFrac=p.progress; } guard++; }
  p.previewPeakAlt=peak; p.previewPeakU=slerpUnit(p.fromU,p.toU,clamp(peakFrac,0,1)); previewProjectile=p;
  if(defense && $('interceptPolicy').value!=='off') previewSolution=planIntercept(new Projectile([from.lat,from.lon],[to.lat,to.lon],curMach,curAngle,curMode,{fromName:from.name,toName:to.name,cruiseAltMi,evasiveness,realistic:real,speedHold}), defense);
  updatePreviewSummary(from,to,defense,p,previewSolution);
}
function updatePreviewSummary(from,to,defense,p,sol){
  const eta=Math.max(0,p.getEtaSec()), etaTxt=eta>3600?(eta/3600).toFixed(1)+' h':(eta>60?Math.ceil(eta/60)+' min':Math.ceil(eta)+' s');
  $('previewNote').innerHTML='<b>LIVE PREVIEW</b><br>Attack route '+escapeHtml(shortPlaceName(from))+' → '+escapeHtml(shortPlaceName(to))+' • ETA <span style="color:#ffd48a">'+etaTxt+'</span> • peak altitude <span style="color:#ffd48a">'+((p.previewPeakAlt||0)*0.00062137119224).toFixed(1)+' mi</span>.';
  if(!defense || $('interceptPolicy').value==='off'){ interceptSummary.innerHTML='<b>PREDICTIVE WINDOW</b><br>Defense is off, so only the offensive arc is previewed.'; return; }
  if(!sol){ interceptSummary.innerHTML='<b>PREDICTIVE WINDOW</b><br>No intercept solution found from '+escapeHtml(shortPlaceName(defense))+'. Try higher interceptor Mach, lower delay, or a closer defense site.'; return; }
  const slack=(sol.available-sol.needed), state=slack>=0?'reachable':'stretched';
  interceptSummary.innerHTML='<b>PREDICTIVE WINDOW</b><br>Defense site <span style="color:#9ef4ff">'+escapeHtml(shortPlaceName(defense))+'</span> sees a <span style="color:'+(slack>=0?'#86ffbb':'#ff9d87')+'">'+state+'</span> solution.<br>Available time <span style="color:#ffd48a">'+sol.available.toFixed(1)+' s</span> • interceptor need <span style="color:#ffd48a">'+sol.needed.toFixed(1)+' s</span> • slack <span style="color:'+(slack>=0?'#86ffbb':'#ff9d87')+'">'+slack.toFixed(1)+' s</span><br>Surface leg <span style="color:#ffd48a">'+miles(sol.surface).toFixed(0)+' mi</span> • straight-line close <span style="color:#ffd48a">'+miles(sol.straight).toFixed(0)+' mi</span>.';
}

async function fireProjectile(){
  if(fireBusy) return; fireBusy=true; const btn=$('btnFire'), old=btn.textContent; btn.textContent='LOCATING...'; btn.disabled=true;
  try{
    const from=await resolvePlace(fromInput.value), to=await resolvePlace(toInput.value); if(Math.abs(from.lat-to.lat)<1e-7&&Math.abs(from.lon-to.lon)<1e-7) throw new Error('Launch and target resolve to the same coordinates.');
    const real=$('realisticMode').checked, speedHold=$('speedHold').checked; fromInput.value=from.name; toInput.value=to.name;
    const attack=new Projectile([from.lat,from.lon],[to.lat,to.lon],curMach,curAngle,curMode,{fromName:from.name,toName:to.name,cruiseAltMi,evasiveness,realistic:real,speedHold});
    projectiles.push(attack); shots++; shotCount.textContent=shots; syncResolvedBoxes(); markPreviewDirty();
    addLog(curMode.toUpperCase()+' '+shortPlaceName(from)+' → '+shortPlaceName(to)+' • '+gcDistMiles([from.lat,from.lon],[to.lat,to.lon]).toFixed(0)+' mi • Mach '+curMach.toFixed(1)+' • '+(real?'realistic':'compressed'), 'fire-entry');
    const hasNationalDefense = !!getArsenalForPlace(to.name);
    let defense = $('interceptPolicy').value==='auto-target' ? to : ($('interceptPolicy').value==='manual' ? await resolvePlace(interceptInput.value) : null);
    if(hasNationalDefense){
      activateNationalDefense({toVal:to.name, defSite:to, realistic:real, threats:projectiles.filter(function(p){return p && p.alive;}), silent:false});
    } else if(defense && $('interceptPolicy').value!=='off'){
      interceptInput.value=defense.name; const solution=planIntercept(attack, defense);
      const batteryCount=+$('batteryCountSlider').value, salvoSpacing=+$('salvoSpacingSlider').value;
      for(let b=0; b<batteryCount; b++){
        const delayBase=+$('delaySlider').value + b*salvoSpacing;
        const aggr=Math.min(1, +$('aggrSlider').value + b*0.04);
        const defDoctrine=getDoctrineForPlace(defense.name||to.name);
        const intc=new Interceptor([defense.lat,defense.lon], attack, {fromName:defense.name, delaySec:delayBase, cmdMach:+$('defMachSlider').value, altBiasMi:+$('defAltSlider').value + b*2, aggression:aggr, allowRetarget:$('allowRetarget').checked, realistic:real, solution, aimLL:solution&&solution.targetState?solution.targetState.ll:[to.lat,to.lon], aimAltM:solution&&solution.targetState?solution.targetState.alt:(+$('defAltSlider').value*1609.344), pkBase:clamp(0.42 + 0.34*aggr + 0.18*Math.min(1,(+$('defMachSlider').value)/16),0.12,0.93), sensorQuality:clamp(0.58 + 0.28*aggr + (solution?0.08:0),0.35,0.98), systemName:'Custom battery', tier:'custom', defenderCountry:defDoctrine.country, doctrine:defDoctrine.doctrine, salvoIndex:b, salvoCount:batteryCount, concurrentChannels:defDoctrine.doctrine.concurrentChannels, reloadElasticity:defDoctrine.doctrine.reloadElasticity,seekerType:'activeRadar',raidRole:(b===0?'primary':(b<2?'support':'screen'))});
        interceptors.push(intc);
      }
      if(solution){ const defDoctrine=getDoctrineForPlace(defense.name||to.name); addLog('DEFENSE '+shortPlaceName(defense)+' launched '+batteryCount+' battery'+(batteryCount>1?'ies':'')+' with best intercept at '+solution.targetState.t.toFixed(1)+' s attack-time and slack '+(solution.available-solution.needed).toFixed(1)+' s. Doctrine '+(doctrineScore(defDoctrine.doctrine)*100).toFixed(0)+'% • raid capacity '+defDoctrine.doctrine.raidCapacity+'.', (solution.available-solution.needed)>=0?'good-entry':'warn-entry'); }
      else addLog('DEFENSE '+shortPlaceName(defense)+' launched '+batteryCount+' interceptor attempt'+(batteryCount>1?'s':'')+' without a clean pre-solution. Terminal chase remains active.', 'warn-entry');
    }
  }catch(err){ addLog(err && err.message ? err.message : 'Could not resolve places.', 'warn-entry'); }
  finally{ fireBusy=false; btn.textContent=old; btn.disabled=false; }
}
$('btnFire').onclick=()=>fireProjectile();
$('btnClear').onclick=()=>{ projectiles=[]; interceptors=[]; previewProjectile=null; previewSolution=null; kills=0; killCount.textContent=kills; metrics.resolvedAttacks=0; metrics.leakedAttacks=0; metrics.interceptedAttacks=0; metrics.failedInterceptShots=0; metrics.successfulInterceptShots=0; metrics.livePkSamples=[]; metrics.doctrineSamples=[]; metrics.saturationSamples=[]; metrics.trackingSamples=[]; metrics.attackRecords=[]; metrics.failureTally={}; metrics.seekerUsage={}; addLog('All tracks cleared. Engagement memory reset.', 'info-entry'); markPreviewDirty(); updateEngagementPanel(); };
$('btnRandom').onclick=()=>{ const pool=PLACE_SEED.filter(p=>p.lat!=null&&(p.kind==='country'||p.kind==='capital city'||p.kind==='city'||p.kind==='town')).map(p=>p.name); const f=pool[Math.floor(Math.random()*pool.length)], t=pool[Math.floor(Math.random()*pool.length)]; fromInput.value=f; toInput.value=t===f?pool[(pool.indexOf(f)+7)%pool.length]:t; $('machSlider').value=(5+Math.random()*25).toFixed(1); $('angleSlider').value=(10+Math.floor(Math.random()*60)); $('machSlider').oninput(); $('angleSlider').oninput(); setMode(['ballistic','guided','cruise','evasive'][Math.floor(Math.random()*4)]); interceptInput.value=toInput.value; syncResolvedBoxes(); markPreviewDirty(); setTimeout(()=>fireProjectile(),60); };

function activeThreat(){ return projectiles.find(p=>p.alive) || previewProjectile || null; }
function activeDefense(){ return interceptors.find(i=>i.alive && i.launched) || null; }
function centerOnVec(vec){ if(!vec) return; for(let i=0;i<18;i++){ const pr=project(vec); const ex=(pr.x-CX)/Math.max(1,GLOBE_R), ey=(pr.y-CY)/Math.max(1,GLOBE_R); if(Math.abs(ex)<0.01&&Math.abs(ey)<0.01) break; rotY += clamp(ex,-1,1)*0.08; rotX = clamp(rotX - clamp(ey,-1,1)*0.08, -1.5, 1.5); } }
function syncRotateButton(){ $('btnRotate').textContent=autoRotate?'AUTO SPIN: ON':'AUTO SPIN: OFF'; $('btnRotate').classList.toggle('active',autoRotate); }
function syncFollowButton(){ $('btnFollow').textContent=followShot?'FOLLOW ACTIVE: ON':'FOLLOW ACTIVE: OFF'; $('btnFollow').classList.toggle('active',followShot); }
function nudgeCamera(dx=0,dy=0){ rotY += dx; rotX = clamp(rotX+dy,-1.5,1.5); }
function zoomBy(mult){ zoom=clamp(zoom*mult,0.75,1.75); resize(); }
$('btnRotate').onclick=()=>{ autoRotate=!autoRotate; syncRotateButton(); };
$('btnFollow').onclick=()=>{ followShot=!followShot; syncFollowButton(); };
$('btnCenterThreat').onclick=()=>{ const t=activeThreat(); if(t){ const vec=t.alive ? t.rEcef().scale(1/RE_M) : (t.impactPosU?t.impactPosU.clone():null); centerOnVec(vec); } };
$('btnCenterDefense').onclick=()=>{ const i=activeDefense(); if(i){ const vec=(i.alive&&i.rEcef)?i.rEcef().scale(1/RE_M):(i.impactPosU?i.impactPosU.clone():null); centerOnVec(vec); } };
$('camReset').onclick=()=>{ rotX=-0.23; rotY=0.55; zoom=1; resize(); };
$('camZoomIn').onclick=()=>zoomBy(1.08); $('camZoomOut').onclick=()=>zoomBy(0.92); $('camLeft').onclick=()=>nudgeCamera(+0.11,0); $('camRight').onclick=()=>nudgeCamera(-0.11,0); $('camUp').onclick=()=>nudgeCamera(0,-0.10); $('camDown').onclick=()=>nudgeCamera(0,+0.10); $('camCenter').onclick=()=>{ const t=activeThreat(); if(t) centerOnVec(t.alive?t.rEcef().scale(1/RE_M):(t.impactPosU?t.impactPosU.clone():null)); };
window.addEventListener('keydown',e=>{ if(e.target && /input|textarea|select/i.test(e.target.tagName)) return; if(e.key==='ArrowLeft'){e.preventDefault(); nudgeCamera(+0.07,0);} else if(e.key==='ArrowRight'){e.preventDefault(); nudgeCamera(-0.07,0);} else if(e.key==='ArrowUp'){e.preventDefault(); nudgeCamera(0,-0.07);} else if(e.key==='ArrowDown'){e.preventDefault(); nudgeCamera(0,+0.07);} else if(e.key==='='){e.preventDefault(); zoomBy(1.06);} else if(e.key==='-'){e.preventDefault(); zoomBy(0.94);} });
canvas.addEventListener('mousedown',e=>{ dragging=true; lastMX=e.clientX; lastMY=e.clientY; if(followShot){ followShot=false; syncFollowButton(); } });
canvas.addEventListener('mousemove',e=>{ if(!dragging) return; rotY -= (e.clientX-lastMX)*0.005; rotX = clamp(rotX-(e.clientY-lastMY)*0.005,-1.5,1.5); lastMX=e.clientX; lastMY=e.clientY; });
canvas.addEventListener('mouseup',()=>dragging=false); canvas.addEventListener('mouseleave',()=>dragging=false); canvas.addEventListener('wheel',e=>{ e.preventDefault(); zoom=clamp(zoom*(e.deltaY>0?0.92:1.08),0.75,1.55); resize(); },{passive:false});
window.addEventListener('resize',resize); window.addEventListener('load',()=>{ resize(); drawGlobe(); setTimeout(resize,100); updateEngagementPanel(); }); resize(); syncRotateButton(); syncFollowButton(); $('machSlider').oninput(); $('angleSlider').oninput(); $('evasionSlider').oninput(); $('delaySlider').oninput(); $('defMachSlider').oninput(); $('defAltSlider').oninput(); $('aggrSlider').oninput(); $('batteryCountSlider').oninput(); $('salvoSpacingSlider').oninput(); setMode(curMode); updateEngagementPanel();

function registerAttackOutcome(p){
  if(!p || p._outcomeRecorded) return;
  p._outcomeRecorded=true;
  metrics.resolvedAttacks++;
  if(p.intercepted) metrics.interceptedAttacks++; else metrics.leakedAttacks++;
  metrics.attackRecords.push({from:p.fromName||'',to:p.toName||'',intercepted:!!p.intercepted,mode:p.mode||'ballistic',mach:p.getMach?p.getMach():p.cmdMach||0,reason:p.destroyReason||''});
}
function registerInterceptorOutcome(i){
  if(!i || i._outcomeRecorded) return;
  i._outcomeRecorded=true;
  const sk=i.seekerType||'activeRadar';
  metrics.seekerUsage[sk]=(metrics.seekerUsage[sk]||0)+1;
  if(i.hit) metrics.successfulInterceptShots++;
  else if(i.missed || i.destroyReason){
    metrics.failedInterceptShots++;
    const fm=i.failureMode || i.destroyReason || 'miss';
    metrics.failureTally[fm]=(metrics.failureTally[fm]||0)+1;
  }
}
function drawEngagementChart(){
  if(!engagementChart) return;
  const c=engagementChart, x=c.getContext('2d');
  const w=c.width, h=c.height;
  x.clearRect(0,0,w,h);
  x.fillStyle='#05101a'; x.fillRect(0,0,w,h);
  for(let i=0;i<5;i++){ const y=18+i*(h-36)/4; x.strokeStyle='rgba(120,150,185,0.12)'; x.beginPath(); x.moveTo(46,y); x.lineTo(w-14,y); x.stroke(); }
  const totalAtt=Math.max(1,metrics.resolvedAttacks);
  const totalInt=Math.max(1,metrics.successfulInterceptShots+metrics.failedInterceptShots);
  const bars=[
    {label:'Attack through', value:metrics.leakedAttacks, total:totalAtt, color:'#ff8a63'},
    {label:'Intercepted', value:metrics.interceptedAttacks, total:totalAtt, color:'#59f0d2'},
    {label:'Int shot kill', value:metrics.successfulInterceptShots, total:totalInt, color:'#61b7ff'},
    {label:'Int shot miss', value:metrics.failedInterceptShots, total:totalInt, color:'#9ba8ba'}
  ];
  const maxV=Math.max(1,...bars.map(b=>b.value));
  const barW=94, gap=44, baseY=h-28, scale=(h-58)/maxV;
  bars.forEach((b,idx)=>{
    const x0=62+idx*(barW+gap), bh=Math.max(2,b.value*scale);
    x.fillStyle='rgba(255,255,255,0.05)'; x.fillRect(x0,24,barW,h-52);
    x.fillStyle=b.color; x.fillRect(x0,baseY-bh,barW,bh);
    x.fillStyle='#eaf4ff'; x.font='bold 14px ui-monospace, Menlo, monospace'; x.textAlign='center';
    x.fillText(String(b.value), x0+barW/2, baseY-bh-8);
    x.fillStyle='#8ea7bf'; x.font='10px ui-monospace, Menlo, monospace';
    x.fillText((100*b.value/Math.max(1,b.total)).toFixed(0)+'%', x0+barW/2, baseY+12);
    x.fillText(b.label, x0+barW/2, baseY+26);
  });
}
function updateEngagementPanel(){
  const attackSucc=metrics.resolvedAttacks?metrics.leakedAttacks/metrics.resolvedAttacks:0;
  const interceptSucc=metrics.resolvedAttacks?metrics.interceptedAttacks/metrics.resolvedAttacks:0;
  const livePk=safeMean(metrics.livePkSamples);
  const doctrineMean=safeMean(metrics.doctrineSamples);
  const saturationMean=safeMean(metrics.saturationSamples);
  attackSuccessRateEl.textContent=(attackSucc*100).toFixed(0)+'%';
  interceptSuccessRateEl.textContent=(interceptSucc*100).toFixed(0)+'%';
  avgPkLiveEl.textContent=(livePk*100).toFixed(0)+'%';
  engagementSummary.innerHTML='<b>ENGAGEMENT MEMORY</b><br>Resolved attacks <span style="color:#ffd48a">'+metrics.resolvedAttacks+'</span> • leakage <span style="color:#ff9d87">'+metrics.leakedAttacks+'</span> • intercepted <span style="color:#86ffbb">'+metrics.interceptedAttacks+'</span>.<br>Interceptor shots: kill <span style="color:#9ef4ff">'+metrics.successfulInterceptShots+'</span> / miss <span style="color:#c4cfdb">'+metrics.failedInterceptShots+'</span>.<br>Live modifiers: doctrine quality <span style="color:#9ef4ff">'+(doctrineMean*100).toFixed(0)+'%</span> • saturation relief <span style="color:#86ffbb">'+(saturationMean*100).toFixed(0)+'%</span>. P(hit) now blends kinematics, technology tier, country doctrine, and raid saturation.';
  drawEngagementChart();
}
function updateHud(){
  const atk=projectiles.find(p=>p.alive), def=interceptors.find(i=>i.alive);
  if(atk){
    const [lat,lon]=atk.getLatLon(), col=MODE_COLORS[atk.mode]||'#ff9955', eta=atk.getEtaSec(), etaTxt=eta>3600?(eta/3600).toFixed(1)+' h':(eta>60?Math.ceil(eta/60)+' min':Math.ceil(eta)+' s');
    const defTxt=def ? (def.launched ? ('ACTIVE • P(hit) '+(((def.pkNow||0))*100).toFixed(0)+'% • track '+(((def.trackingQuality||0))*100).toFixed(0)+'% • '+((def.seekerProfile&&def.seekerProfile.label)||def.seekerType||'seeker')+' • '+(def.raidRole||'primary')+' • sat '+(((def.saturationPenalty||1))*100).toFixed(0)+'%') : ('COUNTDOWN '+Math.max(0, def.launchDelay-def.timeSinceLaunch).toFixed(1)+' s')) : 'NONE';
    hud.innerHTML='<div class="status" style="color:'+col+'">ATTACK TRACK</div>'+
      'FROM <span class="val">'+escapeHtml(shortPlaceName({name:atk.fromName||''}))+'</span> → TO <span class="val">'+escapeHtml(shortPlaceName({name:atk.toName||''}))+'</span><br>'+
      'ALT <span class="val">'+(atk.alt*0.00062137119224).toFixed(1)+' mi</span> • MACH <span class="val">'+atk.getMach().toFixed(2)+'</span> • ETA <span class="val">'+etaTxt+'</span><br>'+
      'POS <span class="val">'+lat.toFixed(2)+'°, '+lon.toFixed(2)+'°</span> • RANGE <span class="val">'+(atk.distToTargetMeters()*0.00062137119224).toFixed(0)+' mi</span><br>'+
      'SIM <span class="val">'+(atk.realistic?'realistic':'compressed')+'</span> • DEFENSE <span class="'+(def?'ok':'warn')+'">'+defTxt+'</span>';
    hud.style.borderColor=col+'55';
    return;
  }
  if(previewProjectile){
    const eta=previewProjectile.getEtaSec(), etaTxt=eta>3600?(eta/3600).toFixed(1)+' h':(eta>60?Math.ceil(eta/60)+' min':Math.ceil(eta)+' s');
    hud.innerHTML='<div class="status" style="color:#9cc9ff">PREVIEW</div>Attack ETA <span class="val">'+etaTxt+'</span> • Peak altitude <span class="val">'+((previewProjectile.previewPeakAlt||0)*0.00062137119224).toFixed(1)+' mi</span><br>Defense preview '+(previewSolution?('<span class="'+((previewSolution.available-previewSolution.needed)>=0?'ok':'warn')+'">'+((previewSolution.available-previewSolution.needed)>=0?'reachable':'stretched')+'</span>'):'<span class="warn">none</span>')+'.';
    hud.style.borderColor='rgba(120,170,220,.3)';
    return;
  }
  hud.innerHTML='<div class="status" style="color:#7d8ea4">READY</div>Resolve launch, target, and defense site. Then fire.'; hud.style.borderColor='rgba(112,146,188,.16)';
}


function totalTrackLoad(){ return Math.max(1, projectiles.length + interceptors.length); }
function applyAdaptiveLoadLimits(){
  const load=totalTrackLoad();
  const pCap = load>80?34:(load>50?48:(load>28?72:(load>14?110:180)));
  const iCap = load>80?28:(load>50?42:(load>28?60:(load>14?96:160)));
  const pTrail = load>80?360:(load>50?520:(load>28?760:(load>14?980:1200)));
  const iTrail = load>80?280:(load>50?420:(load>28?620:(load>14?820:1000)));
  const trailEvery = load>80?6:(load>50?5:(load>28?4:3));
  for(const p of projectiles){
    if(!p) continue;
    p.stepsPerFrame=Math.min(p.stepsPerFrame||pCap,pCap);
    p.maxTrail=Math.min(p.maxTrail||pTrail,pTrail);
    p.trailEvery=Math.max(p.trailEvery||trailEvery,trailEvery);
    if(p.trail && p.trail.length>p.maxTrail) p.trail.splice(0,p.trail.length-p.maxTrail);
  }
  for(const i of interceptors){
    if(!i) continue;
    i.stepsPerFrame=Math.min(i.stepsPerFrame||iCap,iCap);
    i.maxTrail=Math.min(i.maxTrail||iTrail,iTrail);
    i.trailEvery=Math.max(i.trailEvery||trailEvery,trailEvery);
    if(i.trail && i.trail.length>i.maxTrail) i.trail.splice(0,i.trail.length-i.maxTrail);
  }
}
function safeUpdateTrack(obj, label){
  try{
    obj.update();
  }catch(err){
    if(obj){
      obj.alive=false;
      obj.destroyReason='runtime-fault';
      try{ obj.impactPosU = obj.currentU ? obj.currentU().clone() : (obj.currentPathU ? obj.currentPathU().clone() : null); }catch(_e){}
    }
    const msg=(err && err.message ? err.message : String(err));
    addLog((label||'TRACK')+' fault isolated: '+msg, 'warn-entry');
  }
}
window.addEventListener('error', function(ev){
  const msg = ev && ev.message ? ev.message : 'Unknown script error';
  addLog('SCRIPT ERROR: '+msg, 'warn-entry');
});

function loop(){
  requestAnimationFrame(loop);
  try{ if(previewDirty) rebuildPreview(); }catch(err){ addLog('PREVIEW fault recovered: '+(err && err.message ? err.message : String(err)), 'warn-entry'); }
  try{ if(CAMPAIGN_STATE.airDefenseAlwaysOn) autoDefenseSweep(); }catch(err){ addLog('DEFENSE SWEEP fault recovered: '+(err && err.message ? err.message : String(err)), 'warn-entry'); }
  try{ applyAdaptiveLoadLimits(); }catch(err){}
  try{ for(const p of projectiles) safeUpdateTrack(p,'ATTACK'); for(const i of interceptors) safeUpdateTrack(i,'INTERCEPTOR'); }catch(err){ addLog('TRACK fault recovered: '+(err && err.message ? err.message : String(err)), 'warn-entry'); }
  try{
    const liveInterceptors=interceptors.filter(i=>i.alive && i.launched);
    metrics.livePkSamples = liveInterceptors.filter(i=>i.pkNow!=null).slice(0,12).map(i=>i.pkNow);
    metrics.doctrineSamples = liveInterceptors.slice(0,12).map(i=>i.doctrineFactor||0);
    metrics.saturationSamples = liveInterceptors.slice(0,12).map(i=>i.saturationPenalty==null?1:i.saturationPenalty);
    const beforeKills=kills;
    kills = projectiles.filter(p=>p.intercepted).length;
    if(kills!==beforeKills) killCount.textContent=kills;
    const liveThreats=projectiles.filter(p=>p.alive).length;
    const liveDefense=interceptors.filter(i=>i.alive && i.launched).length;
    activeThreatCount.textContent=liveThreats;
    activeDefenseCount.textContent=liveDefense;
    projectiles = projectiles.filter(p=>{ if(p.alive) return true; if(p.impactPosU && p.impactAge<260){ p.impactAge++; return true; } return false; });
    interceptors = interceptors.filter(i=>{ if(i.alive) return true; if(i.impactPosU && i.impactAge<240){ i.impactAge++; return true; } return false; });
  }catch(err){ addLog('STATE fault recovered: '+(err && err.message ? err.message : String(err)), 'warn-entry'); }
  try{
    for(const p of projectiles){
      if(!p.alive && p.destroyReason && !loggedEvents.has('atk:'+p.age+':'+p.destroyReason+':'+p.fromName)){
        loggedEvents.add('atk:'+p.age+':'+p.destroyReason+':'+p.fromName);
        registerAttackOutcome(p);
      }
    }
    for(const i of interceptors){
      if(!i.alive && i.destroyReason && !loggedEvents.has('int:'+i.age+':'+i.destroyReason+':'+i.fromName)){
        loggedEvents.add('int:'+i.age+':'+i.destroyReason+':'+i.fromName);
        registerInterceptorOutcome(i);
      }
    }
  }catch(err){ addLog('OUTCOME fault recovered: '+(err && err.message ? err.message : String(err)), 'warn-entry'); }
  try{ updateEngagementPanel(); }catch(err){ addLog('PANEL fault recovered: '+(err && err.message ? err.message : String(err)), 'warn-entry'); }
  try{
    const tracked=projectiles.find(p=>p.alive) || interceptors.find(i=>i.alive&&i.launched);
    if(followShot && tracked){ const pr=project(tracked.rEcef().scale(1/RE_M)); const ex=(pr.x-CX)/Math.max(1,GLOBE_R), ey=(pr.y-CY)/Math.max(1,GLOBE_R); rotY += clamp(ex,-0.9,0.9)*0.028; rotX = clamp(rotX-clamp(ey,-0.9,0.9)*0.028, -1.5, 1.5); }
    else if(autoRotate && !dragging) rotY += 0.001;
  }catch(err){ addLog('CAMERA fault recovered: '+(err && err.message ? err.message : String(err)), 'warn-entry'); }
  try{ drawGlobe(); }catch(err){ addLog('GLOBE fault recovered: '+(err && err.message ? err.message : String(err)), 'warn-entry'); }
  try{ if(!projectiles.some(p=>p.alive)) drawPreviewShot(previewProjectile, previewSolution); }catch(err){}
  try{ drawAllShots(); }catch(err){ addLog('SHOT DRAW fault recovered: '+(err && err.message ? err.message : String(err)), 'warn-entry'); }
  try{ updateHud(); }catch(err){ addLog('HUD fault recovered: '+(err && err.message ? err.message : String(err)), 'warn-entry'); }
}

/* ═══════════════════════════════════════════════════════
   V4 ADDITIONS — injected before loop(); 
   RULE: This block only ADDS new code. It does NOT
   modify drawGlobe, loop, resize, or init order.
   ═══════════════════════════════════════════════════════ */

/* ── V4 Physics ── */
const J2_C=1.08263e-3,WGS84_AR=6378137;
function usAtmo76(alt){alt=Math.max(0,alt);var T,P,rho;if(alt<=11000){T=288.15-0.0065*alt;P=101325*Math.pow(T/288.15,5.2559);rho=P/(R_AIR*T);}else if(alt<=20000){T=216.65;P=22632.1*Math.exp(-0.00015769*(alt-11000));rho=P/(R_AIR*T);}else if(alt<=32000){T=216.65+0.001*(alt-20000);P=5474.89*Math.pow(216.65/T,34.1632);rho=P/(R_AIR*T);}else if(alt<=47000){T=228.65+0.0028*(alt-32000);P=868.019*Math.pow(228.65/T,12.2009);rho=P/(R_AIR*T);}else if(alt<=51000){T=270.65;P=110.906*Math.exp(-0.00012622*(alt-47000));rho=P/(R_AIR*T);}else if(alt<=71000){T=270.65-0.0028*(alt-51000);P=66.9389*Math.pow(270.65/T,-12.2009);rho=P/(R_AIR*T);}else if(alt<=86000){T=214.65-0.002*(alt-71000);P=3.95642*Math.pow(214.65/T,-17.0816);rho=P/(R_AIR*T);}else{T=186.87;P=Math.max(0,0.3734*Math.exp(-0.00012622*(alt-86000)));rho=Math.max(0,P/(R_AIR*Math.max(150,T)));}return{T:T,P:P,rho:Math.max(0,rho),a:Math.sqrt(GAMMA*R_AIR*Math.max(150,T))};}
function dragCd(m){m=Math.abs(m);if(m<0.6)return 0.2;if(m<0.9)return 0.2+0.65*(m-0.6)/0.3;if(m<1.2)return 0.85+0.35*Math.sin(Math.PI*(m-0.9)/0.6);if(m<3)return 1-0.3*(m-1.2)/1.8;if(m<8)return 0.7-0.22*(m-3)/5;return Math.max(0.15,0.48-0.015*(m-8));}
function gravJ2(alt,latR){var r=RE_M+alt,r2=r*r,f=1.5*J2_C*WGS84_AR*WGS84_AR/r2,s=Math.sin(latR||0);return MU/r2*(1+f*(1-5*s*s));}
function stagnHeat(rho,v){return 1.7415e-4*Math.sqrt(Math.max(0,rho)/0.3)*Math.pow(Math.abs(v),3)/1e4;}

/* ── Monkey-patch Projectile for v4 telemetry + physics ── */
(function(){
  var origUpdate = Projectile.prototype.updateScalarStep;
  Projectile.prototype.updateScalarStep = function(){
    // Initialize telemetry fields if missing
    if(this._v4init===undefined){
      this._v4init=true; this.flightPhase=0; this.boostDuration=clamp(60+this.cmdMach*3,30,320);
      this.lastCd=0;this.lastDragN=0;this.lastGrav=0;this.lastJ2dg=0;
      this.lastRho=0;this.lastTemp=0;this.lastSoS=0;this.lastHeatFlux=0;
    }
    // Run original v3 physics (guaranteed to work)
    origUpdate.call(this);
    // THEN compute v4 telemetry overlays (non-destructive)
    try{
      var atmo=usAtmo76(this.alt), ll=this.getLatLon();
      var g=gravJ2(this.alt, ll[0]*RAD);
      var cd=dragCd(this.getAirspeed()/Math.max(1,atmo.a));
      this.lastCd=cd; this.lastDragN=0.5*cd*0.5*atmo.rho*this.alongSpeed*this.alongSpeed;
      this.lastGrav=g; this.lastJ2dg=g-MU/Math.pow(RE_M+this.alt,2);
      this.lastRho=atmo.rho; this.lastTemp=atmo.T; this.lastSoS=atmo.a;
      if(this.alt<120000&&this.alt>10000&&this.vertSpeed<-100) this.lastHeatFlux=stagnHeat(atmo.rho,this.getAirspeed()); else this.lastHeatFlux=0;
      if(this.mode!=='ballistic'){this.flightPhase=this.progress>=0.85?2:(this.progress>=0.08?1:0);}
      else{if(this.t<this.boostDuration)this.flightPhase=0;else if(this.alt>80000&&this.progress<0.85)this.flightPhase=1;else this.flightPhase=2;}
    }catch(e){}
  };
})();

/* ── Monkey-patch updateHud for v4 telemetry display ── */
var _origUpdateHud = updateHud;
updateHud = function(){
  _origUpdateHud();
  try{
    var atk=projectiles.find(function(p){return p.alive;});
    if(atk && atk._v4init){
      $('ptDrag').textContent='Cd '+atk.lastCd.toFixed(3)+' \u00b7 Drag '+(atk.lastDragN/1000).toFixed(1)+' kN';
      $('ptGrav').textContent='g '+atk.lastGrav.toFixed(3)+' m/s\u00b2 \u00b7 J2 \u0394g '+(atk.lastJ2dg*1e3).toFixed(3)+' mm/s\u00b2';
      $('ptAtmo').textContent='\u03c1 '+atk.lastRho.toExponential(2)+' \u00b7 T '+atk.lastTemp.toFixed(0)+'K \u00b7 a '+atk.lastSoS.toFixed(0)+' m/s';
      $('ptHeat').textContent='q\u0307 '+atk.lastHeatFlux.toFixed(1)+' W/cm\u00b2';
    }
  }catch(e){}
};

/* ── Arsenal Database ── */
var ARSENAL_COUNTRIES=['United States','Russia','China','India','United Kingdom','France','South Korea','Japan','Pakistan','Turkey','Italy','Germany','Israel','Australia','Iran','Saudi Arabia','Egypt','North Korea','Taiwan','Poland'];
var ARSENAL={'United States':{flag:'\u{1F1FA}\u{1F1F8}',offense:[{name:'Minuteman III',type:'ICBM',mach:23,range:13000,altKm:1120,mode:'ballistic',angle:78,evasion:0.05,cep:200,desc:'Silo ICBM, 3 MIRV, 13,000 km'},{name:'Trident II D5',type:'SLBM',mach:24,range:12000,altKm:1000,mode:'ballistic',angle:75,evasion:0.05,cep:90,desc:'Sub-launched, 14 MIRV, CEP 90m'},{name:'Tomahawk Blk V',type:'Cruise',mach:0.75,range:2500,altKm:0.05,mode:'cruise',angle:3,evasion:0.15,cep:5,desc:'Subsonic terrain-following cruise'},{name:'AGM-183A ARRW',type:'Hypersonic',mach:17,range:1600,altKm:80,mode:'guided',angle:38,evasion:0.55,cep:10,desc:'Air-launched boost-glide'},{name:'PrSM',type:'Tactical',mach:5,range:500,altKm:50,mode:'guided',angle:45,evasion:0.4,cep:5,desc:'Precision Strike Missile'}],defense:[{name:'GBI',tier:'exo',mach:24,altMi:1240,altMinMi:60,range:2000,delay:45,batteries:1,aggr:0.9,killR:20000,pk:0.56},{name:'THAAD',tier:'high-endo',mach:8.24,altMi:93,altMinMi:9,range:200,delay:18,batteries:2,aggr:0.8,killR:15000,pk:0.9},{name:'SM-3 Blk IIA',tier:'exo',mach:15.25,altMi:310,altMinMi:30,range:700,delay:25,batteries:2,aggr:0.85,killR:18000,pk:0.7},{name:'Patriot PAC-3 MSE',tier:'point',mach:4.1,altMi:20,altMinMi:0.06,range:35,delay:8,batteries:4,aggr:0.75,killR:8000,pk:0.85}]},'Russia':{flag:'\u{1F1F7}\u{1F1FA}',offense:[{name:'RS-28 Sarmat',type:'ICBM',mach:25,range:18000,altKm:1500,mode:'ballistic',angle:80,evasion:0.08,cep:150,desc:'Heavy ICBM, 10-15 MIRV, 208t'},{name:'Yars RS-24',type:'ICBM',mach:22,range:12000,altKm:1000,mode:'ballistic',angle:76,evasion:0.1,cep:150,desc:'Road-mobile MIRV ICBM'},{name:'Iskander-M',type:'SRBM',mach:6.5,range:500,altKm:50,mode:'evasive',angle:55,evasion:0.75,cep:5,desc:'Quasi-ballistic, terminal evasion'},{name:'Kalibr 3M-14',type:'Cruise',mach:0.8,range:2500,altKm:0.02,mode:'cruise',angle:3,evasion:0.15,cep:3,desc:'Sea-launched subsonic LACM'},{name:'Kh-101',type:'Cruise',mach:0.78,range:5500,altKm:0.06,mode:'cruise',angle:4,evasion:0.15,cep:7,desc:'Air-launched stealth cruise, 5500 km'},{name:'Kinzhal',type:'Hypersonic',mach:10,range:2000,altKm:80,mode:'guided',angle:42,evasion:0.65,cep:1,desc:'Aeroballistic hypersonic'},{name:'Avangard',type:'HGV',mach:27,range:6000,altKm:100,mode:'evasive',angle:30,evasion:0.95,cep:10,desc:'HGV, extreme maneuver'},{name:'Zircon',type:'Hypersonic',mach:9,range:1000,altKm:40,mode:'guided',angle:35,evasion:0.6,cep:1,desc:'Scramjet anti-ship'}],defense:[{name:'A-235 Nudol',tier:'exo',mach:18,altMi:500,altMinMi:30,range:900,delay:35,batteries:1,aggr:0.85,killR:25000,pk:0.6},{name:'S-500',tier:'exo',mach:16,altMi:370,altMinMi:16,range:600,delay:20,batteries:1,aggr:0.9,killR:22000,pk:0.75},{name:'S-400',tier:'high-endo',mach:11.3,altMi:19,altMinMi:0.03,range:400,delay:12,batteries:3,aggr:0.8,killR:15000,pk:0.82},{name:'S-350',tier:'endo',mach:9,altMi:18,altMinMi:0.01,range:120,delay:8,batteries:3,aggr:0.7,killR:12000,pk:0.75},{name:'Pantsir-S1',tier:'point',mach:3.8,altMi:9,altMinMi:0,range:20,delay:5,batteries:6,aggr:0.65,killR:5000,pk:0.7}]},'China':{flag:'\u{1F1E8}\u{1F1F3}',offense:[{name:'DF-41',type:'ICBM',mach:25,range:15000,altKm:1200,mode:'ballistic',angle:78,evasion:0.1,cep:100,desc:'Road-mobile, 10 MIRV'},{name:'DF-26',type:'IRBM',mach:18,range:5000,altKm:500,mode:'guided',angle:60,evasion:0.4,cep:150,desc:'Carrier-killer, maneuvering RV'},{name:'DF-17',type:'HGV',mach:10,range:2500,altKm:60,mode:'evasive',angle:32,evasion:0.85,cep:10,desc:'HGV skip-glide'},{name:'CJ-20',type:'Cruise',mach:0.75,range:2200,altKm:0.05,mode:'cruise',angle:3,evasion:0.12,cep:10,desc:'Ground LACM'},{name:'YJ-21',type:'Hypersonic',mach:10,range:1500,altKm:45,mode:'guided',angle:38,evasion:0.6,cep:5,desc:'Ship-launched hypersonic'}],defense:[{name:'HQ-19',tier:'exo',mach:15,altMi:310,altMinMi:25,range:600,delay:25,batteries:1,aggr:0.85,killR:20000,pk:0.65},{name:'HQ-9B',tier:'endo',mach:6,altMi:18,altMinMi:0.02,range:300,delay:10,batteries:3,aggr:0.75,killR:13000,pk:0.8},{name:'S-400',tier:'high-endo',mach:11.3,altMi:19,altMinMi:0.03,range:400,delay:12,batteries:2,aggr:0.8,killR:15000,pk:0.82}]},'India':{flag:'\u{1F1EE}\u{1F1F3}',offense:[{name:'Agni-V',type:'ICBM',mach:20,range:8000,altKm:800,mode:'ballistic',angle:70,evasion:0.1,cep:100,desc:'Road-mobile, 8000 km'},{name:'BrahMos',type:'Cruise',mach:2.8,range:800,altKm:14,mode:'cruise',angle:10,evasion:0.35,cep:1,desc:'Supersonic cruise'},{name:'K-4 SLBM',type:'SLBM',mach:18,range:3500,altKm:600,mode:'ballistic',angle:68,evasion:0.08,cep:50,desc:'Sub-launched'}],defense:[{name:'S-400',tier:'high-endo',mach:11.3,altMi:19,altMinMi:0.03,range:400,delay:12,batteries:3,aggr:0.8,killR:15000,pk:0.82},{name:'PDV',tier:'exo',mach:12,altMi:93,altMinMi:30,range:600,delay:25,batteries:1,aggr:0.8,killR:18000,pk:0.5},{name:'Akash NG',tier:'point',mach:3.5,altMi:12,altMinMi:0.02,range:60,delay:6,batteries:4,aggr:0.7,killR:8000,pk:0.7}]},'United Kingdom':{flag:'\u{1F1EC}\u{1F1E7}',offense:[{name:'Trident II D5',type:'SLBM',mach:24,range:12000,altKm:1000,mode:'ballistic',angle:75,evasion:0.05,cep:90,desc:'Continuous deterrent'},{name:'Storm Shadow',type:'Cruise',mach:0.8,range:560,altKm:0.04,mode:'cruise',angle:4,evasion:0.15,cep:3,desc:'Stealth cruise'}],defense:[{name:'Sea Viper',tier:'endo',mach:4.5,altMi:15,altMinMi:0.01,range:120,delay:8,batteries:3,aggr:0.75,killR:10000,pk:0.8},{name:'Sky Sabre',tier:'point',mach:3,altMi:9,altMinMi:0,range:45,delay:5,batteries:4,aggr:0.7,killR:6000,pk:0.85}]},'France':{flag:'\u{1F1EB}\u{1F1F7}',offense:[{name:'M51.2 SLBM',type:'SLBM',mach:25,range:10000,altKm:1000,mode:'ballistic',angle:76,evasion:0.08,cep:100,desc:'6-10 MIRV sub-launched'},{name:'SCALP-EG',type:'Cruise',mach:0.8,range:560,altKm:0.04,mode:'cruise',angle:4,evasion:0.15,cep:3,desc:'Air stealth cruise'}],defense:[{name:'SAMP/T Aster 30',tier:'endo',mach:4.5,altMi:15,altMinMi:0.01,range:120,delay:8,batteries:3,aggr:0.75,killR:10000,pk:0.8},{name:'Crotale NG',tier:'point',mach:2.5,altMi:5,altMinMi:0,range:10,delay:4,batteries:5,aggr:0.65,killR:4000,pk:0.7}]},'South Korea':{flag:'\u{1F1F0}\u{1F1F7}',offense:[{name:'Hyunmoo-5',type:'Ballistic',mach:12,range:3000,altKm:400,mode:'ballistic',angle:65,evasion:0.15,cep:5,desc:'9t bunker buster'},{name:'Hyunmoo-3C',type:'Cruise',mach:0.8,range:1500,altKm:0.05,mode:'cruise',angle:3,evasion:0.12,cep:3,desc:'LACM 1500 km'}],defense:[{name:'L-SAM',tier:'high-endo',mach:8,altMi:37,altMinMi:3,range:150,delay:15,batteries:2,aggr:0.8,killR:15000,pk:0.75},{name:'Patriot PAC-3',tier:'endo',mach:4.1,altMi:20,altMinMi:0.06,range:35,delay:8,batteries:3,aggr:0.75,killR:8000,pk:0.85},{name:'KM-SAM',tier:'point',mach:4.5,altMi:12,altMinMi:0.01,range:40,delay:6,batteries:4,aggr:0.7,killR:9000,pk:0.78}]},'Japan':{flag:'\u{1F1EF}\u{1F1F5}',offense:[{name:'Type 12 Blk III',type:'Cruise',mach:0.9,range:1500,altKm:0.04,mode:'cruise',angle:3,evasion:0.15,cep:5,desc:'Extended-range cruise'}],defense:[{name:'SM-3 Blk IIA',tier:'exo',mach:15.25,altMi:310,altMinMi:30,range:700,delay:25,batteries:2,aggr:0.85,killR:18000,pk:0.7},{name:'Patriot PAC-3',tier:'endo',mach:4.1,altMi:20,altMinMi:0.06,range:35,delay:8,batteries:4,aggr:0.75,killR:8000,pk:0.85}]},'Pakistan':{flag:'\u{1F1F5}\u{1F1F0}',offense:[{name:'Shaheen-III',type:'MRBM',mach:14,range:2750,altKm:500,mode:'ballistic',angle:65,evasion:0.1,cep:50,desc:'Solid nuclear 2750 km'},{name:'Babur-3',type:'Cruise',mach:0.7,range:700,altKm:0.03,mode:'cruise',angle:3,evasion:0.12,cep:5,desc:'Sub LACM'}],defense:[{name:'HQ-9/P',tier:'endo',mach:6,altMi:18,altMinMi:0.02,range:200,delay:12,batteries:2,aggr:0.7,killR:13000,pk:0.7}]},'Turkey':{flag:'\u{1F1F9}\u{1F1F7}',offense:[{name:'Tayfun',type:'SRBM',mach:6,range:600,altKm:50,mode:'guided',angle:50,evasion:0.35,cep:10,desc:'Quasi-ballistic'}],defense:[{name:'S-400',tier:'high-endo',mach:11.3,altMi:19,altMinMi:0.03,range:400,delay:12,batteries:1,aggr:0.8,killR:15000,pk:0.82},{name:'HISAR-O+',tier:'point',mach:3.5,altMi:9,altMinMi:0,range:25,delay:6,batteries:4,aggr:0.7,killR:7000,pk:0.7}]},'Italy':{flag:'\u{1F1EE}\u{1F1F9}',offense:[{name:'Storm Shadow',type:'Cruise',mach:0.8,range:560,altKm:0.04,mode:'cruise',angle:4,evasion:0.15,cep:3,desc:'Air stealth cruise'}],defense:[{name:'SAMP/T',tier:'endo',mach:4.5,altMi:15,altMinMi:0.01,range:120,delay:8,batteries:2,aggr:0.75,killR:10000,pk:0.8}]},'Germany':{flag:'\u{1F1E9}\u{1F1EA}',offense:[{name:'Taurus KEPD 350',type:'Cruise',mach:0.9,range:500,altKm:0.04,mode:'cruise',angle:4,evasion:0.15,cep:2,desc:'Bunker buster cruise'}],defense:[{name:'Patriot PAC-3',tier:'endo',mach:4.1,altMi:20,altMinMi:0.06,range:35,delay:8,batteries:3,aggr:0.75,killR:8000,pk:0.85},{name:'IRIS-T SLM',tier:'point',mach:3,altMi:8,altMinMi:0,range:40,delay:5,batteries:4,aggr:0.7,killR:6000,pk:0.82}]},'Israel':{flag:'\u{1F1EE}\u{1F1F1}',offense:[{name:'Jericho III',type:'ICBM',mach:20,range:6500,altKm:800,mode:'ballistic',angle:72,evasion:0.1,cep:100,desc:'Nuclear deterrent'},{name:'LORA',type:'SRBM',mach:4,range:400,altKm:50,mode:'guided',angle:48,evasion:0.3,cep:10,desc:'Quasi-ballistic precision'},{name:'Delilah',type:'Cruise',mach:0.7,range:300,altKm:0.03,mode:'cruise',angle:3,evasion:0.2,cep:1,desc:'Loitering munition'}],defense:[{name:'Arrow 3',tier:'exo',mach:14,altMi:62,altMinMi:25,range:400,delay:15,batteries:2,aggr:0.9,killR:20000,pk:0.85},{name:'Arrow 2',tier:'high-endo',mach:9,altMi:30,altMinMi:5,range:150,delay:12,batteries:2,aggr:0.8,killR:15000,pk:0.8},{name:'Davids Sling',tier:'endo',mach:7.5,altMi:15,altMinMi:0.5,range:160,delay:8,batteries:3,aggr:0.85,killR:10000,pk:0.85},{name:'Iron Dome',tier:'point',mach:2.2,altMi:6,altMinMi:0,range:70,delay:3,batteries:10,aggr:0.7,killR:4000,pk:0.9}]},'Australia':{flag:'\u{1F1E6}\u{1F1FA}',offense:[{name:'Tomahawk',type:'Cruise',mach:0.75,range:2500,altKm:0.05,mode:'cruise',angle:3,evasion:0.15,cep:5,desc:'Ship LACM'},{name:'LRASM',type:'Anti-Ship',mach:0.9,range:930,altKm:0.01,mode:'cruise',angle:2,evasion:0.2,cep:1,desc:'Stealthy anti-ship'}],defense:[{name:'SM-2 Aegis',tier:'endo',mach:3.5,altMi:15,altMinMi:0.01,range:170,delay:10,batteries:2,aggr:0.7,killR:10000,pk:0.75},{name:'NASAMS',tier:'point',mach:3,altMi:8,altMinMi:0,range:30,delay:5,batteries:3,aggr:0.65,killR:6000,pk:0.78}]},'Iran':{flag:'\u{1F1EE}\u{1F1F7}',offense:[{name:'Sejjil-2',type:'MRBM',mach:14,range:2500,altKm:450,mode:'ballistic',angle:65,evasion:0.1,cep:300,desc:'Solid 2-stage 2500 km'},{name:'Fattah-2',type:'HGV',mach:15,range:1400,altKm:100,mode:'evasive',angle:35,evasion:0.7,cep:30,desc:'HGV maneuvering'},{name:'Paveh',type:'Cruise',mach:0.7,range:1650,altKm:0.04,mode:'cruise',angle:3,evasion:0.1,cep:15,desc:'LACM'}],defense:[{name:'Bavar-373',tier:'endo',mach:8,altMi:18,altMinMi:0.02,range:300,delay:12,batteries:2,aggr:0.75,killR:14000,pk:0.65},{name:'Sayyad-4C',tier:'endo',mach:5,altMi:15,altMinMi:0.01,range:150,delay:8,batteries:3,aggr:0.7,killR:10000,pk:0.6}]},'Saudi Arabia':{flag:'\u{1F1F8}\u{1F1E6}',offense:[{name:'DF-3A',type:'IRBM',mach:10,range:2800,altKm:400,mode:'ballistic',angle:60,evasion:0.05,cep:1000,desc:'Chinese liquid IRBM'}],defense:[{name:'THAAD',tier:'high-endo',mach:8.24,altMi:93,altMinMi:9,range:200,delay:18,batteries:1,aggr:0.8,killR:15000,pk:0.9},{name:'Patriot PAC-3',tier:'point',mach:4.1,altMi:20,altMinMi:0.06,range:35,delay:8,batteries:3,aggr:0.75,killR:8000,pk:0.85}]},'Egypt':{flag:'\u{1F1EA}\u{1F1EC}',offense:[{name:'Scud-C',type:'SRBM',mach:5,range:600,altKm:80,mode:'ballistic',angle:50,evasion:0.02,cep:700,desc:'Soviet-era, inaccurate'}],defense:[{name:'S-300VM',tier:'endo',mach:9,altMi:18,altMinMi:0.01,range:200,delay:12,batteries:2,aggr:0.75,killR:14000,pk:0.75},{name:'Buk-M2',tier:'point',mach:4,altMi:12,altMinMi:0,range:50,delay:6,batteries:3,aggr:0.7,killR:8000,pk:0.72}]},'North Korea':{flag:'\u{1F1F0}\u{1F1F5}',offense:[{name:'Hwasong-17',type:'ICBM',mach:24,range:15000,altKm:1300,mode:'ballistic',angle:80,evasion:0.05,cep:1500,desc:'Largest road-mobile ICBM'},{name:'Hwasong-15',type:'ICBM',mach:22,range:13000,altKm:1100,mode:'ballistic',angle:78,evasion:0.05,cep:2000,desc:'Full ICBM range'},{name:'KN-23',type:'SRBM',mach:6,range:600,altKm:50,mode:'evasive',angle:42,evasion:0.6,cep:30,desc:'Iskander-style evasion'}],defense:[{name:'KN-06',tier:'endo',mach:5,altMi:12,altMinMi:0.02,range:150,delay:12,batteries:2,aggr:0.65,killR:10000,pk:0.5}]},'Taiwan':{flag:'\u{1F1F9}\u{1F1FC}',offense:[{name:'Yun Feng',type:'Cruise',mach:3,range:2000,altKm:20,mode:'guided',angle:15,evasion:0.3,cep:10,desc:'Supersonic LACM'},{name:'HF-IIE',type:'Cruise',mach:0.85,range:600,altKm:0.04,mode:'cruise',angle:3,evasion:0.12,cep:5,desc:'Subsonic LACM'}],defense:[{name:'Sky Bow III',tier:'high-endo',mach:7,altMi:28,altMinMi:2,range:200,delay:10,batteries:3,aggr:0.8,killR:14000,pk:0.8},{name:'Patriot PAC-3',tier:'endo',mach:4.1,altMi:20,altMinMi:0.06,range:35,delay:8,batteries:3,aggr:0.75,killR:8000,pk:0.85}]},'Poland':{flag:'\u{1F1F5}\u{1F1F1}',offense:[{name:'ATACMS',type:'Tactical',mach:3,range:300,altKm:30,mode:'guided',angle:45,evasion:0.1,cep:10,desc:'Tactical ballistic'}],defense:[{name:'Patriot PAC-3',tier:'endo',mach:4.1,altMi:20,altMinMi:0.06,range:35,delay:8,batteries:4,aggr:0.75,killR:8000,pk:0.85},{name:'CAMM-ER',tier:'point',mach:3,altMi:8,altMinMi:0,range:25,delay:4,batteries:6,aggr:0.7,killR:6000,pk:0.82}]}};


var DOCTRINE_DB={
  'United States':{c2:0.96,sensorFusion:0.95,training:0.93,maintenance:0.92,shotDiscipline:0.92,raidCapacity:7,raidCapacityNorm:0.95,concurrentChannels:8,reloadElasticity:0.9},
  'Russia':{c2:0.82,sensorFusion:0.80,training:0.78,maintenance:0.72,shotDiscipline:0.76,raidCapacity:5,raidCapacityNorm:0.78,concurrentChannels:5,reloadElasticity:0.72},
  'China':{c2:0.90,sensorFusion:0.89,training:0.86,maintenance:0.86,shotDiscipline:0.86,raidCapacity:6,raidCapacityNorm:0.88,concurrentChannels:7,reloadElasticity:0.85},
  'India':{c2:0.78,sensorFusion:0.76,training:0.75,maintenance:0.72,shotDiscipline:0.74,raidCapacity:4,raidCapacityNorm:0.72,concurrentChannels:4,reloadElasticity:0.72},
  'United Kingdom':{c2:0.91,sensorFusion:0.90,training:0.89,maintenance:0.88,shotDiscipline:0.88,raidCapacity:5,raidCapacityNorm:0.86,concurrentChannels:6,reloadElasticity:0.84},
  'France':{c2:0.88,sensorFusion:0.87,training:0.86,maintenance:0.85,shotDiscipline:0.85,raidCapacity:5,raidCapacityNorm:0.84,concurrentChannels:6,reloadElasticity:0.83},
  'South Korea':{c2:0.89,sensorFusion:0.88,training:0.87,maintenance:0.86,shotDiscipline:0.86,raidCapacity:6,raidCapacityNorm:0.87,concurrentChannels:7,reloadElasticity:0.86},
  'Japan':{c2:0.92,sensorFusion:0.92,training:0.90,maintenance:0.90,shotDiscipline:0.90,raidCapacity:6,raidCapacityNorm:0.90,concurrentChannels:7,reloadElasticity:0.88},
  'Pakistan':{c2:0.68,sensorFusion:0.66,training:0.67,maintenance:0.63,shotDiscipline:0.65,raidCapacity:3,raidCapacityNorm:0.58,concurrentChannels:3,reloadElasticity:0.60},
  'Turkey':{c2:0.74,sensorFusion:0.72,training:0.72,maintenance:0.70,shotDiscipline:0.72,raidCapacity:4,raidCapacityNorm:0.66,concurrentChannels:4,reloadElasticity:0.68},
  'Italy':{c2:0.84,sensorFusion:0.83,training:0.82,maintenance:0.82,shotDiscipline:0.82,raidCapacity:4,raidCapacityNorm:0.78,concurrentChannels:5,reloadElasticity:0.78},
  'Germany':{c2:0.87,sensorFusion:0.86,training:0.85,maintenance:0.84,shotDiscipline:0.85,raidCapacity:5,raidCapacityNorm:0.82,concurrentChannels:6,reloadElasticity:0.80},
  'Israel':{c2:0.97,sensorFusion:0.97,training:0.95,maintenance:0.93,shotDiscipline:0.94,raidCapacity:9,raidCapacityNorm:1.0,concurrentChannels:10,reloadElasticity:0.95},
  'Australia':{c2:0.84,sensorFusion:0.83,training:0.82,maintenance:0.81,shotDiscipline:0.82,raidCapacity:4,raidCapacityNorm:0.76,concurrentChannels:5,reloadElasticity:0.78},
  'Iran':{c2:0.66,sensorFusion:0.62,training:0.64,maintenance:0.58,shotDiscipline:0.60,raidCapacity:3,raidCapacityNorm:0.54,concurrentChannels:3,reloadElasticity:0.55},
  'Saudi Arabia':{c2:0.76,sensorFusion:0.78,training:0.72,maintenance:0.74,shotDiscipline:0.70,raidCapacity:4,raidCapacityNorm:0.68,concurrentChannels:4,reloadElasticity:0.68},
  'Egypt':{c2:0.68,sensorFusion:0.66,training:0.66,maintenance:0.63,shotDiscipline:0.64,raidCapacity:3,raidCapacityNorm:0.56,concurrentChannels:3,reloadElasticity:0.58},
  'North Korea':{c2:0.54,sensorFusion:0.48,training:0.50,maintenance:0.42,shotDiscipline:0.46,raidCapacity:2,raidCapacityNorm:0.42,concurrentChannels:2,reloadElasticity:0.42},
  'Taiwan':{c2:0.88,sensorFusion:0.89,training:0.87,maintenance:0.84,shotDiscipline:0.86,raidCapacity:6,raidCapacityNorm:0.86,concurrentChannels:7,reloadElasticity:0.84},
  'Poland':{c2:0.82,sensorFusion:0.81,training:0.80,maintenance:0.79,shotDiscipline:0.79,raidCapacity:5,raidCapacityNorm:0.78,concurrentChannels:5,reloadElasticity:0.77},
  'Default':{c2:0.78,sensorFusion:0.76,training:0.75,maintenance:0.74,shotDiscipline:0.74,raidCapacity:4,raidCapacityNorm:0.70,concurrentChannels:4,reloadElasticity:0.70}
};

var ALL_COUNTRY_META=[{"name": "Aruba", "alpha2": "AW", "flag": "🇦🇼"}, {"name": "Afghanistan", "alpha2": "AF", "flag": "🇦🇫"}, {"name": "Angola", "alpha2": "AO", "flag": "🇦🇴"}, {"name": "Anguilla", "alpha2": "AI", "flag": "🇦🇮"}, {"name": "Åland Islands", "alpha2": "AX", "flag": "🇦🇽"}, {"name": "Albania", "alpha2": "AL", "flag": "🇦🇱"}, {"name": "Andorra", "alpha2": "AD", "flag": "🇦🇩"}, {"name": "United Arab Emirates", "alpha2": "AE", "flag": "🇦🇪"}, {"name": "Argentina", "alpha2": "AR", "flag": "🇦🇷"}, {"name": "Armenia", "alpha2": "AM", "flag": "🇦🇲"}, {"name": "American Samoa", "alpha2": "AS", "flag": "🇦🇸"}, {"name": "Antarctica", "alpha2": "AQ", "flag": "🇦🇶"}, {"name": "French Southern Territories", "alpha2": "TF", "flag": "🇹🇫"}, {"name": "Antigua and Barbuda", "alpha2": "AG", "flag": "🇦🇬"}, {"name": "Australia", "alpha2": "AU", "flag": "🇦🇺"}, {"name": "Austria", "alpha2": "AT", "flag": "🇦🇹"}, {"name": "Azerbaijan", "alpha2": "AZ", "flag": "🇦🇿"}, {"name": "Burundi", "alpha2": "BI", "flag": "🇧🇮"}, {"name": "Belgium", "alpha2": "BE", "flag": "🇧🇪"}, {"name": "Benin", "alpha2": "BJ", "flag": "🇧🇯"}, {"name": "Bonaire, Sint Eustatius and Saba", "alpha2": "BQ", "flag": "🇧🇶"}, {"name": "Burkina Faso", "alpha2": "BF", "flag": "🇧🇫"}, {"name": "Bangladesh", "alpha2": "BD", "flag": "🇧🇩"}, {"name": "Bulgaria", "alpha2": "BG", "flag": "🇧🇬"}, {"name": "Bahrain", "alpha2": "BH", "flag": "🇧🇭"}, {"name": "Bahamas", "alpha2": "BS", "flag": "🇧🇸"}, {"name": "Bosnia and Herzegovina", "alpha2": "BA", "flag": "🇧🇦"}, {"name": "Saint Barthélemy", "alpha2": "BL", "flag": "🇧🇱"}, {"name": "Belarus", "alpha2": "BY", "flag": "🇧🇾"}, {"name": "Belize", "alpha2": "BZ", "flag": "🇧🇿"}, {"name": "Bermuda", "alpha2": "BM", "flag": "🇧🇲"}, {"name": "Bolivia", "alpha2": "BO", "flag": "🇧🇴"}, {"name": "Brazil", "alpha2": "BR", "flag": "🇧🇷"}, {"name": "Barbados", "alpha2": "BB", "flag": "🇧🇧"}, {"name": "Brunei", "alpha2": "BN", "flag": "🇧🇳"}, {"name": "Bhutan", "alpha2": "BT", "flag": "🇧🇹"}, {"name": "Bouvet Island", "alpha2": "BV", "flag": "🇧🇻"}, {"name": "Botswana", "alpha2": "BW", "flag": "🇧🇼"}, {"name": "Central African Republic", "alpha2": "CF", "flag": "🇨🇫"}, {"name": "Canada", "alpha2": "CA", "flag": "🇨🇦"}, {"name": "Cocos (Keeling) Islands", "alpha2": "CC", "flag": "🇨🇨"}, {"name": "Switzerland", "alpha2": "CH", "flag": "🇨🇭"}, {"name": "Chile", "alpha2": "CL", "flag": "🇨🇱"}, {"name": "China", "alpha2": "CN", "flag": "🇨🇳"}, {"name": "Côte d'Ivoire", "alpha2": "CI", "flag": "🇨🇮"}, {"name": "Cameroon", "alpha2": "CM", "flag": "🇨🇲"}, {"name": "Congo, The Democratic Republic of the", "alpha2": "CD", "flag": "🇨🇩"}, {"name": "Congo", "alpha2": "CG", "flag": "🇨🇬"}, {"name": "Cook Islands", "alpha2": "CK", "flag": "🇨🇰"}, {"name": "Colombia", "alpha2": "CO", "flag": "🇨🇴"}, {"name": "Comoros", "alpha2": "KM", "flag": "🇰🇲"}, {"name": "Cabo Verde", "alpha2": "CV", "flag": "🇨🇻"}, {"name": "Costa Rica", "alpha2": "CR", "flag": "🇨🇷"}, {"name": "Cuba", "alpha2": "CU", "flag": "🇨🇺"}, {"name": "Curaçao", "alpha2": "CW", "flag": "🇨🇼"}, {"name": "Christmas Island", "alpha2": "CX", "flag": "🇨🇽"}, {"name": "Cayman Islands", "alpha2": "KY", "flag": "🇰🇾"}, {"name": "Cyprus", "alpha2": "CY", "flag": "🇨🇾"}, {"name": "Czech Republic", "alpha2": "CZ", "flag": "🇨🇿"}, {"name": "Germany", "alpha2": "DE", "flag": "🇩🇪"}, {"name": "Djibouti", "alpha2": "DJ", "flag": "🇩🇯"}, {"name": "Dominica", "alpha2": "DM", "flag": "🇩🇲"}, {"name": "Denmark", "alpha2": "DK", "flag": "🇩🇰"}, {"name": "Dominican Republic", "alpha2": "DO", "flag": "🇩🇴"}, {"name": "Algeria", "alpha2": "DZ", "flag": "🇩🇿"}, {"name": "Ecuador", "alpha2": "EC", "flag": "🇪🇨"}, {"name": "Egypt", "alpha2": "EG", "flag": "🇪🇬"}, {"name": "Eritrea", "alpha2": "ER", "flag": "🇪🇷"}, {"name": "Western Sahara", "alpha2": "EH", "flag": "🇪🇭"}, {"name": "Spain", "alpha2": "ES", "flag": "🇪🇸"}, {"name": "Estonia", "alpha2": "EE", "flag": "🇪🇪"}, {"name": "Ethiopia", "alpha2": "ET", "flag": "🇪🇹"}, {"name": "Finland", "alpha2": "FI", "flag": "🇫🇮"}, {"name": "Fiji", "alpha2": "FJ", "flag": "🇫🇯"}, {"name": "Falkland Islands (Malvinas)", "alpha2": "FK", "flag": "🇫🇰"}, {"name": "France", "alpha2": "FR", "flag": "🇫🇷"}, {"name": "Faroe Islands", "alpha2": "FO", "flag": "🇫🇴"}, {"name": "Micronesia, Federated States of", "alpha2": "FM", "flag": "🇫🇲"}, {"name": "Gabon", "alpha2": "GA", "flag": "🇬🇦"}, {"name": "United Kingdom", "alpha2": "GB", "flag": "🇬🇧"}, {"name": "Georgia", "alpha2": "GE", "flag": "🇬🇪"}, {"name": "Guernsey", "alpha2": "GG", "flag": "🇬🇬"}, {"name": "Ghana", "alpha2": "GH", "flag": "🇬🇭"}, {"name": "Gibraltar", "alpha2": "GI", "flag": "🇬🇮"}, {"name": "Guinea", "alpha2": "GN", "flag": "🇬🇳"}, {"name": "Guadeloupe", "alpha2": "GP", "flag": "🇬🇵"}, {"name": "Gambia", "alpha2": "GM", "flag": "🇬🇲"}, {"name": "Guinea-Bissau", "alpha2": "GW", "flag": "🇬🇼"}, {"name": "Equatorial Guinea", "alpha2": "GQ", "flag": "🇬🇶"}, {"name": "Greece", "alpha2": "GR", "flag": "🇬🇷"}, {"name": "Grenada", "alpha2": "GD", "flag": "🇬🇩"}, {"name": "Greenland", "alpha2": "GL", "flag": "🇬🇱"}, {"name": "Guatemala", "alpha2": "GT", "flag": "🇬🇹"}, {"name": "French Guiana", "alpha2": "GF", "flag": "🇬🇫"}, {"name": "Guam", "alpha2": "GU", "flag": "🇬🇺"}, {"name": "Guyana", "alpha2": "GY", "flag": "🇬🇾"}, {"name": "Hong Kong", "alpha2": "HK", "flag": "🇭🇰"}, {"name": "Heard Island and McDonald Islands", "alpha2": "HM", "flag": "🇭🇲"}, {"name": "Honduras", "alpha2": "HN", "flag": "🇭🇳"}, {"name": "Croatia", "alpha2": "HR", "flag": "🇭🇷"}, {"name": "Haiti", "alpha2": "HT", "flag": "🇭🇹"}, {"name": "Hungary", "alpha2": "HU", "flag": "🇭🇺"}, {"name": "Indonesia", "alpha2": "ID", "flag": "🇮🇩"}, {"name": "Isle of Man", "alpha2": "IM", "flag": "🇮🇲"}, {"name": "India", "alpha2": "IN", "flag": "🇮🇳"}, {"name": "British Indian Ocean Territory", "alpha2": "IO", "flag": "🇮🇴"}, {"name": "Ireland", "alpha2": "IE", "flag": "🇮🇪"}, {"name": "Iran", "alpha2": "IR", "flag": "🇮🇷"}, {"name": "Iraq", "alpha2": "IQ", "flag": "🇮🇶"}, {"name": "Iceland", "alpha2": "IS", "flag": "🇮🇸"}, {"name": "Israel", "alpha2": "IL", "flag": "🇮🇱"}, {"name": "Italy", "alpha2": "IT", "flag": "🇮🇹"}, {"name": "Jamaica", "alpha2": "JM", "flag": "🇯🇲"}, {"name": "Jersey", "alpha2": "JE", "flag": "🇯🇪"}, {"name": "Jordan", "alpha2": "JO", "flag": "🇯🇴"}, {"name": "Japan", "alpha2": "JP", "flag": "🇯🇵"}, {"name": "Kazakhstan", "alpha2": "KZ", "flag": "🇰🇿"}, {"name": "Kenya", "alpha2": "KE", "flag": "🇰🇪"}, {"name": "Kyrgyzstan", "alpha2": "KG", "flag": "🇰🇬"}, {"name": "Cambodia", "alpha2": "KH", "flag": "🇰🇭"}, {"name": "Kiribati", "alpha2": "KI", "flag": "🇰🇮"}, {"name": "Saint Kitts and Nevis", "alpha2": "KN", "flag": "🇰🇳"}, {"name": "South Korea", "alpha2": "KR", "flag": "🇰🇷"}, {"name": "Kuwait", "alpha2": "KW", "flag": "🇰🇼"}, {"name": "Laos", "alpha2": "LA", "flag": "🇱🇦"}, {"name": "Lebanon", "alpha2": "LB", "flag": "🇱🇧"}, {"name": "Liberia", "alpha2": "LR", "flag": "🇱🇷"}, {"name": "Libya", "alpha2": "LY", "flag": "🇱🇾"}, {"name": "Saint Lucia", "alpha2": "LC", "flag": "🇱🇨"}, {"name": "Liechtenstein", "alpha2": "LI", "flag": "🇱🇮"}, {"name": "Sri Lanka", "alpha2": "LK", "flag": "🇱🇰"}, {"name": "Lesotho", "alpha2": "LS", "flag": "🇱🇸"}, {"name": "Lithuania", "alpha2": "LT", "flag": "🇱🇹"}, {"name": "Luxembourg", "alpha2": "LU", "flag": "🇱🇺"}, {"name": "Latvia", "alpha2": "LV", "flag": "🇱🇻"}, {"name": "Macao", "alpha2": "MO", "flag": "🇲🇴"}, {"name": "Saint Martin (French part)", "alpha2": "MF", "flag": "🇲🇫"}, {"name": "Morocco", "alpha2": "MA", "flag": "🇲🇦"}, {"name": "Monaco", "alpha2": "MC", "flag": "🇲🇨"}, {"name": "Moldova", "alpha2": "MD", "flag": "🇲🇩"}, {"name": "Madagascar", "alpha2": "MG", "flag": "🇲🇬"}, {"name": "Maldives", "alpha2": "MV", "flag": "🇲🇻"}, {"name": "Mexico", "alpha2": "MX", "flag": "🇲🇽"}, {"name": "Marshall Islands", "alpha2": "MH", "flag": "🇲🇭"}, {"name": "North Macedonia", "alpha2": "MK", "flag": "🇲🇰"}, {"name": "Mali", "alpha2": "ML", "flag": "🇲🇱"}, {"name": "Malta", "alpha2": "MT", "flag": "🇲🇹"}, {"name": "Myanmar", "alpha2": "MM", "flag": "🇲🇲"}, {"name": "Montenegro", "alpha2": "ME", "flag": "🇲🇪"}, {"name": "Mongolia", "alpha2": "MN", "flag": "🇲🇳"}, {"name": "Northern Mariana Islands", "alpha2": "MP", "flag": "🇲🇵"}, {"name": "Mozambique", "alpha2": "MZ", "flag": "🇲🇿"}, {"name": "Mauritania", "alpha2": "MR", "flag": "🇲🇷"}, {"name": "Montserrat", "alpha2": "MS", "flag": "🇲🇸"}, {"name": "Martinique", "alpha2": "MQ", "flag": "🇲🇶"}, {"name": "Mauritius", "alpha2": "MU", "flag": "🇲🇺"}, {"name": "Malawi", "alpha2": "MW", "flag": "🇲🇼"}, {"name": "Malaysia", "alpha2": "MY", "flag": "🇲🇾"}, {"name": "Mayotte", "alpha2": "YT", "flag": "🇾🇹"}, {"name": "Namibia", "alpha2": "NA", "flag": "🇳🇦"}, {"name": "New Caledonia", "alpha2": "NC", "flag": "🇳🇨"}, {"name": "Niger", "alpha2": "NE", "flag": "🇳🇪"}, {"name": "Norfolk Island", "alpha2": "NF", "flag": "🇳🇫"}, {"name": "Nigeria", "alpha2": "NG", "flag": "🇳🇬"}, {"name": "Nicaragua", "alpha2": "NI", "flag": "🇳🇮"}, {"name": "Niue", "alpha2": "NU", "flag": "🇳🇺"}, {"name": "Netherlands", "alpha2": "NL", "flag": "🇳🇱"}, {"name": "Norway", "alpha2": "NO", "flag": "🇳🇴"}, {"name": "Nepal", "alpha2": "NP", "flag": "🇳🇵"}, {"name": "Nauru", "alpha2": "NR", "flag": "🇳🇷"}, {"name": "New Zealand", "alpha2": "NZ", "flag": "🇳🇿"}, {"name": "Oman", "alpha2": "OM", "flag": "🇴🇲"}, {"name": "Pakistan", "alpha2": "PK", "flag": "🇵🇰"}, {"name": "Panama", "alpha2": "PA", "flag": "🇵🇦"}, {"name": "Pitcairn", "alpha2": "PN", "flag": "🇵🇳"}, {"name": "Peru", "alpha2": "PE", "flag": "🇵🇪"}, {"name": "Philippines", "alpha2": "PH", "flag": "🇵🇭"}, {"name": "Palau", "alpha2": "PW", "flag": "🇵🇼"}, {"name": "Papua New Guinea", "alpha2": "PG", "flag": "🇵🇬"}, {"name": "Poland", "alpha2": "PL", "flag": "🇵🇱"}, {"name": "Puerto Rico", "alpha2": "PR", "flag": "🇵🇷"}, {"name": "North Korea", "alpha2": "KP", "flag": "🇰🇵"}, {"name": "Portugal", "alpha2": "PT", "flag": "🇵🇹"}, {"name": "Paraguay", "alpha2": "PY", "flag": "🇵🇾"}, {"name": "Palestine", "alpha2": "PS", "flag": "🇵🇸"}, {"name": "French Polynesia", "alpha2": "PF", "flag": "🇵🇫"}, {"name": "Qatar", "alpha2": "QA", "flag": "🇶🇦"}, {"name": "Réunion", "alpha2": "RE", "flag": "🇷🇪"}, {"name": "Romania", "alpha2": "RO", "flag": "🇷🇴"}, {"name": "Russia", "alpha2": "RU", "flag": "🇷🇺"}, {"name": "Rwanda", "alpha2": "RW", "flag": "🇷🇼"}, {"name": "Saudi Arabia", "alpha2": "SA", "flag": "🇸🇦"}, {"name": "Sudan", "alpha2": "SD", "flag": "🇸🇩"}, {"name": "Senegal", "alpha2": "SN", "flag": "🇸🇳"}, {"name": "Singapore", "alpha2": "SG", "flag": "🇸🇬"}, {"name": "South Georgia and the South Sandwich Islands", "alpha2": "GS", "flag": "🇬🇸"}, {"name": "Saint Helena, Ascension and Tristan da Cunha", "alpha2": "SH", "flag": "🇸🇭"}, {"name": "Svalbard and Jan Mayen", "alpha2": "SJ", "flag": "🇸🇯"}, {"name": "Solomon Islands", "alpha2": "SB", "flag": "🇸🇧"}, {"name": "Sierra Leone", "alpha2": "SL", "flag": "🇸🇱"}, {"name": "El Salvador", "alpha2": "SV", "flag": "🇸🇻"}, {"name": "San Marino", "alpha2": "SM", "flag": "🇸🇲"}, {"name": "Somalia", "alpha2": "SO", "flag": "🇸🇴"}, {"name": "Saint Pierre and Miquelon", "alpha2": "PM", "flag": "🇵🇲"}, {"name": "Serbia", "alpha2": "RS", "flag": "🇷🇸"}, {"name": "South Sudan", "alpha2": "SS", "flag": "🇸🇸"}, {"name": "Sao Tome and Principe", "alpha2": "ST", "flag": "🇸🇹"}, {"name": "Suriname", "alpha2": "SR", "flag": "🇸🇷"}, {"name": "Slovakia", "alpha2": "SK", "flag": "🇸🇰"}, {"name": "Slovenia", "alpha2": "SI", "flag": "🇸🇮"}, {"name": "Sweden", "alpha2": "SE", "flag": "🇸🇪"}, {"name": "Eswatini", "alpha2": "SZ", "flag": "🇸🇿"}, {"name": "Sint Maarten (Dutch part)", "alpha2": "SX", "flag": "🇸🇽"}, {"name": "Seychelles", "alpha2": "SC", "flag": "🇸🇨"}, {"name": "Syria", "alpha2": "SY", "flag": "🇸🇾"}, {"name": "Turks and Caicos Islands", "alpha2": "TC", "flag": "🇹🇨"}, {"name": "Chad", "alpha2": "TD", "flag": "🇹🇩"}, {"name": "Togo", "alpha2": "TG", "flag": "🇹🇬"}, {"name": "Thailand", "alpha2": "TH", "flag": "🇹🇭"}, {"name": "Tajikistan", "alpha2": "TJ", "flag": "🇹🇯"}, {"name": "Tokelau", "alpha2": "TK", "flag": "🇹🇰"}, {"name": "Turkmenistan", "alpha2": "TM", "flag": "🇹🇲"}, {"name": "Timor-Leste", "alpha2": "TL", "flag": "🇹🇱"}, {"name": "Tonga", "alpha2": "TO", "flag": "🇹🇴"}, {"name": "Trinidad and Tobago", "alpha2": "TT", "flag": "🇹🇹"}, {"name": "Tunisia", "alpha2": "TN", "flag": "🇹🇳"}, {"name": "Türkiye", "alpha2": "TR", "flag": "🇹🇷"}, {"name": "Tuvalu", "alpha2": "TV", "flag": "🇹🇻"}, {"name": "Taiwan", "alpha2": "TW", "flag": "🇹🇼"}, {"name": "Tanzania", "alpha2": "TZ", "flag": "🇹🇿"}, {"name": "Uganda", "alpha2": "UG", "flag": "🇺🇬"}, {"name": "Ukraine", "alpha2": "UA", "flag": "🇺🇦"}, {"name": "United States Minor Outlying Islands", "alpha2": "UM", "flag": "🇺🇲"}, {"name": "Uruguay", "alpha2": "UY", "flag": "🇺🇾"}, {"name": "United States", "alpha2": "US", "flag": "🇺🇸"}, {"name": "Uzbekistan", "alpha2": "UZ", "flag": "🇺🇿"}, {"name": "Holy See (Vatican City State)", "alpha2": "VA", "flag": "🇻🇦"}, {"name": "Saint Vincent and the Grenadines", "alpha2": "VC", "flag": "🇻🇨"}, {"name": "Venezuela", "alpha2": "VE", "flag": "🇻🇪"}, {"name": "Virgin Islands, British", "alpha2": "VG", "flag": "🇻🇬"}, {"name": "Virgin Islands, U.S.", "alpha2": "VI", "flag": "🇻🇮"}, {"name": "Vietnam", "alpha2": "VN", "flag": "🇻🇳"}, {"name": "Vanuatu", "alpha2": "VU", "flag": "🇻🇺"}, {"name": "Wallis and Futuna", "alpha2": "WF", "flag": "🇼🇫"}, {"name": "Samoa", "alpha2": "WS", "flag": "🇼🇸"}, {"name": "Yemen", "alpha2": "YE", "flag": "🇾🇪"}, {"name": "South Africa", "alpha2": "ZA", "flag": "🇿🇦"}, {"name": "Zambia", "alpha2": "ZM", "flag": "🇿🇲"}, {"name": "Zimbabwe", "alpha2": "ZW", "flag": "🇿🇼"}, {"name": "Kosovo", "alpha2": "XK", "flag": "🇽🇰"}];
var COUNTRY_ALIAS_MAP={
  'USA':'United States','US':'United States','U.S.A.':'United States','United States of America':'United States',
  'Russian Federation':'Russia','Iran, Islamic Republic of':'Iran','Korea, Republic of':'South Korea',
  "Korea, Democratic People's Republic of":'North Korea','Taiwan, Province of China':'Taiwan',
  'Viet Nam':'Vietnam','Syrian Arab Republic':'Syria',"Lao People's Democratic Republic":'Laos',
  'Moldova, Republic of':'Moldova','Tanzania, United Republic of':'Tanzania','Venezuela, Bolivarian Republic of':'Venezuela',
  'Bolivia, Plurinational State of':'Bolivia','Palestine, State of':'Palestine','Brunei Darussalam':'Brunei','Czechia':'Czech Republic',
  'Türkiye':'Turkey','Republic of Türkiye':'Turkey','Republic of Korea':'South Korea','DPRK':'North Korea',
  'The Bahamas':'Bahamas','Cabo Verde':'Cape Verde','Democratic Republic of the Congo':'Congo, The Democratic Republic of the',
  'DR Congo':'Congo, The Democratic Republic of the','Congo DRC':'Congo, The Democratic Republic of the',
  'Ivory Coast':"Côte d'Ivoire",'Eswatini (Swaziland)':'Eswatini','Holy See':'Holy See (Vatican City State)'
};
function normalizeCountryName(name){
  name=(name||'').trim();
  return COUNTRY_ALIAS_MAP[name] || name;
}
function stableHash01(s){
  s=String(s||'Default'); let h=2166136261>>>0;
  for(let i=0;i<s.length;i++){ h ^= s.charCodeAt(i); h = Math.imul(h,16777619); }
  return ((h>>>0)%10000)/10000;
}
const COUNTRY_BAND_HINTS={
  super:new Set(['United States','Russia','China']),
  strategic:new Set(['India','United Kingdom','France','Israel','Pakistan','North Korea']),
  advanced:new Set(['Japan','South Korea','Germany','Italy','Turkey','Australia','Poland','Taiwan','Saudi Arabia','Iran','Ukraine','Canada','Spain','Netherlands','Norway','Sweden','Finland','Greece','Romania','Czech Republic','Belgium','Denmark','Portugal','Singapore','United Arab Emirates','Qatar','Brazil','South Africa','Egypt','Algeria','Indonesia','Vietnam']),
  regional:new Set(['Argentina','Chile','Colombia','Peru','Mexico','Venezuela','Malaysia','Thailand','Philippines','Bangladesh','Myanmar','Sri Lanka','Kazakhstan','Uzbekistan','Turkmenistan','Azerbaijan','Armenia','Georgia','Serbia','Croatia','Hungary','Slovakia','Slovenia','Bulgaria','Lithuania','Latvia','Estonia','Belarus','Iraq','Syria','Jordan','Kuwait','Oman','Bahrain','Morocco','Tunisia','Libya','Ethiopia','Kenya','Nigeria','Ghana','Angola']),
  micro:new Set(['Andorra','Antigua and Barbuda','Aruba','Bahamas','Barbados','Belize','Bermuda','Bhutan','Bonaire, Sint Eustatius and Saba','Brunei','Cape Verde','Comoros','Cook Islands','Curaçao','Dominica','Fiji','French Polynesia','Greenland','Grenada','Guam','Guyana','Iceland','Jamaica','Kiribati','Liechtenstein','Luxembourg','Maldives','Malta','Marshall Islands','Mauritius','Micronesia','Monaco','Montserrat','Nauru','New Caledonia','New Zealand','Niue','Palau','Papua New Guinea','Puerto Rico','Saint Barthélemy','Saint Kitts and Nevis','Saint Lucia','Saint Martin (French part)','Saint Pierre and Miquelon','Saint Vincent and the Grenadines','Samoa','San Marino','Sao Tome and Principe','Seychelles','Singapore','Sint Maarten (Dutch part)','Solomon Islands','Suriname','Tonga','Trinidad and Tobago','Tuvalu','Vanuatu','Virgin Islands, British','Virgin Islands, U.S.','Kosovo'])
};
function inferCountryBand(country){
  country=normalizeCountryName(country);
  if(COUNTRY_BAND_HINTS.super.has(country)) return 'super';
  if(COUNTRY_BAND_HINTS.strategic.has(country)) return 'strategic';
  if(COUNTRY_BAND_HINTS.advanced.has(country)) return 'advanced';
  if(COUNTRY_BAND_HINTS.regional.has(country)) return 'regional';
  if(COUNTRY_BAND_HINTS.micro.has(country)) return 'micro';
  const lc=country.toLowerCase();
  if(/islands|island|territories|territory|minor outlying|saint |st\.|futuna|jan mayen|cocos|keeling|tokelau|pitcairn/.test(lc)) return 'micro';
  return 'limited';
}
function bandParams(country){
  const band=inferCountryBand(country);
  if(band==='super') return {band, qBase:0.86, qSpread:0.07, offenseScale:2.8, defenseScale:2.7, exoBias:1.0, hypBias:1.0};
  if(band==='strategic') return {band, qBase:0.77, qSpread:0.08, offenseScale:1.95, defenseScale:1.8, exoBias:0.72, hypBias:0.62};
  if(band==='advanced') return {band, qBase:0.69, qSpread:0.10, offenseScale:1.28, defenseScale:1.35, exoBias:0.35, hypBias:0.28};
  if(band==='regional') return {band, qBase:0.59, qSpread:0.10, offenseScale:0.92, defenseScale:0.95, exoBias:0.12, hypBias:0.12};
  if(band==='micro') return {band, qBase:0.47, qSpread:0.08, offenseScale:0.35, defenseScale:0.45, exoBias:0.0, hypBias:0.0};
  return {band, qBase:0.52, qSpread:0.09, offenseScale:0.56, defenseScale:0.62, exoBias:0.05, hypBias:0.03};
}
function synthDoctrineForCountry(country){
  country=normalizeCountryName(country);
  const bp=bandParams(country), h=stableHash01(country), q=clamp(bp.qBase + bp.qSpread*(h-0.5)*2, 0.38, 0.95);
  const c2=clamp(q + 0.06*(stableHash01(country+'c2')-0.5),0.35,0.97);
  const sf=clamp(q + 0.07*(stableHash01(country+'sf')-0.5) + (bp.band==='advanced'||bp.band==='super'?0.03:0),0.34,0.97);
  const tr=clamp(q + 0.06*(stableHash01(country+'tr')-0.5),0.34,0.96);
  const mt=clamp(q + 0.08*(stableHash01(country+'mt')-0.5),0.30,0.96);
  const sd=clamp(q + 0.06*(stableHash01(country+'sd')-0.5),0.32,0.96);
  const raidBase=bp.band==='super'?9:(bp.band==='strategic'?7:(bp.band==='advanced'?5:(bp.band==='regional'?4:(bp.band==='limited'?3:2))));
  const chanBase=bp.band==='super'?10:(bp.band==='strategic'?8:(bp.band==='advanced'?6:(bp.band==='regional'?4:(bp.band==='limited'?3:2))));
  const rc=Math.max(1, Math.round(raidBase + 3*q + stableHash01(country+'rc')*2));
  const cc=Math.max(1, Math.round(chanBase + 2*q + stableHash01(country+'cc')*2));
  const re=clamp(0.40 + q*0.50 + 0.05*(stableHash01(country+'re')-0.5),0.32,0.94);
  return {c2:c2,sensorFusion:sf,training:tr,maintenance:mt,shotDiscipline:sd,raidCapacity:rc,raidCapacityNorm:clamp(rc/10,0.20,0.98),concurrentChannels:cc,reloadElasticity:re,synthetic:true,band:bp.band,forceScale:bp.offenseScale,defenseScale:bp.defenseScale};
}
function synthArsenalForCountry(country, flag){
  country=normalizeCountryName(country);
  const d=DOCTRINE_DB[country] || synthDoctrineForCountry(country);
  const bp=bandParams(country);
  const q=clamp((d.c2+d.sensorFusion+d.training+d.maintenance+d.shotDiscipline)/5,0.32,0.96);
  const offense=[], defense=[];
  const areaName=bp.band==='micro' ? 'Territorial Guard Missile' : (bp.band==='limited' ? 'National Rocket Force' : 'Strategic Missile Force');
  const areaType=(bp.band==='super'?'IRBM':(bp.band==='strategic'?'MRBM':(bp.band==='advanced'?'SRBM':(bp.band==='regional'?'SRBM':'Tactical'))));
  const ballisticRange=Math.round(lerp(bp.band==='micro'?90:140, bp.band==='super'?9000:(bp.band==='strategic'?5500:(bp.band==='advanced'?2200:1200)), Math.pow(q,1.2)));
  const ballisticMach=+(lerp(bp.band==='micro'?2.4:3.0, bp.band==='super'?18.5:(bp.band==='strategic'?14.5:(bp.band==='advanced'?9.5:7.2)), q)).toFixed(1);
  offense.push({name:areaName,type:areaType,mach:ballisticMach,range:ballisticRange,altKm:Math.round(lerp(18,bp.band==='super'?950:(bp.band==='strategic'?700:(bp.band==='advanced'?260:120)),q)),mode:(q>0.72?'guided':'ballistic'),angle:Math.round(lerp(26,bp.band==='super'?76:62,q)),evasion:+clamp(0.04 + 0.42*q + (bp.band==='super'?0.06:0),0.03,0.72).toFixed(2),cep:Math.round(lerp(bp.band==='micro'?1500:1100,bp.band==='super'?45:(bp.band==='strategic'?80:(bp.band==='advanced'?140:260)),q)),desc:'Projected national ballistic strike force'});
  offense.push({name:(bp.band==='micro'?'Coastal Strike Wing':'Cruise Strike Wing'),type:'Cruise',mach:+lerp(0.72,bp.band==='super'?3.5:(bp.band==='strategic'?2.6:(bp.band==='advanced'?2.2:1.4)),q).toFixed(2),range:Math.round(lerp(bp.band==='micro'?80:180,bp.band==='super'?3200:(bp.band==='strategic'?2200:(bp.band==='advanced'?1600:900)),q)),altKm:+lerp(0.02,bp.band==='advanced'?16:8,q).toFixed(2),mode:'cruise',angle:Math.round(lerp(3,14,q)),evasion:+clamp(0.08 + 0.22*q + 0.05*stableHash01(country+'cruise'),0.06,0.52).toFixed(2),cep:Math.round(lerp(180,bp.band==='super'?8:(bp.band==='strategic'?12:(bp.band==='advanced'?18:35)),q)),desc:'Projected stand-off and cruise strike inventory'});
  if(q>0.58 || bp.hypBias>0.25){
    offense.push({name:(bp.band==='super'||bp.band==='strategic')?'Advanced Glide Vehicle':'Maneuver Strike Vehicle',type:(bp.band==='super'||bp.band==='strategic')?'Hypersonic':'Guided',mach:+lerp(4.2,bp.band==='super'?18:(bp.band==='strategic'?12.5:(bp.band==='advanced'?8.5:6.0)),clamp(q+bp.hypBias*0.2,0,1)).toFixed(1),range:Math.round(lerp(220,bp.band==='super'?4200:(bp.band==='strategic'?2400:(bp.band==='advanced'?1200:700)),q)),altKm:Math.round(lerp(18,bp.band==='super'?120:(bp.band==='strategic'?90:55),q)),mode:(q>0.66?'evasive':'guided'),angle:Math.round(lerp(18,38,q)),evasion:+clamp(0.22 + 0.48*q + 0.10*bp.hypBias,0.18,0.88).toFixed(2),cep:Math.round(lerp(120,bp.band==='super'?10:(bp.band==='strategic'?16:(bp.band==='advanced'?22:40)),q)),desc:'Projected maneuvering strike / glide vehicle'});
  }
  if(bp.band==='super' || bp.band==='strategic'){
    offense.unshift({name:(bp.band==='super'?'National Strategic Deterrent':'Strategic Deterrent Wing'),type:(bp.band==='super'?'ICBM':'IRBM'),mach:+lerp(12,bp.band==='super'?25:20,q).toFixed(1),range:Math.round(lerp(3500,bp.band==='super'?14000:9000,q)),altKm:Math.round(lerp(420,bp.band==='super'?1400:900,q)),mode:'ballistic',angle:Math.round(lerp(54,80,q)),evasion:+clamp(0.05+0.16*q,0.05,0.24).toFixed(2),cep:Math.round(lerp(220,bp.band==='super'?90:140,q)),desc:'Projected strategic deterrent and long-range strike inventory'});
  }
  const pointPk=clamp(0.40 + 0.38*q + 0.04*bp.defenseScale,0.36,0.90);
  defense.push({name:(bp.band==='micro'?'Territorial Point Defense':'National Point Defense'),tier:'point',mach:+lerp(2.0,bp.band==='super'?6.0:(bp.band==='strategic'?5.4:(bp.band==='advanced'?4.8:4.0)),q).toFixed(1),altMi:+lerp(3,bp.band==='super'?18:14,q).toFixed(1),altMinMi:0,range:Math.round(lerp(12,bp.band==='super'?90:(bp.band==='strategic'?75:(bp.band==='advanced'?65:45)),q)),delay:Math.round(lerp(9,3,q)),batteries:Math.max(1,Math.round((bp.defenseScale*2.2) + d.raidCapacityNorm*5)),aggr:+clamp(0.52+0.30*q,0.50,0.92).toFixed(2),killR:Math.round(lerp(3600,bp.band==='super'?11000:9000,q)),pk:+pointPk.toFixed(2),stockScale:+(0.7*bp.defenseScale).toFixed(2)});
  defense.push({name:'National Area Defense',tier:'endo',mach:+lerp(3.0,bp.band==='super'?10.5:(bp.band==='strategic'?9.2:(bp.band==='advanced'?8.4:6.6)),q).toFixed(1),altMi:+lerp(7,bp.band==='super'?30:(bp.band==='strategic'?26:22),q).toFixed(1),altMinMi:0.01,range:Math.round(lerp(24,bp.band==='super'?320:(bp.band==='strategic'?280:(bp.band==='advanced'?230:150)),q)),delay:Math.round(lerp(15,6,q)),batteries:Math.max(1,Math.round(bp.defenseScale*1.5 + d.concurrentChannels/2.5)),aggr:+clamp(0.60+0.24*q,0.56,0.94).toFixed(2),killR:Math.round(lerp(6200,bp.band==='super'?16500:14000,q)),pk:+clamp(0.48 + 0.32*q + 0.03*bp.defenseScale,0.42,0.90).toFixed(2),stockScale:+(0.9*bp.defenseScale).toFixed(2)});
  if(q>0.56 || bp.band==='advanced' || bp.band==='strategic' || bp.band==='super') defense.unshift({name:'National High-Altitude Defense',tier:(q>0.82||bp.band==='super'?'exo':'high-endo'),mach:+lerp(6.0,bp.band==='super'?18.0:(bp.band==='strategic'?15.0:(bp.band==='advanced'?12.5:9.5)),q).toFixed(1),altMi:+lerp(20,bp.band==='super'?420:(bp.band==='strategic'?240:(bp.band==='advanced'?120:70)),q).toFixed(1),altMinMi:+lerp(2,bp.band==='super'?35:(bp.band==='strategic'?22:(bp.band==='advanced'?12:6)),q).toFixed(1),range:Math.round(lerp(80,bp.band==='super'?900:(bp.band==='strategic'?650:(bp.band==='advanced'?420:220)),q)),delay:Math.round(lerp(24,9,q)),batteries:Math.max(1,Math.round(bp.exoBias*2.4 + d.raidCapacityNorm*1.8)),aggr:+clamp(0.68+0.22*q,0.64,0.96).toFixed(2),killR:Math.round(lerp(11000,bp.band==='super'?24000:21000,q)),pk:+clamp(0.55 + 0.26*q + 0.03*bp.exoBias,0.50,0.93).toFixed(2),stockScale:+Math.max(0.4, 0.55*bp.defenseScale + 0.35*bp.exoBias).toFixed(2)});
  return {flag:flag||'🏳️', offense:offense, defense:defense, synthetic:true, band:bp.band};
}
(function expandToAllCountries(){
  for(const meta of ALL_COUNTRY_META){
    const name=normalizeCountryName(meta.name);
    if(!DOCTRINE_DB[name]) DOCTRINE_DB[name]=synthDoctrineForCountry(name);
    else if(!DOCTRINE_DB[name].band){
      const auto=synthDoctrineForCountry(name);
      DOCTRINE_DB[name]=Object.assign({}, auto, DOCTRINE_DB[name], {band:auto.band, forceScale:auto.forceScale, defenseScale:auto.defenseScale});
    }
    if(!ARSENAL[name]) ARSENAL[name]=synthArsenalForCountry(name, meta.flag);
    else if(!ARSENAL[name].band) ARSENAL[name].band=inferCountryBand(name);
  }
  

const CITY_AWARE_DB={};
function buildCityAwareDB(){
  const countries=(typeof ARSENAL_COUNTRIES!=='undefined' && ARSENAL_COUNTRIES && ARSENAL_COUNTRIES.length)?ARSENAL_COUNTRIES:Object.keys(ARSENAL||{});
  const seededByCountry={};
  for(const item of PLACE_SEED){
    if(item==null || item.lat==null || item.lon==null) continue;
    const kind=(item.kind||'').toLowerCase();
    if(!(kind.includes('city') || kind.includes('town') || kind.includes('capital'))) continue;
    const country=inferCountryFromPlaceName(item.name||'');
    if(!country) continue;
    if(!seededByCountry[country]) seededByCountry[country]=[];
    const nm=(''+item.name).trim();
    seededByCountry[country].push({
      name:nm, lat:+item.lat, lon:+item.lon,
      kind:item.kind||'city', provider:item.provider||'seed',
      weight:kind.includes('capital')?1.0:(kind.includes('city')?0.84:0.68),
      synthetic:false,
      priority:item.priority||0
    });
  }
  for(const country of countries){
    const centroid=resolveSeedPlaceFast(country);
    const nodes=(seededByCountry[country]||[]).slice();
    const used={};
    const uniq=[];
    for(const node of nodes.sort((a,b)=>(b.weight||0)-(a.weight||0) || (b.priority||0)-(a.priority||0))){
      const k=normalizePlaceKey(node.name);
      if(used[k]) continue;
      used[k]=1; uniq.push(node);
    }
    if(centroid && centroid.lat!=null){
      const cap=uniq.find(n => /capital/i.test(n.kind||''));
      if(!cap){
        uniq.unshift({name:country+' Capital Sector', lat:+centroid.lat, lon:+centroid.lon, kind:'capital sector', provider:'synthetic', weight:0.96, synthetic:true, priority:100});
      }
      if(!uniq.length || gcDistMeters([uniq[0].lat,uniq[0].lon],[centroid.lat,centroid.lon])>250000){
        uniq.push({name:country+' Central Sector', lat:+centroid.lat, lon:+centroid.lon, kind:'central sector', provider:'country', weight:0.72, synthetic:true, priority:30});
      }
      const bp=bandParams(country);
      const sectorCount=bp.band==='super'?4:(bp.band==='strategic'?4:(bp.band==='advanced'?3:(bp.band==='regional'?3:2)));
      const sectorRange=bp.band==='super'?320:(bp.band==='strategic'?260:(bp.band==='advanced'?180:(bp.band==='regional'?120:80)));
      const labels=['Northern Sector','Eastern Sector','Southern Sector','Western Sector'];
      for(let i=0;i<sectorCount;i++){
        const bearing=(stableHash01(country+'sector'+i)*360 + i*77)%360;
        const dist=sectorRange*(0.55+0.55*stableHash01(country+'sectorDist'+i));
        const ll=offsetLatLon(centroid.lat, centroid.lon, bearing, dist);
        const nodeName=country+' '+labels[i%labels.length];
        uniq.push({name:nodeName, lat:+ll.lat.toFixed(6), lon:+ll.lon.toFixed(6), kind:'regional sector', provider:'synthetic', weight:0.58-0.04*i, synthetic:true, priority:20-i});
      }
    }
    CITY_AWARE_DB[country]=uniq.slice(0,6);
  }
}
function getCityDefenseNodes(country, fallbackPlace){
  country=normalizeCountryName(country||'');
  let nodes=(CITY_AWARE_DB[country]||[]).slice();
  if(fallbackPlace && fallbackPlace.lat!=null){
    nodes.unshift({name:fallbackPlace.name||country+' Sector', lat:+fallbackPlace.lat, lon:+fallbackPlace.lon, kind:'manual site', provider:'runtime', weight:0.92, synthetic:false, priority:200});
  }
  const out=[]; const seen={};
  for(const n of nodes){
    const k=(n.name||'')+'|'+(+n.lat).toFixed(3)+'|'+(+n.lon).toFixed(3);
    if(seen[k]) continue; seen[k]=1; out.push(n);
  }
  return out;
}
window.getCityDefenseNodes = getCityDefenseNodes;
window.getCityDefenseNode = getCityDefenseNode;
function activeDefendersForNode(country, node){
  const nm=node && node.name ? node.name : '';
  return interceptors.filter(i=>i && i.alive && !i.excludeFromMetrics && i.defenderCountry===country && (i.defenseNodeName||'')===nm).length;
}
function defenseNodeScore(country, node, threat, doctrine){
  const targetLL=threat && (threat.toLL || (threat.currentLL&&threat.currentLL()) || null);
  const dist=targetLL ? gcDistMeters([node.lat,node.lon], targetLL)/1000 : 250;
  const closeness=1/(1+dist/260);
  const load=activeDefendersForNode(country, node);
  const loadPenalty=1/(1+0.42*load);
  const capBoost=/capital/i.test(node.kind||'') ? 0.12 : 0;
  const base=(node.weight||0.6) + capBoost + 0.08*((doctrine&&doctrine.sensorFusion)||0.7);
  return base * closeness * loadPenalty;
}
function chooseDefenseNodeForThreat(country, threat, fallbackPlace){
  const doctrine=getDoctrineForCountry(country||'Default');
  const nodes=getCityDefenseNodes(country, fallbackPlace);
  if(!nodes.length) return fallbackPlace || resolveSeedPlaceFast(country);
  let best=nodes[0], bestScore=-1;
  for(const node of nodes){
    const score=defenseNodeScore(country,node,threat,doctrine);
    if(score>bestScore){ bestScore=score; best=node; }
  }
  return best;
}
function chooseCounterstrikeOrigin(country, enemyCountry, incomingAttack){
  const nodes=getCityDefenseNodes(country, resolveSeedPlaceFast(country));
  if(!nodes.length) return resolveSeedPlaceFast(country);
  const enemyAim=(incomingAttack && incomingAttack.fromLL)? incomingAttack.fromLL : ((resolveSeedPlaceFast(enemyCountry)||{}).lat!=null ? [resolveSeedPlaceFast(enemyCountry).lat, resolveSeedPlaceFast(enemyCountry).lon] : null);
  let best=nodes[0], bestScore=-1;
  for(const node of nodes){
    const rangeScore=enemyAim ? gcDistMeters([node.lat,node.lon], enemyAim)/1000 : 0;
    const score=(node.weight||0.6) + 0.00007*rangeScore + (/capital|central/i.test(node.kind||'')?0.06:0);
    if(score>bestScore){ bestScore=score; best=node; }
  }
  return best;
}
window.chooseCounterstrikeOrigin = chooseCounterstrikeOrigin;
function chooseCounterstrikeTarget(country, incomingAttack){
  if(incomingAttack && incomingAttack.fromName){
    const exact=resolveSeedPlaceFast(incomingAttack.fromName);
    if(exact && exact.lat!=null) return exact;
  }
  const nodes=getCityDefenseNodes(country, resolveSeedPlaceFast(country));
  if(nodes.length){
    const cap=nodes.find(n=>/capital/i.test(n.kind||''));
    return cap || nodes[0];
  }
  return resolveSeedPlaceFast(country);
}
buildCityAwareDB();
ARSENAL_COUNTRIES = Object.keys(ARSENAL).sort((a,b)=>a.localeCompare(b));
window.getCityDefenseNodes = getCityDefenseNodes;
window.getCityDefenseNode = function(country, fallbackPlace){ const nodes=getCityDefenseNodes(country, fallbackPlace); return nodes && nodes.length ? nodes[0] : (fallbackPlace || resolveSeedPlaceFast(country)); };
window.getCityDefenceNodes = window.getCityDefenseNodes;
window.getCityDefenceNode = window.getCityDefenseNode;
window.chooseCounterstrikeOrigin = chooseCounterstrikeOrigin;
window.chooseCounterStrikeOrigin = chooseCounterstrikeOrigin;
window.chooseCounterstrikeTarget = chooseCounterstrikeTarget;
window.chooseCounterStrikeTarget = chooseCounterstrikeTarget;
window.resolveSeedPlaceFast = resolveSeedPlaceFast;
window.getDoctrineForCountry = getDoctrineForCountry;
})();

function getDoctrineForCountry(country){ return DOCTRINE_DB[country] || DOCTRINE_DB.Default; }
function getDoctrineForPlace(placeName){
  var ar=getArsenalForPlace(placeName||'');
  return {country:ar?ar.country:'Default', doctrine:getDoctrineForCountry(ar?ar.country:'Default')};
}

function getArsenalForPlace(pn){
  if(!pn)return null;pn=pn.toLowerCase();
  var map={'washington':'United States','new york':'United States','moscow':'Russia','saint petersburg':'Russia','beijing':'China','shanghai':'China','new delhi':'India','mumbai':'India','london':'United Kingdom','paris':'France','seoul':'South Korea','busan':'South Korea','tokyo':'Japan','osaka':'Japan','islamabad':'Pakistan','karachi':'Pakistan','ankara':'Turkey','istanbul':'Turkey','rome':'Italy','berlin':'Germany','tel aviv':'Israel','jerusalem':'Israel','canberra':'Australia','sydney':'Australia','tehran':'Iran','riyadh':'Saudi Arabia','cairo':'Egypt','pyongyang':'North Korea','taipei':'Taiwan','warsaw':'Poland'};
  for(var c=0;c<ARSENAL_COUNTRIES.length;c++){if(pn.indexOf(ARSENAL_COUNTRIES[c].toLowerCase())>=0)return{country:ARSENAL_COUNTRIES[c],data:ARSENAL[ARSENAL_COUNTRIES[c]]};}
  for(var city in map){if(pn.indexOf(city)>=0){var co=map[city];return{country:co,data:ARSENAL[co]};}}
  return null;
}

/* ── Weapon Selection Handler ── */
function updateWeaponDropdown(){
  var ar=getArsenalForPlace(fromInput.value),sel=$('weaponSelect');
  sel.innerHTML='<option value="">— Custom (sliders) —</option>';
  $('weaponCountry').textContent='';$('weaponDesc').textContent='';$('weaponSpecs').innerHTML='';
  if(!ar)return;
  $('weaponCountry').textContent=ar.data.flag+' '+ar.country;
  for(var i=0;i<ar.data.offense.length;i++){var m=ar.data.offense[i];sel.innerHTML+='<option value="'+i+'">'+m.name+' ('+m.type+' \u2022 Mach '+m.mach+')</option>';}
}
$('weaponSelect').onchange=function(){
  var idx=this.value,ar=getArsenalForPlace(fromInput.value);
  if(!ar||idx===''){$('weaponDesc').textContent='Custom slider values.';$('weaponSpecs').innerHTML='';return;}
  var m=ar.data.offense[+idx];
  $('machSlider').value=clamp(m.mach,1,60);$('machSlider').oninput();
  $('angleSlider').value=clamp(m.angle,1,85);$('angleSlider').oninput();
  setMode(m.mode);
  $('evasionSlider').value=clamp(m.evasion||0,0,1);$('evasionSlider').oninput();
  if(m.mode==='cruise'&&m.altKm<1)cruiseAltMi=Math.max(0.03,m.altKm*0.621371);
  $('weaponDesc').textContent=m.desc;
  var from=resolveSeedPlaceFast(fromInput.value),to=resolveSeedPlaceFast(toInput.value);
  var html='Range: '+m.range.toLocaleString()+' km \u2022 CEP: '+m.cep+'m \u2022 Evasion: '+(m.evasion*100).toFixed(0)+'%';
  if(from&&from.lat!=null&&to&&to.lat!=null){
    var distKm=gcDistMeters([from.lat,from.lon],[to.lat,to.lon])/1000;
    if(distKm>m.range*1.05)html+='<br><span style="color:#ff6d6d;font-weight:700">\u2718 OUT OF RANGE: '+distKm.toFixed(0)+' km / '+m.range+' km ('+(distKm-m.range).toFixed(0)+' km short)</span>';
    else if(distKm>m.range*0.9)html+='<br><span style="color:#ffd248">\u26a0 MARGINAL: '+distKm.toFixed(0)+' km near max '+m.range+' km</span>';
    else html+='<br><span style="color:#86ffbb">\u2714 IN RANGE: '+distKm.toFixed(0)+'/'+m.range+' km</span>';
    var spd=m.mach*(m.mode==='cruise'?295:330)*0.85,eta=distKm*1000/Math.max(200,spd);
    html+=' \u2022 ~'+(eta>3600?(eta/3600).toFixed(1)+' hr':eta>60?Math.ceil(eta/60)+' min':Math.ceil(eta)+' s');
  }
  $('weaponSpecs').innerHTML=html;markPreviewDirty();
};
fromInput.addEventListener('change',updateWeaponDropdown);
fromInput.addEventListener('input',function(){setTimeout(updateWeaponDropdown,300);});
setTimeout(updateWeaponDropdown,500);

/* ── Defense Activation ── */
function updateDefensePanel(){
  var toVal=toInput.value||interceptInput.value,ar=getArsenalForPlace(toVal),panel=$('defenseActivation');
  if(!ar){panel.style.display='none';return;}
  panel.style.display='block';$('defCountryName').textContent=ar.data.flag+' '+ar.country;
  var tierC={exo:'#c088ff',endo:'#40d6ff',point:'#67ff7a','high-endo':'#ff9852'};
  var tierL={exo:'EXO',endo:'ENDO',point:'POINT','high-endo':'HI-ENDO'};
  var html='';
  for(var i=0;i<ar.data.defense.length;i++){var d=ar.data.defense[i];var tc=tierC[d.tier]||'#9ef4ff';
    html+='<span style="color:'+tc+'">['+tierL[d.tier]+'] '+d.name+'</span> Mach '+d.mach+' \u2022 '+(d.altMinMi||0)+'-'+d.altMi+' mi \u2022 Pk '+(d.pk*100).toFixed(0)+'% \u2022 '+d.batteries+'x<br>';}
  $('defLayers').innerHTML=html;
}
function activateNationalDefense(opts){
  opts=opts||{};
  var toVal=opts.toVal || toInput.value || interceptInput.value, ar=getArsenalForPlace(toVal);
  if(!ar){ if(!opts.silent) addLog('No air defense data.','warn-entry'); return 0; }
  var aliveThreats=(opts.threats||projectiles).filter(function(p){
    return p && p.alive && !p.excludeFromMetrics && (!ar.country || p.defenderCountry===ar.country);
  });
  if(!aliveThreats.length){ if(!opts.silent) addLog('AUTO DEFENSE: '+escapeHtml(ar.country)+' has no inbound hostile tracks to engage right now.','info-entry'); return 0; }
  var defSite=opts.defSite || resolveSeedPlaceFast(toVal) || resolveSeedPlaceFast(interceptInput.value);
  if(!defSite||defSite.lat==null){ if(!opts.silent) addLog('Cannot resolve defense site.','warn-entry'); return 0; }
  var real=opts.realistic!=null ? !!opts.realistic : $('realisticMode').checked;
  var tierOrder={exo:0,'high-endo':1,endo:2,point:3};
  var sorted=ar.data.defense.slice().sort(function(a,b){return(tierOrder[a.tier]||2)-(tierOrder[b.tier]||2);});
  var doctrinePack=getDoctrineForCountry(ar.country);
  var ranked=aliveThreats.slice().sort(function(a,b){return threatPriorityScore(b,{fromLL:[defSite.lat,defSite.lon], doctrine:doctrinePack})-threatPriorityScore(a,{fromLL:[defSite.lat,defSite.lon], doctrine:doctrinePack});});
  var total=0,layerDelay=0,allocSummary={},siteSummary={};
  for(var i=0;i<sorted.length;i++){var layer=sorted[i];
    for(var b=0;b<layer.batteries;b++){
      var tgt=ranked[(total+b)%ranked.length];
      var node=chooseDefenseNodeForThreat(ar.country, tgt, defSite) || defSite;
      var role=((b%Math.max(1,doctrinePack.concurrentChannels||4))===0)?'primary':(((b%2)===0)?'support':'screen');
      var seeker=inferSeekerType(layer.name, layer.tier);
      var siteBoost=clamp((node.weight||0.65) + (/capital/i.test(node.kind||'')?0.05:0),0.45,1.1);
      var sensorQ=clamp((0.62+0.18*(layer.aggr||0.75)+(layer.tier==='exo'?0.08:0))*siteBoost,0.35,0.99);
      var intc=new Interceptor([node.lat,node.lon],tgt,{fromName:node.name+' ['+layer.name+']',delaySec:layer.delay+layerDelay+b*3,cmdMach:layer.mach,altBiasMi:layer.altMi,aggression:layer.aggr||0.75,allowRetarget:$('allowRetarget').checked,realistic:real,aimLL:tgt.toLL,aimAltM:layer.altMi*1609.344,pkBase:clamp(layer.pk*(0.94+0.10*siteBoost),0.05,0.995),killRadiusBase:layer.killR,systemName:layer.name,tier:layer.tier,sensorQuality:sensorQ,defenderCountry:ar.country,doctrine:doctrinePack,salvoIndex:b,salvoCount:layer.batteries,concurrentChannels:doctrinePack.concurrentChannels,reloadElasticity:doctrinePack.reloadElasticity,seekerType:seeker,raidRole:role});
      intc.defenseNodeName=node.name; intc.defenseNodeKind=node.kind||'sector'; intc.cityAware=true;
      interceptors.push(intc); total++;
      var key=(tgt.toName||tgt.fromName||'target'); allocSummary[key]=(allocSummary[key]||0)+1;
      siteSummary[node.name]=(siteSummary[node.name]||0)+1;
    }
    layerDelay+=layer.delay*0.6;
  }
  if(total>0 && !opts.silent){
    var allocTxt=Object.entries(allocSummary).slice(0,3).map(function(x){return shortPlaceName({name:x[0]})+': '+x[1];}).join(' • ');
    var siteTxt=Object.entries(siteSummary).slice(0,3).map(function(x){return shortPlaceName({name:x[0]})+'×'+x[1];}).join(' • ');
    addLog('AUTO DEFENSE LOCK: '+ar.data.flag+' '+ar.country+' • '+sorted.length+' layers • '+total+' interceptors • city sectors '+siteTxt+(allocTxt?' • raid allocation '+allocTxt:''),'good-entry');
  }
  return total;
}
$('btnActivateDefense').onclick=function(){ activateNationalDefense({silent:false}); };
toInput.addEventListener('change',updateDefensePanel);
toInput.addEventListener('input',function(){setTimeout(updateDefensePanel,300);});
interceptInput.addEventListener('change',updateDefensePanel);
setTimeout(updateDefensePanel,600);


loop();


/* ═══════════════════════════════════════════════════════
   V9 ADDITIONS — MIRV / DECOY / REENTRY SPLIT / DISCRIMINATION
   ═══════════════════════════════════════════════════════ */
const PAYLOAD_STATE={nextRaidId:1, groups:{}};
function getCurrentSelectedWeapon(){
  const ar=getArsenalForPlace(fromInput.value), idx=$('weaponSelect').value;
  if(!ar || idx==='') return null;
  const w=ar.data.offense[+idx];
  return w ? Object.assign({country:ar.country}, w) : null;
}
function inferPayloadPlanFromWeapon(w, mode, mach){
  const name=((w&&w.name)||'').toLowerCase(), desc=((w&&w.desc)||'').toLowerCase(), typ=((w&&w.type)||'').toLowerCase();
  const txt=name+' '+desc+' '+typ;
  const plan={rvs:1, decoys:0, splitFrac:null, splitAltMi:null, cloudDensity:0, maneuverableReentry:false, label:'single-body'};
  if(/mirv|multiple independently|sub-launched|m51|trident ii|df-41|rs-28|bulava|hwasong-17|hwasong-15|jericho iii/.test(txt)){
    plan.rvs = /m51/.test(txt) ? 6 : (/trident|rs-28|df-41/.test(txt) ? 8 : 4);
    plan.decoys = Math.max(2, Math.round(plan.rvs*1.5));
    plan.splitFrac = 0.42;
    plan.splitAltMi = 55;
    plan.cloudDensity = 0.55;
    plan.label='MIRV bus';
  } else if(/hgv|fattah|avangard|hypersonic/.test(txt) || mode==='evasive' || mach>=12){
    plan.rvs = 1;
    plan.decoys = mach>=15 ? 2 : 1;
    plan.splitFrac = 0.58;
    plan.splitAltMi = 28;
    plan.cloudDensity = 0.32;
    plan.maneuverableReentry = true;
    plan.label='MaRV/HGV package';
  } else if(mode==='ballistic' && mach>=8){
    plan.rvs = 1;
    plan.decoys = 1;
    plan.splitFrac = 0.63;
    plan.splitAltMi = 22;
    plan.cloudDensity = 0.18;
    plan.label='penetration-aid package';
  } else if(mode==='cruise'){
    plan.rvs = 1;
    plan.decoys = 0;
    plan.label='single-body cruise';
  }
  return plan;
}
function configurePayloadForAttack(p, weapon){
  const plan=inferPayloadPlanFromWeapon(weapon, p.mode, p.cmdMach);
  p.weaponMeta=weapon||null;
  p.payloadPlan=plan;
  p.payloadDeployed=false;
  p.excludeFromMetrics=!!(plan && (plan.rvs>1 || plan.decoys>0));
  p.raidId='raid-'+(PAYLOAD_STATE.nextRaidId++);
  PAYLOAD_STATE.groups[p.raidId]={source:p.fromName||'', target:p.toName||'', aliveCredible:plan.rvs||1, decoys:plan.decoys||0, rvs:plan.rvs||1};
}
const _projClone=Projectile.prototype.cloneForForecast;
Projectile.prototype.cloneForForecast=function(){
  const c=_projClone.call(this);
  c.kind=this.kind; c.weaponMeta=this.weaponMeta||null; c.payloadPlan=this.payloadPlan?Object.assign({},this.payloadPlan):null; c.excludeFromMetrics=!!this.excludeFromMetrics; c.raidId=this.raidId||null;
  return c;
};
const _projLateral=Projectile.prototype.lateralOffsetAngle;
Projectile.prototype.lateralOffsetAngle=function(){
  let off=_projLateral.call(this);
  if(this.extraSpreadAngle){
    const frac=clamp(this.progress,0,1), win=Math.sin(Math.PI*frac);
    off += this.extraSpreadAngle*win*Math.sin((this.extraSpreadFreq||1.2)*Math.PI*frac + (this.extraSpreadPhase||0));
  }
  if(this.biasOffsetAngle){
    off += this.biasOffsetAngle*Math.sin(Math.PI*clamp(this.progress,0,1));
  }
  return off;
};
function spawnPayloadChildren(parent){
  if(!parent || parent.payloadDeployed || !parent.payloadPlan) return [];
  const plan=parent.payloadPlan;
  if((plan.rvs||1)<=1 && (plan.decoys||0)<=0) return [];
  const st=parent.getState(), startLL=st.ll, velMag=Math.max(parent.getAirspeed?parent.getAirspeed():0, parent.alongSpeed||350), cloud=plan.cloudDensity||0;
  const spawned=[], total=(plan.rvs||1)+(plan.decoys||0), realRVs=Math.max(1, plan.rvs||1);
  const grp=PAYLOAD_STATE.groups[parent.raidId] || {aliveCredible:realRVs, decoys:plan.decoys||0, rvs:realRVs};
  PAYLOAD_STATE.groups[parent.raidId]=grp;
  for(let i=0;i<total;i++){
    const isDecoy=i>=realRVs;
    const lane=i-(total-1)/2;
    const m=isDecoy ? clamp(parent.cmdMach*(0.82+0.06*Math.random()),0.8,28) : clamp(parent.cmdMach*(plan.maneuverableReentry?0.95:0.90),1,32);
    const mode=isDecoy ? (parent.mode==='ballistic'?'guided':parent.mode) : (plan.maneuverableReentry?'evasive':parent.mode);
    const elev=isDecoy ? clamp(parent.elevDeg*0.72,2,55) : clamp(parent.elevDeg*0.82,2,65);
    const child=new Projectile(startLL, parent.toLL, m, elev, mode, {fromName:parent.fromName,toName:parent.toName,cruiseAltMi:parent.cruiseAltMi,evasiveness:clamp(parent.evasiveness + (isDecoy?0.08:0.18),0,1),realistic:parent.realistic,speedHold:parent.speedHold,kind:isDecoy?'decoy':'rv'});
    child.alt=Math.max(500, st.alt + (isDecoy?Math.random()*4000:0));
    child.alongSpeed=Math.max(220, velMag*(isDecoy?0.93:1.00));
    child.vertSpeed=(st.vel && isFinite(st.vel.y)) ? Math.max(-3500, Math.min(3500, st.vel.dot(child.currentU()))) : child.vertSpeed;
    child.t=Math.max(0,parent.t);
    child.raidId=parent.raidId;
    child.parentBus=true;
    child.weaponMeta=parent.weaponMeta||null;
    child.payloadPlan=null;
    child.excludeFromMetrics=!!isDecoy;
    child.credible=!isDecoy;
    child.cloudDensity=cloud;
    child.decoyStrength=isDecoy ? clamp(0.65+0.20*Math.random()+0.12*cloud,0.4,1.0) : clamp(0.08+0.20*cloud,0.05,0.45);
    child.discriminationDifficulty=isDecoy ? clamp(0.72+0.18*Math.random()+0.12*cloud,0.55,1.0) : clamp(0.25+0.25*cloud,0.15,0.7);
    child.radarCrossSection=isDecoy ? clamp(0.7+0.5*Math.random(),0.5,1.4) : clamp(0.6+0.3*Math.random(),0.45,1.0);
    child.irSignature=isDecoy ? clamp(0.4+0.4*Math.random(),0.3,1.0) : clamp(0.7+0.2*Math.random(),0.6,1.0);
    child.extraSpreadAngle=((isDecoy?1.25:0.85)*lane)*(0.010/Math.max(1,total));
    child.biasOffsetAngle=((isDecoy?1.2:0.8)*lane)*(0.024/Math.max(1,total));
    child.extraSpreadPhase=i*0.75 + Math.random()*0.5;
    child.extraSpreadFreq=isDecoy?1.8:1.2;
    child.label=isDecoy?('Decoy '+(i-realRVs+1)):('RV '+(i+1));
    child.modeColor=isDecoy?'#ffd36b':null;
    spawned.push(child);
  }
  parent.payloadDeployed=true;
  parent.excludeFromMetrics=true;
  parent.visible=false;
  parent.alive=false;
  parent.destroyReason='post-boost deployment';
  parent.impactPosU=parent.currentPathU().clone();
  const credibleAdded=Math.max(0, realRVs-1);
  if(credibleAdded>0){ shots += credibleAdded; shotCount.textContent=shots; }
  projectiles.push(...spawned);
  addLog('BUS deployment from '+shortPlaceName({name:parent.fromName})+' released '+realRVs+' credible RV'+(realRVs>1?'s':'')+' and '+(plan.decoys||0)+' decoy'+((plan.decoys||0)!==1?'s':'')+'.', 'info-entry');
  return spawned;
}
const _projUpdate=Projectile.prototype.update;
Projectile.prototype.update=function(){
  if(this.alive && !this.payloadDeployed && this.payloadPlan){
    const plan=this.payloadPlan;
    const splitFrac=plan.splitFrac==null?null:plan.splitFrac;
    const splitAlt=(plan.splitAltMi==null?null:plan.splitAltMi*1609.344);
    const shouldSplit=((splitFrac!=null && this.progress>=splitFrac) || (splitAlt!=null && this.alt<=splitAlt && this.t>5));
    if(shouldSplit){ spawnPayloadChildren(this); }
  }
  _projUpdate.call(this);
  if(this.alive && !this.payloadDeployed && this.payloadPlan){
    const plan=this.payloadPlan;
    const splitFrac=plan.splitFrac==null?null:plan.splitFrac;
    const splitAlt=(plan.splitAltMi==null?null:plan.splitAltMi*1609.344);
    const shouldSplit=((splitFrac!=null && this.progress>=splitFrac) || (splitAlt!=null && this.alt<=splitAlt && this.t>5));
    if(shouldSplit){ spawnPayloadChildren(this); }
  }
};
function selectThreatForInterceptor(interceptor,currentTarget){
  const alive=projectiles.filter(p=>p.alive);
  if(!alive.length) return currentTarget||null;
  let best=currentTarget&&currentTarget.alive?currentTarget:null, bestScore=-1e9;
  for(const p of alive){
    const assignment=interceptors.filter(i=>i.alive && i.launched && i!==interceptor && i.linkTarget===p).length;
    let score=threatPriorityScore(p, interceptor)/(1+0.65*assignment);
    if(p.kind==='decoy') score*=0.28;
    if(p.kind==='rv') score*=1.15;
    if(p.cloudDensity) score*=1+0.06*p.cloudDensity;
    if(score>bestScore){ bestScore=score; best=p; }
  }
  return best;
}
const _getAimState=Interceptor.prototype.getAimState;
Interceptor.prototype.getAimState=function(){
  if(this.allowRetarget){
    const best=selectThreatForInterceptor(this, this.linkTarget);
    if(best) this.linkTarget=best;
  }
  return _getAimState.call(this);
};
const _threatPriorityScore=threatPriorityScore;
threatPriorityScore=function(p, interceptor){
  let base=_threatPriorityScore(p, interceptor);
  if(p && p.kind==='decoy') base*=0.22 + 0.12*(p.discriminationDifficulty||0.6);
  else if(p && p.kind==='rv') base*=1.10;
  if(p && p.cloudDensity) base*=1 + 0.05*p.cloudDensity;
  return base;
};
const _computeSeekerState=computeSeekerState;
computeSeekerState=function(interceptor, geom){
  const state=_computeSeekerState(interceptor, geom);
  const tgt=interceptor&&interceptor.linkTarget?interceptor.linkTarget:null;
  if(!tgt) return state;
  const seeker=(interceptor.seekerType||'activeRadar');
  const discBase=seeker==='hitToKill'?0.82:(seeker==='activeRadar'?0.72:(seeker==='semiActiveRadar'?0.66:(seeker==='ir'?0.54:0.60)));
  const cloudPenalty=tgt.cloudDensity?clamp(1-0.16*tgt.cloudDensity*(seeker==='hitToKill'?0.6:1.0),0.72,1.0):1;
  if(tgt.kind==='decoy'){
    const fool=clamp((tgt.discriminationDifficulty||0.7)*(1-discBase*0.62),0.05,0.55);
    state.tracking=clamp(state.tracking*(0.92+0.12*(tgt.radarCrossSection||1))*cloudPenalty,0.12,1.22);
    state.pkFactor=clamp(state.pkFactor*(0.88+0.20*(1-fool)),0.14,1.28);
    state.failureMode=state.failureMode||((seeker==='ir')?'thermal decoy / bloom':'decoy seduction');
  } else {
    const discriminationDrag=clamp(1 - 0.20*(tgt.cloudDensity||0)*(1-discBase),0.70,1.0);
    const signatureFactor=(seeker==='ir')?(tgt.irSignature||0.85):(tgt.radarCrossSection||0.85);
    state.tracking=clamp(state.tracking*discriminationDrag*cloudPenalty*(0.90+0.14*signatureFactor),0.12,1.22);
    state.pkFactor=clamp(state.pkFactor*discriminationDrag*(0.92+0.10*discBase),0.14,1.26);
  }
  return state;
};
const _registerAttackOutcome=registerAttackOutcome;
registerAttackOutcome=function(p){
  if(!p || p.excludeFromMetrics) { if(p) p._outcomeRecorded=true; return; }
  _registerAttackOutcome(p);
};
const _registerInterceptorOutcome=registerInterceptorOutcome;
registerInterceptorOutcome=function(i){
  _registerInterceptorOutcome(i);
};
const _updateHud=updateHud;
updateHud=function(){
  _updateHud();
  const atk=projectiles.find(p=>p.alive && !p.excludeFromMetrics) || projectiles.find(p=>p.alive);
  if(!atk || !hud || !atk.kind) return;
  if(atk.kind==='rv' || atk.kind==='decoy'){
    hud.innerHTML += '<br>PAYLOAD <span class="val">'+escapeHtml((atk.kind==='decoy'?'DECOY':'RV')+(atk.label?' • '+atk.label:''))+'</span> • raid <span class="val">'+escapeHtml(atk.raidId||'single')+'</span> • cloud <span class="val">'+((atk.cloudDensity||0)*100).toFixed(0)+'%</span>';
  }
};
const _drawAttackLine=drawAttackLine;
drawAttackLine=function(p,col){
  const lineCol=(p && p.kind==='decoy') ? '#ffd36b' : col;
  _drawAttackLine(p,lineCol);
};
const _drawProjectileTrace=drawProjectileTrace;
drawProjectileTrace=function(p,col){
  const lineCol=(p && p.kind==='decoy') ? '#ffd36b' : col;
  _drawProjectileTrace(p,lineCol);
};
const _updateEngagementPanel=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel();
  const decoysAlive=projectiles.filter(p=>p.alive && p.kind==='decoy').length;
  const rvsAlive=projectiles.filter(p=>p.alive && p.kind==='rv').length;
  engagementSummary.innerHTML += '<br>Live payloads: credible RVs <span style="color:#ffcf7a">'+rvsAlive+'</span> • decoys <span style="color:#ffd36b">'+decoysAlive+'</span>.';
};
const _fireProjectile=fireProjectile;
fireProjectile=async function(){
  return _fireProjectile.apply(this, arguments);
};
const _oldBtnFire=$('btnFire').onclick;
$('btnFire').onclick=async ()=>{
  const w=getCurrentSelectedWeapon();
  const oldPush=projectiles.push.bind(projectiles);
  let configured=false;
  projectiles.push=function(...items){
    for(const it of items){
      if(!configured && it && it.kind==='attack'){
        configurePayloadForAttack(it,w);
        configured=true;
      }
    }
    return oldPush(...items);
  };
  try{ await _oldBtnFire(); }
  finally{ projectiles.push=oldPush; }
};
$('previewNote').innerHTML='<b>LIVE PREVIEW</b><br>Drag Mach, elevation, and evasiveness. MIRV buses, penetration decoys, and reentry-body splitting now deploy automatically when the selected system profile supports them.';


/*
   V10 ADDITIONS - SYSTEM-SPECIFIC COUNTERMEASURES / ECM / ECCM
*/
const ECM_DB={
  default:{label:'Baseline package', jammer:0.10, drfm:0.06, chaff:0.08, decoyCtl:0.08, emissionDiscipline:0.08, stealth:0.05, thermalMask:0.04, terminalWeave:0.08},
  us_icbm:{label:'US strategic aids', jammer:0.16, drfm:0.14, chaff:0.14, decoyCtl:0.16, emissionDiscipline:0.16, stealth:0.10, thermalMask:0.08, terminalWeave:0.10},
  us_cruise:{label:'US low-observable cruise aids', jammer:0.18, drfm:0.16, chaff:0.10, decoyCtl:0.08, emissionDiscipline:0.18, stealth:0.22, thermalMask:0.14, terminalWeave:0.12},
  ru_hgv:{label:'Russian HGV penetration aids', jammer:0.18, drfm:0.18, chaff:0.10, decoyCtl:0.18, emissionDiscipline:0.12, stealth:0.12, thermalMask:0.12, terminalWeave:0.18},
  ru_icbm:{label:'Russian MIRV bus aids', jammer:0.16, drfm:0.20, chaff:0.16, decoyCtl:0.22, emissionDiscipline:0.10, stealth:0.08, thermalMask:0.08, terminalWeave:0.10},
  cn_hgv:{label:'Chinese hypersonic package', jammer:0.16, drfm:0.17, chaff:0.12, decoyCtl:0.18, emissionDiscipline:0.16, stealth:0.12, thermalMask:0.10, terminalWeave:0.16},
  il_layered:{label:'Israeli smart countermeasures', jammer:0.12, drfm:0.12, chaff:0.10, decoyCtl:0.12, emissionDiscipline:0.18, stealth:0.16, thermalMask:0.10, terminalWeave:0.12},
  ir_hgv:{label:'Iranian maneuver package', jammer:0.10, drfm:0.09, chaff:0.08, decoyCtl:0.10, emissionDiscipline:0.08, stealth:0.08, thermalMask:0.08, terminalWeave:0.16},
  generic_cruise:{label:'Cruise penetration aids', jammer:0.12, drfm:0.10, chaff:0.08, decoyCtl:0.06, emissionDiscipline:0.14, stealth:0.16, thermalMask:0.12, terminalWeave:0.12},
  generic_ballistic:{label:'Ballistic penetration aids', jammer:0.10, drfm:0.12, chaff:0.10, decoyCtl:0.14, emissionDiscipline:0.08, stealth:0.04, thermalMask:0.06, terminalWeave:0.10}
};
const ECCM_BY_SEEKER={
  hitToKill:{jamResist:0.82, decoyFilter:0.86, clutterReject:0.84, thermalGate:0.48},
  activeRadar:{jamResist:0.72, decoyFilter:0.74, clutterReject:0.72, thermalGate:0.38},
  semiActiveRadar:{jamResist:0.64, decoyFilter:0.68, clutterReject:0.66, thermalGate:0.32},
  commandGuided:{jamResist:0.58, decoyFilter:0.60, clutterReject:0.62, thermalGate:0.28},
  ir:{jamResist:0.34, decoyFilter:0.54, clutterReject:0.44, thermalGate:0.82}
};
function countermeasureStrength(cm){
  if(!cm) return 0.10;
  return clamp(0.22*(cm.jammer||0)+0.18*(cm.drfm||0)+0.15*(cm.chaff||0)+0.17*(cm.decoyCtl||0)+0.10*(cm.emissionDiscipline||0)+0.08*(cm.stealth||0)+0.05*(cm.thermalMask||0)+0.05*(cm.terminalWeave||0),0.02,0.95);
}
function mergeCountermeasure(a,b){ const o=Object.assign({}, a||{}); for(const k in (b||{})) o[k]=b[k]; return o; }
function inferCountermeasureProfile(weapon, projectile){
  const w=weapon||projectile&&projectile.weaponMeta||null;
  const country=(w&&w.country)||'';
  const name=((w&&w.name)||projectile&&projectile.systemName||'').toLowerCase();
  const typ=((w&&w.type)||'').toLowerCase();
  let base=ECM_DB.default;
  if(/trident|minuteman/.test(name)) base=ECM_DB.us_icbm;
  else if(/tomahawk|agm-183|lrasm|storm shadow|taurus|kh-101|kalibr/.test(name)) base=ECM_DB.us_cruise;
  else if(/avangard|kinzhal|zircon|rs-28|yars/.test(name)) base=/avangard|kinzhal|zircon/.test(name)?ECM_DB.ru_hgv:ECM_DB.ru_icbm;
  else if(/df-17|df-41|df-26|yj-21/.test(name)) base=/df-17|yj-21/.test(name)?ECM_DB.cn_hgv:ECM_DB.generic_ballistic;
  else if(/jericho|lora|delilah/.test(name)) base=ECM_DB.il_layered;
  else if(/fattah|sejjil|paveh/.test(name)) base=/fattah/.test(name)?ECM_DB.ir_hgv:ECM_DB.generic_ballistic;
  else if((projectile&&projectile.mode)==='cruise' || /cruise/.test(typ)) base=ECM_DB.generic_cruise;
  else if((projectile&&projectile.mode)==='ballistic' || /icbm|mrbm|srbm|irbm|hgv/.test(typ)) base=ECM_DB.generic_ballistic;
  let cm=Object.assign({country:country||'Unknown'}, base);
  if(country==='United States') cm=mergeCountermeasure(cm,{emissionDiscipline:cm.emissionDiscipline+0.02, stealth:cm.stealth+0.02});
  if(country==='Russia') cm=mergeCountermeasure(cm,{drfm:cm.drfm+0.02, decoyCtl:cm.decoyCtl+0.02});
  if(country==='China') cm=mergeCountermeasure(cm,{jammer:cm.jammer+0.02, emissionDiscipline:cm.emissionDiscipline+0.02});
  if(country==='Israel') cm=mergeCountermeasure(cm,{stealth:cm.stealth+0.03, emissionDiscipline:cm.emissionDiscipline+0.03});
  cm.effectiveness=countermeasureStrength(cm);
  return cm;
}
const _configurePayloadForAttack_base=configurePayloadForAttack;
configurePayloadForAttack=function(p, weapon){
  _configurePayloadForAttack_base(p, weapon);
  p.systemName=(weapon&&weapon.name)||p.systemName||'Attack system';
  p.countermeasureProfile=inferCountermeasureProfile(weapon, p);
  p.ecmStrength=p.countermeasureProfile.effectiveness;
  p.jamStrength=clamp((p.countermeasureProfile.jammer||0)+(p.countermeasureProfile.drfm||0)*0.8,0,1);
  p.stealthFactor=clamp((p.countermeasureProfile.stealth||0)+(p.countermeasureProfile.emissionDiscipline||0)*0.6,0,1);
  if(p.payloadPlan){
    p.payloadPlan.cloudDensity=clamp((p.payloadPlan.cloudDensity||0)+0.25*(p.countermeasureProfile.decoyCtl||0),0,0.95);
  }
};
const _spawnPayloadChildren_base=spawnPayloadChildren;
spawnPayloadChildren=function(parent){
  const kids=_spawnPayloadChildren_base(parent) || [];
  for(const child of kids){
    child.systemName=parent.systemName||child.systemName;
    child.weaponMeta=parent.weaponMeta||null;
    child.countermeasureProfile=parent.countermeasureProfile||inferCountermeasureProfile(parent.weaponMeta,parent);
    child.ecmStrength=clamp((parent.ecmStrength||countermeasureStrength(child.countermeasureProfile))*(child.kind==='decoy'?1.10:1.0),0,1);
    child.jamStrength=clamp((parent.jamStrength||0.1)*(child.kind==='decoy'?1.18:1.0),0,1);
    child.stealthFactor=clamp((parent.stealthFactor||0.08)*(child.kind==='decoy'?0.7:1.0),0,1);
    child.discriminationDifficulty=clamp((child.discriminationDifficulty||0.5)+0.30*(child.countermeasureProfile.decoyCtl||0),0.05,0.98);
    child.cloudDensity=clamp((child.cloudDensity||0)+0.20*(child.countermeasureProfile.chaff||0)+0.18*(child.countermeasureProfile.decoyCtl||0),0,1);
    if(child.kind==='rv'){
      child.radarCrossSection=clamp((child.radarCrossSection||0.85)*(1-0.24*(child.countermeasureProfile.stealth||0)),0.25,1.2);
      child.irSignature=clamp((child.irSignature||0.85)*(1-0.20*(child.countermeasureProfile.thermalMask||0)),0.25,1.2);
    }
  }
  return kids;
};
metrics.ecmSamples=[];
metrics.eccmSamples=[];
const _computeSeekerState_v10_prev=computeSeekerState;
computeSeekerState=function(interceptor, geom){
  const state=_computeSeekerState_v10_prev(interceptor, geom);
  const tgt=interceptor&&interceptor.linkTarget?interceptor.linkTarget:null;
  if(!tgt) return state;
  const seeker=interceptor.seekerType||'activeRadar';
  const eccm=ECCM_BY_SEEKER[seeker] || ECCM_BY_SEEKER.activeRadar;
  const cm=tgt.countermeasureProfile || inferCountermeasureProfile(tgt.weaponMeta,tgt);
  const jamBurden=clamp(((cm.jammer||0)+(cm.drfm||0)*1.05+(tgt.jamStrength||0)*0.65) * (1-(eccm.jamResist||0)*0.72), 0, 0.65);
  const clutterBurden=clamp(((cm.chaff||0)+(tgt.cloudDensity||0)*0.55) * (1-(eccm.clutterReject||0)*0.70), 0, 0.45);
  const stealthBurden=clamp(((tgt.stealthFactor||0)+(cm.stealth||0)*0.8+(cm.emissionDiscipline||0)*0.6) * (seeker==='ir'?0.18:0.42),0,0.26);
  const thermalBurden=clamp(((cm.thermalMask||0)+(tgt.kind==='decoy'?0.14:0)) * (seeker==='ir'?(1-(eccm.thermalGate||0)*0.78):0.16),0,0.30);
  const weaveBurden=clamp(((cm.terminalWeave||0)+0.4*(geom.targetEvasion||0))*(geom.targetMach>6?1.0:0.72),0,0.28);
  const totalBurden=clamp(jamBurden+clutterBurden+stealthBurden+thermalBurden+weaveBurden,0,0.82);
  const eccmRelief=clamp(0.70+0.20*(eccm.jamResist||0)+0.10*(eccm.decoyFilter||0),0.45,1.0);
  state.tracking=clamp(state.tracking*(1-totalBurden)*(0.92+0.10*eccmRelief),0.08,1.24);
  state.pkFactor=clamp(state.pkFactor*(1-0.72*totalBurden)*(0.94+0.08*eccmRelief),0.08,1.30);
  state.radiusFactor=clamp(state.radiusFactor*(1-0.35*jamBurden-0.22*weaveBurden),0.22,1.24);
  state.ecmBurden=totalBurden;
  state.eccmRelief=eccmRelief;
  state.failureMode=state.failureMode || (totalBurden>0.38 ? (seeker==='ir'?'IR seduction / thermal masking':'ECM breaklock') : '');
  return state;
};
const _interceptor_updateScalarStep_v10_prev=Interceptor.prototype.updateScalarStep;
Interceptor.prototype.updateScalarStep=function(){
  _interceptor_updateScalarStep_v10_prev.call(this);
  if(this.alive){
    metrics.ecmSamples.push(this.seekerStateLast&&this.seekerStateLast.ecmBurden||0);
    metrics.eccmSamples.push(this.seekerStateLast&&this.seekerStateLast.eccmRelief||0);
    if(metrics.ecmSamples.length>240) metrics.ecmSamples.shift();
    if(metrics.eccmSamples.length>240) metrics.eccmSamples.shift();
  }
};
const _updateEngagementPanel_v10_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v10_prev();
  const ecmMean=safeMean(metrics.ecmSamples||[]), eccmMean=safeMean(metrics.eccmSamples||[]);
  if(engagementSummary){
    engagementSummary.innerHTML += '<br>Electronic fight: ECM burden <span style="color:#ffd36b">'+(ecmMean*100).toFixed(0)+'%</span> • ECCM recovery <span style="color:#9ef4ff">'+(eccmMean*100).toFixed(0)+'%</span>.';
  }
};
const _updateHud_v10_prev=updateHud;
updateHud=function(){
  _updateHud_v10_prev();
  const def=interceptors.find(i=>i.alive && i.launched);
  const atk=projectiles.find(p=>p.alive && !p.excludeFromMetrics) || projectiles.find(p=>p.alive);
  if(def && def.seekerStateLast){
    hud.innerHTML += '<br>EW <span class="val">ECM '+((def.seekerStateLast.ecmBurden||0)*100).toFixed(0)+'%</span> • ECCM <span class="val">'+((def.seekerStateLast.eccmRelief||0)*100).toFixed(0)+'%</span>';
  }
  if(atk && atk.countermeasureProfile){
    hud.innerHTML += '<br>CM <span class="val">'+escapeHtml(atk.countermeasureProfile.label||'package')+'</span> • jam <span class="val">'+((atk.jamStrength||0)*100).toFixed(0)+'%</span> • stealth <span class="val">'+((atk.stealthFactor||0)*100).toFixed(0)+'%</span>';
  }
};
const _clearAll_v10_prev=$('btnClear').onclick;
$('btnClear').onclick=()=>{ metrics.ecmSamples=[]; metrics.eccmSamples=[]; _clearAll_v10_prev(); };



/* ═══════════════════════════════════════════════════════
   V13 ADDITIONS — CAMPAIGN STOCKPILES / RELIABILITY / AUTO COUNTERSTRIKE
   ═══════════════════════════════════════════════════════ */
const CAMPAIGN_STATE={countries:{}, retaliationLedger:{}, exchangeEvents:[], defenseFireLedger:{}, airDefenseAlwaysOn:true};
metrics.stockpileSamples=[];
metrics.exchangeCount=0;
metrics.failedAttackLaunches=0;
metrics.failedDefenseLaunches=0;

function complexityPenalty(name,type,kind){
  const txt=((name||'')+' '+(type||'')).toLowerCase();
  let p=0;
  if(/hgv|hypersonic|arrw|avangard|kinzhal|zircon|fattah|df-17/.test(txt)) p+=0.08;
  if(/mirv|icbm|slbm|trident|minuteman|m51|sarmat|df-41|yars|hwasong/.test(txt)) p+=0.05;
  if(/gbi|sm-3|thaad|arrow 3|hq-19|nudol|pdv/.test(txt)) p+=0.07;
  if(/patriot|s-400|s-500|aster|sea viper|sky bow|l-sam/.test(txt)) p+=0.03;
  if(kind==='offense' && /cruise|tomahawk|scalp|storm shadow|delilah|taurus|kalibr|kh-101|cj-20|paveh/.test(txt)) p-=0.02;
  if(/scud|df-3a|old|soviet-era/.test(txt)) p+=0.06;
  return clamp(p, -0.03, 0.14);
}
function projectedSystemReliability(country, item, kind){
  const d=getDoctrineForCountry(country||'Default');
  const maint=d.maintenance||0.74, train=d.training||0.75, c2=d.c2||0.78;
  let base=kind==='defense' ? 0.89 : 0.90;
  base += 0.08*(maint-0.7) + 0.04*(train-0.7) + 0.02*(c2-0.7);
  base -= complexityPenalty(item&&item.name, item&&item.type, kind);
  return clamp(base, 0.58, 0.985);
}
function estimateOffenseInventory(country,w){
  const txt=((w&&w.name)||'').toLowerCase(), typ=((w&&w.type)||'').toLowerCase();
  const bp=bandParams(country||'Default');
  let base;
  if(/icbm|slbm/.test(typ) || /trident|minuteman|m51|sarmat|df-41|yars|hwasong|jericho iii/.test(txt)) base=bp.band==='super'?16:(bp.band==='strategic'?10:4);
  else if(/hgv|hypersonic/.test(typ) || /kinzhal|zircon|df-17|fattah|arrw|yj-21/.test(txt)) base=bp.band==='super'?28:(bp.band==='strategic'?18:(bp.band==='advanced'?10:5));
  else if(/cruise|tomahawk|storm shadow|scalp|taurus|kh-101|kalibr|cj-20|paveh|delilah/.test(txt)) base=bp.band==='super'?72:(bp.band==='strategic'?46:(bp.band==='advanced'?28:(bp.band==='regional'?18:10)));
  else if(/srbm|mrbm|irbm|tactical|prsm|atacms|lora|tayfun|iskander|agni|hyunmoo|shaheen/.test(txt+ ' ' + typ)) base=bp.band==='super'?48:(bp.band==='strategic'?32:(bp.band==='advanced'?22:(bp.band==='regional'?14:8)));
  else base=bp.band==='super'?30:(bp.band==='strategic'?22:(bp.band==='advanced'?16:(bp.band==='regional'?10:5)));
  const sysScale=(w&&w.stockScale!=null)?w.stockScale:1;
  return Math.max(1, Math.round(base * bp.offenseScale * sysScale));
}
function estimateDefenseInventory(country,layer,doc){
  const bp=bandParams(country||'Default');
  const batt=Math.max(1, layer&&layer.batteries||1);
  const tier=(layer&&layer.tier)||'endo';
  const mult=tier==='exo'?6:(tier==='high-endo'?10:(tier==='endo'?15:20));
  const raid=Math.max(0.45, (doc&&doc.raidCapacityNorm)||0.6);
  const stockScale=(layer&&layer.stockScale!=null)?layer.stockScale:1;
  const base=batt*mult*raid*bp.defenseScale*stockScale;
  return Math.max(2, Math.round(base));
}
function initCountryCampaign(country){
  if(!country) country='Default';
  if(CAMPAIGN_STATE.countries[country]) return CAMPAIGN_STATE.countries[country];
  const ar=ARSENAL[country];
  const doc=getDoctrineForCountry(country);
  const state={country, doctrine:doc, offense:{}, defense:{}, retaliationsSent:0, retaliationsRecv:0};
  if(ar){
    for(const w of (ar.offense||[])){
      state.offense[w.name]={remaining:estimateOffenseInventory(country,w), initial:estimateOffenseInventory(country,w), reliability:projectedSystemReliability(country,w,'offense'), item:w};
    }
    for(const l of (ar.defense||[])){
      state.defense[l.name]={remaining:estimateDefenseInventory(country,l,doc), initial:estimateDefenseInventory(country,l,doc), reliability:projectedSystemReliability(country,l,'defense'), item:l};
    }
  }
  CAMPAIGN_STATE.countries[country]=state;
  return state;
}
function resetCampaignState(){
  CAMPAIGN_STATE.countries={}; CAMPAIGN_STATE.retaliationLedger={}; CAMPAIGN_STATE.exchangeEvents=[]; CAMPAIGN_STATE.defenseFireLedger={}; CAMPAIGN_STATE.airDefenseAlwaysOn=true;
  for(const c of Object.keys(ARSENAL||{})) initCountryCampaign(c);
}
resetCampaignState();
function getCountryState(country){ return initCountryCampaign(country||'Default'); }
function stockStress(entry){
  if(!entry || !entry.initial) return 0;
  return clamp(1 - entry.remaining/Math.max(1, entry.initial), 0, 0.95);
}
function consumeInventory(entry,count){
  const n=Math.max(0, Math.floor(count||0));
  if(!entry) return 0;
  const fired=Math.min(entry.remaining, n);
  entry.remaining -= fired;
  return fired;
}
function projectedReliability(entry, doc){
  const base=entry&&entry.reliability!=null ? entry.reliability : 0.82;
  const stress=stockStress(entry);
  const maint=(doc&&doc.maintenance)||0.74;
  const shot=(doc&&doc.shotDiscipline)||0.74;
  return clamp(base*(0.97+0.04*maint)*(0.98+0.03*shot)*(1-0.18*stress), 0.45, 0.995);
}
function campaignSnapshot(){
  const lines=[];
  for(const country of ['United States','Russia','China','Israel','Iran','Japan','South Korea','India']){
    const st=CAMPAIGN_STATE.countries[country]; if(!st) continue;
    const off=Object.values(st.offense).reduce((a,b)=>a+b.remaining,0);
    const de=Object.values(st.defense).reduce((a,b)=>a+b.remaining,0);
    lines.push(country+': O '+off+' • D '+de);
  }
  return lines.slice(0,4).join(' | ');
}
function updateStockpileSamples(){
  const snaps=[];
  for(const country in CAMPAIGN_STATE.countries){
    const st=CAMPAIGN_STATE.countries[country];
    const off=Object.values(st.offense).reduce((a,b)=>a+b.remaining,0);
    const de=Object.values(st.defense).reduce((a,b)=>a+b.remaining,0);
    snaps.push({country, off, de});
  }
  metrics.stockpileSamples=snaps;
}

const _projectile_updateScalarStep_v13_prev=Projectile.prototype.updateScalarStep;
Projectile.prototype.updateScalarStep=function(){
  if(this.alive && !this._launchReliabilityChecked){
    this._launchReliabilityChecked=true;
    const rel=this.systemReliability!=null ? this.systemReliability : 0.9;
    if(Math.random() > rel){
      this.alive=false; this.destroyed=true; this.destroyReason='launch failure'; this.impactPosU=this.currentPathU().clone();
      metrics.failedAttackLaunches=(metrics.failedAttackLaunches||0)+1;
      addLog('ATTACK FAILURE: '+escapeHtml(shortPlaceName({name:this.fromName||this.attackerCountry||'Launcher'}))+' '+escapeHtml(this.systemName||'weapon')+' failed on launch readiness.', 'bad-entry');
      return;
    }
  }
  _projectile_updateScalarStep_v13_prev.call(this);
  if(this.alive && !this._midcourseFailRolled && this.progress>0.18){
    const rel=this.systemReliability!=null ? this.systemReliability : 0.9;
    const p=clamp((1-rel)*0.10*(this.mode==='ballistic'?0.8:1.0),0,0.06);
    if(Math.random() < p){
      this.alive=false; this.destroyed=true; this.destroyReason='midcourse malfunction'; this.impactPosU=this.currentPathU().clone();
      addLog('ATTACK FAILURE: '+escapeHtml(this.systemName||'weapon')+' suffered midcourse malfunction en route to '+escapeHtml(shortPlaceName({name:this.toName||this.defenderCountry||'target'}))+'.', 'bad-entry');
    }
    this._midcourseFailRolled=true;
  }
};

const _interceptor_updateScalarStep_v13_prev=Interceptor.prototype.updateScalarStep;
Interceptor.prototype.updateScalarStep=function(){
  if(this.alive && this.launched && !this._launchReliabilityChecked){
    this._launchReliabilityChecked=true;
    const rel=this.systemReliability!=null ? this.systemReliability : 0.88;
    if(Math.random() > rel){
      this.missed=true; this.failureMode='launch failure'; this.markDone('launch failure');
      metrics.failedDefenseLaunches=(metrics.failedDefenseLaunches||0)+1;
      addLog('DEFENSE FAILURE: '+escapeHtml(this.systemName||'interceptor')+' at '+escapeHtml(shortPlaceName({name:this.fromName||this.defenderCountry||'defense site'}))+' failed to launch cleanly.', 'warn-entry');
      return;
    }
  }
  _interceptor_updateScalarStep_v13_prev.call(this);
  if(this.alive && this.launched && !this._midcourseFailRolled && this.age>6/this.dt){
    const rel=this.systemReliability!=null ? this.systemReliability : 0.88;
    const p=clamp((1-rel)*0.12,0,0.08);
    if(Math.random() < p){
      this.missed=true; this.failureMode='seeker or propulsion failure'; this.markDone('malfunction');
      addLog('DEFENSE FAILURE: '+escapeHtml(this.systemName||'interceptor')+' lost track / propulsion during intercept.', 'warn-entry');
    }
    this._midcourseFailRolled=true;
  }
};

function chooseWeaponForCountry(country, preferredName){
  const ar=ARSENAL[country]; if(!ar || !ar.offense || !ar.offense.length) return null;
  const st=getCountryState(country);
  let pool=ar.offense.filter(w => st.offense[w.name] && st.offense[w.name].remaining>0);
  if(!pool.length) return null;
  if(preferredName){
    const exact=pool.find(w => w.name===preferredName);
    if(exact) return exact;
  }
  pool=pool.slice().sort((a,b)=>{
    const ea=st.offense[a.name], eb=st.offense[b.name];
    const sa=(ea.remaining/Math.max(1,ea.initial))*(ea.reliability||0.8)*(a.mach||1);
    const sb=(eb.remaining/Math.max(1,eb.initial))*(eb.reliability||0.8)*(b.mach||1);
    return sb-sa;
  });
  return pool[0];
}

function makeAttackObject(from,to,weapon,opts){
  opts=opts||{};
  const real=opts.realistic!=null ? !!opts.realistic : $('realisticMode').checked;
  const speedHold=opts.speedHold!=null ? !!opts.speedHold : $('speedHold').checked;
  const mode=(opts.mode||weapon&&weapon.mode||curMode);
  const mach=+(opts.mach!=null ? opts.mach : (weapon&&weapon.mach!=null ? weapon.mach : curMach));
  const angle=+(opts.angle!=null ? opts.angle : (weapon&&weapon.angle!=null ? weapon.angle : curAngle));
  const ev=+(opts.evasion!=null ? opts.evasion : (weapon&&weapon.evasion!=null ? weapon.evasion : evasiveness));
  const p=new Projectile([from.lat,from.lon],[to.lat,to.lon],mach,angle,mode,{fromName:from.name,toName:to.name,cruiseAltMi, evasiveness:ev, realistic:real, speedHold});
  const arFrom=getArsenalForPlace(from.name||''); const arTo=getArsenalForPlace(to.name||'');
  p.attackerCountry=(opts.attackerCountry||arFrom&&arFrom.country||'');
  p.defenderCountry=(opts.defenderCountry||arTo&&arTo.country||'');
  p.systemName=(weapon&&weapon.name)||opts.systemName||'Custom attack';
  configurePayloadForAttack(p, weapon||null);
  const st=p.attackerCountry?getCountryState(p.attackerCountry):null;
  const entry=st&&st.offense[p.systemName]?st.offense[p.systemName]:null;
  p.systemReliability=projectedReliability(entry, st&&st.doctrine);
  p.exchangeDepth=opts.exchangeDepth||0;
  p.autoCounterEnabled=opts.autoCounterEnabled!==false;
  return p;
}

function scheduleCounterstrike(attack){
  if(!attack || !attack.autoCounterEnabled) return;
  const fromC=attack.attackerCountry, toC=attack.defenderCountry;
  if(!fromC || !toC || fromC===toC) return;
  const defAr=ARSENAL[toC], atkAr=ARSENAL[fromC];
  if(!defAr || !atkAr) return;
  const ledgerKey=toC+'->'+fromC+'|d'+(attack.exchangeDepth||0);
  if(CAMPAIGN_STATE.retaliationLedger[ledgerKey]) return;
  if((attack.exchangeDepth||0) >= 1) return;
  const fromPlace=chooseCounterstrikeOrigin(toC, fromC, attack) || resolveSeedPlaceFast(attack.toName||toC);
  const toPlace=chooseCounterstrikeTarget(fromC, attack) || resolveSeedPlaceFast(attack.fromName||fromC);
  if(!fromPlace || !toPlace) return;
  const weapon=chooseWeaponForCountry(toC);
  if(!weapon) return;
  CAMPAIGN_STATE.retaliationLedger[ledgerKey]=true;
  const reactionMs=Math.round(700 + 1400*(1-(getDoctrineForCountry(toC).c2||0.75)) + 250*Math.random());
  addLog('COUNTERSTRIKE QUEUED: ACTIVE AIR-DEFENSE POSTURE HOLDS. '+escapeHtml(toC)+' preparing automatic reply from '+escapeHtml(shortPlaceName(fromPlace))+' toward '+escapeHtml(shortPlaceName(toPlace))+' in '+(reactionMs/1000).toFixed(1)+' s.', 'info-entry');
  setTimeout(function(){
    launchProjectedAttack({from:fromPlace,to:toPlace,weapon:weapon,exchangeDepth:(attack.exchangeDepth||0)+1,autoCounterEnabled:false,tag:'counterstrike'});
  }, reactionMs);
}


function activeDefendersForCountry(country){
  return interceptors.filter(i=>i && i.alive && !i.excludeFromMetrics && i.defenderCountry===country).length;
}
function activeThreatsForCountry(country){
  return projectiles.filter(p=>p && p.alive && !p.excludeFromMetrics && p.defenderCountry===country);
}
function shouldAutoLaunchDefense(country, threats){
  if(!country || !threats || !threats.length) return false;
  const doctrine=getDoctrineForCountry(country);
  const active=activeDefendersForCountry(country);
  const desired=Math.max(1, Math.min(threats.length*2, Math.max(2, Math.round((doctrine.concurrentChannels||4)*0.5))));
  if(active>=desired) return false;
  const last=CAMPAIGN_STATE.defenseFireLedger[country]||0;
  const now=(typeof performance!=='undefined' && performance.now)?performance.now():Date.now();
  const minGap=900 + 1200*Math.max(0, threats.length-1) + 900*Math.max(0,active);
  if((now-last)<minGap) return false;
  return true;
}
function autoDefenseSweep(){
  const seen={};
  const alive=projectiles.filter(p=>p && p.alive && !p.excludeFromMetrics && p.defenderCountry && ARSENAL[p.defenderCountry]);
  for(const p of alive){
    seen[p.defenderCountry]=true;
  }
  for(const country of Object.keys(seen)){
    const threats=activeThreatsForCountry(country);
    if(!shouldAutoLaunchDefense(country, threats)) continue;
    const primary=threats.slice().sort((a,b)=>a.distToTargetMeters()-b.distToTargetMeters())[0];
    const defSite=chooseDefenseNodeForThreat(country, primary, resolveSeedPlaceFast(primary && (primary.toName||country)) || resolveSeedPlaceFast(country));
    CAMPAIGN_STATE.defenseFireLedger[country]=(typeof performance!=='undefined' && performance.now)?performance.now():Date.now();
    activateNationalDefense({toVal:country, defSite:defSite, realistic:$('realisticMode').checked, threats:threats, silent:false});
  }
}

function launchProjectedAttack(opts){
  opts=opts||{};
  const from=opts.from, to=opts.to; if(!from||!to) return null;
  const arFrom=getArsenalForPlace(from.name||''), arTo=getArsenalForPlace(to.name||'');
  const attackerCountry=opts.attackerCountry||arFrom&&arFrom.country||'';
  const defenderCountry=opts.defenderCountry||arTo&&arTo.country||'';
  const weapon=opts.weapon || getCurrentSelectedWeapon() || chooseWeaponForCountry(attackerCountry);
  const attackState=attackerCountry?getCountryState(attackerCountry):null;
  const entry=attackState&&weapon?attackState.offense[weapon.name]:null;
  if(attackerCountry && weapon && (!entry || entry.remaining<=0)){
    addLog('OFFENSE DEPLETED: '+escapeHtml(attackerCountry)+' has no ready rounds left for '+escapeHtml(weapon.name)+'.', 'warn-entry');
    return null;
  }
  if(entry) consumeInventory(entry,1);
  const attack=makeAttackObject(from,to,weapon,Object.assign({},opts,{attackerCountry,defenderCountry}));
  projectiles.push(attack); shots++; shotCount.textContent=shots;
  markPreviewDirty(); syncResolvedBoxes(); updateStockpileSamples();
  const relPct=((attack.systemReliability||0)*100).toFixed(0);
  addLog(((opts.tag==='counterstrike')?'COUNTERSTRIKE ':'')+attack.mode.toUpperCase()+' '+shortPlaceName(from)+' → '+shortPlaceName(to)+' • '+gcDistMiles([from.lat,from.lon],[to.lat,to.lon]).toFixed(0)+' mi • '+escapeHtml(attack.systemName)+' • rel '+relPct+'% • '+($('realisticMode').checked?'realistic':'compressed'), opts.tag==='counterstrike'?'warn-entry':'fire-entry');
  if(defenderCountry && ARSENAL[defenderCountry]){
    CAMPAIGN_STATE.defenseFireLedger[defenderCountry]=0;
    addLog('AUTO WATCH ACTIVE: '+escapeHtml(defenderCountry)+' defensive network is hot and scanning immediately.', 'info-entry');
    activateNationalDefense({toVal:defenderCountry, defSite:to, realistic:$('realisticMode').checked, threats:projectiles.filter(p=>p&&p.alive&&p.defenderCountry===defenderCountry), silent:false});
    autoDefenseSweep();
  }
  else {
    let defense = $('interceptPolicy').value==='auto-target' ? to : ($('interceptPolicy').value==='manual' ? resolveSeedPlaceFast(interceptInput.value) : null);
    if(defense && $('interceptPolicy').value!=='off'){
      const solution=planIntercept(attack, defense);
      const batteryCount=+$('batteryCountSlider').value, salvoSpacing=+$('salvoSpacingSlider').value;
      for(let b=0; b<batteryCount; b++){
        const delayBase=+$('delaySlider').value + b*salvoSpacing;
        const aggr=Math.min(1, +$('aggrSlider').value + b*0.04);
        const defDoctrine=getDoctrineForPlace(defense.name||to.name);
        const intc=new Interceptor([defense.lat,defense.lon], attack, {fromName:defense.name, delaySec:delayBase, cmdMach:+$('defMachSlider').value, altBiasMi:+$('defAltSlider').value + b*2, aggression:aggr, allowRetarget:$('allowRetarget').checked, realistic:$('realisticMode').checked, solution, aimLL:solution&&solution.targetState?solution.targetState.ll:[to.lat,to.lon], aimAltM:solution&&solution.targetState?solution.targetState.alt:(+$('defAltSlider').value*1609.344), pkBase:clamp(0.42 + 0.34*aggr + 0.18*Math.min(1,(+$('defMachSlider').value)/16),0.12,0.93), sensorQuality:clamp(0.58 + 0.28*aggr + (solution?0.08:0),0.35,0.98), systemName:'Custom battery', tier:'custom', defenderCountry:defDoctrine.country, doctrine:defDoctrine.doctrine, salvoIndex:b, salvoCount:batteryCount, concurrentChannels:defDoctrine.doctrine.concurrentChannels, reloadElasticity:defDoctrine.doctrine.reloadElasticity,seekerType:'activeRadar',raidRole:(b===0?'primary':(b<2?'support':'screen'))});
        intc.systemReliability=0.90;
        interceptors.push(intc);
      }
    }
  }
  scheduleCounterstrike(attack);
  return attack;
}

fireProjectile=async function(){
  if(fireBusy) return; fireBusy=true; const btn=$('btnFire'), old=btn.textContent; btn.textContent='LOCATING...'; btn.disabled=true;
  try{
    const from=await resolvePlace(fromInput.value), to=await resolvePlace(toInput.value);
    if(Math.abs(from.lat-to.lat)<1e-7&&Math.abs(from.lon-to.lon)<1e-7) throw new Error('Launch and target resolve to the same coordinates.');
    fromInput.value=from.name; toInput.value=to.name;
    launchProjectedAttack({from,to,weapon:getCurrentSelectedWeapon(),exchangeDepth:0,autoCounterEnabled:true,tag:'manual'});
  }catch(err){ addLog(err && err.message ? err.message : 'Could not resolve places.', 'warn-entry'); }
  finally{ fireBusy=false; btn.textContent=old; btn.disabled=false; }
};
$('btnFire').onclick=()=>fireProjectile();

const _activateNationalDefense_v13_prev=activateNationalDefense;
activateNationalDefense=function(opts){
  opts=opts||{};
  const toVal=opts.toVal || toInput.value || interceptInput.value;
  const ar=getArsenalForPlace(toVal);
  if(!ar) return _activateNationalDefense_v13_prev(opts);
  const state=getCountryState(ar.country);
  const aliveThreats=(opts.threats||projectiles).filter(p=>p&&p.alive&&!p.excludeFromMetrics);
  if(!aliveThreats.length){ if(!opts.silent) addLog('No active threat. Launch an attack first.','warn-entry'); return 0; }
  const defSite=opts.defSite || resolveSeedPlaceFast(toVal) || resolveSeedPlaceFast(interceptInput.value);
  if(!defSite||defSite.lat==null){ if(!opts.silent) addLog('Cannot resolve defense site.','warn-entry'); return 0; }
  const real=opts.realistic!=null ? !!opts.realistic : $('realisticMode').checked;
  const tierOrder={exo:0,'high-endo':1,endo:2,point:3};
  const sorted=ar.data.defense.slice().sort((a,b)=>(tierOrder[a.tier]||2)-(tierOrder[b.tier]||2));
  const doctrinePack=getDoctrineForCountry(ar.country);
  const ranked=aliveThreats.slice().sort((a,b)=>threatPriorityScore(b,{fromLL:[defSite.lat,defSite.lon], doctrine:doctrinePack})-threatPriorityScore(a,{fromLL:[defSite.lat,defSite.lon], doctrine:doctrinePack}));
  let total=0, layerDelay=0, allocSummary={}, starved=[];
  for(const layer of sorted){
    const entry=state.defense[layer.name] || {remaining:0, reliability:projectedSystemReliability(ar.country,layer,'defense'), initial:0};
    const raidStress=Math.max(0, aliveThreats.length-(doctrinePack.raidCapacity||4))/Math.max(1,doctrinePack.raidCapacity||4);
    const readyNominal=Math.max(1, Math.round(layer.batteries * (0.72 + 0.38*(doctrinePack.shotDiscipline||0.75)) * (1-0.22*raidStress)));
    const launchCount=Math.min(entry.remaining, readyNominal);
    if(launchCount<=0){ starved.push(layer.name); continue; }
    consumeInventory(entry, launchCount);
    const sysRel=projectedReliability(entry, doctrinePack);
    for(let b=0;b<launchCount;b++){
      const tgt=ranked[(total+b)%ranked.length];
      const role=((b%Math.max(1,doctrinePack.concurrentChannels||4))===0)?'primary':(((b%2)===0)?'support':'screen');
      const seeker=inferSeekerType(layer.name, layer.tier);
      const fatigue=stockStress(entry);
      const pkAdj=clamp(layer.pk * (0.92+0.12*sysRel) * (1-0.10*fatigue), 0.08, 0.985);
      const intc=new Interceptor([defSite.lat,defSite.lon],tgt,{fromName:defSite.name+' ['+layer.name+']',delaySec:layer.delay+layerDelay+b*3,cmdMach:layer.mach,altBiasMi:layer.altMi,aggression:layer.aggr||0.75,allowRetarget:$('allowRetarget').checked,realistic:real,aimLL:tgt.toLL,aimAltM:layer.altMi*1609.344,pkBase:pkAdj,killRadiusBase:layer.killR,systemName:layer.name,tier:layer.tier,sensorQuality:clamp((0.62+0.18*(layer.aggr||0.75)+(layer.tier==='exo'?0.08:0))*(0.94+0.10*sysRel),0.35,0.98),defenderCountry:ar.country,doctrine:doctrinePack,salvoIndex:b,salvoCount:launchCount,concurrentChannels:doctrinePack.concurrentChannels,reloadElasticity:doctrinePack.reloadElasticity,seekerType:seeker,raidRole:role});
      intc.systemReliability=sysRel;
      interceptors.push(intc); total++;
      const key=(tgt.toName||tgt.fromName||'target'); allocSummary[key]=(allocSummary[key]||0)+1;
    }
    layerDelay += layer.delay*0.55;
  }
  updateStockpileSamples();
  if(total>0 && !opts.silent){
    const allocTxt=Object.entries(allocSummary).slice(0,3).map(x=>shortPlaceName({name:x[0]})+': '+x[1]).join(' • ');
    let msg='AIR DEFENSE: '+ar.data.flag+' '+ar.country+' • '+total+' launched • doctrine '+(doctrineScore(doctrinePack)*100).toFixed(0)+'% • stock '+Object.values(state.defense).reduce((a,b)=>a+b.remaining,0);
    if(allocTxt) msg += ' • '+allocTxt;
    if(starved.length) msg += ' • depleted '+starved.slice(0,2).join(', ');
    addLog(msg,'good-entry');
  }
  return total;
};

const _registerAttackOutcome_v13_prev=registerAttackOutcome;
registerAttackOutcome=function(p){
  _registerAttackOutcome_v13_prev(p);
  if(!p || !p.attackerCountry || !p.defenderCountry) return;
  CAMPAIGN_STATE.exchangeEvents.push({from:p.attackerCountry,to:p.defenderCountry,intercepted:!!p.intercepted,reason:p.destroyReason||''});
  metrics.exchangeCount=CAMPAIGN_STATE.exchangeEvents.length;
};

const _updateEngagementPanel_v13_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v13_prev();
  updateStockpileSamples();
  const top=(metrics.stockpileSamples||[]).slice().sort((a,b)=>(b.off+b.de)-(a.off+a.de)).slice(0,4);
  if(engagementSummary && top.length){
    const bits=top.map(s=>escapeHtml(shortPlaceName({name:s.country}))+': O '+s.off+' / D '+s.de).join(' • ');
    engagementSummary.innerHTML += '<br>Projected ready stocks: '+bits+'. Launch failures A/D: <span style="color:#ffb38f">'+(metrics.failedAttackLaunches||0)+'</span> / <span style="color:#9ef4ff">'+(metrics.failedDefenseLaunches||0)+'</span>. Exchanges: <span style="color:#ffd48a">'+(metrics.exchangeCount||0)+'</span>.';
  }
};

const _updateHud_v13_prev=updateHud;
updateHud=function(){
  _updateHud_v13_prev();
  const atk=projectiles.find(p=>p.alive && !p.excludeFromMetrics) || projectiles.find(p=>p.alive);
  if(atk && atk.attackerCountry){
    const aSt=getCountryState(atk.attackerCountry), dSt=atk.defenderCountry?getCountryState(atk.defenderCountry):null;
    const aOff=Object.values(aSt.offense).reduce((x,y)=>x+y.remaining,0);
    const dDef=dSt?Object.values(dSt.defense).reduce((x,y)=>x+y.remaining,0):0;
    hud.innerHTML += '<br>Stock <span class="val">'+escapeHtml(atk.attackerCountry)+': O '+aOff+'</span>' + (dSt?' • <span class="val">'+escapeHtml(atk.defenderCountry)+': D '+dDef+'</span>':'');
    hud.innerHTML += '<br>Reliability <span class="val">attack '+(((atk.systemReliability||0))*100).toFixed(0)+'%</span>';
  }
  const def=interceptors.find(i=>i.alive && i.launched);
  if(def && def.systemReliability!=null){
    hud.innerHTML += ' • <span class="val">defense '+((def.systemReliability||0)*100).toFixed(0)+'%</span>';
  }
};

const _btnClear_v13_prev=$('btnClear').onclick;
$('btnClear').onclick=()=>{ resetCampaignState(); metrics.stockpileSamples=[]; metrics.exchangeCount=0; metrics.failedAttackLaunches=0; metrics.failedDefenseLaunches=0; _btnClear_v13_prev(); };



/* ═══════════════════════════════════════════════════════
   V18 ADDITIONS — sector damage, reloads, terrain/radar masking,
   command survivability, persistent sectorized defense
   ═══════════════════════════════════════════════════════ */
metrics.offlineSectors=0;
metrics.reloadingSectors=0;
metrics.commandSamples=[];
metrics.maskingSamples=[];

function ensureCampaignAugments(){
  CAMPAIGN_STATE.sectorStatus = CAMPAIGN_STATE.sectorStatus || {};
  CAMPAIGN_STATE.commandStatus = CAMPAIGN_STATE.commandStatus || {};
  for(const country of Object.keys(ARSENAL||{})){
    if(!CAMPAIGN_STATE.commandStatus[country]){
      const bp=bandParams(country||'Default');
      const doc=getDoctrineForCountry(country);
      CAMPAIGN_STATE.commandStatus[country]={
        survivability:clamp(0.56 + 0.10*(doc.c2||0.75) + 0.08*(doc.sensorFusion||0.75) + (bp.band==='super'?0.18:(bp.band==='strategic'?0.12:(bp.band==='advanced'?0.08:(bp.band==='regional'?0.03:0)))), 0.35, 0.98),
        degradedUntil:0,
        pressure:0
      };
    }
    if(!CAMPAIGN_STATE.sectorStatus[country]) CAMPAIGN_STATE.sectorStatus[country]={};
    const nodes=getCityDefenseNodes(country, resolveSeedPlaceFast(country));
    for(const node of nodes){
      if(!CAMPAIGN_STATE.sectorStatus[country][node.name]){
        CAMPAIGN_STATE.sectorStatus[country][node.name]={
          nodeName:node.name,
          readyAt:0,
          damage:0,
          kills:0,
          launches:0,
          reloadCycleMs:0,
          watch:clamp((node.weight||0.6) + (/capital/i.test(node.kind||'')?0.1:0),0.4,1.1)
        };
      }
    }
  }
}
ensureCampaignAugments();
const _resetCampaignState_v18_prev=resetCampaignState;
resetCampaignState=function(){
  _resetCampaignState_v18_prev();
  CAMPAIGN_STATE.sectorStatus={};
  CAMPAIGN_STATE.commandStatus={};
  ensureCampaignAugments();
};
const _getCountryState_v18_prev=getCountryState;
getCountryState=function(country){
  ensureCampaignAugments();
  return _getCountryState_v18_prev(country);
};
function nowMs(){ return (typeof performance!=='undefined' && performance.now)?performance.now():Date.now(); }
function getCommandStatus(country){ ensureCampaignAugments(); return CAMPAIGN_STATE.commandStatus[normalizeCountryName(country||'Default')] || {survivability:0.7,degradedUntil:0,pressure:0}; }
function getSectorStatus(country,nodeName){
  ensureCampaignAugments();
  country=normalizeCountryName(country||'Default');
  if(!CAMPAIGN_STATE.sectorStatus[country]) CAMPAIGN_STATE.sectorStatus[country]={};
  if(!CAMPAIGN_STATE.sectorStatus[country][nodeName]) CAMPAIGN_STATE.sectorStatus[country][nodeName]={nodeName,readyAt:0,damage:0,kills:0,launches:0,reloadCycleMs:0,watch:0.65};
  return CAMPAIGN_STATE.sectorStatus[country][nodeName];
}
function commandPenaltyFactor(country){
  const cs=getCommandStatus(country), doc=getDoctrineForCountry(country||'Default');
  const now=nowMs();
  const degraded=now < (cs.degradedUntil||0) ? 1 : 0;
  return clamp((cs.survivability||0.75) * (degraded ? 0.78 : 1.0) * (0.96 + 0.05*(doc.c2||0.75)), 0.40, 1.05);
}
function terrainMaskingFactorForThreat(node, threat){
  const targetLL=threat && (threat.currentLL ? threat.currentLL() : threat.toLL);
  if(!node || !targetLL) return 1;
  const distKm=Math.max(1, gcDistMeters([node.lat,node.lon], targetLL)/1000);
  const reliefSeed=stableHash01((node.name||'')+'|'+(threat.toName||threat.fromName||''));
  const relief=0.08 + 0.32*reliefSeed;
  const altM=threat && threat.getState ? (threat.getState().alt||0) : 0;
  const lowAlt=clamp(1 - altM/22000, 0, 1);
  const distBurden=clamp(distKm/420, 0, 1);
  return clamp(1 - relief*lowAlt*(0.55+0.45*distBurden), 0.55, 1.0);
}
function radarHorizonFactorForThreat(node, threat){
  const altM=threat && threat.getState ? (threat.getState().alt||0) : 0;
  const nodeAltM=120 + 240*stableHash01((node&&node.name||'node')+'-radar-alt');
  const horizonKm=3.57*(Math.sqrt(Math.max(0,nodeAltM)) + Math.sqrt(Math.max(0,altM)));
  const distKm=threat && threat.currentLL ? gcDistMeters([node.lat,node.lon], threat.currentLL())/1000 : (threat&&threat.toLL?gcDistMeters([node.lat,node.lon], threat.toLL)/1000:0);
  if(!distKm) return 1;
  if(distKm <= horizonKm) return 1;
  const excess=(distKm-horizonKm)/Math.max(40, horizonKm);
  return clamp(1 - 0.55*excess, 0.28, 1.0);
}
function sectorReadinessFactor(country,node,threat){
  const st=getSectorStatus(country,node.name);
  const now=nowMs();
  const reloading = now < (st.readyAt||0);
  const damagePenalty=clamp(1 - 0.55*(st.damage||0), 0.35, 1.0);
  const horizon=radarHorizonFactorForThreat(node, threat);
  const terrain=terrainMaskingFactorForThreat(node, threat);
  const cmd=commandPenaltyFactor(country);
  const readiness=clamp((reloading?0.42:1.0) * damagePenalty * horizon * terrain * cmd * (st.watch||0.7), 0.16, 1.08);
  return {readiness,reloading,damagePenalty,horizon,terrain,cmd,damage:st.damage||0};
}
const _defenseNodeScore_v18_prev=defenseNodeScore;
defenseNodeScore=function(country,node,threat,doctrine){
  const base=_defenseNodeScore_v18_prev(country,node,threat,doctrine);
  const sector=sectorReadinessFactor(country,node,threat);
  return base * (0.62 + 0.60*sector.readiness);
};
function chooseDefenseNodeForThreatReady(country, threat, fallbackPlace){
  const nodes=getCityDefenseNodes(country, fallbackPlace);
  if(!nodes.length) return fallbackPlace || resolveSeedPlaceFast(country);
  let best=nodes[0], bestScore=-1;
  for(const node of nodes){
    const s=defenseNodeScore(country,node,threat,getDoctrineForCountry(country)) || 0;
    const rs=sectorReadinessFactor(country,node,threat);
    const score=s * (0.9 + 0.25*(node.weight||0.6)) * (rs.reloading?0.72:1);
    if(score>bestScore){ bestScore=score; best=node; }
  }
  return best;
}
function applySectorReload(country,nodeName,layer,doctrine,shots){
  const st=getSectorStatus(country,nodeName);
  const tier=((layer&&layer.tier)||'endo');
  const base=tier==='exo'?18000:(tier==='high-endo'?13000:(tier==='endo'?9000:6000));
  const doc=doctrine||getDoctrineForCountry(country);
  const reload=base*(0.90+0.35*Math.max(0,shots-1))*(1.16-0.30*(doc.reloadElasticity||0.7))*(1+0.55*(st.damage||0));
  st.reloadCycleMs=reload;
  st.readyAt=Math.max(st.readyAt||0, nowMs()+reload);
  st.launches=(st.launches||0)+shots;
}
function updateCampaignWearAndReload(){
  ensureCampaignAugments();
  let offline=0, reloading=0, cmd=[];
  const now=nowMs();
  for(const country of Object.keys(CAMPAIGN_STATE.sectorStatus||{})){
    const cs=getCommandStatus(country);
    cs.pressure=clamp((cs.pressure||0)*0.992,0,1.5);
    if(now > (cs.degradedUntil||0) && cs.survivability<0.985) cs.survivability=clamp(cs.survivability+0.0009,0.2,0.985);
    cmd.push(cs.survivability||0.75);
    const bag=CAMPAIGN_STATE.sectorStatus[country];
    for(const k of Object.keys(bag)){
      const s=bag[k];
      if(s.damage>0) s.damage=clamp(s.damage-0.00055,0,1);
      if((s.readyAt||0)>now) reloading++;
      if((s.damage||0)>=0.82) offline++;
    }
  }
  metrics.offlineSectors=offline;
  metrics.reloadingSectors=reloading;
  metrics.commandSamples=cmd.slice(0,20);
}
const _loop_v18_update = loop;
loop = function(){ updateCampaignWearAndReload(); _loop_v18_update(); };
const _chooseCounterstrikeTarget_v18_prev=chooseCounterstrikeTarget;
chooseCounterstrikeTarget=function(country,incomingAttack){
  const base=_chooseCounterstrikeTarget_v18_prev(country,incomingAttack);
  const nodes=getCityDefenseNodes(country, base);
  if(!nodes.length) return base;
  let best=nodes[0], bestScore=-1;
  for(const node of nodes){
    const score=(node.weight||0.6) + (/capital|central/i.test(node.kind||'')?0.18:0) + 0.12*(getSectorStatus(country,node.name).damage||0);
    if(score>bestScore){ bestScore=score; best=node; }
  }
  return best;
};
const _registerAttackOutcome_v18_prev=registerAttackOutcome;
registerAttackOutcome=function(p){
  _registerAttackOutcome_v18_prev(p);
  if(!p || !p.defenderCountry || p.intercepted) return;
  const country=p.defenderCountry;
  const node=chooseDefenseNodeForThreatReady(country, p, resolveSeedPlaceFast(p.toName||country));
  if(node && node.name){
    const st=getSectorStatus(country,node.name);
    const impactSeverity=clamp((p.mode==='ballistic'?0.22:(p.mode==='guided'?0.16:0.10)) + 0.20*Math.min(1,(p.cmdMach||1)/24) + 0.12*(p.evasiveness||p.evasion||0) - 0.06*(commandPenaltyFactor(country)-0.7), 0.04, 0.55);
    st.damage=clamp((st.damage||0) + impactSeverity, 0, 1);
    st.readyAt=Math.max(st.readyAt||0, nowMs() + 8000 + 24000*impactSeverity);
    const cs=getCommandStatus(country);
    if(/capital/i.test(node.kind||'')){
      cs.survivability=clamp((cs.survivability||0.75) - 0.06 - 0.16*impactSeverity, 0.20, 0.985);
      cs.degradedUntil=Math.max(cs.degradedUntil||0, nowMs() + 18000 + 42000*impactSeverity);
    } else {
      cs.pressure=clamp((cs.pressure||0)+0.08+0.25*impactSeverity,0,2);
      cs.survivability=clamp((cs.survivability||0.75) - 0.02*impactSeverity,0.20,0.985);
    }
  }
};
const _registerInterceptorOutcome_v18_prev=registerInterceptorOutcome;
registerInterceptorOutcome=function(i){
  _registerInterceptorOutcome_v18_prev(i);
  if(!i || !i.defenderCountry || !i.defenseNodeName) return;
  const st=getSectorStatus(i.defenderCountry,i.defenseNodeName);
  if(i.hit) st.kills=(st.kills||0)+1;
};
const _activateNationalDefense_v18_prev=activateNationalDefense;
activateNationalDefense=function(opts){
  ensureCampaignAugments();
  opts=opts||{};
  const toVal=opts.toVal || toInput.value || interceptInput.value;
  const ar=getArsenalForPlace(toVal);
  if(!ar) return _activateNationalDefense_v18_prev(opts);
  const state=getCountryState(ar.country);
  const aliveThreats=(opts.threats||projectiles).filter(p=>p&&p.alive&&!p.excludeFromMetrics&&(!p.defenderCountry || p.defenderCountry===ar.country));
  if(!aliveThreats.length){ if(!opts.silent) addLog('No active threat. Launch an attack first.','warn-entry'); return 0; }
  const real=opts.realistic!=null ? !!opts.realistic : $('realisticMode').checked;
  const doctrinePack=getDoctrineForCountry(ar.country);
  const tierOrder={exo:0,'high-endo':1,endo:2,point:3};
  const sorted=ar.data.defense.slice().sort((a,b)=>(tierOrder[a.tier]||2)-(tierOrder[b.tier]||2));
  let total=0, layerDelay=0, allocSummary={}, starved=[], sectorBits=[];
  const maxChannels=Math.max(1, Math.round((doctrinePack.concurrentChannels||4) * commandPenaltyFactor(ar.country)));
  for(const layer of sorted){
    const entry=state.defense[layer.name] || {remaining:0, reliability:projectedSystemReliability(ar.country,layer,'defense'), initial:0};
    const raidStress=Math.max(0, aliveThreats.length-maxChannels)/Math.max(1,maxChannels);
    const readyNominal=Math.max(1, Math.round(layer.batteries * (0.68 + 0.42*(doctrinePack.shotDiscipline||0.75)) * (1-0.22*raidStress)));
    const launchCount=Math.min(entry.remaining, readyNominal);
    if(launchCount<=0){ starved.push(layer.name); continue; }
    const launched=consumeInventory(entry, launchCount);
    if(launched<=0){ starved.push(layer.name); continue; }
    const sysRel=projectedReliability(entry, doctrinePack) * commandPenaltyFactor(ar.country);
    for(let b=0;b<launched;b++){
      const tgt=aliveThreats.slice().sort((a,b2)=>threatPriorityScore(b2,{fromLL:[(opts.defSite||resolveSeedPlaceFast(ar.country)||{}).lat||0,(opts.defSite||resolveSeedPlaceFast(ar.country)||{}).lon||0], doctrine:doctrinePack})-threatPriorityScore(a,{fromLL:[(opts.defSite||resolveSeedPlaceFast(ar.country)||{}).lat||0,(opts.defSite||resolveSeedPlaceFast(ar.country)||{}).lon||0], doctrine:doctrinePack}))[b % aliveThreats.length];
      const node=chooseDefenseNodeForThreatReady(ar.country, tgt, opts.defSite || resolveSeedPlaceFast(tgt&&tgt.toName||ar.country) || resolveSeedPlaceFast(ar.country));
      const sector=sectorReadinessFactor(ar.country,node,tgt);
      const role=((b%Math.max(1,maxChannels))===0)?'primary':(((b%2)===0)?'support':'screen');
      const seeker=inferSeekerType(layer.name, layer.tier);
      const fatigue=stockStress(entry);
      const pkAdj=clamp(layer.pk * (0.90+0.12*sysRel) * (1-0.10*fatigue) * sector.horizon * sector.terrain * sector.damagePenalty, 0.05, 0.985);
      const sensorQuality=clamp((0.60+0.18*(layer.aggr||0.75)+(layer.tier==='exo'?0.08:0))*(0.92+0.10*sysRel)*sector.horizon*sector.terrain,0.18,0.98);
      const intc=new Interceptor([node.lat,node.lon],tgt,{fromName:node.name+' ['+layer.name+']',delaySec:layer.delay+layerDelay+b*3,cmdMach:layer.mach,altBiasMi:layer.altMi,aggression:layer.aggr||0.75,allowRetarget:$('allowRetarget').checked,realistic:real,aimLL:tgt.toLL,aimAltM:layer.altMi*1609.344,pkBase:pkAdj,killRadiusBase:layer.killR,systemName:layer.name,tier:layer.tier,sensorQuality:sensorQuality,defenderCountry:ar.country,doctrine:doctrinePack,salvoIndex:b,salvoCount:launched,concurrentChannels:maxChannels,reloadElasticity:doctrinePack.reloadElasticity,seekerType:seeker,raidRole:role});
      intc.systemReliability=sysRel;
      intc.defenseNodeName=node.name; intc.defenseNodeKind=node.kind||'sector'; intc.cityAware=true;
      intc.commandPenalty=sector.cmd; intc.horizonFactor=sector.horizon; intc.terrainMasking=sector.terrain;
      interceptors.push(intc); total++;
      allocSummary[(tgt.toName||tgt.fromName||'target')]=(allocSummary[(tgt.toName||tgt.fromName||'target')]||0)+1;
      sectorBits.push(shortPlaceName({name:node.name})+' '+(100*sector.readiness).toFixed(0)+'%');
      applySectorReload(ar.country,node.name,layer,doctrinePack,1);
    }
    layerDelay += layer.delay*0.55;
  }
  updateStockpileSamples();
  if(total>0 && !opts.silent){
    const allocTxt=Object.entries(allocSummary).slice(0,3).map(x=>shortPlaceName({name:x[0]})+': '+x[1]).join(' • ');
    let msg='AIR DEFENSE: '+ar.data.flag+' '+ar.country+' • '+total+' launched • doctrine '+(doctrineScore(doctrinePack)*100).toFixed(0)+'% • C2 '+(100*commandPenaltyFactor(ar.country)).toFixed(0)+'%';
    if(allocTxt) msg += ' • '+allocTxt;
    if(sectorBits.length) msg += ' • sectors '+sectorBits.slice(0,3).join(' • ');
    if(starved.length) msg += ' • depleted '+starved.slice(0,2).join(', ');
    addLog(msg,'good-entry');
  }
  return total;
};
const _autoDefenseSweep_v18_prev=autoDefenseSweep;
autoDefenseSweep=function(){
  updateCampaignWearAndReload();
  _autoDefenseSweep_v18_prev();
};
const _updateEngagementPanel_v18_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v18_prev();
  updateCampaignWearAndReload();
  if(engagementSummary){
    const topCmd=Object.entries(CAMPAIGN_STATE.commandStatus||{}).sort((a,b)=>(a[1].survivability||0)-(b[1].survivability||0)).slice(0,3)
      .map(x=>escapeHtml(shortPlaceName({name:x[0]}))+': '+((x[1].survivability||0)*100).toFixed(0)+'%').join(' • ');
    engagementSummary.innerHTML += '<br>Sectors offline: <span style="color:#ff8484">'+(metrics.offlineSectors||0)+'</span> • reloading: <span style="color:#ffd48a">'+(metrics.reloadingSectors||0)+'</span>' + (topCmd?(' • stressed C2 '+topCmd):'') + '.';
  }
};
const _updateHud_v18_prev=updateHud;
updateHud=function(){
  _updateHud_v18_prev();
  const def=interceptors.find(i=>i.alive && i.launched);
  if(def){
    hud.innerHTML += '<br>Sector <span class="val">'+escapeHtml(shortPlaceName({name:def.defenseNodeName||def.fromName||'Sector'}))+'</span>';
    if(def.horizonFactor!=null || def.terrainMasking!=null) hud.innerHTML += ' • <span class="val">radar '+((def.horizonFactor||1)*100).toFixed(0)+'%</span> • <span class="val">terrain '+((def.terrainMasking||1)*100).toFixed(0)+'%</span>';
  }
  const atk=projectiles.find(p=>p.alive && !p.excludeFromMetrics) || projectiles.find(p=>p.alive);
  if(atk && atk.defenderCountry){
    const cs=getCommandStatus(atk.defenderCountry);
    hud.innerHTML += '<br>C2 <span class="val">'+escapeHtml(atk.defenderCountry)+': '+((cs.survivability||0)*100).toFixed(0)+'%</span>';
  }
};
const _btnClear_v18_prev=$('btnClear').onclick;
$('btnClear').onclick=()=>{ _btnClear_v18_prev(); ensureCampaignAugments(); metrics.offlineSectors=0; metrics.reloadingSectors=0; metrics.commandSamples=[]; metrics.maskingSamples=[]; };


/* ═══════════════════════════════════════════════════════
   V20 MULTI-DOMAIN UPGRADE
   Adds air / sea / land visual abstractions and domain stats
   without rewriting the existing missile-defense core.
   ═══════════════════════════════════════════════════════ */
const DOMAIN_CACHE={};
function hashStr(s){ s=String(s||''); let h=2166136261>>>0; for(let i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=Math.imul(h,16777619);} return h>>>0; }
function seeded01(key){ return (hashStr(key)%100000)/100000; }
function countryTierSeed(country){
  const ar=country?(getArsenalByCountry?getArsenalByCountry(country):getArsenalForPlace(country)):null;
  if(ar && ar.data && ar.data.band) return ar.data.band;
  const h=seeded01(country||'world');
  if(h>0.985) return 'super';
  if(h>0.94) return 'strategic';
  if(h>0.82) return 'advanced';
  if(h>0.62) return 'regional';
  if(h>0.32) return 'limited';
  return 'micro';
}
function tierDomainBase(tier){
  switch(tier){
    case 'super': return {air:0.98,sea:0.98,land:0.96,log:0.98,space:0.96};
    case 'strategic': return {air:0.90,sea:0.84,land:0.88,log:0.88,space:0.80};
    case 'advanced': return {air:0.80,sea:0.72,land:0.78,log:0.78,space:0.60};
    case 'regional': return {air:0.66,sea:0.52,land:0.70,log:0.64,space:0.38};
    case 'limited': return {air:0.48,sea:0.32,land:0.52,log:0.46,space:0.18};
    default: return {air:0.28,sea:0.16,land:0.30,log:0.24,space:0.05};
  }
}
function estimateCountryStockpile(country){
  country=country||'Default';
  const st=typeof getCountryState==='function'?getCountryState(country):null;
  if(!st) return null;
  const off=Object.values(st.offense||{}).reduce((a,b)=>a+(+b.remaining||0),0);
  const de=Object.values(st.defense||{}).reduce((a,b)=>a+(+b.remaining||0),0);
  return {offense:off, defense:de, readiness:clamp((off+de)/Math.max(1,off+de),0,1)};
}
function domainProfile(country){
  country=country||'Unknown';
  if(DOMAIN_CACHE[country]) return DOMAIN_CACHE[country];
  const tier=countryTierSeed(country);
  const base=tierDomainBase(tier);
  const ar=getArsenalForPlace(country);
  const doc=ar&&ar.data&&ar.data.doctrine ? ar.data.doctrine : null;
  const docBoost=doc?doctrineScore(doc):0.78;
  const stock=estimateCountryStockpile?estimateCountryStockpile(country):null;
  const strikeScale=stock&&stock.offense?clamp(stock.offense/260,0.35,1.35):0.65;
  const defScale=stock&&stock.defense?clamp(stock.defense/320,0.30,1.35):0.62;
  const rndA=seeded01(country+':air')-0.5, rndS=seeded01(country+':sea')-0.5, rndL=seeded01(country+':land')-0.5, rndG=seeded01(country+':log')-0.5;
  const prof={
    country,
    tier,
    air:clamp(base.air*(0.84+0.24*docBoost)*(0.80+0.28*defScale)*(1+rndA*0.16),0.08,1.25),
    sea:clamp(base.sea*(0.86+0.18*docBoost)*(0.82+0.32*strikeScale)*(1+rndS*0.18),0.03,1.20),
    land:clamp(base.land*(0.86+0.18*docBoost)*(0.84+0.24*strikeScale)*(1+rndL*0.14),0.08,1.20),
    logistics:clamp(base.log*(0.86+0.20*docBoost)*(0.86+0.26*(stock&&stock.readiness||0.65))*(1+rndG*0.12),0.06,1.20),
    space:clamp(base.space*(0.88+0.20*docBoost),0.02,1.10)
  };
  prof.integrated=clamp(0.34*prof.air+0.22*prof.sea+0.22*prof.land+0.22*prof.logistics,0.05,1.20);
  DOMAIN_CACHE[country]=prof;
  return prof;
}
function getDefenseNetworkForCountry(country){
  country=country||'';
  const nodes=typeof getCityDefenseNodes==='function' ? getCityDefenseNodes(country, typeof resolveSeedPlaceFast==='function'?resolveSeedPlaceFast(country):null) : [];
  return (nodes||[]).map(function(n){ return Object.assign({importance:n.weight||0.65}, n); });
}
function getCountryAnchor(country){
  const sectors=(typeof getDefenseNetworkForCountry==='function')?getDefenseNetworkForCountry(country):null;
  if(sectors && sectors.length){
    const sorted=sectors.slice().sort((a,b)=>(b.importance||0)-(a.importance||0));
    const s=sorted[0]; if(s&&s.lat!=null&&s.lon!=null) return {lat:s.lat,lon:s.lon,name:s.name||country};
  }
  const fast=resolveSeedPlaceFast?resolveSeedPlaceFast(country):null;
  if(fast&&fast.lat!=null) return {lat:fast.lat,lon:fast.lon,name:fast.name||country};
  return null;
}
function getActiveCountries(){
  const m=new Map();
  for(const p of projectiles){ if(!p) continue; const a=inferCountryFromPlaceName(p.fromName||'')||p.attackerCountry||''; const d=p.defenderCountry||inferCountryFromPlaceName(p.toName||'')||''; if(a) m.set(a,true); if(d) m.set(d,true); }
  for(const i of interceptors){ if(!i) continue; const c=i.country||inferCountryFromPlaceName(i.fromName||'')||''; if(c) m.set(c,true); }
  return Array.from(m.keys()).slice(0,10);
}
function getActiveCountriesDetailed(){
  return getActiveCountries().map(country=>({country, profile:domainProfile(country), anchor:getCountryAnchor(country)})).filter(x=>x.anchor);
}
function drawDomainRing(anchor, strength, color, dash, band){
  const pr=projectLL(anchor.lat,anchor.lon,1.01); if(!pr.visible) return;
  const pulse=0.85+0.15*Math.sin(performance.now()*0.0015 + seeded01(anchor.name||anchor.lat)*6.28 + band);
  const r=(16+band*11 + strength*28)*pulse;
  ctx.save(); ctx.globalAlpha=0.10+0.10*strength; ctx.fillStyle=color; ctx.beginPath(); ctx.arc(pr.x,pr.y,r*1.18,0,Math.PI*2); ctx.fill();
  ctx.globalAlpha=0.22+0.20*strength; ctx.strokeStyle=color; ctx.lineWidth=1.2+1.3*strength; ctx.setLineDash(dash||[]); ctx.beginPath(); ctx.arc(pr.x,pr.y,r,0,Math.PI*2); ctx.stroke();
  ctx.restore();
}
function drawAirPatrol(anchor, strength, color){
  const pr=projectLL(anchor.lat,anchor.lon,1.012); if(!pr.visible) return;
  const t=performance.now()*0.0012 + seeded01(anchor.name||anchor.lat)*6.28;
  for(let k=0;k<Math.max(1,Math.round(1+strength*3));k++){
    const ang=t + k*(Math.PI*2/Math.max(1,Math.round(1+strength*3)));
    const r=18+strength*34 + (k%2)*7;
    const x=pr.x + Math.cos(ang)*r, y=pr.y + Math.sin(ang)*r*0.62;
    ctx.save(); ctx.globalAlpha=0.70; ctx.strokeStyle=color; ctx.lineWidth=1.4; ctx.beginPath(); ctx.moveTo(x-4,y+2); ctx.lineTo(x,y-3); ctx.lineTo(x+5,y+2); ctx.stroke(); ctx.restore();
  }
}
function drawSeaGroup(anchor, strength, color){
  const pr=projectLL(anchor.lat,anchor.lon,1.011); if(!pr.visible) return;
  const t=performance.now()*0.0007 + seeded01(anchor.name||anchor.lon)*6.28;
  const dx=Math.cos(t)*(14+strength*22), dy=Math.sin(t*1.3)*(8+strength*14);
  const x=pr.x+dx, y=pr.y+dy;
  ctx.save(); ctx.globalAlpha=0.75; ctx.strokeStyle=color; ctx.lineWidth=1.5; ctx.beginPath(); ctx.moveTo(x-5,y+3); ctx.lineTo(x+6,y+3); ctx.lineTo(x+2,y-3); ctx.closePath(); ctx.stroke(); ctx.restore();
}
function drawLandAsset(anchor, strength, color){
  const pr=projectLL(anchor.lat,anchor.lon,1.009); if(!pr.visible) return;
  const s=4+strength*5;
  ctx.save(); ctx.globalAlpha=0.55; ctx.strokeStyle=color; ctx.lineWidth=1.2; ctx.strokeRect(pr.x-s, pr.y-s, s*2, s*2); ctx.restore();
}
function drawThreatPressureCloud(){
  const active=projectiles.filter(p=>p.alive).slice(0,10);
  for(const p of active){
    const pr=project(p.rEcef().scale(1/RE_M)); if(!pr.visible) continue;
    const pressure=clamp((p.cmdMach||1)/18,0.18,1.15);
    ctx.save();
    const g=ctx.createRadialGradient(pr.x,pr.y,0,pr.x,pr.y,18+pressure*28);
    g.addColorStop(0,'rgba(255,100,80,'+(0.18+pressure*0.12)+')');
    g.addColorStop(1,'rgba(255,100,80,0)');
    ctx.fillStyle=g; ctx.beginPath(); ctx.arc(pr.x,pr.y,18+pressure*28,0,Math.PI*2); ctx.fill();
    ctx.restore();
  }
}
function drawMultiDomainOverlay(){
  const active=getActiveCountriesDetailed();
  if(!active.length) return;
  ctx.save();
  for(const item of active){
    const a=item.anchor, p=item.profile;
    drawDomainRing(a,p.air,'rgba(80,210,255,0.95)',[6,5],0);
    drawDomainRing(a,p.sea,'rgba(110,150,255,0.85)',[2,6],1);
    drawDomainRing(a,p.land,'rgba(255,178,90,0.90)',[],2);
    drawAirPatrol(a,p.air,'rgba(130,235,255,0.95)');
    drawSeaGroup(a,p.sea,'rgba(118,166,255,0.95)');
    drawLandAsset(a,p.land,'rgba(255,194,120,0.95)');
  }
  drawThreatPressureCloud();
  ctx.restore();
}
function currentDomainBalance(){
  const threats=projectiles.filter(p=>p.alive && !p.excludeFromMetrics);
  if(!threats.length) return null;
  const t=threats[0];
  const atk=domainProfile(inferCountryFromPlaceName(t.fromName||'')||t.attackerCountry||'Unknown');
  const def=domainProfile(t.defenderCountry||inferCountryFromPlaceName(t.toName||'')||'Unknown');
  const rangeNorm=clamp(gcDistMiles(t.fromLL,t.toLL)/7000,0,1.6);
  const missileBurden=clamp((t.cmdMach||1)/20,0.15,1.4);
  const attackAir=clamp(atk.air*(0.85+0.22*atk.logistics),0.04,1.35);
  const attackSea=clamp(atk.sea*(0.80+0.28*(rangeNorm>0.55?1:0.6)),0.02,1.35);
  const attackLand=clamp(atk.land*(0.84+0.20*missileBurden),0.04,1.35);
  const defAir=clamp(def.air*(0.92+0.18*def.logistics),0.05,1.35);
  const defSea=clamp(def.sea*(0.84+0.14*def.air),0.02,1.30);
  const defLand=clamp(def.land*(0.90+0.20*def.logistics),0.04,1.30);
  const atkIntegrated=clamp(0.38*attackAir+0.22*attackSea+0.20*attackLand+0.20*atk.logistics,0.04,1.4);
  const defIntegrated=clamp(0.40*defAir+0.14*defSea+0.24*defLand+0.22*def.logistics,0.04,1.4);
  return {atk,def,attackAir,attackSea,attackLand,defAir,defSea,defLand,atkIntegrated,defIntegrated,rangeNorm,missileBurden};
}
function updateDomainMetrics(){
  const bal=currentDomainBalance();
  if(!bal) return;
  metrics.airSamples=(metrics.airSamples||[]); metrics.seaSamples=(metrics.seaSamples||[]); metrics.landSamples=(metrics.landSamples||[]); metrics.logisticsSamples=(metrics.logisticsSamples||[]);
  metrics.airSamples=metrics.airSamples.concat([bal.defAir]).slice(-24);
  metrics.seaSamples=metrics.seaSamples.concat([bal.defSea]).slice(-24);
  metrics.landSamples=metrics.landSamples.concat([bal.defLand]).slice(-24);
  metrics.logisticsSamples=metrics.logisticsSamples.concat([bal.def.logistics]).slice(-24);
}
const _drawGlobe_v20_prev=drawGlobe;
drawGlobe=function(){ _drawGlobe_v20_prev(); drawMultiDomainOverlay(); };
const _drawAllShots_v20_prev=drawAllShots;
drawAllShots=function(){ _drawAllShots_v20_prev();
  const active=getActiveCountriesDetailed();
  for(const item of active){
    const pr=projectLL(item.anchor.lat,item.anchor.lon,1.014); if(!pr.visible) continue;
    ctx.save(); ctx.fillStyle='rgba(255,255,255,0.8)'; ctx.font='10px ui-monospace, monospace'; ctx.textAlign='center';
    ctx.fillText(item.country.toUpperCase().slice(0,12), pr.x, pr.y-(24+item.profile.air*8)); ctx.restore();
  }
};
const _loop_v20_prev=loop;
loop=function(){ updateDomainMetrics(); _loop_v20_prev(); };
const _updateEngagementPanel_v20_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v20_prev();
  const air=safeMean(metrics.airSamples||[]), sea=safeMean(metrics.seaSamples||[]), land=safeMean(metrics.landSamples||[]), logi=safeMean(metrics.logisticsSamples||[]);
  const bar=(label,val,color)=>'<div style="display:flex;align-items:center;gap:6px;margin:2px 0"><span style="width:54px;color:#9fb5c9">'+label+'</span><div style="flex:1;height:8px;background:#091321;border:1px solid #223246;border-radius:999px;overflow:hidden"><div style="height:100%;width:'+Math.round(100*clamp(val,0,1.2))+'%;background:'+color+'"></div></div><span style="width:34px;text-align:right;color:#d9e8f7">'+Math.round(val*100)+'%</span></div>';
  engagementSummary.innerHTML += '<br><span style="color:#90dfff">MULTI-DOMAIN POSTURE</span>'+
    bar('Air',air,'linear-gradient(90deg,#39d9ff,#83f4ff)')+
    bar('Sea',sea,'linear-gradient(90deg,#5c82ff,#8fa8ff)')+
    bar('Land',land,'linear-gradient(90deg,#ffb05f,#ffd28f)')+
    bar('Log',logi,'linear-gradient(90deg,#5bff9a,#abffd2)');
  const bal=currentDomainBalance();
  if(bal){
    engagementSummary.innerHTML += '<div style="margin-top:4px;color:#8ca2b9">Active balance: <span style="color:#ffd28f">'+escapeHtml(bal.atk.country)+'</span> integrated '+(bal.atkIntegrated*100).toFixed(0)+'% vs <span style="color:#9ef4ff">'+escapeHtml(bal.def.country)+'</span> integrated '+(bal.defIntegrated*100).toFixed(0)+'%.</div>';
  }
};
const _updateHud_v20_prev=updateHud;
updateHud=function(){
  _updateHud_v20_prev();
  const bal=currentDomainBalance();
  if(bal){
    hud.innerHTML += '<br>AIR <span class="val">A '+(bal.attackAir*100).toFixed(0)+'%</span> / <span class="val">D '+(bal.defAir*100).toFixed(0)+'%</span>'+
      ' • SEA <span class="val">A '+(bal.attackSea*100).toFixed(0)+'%</span> / <span class="val">D '+(bal.defSea*100).toFixed(0)+'%</span>'+
      ' • LAND <span class="val">A '+(bal.attackLand*100).toFixed(0)+'%</span> / <span class="val">D '+(bal.defLand*100).toFixed(0)+'%</span>'+
      '<br>Integrated posture <span class="val">'+escapeHtml(bal.atk.country)+' '+(bal.atkIntegrated*100).toFixed(0)+'%</span> vs <span class="val">'+escapeHtml(bal.def.country)+' '+(bal.defIntegrated*100).toFixed(0)+'%</span>';
  }
};
const _btnClear_v20_prev=$('btnClear').onclick;
$('btnClear').onclick=()=>{ DOMAIN_CACHE.__reset=1; metrics.airSamples=[]; metrics.seaSamples=[]; metrics.landSamples=[]; metrics.logisticsSamples=[]; _btnClear_v20_prev(); };
addLog('MULTI-DOMAIN LAYER ONLINE: air / sea / land overlays active.', 'good-entry');



/* ═══════════════════════════════════════════════════════
   V21 DOMAIN ATTRITION + BASE DAMAGE PROPAGATION
   Separates air / sea / land / logistics wear, readiness, and battle damage
   while preserving the existing missile-defense engine.
   ═══════════════════════════════════════════════════════ */
const DOMAIN_WAR={};
function ensureDomainWarState(country){
  country=country||'Unknown';
  if(DOMAIN_WAR[country]) return DOMAIN_WAR[country];
  const prof=domainProfile(country);
  const tier=prof.tier||countryTierSeed(country);
  const stock=estimateCountryStockpile?estimateCountryStockpile(country):null;
  const offense=stock&&stock.offense?stock.offense:(90+Math.round(prof.integrated*220));
  const defense=stock&&stock.defense?stock.defense:(110+Math.round(prof.integrated*280));
  const support=60+Math.round(prof.logistics*180);
  const state={
    country,
    tier,
    air:{ready:Math.round(offense*(0.25+0.35*prof.air)), max:Math.round(offense*(0.25+0.35*prof.air)), dmg:0, fatigue:0, commits:0, kills:0, losses:0},
    sea:{ready:Math.round(offense*(0.16+0.32*prof.sea)), max:Math.round(offense*(0.16+0.32*prof.sea)), dmg:0, fatigue:0, commits:0, kills:0, losses:0},
    land:{ready:Math.round(offense*(0.34+0.42*prof.land)), max:Math.round(offense*(0.34+0.42*prof.land)), dmg:0, fatigue:0, commits:0, kills:0, losses:0},
    airDefense:{ready:Math.round(defense*(0.42+0.34*prof.air)), max:Math.round(defense*(0.42+0.34*prof.air)), dmg:0, fatigue:0, shots:0, hits:0, misses:0},
    navalDefense:{ready:Math.round(defense*(0.12+0.22*prof.sea)), max:Math.round(defense*(0.12+0.22*prof.sea)), dmg:0, fatigue:0, shots:0},
    groundDefense:{ready:Math.round(defense*(0.22+0.26*prof.land)), max:Math.round(defense*(0.22+0.26*prof.land)), dmg:0, fatigue:0, shots:0},
    logistics:{health:clamp(0.62+0.32*prof.logistics,0.18,1.25), throughput:support, strain:0},
    c2:{health:clamp(0.60+0.34*prof.integrated,0.18,1.20), degraded:0},
    history:[]
  };
  DOMAIN_WAR[country]=state;
  return state;
}
function avgObj(arr,key){ return (arr&&arr.length)?arr.reduce((a,x)=>a+(+x[key]||0),0)/arr.length:0; }
function domainAssetFactor(asset){
  if(!asset) return 0.2;
  const ready=(asset.max>0)?asset.ready/asset.max:0;
  const dmg=1-clamp(asset.dmg||0,0,0.95);
  const fatigue=1-clamp(asset.fatigue||0,0,0.85);
  return clamp(0.15 + 0.85*ready*dmg*fatigue,0.05,1.25);
}
function logisticsFactor(ws){
  if(!ws) return 0.2;
  return clamp((ws.logistics.health||0.5)*(1-0.45*(ws.logistics.strain||0))*(0.82+0.18*(ws.c2.health||0.6)),0.05,1.25);
}
function classifyAttackDomain(attack){
  const name=((attack&&attack.systemName)||'').toLowerCase();
  const mode=((attack&&attack.mode)||'').toLowerCase();
  if(name.includes('carrier')||name.includes('sub')||name.includes('ship')||name.includes('naval')) return 'sea';
  if(mode==='cruise' || name.includes('cruise') || name.includes('air ') || name.includes('fighter') || name.includes('bomber')) return 'air';
  if(mode==='guided' || mode==='ballistic' || mode==='evasive' || name.includes('missile') || name.includes('hgv') || name.includes('icbm') || name.includes('mrbm')) return 'land';
  return 'land';
}
function classifyDefenseBucket(intc){
  const tier=((intc&&intc.tier)||'').toLowerCase();
  const seeker=((intc&&intc.seekerType)||'').toLowerCase();
  if(tier==='exo' || tier==='high-endo' || seeker.includes('radar') || seeker.includes('hit')) return 'airDefense';
  if(seeker.includes('ir')) return 'groundDefense';
  return 'airDefense';
}
function consumeDomainAsset(country,bucket,qty){
  const ws=ensureDomainWarState(country); const asset=ws[bucket]; if(!asset) return ws;
  qty=Math.max(0,+qty||0);
  asset.ready=Math.max(0, asset.ready-qty);
  asset.commits=(asset.commits||asset.shots||0)+qty;
  asset.fatigue=clamp((asset.fatigue||0)+0.0035*qty,0,0.90);
  ws.logistics.strain=clamp((ws.logistics.strain||0)+0.0018*qty,0,0.95);
  return ws;
}
function applyDomainDamage(country, payload){
  const ws=ensureDomainWarState(country); payload=payload||{};
  const kind=payload.kind||'land';
  const severity=clamp(payload.severity||0.1,0.01,0.95);
  const spread=payload.spread!=null?payload.spread:0.55;
  const sectors=(kind==='air')?['air','airDefense','logistics']:(kind==='sea')?['sea','navalDefense','logistics']:['land','groundDefense','airDefense','logistics'];
  for(const s of sectors){
    const obj=ws[s];
    if(!obj) continue;
    if(obj.health!=null){
      obj.health=clamp(obj.health - severity*(s==='logistics'?0.42:0.18), 0.05, 1.25);
    } else {
      obj.dmg=clamp((obj.dmg||0)+severity*(0.40+0.30*Math.random())*(s===sectors[0]?1.0:spread),0,0.98);
      const burn=Math.round((obj.max||0)*severity*(s===sectors[0]?0.06:0.03));
      obj.ready=Math.max(0,(obj.ready||0)-burn);
      obj.losses=(obj.losses||0)+burn;
    }
  }
  ws.c2.health=clamp((ws.c2.health||0.7)-severity*(payload.c2Weight||0.10),0.08,1.20);
  ws.c2.degraded=clamp((ws.c2.degraded||0)+severity*0.25,0,1.20);
  ws.history.push({t:Date.now(), type:'damage', kind, severity});
  if(ws.history.length>40) ws.history.shift();
  return ws;
}
function recoverDomainWar(){
  for(const country of Object.keys(DOMAIN_WAR)){
    const ws=DOMAIN_WAR[country];
    for(const key of ['air','sea','land','airDefense','navalDefense','groundDefense']){
      const a=ws[key]; if(!a) continue;
      a.fatigue=clamp((a.fatigue||0)-0.0006,0,0.9);
      if(a.ready<a.max){
        const regen=Math.max(0.005*a.max,0.02)*(0.45+0.65*logisticsFactor(ws))*(1-(a.dmg||0)*0.7);
        a.ready=Math.min(a.max, a.ready+regen);
      }
      a.dmg=clamp((a.dmg||0)-0.00018*(0.6+logisticsFactor(ws)),0,0.98);
    }
    ws.logistics.strain=clamp((ws.logistics.strain||0)-0.00055,0,0.95);
    ws.logistics.health=clamp((ws.logistics.health||0.8)+0.00012*(1-(ws.logistics.strain||0)),0.05,1.25);
    ws.c2.degraded=clamp((ws.c2.degraded||0)-0.0005,0,1.20);
    ws.c2.health=clamp((ws.c2.health||0.8)+0.00008*(1-(ws.c2.degraded||0)),0.08,1.20);
  }
}
function domainCombatScalar(country, role){
  const ws=ensureDomainWarState(country);
  const prof=domainProfile(country);
  const atk=(0.34*domainAssetFactor(ws.air)+0.22*domainAssetFactor(ws.sea)+0.28*domainAssetFactor(ws.land)+0.16*logisticsFactor(ws));
  const def=(0.48*domainAssetFactor(ws.airDefense)+0.18*domainAssetFactor(ws.navalDefense)+0.18*domainAssetFactor(ws.groundDefense)+0.16*logisticsFactor(ws));
  const c2=clamp((ws.c2.health||0.7)*(1-0.40*(ws.c2.degraded||0)),0.08,1.25);
  return role==='defense' ? clamp(def*c2*(0.78+0.30*prof.air),0.05,1.35) : clamp(atk*c2*(0.80+0.28*prof.integrated),0.05,1.45);
}
function noteDomainSample(){
  const bal=currentDomainBalance(); if(!bal) return;
  metrics.airAttackSamples=(metrics.airAttackSamples||[]).concat([bal.attackAir]).slice(-24);
  metrics.seaAttackSamples=(metrics.seaAttackSamples||[]).concat([bal.attackSea]).slice(-24);
  metrics.landAttackSamples=(metrics.landAttackSamples||[]).concat([bal.attackLand]).slice(-24);
}
const _domainProfile_v21_prev=domainProfile;
domainProfile=function(country){
  const prof=_domainProfile_v21_prev(country);
  const ws=ensureDomainWarState(country);
  const out=Object.assign({}, prof);
  out.air=clamp(prof.air * (0.48+0.52*domainAssetFactor(ws.air)) * (0.56+0.44*domainAssetFactor(ws.airDefense)),0.04,1.25);
  out.sea=clamp(prof.sea * (0.45+0.55*domainAssetFactor(ws.sea)) * (0.70+0.30*logisticsFactor(ws)),0.02,1.20);
  out.land=clamp(prof.land * (0.45+0.55*domainAssetFactor(ws.land)) * (0.72+0.28*domainAssetFactor(ws.groundDefense)),0.04,1.20);
  out.logistics=clamp(prof.logistics * logisticsFactor(ws),0.03,1.20);
  out.integrated=clamp(0.32*out.air+0.18*out.sea+0.24*out.land+0.16*out.logistics+0.10*clamp((ws.c2.health||0.7)*(1-(ws.c2.degraded||0)*0.5),0.05,1.2),0.03,1.30);
  out.warState=ws;
  return out;
};
const _launchProjectedAttack_v21_prev=launchProjectedAttack;
launchProjectedAttack=function(opts){
  const beforeCount=projectiles.length;
  const attack=_launchProjectedAttack_v21_prev(opts);
  if(attack && attack.attackerCountry){
    const bucket=classifyAttackDomain(attack);
    attack.domainKind=bucket;
    const spend=(bucket==='air')?1.2:(bucket==='sea'?1.0:1.35);
    consumeDomainAsset(attack.attackerCountry,bucket,spend);
    const ws=ensureDomainWarState(attack.attackerCountry);
    attack.domainReadiness=domainCombatScalar(attack.attackerCountry,'attack');
    attack.logisticsReadiness=logisticsFactor(ws);
  }
  return attack;
};
const _activateNationalDefense_v21_prev=activateNationalDefense;
activateNationalDefense=function(opts){
  const before=interceptors.length;
  const n=_activateNationalDefense_v21_prev(opts);
  for(let idx=before; idx<interceptors.length; idx++){
    const i=interceptors[idx]; if(!i || i._domainTracked) continue;
    i._domainTracked=true;
    const bucket=classifyDefenseBucket(i);
    i.domainBucket=bucket;
    if(i.defenderCountry){
      consumeDomainAsset(i.defenderCountry,bucket,1.0);
      const ws=ensureDomainWarState(i.defenderCountry);
      const scalar=domainCombatScalar(i.defenderCountry,'defense');
      i.pkBase=clamp((i.pkBase||0.45)*(0.72+0.34*scalar),0.05,0.995);
      i.sensorQuality=clamp((i.sensorQuality||0.65)*(0.74+0.30*scalar),0.20,0.995);
      i.domainDefenseScalar=scalar;
    }
  }
  return n;
};
const _registerAttackOutcome_v21_prev=registerAttackOutcome;
registerAttackOutcome=function(p){
  const before=p && p._outcomeRecorded;
  _registerAttackOutcome_v21_prev(p);
  if(!p || before) return;
  const kind=p.domainKind||classifyAttackDomain(p);
  if(p.attackerCountry){
    const aws=ensureDomainWarState(p.attackerCountry);
    const asset=aws[kind]||aws.land;
    asset.kills=(asset.kills||0)+(p.intercepted?0:1);
  }
  if(p.defenderCountry){
    if(p.intercepted){
      const dws=ensureDomainWarState(p.defenderCountry);
      dws.airDefense.hits=(dws.airDefense.hits||0)+1;
      dws.logistics.strain=clamp((dws.logistics.strain||0)+0.0025,0,0.95);
    } else {
      const sev=clamp((p.mode==='ballistic'?0.20:(p.mode==='guided'?0.15:(p.mode==='cruise'?0.11:0.13))) + 0.16*Math.min(1,(p.cmdMach||1)/24) + 0.08*(p.evasiveness||p.evasion||0),0.05,0.82);
      applyDomainDamage(p.defenderCountry,{kind,severity:sev,c2Weight:(p.mode==='ballistic'?0.16:0.10)});
    }
  }
};
const _registerInterceptorOutcome_v21_prev=registerInterceptorOutcome;
registerInterceptorOutcome=function(i){
  const before=i && i._outcomeRecorded;
  _registerInterceptorOutcome_v21_prev(i);
  if(!i || before || !i.defenderCountry) return;
  const ws=ensureDomainWarState(i.defenderCountry);
  const bucket=i.domainBucket||classifyDefenseBucket(i);
  const obj=ws[bucket]||ws.airDefense;
  obj.shots=(obj.shots||0)+1;
  if(i.hit){ obj.hits=(obj.hits||0)+1; obj.fatigue=clamp((obj.fatigue||0)+0.0015,0,0.9); }
  else { obj.misses=(obj.misses||0)+1; obj.fatigue=clamp((obj.fatigue||0)+0.0028,0,0.9); }
};
const _currentDomainBalance_v21_prev=currentDomainBalance;
currentDomainBalance=function(){
  const bal=_currentDomainBalance_v21_prev();
  if(!bal) return bal;
  const atkScalar=domainCombatScalar(bal.atk.country,'attack');
  const defScalar=domainCombatScalar(bal.def.country,'defense');
  const atkWs=ensureDomainWarState(bal.atk.country), defWs=ensureDomainWarState(bal.def.country);
  bal.attackAir=clamp(bal.attackAir*(0.72+0.34*domainAssetFactor(atkWs.air))*(0.76+0.28*logisticsFactor(atkWs)),0.03,1.5);
  bal.attackSea=clamp(bal.attackSea*(0.70+0.36*domainAssetFactor(atkWs.sea))*(0.76+0.28*logisticsFactor(atkWs)),0.02,1.45);
  bal.attackLand=clamp(bal.attackLand*(0.70+0.38*domainAssetFactor(atkWs.land))*(0.78+0.24*logisticsFactor(atkWs)),0.03,1.45);
  bal.defAir=clamp(bal.defAir*(0.68+0.42*domainAssetFactor(defWs.airDefense))*(0.78+0.24*logisticsFactor(defWs)),0.03,1.5);
  bal.defSea=clamp(bal.defSea*(0.68+0.40*domainAssetFactor(defWs.navalDefense)),0.02,1.35);
  bal.defLand=clamp(bal.defLand*(0.70+0.38*domainAssetFactor(defWs.groundDefense)),0.03,1.35);
  bal.atkIntegrated=clamp(bal.atkIntegrated*(0.72+0.38*atkScalar),0.03,1.55);
  bal.defIntegrated=clamp(bal.defIntegrated*(0.72+0.38*defScalar),0.03,1.55);
  bal.atkWar=atkWs; bal.defWar=defWs; bal.atkScalar=atkScalar; bal.defScalar=defScalar;
  return bal;
};
const _drawMultiDomainOverlay_v21_prev=drawMultiDomainOverlay;
drawMultiDomainOverlay=function(){
  _drawMultiDomainOverlay_v21_prev();
  const active=getActiveCountriesDetailed();
  for(const item of active){
    const ws=ensureDomainWarState(item.country); const pr=projectLL(item.anchor.lat,item.anchor.lon,1.016); if(!pr.visible) continue;
    const stress=clamp(avgObj([ws.air,ws.sea,ws.land,ws.airDefense,ws.groundDefense],'dmg') + (ws.logistics.strain||0)*0.5 + (ws.c2.degraded||0)*0.4,0,1.6);
    if(stress>0.08){
      ctx.save();
      const rr=18+28*stress;
      const g=ctx.createRadialGradient(pr.x,pr.y,0,pr.x,pr.y,rr);
      g.addColorStop(0,'rgba(255,72,72,'+(0.16+0.12*stress)+')');
      g.addColorStop(1,'rgba(255,72,72,0)');
      ctx.fillStyle=g; ctx.beginPath(); ctx.arc(pr.x,pr.y,rr,0,Math.PI*2); ctx.fill();
      ctx.restore();
    }
  }
};
const _updateDomainMetrics_v21_prev=updateDomainMetrics;
updateDomainMetrics=function(){ _updateDomainMetrics_v21_prev(); noteDomainSample(); recoverDomainWar(); };
const _updateEngagementPanel_v21_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v21_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const pct=v=>Math.round(100*clamp(v,0,1.5));
  const line=(lbl,a,b)=>'<div style="display:flex;justify-content:space-between;gap:8px;color:#9fb5c9;margin-top:2px"><span>'+lbl+'</span><span style="color:#ffd48a">A '+pct(a)+'%</span><span style="color:#9ef4ff">D '+pct(b)+'%</span></div>';
  engagementSummary.innerHTML += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid rgba(120,150,180,.12)"><span style="color:#ffcf93">DOMAIN ATTRITION</span>'+
    line('Air ops', domainAssetFactor(bal.atkWar.air), domainAssetFactor(bal.defWar.airDefense))+
    line('Sea ops', domainAssetFactor(bal.atkWar.sea), domainAssetFactor(bal.defWar.navalDefense))+
    line('Land ops', domainAssetFactor(bal.atkWar.land), domainAssetFactor(bal.defWar.groundDefense))+
    line('Logistics', logisticsFactor(bal.atkWar), logisticsFactor(bal.defWar))+
    '<div style="color:#7f97ad;margin-top:4px">C2 health '+escapeHtml(bal.atk.country)+' '+pct((bal.atkWar.c2.health||0.7)*(1-(bal.atkWar.c2.degraded||0)*0.4))+'% vs '+escapeHtml(bal.def.country)+' '+pct((bal.defWar.c2.health||0.7)*(1-(bal.defWar.c2.degraded||0)*0.4))+'%.</div></div>';
};
const _updateHud_v21_prev=updateHud;
updateHud=function(){
  _updateHud_v21_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const pct=v=>Math.round(100*clamp(v,0,1.5));
  hud.innerHTML += '<br>Readiness <span class="val">A '+pct(domainAssetFactor(bal.atkWar.air))+ '/' + pct(domainAssetFactor(bal.atkWar.sea)) + '/' + pct(domainAssetFactor(bal.atkWar.land)) + '%</span>'+
    ' • <span class="val">D '+pct(domainAssetFactor(bal.defWar.airDefense))+ '/' + pct(domainAssetFactor(bal.defWar.navalDefense)) + '/' + pct(domainAssetFactor(bal.defWar.groundDefense)) + '%</span>'+
    '<br>Logistics <span class="val">A '+pct(logisticsFactor(bal.atkWar))+'%</span> • <span class="val">D '+pct(logisticsFactor(bal.defWar))+'%</span>'+
    ' • C2 <span class="val">A '+pct((bal.atkWar.c2.health||0.7)*(1-(bal.atkWar.c2.degraded||0)*0.4))+'%</span> / <span class="val">D '+pct((bal.defWar.c2.health||0.7)*(1-(bal.defWar.c2.degraded||0)*0.4))+'%</span>';
};
const _btnClear_v21_prev=$('btnClear').onclick;
$('btnClear').onclick=()=>{ for(const k of Object.keys(DOMAIN_WAR)) delete DOMAIN_WAR[k]; metrics.airAttackSamples=[]; metrics.seaAttackSamples=[]; metrics.landAttackSamples=[]; _btnClear_v21_prev(); };
addLog('V21 DOMAIN ATTRITION ONLINE: separate air / sea / land readiness and damage propagation active.', 'good-entry');


/* ═══════════════════════════════════════════════════════
   V22 CAMPAIGN THEATERS + ASSET COUNTS
   Adds theater-sector overlays, asset-count symbology,
   and a persistent campaign timeline clock.
   ═══════════════════════════════════════════════════════ */
const CAMPAIGN_CLOCK={running:false, hours:0, speedHoursPerSec:8, lastT:0, mode:'compressed'};
function theaterCountForTier(tier){
  switch(tier){
    case 'super': return 5;
    case 'strategic': return 4;
    case 'advanced': return 4;
    case 'regional': return 3;
    case 'limited': return 2;
    default: return 1;
  }
}
function estimateAssetCounts(country){
  const p=domainProfile(country); const ws=ensureDomainWarState(country);
  const baseScale=(p.integrated||0.4);
  const readinessAir=domainAssetFactor(ws.air||ws.airDefense||{readiness:0.7});
  const readinessSea=domainAssetFactor(ws.sea||ws.navalDefense||{readiness:0.6});
  const readinessLand=domainAssetFactor(ws.land||ws.groundDefense||{readiness:0.7});
  const logi=logisticsFactor(ws);
  const tierMul={super:1.9, strategic:1.55, advanced:1.25, regional:0.95, limited:0.66, micro:0.38}[p.tier] || 0.6;
  const squadrons=Math.max(1,Math.round((5 + 20*p.air + 6*baseScale)*tierMul*readinessAir));
  const fleets=Math.max(0,Math.round((1 + 10*p.sea + 3*baseScale)*tierMul*readinessSea));
  const brigades=Math.max(1,Math.round((6 + 24*p.land + 5*baseScale)*tierMul*readinessLand));
  const batteries=Math.max(1,Math.round((4 + 18*p.air + 4*(p.logistics||0.4))*tierMul*(0.75*readinessAir+0.25*logi)));
  return {squadrons,fleets,brigades,batteries};
}
function getCountryTheaterNodes(country){
  const anchor=getCountryAnchor(country); if(!anchor) return [];
  const p=domainProfile(country); const n=theaterCountForTier(p.tier);
  const nodes=[];
  const spread=(p.tier==='super'?11:(p.tier==='strategic'?9:(p.tier==='advanced'?7:(p.tier==='regional'?5:3.5))));
  for(let i=0;i<n;i++){
    const ang=(i/n)*Math.PI*2 + seeded01(country+':th:'+i)*0.9;
    const lat=clamp(anchor.lat + Math.sin(ang)*spread*(0.55+0.45*seeded01(country+':lat:'+i)),-72,78);
    const lon=((anchor.lon + Math.cos(ang)*(spread*1.65)*(0.55+0.45*seeded01(country+':lon:'+i)) + 540)%360)-180;
    nodes.push({name:(anchor.name||country)+' T'+(i+1),lat,lon,importance:1.0-0.1*i,domainMix:{air:clamp(p.air*(0.85+0.2*seeded01(country+':a:'+i)),0.05,1.4),sea:clamp(p.sea*(0.82+0.24*seeded01(country+':s:'+i)),0.02,1.3),land:clamp(p.land*(0.84+0.20*seeded01(country+':l:'+i)),0.05,1.3)}});
  }
  nodes.unshift({name:(anchor.name||country)+' Capital Sector',lat:anchor.lat,lon:anchor.lon,importance:1.25,domainMix:{air:p.air,sea:p.sea,land:p.land}});
  return nodes;
}
function drawAssetIcon(x,y,type,color,scale,label){
  const s=scale||1;
  ctx.save(); ctx.translate(x,y); ctx.strokeStyle=color; ctx.fillStyle='rgba(7,14,24,0.92)'; ctx.lineWidth=1.2;
  if(type==='air'){
    ctx.beginPath(); ctx.moveTo(-5*s,2*s); ctx.lineTo(0,-4*s); ctx.lineTo(6*s,2*s); ctx.moveTo(0,-4*s); ctx.lineTo(0,5*s); ctx.stroke();
  } else if(type==='sea'){
    ctx.beginPath(); ctx.moveTo(-6*s,3*s); ctx.lineTo(6*s,3*s); ctx.lineTo(2*s,-3*s); ctx.closePath(); ctx.stroke();
  } else if(type==='land'){
    ctx.strokeRect(-4.5*s,-4.5*s,9*s,9*s);
  } else if(type==='battery'){
    ctx.beginPath(); ctx.arc(0,0,4.5*s,0,Math.PI*2); ctx.stroke(); ctx.beginPath(); ctx.moveTo(-6*s,0); ctx.lineTo(6*s,0); ctx.moveTo(0,-6*s); ctx.lineTo(0,6*s); ctx.stroke();
  }
  if(label){ ctx.font='9px ui-monospace, monospace'; ctx.textAlign='left'; ctx.fillStyle='rgba(235,245,255,0.92)'; ctx.fillText(label,8*s,-2*s); }
  ctx.restore();
}
function drawTheaterSector(node,color,widthMul,dash){
  const pr=projectLL(node.lat,node.lon,1.013); if(!pr.visible) return;
  const t=performance.now()*0.0005 + seeded01(node.name)*6.28;
  const r=(20 + 10*(node.importance||1) + 12*widthMul)*(0.96+0.08*Math.sin(t));
  ctx.save(); ctx.globalAlpha=0.16; ctx.strokeStyle=color; ctx.lineWidth=1.0+1.2*widthMul; ctx.setLineDash(dash||[]);
  ctx.beginPath(); ctx.arc(pr.x,pr.y,r,0,Math.PI*2); ctx.stroke();
  ctx.globalAlpha=0.08; ctx.fillStyle=color; ctx.beginPath(); ctx.arc(pr.x,pr.y,r*1.12,0,Math.PI*2); ctx.fill();
  ctx.restore();
}
function drawCampaignTheaterOverlay(){
  const active=getActiveCountriesDetailed();
  for(const item of active){
    const counts=estimateAssetCounts(item.country);
    const nodes=getCountryTheaterNodes(item.country).slice(0,5);
    let i=0;
    for(const node of nodes){
      drawTheaterSector(node,'rgba(125,170,255,0.62)',node.domainMix.sea||0.2,[3,7]);
      drawTheaterSector(node,'rgba(90,230,255,0.58)',node.domainMix.air||0.2,[7,4]);
      drawTheaterSector(node,'rgba(255,190,110,0.56)',node.domainMix.land||0.2,[]);
      const pr=projectLL(node.lat,node.lon,1.017); if(!pr.visible) { i++; continue; }
      const jitter=seeded01(node.name+':j');
      if(i===0){
        drawAssetIcon(pr.x-14, pr.y-8, 'air', 'rgba(128,238,255,0.95)', 0.9, String(counts.squadrons));
        drawAssetIcon(pr.x+2, pr.y+8, 'battery', 'rgba(160,220,255,0.95)', 0.84, String(counts.batteries));
        if(counts.fleets>0) drawAssetIcon(pr.x-6, pr.y+22, 'sea', 'rgba(135,160,255,0.95)', 0.86, String(counts.fleets));
        drawAssetIcon(pr.x+18, pr.y-18, 'land', 'rgba(255,205,125,0.95)', 0.9, String(counts.brigades));
      } else {
        if((node.domainMix.air||0)>0.22) drawAssetIcon(pr.x-6, pr.y-5, 'air', 'rgba(128,238,255,0.86)', 0.68);
        if((node.domainMix.sea||0)>0.18) drawAssetIcon(pr.x+8, pr.y+6, 'sea', 'rgba(135,160,255,0.84)', 0.66);
        if((node.domainMix.land||0)>0.22) drawAssetIcon(pr.x+1, pr.y-10, 'land', 'rgba(255,205,125,0.84)', 0.66);
        if(jitter>0.58) drawAssetIcon(pr.x-12, pr.y+11, 'battery', 'rgba(160,220,255,0.82)', 0.60);
      }
      i++;
    }
  }
}
function updateCampaignClock(){
  const now=performance.now();
  if(!CAMPAIGN_CLOCK.lastT) CAMPAIGN_CLOCK.lastT=now;
  const active=projectiles.some(p=>p.alive) || interceptors.some(i=>i.alive);
  CAMPAIGN_CLOCK.running=active;
  if(active){
    const dt=Math.max(0, Math.min(0.25,(now-CAMPAIGN_CLOCK.lastT)/1000));
    CAMPAIGN_CLOCK.hours += dt*CAMPAIGN_CLOCK.speedHoursPerSec;
  }
  CAMPAIGN_CLOCK.lastT=now;
}
function campaignClockLabel(){
  const total=Math.max(0,CAMPAIGN_CLOCK.hours||0);
  const day=Math.floor(total/24)+1;
  const hour=Math.floor(total%24);
  const week=Math.floor((day-1)/7)+1;
  return {day,hour,week,text:'W'+week+' • D'+day+' • H'+String(hour).padStart(2,'0')};
}
const _drawMultiDomainOverlay_v22_prev=drawMultiDomainOverlay;
drawMultiDomainOverlay=function(){ _drawMultiDomainOverlay_v22_prev(); drawCampaignTheaterOverlay(); };
const _loop_v22_prev=loop;
loop=function(){ updateCampaignClock(); _loop_v22_prev(); };
const _updateHud_v22_prev=updateHud;
updateHud=function(){
  _updateHud_v22_prev();
  const c=campaignClockLabel();
  hud.innerHTML += '<br>Campaign clock <span class="val">'+c.text+'</span> • mode <span class="val">'+escapeHtml(CAMPAIGN_CLOCK.mode)+'</span>';
  const bal=currentDomainBalance();
  if(bal){
    const ac=estimateAssetCounts(bal.atk.country), dc=estimateAssetCounts(bal.def.country);
    hud.innerHTML += '<br>Assets <span class="val">'+escapeHtml(bal.atk.country)+' A/S/L/AD '+ac.squadrons+'/'+ac.fleets+'/'+ac.brigades+'/'+ac.batteries+'</span>'+
      ' • <span class="val">'+escapeHtml(bal.def.country)+' '+dc.squadrons+'/'+dc.fleets+'/'+dc.brigades+'/'+dc.batteries+'</span>';
  }
};
const _updateEngagementPanel_v22_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v22_prev();
  const c=campaignClockLabel();
  const bal=currentDomainBalance();
  if(!bal) return;
  const ac=estimateAssetCounts(bal.atk.country), dc=estimateAssetCounts(bal.def.country);
  const row=(name,a,d,color)=>'<div style="display:flex;align-items:center;gap:8px;margin:2px 0"><span style="width:70px;color:#9fb5c9">'+name+'</span><span style="width:56px;color:#ffd48a;text-align:right">'+a+'</span><div style="flex:1;height:6px;background:#091321;border:1px solid #223246;border-radius:999px;overflow:hidden"><div style="width:'+Math.min(100,Math.round((a/(Math.max(a,d)||1))*100))+'%;height:100%;background:'+color+';opacity:.85"></div></div><span style="width:56px;color:#9ef4ff">'+d+'</span></div>';
  engagementSummary.innerHTML += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid rgba(120,150,180,.12)"><span style="color:#b7d7ff">THEATER CAMPAIGN MODE</span>'+
    '<div style="color:#8ca2b9;margin:4px 0">Timeline '+c.text+' • regional sectors active • asset overlays persistent until reset.</div>'+
    row('Squadrons',ac.squadrons,dc.squadrons,'linear-gradient(90deg,#58e2ff,#8df3ff)')+
    row('Fleets',ac.fleets,dc.fleets,'linear-gradient(90deg,#6f86ff,#9cb2ff)')+
    row('Brigades',ac.brigades,dc.brigades,'linear-gradient(90deg,#ffbb66,#ffd28c)')+
    row('Batteries',ac.batteries,dc.batteries,'linear-gradient(90deg,#8fd4ff,#d0edff)')+
    '</div>';
};
const _btnClear_v22_prev=$('btnClear').onclick;
$('btnClear').onclick=()=>{ CAMPAIGN_CLOCK.hours=0; CAMPAIGN_CLOCK.lastT=0; _btnClear_v22_prev(); };
addLog('V22 CAMPAIGN THEATERS ONLINE: asset counts, regional sectors, and timeline clock active.', 'good-entry');


/* ═══════════════════════════════════════════════════════
   V23 THEATER COMBAT LOOPS
   Separate squadron attrition, fleet wear, brigade pressure,
   and battery kill-chain degradation by sector.
   ═══════════════════════════════════════════════════════ */
const THEATER_WAR={};
metrics.cityCaptureSamples=[]; metrics.batteryKillChainSamples=[]; metrics.theaterPairs=[];

function ensureTheaterWarState(country){
  if(!country) return null;
  if(THEATER_WAR[country]) return THEATER_WAR[country];
  const base=estimateAssetCounts_base(country);
  THEATER_WAR[country]={
    squadrons:{base:base.squadrons, current:base.squadrons, losses:0, fatigue:0},
    fleets:{base:base.fleets, current:base.fleets, losses:0, fatigue:0},
    brigades:{base:base.brigades, current:base.brigades, losses:0, fatigue:0},
    batteries:{base:base.batteries, current:base.batteries, losses:0, fatigue:0},
    sectorPressure:{},
    cityCapture:0,
    airSuperiority:0.5,
    seaControl:0.5,
    landControl:0.5,
    batteryKillChain:1.0,
    lastTick:performance.now()
  };
  return THEATER_WAR[country];
}
const estimateAssetCounts_base=estimateAssetCounts;
estimateAssetCounts=function(country){
  const st=ensureTheaterWarState(country);
  const base=estimateAssetCounts_base(country);
  if(!st) return base;
  const ws=ensureDomainWarState(country);
  const c2f=clamp((ws.c2.health||0.7)*(1-0.38*(ws.c2.degraded||0)),0.18,1.2);
  const logf=clamp(logisticsFactor(ws),0.12,1.25);
  const pressurePenalty=1-clamp(st.cityCapture||0,0,0.92)*0.30;
  return {
    squadrons: Math.max(0, Math.min(base.squadrons, Math.round(st.squadrons.current * (0.82+0.18*c2f)))),
    fleets: Math.max(0, Math.min(base.fleets, Math.round(st.fleets.current * (0.86+0.14*logf)))),
    brigades: Math.max(0, Math.min(base.brigades, Math.round(st.brigades.current * pressurePenalty))),
    batteries: Math.max(0, Math.min(base.batteries, Math.round(st.batteries.current * st.batteryKillChain)))
  };
};
function theaterAssetRatio(country, key){
  const st=ensureTheaterWarState(country); if(!st||!st[key]) return 0.5;
  const a=st[key];
  return clamp((a.current||0)/Math.max(1,a.base||1),0,1.25);
}
function degradeSectorKillChain(country, severity){
  if(!country) return;
  const st=ensureTheaterWarState(country); if(!st) return;
  st.batteryKillChain=clamp((st.batteryKillChain||1) - severity, 0.22, 1.04);
  const net=(typeof getDefenseNetworkForCountry==='function')?getDefenseNetworkForCountry(country):[];
  for(const node of (net||[]).slice(0,5)){
    const sec=getSectorStatus(country,node.name);
    sec.damage=clamp((sec.damage||0)+severity*(0.45+0.35*seeded01(country+node.name+':kk')),0,0.98);
    sec.watch=clamp((sec.watch||0.7)-severity*0.55,0.08,1.0);
    sec.readyAt=Math.max(sec.readyAt||0, performance.now()+severity*9000*(0.6+seeded01(node.name+':ra')));
  }
}
function theaterPairMap(){
  const pairs=new Map();
  for(const p of projectiles){
    if(!p || !(p.alive||(!p._outcomeRecorded&&p.impactAge<150))) continue;
    const a=p.attackerCountry||inferCountryFromPlaceName(p.fromName||'');
    const d=p.defenderCountry||inferCountryFromPlaceName(p.toName||'');
    if(!a || !d || a===d) continue;
    const key=a+'→'+d;
    if(!pairs.has(key)) pairs.set(key,{attacker:a,defender:d,liveThreats:0,modes:{air:0,sea:0,land:0},mach:0});
    const rec=pairs.get(key);
    rec.liveThreats += p.alive?1:0.35;
    const kind=p.domainKind||classifyAttackDomain(p);
    rec.modes[kind]=(rec.modes[kind]||0)+1;
    rec.mach += Math.min(30, p.cmdMach||p.getMach&&p.getMach()||5);
  }
  return Array.from(pairs.values());
}
function applyAttritionLoss(side,key,amt){
  const bucket=side && side[key]; if(!bucket) return 0;
  const loss=Math.min(bucket.current||0, Math.max(0,amt||0));
  bucket.current=Math.max(0, bucket.current-loss);
  bucket.losses=(bucket.losses||0)+loss;
  bucket.fatigue=clamp((bucket.fatigue||0)+0.015*loss,0,0.92);
  return loss;
}
function processTheaterCombat(){
  const pairs=theaterPairMap();
  metrics.theaterPairs=pairs.slice(0,6).map(p=>p.attacker+'→'+p.defender+'('+p.liveThreats.toFixed(1)+')');
  const dt=0.30;
  for(const pair of pairs){
    const atk=ensureTheaterWarState(pair.attacker), def=ensureTheaterWarState(pair.defender);
    const bal=currentDomainBalance();
    const atkProf=domainProfile(pair.attacker), defProf=domainProfile(pair.defender);
    const atkWs=ensureDomainWarState(pair.attacker), defWs=ensureDomainWarState(pair.defender);
    const avgMach=pair.mach/Math.max(1,pair.liveThreats);
    const threatWeight=clamp(pair.liveThreats*(0.45+0.02*avgMach),0.25,6.0);
    const atkAir=(atkProf.air||0.3)*(0.70+0.45*theaterAssetRatio(pair.attacker,'squadrons'));
    const defAir=(defProf.air||0.3)*(0.72+0.50*theaterAssetRatio(pair.defender,'squadrons'))*(0.78+0.32*theaterAssetRatio(pair.defender,'batteries'));
    const airDelta=atkAir-defAir;
    atk.airSuperiority=clamp(0.5+0.45*(airDelta),0.02,0.98);
    def.airSuperiority=1-atk.airSuperiority;
    const atkSea=(atkProf.sea||0.15)*(0.70+0.48*theaterAssetRatio(pair.attacker,'fleets'))*(0.78+0.26*logisticsFactor(atkWs));
    const defSea=(defProf.sea||0.15)*(0.70+0.48*theaterAssetRatio(pair.defender,'fleets'))*(0.78+0.26*logisticsFactor(defWs));
    atk.seaControl=clamp(0.5+0.42*(atkSea-defSea),0.04,0.96);
    def.seaControl=1-atk.seaControl;
    const atkLand=(atkProf.land||0.2)*(0.68+0.52*theaterAssetRatio(pair.attacker,'brigades'))*(0.70+0.30*atk.airSuperiority);
    const defLand=(defProf.land||0.2)*(0.68+0.52*theaterAssetRatio(pair.defender,'brigades'))*(0.72+0.28*def.airSuperiority);
    atk.landControl=clamp(0.5+0.38*(atkLand-defLand),0.04,0.96);
    def.landControl=1-atk.landControl;

    const airLossAtk = dt*threatWeight*clamp(0.014 + 0.038*def.airSuperiority*(1+pair.modes.air*0.20),0,0.22);
    const airLossDef = dt*threatWeight*clamp(0.012 + 0.042*atk.airSuperiority*(1+pair.modes.air*0.24),0,0.24);
    applyAttritionLoss(atk,'squadrons',airLossAtk);
    applyAttritionLoss(def,'squadrons',airLossDef);

    const navalContest=(pair.modes.sea||0) + ((avgMach>10 && Math.abs(pair.modes.land-pair.modes.air)<2)?0.15:0);
    if(navalContest>0.12){
      const seaLossAtk = dt*(0.008+0.020*def.seaControl)*navalContest;
      const seaLossDef = dt*(0.008+0.022*atk.seaControl)*navalContest;
      applyAttritionLoss(atk,'fleets',seaLossAtk);
      applyAttritionLoss(def,'fleets',seaLossDef);
      atkWs.logistics.strain=clamp((atkWs.logistics.strain||0)+seaLossAtk*0.0025,0,0.95);
      defWs.logistics.strain=clamp((defWs.logistics.strain||0)+seaLossDef*0.0025,0,0.95);
    }

    const landPressure = dt*threatWeight*clamp(0.010 + 0.040*atk.landControl + 0.022*atk.airSuperiority + 0.018*(pair.modes.land||0),0,0.26);
    const relief = dt*clamp(0.006 + 0.026*def.landControl + 0.010*def.airSuperiority,0,0.18);
    def.cityCapture=clamp((def.cityCapture||0)+landPressure-relief,0,0.995);
    atk.cityCapture=clamp((atk.cityCapture||0)+dt*(0.003+0.012*def.landControl)-dt*(0.002+0.010*atk.landControl),0,0.55);
    applyAttritionLoss(def,'brigades', landPressure*(0.55+0.35*atk.landControl));
    applyAttritionLoss(atk,'brigades', dt*threatWeight*(0.004+0.015*def.landControl));

    const batteryPressure = dt*threatWeight*clamp(0.010 + 0.050*atk.airSuperiority + 0.018*(pair.modes.air||0) + 0.012*(pair.modes.land||0),0,0.28);
    applyAttritionLoss(def,'batteries', batteryPressure*(0.70+0.35*atk.airSuperiority));
    degradeSectorKillChain(pair.defender, batteryPressure*0.040);
    def.batteryKillChain=clamp(def.batteryKillChain*(1-0.012*batteryPressure) - 0.002*(def.cityCapture||0),0.20,1.03);
    atk.batteryKillChain=clamp(atk.batteryKillChain + 0.0015*atk.airSuperiority,0.24,1.04);

    const net=(typeof getDefenseNetworkForCountry==='function')?getDefenseNetworkForCountry(pair.defender):[];
    for(const node of (net||[]).slice(0,4)){
      const key=node.name;
      def.sectorPressure[key]=clamp((def.sectorPressure[key]||0)+landPressure*(0.45+0.30*seeded01(key+pair.attacker)),0,1.1);
    }
  }

  for(const country of Object.keys(THEATER_WAR)){
    const st=THEATER_WAR[country];
    const ws=ensureDomainWarState(country);
    for(const k of ['squadrons','fleets','brigades','batteries']){
      const a=st[k]; if(!a) continue;
      const regen=0.0022*(a.base||1)*(0.45+0.55*logisticsFactor(ws))*(1-(a.fatigue||0)*0.75);
      a.current=Math.min(a.base, a.current+regen);
      a.fatigue=clamp((a.fatigue||0)-0.0011,0,0.92);
    }
    st.cityCapture=clamp((st.cityCapture||0)-0.0008*(0.7+0.3*domainAssetFactor(ws.groundDefense||ws.land)),0,0.995);
    st.batteryKillChain=clamp((st.batteryKillChain||1)+0.0009*(0.6+0.4*(ws.c2.health||0.7)),0.20,1.04);
    for(const kk of Object.keys(st.sectorPressure||{})){
      st.sectorPressure[kk]=clamp((st.sectorPressure[kk]||0)-0.0012,0,1.2);
    }
  }

  metrics.cityCaptureSamples=Object.keys(THEATER_WAR).slice(0,12).map(c=>({country:c,v:THEATER_WAR[c].cityCapture||0}))
    .sort((a,b)=>b.v-a.v).slice(0,6);
  metrics.batteryKillChainSamples=Object.keys(THEATER_WAR).slice(0,12).map(c=>({country:c,v:THEATER_WAR[c].batteryKillChain||1}))
    .sort((a,b)=>a.v-b.v).slice(0,6);
}
function drawBatteryKillChainHalo(country, anchor){
  const st=ensureTheaterWarState(country); if(!st||!anchor) return;
  const pr=projectLL(anchor.lat,anchor.lon,1.019); if(!pr.visible) return;
  const weak=1-clamp(st.batteryKillChain||1,0,1.1);
  if(weak<0.06) return;
  ctx.save();
  ctx.globalAlpha=0.10+0.18*weak;
  ctx.strokeStyle='rgba(255,88,88,0.95)';
  ctx.setLineDash([4,5]);
  ctx.lineWidth=1.2+2.0*weak;
  ctx.beginPath(); ctx.arc(pr.x,pr.y,26+44*weak,0,Math.PI*2); ctx.stroke();
  ctx.restore();
}
function drawCapturePressure(country, anchor){
  const st=ensureTheaterWarState(country); if(!st||!anchor) return;
  const pr=projectLL(anchor.lat,anchor.lon,1.018); if(!pr.visible) return;
  const cap=clamp(st.cityCapture||0,0,1);
  if(cap<0.05) return;
  ctx.save();
  const rr=18+36*cap;
  const g=ctx.createRadialGradient(pr.x,pr.y,0,pr.x,pr.y,rr);
  g.addColorStop(0,'rgba(255,164,64,'+(0.12+0.18*cap)+')');
  g.addColorStop(1,'rgba(255,164,64,0)');
  ctx.fillStyle=g; ctx.beginPath(); ctx.arc(pr.x,pr.y,rr,0,Math.PI*2); ctx.fill();
  ctx.restore();
}
const _drawCampaignTheaterOverlay_v23_prev=drawCampaignTheaterOverlay;
drawCampaignTheaterOverlay=function(){
  _drawCampaignTheaterOverlay_v23_prev();
  const active=getActiveCountriesDetailed();
  for(const item of active){
    drawCapturePressure(item.country,item.anchor);
    drawBatteryKillChainHalo(item.country,item.anchor);
  }
};
const _updateDomainMetrics_v23_prev=updateDomainMetrics;
updateDomainMetrics=function(){ _updateDomainMetrics_v23_prev(); processTheaterCombat(); };
const _registerAttackOutcome_v23_prev=registerAttackOutcome;
registerAttackOutcome=function(p){
  _registerAttackOutcome_v23_prev(p);
  if(!p || !p.defenderCountry) return;
  const def=ensureTheaterWarState(p.defenderCountry);
  const atk=ensureTheaterWarState(p.attackerCountry||'');
  const kind=p.domainKind||classifyAttackDomain(p);
  const sev=clamp((p.cmdMach||6)/40,0.06,0.48) + (p.intercepted?0:0.08);
  if(!p.intercepted){
    if(kind==='air'){ applyAttritionLoss(def,'squadrons',0.18+0.9*sev); applyAttritionLoss(def,'batteries',0.12+0.6*sev); }
    else if(kind==='sea'){ applyAttritionLoss(def,'fleets',0.16+0.8*sev); }
    else { applyAttritionLoss(def,'brigades',0.20+1.0*sev); applyAttritionLoss(def,'batteries',0.10+0.45*sev); }
    def.cityCapture=clamp((def.cityCapture||0)+0.03+0.16*sev,0,0.995);
    degradeSectorKillChain(p.defenderCountry,0.018+0.05*sev);
  } else if(atk){
    if(kind==='air') applyAttritionLoss(atk,'squadrons',0.06+0.18*sev);
    else if(kind==='sea') applyAttritionLoss(atk,'fleets',0.05+0.16*sev);
    else applyAttritionLoss(atk,'brigades',0.05+0.12*sev);
  }
};
const _registerInterceptorOutcome_v23_prev=registerInterceptorOutcome;
registerInterceptorOutcome=function(i){
  _registerInterceptorOutcome_v23_prev(i);
  if(!i || !i.defenderCountry) return;
  const def=ensureTheaterWarState(i.defenderCountry);
  if(i.hit){
    def.batteryKillChain=clamp((def.batteryKillChain||1)+0.0035,0.2,1.04);
  }else{
    applyAttritionLoss(def,'batteries',0.015);
    def.batteryKillChain=clamp((def.batteryKillChain||1)-0.0025,0.2,1.04);
  }
};
const _updateHud_v23_prev=updateHud;
updateHud=function(){
  _updateHud_v23_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const at=ensureTheaterWarState(bal.atk.country), df=ensureTheaterWarState(bal.def.country);
  const pct2=v=>Math.round(100*clamp(v,0,1.2));
  hud.innerHTML += '<br>Theater <span class="val">cap '+escapeHtml(bal.def.country)+' '+pct2(df.cityCapture||0)+'%</span>'+
    ' • <span class="val">kill-chain '+escapeHtml(bal.def.country)+' '+pct2(df.batteryKillChain||1)+'%</span>'+
    ' • <span class="val">air sup '+escapeHtml(bal.atk.country)+' '+pct2(at.airSuperiority||0.5)+'%</span>';
};
const _updateEngagementPanel_v23_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v23_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const at=ensureTheaterWarState(bal.atk.country), df=ensureTheaterWarState(bal.def.country);
  const row=(name,a,b,color)=>'<div style="display:flex;align-items:center;gap:8px;margin:2px 0"><span style="width:86px;color:#9fb5c9">'+name+'</span><span style="width:56px;color:#ffd48a;text-align:right">'+a+'</span><div style="flex:1;height:6px;background:#091321;border:1px solid #223246;border-radius:999px;overflow:hidden"><div style="width:'+Math.min(100,Math.round((a/(Math.max(a,b)||1))*100))+'%;height:100%;background:'+color+';opacity:.85"></div></div><span style="width:56px;color:#9ef4ff">'+b+'</span></div>';
  const pairBits=(metrics.theaterPairs||[]).slice(0,3).join(' • ');
  engagementSummary.innerHTML += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid rgba(120,150,180,.12)"><span style="color:#ffc37d">THEATER COMBAT LOOPS</span>'+
    '<div style="color:#8ca2b9;margin:4px 0">Air attrition, fleet wear, brigade pressure, and battery kill-chain degradation now run continuously. '+escapeHtml(pairBits||'No live pair pressure yet')+'.</div>'+
    row('Sqdn losses',Math.round(at.squadrons.losses||0),Math.round(df.squadrons.losses||0),'linear-gradient(90deg,#58e2ff,#8df3ff)')+
    row('Fleet losses',Math.round(at.fleets.losses||0),Math.round(df.fleets.losses||0),'linear-gradient(90deg,#6f86ff,#9cb2ff)')+
    row('Brig losses',Math.round(at.brigades.losses||0),Math.round(df.brigades.losses||0),'linear-gradient(90deg,#ffbb66,#ffd28c)')+
    row('Batt losses',Math.round(at.batteries.losses||0),Math.round(df.batteries.losses||0),'linear-gradient(90deg,#8fd4ff,#d0edff)')+
    '<div style="color:#7f97ad;margin-top:4px">'+escapeHtml(bal.def.country)+' city pressure <span style="color:#ffd48a">'+Math.round(100*clamp(df.cityCapture||0,0,1))+'%</span> • battery kill-chain <span style="color:#9ef4ff">'+Math.round(100*clamp(df.batteryKillChain||1,0,1.2))+'%</span>.</div></div>';
};
const _btnClear_v23_prev=$('btnClear').onclick;
$('btnClear').onclick=()=>{ for(const k of Object.keys(THEATER_WAR)) delete THEATER_WAR[k]; metrics.cityCaptureSamples=[]; metrics.batteryKillChainSamples=[]; metrics.theaterPairs=[]; _btnClear_v23_prev(); };
addLog('V23 THEATER LOOPS ONLINE: squadron attrition, fleet wear, brigade pressure, and battery kill-chain degradation active.', 'good-entry');


/* ═══════════════════════════════════════════════════════
   V24 INFRASTRUCTURE CASCADE UPGRADE
   Adds city capture states, port shutdowns, and airbase runway kills
   with persistent visuals and campaign statistics.
   ═══════════════════════════════════════════════════════ */
const INFRA_WAR={};
function ensureInfraWarState(country){
  country=country||'Unknown';
  if(INFRA_WAR[country]) return INFRA_WAR[country];
  const prof=domainProfile(country);
  const seedNodes=getCountryTheaterNodes(country)||[];
  const cap=seedNodes[0] || getCountryAnchor(country) || {name:country,lat:0,lon:0,importance:1};
  const ports=[]; const airbases=[]; const cities=[];
  const coastalBias=clamp(prof.sea||0.2,0.05,1.2); const airBias=clamp(prof.air||0.2,0.05,1.2); const landBias=clamp(prof.land||0.2,0.05,1.2);
  for(let i=0;i<seedNodes.length;i++){
    const n=seedNodes[i];
    const portLike = (i===0 && coastalBias>0.45) || seeded01(country+':port:'+i) < (0.16 + 0.36*coastalBias);
    const airLike = i<2 || seeded01(country+':airbase:'+i) < (0.24 + 0.32*airBias);
    cities.push({name:n.name.replace(/\s*T\d+$/,''), lat:n.lat, lon:n.lon, importance:n.importance||1, pressure:0, captured:false, captureClock:0, status:'contested'});
    if(portLike) ports.push({name:n.name+' Port', lat:n.lat-0.32, lon:n.lon+0.55, importance:0.75+0.45*(n.importance||1), shutdown:0, throughput:clamp(0.44+0.46*coastalBias+0.10*seeded01(country+':pt:'+i),0.15,1.25), hits:0, offline:false});
    if(airLike) airbases.push({name:n.name+' Airbase', lat:n.lat+0.28, lon:n.lon-0.48, importance:0.80+0.50*(n.importance||1), runwayDamage:0, sortieRate:clamp(0.46+0.42*airBias+0.12*seeded01(country+':ab:'+i),0.16,1.25), hits:0, offline:false});
  }
  if(!ports.length) ports.push({name:cap.name+' Main Port', lat:cap.lat-0.4, lon:cap.lon+0.65, importance:1.0, shutdown:0, throughput:clamp(0.34+0.50*coastalBias,0.12,1.05), hits:0, offline:false});
  if(!airbases.length) airbases.push({name:cap.name+' Airbase', lat:cap.lat+0.34, lon:cap.lon-0.55, importance:1.0, runwayDamage:0, sortieRate:clamp(0.40+0.50*airBias,0.14,1.08), hits:0, offline:false});
  const state={country, ports, airbases, cities, primaryCity:cap.name, portShutdown:0, runwayKill:0, cityCapture:0, infraStress:0, cascade:0, lastUpdate:performance.now()};
  INFRA_WAR[country]=state;
  return state;
}
function nearestInfraNode(list, lat, lon){
  if(!list || !list.length) return null;
  let best=null,bestD=1e9;
  for(const n of list){
    const d=Math.hypot((n.lat-lat)*1.15, ((n.lon-lon+540)%360-180)*Math.cos((lat||0)*Math.PI/180));
    if(d<bestD){ bestD=d; best=n; }
  }
  return best;
}
function updateInfraAggregates(state){
  if(!state) return;
  state.portShutdown = safeMean((state.ports||[]).map(p=>clamp(p.shutdown||0,0,1)));
  state.runwayKill = safeMean((state.airbases||[]).map(a=>clamp(a.runwayDamage||0,0,1)));
  state.cityCapture = safeMean((state.cities||[]).map(c=>clamp(c.pressure||0,0,1)));
  state.infraStress = clamp(0.45*state.portShutdown + 0.35*state.runwayKill + 0.35*state.cityCapture,0,1.5);
  state.cascade = clamp(0.40*state.portShutdown + 0.40*state.runwayKill + 0.25*state.cityCapture,0,1.4);
}
function inflictInfrastructureStrike(defCountry, atkCountry, lat, lon, domainKind, severity, intercepted){
  if(!defCountry) return;
  const st=ensureInfraWarState(defCountry);
  const sev=clamp((severity||0.2) * (intercepted?0.35:1.0), 0.02, 0.95);
  const city=nearestInfraNode(st.cities, lat, lon);
  const port=nearestInfraNode(st.ports, lat, lon);
  const airbase=nearestInfraNode(st.airbases, lat, lon);
  if(city){
    city.pressure = clamp((city.pressure||0) + sev*(domainKind==='land'?0.65:(domainKind==='air'?0.45:0.30))*city.importance, 0, 1.25);
    city.captureClock = (city.captureClock||0) + sev*(domainKind==='land'?1.2:0.6);
    city.captured = city.pressure>0.92;
    city.status = city.captured ? 'captured' : (city.pressure>0.48 ? 'under strike' : 'contested');
  }
  if((domainKind==='sea' || domainKind==='land') && port){
    port.shutdown = clamp((port.shutdown||0) + sev*(0.34 + 0.44*(domainKind==='sea'?1:0.45))*port.importance, 0, 1.25);
    port.hits = (port.hits||0)+1;
    port.offline = port.shutdown>0.88;
  }
  if((domainKind==='air' || domainKind==='land') && airbase){
    airbase.runwayDamage = clamp((airbase.runwayDamage||0) + sev*(0.38 + 0.40*(domainKind==='air'?1:0.35))*airbase.importance, 0, 1.25);
    airbase.hits = (airbase.hits||0)+1;
    airbase.offline = airbase.runwayDamage>0.88;
  }
  updateInfraAggregates(st);
  const dws=ensureDomainWarState(defCountry);
  if(dws){
    dws.logistics.health = clamp(dws.logistics.health - 0.10*st.portShutdown - 0.06*st.cityCapture, 0.08, 1.25);
    dws.c2.health = clamp(dws.c2.health - 0.08*st.runwayKill - 0.06*st.cityCapture, 0.08, 1.20);
    dws.air.ready = Math.max(0, Math.round(dws.air.ready*(1 - 0.05*st.runwayKill)));
    dws.sea.ready = Math.max(0, Math.round(dws.sea.ready*(1 - 0.05*st.portShutdown)));
    dws.land.ready = Math.max(0, Math.round(dws.land.ready*(1 - 0.03*st.cityCapture)));
    dws.history && dws.history.push({t:Date.now(), atk:atkCountry||'', type:'infra', port:st.portShutdown, runway:st.runwayKill, city:st.cityCapture});
    if(dws.history && dws.history.length>60) dws.history.shift();
  }
  const tws=ensureTheaterWarState(defCountry);
  if(tws){
    tws.cityCapture = clamp(Math.max(tws.cityCapture||0, st.cityCapture),0,1.2);
    tws.batteryKillChain = clamp((tws.batteryKillChain||1) - 0.10*st.runwayKill - 0.07*st.cityCapture, 0.18, 1.04);
  }
}
function recoverInfrastructureStates(dtSec){
  const dt=Math.max(0.01, dtSec||0.033);
  for(const k of Object.keys(INFRA_WAR)){
    const st=INFRA_WAR[k]; if(!st) continue;
    for(const p of st.ports||[]){
      const rec=(0.0009 + 0.0018*(ensureDomainWarState(k).logistics.health||0.5))*dt;
      p.shutdown = clamp((p.shutdown||0)-rec,0,1.25); p.offline=p.shutdown>0.88;
    }
    for(const a of st.airbases||[]){
      const rec=(0.0010 + 0.0017*(ensureDomainWarState(k).c2.health||0.5))*dt;
      a.runwayDamage = clamp((a.runwayDamage||0)-rec,0,1.25); a.offline=a.runwayDamage>0.88;
    }
    for(const c of st.cities||[]){
      const rec=(0.00045 + 0.0008*(ensureDomainWarState(k).land.ready/Math.max(1,ensureDomainWarState(k).land.max||1)))*dt;
      c.pressure = clamp((c.pressure||0)-rec,0,1.25);
      c.captured = c.pressure>0.92;
      c.status = c.captured ? 'captured' : (c.pressure>0.48 ? 'under strike' : 'contested');
    }
    updateInfraAggregates(st);
  }
}
function drawPortShutdownOverlay(country, anchor){
  const st=ensureInfraWarState(country); if(!st) return;
  for(const p of (st.ports||[])){
    const q=clamp(p.shutdown||0,0,1); if(q<0.08) continue;
    const pr=projectLL(p.lat,p.lon,1.014); if(!pr.visible) continue;
    ctx.save();
    const rr=12+26*q;
    ctx.strokeStyle='rgba(82,198,255,'+(0.16+0.52*q)+')'; ctx.lineWidth=1.0+2.3*q; ctx.setLineDash([3,4]);
    ctx.beginPath(); ctx.arc(pr.x,pr.y,rr,0,Math.PI*2); ctx.stroke();
    ctx.fillStyle='rgba(82,198,255,'+(0.08+0.12*q)+')'; ctx.beginPath(); ctx.arc(pr.x,pr.y,4+3*q,0,Math.PI*2); ctx.fill();
    ctx.restore();
  }
}
function drawRunwayKillOverlay(country, anchor){
  const st=ensureInfraWarState(country); if(!st) return;
  for(const a of (st.airbases||[])){
    const q=clamp(a.runwayDamage||0,0,1); if(q<0.08) continue;
    const pr=projectLL(a.lat,a.lon,1.015); if(!pr.visible) continue;
    ctx.save();
    ctx.strokeStyle='rgba(255,94,94,'+(0.18+0.56*q)+')'; ctx.lineWidth=1.1+2.0*q;
    const rr=10+24*q; ctx.beginPath(); ctx.moveTo(pr.x-rr,pr.y-rr); ctx.lineTo(pr.x+rr,pr.y+rr); ctx.moveTo(pr.x+rr,pr.y-rr); ctx.lineTo(pr.x-rr,pr.y+rr); ctx.stroke();
    ctx.restore();
  }
}
function drawInfraStressHalo(country, anchor){
  const st=ensureInfraWarState(country); if(!st||!anchor) return;
  const q=clamp(st.infraStress||0,0,1); if(q<0.05) return;
  const pr=projectLL(anchor.lat,anchor.lon,1.016); if(!pr.visible) return;
  ctx.save();
  const rr=24+44*q;
  const g=ctx.createRadialGradient(pr.x,pr.y,0,pr.x,pr.y,rr);
  g.addColorStop(0,'rgba(255,70,70,'+(0.04+0.10*q)+')');
  g.addColorStop(0.45,'rgba(255,170,78,'+(0.07+0.14*q)+')');
  g.addColorStop(1,'rgba(255,170,78,0)');
  ctx.fillStyle=g; ctx.beginPath(); ctx.arc(pr.x,pr.y,rr,0,Math.PI*2); ctx.fill();
  ctx.restore();
}
const _drawCampaignTheaterOverlay_v24_prev=drawCampaignTheaterOverlay;
drawCampaignTheaterOverlay=function(){
  _drawCampaignTheaterOverlay_v24_prev();
  const active=getActiveCountriesDetailed();
  for(const item of active){
    drawInfraStressHalo(item.country,item.anchor);
    drawPortShutdownOverlay(item.country,item.anchor);
    drawRunwayKillOverlay(item.country,item.anchor);
  }
};
const _registerAttackOutcome_v24_prev=registerAttackOutcome;
registerAttackOutcome=function(p){
  _registerAttackOutcome_v24_prev(p);
  if(!p || !p.defenderCountry) return;
  let ll=[0,0];
  try{ ll=p.impactPosU ? v2ll(p.impactPosU) : (p.getLatLon ? p.getLatLon() : (p.toLL||[0,0])); }catch(_e){ ll=[0,0]; }
  const kind=p.domainKind||classifyAttackDomain(p);
  const sev=clamp((p.cmdMach||6)/36 + (p.realistic?0.04:0) + ((p.mode==='cruise'||kind==='air')?0.05:0),0.06,0.72);
  inflictInfrastructureStrike(p.defenderCountry,p.attackerCountry||'',ll[0],ll[1],kind,sev,!!p.intercepted);
};
const _updateDomainMetrics_v24_prev=updateDomainMetrics;
updateDomainMetrics=function(){
  _updateDomainMetrics_v24_prev();
  recoverInfrastructureStates(0.033);
  const active=getActiveCountriesDetailed();
  metrics.portShutdownSamples=[]; metrics.runwayKillSamples=[]; metrics.infraStressPairs=[];
  for(const item of active){
    const st=ensureInfraWarState(item.country);
    metrics.portShutdownSamples.push(st.portShutdown||0);
    metrics.runwayKillSamples.push(st.runwayKill||0);
    metrics.infraStressPairs.push(item.country+':P'+Math.round(100*(st.portShutdown||0))+' R'+Math.round(100*(st.runwayKill||0))+' C'+Math.round(100*(st.cityCapture||0)));
  }
};
const _updateHud_v24_prev=updateHud;
updateHud=function(){
  _updateHud_v24_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const ds=ensureInfraWarState(bal.def.country);
  hud.innerHTML += '<br>Infra <span class="val">ports '+escapeHtml(bal.def.country)+' '+Math.round(100*clamp(ds.portShutdown||0,0,1))+'%</span>'+
    ' • <span class="val">runways '+escapeHtml(bal.def.country)+' '+Math.round(100*clamp(ds.runwayKill||0,0,1))+'%</span>'+
    ' • <span class="val">cities '+escapeHtml(bal.def.country)+' '+Math.round(100*clamp(ds.cityCapture||0,0,1))+'%</span>';
};
const _updateEngagementPanel_v24_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v24_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const ds=ensureInfraWarState(bal.def.country), as=ensureInfraWarState(bal.atk.country);
  const row=(name,a,b,color)=>'<div style="display:flex;align-items:center;gap:8px;margin:2px 0"><span style="width:86px;color:#9fb5c9">'+name+'</span><span style="width:56px;color:#ffd48a;text-align:right">'+a+'</span><div style="flex:1;height:6px;background:#091321;border:1px solid #223246;border-radius:999px;overflow:hidden"><div style="width:'+Math.min(100,Math.round((a/(Math.max(a,b)||1))*100))+'%;height:100%;background:'+color+';opacity:.85"></div></div><span style="width:56px;color:#9ef4ff">'+b+'</span></div>';
  const pairBits=(metrics.infraStressPairs||[]).slice(0,3).join(' • ');
  engagementSummary.innerHTML += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid rgba(120,150,180,.12)"><span style="color:#ffae73">INFRASTRUCTURE CASCADE</span>'+
    '<div style="color:#8ca2b9;margin:4px 0">Ports can shut down, runways can be cratered, and cities can tip into capture pressure. '+escapeHtml(pairBits||'No infrastructure stress yet')+'.</div>'+
    row('Port shut',Math.round(100*clamp(as.portShutdown||0,0,1)),Math.round(100*clamp(ds.portShutdown||0,0,1)),'linear-gradient(90deg,#60d5ff,#a0efff)')+
    row('Runway kill',Math.round(100*clamp(as.runwayKill||0,0,1)),Math.round(100*clamp(ds.runwayKill||0,0,1)),'linear-gradient(90deg,#ff6b6b,#ffb17b)')+
    row('City capture',Math.round(100*clamp(as.cityCapture||0,0,1)),Math.round(100*clamp(ds.cityCapture||0,0,1)),'linear-gradient(90deg,#ffae66,#ffd79c)')+
    '<div style="color:#7f97ad;margin-top:4px">Defender cascade stress <span style="color:#ffd48a">'+Math.round(100*clamp(ds.cascade||0,0,1.4))+'%</span> • logistics drag <span style="color:#9ef4ff">'+Math.round(100*clamp(1-(ensureDomainWarState(bal.def.country).logistics.health||0.5),0,1))+'%</span>.</div></div>';
};
const _btnClear_v24_prev=$('btnClear').onclick;
$('btnClear').onclick=()=>{ for(const k of Object.keys(INFRA_WAR)) delete INFRA_WAR[k]; metrics.portShutdownSamples=[]; metrics.runwayKillSamples=[]; metrics.infraStressPairs=[]; _btnClear_v24_prev(); };
addLog('V24 INFRASTRUCTURE CASCADE ONLINE: city capture, port shutdown, and runway-kill layers active.', 'good-entry');


/* ═══════════════════════════════════════════════════════
   V25 FUNCTIONAL CLOSURES + SECTOR OWNERSHIP DRAG
   Ports now throttle naval launches, runway kills throttle sortie generation,
   and city-capture pressure shifts defense/counterstrike origin choice.
   ═══════════════════════════════════════════════════════ */
function infraClosureFactor(country, domain){
  const st=ensureInfraWarState(country||'');
  const port=clamp(st.portShutdown||0,0,1.25);
  const runway=clamp(st.runwayKill||0,0,1.25);
  const city=clamp(st.cityCapture||0,0,1.25);
  const cascade=clamp(st.cascade||0,0,1.4);
  if(domain==='sea') return clamp(1 - 0.72*port - 0.18*city - 0.10*cascade, 0.05, 1.05);
  if(domain==='air' || domain==='airDefense') return clamp(1 - 0.74*runway - 0.16*city - 0.10*cascade, 0.05, 1.05);
  if(domain==='land') return clamp(1 - 0.42*city - 0.18*runway - 0.08*cascade, 0.08, 1.05);
  if(domain==='logistics') return clamp(1 - 0.42*port - 0.32*runway - 0.20*city, 0.08, 1.05);
  return clamp(1 - 0.30*port - 0.30*runway - 0.28*city, 0.06, 1.05);
}
function nodeClosurePenalty(country,node){
  const st=ensureInfraWarState(country||''); if(!st||!node) return 0;
  const ll=[node.lat,node.lon];
  const cityNear=(st.cities||[]).map(c=>({d:gcDistMeters(ll,[c.lat,c.lon]), q:clamp(c.pressure||0,0,1.25)})).sort((a,b)=>a.d-b.d)[0];
  const portNear=(st.ports||[]).map(c=>({d:gcDistMeters(ll,[c.lat,c.lon]), q:clamp(c.shutdown||0,0,1.25)})).sort((a,b)=>a.d-b.d)[0];
  const abNear=(st.airbases||[]).map(c=>({d:gcDistMeters(ll,[c.lat,c.lon]), q:clamp(c.runwayDamage||0,0,1.25)})).sort((a,b)=>a.d-b.d)[0];
  let p=0;
  if(cityNear && cityNear.d<260000) p += 0.55*cityNear.q*(1-cityNear.d/260000);
  if(portNear && portNear.d<220000) p += 0.45*portNear.q*(1-portNear.d/220000);
  if(abNear && abNear.d<220000) p += 0.50*abNear.q*(1-abNear.d/220000);
  if(/capital/i.test(node.kind||'')) p += 0.18*clamp(st.cityCapture||0,0,1);
  return clamp(p,0,1.25);
}
function chooseFallbackClosureNode(country, preferKind){
  const nodes=getCityDefenseNodes(country, resolveSeedPlaceFast(country));
  if(!nodes.length) return resolveSeedPlaceFast(country);
  let ranked=nodes.slice().map(n=>({n, score:(n.weight||0.6) - 0.95*nodeClosurePenalty(country,n) + ((preferKind&&new RegExp(preferKind,'i').test(n.kind||''))?0.08:0)}));
  ranked.sort((a,b)=>b.score-a.score);
  return ranked[0] ? ranked[0].n : nodes[0];
}
const _chooseDefenseNodeForThreat_v25_prev=chooseDefenseNodeForThreat;
chooseDefenseNodeForThreat=function(country, threat, fallbackPlace){
  const node=_chooseDefenseNodeForThreat_v25_prev(country, threat, fallbackPlace);
  const nodes=getCityDefenseNodes(country, fallbackPlace||resolveSeedPlaceFast(country));
  if(!nodes.length) return node;
  let best=node||nodes[0], bestScore=-1e9;
  const doctrine=getDoctrineForCountry(country||'Default');
  for(const cand of nodes){
    const score=defenseNodeScore(country,cand,threat,doctrine) - 1.10*nodeClosurePenalty(country,cand);
    if(score>bestScore){ bestScore=score; best=cand; }
  }
  return best;
};
const _chooseCounterstrikeOrigin_v25_prev=chooseCounterstrikeOrigin;
chooseCounterstrikeOrigin=function(country, enemyCountry, incomingAttack){
  const node=_chooseCounterstrikeOrigin_v25_prev(country, enemyCountry, incomingAttack);
  const st=ensureInfraWarState(country||'');
  if(node && nodeClosurePenalty(country,node) < 0.38) return node;
  const airGate=infraClosureFactor(country,'air');
  const seaGate=infraClosureFactor(country,'sea');
  const prefer=(airGate>=seaGate)?'air|capital|central':'port|coast|naval';
  const fallback=chooseFallbackClosureNode(country, prefer);
  if(fallback && fallback!==node){
    addLog('COUNTERSTRIKE ORIGIN SHIFT: '+escapeHtml(country)+' rerouting launch origin toward '+escapeHtml(shortPlaceName(fallback))+' due to local infrastructure/city pressure.', 'info-entry');
    return fallback;
  }
  return node || fallback;
};
const _domainProfile_v25_prev=domainProfile;
domainProfile=function(country){
  const out=_domainProfile_v25_prev(country);
  out.air=clamp(out.air*infraClosureFactor(country,'air'),0.02,1.25);
  out.sea=clamp(out.sea*infraClosureFactor(country,'sea'),0.02,1.20);
  out.land=clamp(out.land*infraClosureFactor(country,'land'),0.02,1.20);
  out.logistics=clamp(out.logistics*infraClosureFactor(country,'logistics'),0.02,1.20);
  out.integrated=clamp(0.34*out.air+0.18*out.sea+0.24*out.land+0.16*out.logistics+0.08*clamp((out.warState&&out.warState.c2&&out.warState.c2.health)||0.7,0.05,1.2),0.02,1.30);
  out.closure={air:infraClosureFactor(country,'air'),sea:infraClosureFactor(country,'sea'),land:infraClosureFactor(country,'land'),logistics:infraClosureFactor(country,'logistics')};
  return out;
};
const _launchProjectedAttack_v25_prev=launchProjectedAttack;
launchProjectedAttack=function(opts){
  opts=opts||{};
  const from=opts.from, to=opts.to;
  let attackerCountry=opts.attackerCountry||((from&&getArsenalForPlace(from.name||''))||{}).country||'';
  const chosenWeapon=opts.weapon || getCurrentSelectedWeapon() || chooseWeaponForCountry(attackerCountry);
  const guessedKind=(chosenWeapon && /carrier|sub|ship|naval/i.test(chosenWeapon.name||'')) ? 'sea' : (chosenWeapon && /cruise|air|fighter|bomber/i.test(chosenWeapon.name||'')) ? 'air' : 'land';
  const gate=infraClosureFactor(attackerCountry, guessedKind);
  const closureFail=(guessedKind==='sea' && gate<0.22) || (guessedKind==='air' && gate<0.18);
  if(attackerCountry && (closureFail || Math.random() > clamp(0.15 + 0.85*gate,0.12,0.995))){
    addLog('FUNCTIONAL CLOSURE: '+escapeHtml(attackerCountry)+' could not generate a '+escapeHtml(guessedKind.toUpperCase())+' sortie. Infrastructure stress blocked or aborted launch.', 'warn-entry');
    const ws=ensureDomainWarState(attackerCountry);
    ws.logistics.strain=clamp((ws.logistics.strain||0)+0.018,0,0.95);
    ws.c2.degraded=clamp((ws.c2.degraded||0)+0.01,0,1.2);
    return null;
  }
  const attack=_launchProjectedAttack_v25_prev(opts);
  if(attack && attackerCountry){
    const kind=attack.domainKind||classifyAttackDomain(attack)||guessedKind;
    const postGate=infraClosureFactor(attackerCountry, kind);
    attack.infrastructureGate=postGate;
    attack.systemReliability=clamp((attack.systemReliability||0.9)*(0.72+0.32*postGate),0.03,0.995);
    attack.sensorQuality=clamp((attack.sensorQuality||0.65)*(0.74+0.28*postGate),0.08,0.995);
    if(kind==='air') attack.cmdMach=Math.max(0.8, (attack.cmdMach||4)*(0.82+0.18*postGate));
    if(kind==='sea') attack.dragCoef=(attack.dragCoef||0.0006)*(1.06-0.08*postGate);
  }
  return attack;
};
const _activateNationalDefense_v25_prev=activateNationalDefense;
activateNationalDefense=function(opts){
  const before=interceptors.length;
  const n=_activateNationalDefense_v25_prev(opts);
  let blocked=0;
  for(let idx=interceptors.length-1; idx>=before; idx--){
    const i=interceptors[idx]; if(!i) continue;
    const gate=infraClosureFactor(i.defenderCountry||((opts&&opts.toVal)||''), (i.domainBucket==='airDefense'?'airDefense':'land'));
    const locPenalty=nodeClosurePenalty(i.defenderCountry||'', {lat:i.launchLat||((opts&&opts.defSite)||{}).lat||0, lon:i.launchLon||((opts&&opts.defSite)||{}).lon||0, kind:'battery'});
    const eff=clamp(gate*(1-0.55*locPenalty),0.04,1.05);
    if(eff<0.16 || Math.random()>clamp(0.10+0.90*eff,0.10,0.995)){
      interceptors.splice(idx,1);
      blocked++;
      continue;
    }
    i.pkBase=clamp((i.pkBase||0.45)*(0.70+0.34*eff),0.03,0.995);
    i.sensorQuality=clamp((i.sensorQuality||0.65)*(0.72+0.30*eff),0.08,0.995);
    i.delaySec=(i.delaySec||0) + Math.max(0, (1-eff)*1.8);
    i.infrastructureGate=eff;
  }
  if(blocked>0){
    const country=((opts&&opts.toVal)||'').trim()||'Defender';
    addLog('DEFENSE CLOSURE DRAG: '+escapeHtml(country)+' lost '+blocked+' queued defensive launch'+(blocked===1?'':'es')+' to runway/sector infrastructure disruption.', 'warn-entry');
  }
  return Math.max(0, (n||0)-blocked);
};
const _scheduleCounterstrike_v25_prev=scheduleCounterstrike;
scheduleCounterstrike=function(attack){
  if(!attack || !attack.autoCounterEnabled) return _scheduleCounterstrike_v25_prev(attack);
  const gate=infraClosureFactor(attack.defenderCountry||'', 'logistics');
  if(gate<0.10){
    addLog('COUNTERSTRIKE SUPPRESSED: '+escapeHtml(attack.defenderCountry||'Defender')+' cannot organize an immediate reply under current infrastructure/C2 collapse.', 'warn-entry');
    return;
  }
  return _scheduleCounterstrike_v25_prev(attack);
};
const _updateHud_v25_prev=updateHud;
updateHud=function(){
  _updateHud_v25_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const atkP=domainProfile(bal.atk.country), defP=domainProfile(bal.def.country);
  hud.innerHTML += '<br>Closure <span class="val">'+escapeHtml(bal.atk.country)+' A '+Math.round(100*clamp((atkP.closure&&atkP.closure.air)||1,0,1.05))+'%</span>'+
    ' / <span class="val">S '+Math.round(100*clamp((atkP.closure&&atkP.closure.sea)||1,0,1.05))+'%</span>'+
    ' • <span class="val">'+escapeHtml(bal.def.country)+' A '+Math.round(100*clamp((defP.closure&&defP.closure.air)||1,0,1.05))+'%</span>'+
    ' / <span class="val">S '+Math.round(100*clamp((defP.closure&&defP.closure.sea)||1,0,1.05))+'%</span>';
};
const _updateEngagementPanel_v25_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v25_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const atkP=domainProfile(bal.atk.country), defP=domainProfile(bal.def.country);
  const row=(name,a,b,color)=>'<div style="display:flex;align-items:center;gap:8px;margin:2px 0"><span style="width:86px;color:#9fb5c9">'+name+'</span><span style="width:56px;color:#ffd48a;text-align:right">'+a+'</span><div style="flex:1;height:6px;background:#091321;border:1px solid #223246;border-radius:999px;overflow:hidden"><div style="width:'+Math.min(100,Math.round((a/(Math.max(a,b)||1))*100))+'%;height:100%;background:'+color+';opacity:.85"></div></div><span style="width:56px;color:#9ef4ff">'+b+'</span></div>';
  engagementSummary.innerHTML += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid rgba(120,150,180,.12)"><span style="color:#7fe8ff">FUNCTIONAL CLOSURES</span>'+
    '<div style="color:#8ca2b9;margin:4px 0">Ports now throttle naval launches, runway damage throttles sortie generation, and capture pressure pushes launch origins away from stressed sectors.</div>'+
    row('Air gate',Math.round(100*clamp((atkP.closure&&atkP.closure.air)||1,0,1.05)),Math.round(100*clamp((defP.closure&&defP.closure.air)||1,0,1.05)),'linear-gradient(90deg,#6ee7ff,#b8f7ff)')+
    row('Sea gate',Math.round(100*clamp((atkP.closure&&atkP.closure.sea)||1,0,1.05)),Math.round(100*clamp((defP.closure&&defP.closure.sea)||1,0,1.05)),'linear-gradient(90deg,#7ac7ff,#d3f0ff)')+
    row('Land gate',Math.round(100*clamp((atkP.closure&&atkP.closure.land)||1,0,1.05)),Math.round(100*clamp((defP.closure&&defP.closure.land)||1,0,1.05)),'linear-gradient(90deg,#ffba6b,#ffe0a8)')+
    '</div>';
};
const _btnClear_v25_prev=$('btnClear').onclick;
$('btnClear').onclick=()=>{ _btnClear_v25_prev(); };
addLog('V25 FUNCTIONAL CLOSURES ONLINE: ports throttle sea launches, runway kills throttle air launches, and city pressure shifts origin/sector ownership.', 'good-entry');

</script>
</body>
</html>
'''



EXTRA_V26_JS = r'''

<script>
(function(){
const OPS_V26={};
let OPS_V26_LAST=performance.now();
function meanWeighted(arr, fn){
  if(!arr || !arr.length) return 0;
  let num=0, den=0;
  for(const x of arr){ const w=Math.max(0.1, +((x&&x.importance)||1)); num += w*fn(x); den += w; }
  return den>0 ? num/den : 0;
}
function ensureOpsV26(country){
  if(!country) return null;
  const infra=ensureInfraWarState(country); if(!infra) return null;
  if(!OPS_V26[country]) OPS_V26[country]={country, sortiesGenerated:0, navalDepartures:0, lostCityShare:0, repairLoad:0, lastUpdate:performance.now()};
  const ops=OPS_V26[country];
  const prof=(typeof _domainProfile_v25_prev==='function') ? _domainProfile_v25_prev(country) : domainProfile(country);
  for(const a of (infra.airbases||[])){
    if(a.sortieQueue==null) a.sortieQueue=0;
    if(a.turnaroundH==null) a.turnaroundH=clamp(1.2 + 2.4*(1-clamp(prof.air||0.4,0,1.2)) + 0.8*seeded01(country+':ta:'+a.name),0.7,4.8);
    if(a.repairQueue==null) a.repairQueue=0;
    if(a.suppression==null) a.suppression=0;
    if(a.operationalFactor==null) a.operationalFactor=1;
    if(a.maxQueue==null) a.maxQueue=Math.max(1, Math.round((a.importance||1)*2 + 2.2*clamp(prof.air||0.3,0.1,1.4)));
  }
  for(const p of (infra.ports||[])){
    if(p.berthLoad==null) p.berthLoad=0;
    if(p.repairQueue==null) p.repairQueue=0;
    if(p.operationalFactor==null) p.operationalFactor=1;
    if(p.maxBerths==null) p.maxBerths=Math.max(1, Math.round((p.importance||1)*1.6 + 2.4*clamp(prof.sea||0.25,0.08,1.4)));
    if(p.turnH==null) p.turnH=clamp(3.0 + 5.0*(1-clamp(prof.sea||0.3,0,1.2)) + 1.2*seeded01(country+':pt:'+p.name),1.5,10.0);
  }
  for(const c of (infra.cities||[])){
    if(c.controlScore==null) c.controlScore=0.85;
    if(c.controller==null) c.controller=country;
    if(c.captureBy==null) c.captureBy='';
    if(c.contestedH==null) c.contestedH=0;
  }
  return ops;
}
function dominantAttackerAgainst(country){
  const tally={};
  for(const p of projectiles){
    if(!p || !p.alive || p.defenderCountry!==country) continue;
    const a=p.attackerCountry || inferCountryFromPlaceName(p.fromName||'') || '';
    if(!a) continue;
    tally[a]=(tally[a]||0)+(p.kind==='decoy'?0.2:1)*(1+0.02*(p.cmdMach||0));
  }
  let best='', score=0;
  for(const k in tally){ if(tally[k]>score){ score=tally[k]; best=k; } }
  return best;
}
function computeInboundPressure(country){
  let score=0;
  for(const p of projectiles){
    if(!p || !p.alive || p.defenderCountry!==country) continue;
    score += (p.kind==='decoy'?0.18:0.55) + 0.02*Math.min(25, p.cmdMach||0) + 0.25*(p.intercepted?0:1);
  }
  return clamp(score/8,0,1.6);
}
function allocateSortie(country, ll){
  const ops=ensureOpsV26(country); const infra=ensureInfraWarState(country); if(!ops || !infra || !(infra.airbases||[]).length) return null;
  const node=nearestInfraNode(infra.airbases, ll[0], ll[1]) || infra.airbases[0];
  const cap=Math.max(1, node.maxQueue||2);
  node.sortieQueue=(node.sortieQueue||0)+1;
  const overload=Math.max(0, (node.sortieQueue-cap)/cap);
  const suppression=clamp(node.suppression||0,0,1.2);
  const runway=clamp(node.runwayDamage||0,0,1.2);
  node.operationalFactor=clamp((1-0.78*runway)*(1-0.55*suppression)*(1-0.25*overload),0.08,1.05);
  ops.sortiesGenerated=(ops.sortiesGenerated||0)+1;
  return {node, overload, rel:clamp(node.operationalFactor*(0.92-0.16*overload),0.18,1.0), speedMul:clamp(0.94-0.07*overload-0.06*runway,0.72,1.0)};
}
function allocatePortDeparture(country, ll){
  const ops=ensureOpsV26(country); const infra=ensureInfraWarState(country); if(!ops || !infra || !(infra.ports||[]).length) return null;
  const node=nearestInfraNode(infra.ports, ll[0], ll[1]) || infra.ports[0];
  const cap=Math.max(1, node.maxBerths||2);
  node.berthLoad=(node.berthLoad||0)+1;
  const overload=Math.max(0, (node.berthLoad-cap)/cap);
  const shut=clamp(node.shutdown||0,0,1.2);
  node.operationalFactor=clamp((1-0.80*shut)*(1-0.35*overload),0.08,1.08);
  ops.navalDepartures=(ops.navalDepartures||0)+1;
  return {node, overload, rel:clamp(node.operationalFactor*(0.94-0.14*overload),0.20,1.02), speedMul:clamp(0.96-0.06*overload-0.04*shut,0.74,1.02)};
}
function updateOpsV26(dtSec){
  const dt=Math.max(0.02, dtSec||0.033);
  const activeCountries=new Set(Object.keys(INFRA_WAR));
  for(const p of projectiles){ if(p && p.attackerCountry) activeCountries.add(p.attackerCountry); if(p && p.defenderCountry) activeCountries.add(p.defenderCountry); }
  for(const country of activeCountries){
    const ops=ensureOpsV26(country); const infra=ensureInfraWarState(country); const ws=ensureDomainWarState(country); const tws=ensureTheaterWarState(country); if(!ops||!infra||!ws||!tws) continue;
    const inbound=computeInboundPressure(country);
    const dominant=dominantAttackerAgainst(country);
    const brigadeRatio=theaterAssetRatio(country,'brigades');
    const defenseGrip=clamp(0.52*brigadeRatio + 0.24*clamp(ws.c2.health||0.6,0,1.2) + 0.24*clamp(logisticsFactor(ws),0,1.2),0,1.2);
    for(const a of (infra.airbases||[])){
      const cycle=(1/Math.max(0.4,a.turnaroundH||2.5));
      a.sortieQueue=Math.max(0,(a.sortieQueue||0)-dt*CAMPAIGN_CLOCK.speedHoursPerSec*cycle*(0.85+0.35*clamp(ws.logistics.health||0.6,0.2,1.2)));
      a.suppression=clamp((a.suppression||0) + dt*(0.14*inbound - 0.05*defenseGrip),0,1.3);
      a.repairQueue=clamp((a.repairQueue||0) + dt*(0.10*(a.runwayDamage||0) - 0.04*clamp(ws.c2.health||0.6,0.1,1.2)),0,2.2);
      const overload=Math.max(0, ((a.sortieQueue||0)-(a.maxQueue||2))/Math.max(1,a.maxQueue||2));
      a.operationalFactor=clamp((1-0.74*clamp(a.runwayDamage||0,0,1.2))*(1-0.45*(a.suppression||0))*(1-0.22*overload),0.05,1.08);
    }
    for(const p of (infra.ports||[])){
      const cycle=(1/Math.max(0.9,p.turnH||5.0));
      p.berthLoad=Math.max(0,(p.berthLoad||0)-dt*CAMPAIGN_CLOCK.speedHoursPerSec*cycle*(0.80+0.40*clamp(ws.logistics.health||0.6,0.2,1.2)));
      p.repairQueue=clamp((p.repairQueue||0) + dt*(0.08*(p.shutdown||0) - 0.03*clamp(ws.logistics.health||0.6,0.1,1.2)),0,2.0);
      const overload=Math.max(0, ((p.berthLoad||0)-(p.maxBerths||2))/Math.max(1,p.maxBerths||2));
      p.operationalFactor=clamp((1-0.78*clamp(p.shutdown||0,0,1.2))*(1-0.28*overload),0.05,1.08);
    }
    for(const c of (infra.cities||[])){
      const attackPressure=clamp((c.pressure||0) + 0.24*inbound + 0.18*(1-clamp(tws.batteryKillChain||1,0,1.1)),0,1.8);
      const attackCountry=(dominant && attackPressure>0.58 && defenseGrip<0.72) ? dominant : '';
      if(attackCountry) c.captureBy=attackCountry;
      const delta=dt*(0.038*defenseGrip - 0.050*attackPressure);
      c.controlScore=clamp((c.controlScore==null?0.85:c.controlScore)+delta,-1.25,1.25);
      c.contestedH=Math.max(0,(c.contestedH||0)+dt*CAMPAIGN_CLOCK.speedHoursPerSec*(attackPressure>0.42?1:-0.6));
      if(c.captureBy && c.controlScore<-0.68 && attackPressure>0.72){ c.controller=c.captureBy; c.status='captured'; }
      else if(c.controlScore>0.12){ c.controller=country; c.status=(c.pressure||0)>0.48?'under strike':'contested'; }
    }
    ops.lostCityShare=meanWeighted(infra.cities||[], c => (c.controller && c.controller!==country)?1:0);
    ops.repairLoad=0.5*safeMean((infra.airbases||[]).map(a=>a.repairQueue||0)) + 0.5*safeMean((infra.ports||[]).map(p=>p.repairQueue||0));
  }
}
function opsFactor(country, domain){
  const ops=ensureOpsV26(country); const infra=ensureInfraWarState(country); if(!ops || !infra) return 1;
  const lost=clamp(ops.lostCityShare||0,0,1);
  const airOps=safeMean((infra.airbases||[]).map(a=>clamp(a.operationalFactor==null?1:a.operationalFactor,0,1.1)));
  const seaOps=safeMean((infra.ports||[]).map(p=>clamp(p.operationalFactor==null?1:p.operationalFactor,0,1.1)));
  const groundHold=1-0.68*lost;
  if(domain==='air' || domain==='airDefense') return clamp(0.55*airOps + 0.45*groundHold,0.06,1.08);
  if(domain==='sea') return clamp(0.65*seaOps + 0.35*(1-0.55*lost),0.06,1.08);
  if(domain==='land') return clamp(groundHold*(1-0.20*clamp((ops.repairLoad||0)/2,0,1)),0.06,1.08);
  if(domain==='logistics') return clamp(0.44*airOps + 0.44*seaOps + 0.22*groundHold,0.06,1.08);
  return 1;
}
const _domainProfile_v26_prev=domainProfile;
domainProfile=function(country){
  const out=_domainProfile_v26_prev(country);
  const airF=opsFactor(country,'air'), seaF=opsFactor(country,'sea'), landF=opsFactor(country,'land'), logF=opsFactor(country,'logistics');
  out.air=clamp(out.air*airF,0.01,1.3);
  out.sea=clamp(out.sea*seaF,0.01,1.3);
  out.land=clamp(out.land*landF,0.01,1.3);
  out.logistics=clamp(out.logistics*logF,0.01,1.3);
  out.integrated=clamp(out.integrated*(0.35+0.18*airF+0.17*seaF+0.17*landF+0.13*logF),0.02,1.35);
  out.ops={air:airF, sea:seaF, land:landF, logistics:logF, lostCityShare:(OPS_V26[country]&&OPS_V26[country].lostCityShare)||0};
  return out;
};
const _launchProjectedAttack_v26_prev=launchProjectedAttack;
launchProjectedAttack=function(opts){
  const before=projectiles.length;
  const attack=_launchProjectedAttack_v26_prev(opts);
  const born=projectiles.slice(before);
  for(const p of born){
    if(!p || p.kind==='decoy' || p.kind==='rv') continue;
    const country=p.attackerCountry || inferCountryFromPlaceName(p.fromName||'') || '';
    const kind=p.domainKind || classifyAttackDomain(p);
    const alloc=(kind==='sea') ? allocatePortDeparture(country,p.fromLL||[0,0]) : (kind==='air' ? allocateSortie(country,p.fromLL||[0,0]) : null);
    if(alloc){
      p.systemReliability=clamp((p.systemReliability||0.9)*alloc.rel,0.03,0.995);
      p.sensorQuality=clamp((p.sensorQuality||0.65)*(0.70+0.30*alloc.rel),0.06,0.995);
      p.cmdMach=Math.max(0.8,(p.cmdMach||4)*(alloc.speedMul||1));
      p.launchNodeName=(alloc.node && alloc.node.name) || '';
      p.opsOverload=alloc.overload||0;
      if((alloc.overload||0)>0.45) addLog('OPS QUEUE: '+escapeHtml(country)+' launch flow at '+escapeHtml(p.launchNodeName)+' is congested. Reliability reduced.', 'warn-entry');
    }
  }
  return attack;
};
const _fireProjectile_v26_prev=fireProjectile;
fireProjectile=async function(){
  const before=projectiles.length;
  await _fireProjectile_v26_prev();
  const born=projectiles.slice(before);
  for(const p of born){
    if(!p || p.kind==='decoy' || p.kind==='rv') continue;
    const country=p.attackerCountry || inferCountryFromPlaceName(p.fromName||'') || '';
    const kind=p.domainKind || classifyAttackDomain(p);
    const alloc=(kind==='sea') ? allocatePortDeparture(country,p.fromLL||[0,0]) : ((kind==='air' || p.mode==='cruise') ? allocateSortie(country,p.fromLL||[0,0]) : null);
    if(alloc){
      p.systemReliability=clamp((p.systemReliability||0.9)*alloc.rel,0.03,0.995);
      p.sensorQuality=clamp((p.sensorQuality||0.65)*(0.72+0.28*alloc.rel),0.06,0.995);
      p.cmdMach=Math.max(0.8,(p.cmdMach||4)*(alloc.speedMul||1));
      p.launchNodeName=(alloc.node && alloc.node.name) || '';
      p.opsOverload=alloc.overload||0;
    }
  }
};
$('btnFire').onclick=()=>fireProjectile();
const _chooseCounterstrikeOrigin_v26_prev=chooseCounterstrikeOrigin;
chooseCounterstrikeOrigin=function(country, enemyCountry, incomingAttack){
  const base=_chooseCounterstrikeOrigin_v26_prev(country, enemyCountry, incomingAttack);
  const infra=ensureInfraWarState(country); if(!infra || !(infra.cities||[]).length) return base;
  const enemyAim=(incomingAttack && incomingAttack.fromLL) ? incomingAttack.fromLL : null;
  let best=null,bestScore=-1e9;
  for(const city of infra.cities){
    const own=(city.controller||country)===country ? 1 : 0;
    const stress=clamp(city.pressure||0,0,1.2);
    const ctrl=clamp((city.controlScore==null?0.6:city.controlScore),-1.2,1.2);
    const range=enemyAim ? gcDistMeters([city.lat,city.lon], enemyAim)/1000 : 0;
    const score=1.2*own + 0.28*(city.importance||1) + 0.00004*range - 0.85*stress + 0.35*ctrl;
    if(score>bestScore){ bestScore=score; best=city; }
  }
  return best || base;
};
function drawOwnershipOverlay(country){
  const infra=ensureInfraWarState(country); if(!infra) return;
  for(const c of (infra.cities||[])){
    const pr=projectLL(c.lat,c.lon,1.016); if(!pr.visible) continue;
    const own=(c.controller||country)===country;
    const q=clamp(Math.abs(c.controlScore==null?0.6:c.controlScore),0,1.2);
    ctx.save();
    ctx.fillStyle=own ? 'rgba(100,255,170,'+(0.15+0.55*q)+')' : 'rgba(255,88,88,'+(0.16+0.60*q)+')';
    ctx.beginPath(); ctx.arc(pr.x, pr.y, 3.2 + 4.2*q, 0, Math.PI*2); ctx.fill();
    if(!own){ ctx.strokeStyle='rgba(255,210,120,'+(0.22+0.55*q)+')'; ctx.lineWidth=1.2; ctx.setLineDash([2,3]); ctx.beginPath(); ctx.arc(pr.x,pr.y,8+8*q,0,Math.PI*2); ctx.stroke(); }
    ctx.restore();
  }
}
const _drawCampaignTheaterOverlay_v26_prev=drawCampaignTheaterOverlay;
drawCampaignTheaterOverlay=function(){
  _drawCampaignTheaterOverlay_v26_prev();
  const active=getActiveCountriesDetailed();
  for(const item of active){ drawOwnershipOverlay(item.country); }
};
const _loop_v26_prev=loop;
loop=function(){
  const now=performance.now();
  const dt=Math.max(0.016, Math.min(0.25, (now-OPS_V26_LAST)/1000));
  OPS_V26_LAST=now;
  updateOpsV26(dt);
  _loop_v26_prev();
};
const _updateHud_v26_prev=updateHud;
updateHud=function(){
  _updateHud_v26_prev();
  const bal=currentDomainBalance();
  if(!bal) return;
  const aOps=ensureOpsV26(bal.atk.country), dOps=ensureOpsV26(bal.def.country);
  const aInf=ensureInfraWarState(bal.atk.country), dInf=ensureInfraWarState(bal.def.country);
  const aAir=safeMean((aInf.airbases||[]).map(x=>x.sortieQueue||0)).toFixed(1), dAir=safeMean((dInf.airbases||[]).map(x=>x.sortieQueue||0)).toFixed(1);
  const aSea=safeMean((aInf.ports||[]).map(x=>x.berthLoad||0)).toFixed(1), dSea=safeMean((dInf.ports||[]).map(x=>x.berthLoad||0)).toFixed(1);
  hud.innerHTML += '<br>Ops queues <span class="val">'+escapeHtml(bal.atk.country)+' air '+aAir+' • sea '+aSea+'</span> • <span class="val">'+escapeHtml(bal.def.country)+' air '+dAir+' • sea '+dSea+'</span>';
  hud.innerHTML += '<br>Sector ownership <span class="val">'+escapeHtml(bal.atk.country)+' lost '+Math.round(100*((aOps&&aOps.lostCityShare)||0))+'%</span> • <span class="val">'+escapeHtml(bal.def.country)+' lost '+Math.round(100*((dOps&&dOps.lostCityShare)||0))+'%</span>';
};
const _updateEngagementPanel_v26_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v26_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const aOps=ensureOpsV26(bal.atk.country), dOps=ensureOpsV26(bal.def.country);
  const block='<div style="margin-top:6px;border-top:1px solid rgba(130,170,210,0.18);padding-top:6px">'+
    '<div style="color:#9fd8ff;font-size:11px;margin-bottom:4px">Airport / Port Ops & Ownership</div>'+
    '<div style="display:flex;gap:8px;font-size:11px"><div style="flex:1"><span style="color:#ffd48a">'+escapeHtml(bal.atk.country)+'</span><br>sorties '+Math.round((aOps&&aOps.sortiesGenerated)||0)+' • naval dep '+Math.round((aOps&&aOps.navalDepartures)||0)+'<br>lost city share '+Math.round(100*((aOps&&aOps.lostCityShare)||0))+'% • repair '+(((aOps&&aOps.repairLoad)||0)).toFixed(2)+'</div>'+
    '<div style="flex:1"><span style="color:#9ef4ff">'+escapeHtml(bal.def.country)+'</span><br>sorties '+Math.round((dOps&&dOps.sortiesGenerated)||0)+' • naval dep '+Math.round((dOps&&dOps.navalDepartures)||0)+'<br>lost city share '+Math.round(100*((dOps&&dOps.lostCityShare)||0))+'% • repair '+(((dOps&&dOps.repairLoad)||0)).toFixed(2)+'</div></div></div>';
  engagementSummary.innerHTML += block;
};
$('btnClear').addEventListener('click', ()=>{ for(const k of Object.keys(OPS_V26)) delete OPS_V26[k]; });
})();
</script>
'''

USER_AGENT = os.environ.get("GLOBE_STRIKE_USER_AGENT") or (
    "GlobeStrikeGeocoder/2.0" + (f" ({os.environ.get('GLOBE_STRIKE_CONTACT_EMAIL')})" if os.environ.get("GLOBE_STRIKE_CONTACT_EMAIL") else " (local-app)")
)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
LATLON_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def find_open_port(start=8080, end=8095):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start

PORT = find_open_port()

BUILTIN_GEOCODE = {
    "usa": {"name": "United States", "lat": 39.8, "lon": -98.6, "provider": "builtin", "kind": "country"},
    "united states": {"name": "United States", "lat": 39.8, "lon": -98.6, "provider": "builtin", "kind": "country"},
    "uk": {"name": "United Kingdom", "lat": 55.4, "lon": -3.4, "provider": "builtin", "kind": "country"},
    "uae": {"name": "United Arab Emirates", "lat": 23.4, "lon": 53.8, "provider": "builtin", "kind": "country"},
    "new york city": {"name": "New York City, New York, United States", "lat": 40.7128, "lon": -74.0060, "provider": "builtin", "kind": "city"},
    "nyc": {"name": "New York City, New York, United States", "lat": 40.7128, "lon": -74.0060, "provider": "builtin", "kind": "city"},
    "london": {"name": "London, England, United Kingdom", "lat": 51.5074, "lon": -0.1278, "provider": "builtin", "kind": "city"},
    "tokyo": {"name": "Tokyo, Japan", "lat": 35.6762, "lon": 139.6503, "provider": "builtin", "kind": "city"},
    "paris": {"name": "Paris, France", "lat": 48.8566, "lon": 2.3522, "provider": "builtin", "kind": "city"},
    "accra": {"name": "Accra, Ghana", "lat": 5.6037, "lon": -0.1870, "provider": "builtin", "kind": "city"},
    "coram": {"name": "Coram, New York, United States", "lat": 40.8687, "lon": -72.9996, "provider": "builtin", "kind": "town"},
    "washington, d.c.": {"name": "Washington, D.C., United States", "lat": 38.9072, "lon": -77.0369, "provider": "builtin", "kind": "city"},
    "washington": {"name": "Washington, D.C., United States", "lat": 38.9072, "lon": -77.0369, "provider": "builtin", "kind": "city"},
    "moscow": {"name": "Moscow, Russia", "lat": 55.7558, "lon": 37.6173, "provider": "builtin", "kind": "city"},
    "beijing": {"name": "Beijing, China", "lat": 39.9042, "lon": 116.4074, "provider": "builtin", "kind": "city"},
    "pyongyang": {"name": "Pyongyang, North Korea", "lat": 39.0392, "lon": 125.7625, "provider": "builtin", "kind": "city"},
    "tehran": {"name": "Tehran, Iran", "lat": 35.6892, "lon": 51.389, "provider": "builtin", "kind": "city"},
    "tel aviv": {"name": "Tel Aviv, Israel", "lat": 32.0853, "lon": 34.7818, "provider": "builtin", "kind": "city"},
    "sydney": {"name": "Sydney, Australia", "lat": -33.8688, "lon": 151.2093, "provider": "builtin", "kind": "city"},
    "mumbai": {"name": "Mumbai, India", "lat": 19.076, "lon": 72.8777, "provider": "builtin", "kind": "city"},
    "seoul": {"name": "Seoul, South Korea", "lat": 37.5665, "lon": 126.978, "provider": "builtin", "kind": "city"},
    "patchogue": {"name": "Patchogue, New York, United States", "lat": 40.7657, "lon": -73.0151, "provider": "builtin", "kind": "town"},
}


def _norm_key(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _country_latlng(country_name: str):
    if CountryInfo is None:
        return None, None, None
    try:
        info = CountryInfo(country_name).info()
    except Exception:
        return None, None, None
    latlng = info.get("latlng") or []
    if not isinstance(latlng, (list, tuple)) or len(latlng) < 2:
        return None, None, info
    try:
        return float(latlng[0]), float(latlng[1]), info
    except Exception:
        return None, None, info


def build_place_seed():
    local = {}
    seed = []
    option_values = []
    seen_seed = set()

    def add_seed(name: str, kind: str, provider: str, priority=None, lat=None, lon=None):
        nm = " ".join((name or "").split()).strip()
        if not nm:
            return
        key = _norm_key(nm)
        if key in seen_seed:
            if lat is not None and lon is not None:
                for item in seed:
                    if _norm_key(item.get("name","")) == key and "lat" not in item:
                        item["lat"] = round(float(lat),6)
                        item["lon"] = round(float(lon),6)
                        break
            return
        seen_seed.add(key)
        item = {"name": nm, "kind": kind, "provider": provider}
        if lat is not None and lon is not None:
            try:
                item["lat"] = round(float(lat),6)
                item["lon"] = round(float(lon),6)
            except: pass
        if priority is not None:
            item["priority"] = priority
        seed.append(item)
        option_values.append(nm)

    def add_local(name: str, lat, lon, kind: str, provider: str, aliases=None, priority=None):
        try:
            lat = float(lat)
            lon = float(lon)
        except Exception:
            return
        nm = " ".join((name or "").split()).strip()
        payload = {"name": nm, "lat": lat, "lon": lon, "provider": provider, "kind": kind}
        local[_norm_key(nm)] = payload
        add_seed(nm, kind, provider, priority=priority, lat=lat, lon=lon)
        for alias in aliases or []:
            ak = _norm_key(alias)
            if ak:
                local[ak] = payload

    if pycountry is not None:
        for country in pycountry.countries:
            primary = getattr(country, "name", None)
            if not primary:
                continue
            lat, lon, info = _country_latlng(primary)
            aliases = []
            for attr in ("official_name", "common_name", "alpha_2", "alpha_3"):
                val = getattr(country, attr, None)
                if val and val != primary:
                    aliases.append(val)
            add_local(primary, lat, lon, "country", "countryinfo", aliases=aliases, priority=10)
            if info:
                capital = info.get("capital")
                cap_latlng = info.get("capital_latlng") or []
                if capital and isinstance(cap_latlng, (list, tuple)) and len(cap_latlng) >= 2:
                    add_local(f"{capital}, {primary}", cap_latlng[0], cap_latlng[1], "capital city", "countryinfo", priority=20)
                    add_local(capital, cap_latlng[0], cap_latlng[1], "capital city", "countryinfo", priority=20)

    curated = {
        "usa": ("United States", 39.8, -98.6, "country"),
        "uk": ("United Kingdom", 55.4, -3.4, "country"),
        "uae": ("United Arab Emirates", 23.4, 53.8, "country"),
        "nyc": ("New York City, New York, United States", 40.7128, -74.0060, "city"),
        "coram": ("Coram, New York, United States", 40.8687, -72.9996, "town"),
        "patchogue": ("Patchogue, New York, United States", 40.7657, -73.0151, "town"),
        "kings park": ("Kings Park, New York, United States", 40.8862, -73.2437, "town"),
        "accra": ("Accra, Ghana", 5.6037, -0.1870, "city"),
        "greater accra": ("Greater Accra Region, Ghana", 5.8143, 0.0747, "region"),
        "tokyo": ("Tokyo, Japan", 35.6762, 139.6503, "city"),
        "london": ("London, England, United Kingdom", 51.5074, -0.1278, "city"),
        "paris": ("Paris, France", 48.8566, 2.3522, "city"),
    }
    for alias, (name, lat, lon, kind) in curated.items():
        add_local(name, lat, lon, kind, "builtin", aliases=[alias], priority=1)

    for alias, item in BUILTIN_GEOCODE.items():
        add_local(
            item.get("name", alias),
            item.get("lat"),
            item.get("lon"),
            item.get("kind", "place"),
            item.get("provider", "builtin"),
            aliases=[alias],
            priority=5,
        )

    if pycountry is not None:
        for sub in sorted(pycountry.subdivisions, key=lambda s: (getattr(s, "country_code", ""), s.name)):
            label = sub.name
            try:
                country = pycountry.countries.get(alpha_2=getattr(sub, "country_code", "")) if getattr(sub, "country_code", None) else None
                country_name = country.name if country else None
            except Exception:
                country_name = None
            add_seed(f"{label}, {country_name}" if country_name else label, "region", "pycountry")
            add_seed(label, "region", "pycountry")

    popular = [
        "United States", "Japan", "Ghana", "United Kingdom", "New York City, New York, United States",
        "Coram, New York, United States", "Patchogue, New York, United States", "Accra, Ghana",
        "Tokyo, Japan", "London, England, United Kingdom", "Paris, France", "Greater Accra Region, Ghana",
    ]
    for idx, name in enumerate(popular, start=1):
        for item in seed:
            if _norm_key(item["name"]) == _norm_key(name):
                item["priority"] = min(item.get("priority", 999), idx)
                break

    return local, seed, list(dict.fromkeys(option_values))




EXTRA_V27_JS = r'''
<script>
(function(){
var NODE_BIND = window.NODE_BIND || (window.NODE_BIND = {});
function activeCountrySet(){
  const s=new Set();
  for(const p of projectiles||[]){
    if(!p || !p.alive) continue;
    if(p.attackerCountry) s.add(p.attackerCountry);
    if(p.defenderCountry) s.add(p.defenderCountry);
  }
  return s;
}
function nodeOpFactor(node){
  if(!node) return 0.1;
  const runway = 1 - clamp((node.runwayDamage||0),0,0.95)*0.7;
  const port = 1 - clamp((node.shutdown||0),0,0.95)*0.7;
  const cap = 1 - clamp((node.capturePressure||0),0,1)*0.55;
  const supp = 1 - clamp((node.suppression||0),0,1)*0.45;
  const q = 1 - clamp(((node.sortieQueue||node.berthLoad||0) / Math.max(1,(node.maxQueue||node.maxBerths||4))),0,1)*0.35;
  const dmg = 1 - clamp((node.damage||0),0,0.95)*0.5;
  return clamp(runway*port*cap*supp*q*dmg,0.06,1.15);
}
function initNodeAssets(country){
  if(!country) return null;
  if(NODE_BIND[country]) return NODE_BIND[country];
  const infra=ensureInfraWarState(country); if(!infra) return null;
  const prof=(typeof _domainProfile_v25_prev==='function') ? _domainProfile_v25_prev(country) : domainProfile(country);
  const theater=(typeof ensureTheaterWarState==='function') ? ensureTheaterWarState(country) : null;
  const airTotal=Math.max(4, Math.round(((theater&&theater.squadrons&&theater.squadrons.ready)||0) || (8 + prof.air*36)));
  const seaTotal=Math.max(0, Math.round(((theater&&theater.fleets&&theater.fleets.ready)||0) || (2 + prof.sea*18)));
  const landTotal=Math.max(6, Math.round(((theater&&theater.brigades&&theater.brigades.ready)||0) || (10 + prof.land*48)));
  const adTotal=Math.max(4, Math.round(((theater&&theater.batteries&&theater.batteries.ready)||0) || (8 + prof.air*28)));
  const state={country, airbases:[], ports:[], cities:[], sectors:[], generatedAt:performance.now()};
  const alloc=(arr,total,field)=>{
    arr=arr||[];
    const weights=arr.map(n=>Math.max(0.25, +((n&&n.importance)||1) * (n.capital?1.45:1) * nodeOpFactor(n)));
    let sum=weights.reduce((a,b)=>a+b,0) || 1;
    let rem=total;
    for(let i=0;i<arr.length;i++){
      const n=arr[i];
      n[field]=Math.max(0, Math.round(total * weights[i]/sum));
      rem -= n[field];
    }
    let j=0;
    while(rem>0 && arr.length){ arr[j%arr.length][field]++; rem--; j++; }
    return arr;
  };
  alloc(infra.airbases, airTotal, 'fighters').forEach(n=>{ n.nodeType='airbase'; n.operationalFactor=nodeOpFactor(n); state.airbases.push(n); });
  alloc(infra.ports, seaTotal, 'ships').forEach(n=>{ n.nodeType='port'; n.operationalFactor=nodeOpFactor(n); state.ports.push(n); });
  alloc(infra.cities, landTotal, 'brigades').forEach(n=>{ n.nodeType='city'; n.operationalFactor=nodeOpFactor(n); state.cities.push(n); });
  const secArr=(infra.sectors&&infra.sectors.length)?infra.sectors:infra.cities;
  alloc(secArr, adTotal, 'batteries').forEach(n=>{ n.nodeType=n.nodeType||'sector'; n.operationalFactor=nodeOpFactor(n); if(!state.sectors.includes(n)) state.sectors.push(n); });
  NODE_BIND[country]=state;
  return state;
}
function refreshNodeBinding(country){
  const st=initNodeAssets(country); if(!st) return null;
  for(const grp of ['airbases','ports','cities','sectors']){
    for(const n of st[grp]){
      n.operationalFactor=nodeOpFactor(n);
      if(n.fighters!=null) n.availableFighters=Math.max(0, Math.round(n.fighters * n.operationalFactor));
      if(n.ships!=null) n.availableShips=Math.max(0, Math.round(n.ships * n.operationalFactor));
      if(n.brigades!=null) n.availableBrigades=Math.max(0, Math.round(n.brigades * n.operationalFactor));
      if(n.batteries!=null) n.availableBatteries=Math.max(0, Math.round(n.batteries * n.operationalFactor));
    }
  }
  return st;
}
function bestOriginNode(country, kind, targetLL){
  const st=refreshNodeBinding(country); if(!st) return null;
  const arr = kind==='air' ? st.airbases : kind==='sea' ? st.ports : st.cities;
  if(!arr || !arr.length) return null;
  let best=null, bestScore=-1e9;
  for(const n of arr){
    const avail = kind==='air' ? (n.availableFighters||0) : kind==='sea' ? (n.availableShips||0) : (n.availableBrigades||0);
    const dist = targetLL && n.lat!=null ? gcDistMiles([n.lat,n.lon], Array.isArray(targetLL)?targetLL:[targetLL.lat,targetLL.lon]) : 0;
    const prox = 1 - clamp(dist/7000,0,1.1);
    const score = 1.3*avail + 18*(n.operationalFactor||0.2) + 5*((n.importance)||1) + 8*prox;
    if(score>bestScore){ bestScore=score; best=n; }
  }
  return best;
}
function bestDefenseNode(country, threat){
  const st=refreshNodeBinding(country); if(!st) return null;
  const arr=st.sectors&&st.sectors.length?st.sectors:(st.airbases||[]);
  let best=null,bestScore=-1e9;
  for(const n of arr){
    const avail=(n.availableBatteries||0);
    const dist = threat&&n.lat!=null ? gcDistMiles([n.lat,n.lon], threat.toLL||(threat.currentLL?[threat.currentLL[0],threat.currentLL[1]]:null)||threat.fromLL||[n.lat,n.lon]) : 0;
    const prox = 1 - clamp(dist/3500,0,1.2);
    const score = 1.8*avail + 20*(n.operationalFactor||0.2) + 6*((n.importance)||1) + 12*prox;
    if(score>bestScore){ bestScore=score; best=n; }
  }
  return best;
}
function bindLiveProjectiles(){
  for(const p of projectiles||[]){
    if(!p || !p.alive) continue;
    if(!p.originNodeBound && p.attackerCountry){
      const kind=p.domainKind || classifyAttackDomain(p);
      const node=bestOriginNode(p.attackerCountry, kind, p.toLL||p.currentLL||p.fromLL);
      if(node){
        p.originNodeBound={country:p.attackerCountry,name:node.name||node.label||kind,kind:node.nodeType||kind,lat:node.lat,lon:node.lon};
        p.originNodeName=node.name||node.label||kind;
        if(kind==='air' && node.fighters!=null && node.fighters>0) node.fighters=Math.max(0,node.fighters-1);
        if(kind==='sea' && node.ships!=null && node.ships>0) node.ships=Math.max(0,node.ships-1);
        if(kind==='land' && node.brigades!=null && node.brigades>0) node.brigades=Math.max(0,node.brigades-1);
      }
    }
  }
  for(const i of interceptors||[]){
    if(!i || !i.alive || i.defenseNodeBound || !i.target || !i.country) continue;
    const node=bestDefenseNode(i.country, i.target);
    if(node){
      i.defenseNodeBound={country:i.country,name:node.name||node.label||'Defense Sector',kind:node.nodeType||'sector',lat:node.lat,lon:node.lon};
      i.defenseNodeName=node.name||node.label||'Defense Sector';
      if(node.batteries!=null && node.batteries>0) node.batteries=Math.max(0,node.batteries-1);
    }
  }
}
function drawAssetNodeOverlay(){
  const active=Array.from(activeCountrySet());
  if(!active.length) return;
  ctx.save();
  for(const country of active){
    const st=refreshNodeBinding(country); if(!st) continue;
    const drawNodes=(arr,label,color,field,dy)=>{
      for(const n of arr.slice(0,8)){
        if(n.lat==null || n.lon==null) continue;
        const pr=projectLL(n.lat,n.lon,1.012); if(!pr.visible) continue;
        const val=(n[field]!=null)?n[field]:0; if(val<=0 && (n.operationalFactor||0)<0.12) continue;
        ctx.globalAlpha=0.82;
        ctx.strokeStyle=color; ctx.fillStyle='rgba(4,11,18,0.6)'; ctx.lineWidth=1.1;
        ctx.beginPath(); ctx.arc(pr.x,pr.y,8+Math.min(10,val*0.18),0,Math.PI*2); ctx.fill(); ctx.stroke();
        ctx.fillStyle=color; ctx.font='9px ui-monospace, monospace'; ctx.textAlign='center';
        ctx.fillText(label+Math.max(0,Math.round(val)), pr.x, pr.y+dy);
      }
    };
    drawNodes(st.airbases,'A','rgba(117,239,255,0.95)','availableFighters',-12);
    drawNodes(st.ports,'S','rgba(126,153,255,0.95)','availableShips',-12);
    drawNodes(st.cities,'L','rgba(255,194,120,0.95)','availableBrigades',-12);
    drawNodes(st.sectors,'D','rgba(255,115,115,0.92)','availableBatteries',14);
  }
  for(const p of projectiles||[]){
    if(!p || !p.alive || !p.originNodeBound) continue;
    const a=projectLL(p.originNodeBound.lat,p.originNodeBound.lon,1.01), b=project(p.rEcef().scale(1/RE_M));
    if(!a.visible || !b.visible) continue;
    ctx.strokeStyle='rgba(255,255,255,0.18)'; ctx.lineWidth=1; ctx.setLineDash([3,4]);
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); ctx.setLineDash([]);
  }
  for(const i of interceptors||[]){
    if(!i || !i.alive || !i.defenseNodeBound) continue;
    const a=projectLL(i.defenseNodeBound.lat,i.defenseNodeBound.lon,1.01), b=project(i.rEcef().scale(1/RE_M));
    if(!a.visible || !b.visible) continue;
    ctx.strokeStyle='rgba(120,240,255,0.22)'; ctx.lineWidth=1; ctx.setLineDash([2,3]);
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); ctx.setLineDash([]);
  }
  ctx.restore();
}
function nodeBindingSummary(country){
  const st=refreshNodeBinding(country); if(!st) return null;
  const sum=(arr,field)=>Math.round((arr||[]).reduce((a,n)=>a+(+(n[field]||0)),0));
  return {
    air:sum(st.airbases,'availableFighters'),
    sea:sum(st.ports,'availableShips'),
    land:sum(st.cities,'availableBrigades'),
    ad:sum(st.sectors,'availableBatteries')
  };
}
const _drawGlobe_v27_prev=drawGlobe;
drawGlobe=function(){ _drawGlobe_v27_prev(); bindLiveProjectiles(); drawAssetNodeOverlay(); };
const _loop_v27_prev=loop;
loop=function(){
  for(const c of activeCountrySet()) refreshNodeBinding(c);
  _loop_v27_prev();
};
const _launchProjectedAttack_v27_prev=launchProjectedAttack;
launchProjectedAttack=function(opts){
  const atk=_launchProjectedAttack_v27_prev(opts);
  try{
    if(atk && atk.attackerCountry){
      const kind=atk.domainKind || classifyAttackDomain(atk);
      const node=bestOriginNode(atk.attackerCountry, kind, atk.toLL||atk.fromLL);
      if(node){
        atk.originNodeBound={country:atk.attackerCountry,name:node.name||node.label||kind,kind:node.nodeType||kind,lat:node.lat,lon:node.lon};
        atk.originNodeName=node.name||node.label||kind;
      }
    }
  }catch(e){ console.warn('V27 launch bind fail', e); }
  return atk;
};
const _updateHud_v27_prev=updateHud;
updateHud=function(){
  _updateHud_v27_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const a=nodeBindingSummary(bal.atk.country), d=nodeBindingSummary(bal.def.country);
  if(a && d){
    hud.innerHTML += '<br>NODE-BOUND ASSETS <span class="val">'+escapeHtml(bal.atk.country)+' A'+a.air+' S'+a.sea+' L'+a.land+' D'+a.ad+'</span> vs <span class="val">'+escapeHtml(bal.def.country)+' A'+d.air+' S'+d.sea+' L'+d.land+' D'+d.ad+'</span>';
  }
};
const _updateEngagementPanel_v27_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v27_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const a=nodeBindingSummary(bal.atk.country), d=nodeBindingSummary(bal.def.country);
  if(!(a&&d)) return;
  const bar=(label,av,dv,color)=>'<div style="display:flex;align-items:center;gap:6px;margin:2px 0"><span style="width:62px;color:#9fb5c9">'+label+'</span><div style="flex:1;height:8px;background:#091321;border:1px solid #223246;border-radius:999px;overflow:hidden"><div style="height:100%;width:'+Math.round(100*clamp(av/Math.max(1,av+dv),0,1))+'%;background:'+color+'"></div></div><span style="width:86px;text-align:right;color:#d9e8f7">'+Math.round(av)+' / '+Math.round(dv)+'</span></div>';
  engagementSummary.innerHTML += '<br><div style="color:#9fd8ff;font-size:11px;margin-bottom:4px">Asset-to-Node Binding</div>'+
    bar('Air nodes',a.air,d.air,'linear-gradient(90deg,#4fe8ff,#8ff8ff)')+
    bar('Sea nodes',a.sea,d.sea,'linear-gradient(90deg,#6f8dff,#9eb2ff)')+
    bar('Land nodes',a.land,d.land,'linear-gradient(90deg,#ffb66e,#ffd49c)')+
    bar('AD nodes',a.ad,d.ad,'linear-gradient(90deg,#ff6b6b,#ffaaaa)');
};
const _btnClear_v27_prev=$('btnClear').onclick;
$('btnClear').onclick=()=>{ for(const k in NODE_BIND) delete NODE_BIND[k]; _btnClear_v27_prev(); };
addLog('V27 NODE-BOUND OPERATIONS ONLINE: assets now bind to airbases, ports, cities, and defense sectors.', 'good-entry');
})();
</script>
'''



EXTRA_V28_JS = r'''
<script>
(function(){
const NODE_DAMAGE_V28={};
function ensureNodeDamageBag(country){
  if(!country) return null;
  if(!NODE_DAMAGE_V28[country]) NODE_DAMAGE_V28[country]={country,nodeLosses:0,assetKills:{air:0,sea:0,land:0,ad:0},destroyedNodes:0,lastImpact:0};
  return NODE_DAMAGE_V28[country];
}
function nodeArrayByType(st, type){
  if(!st) return [];
  if(type==='air') return st.airbases||[];
  if(type==='sea') return st.ports||[];
  if(type==='land') return st.cities||[];
  if(type==='ad') return st.sectors||[];
  return [];
}
function nodeAssetField(type){ return type==='air' ? 'fighters' : type==='sea' ? 'ships' : type==='land' ? 'brigades' : 'batteries'; }
function nodeAvailField(type){ return type==='air' ? 'availableFighters' : type==='sea' ? 'availableShips' : type==='land' ? 'availableBrigades' : 'availableBatteries'; }
function nearestBoundNode(country, type, ll){
  const st=refreshNodeBinding(country); if(!st) return null;
  const arr=nodeArrayByType(st, type); if(!arr.length) return null;
  let best=null, bestScore=-1e18;
  for(const n of arr){
    const d=ll ? gcDistMeters(ll,[n.lat,n.lon]) : 0;
    const score = -d + 150000*(n.importance||1) + 100000*(n.operationalFactor||0.2);
    if(score>bestScore){ bestScore=score; best=n; }
  }
  return best;
}
function collapseNode(node, type, severity){
  if(!node) return 0;
  const field=nodeAssetField(type), avail=nodeAvailField(type);
  const base=Math.max(0, +(node[field]||0));
  const extra=clamp(severity||0,0,1.4);
  const frac = type==='air' ? (0.18 + 0.62*clamp(node.runwayDamage||0,0,1.2) + 0.18*extra)
    : type==='sea' ? (0.16 + 0.66*clamp(node.shutdown||0,0,1.2) + 0.18*extra)
    : type==='land' ? (0.10 + 0.54*clamp(node.pressure||0,0,1.4) + 0.20*Math.max(0,-(node.controlScore||0)))
    : (0.14 + 0.58*clamp(node.damage||0,0,1.2) + 0.24*extra);
  let loss=Math.round(base*clamp(frac,0.05,0.88));
  if(loss<1 && base>0 && extra>0.35) loss=1;
  node[field]=Math.max(0, base-loss);
  if(node[avail]!=null) node[avail]=Math.min(node[avail], node[field]);
  node.destroyed = base>0 && node[field]===0;
  node.destroyLevel = clamp((node.destroyLevel||0) + frac*0.6, 0, 1.4);
  return loss;
}
function applyNodeToNodeDamage(country, ll, severity, domainKind, attackerCountry){
  if(!country) return;
  const st=refreshNodeBinding(country); if(!st) return;
  const bag=ensureNodeDamageBag(country);
  const infra=ensureInfraWarState(country);
  const sev=clamp(severity||0,0.02,1.2);
  const targets=[];
  if(domainKind==='air'){
    targets.push(['air', nearestBoundNode(country,'air',ll), 1.00]);
    targets.push(['ad', nearestBoundNode(country,'ad',ll), 0.65]);
  } else if(domainKind==='sea'){
    targets.push(['sea', nearestBoundNode(country,'sea',ll), 1.00]);
    targets.push(['land', nearestBoundNode(country,'land',ll), 0.28]);
  } else if(domainKind==='land'){
    targets.push(['land', nearestBoundNode(country,'land',ll), 1.00]);
    targets.push(['ad', nearestBoundNode(country,'ad',ll), 0.45]);
    targets.push(['air', nearestBoundNode(country,'air',ll), 0.36]);
  } else {
    targets.push(['ad', nearestBoundNode(country,'ad',ll), 1.00]);
    targets.push(['air', nearestBoundNode(country,'air',ll), 0.42]);
    targets.push(['sea', nearestBoundNode(country,'sea',ll), 0.24]);
    targets.push(['land', nearestBoundNode(country,'land',ll), 0.32]);
  }
  let msg=[];
  for(const [type,node,wt] of targets){
    if(!node) continue;
    const loss=collapseNode(node, type, sev*wt);
    if(loss>0){
      bag.assetKills[type]=(bag.assetKills[type]||0)+loss;
      bag.nodeLosses += loss;
      bag.lastImpact=Date.now();
      msg.push((node.name||type)+' -'+loss+' '+type.toUpperCase());
      if(node.destroyed) bag.destroyedNodes=(bag.destroyedNodes||0)+1;
    }
  }
  if(infra){
    for(const c of (infra.cities||[])){
      if(ll && gcDistMeters(ll,[c.lat,c.lon])<180000){
        c.capturePressure=clamp((c.capturePressure||0)+0.22*sev,0,1.5);
        c.pressure=clamp((c.pressure||0)+0.10*sev,0,1.5);
        if(attackerCountry && (c.controlScore||0)<-0.55) c.captureBy=attackerCountry;
      }
    }
  }
  if(msg.length) addLog('NODE DAMAGE '+escapeHtml(country)+': '+escapeHtml(msg.slice(0,3).join(' • ')), 'warn-entry');
}
function recoverDestroyedNodes(dtSec){
  const dt=Math.max(0.02, dtSec||0.033);
  for(const country of Object.keys(NODE_BIND)){
    const st=NODE_BIND[country]; if(!st) continue;
    const ws=ensureDomainWarState(country); if(!ws) continue;
    const logF=clamp(logisticsFactor(ws),0.08,1.2), c2=clamp(ws.c2.health||0.6,0.08,1.2);
    for(const [type,arr] of [['air',st.airbases||[]],['sea',st.ports||[]],['land',st.cities||[]],['ad',st.sectors||[]]]){
      const field=nodeAssetField(type);
      for(const node of arr){
        if(node.baseline==null) node.baseline=node[field]||0;
        if(node.baseline < (node[field]||0)) node.baseline=node[field]||0;
        const base=Math.max(node.baseline||0, node[field]||0);
        const room=base-(node[field]||0);
        if(room<=0) continue;
        const infraPenalty=1 - 0.55*clamp(node.runwayDamage||node.shutdown||node.damage||0,0,1.2);
        const ctrlBonus=(type==='land') ? (0.55+0.45*clamp((node.controlScore||0.6),0,1.1)) : 1;
        const recRate=(type==='air'?0.012:type==='sea'?0.008:type==='land'?0.016:0.010)*CAMPAIGN_CLOCK.speedHoursPerSec*dt*logF*c2*infraPenalty*ctrlBonus;
        const add=Math.min(room, recRate>0.75?Math.floor(recRate):0);
        if(add>0) node[field]=(node[field]||0)+add;
      }
    }
  }
}
function drawDestroyedNodeOverlay(){
  ctx.save();
  for(const country of Object.keys(NODE_BIND)){
    const st=NODE_BIND[country]; if(!st) continue;
    const map={airbases:'air',ports:'sea',cities:'land',sectors:'ad'};
    for(const grp of ['airbases','ports','cities','sectors']){
      for(const n of st[grp]||[]){
        const type=map[grp];
        const destroyed = n.destroyed || (n.destroyLevel||0)>0.75 || ((n[nodeAssetField(type)]||0)===0 && (n.baseline||0)>0);
        if(!destroyed) continue;
        const pr=projectLL(n.lat,n.lon,1.014); if(!pr.visible) continue;
        const q=clamp(n.destroyLevel||0.8,0.2,1.2);
        ctx.strokeStyle='rgba(255,92,92,'+(0.35+0.45*q)+')'; ctx.lineWidth=1.4; ctx.setLineDash([3,3]);
        ctx.beginPath(); ctx.arc(pr.x,pr.y,10+8*q,0,Math.PI*2); ctx.stroke();
        ctx.setLineDash([]); ctx.beginPath(); ctx.moveTo(pr.x-6,pr.y-6); ctx.lineTo(pr.x+6,pr.y+6); ctx.moveTo(pr.x+6,pr.y-6); ctx.lineTo(pr.x-6,pr.y+6); ctx.stroke();
      }
    }
  }
  ctx.restore();
}
const _registerAttackOutcome_v28_prev=registerAttackOutcome;
registerAttackOutcome=function(p){
  _registerAttackOutcome_v28_prev(p);
  try{
    if(!p || p.intercepted || !p.defenderCountry) return;
    const ll = p.impactPosU ? v2ll(p.impactPosU) : (p.getLatLon ? p.getLatLon() : p.toLL || null);
    const sev = clamp((p.mode==='ballistic'?0.42:(p.mode==='guided'?0.30:0.22)) + 0.18*Math.min(1,(p.cmdMach||0)/20) + 0.10*(p.evasiveness||p.evasion||0),0.08,1.15);
    applyNodeToNodeDamage(p.defenderCountry, ll, sev, p.domainKind || classifyAttackDomain(p), p.attackerCountry||'');
  }catch(e){ console.warn('V28 attack outcome node transfer failed', e); }
};
const _registerInterceptorOutcome_v28_prev=registerInterceptorOutcome;
registerInterceptorOutcome=function(i){
  _registerInterceptorOutcome_v28_prev(i);
  try{
    if(!i || !i.defenderCountry || !i.defenseNodeName) return;
    const st=refreshNodeBinding(i.defenderCountry); if(!st) return;
    const node=(st.sectors||[]).find(n => (n.name||'')===i.defenseNodeName) || nearestBoundNode(i.defenderCountry,'ad', i.target&&i.target.toLL ? i.target.toLL : null);
    if(!node) return;
    node.shotStress=clamp((node.shotStress||0) + (i.hit?0.04:0.02),0,1.4);
    node.damage=clamp((node.damage||0) + (i.failureMode==='launch failure'?0.05:0.015),0,1.2);
    if(i.hit && node.batteries!=null && node.batteries===0 && (node.baseline||0)>0){ node.destroyed=true; }
  }catch(e){ console.warn('V28 interceptor outcome node transfer failed', e); }
};
const _loop_v28_prev=loop;
loop=function(){
  const now=performance.now();
  const dt=Math.max(0.016, Math.min(0.25, (now-(window.__V28_LAST__||now))/1000));
  window.__V28_LAST__=now;
  recoverDestroyedNodes(dt);
  _loop_v28_prev();
};
const _drawGlobe_v28_prev=drawGlobe;
drawGlobe=function(){ _drawGlobe_v28_prev(); drawDestroyedNodeOverlay(); };
const _updateHud_v28_prev=updateHud;
updateHud=function(){
  _updateHud_v28_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const a=ensureNodeDamageBag(bal.atk.country), d=ensureNodeDamageBag(bal.def.country);
  hud.innerHTML += '<br>Node attrition <span class="val">'+escapeHtml(bal.atk.country)+' lost A'+Math.round((a&&a.assetKills.air)||0)+' S'+Math.round((a&&a.assetKills.sea)||0)+' L'+Math.round((a&&a.assetKills.land)||0)+' D'+Math.round((a&&a.assetKills.ad)||0)+'</span> • <span class="val">'+escapeHtml(bal.def.country)+' lost A'+Math.round((d&&d.assetKills.air)||0)+' S'+Math.round((d&&d.assetKills.sea)||0)+' L'+Math.round((d&&d.assetKills.land)||0)+' D'+Math.round((d&&d.assetKills.ad)||0)+'</span>';
};
const _updateEngagementPanel_v28_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v28_prev();
  const bal=currentDomainBalance(); if(!bal) return;
  const a=ensureNodeDamageBag(bal.atk.country), d=ensureNodeDamageBag(bal.def.country);
  const row=(label,av,dv,color)=>'<div style="display:flex;align-items:center;gap:6px;margin:2px 0"><span style="width:70px;color:#9fb5c9">'+label+'</span><div style="flex:1;height:8px;background:#091321;border:1px solid #223246;border-radius:999px;overflow:hidden"><div style="height:100%;width:'+Math.round(100*clamp(av/Math.max(1,av+dv),0,1))+'%;background:'+color+'"></div></div><span style="width:86px;text-align:right;color:#d9e8f7">'+Math.round(av)+' / '+Math.round(dv)+'</span></div>';
  engagementSummary.innerHTML += '<br><div style="color:#ffb0b0;font-size:11px;margin-bottom:4px">Node-to-Node Damage Transfer</div>'+
    row('Air lost',(a&&a.assetKills.air)||0,(d&&d.assetKills.air)||0,'linear-gradient(90deg,#66f1ff,#9ffaff)')+
    row('Sea lost',(a&&a.assetKills.sea)||0,(d&&d.assetKills.sea)||0,'linear-gradient(90deg,#7690ff,#a8bbff)')+
    row('Land lost',(a&&a.assetKills.land)||0,(d&&d.assetKills.land)||0,'linear-gradient(90deg,#ffc077,#ffe0a8)')+
    row('AD lost',(a&&a.assetKills.ad)||0,(d&&d.assetKills.ad)||0,'linear-gradient(90deg,#ff7474,#ffb4b4)');
};
const _btnClear_v28_prev=$('btnClear').onclick;
$('btnClear').onclick=()=>{ for(const k in NODE_DAMAGE_V28) delete NODE_DAMAGE_V28[k]; _btnClear_v28_prev(); };
addLog('V28 NODE-TO-NODE DAMAGE ONLINE: strikes now remove local node-bound assets and can collapse specific airbases, ports, cities, and defense sectors.', 'good-entry');
})();
</script>
'''

EXTRA_V29_JS = r'''
<script>
(()=>{
const KCHAIN_V29 = window.KCHAIN_V29 = window.KCHAIN_V29 || {};
function ensureKChain(country){
  country=country||'Unknown';
  if(!KCHAIN_V29[country]){
    const p=domainProfile(country)||{};
    const tierMul={super:1.08, strategic:1.02, advanced:0.97, regional:0.90, limited:0.82, micro:0.72}[p.tier] || 0.85;
    KCHAIN_V29[country]={
      radar: clamp((0.58+0.34*(p.air||0.4))*tierMul,0.18,1.18),
      isr: clamp((0.54+0.36*((p.integrated||0.4)))*tierMul,0.18,1.18),
      sat: clamp((0.44+0.42*((p.logistics||0.4)) + 0.14*((p.air||0.3)))*tierMul,0.12,1.18),
      comm: clamp((0.50+0.36*(p.doctrine||0.5))*tierMul,0.15,1.18),
      ewDef: clamp((0.48+0.32*(p.air||0.3)+0.18*(p.logistics||0.4))*tierMul,0.12,1.15),
      cyberStress: 0,
      blind: 0,
      history: []
    };
  }
  return KCHAIN_V29[country];
}
function kChainFactor(country){
  const k=ensureKChain(country);
  return clamp(0.24*k.radar + 0.22*k.isr + 0.18*k.sat + 0.22*k.comm + 0.14*k.ewDef - 0.28*k.cyberStress - 0.18*k.blind, 0.16, 1.12);
}
function drawKNode(x,y,label,val,color){
  ctx.save();
  const q=clamp(val||0,0,1.2); const rr=7+6*q;
  ctx.globalAlpha=0.15+0.28*q;
  ctx.fillStyle=color; ctx.beginPath(); ctx.arc(x,y,rr,0,Math.PI*2); ctx.fill();
  ctx.globalAlpha=0.85; ctx.lineWidth=1.2+0.6*q; ctx.strokeStyle=color; ctx.beginPath(); ctx.arc(x,y,rr,0,Math.PI*2); ctx.stroke();
  if(q<0.33){ ctx.strokeStyle='rgba(255,90,90,0.95)'; ctx.beginPath(); ctx.moveTo(x-rr*0.65,y-rr*0.65); ctx.lineTo(x+rr*0.65,y+rr*0.65); ctx.moveTo(x+rr*0.65,y-rr*0.65); ctx.lineTo(x-rr*0.65,y+rr*0.65); ctx.stroke(); }
  ctx.fillStyle='rgba(238,246,255,0.96)'; ctx.font='9px ui-monospace, monospace'; ctx.textAlign='center'; ctx.fillText(label,x,y+3);
  ctx.restore();
}
function drawKillChainOverlay(){
  const active=getActiveCountriesDetailed();
  for(const item of active){
    const country=item.country; const k=ensureKChain(country); const nodes=getCountryTheaterNodes(country).slice(0,3); if(!nodes.length) continue;
    const p0=projectLL(nodes[0].lat,nodes[0].lon,1.020); if(!p0.visible) continue;
    drawKNode(p0.x-26,p0.y-24,'R',k.radar,'rgba(125,225,255,0.92)');
    drawKNode(p0.x,p0.y-32,'I',k.isr,'rgba(149,255,185,0.92)');
    drawKNode(p0.x+26,p0.y-24,'S',k.sat,'rgba(180,165,255,0.92)');
    drawKNode(p0.x,p0.y+28,'C',k.comm,'rgba(255,210,120,0.92)');
    if((k.cyberStress||0)>0.08){
      ctx.save(); ctx.strokeStyle='rgba(255,96,170,'+(0.35+0.45*k.cyberStress)+')'; ctx.setLineDash([4,4]); ctx.lineWidth=1.2+1.6*k.cyberStress;
      ctx.beginPath(); ctx.arc(p0.x,p0.y,32+12*k.cyberStress,0,Math.PI*2); ctx.stroke(); ctx.restore();
    }
  }
}
function degradeKChain(country, threat, dt){
  const k=ensureKChain(country); const cm=(threat&&threat.countermeasureProfile)||{};
  const dom=(threat&&threat.domainKind)||'strategic';
  const ew = clamp(0.26*(cm.jammer||0)+0.22*(cm.drfm||0)+0.16*(cm.clutter||0)+0.18*(cm.stealth||0)+0.10*(cm.thermalMasking||0)+0.08*(cm.terminalWeave||0),0,1.1);
  const rate = (dt||0.03) * (0.004 + 0.010*ew + 0.005*((threat&&threat.cmdMach||6)/20));
  k.radar = clamp(k.radar - rate*(dom==='air'||dom==='strategic'?1.10:0.65),0.08,1.18);
  k.isr   = clamp(k.isr   - rate*(dom==='land'?0.72:0.92),0.08,1.18);
  k.sat   = clamp(k.sat   - rate*(0.55 + 0.65*(cm.stealth||0)),0.08,1.18);
  k.comm  = clamp(k.comm  - rate*(0.45 + 0.85*(cm.jammer||0) + 0.40*(dom==='strategic')),0.08,1.18);
  k.ewDef = clamp(k.ewDef - rate*(0.35 + 0.45*(cm.drfm||0)),0.08,1.18);
  k.cyberStress = clamp(k.cyberStress + rate*(0.9*(cm.emissionDiscipline||0.2) + 0.7*(cm.drfm||0.2) + 0.55*(dom==='strategic')),0,1.2);
  k.blind = clamp(1 - (0.33*k.radar + 0.24*k.isr + 0.18*k.sat + 0.25*k.comm), 0, 1);
}
function recoverKChain(dt){
  const d=Math.max(0.01,dt||0.03);
  for(const country of Object.keys(KCHAIN_V29)){
    const k=KCHAIN_V29[country]; const ws=ensureDomainWarState(country); const logi=(ws&&ws.logistics&&ws.logistics.health)||0.5; const c2=(ws&&ws.c2&&ws.c2.health)||0.5;
    const r=(0.0018 + 0.0032*logi + 0.0024*c2)*d;
    k.radar=clamp(k.radar+r*0.9,0.08,1.18); k.isr=clamp(k.isr+r*0.85,0.08,1.18); k.sat=clamp(k.sat+r*0.65,0.08,1.18); k.comm=clamp(k.comm+r,0.08,1.18); k.ewDef=clamp(k.ewDef+r*0.8,0.08,1.18);
    k.cyberStress=clamp(k.cyberStress-r*0.72,0,1.2); k.blind=clamp(1 - (0.33*k.radar + 0.24*k.isr + 0.18*k.sat + 0.25*k.comm), 0, 1);
    k.history.push({t:Date.now(), f:kChainFactor(country)}); if(k.history.length>80) k.history.shift();
  }
}
function updateKillChainWar(dt){
  for(const p of projectiles){ if(!p.alive || p.excludeFromMetrics) continue; degradeKChain(p.defenderCountry||inferCountryFromPlaceName(p.toName||'')||'Unknown', p, dt); }
  for(const ic of interceptors){
    if(!ic.alive || !ic.target || !ic.target.alive) continue;
    const dc=ic.target.attackerCountry||inferCountryFromPlaceName(ic.target.fromName||'')||'Unknown';
    const k=ensureKChain(dc); const seek=(ic.seekerProfile||{}); const s=(dt||0.03)*(0.0025 + 0.004*((seek.baseTrack||0.7)));
    k.radar=clamp(k.radar-s*0.24,0.08,1.18); k.isr=clamp(k.isr-s*0.20,0.08,1.18); k.comm=clamp(k.comm-s*0.18,0.08,1.18);
  }
  recoverKChain(dt);
}
const _currentDomainBalance_v29_prev=currentDomainBalance;
currentDomainBalance=function(){
  const bal=_currentDomainBalance_v29_prev(); if(!bal) return bal;
  const atkF=kChainFactor(bal.atk.country||'Unknown'); const defF=kChainFactor(bal.def.country||'Unknown');
  bal.atkKChain=atkF; bal.defKChain=defF;
  bal.attackAir=clamp(bal.attackAir*(0.86+0.28*atkF),0.02,1.8);
  bal.attackSea=clamp(bal.attackSea*(0.84+0.26*atkF),0.02,1.8);
  bal.attackLand=clamp(bal.attackLand*(0.88+0.24*atkF),0.02,1.8);
  bal.defAir=clamp(bal.defAir*(0.74+0.40*defF),0.02,1.8);
  bal.defSea=clamp(bal.defSea*(0.78+0.30*defF),0.02,1.8);
  bal.defLand=clamp(bal.defLand*(0.82+0.24*defF),0.02,1.8);
  bal.atkIntegrated=clamp(bal.atkIntegrated*(0.86+0.26*atkF),0.03,2.0);
  bal.defIntegrated=clamp(bal.defIntegrated*(0.72+0.42*defF),0.03,2.0);
  return bal;
};
const _loop_v29_prev=loop;
loop=function(){
  const now=performance.now(); const dt=Math.max(0.016, Math.min(0.25, (now-(window.__V29_LAST__||now))/1000)); window.__V29_LAST__=now;
  updateKillChainWar(dt); _loop_v29_prev();
};
const _drawGlobe_v29_prev=drawGlobe;
drawGlobe=function(){ _drawGlobe_v29_prev(); drawKillChainOverlay(); };
const _updateHud_v29_prev=updateHud;
updateHud=function(){
  _updateHud_v29_prev(); const bal=currentDomainBalance(); if(!bal) return;
  const dk=ensureKChain(bal.def.country);
  hud.innerHTML += '<br>Kill chain <span class="val">'+escapeHtml(bal.atk.country)+' '+Math.round(100*bal.atkKChain)+'%</span> • <span class="val">'+escapeHtml(bal.def.country)+' '+Math.round(100*bal.defKChain)+'%</span>'+
                   '<br>ISR/Radar/Sat <span class="val">'+escapeHtml(bal.def.country)+' R'+Math.round(100*dk.radar)+' I'+Math.round(100*dk.isr)+' S'+Math.round(100*dk.sat)+'</span> • <span class="val">Cyber '+Math.round(100*dk.cyberStress)+'%</span>';
};
const _updateEngagementPanel_v29_prev=updateEngagementPanel;
updateEngagementPanel=function(){
  _updateEngagementPanel_v29_prev(); const bal=currentDomainBalance(); if(!bal) return;
  const ak=ensureKChain(bal.atk.country), dk=ensureKChain(bal.def.country);
  const row=(label,av,dv,color)=>'<div style="display:flex;align-items:center;gap:6px;margin:2px 0"><span style="width:72px;color:#9fb5c9">'+label+'</span><div style="flex:1;height:8px;background:#091321;border:1px solid #223246;border-radius:999px;overflow:hidden"><div style="height:100%;width:'+Math.round(100*clamp(av/Math.max(1e-6,av+dv),0,1))+'%;background:'+color+'"></div></div><span style="width:92px;text-align:right;color:#d9e8f7">'+Math.round(100*av)+' / '+Math.round(100*dv)+'</span></div>';
  engagementSummary.innerHTML += '<br><div style="color:#ffa8f0;font-size:11px;margin-bottom:4px">Kill-Chain / ISR / Cyber-EW Graph</div>'+
    row('Radar',ak.radar,dk.radar,'linear-gradient(90deg,#89efff,#c4fbff)')+
    row('ISR',ak.isr,dk.isr,'linear-gradient(90deg,#8fffba,#c9ffdd)')+
    row('Satellite',ak.sat,dk.sat,'linear-gradient(90deg,#b89dff,#ddd3ff)')+
    row('Comms',ak.comm,dk.comm,'linear-gradient(90deg,#ffd08b,#ffebb9)')+
    row('EW shield',ak.ewDef,dk.ewDef,'linear-gradient(90deg,#ff8fb9,#ffc5da)')+
    '<div style="color:#89a0b7;margin-top:4px">Blindness pressure: <span style="color:#ffd48a">'+escapeHtml(bal.atk.country)+' '+Math.round(100*ak.blind)+'%</span> • <span style="color:#9ef4ff">'+escapeHtml(bal.def.country)+' '+Math.round(100*dk.blind)+'%</span>. Cyber stress: <span style="color:#ffb3d2">'+Math.round(100*ak.cyberStress)+'%</span> / <span style="color:#ffb3d2">'+Math.round(100*dk.cyberStress)+'%</span>.</div>';
};
const _btnClear_v29_prev=$('btnClear').onclick;
$('btnClear').onclick=()=>{ for(const k in KCHAIN_V29) delete KCHAIN_V29[k]; _btnClear_v29_prev(); };
addLog('V29 KILL-CHAIN GRAPH ONLINE: radar, ISR, satellite, comms, and cyber/EW nodes now degrade and recover, shaping how cleanly each country can see, decide, and fire.', 'good-entry');
})();
</script>
'''



EXTRA_V30_JS = r'''
<script>
(() => {
  const gid = (id) => document.getElementById(id);
  const FINAL_V30 = {snapshots: [], lastSnap: 0, exportSeq: 0};

  function fnum(v, d=0){
    const n = Number(v);
    return Number.isFinite(n) ? n.toFixed(d) : '0';
  }
  function pct(v){ return Math.round(100 * (Number(v) || 0)); }
  function clamp30(x,a,b){ return Math.max(a, Math.min(b, x)); }
  function softmaxPair(a,b){ const ea=Math.exp(a), eb=Math.exp(b), s=ea+eb; return s>0 ? ea/s : 0.5; }
  function randn(){ let u=0,v=0; while(!u) u=Math.random(); while(!v) v=Math.random(); return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v); }

  function ensureFinalPanel(){
    if(gid('finalOpsPanel')) return;
    const panel = document.createElement('div');
    panel.id = 'finalOpsPanel';
    panel.style.cssText = 'position:absolute;right:16px;bottom:16px;width:320px;max-height:40vh;overflow:auto;z-index:16;background:rgba(5,10,18,0.9);border:1px solid rgba(120,190,255,0.22);border-radius:14px;box-shadow:0 18px 50px rgba(0,0,0,0.35);padding:12px;color:#dbe8f6;font:12px/1.35 Arial,sans-serif;backdrop-filter: blur(7px);';
    panel.innerHTML = [
      '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px">',
      '<div style="font-size:13px;font-weight:700;letter-spacing:.04em;color:#8fe0ff">Final Command Matrix</div>',
      '<div id="v30AlertLadder" style="font-size:11px;color:#ffd48a">WATCH</div>',
      '</div>',
      '<div id="v30ForecastBars"></div>',
      '<div id="v30Dominance" style="margin-top:8px"></div>',
      '<div id="v30SnapshotMeta" style="margin-top:8px;color:#91a7bd"></div>',
      '<canvas id="v30Spark" width="292" height="86" style="margin-top:8px;width:100%;height:86px;border:1px solid rgba(120,190,255,0.14);border-radius:10px;background:rgba(7,15,26,0.95)"></canvas>',
      '<div style="display:flex;gap:8px;margin-top:10px">',
      '<button id="btnExportReport" style="flex:1;background:#0e2032;color:#d8ebff;border:1px solid #28547a;border-radius:10px;padding:8px 10px;cursor:pointer">Export report</button>',
      '<button id="btnSnapshotNow" style="flex:1;background:#122c20;color:#dcffe6;border:1px solid #2e7c58;border-radius:10px;padding:8px 10px;cursor:pointer">Snapshot now</button>',
      '</div>'
    ].join('');
    document.body.appendChild(panel);
    gid('btnExportReport').onclick = exportFinalReport;
    gid('btnSnapshotNow').onclick = () => takeSnapshot(true);
  }

  function forecastFromBalance(){
    const bal = typeof currentDomainBalance === 'function' ? currentDomainBalance() : null;
    if(!bal) return null;
    const atkK = typeof ensureKChain === 'function' ? ensureKChain(bal.atk.country) : {radar:1,isr:1,sat:1,comm:1,ewDef:1,cyberStress:0,blind:0};
    const defK = typeof ensureKChain === 'function' ? ensureKChain(bal.def.country) : {radar:1,isr:1,sat:1,comm:1,ewDef:1,cyberStress:0,blind:0};
    const atkW = bal.atkWar || (typeof ensureDomainWarState==='function' ? ensureDomainWarState(bal.atk.country) : null);
    const defW = bal.defWar || (typeof ensureDomainWarState==='function' ? ensureDomainWarState(bal.def.country) : null);
    let atkWin=0, defHold=0, exhaust=0;
    const samples = 180;
    for(let i=0;i<samples;i++){
      const atkShock = 1 + 0.06*randn();
      const defShock = 1 + 0.06*randn();
      const atkStrike = (
        1.8*(bal.attackAir||0) +
        1.35*(bal.attackSea||0) +
        1.65*(bal.attackLand||0) +
        1.25*(bal.atkIntegrated||0) +
        0.90*((atkW&&atkW.logistics&&atkW.logistics.health)||0.6) +
        0.55*(atkK.radar+atkK.isr+atkK.sat+atkK.comm)/4 -
        0.75*(atkK.blind||0) -
        0.45*(atkK.cyberStress||0)
      ) * atkShock;
      const defShield = (
        1.95*(bal.defAir||0) +
        1.20*(bal.defSea||0) +
        1.35*(bal.defLand||0) +
        1.20*(bal.defIntegrated||0) +
        1.00*((defW&&defW.logistics&&defW.logistics.health)||0.6) +
        0.65*((defW&&defW.c2&&defW.c2.health)||0.6) +
        0.65*(defK.radar+defK.isr+defK.comm)/3 -
        0.55*(defK.blind||0) -
        0.35*(defK.cyberStress||0)
      ) * defShock;
      const pAtk = softmaxPair(atkStrike, defShield);
      if(Math.abs(pAtk - 0.5) < 0.07) exhaust++;
      else if(pAtk > 0.5) atkWin++;
      else defHold++;
    }
    const atkP = atkWin / samples, defP = defHold / samples, exP = exhaust / samples;
    const dominance = clamp30((
      0.24*((bal.attackAir||0)-(bal.defAir||0)) +
      0.14*((bal.attackSea||0)-(bal.defSea||0)) +
      0.18*((bal.attackLand||0)-(bal.defLand||0)) +
      0.16*((bal.atkIntegrated||0)-(bal.defIntegrated||0)) +
      0.12*(((atkW&&atkW.logistics&&atkW.logistics.health)||0.6)-((defW&&defW.logistics&&defW.logistics.health)||0.6)) +
      0.08*(((atkW&&atkW.c2&&atkW.c2.health)||0.6)-((defW&&defW.c2&&defW.c2.health)||0.6)) +
      0.08*((atkK.radar+atkK.isr+atkK.sat+atkK.comm)/4 - (defK.radar+defK.isr+defK.sat+defK.comm)/4)
    ), -1.5, 1.5);
    return {bal, atkP, defP, exP, dominance, atkW, defW, atkK, defK};
  }

  function barRow(label, leftPct, rightPct, leftColor, rightColor, leftText, rightText){
    const total = Math.max(1e-6, leftPct + rightPct);
    const lp = 100 * leftPct / total;
    return '<div style="margin:4px 0">'+
      '<div style="display:flex;justify-content:space-between;gap:8px;color:#9fb5c9;font-size:11px"><span>'+label+'</span><span>'+leftText+' • '+rightText+'</span></div>'+
      '<div style="display:flex;height:10px;border-radius:999px;overflow:hidden;border:1px solid #223246;background:#091321">'+
      '<div style="width:'+lp+'%;background:'+leftColor+'"></div>'+
      '<div style="width:'+(100-lp)+'%;background:'+rightColor+'"></div>'+
      '</div></div>';
  }

  function drawSpark(){
    const cv = gid('v30Spark');
    if(!cv) return;
    const c = cv.getContext('2d');
    c.clearRect(0,0,cv.width,cv.height);
    c.fillStyle = '#07111a'; c.fillRect(0,0,cv.width,cv.height);
    c.strokeStyle = 'rgba(120,190,255,0.12)'; c.lineWidth = 1;
    for(let i=1;i<4;i++){ c.beginPath(); c.moveTo(0,i*cv.height/4); c.lineTo(cv.width,i*cv.height/4); c.stroke(); }
    const data = FINAL_V30.snapshots.slice(-48);
    if(data.length < 2){
      c.fillStyle = '#7f94a9'; c.font = '11px Arial'; c.fillText('Strategic sparkline will grow as the campaign breathes.', 10, 46);
      return;
    }
    const xs = (i) => 8 + i*(cv.width-16)/Math.max(1,data.length-1);
    const ys = (v) => cv.height-8 - clamp30(v,0,1)*(cv.height-16);
    const traces = [
      {key:'atkP', color:'#ff8a8a'},
      {key:'defP', color:'#8fe0ff'},
      {key:'exP', color:'#ffe18e'}
    ];
    traces.forEach(t => {
      c.strokeStyle = t.color; c.lineWidth = 2; c.beginPath();
      data.forEach((d,i) => {
        const x = xs(i), y = ys(d[t.key]||0);
        if(i===0) c.moveTo(x,y); else c.lineTo(x,y);
      });
      c.stroke();
    });
  }

  function updateFinalPanel(){
    ensureFinalPanel();
    const fc = forecastFromBalance();
    if(!fc){
      gid('v30ForecastBars').innerHTML = '<div style="color:#91a7bd">Awaiting an active engagement.</div>';
      gid('v30Dominance').innerHTML = '';
      gid('v30SnapshotMeta').textContent = 'No live engagement snapshots yet.';
      drawSpark();
      return;
    }
    const {bal, atkP, defP, exP, dominance, atkW, defW, atkK, defK} = fc;
    gid('v30ForecastBars').innerHTML = [
      barRow('Campaign forecast', atkP, defP, 'linear-gradient(90deg,#6a1d1d,#ff7a7a)', 'linear-gradient(90deg,#0d3550,#8fe0ff)', pct(atkP)+'% '+escapeHtml(bal.atk.country), pct(defP)+'% '+escapeHtml(bal.def.country)),
      barRow('Mutual exhaustion', exP, 1-exP, 'linear-gradient(90deg,#6a5d18,#ffe18e)', 'linear-gradient(90deg,#132033,#223246)', pct(exP)+'% draw drag', pct(1-exP)+'% decisive'),
      barRow('Kill-chain', (atkK.radar+atkK.isr+atkK.sat+atkK.comm)/4, (defK.radar+defK.isr+defK.sat+defK.comm)/4, 'linear-gradient(90deg,#6941c6,#b99cff)', 'linear-gradient(90deg,#145b6b,#78f0ff)', pct((atkK.radar+atkK.isr+atkK.sat+atkK.comm)/4)+'% atk', pct((defK.radar+defK.isr+defK.sat+defK.comm)/4)+'% def')
    ].join('');
    const ladder = dominance > 0.45 ? 'ATTACK EDGE' : dominance < -0.45 ? 'DEFENSE EDGE' : Math.abs(dominance) < 0.12 ? 'CONTESTED' : 'HOT';
    gid('v30AlertLadder').textContent = ladder;
    gid('v30Dominance').innerHTML = [
      '<div style="font-size:11px;color:#9fb5c9;margin-bottom:4px">Operational matrix</div>',
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">',
      '<div style="padding:8px;border:1px solid rgba(255,120,120,0.18);border-radius:10px;background:rgba(38,12,12,0.35)"><div style="color:#ffb0b0">'+escapeHtml(bal.atk.country)+'</div><div style="margin-top:4px">Air '+pct(bal.attackAir||0)+' • Sea '+pct(bal.attackSea||0)+' • Land '+pct(bal.attackLand||0)+'</div><div>Log '+pct((atkW&&atkW.logistics&&atkW.logistics.health)||0)+' • C2 '+pct((atkW&&atkW.c2&&atkW.c2.health)||0)+'</div></div>',
      '<div style="padding:8px;border:1px solid rgba(120,210,255,0.18);border-radius:10px;background:rgba(10,26,38,0.42)"><div style="color:#9fe7ff">'+escapeHtml(bal.def.country)+'</div><div style="margin-top:4px">Air '+pct(bal.defAir||0)+' • Sea '+pct(bal.defSea||0)+' • Land '+pct(bal.defLand||0)+'</div><div>Log '+pct((defW&&defW.logistics&&defW.logistics.health)||0)+' • C2 '+pct((defW&&defW.c2&&defW.c2.health)||0)+'</div></div>',
      '</div>'
    ].join('');
    gid('v30SnapshotMeta').textContent = 'Snapshots kept until reset: ' + FINAL_V30.snapshots.length + ' • Dominance drift ' + fnum(dominance, 2) + ' • Cyber stress ' + pct(atkK.cyberStress||0) + '% / ' + pct(defK.cyberStress||0) + '%';
    drawSpark();
  }

  function takeSnapshot(force){
    const now = Date.now();
    if(!force && now - FINAL_V30.lastSnap < 2500) return;
    const fc = forecastFromBalance();
    if(!fc) return;
    FINAL_V30.lastSnap = now;
    FINAL_V30.snapshots.push({
      t: now,
      atk: fc.bal.atk.country,
      def: fc.bal.def.country,
      atkP: fc.atkP,
      defP: fc.defP,
      exP: fc.exP,
      dominance: fc.dominance,
      atkLog: (fc.atkW&&fc.atkW.logistics&&fc.atkW.logistics.health)||0,
      defLog: (fc.defW&&fc.defW.logistics&&fc.defW.logistics.health)||0,
      atkC2: (fc.atkW&&fc.atkW.c2&&fc.atkW.c2.health)||0,
      defC2: (fc.defW&&fc.defW.c2&&fc.defW.c2.health)||0
    });
    if(FINAL_V30.snapshots.length > 180) FINAL_V30.snapshots.shift();
  }

  function exportFinalReport(){
    const fc = forecastFromBalance();
    const payload = {
      version: 'v30_final',
      exported_at: new Date().toISOString(),
      forecast: fc ? {
        attacker: fc.bal.atk.country,
        defender: fc.bal.def.country,
        attacker_win_probability: fc.atkP,
        defender_hold_probability: fc.defP,
        mutual_exhaustion_probability: fc.exP,
        dominance_drift: fc.dominance
      } : null,
      snapshots: FINAL_V30.snapshots,
      domain_war: (typeof DOMAIN_WAR !== 'undefined') ? DOMAIN_WAR : null,
      kill_chain: (typeof KCHAIN_V29 !== 'undefined') ? KCHAIN_V29 : null,
      log_tail: gid('log') ? gid('log').textContent.split('\n').slice(-120) : []
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'globe_strike_command_lab_v30_report_' + (++FINAL_V30.exportSeq) + '.json';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1500);
    if(typeof addLog === 'function') addLog('V30 FINAL REPORT EXPORTED: campaign forecast, snapshots, kill-chain, and live war-state bundle saved to JSON.', 'good-entry');
  }

  const _updateHud_v30_prev = updateHud;
  updateHud = function(){
    _updateHud_v30_prev();
    try { takeSnapshot(false); updateFinalPanel(); } catch(e){}
  };
  const _updateEngagementPanel_v30_prev = updateEngagementPanel;
  updateEngagementPanel = function(){
    _updateEngagementPanel_v30_prev();
    try {
      const fc = forecastFromBalance();
      if(!fc) return;
      engagementSummary.innerHTML += '<br><div style="color:#8fe0ff;font-size:11px;margin-bottom:4px">Strategic Forecast / Final Matrix</div>'+
        '<div style="color:#a9bdd3">Attack edge: <span style="color:#ffb0b0">'+escapeHtml(fc.bal.atk.country)+' '+pct(fc.atkP)+'%</span> • Defense edge: <span style="color:#9fe7ff">'+escapeHtml(fc.bal.def.country)+' '+pct(fc.defP)+'%</span> • Mutual exhaustion: <span style="color:#ffe18e">'+pct(fc.exP)+'%</span> • Dominance drift <span style="color:#d9e8f7">'+fnum(fc.dominance,2)+'</span>.</div>';
    } catch(e){}
  };
  const _btnClear_v30_prev = gid('btnClear').onclick;
  gid('btnClear').onclick = () => {
    FINAL_V30.snapshots.length = 0;
    FINAL_V30.lastSnap = 0;
    _btnClear_v30_prev();
    setTimeout(updateFinalPanel, 30);
  };
  window.addEventListener('load', () => setTimeout(updateFinalPanel, 250));
  if(typeof addLog === 'function') addLog('V30 FINAL MATRIX ONLINE: strategic forecast, dominance drift, exportable campaign reports, and persistent snapshot memory are now live.', 'good-entry');
})();
</script>
'''



EXTRA_V31_JS = r'''
<script>
(() => {
  const gid = (id) => document.getElementById(id);
  const V31 = { panelReady:false };
  const clamp31 = (x,a,b) => Math.max(a, Math.min(b, x));
  const pct31 = (v) => Math.round(100 * (Number(v) || 0));
  const lerp31 = (a,b,t) => a + (b-a)*t;
  function mix31(a,b,t){ return [Math.round(lerp31(a[0],b[0],t)), Math.round(lerp31(a[1],b[1],t)), Math.round(lerp31(a[2],b[2],t))]; }
  function rgba31(rgb,a){ return 'rgba('+rgb[0]+','+rgb[1]+','+rgb[2]+','+a+')'; }
  function glowAlpha31(color, a){ return color.replace(/rgba\(([^)]+),[^,]+\)/, 'rgba($1,'+a+')'); }
  function areaColor31(signal, drawBias){
    const drawPull = clamp31(drawBias || 0, 0, 1);
    if(drawPull > 0.56){
      const t = clamp31((drawPull-0.56)/0.44, 0, 1);
      return rgba31(mix31([255,188,70],[255,225,140],t), 0.13 + 0.12*t);
    }
    if(signal >= 0){
      const t = clamp31(signal/0.9, 0, 1);
      return rgba31(mix31([55,118,255],[70,255,170],t), 0.12 + 0.12*t);
    }
    const t = clamp31((-signal)/0.9, 0, 1);
    return rgba31(mix31([255,176,90],[255,78,78],t), 0.12 + 0.14*t);
  }

  function ensureV31Panel(){
    if(gid('v31BattlePanel')) return;
    const host = document.querySelector('.row > .stack:nth-child(2)') || document.body;
    const panel = document.createElement('div');
    panel.id = 'v31BattlePanel';
    panel.className = 'pnl';
    panel.innerHTML = [
      '<h3>COMMAND MOSAIC · MULTI-DOMAIN UI</h3>',
      '<div id="v31Headline" style="font-size:11px;color:#9fb5c9;line-height:1.5;margin-bottom:8px">Waiting for a live exchange.</div>',
      '<div id="v31DuelBars" style="display:grid;grid-template-columns:1fr 1fr;gap:10px"></div>',
      '<div id="v31SupportGrid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px"></div>',
      '<div id="v31CoalitionRows" style="margin-top:10px"></div>',
      '<div id="v31Legend" style="margin-top:10px;padding:10px;border:1px solid #1b2e44;border-radius:12px;background:#07101a"></div>'
    ].join('');
    host.appendChild(panel);
    const style = document.createElement('style');
    style.textContent = `
      #v31BattlePanel .v31-card{padding:10px;border-radius:12px;border:1px solid rgba(120,190,255,.14);background:linear-gradient(180deg,rgba(7,16,26,.96),rgba(4,10,18,.96));min-height:112px}
      #v31BattlePanel .v31-side{font-size:12px;font-weight:800;margin-bottom:6px}
      #v31BattlePanel .v31-sub{font-size:10px;color:#7f97af;margin-bottom:8px}
      #v31BattlePanel .v31-meter{display:flex;height:10px;border-radius:999px;overflow:hidden;background:#091321;border:1px solid #223246;margin:4px 0 8px}
      #v31BattlePanel .v31-fill{height:100%}
      #v31BattlePanel .v31-mini{display:grid;grid-template-columns:repeat(2,1fr);gap:6px;margin-top:6px}
      #v31BattlePanel .v31-k{padding:7px 8px;border-radius:10px;background:rgba(8,18,30,.85);border:1px solid rgba(120,190,255,.08);font-size:10px;color:#92a9bf}
      #v31BattlePanel .v31-k b{display:block;color:#eaf4ff;font-size:14px;margin-top:2px}
      #v31BattlePanel .v31-chip{display:inline-flex;align-items:center;gap:6px;padding:5px 8px;border-radius:999px;background:#0a1625;border:1px solid #21344a;font-size:10px;color:#b3cae2;margin:0 6px 6px 0}
      #v31BattlePanel .v31-dot{width:10px;height:10px;border-radius:50%}
      #v31BattlePanel .v31-row{margin:6px 0;padding:8px 10px;border-radius:10px;background:#08111d;border:1px solid #1b2e44}
      #v31BattlePanel .v31-rowhead{display:flex;justify-content:space-between;gap:8px;font-size:11px;color:#a9bfd4;margin-bottom:5px}
      #v31BattlePanel .v31-ally{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:10px;color:#8ea6be;margin-top:4px}
      #v31BattlePanel .v31-ally b{color:#e8f1fa}
    `;
    document.head.appendChild(style);
  }

  function nearestCoalition(country, count=3){
    const anchor = typeof getCountryAnchor === 'function' ? getCountryAnchor(country) : null;
    if(!anchor || !Array.isArray(PLACE_SEED)) return [];
    const countries = PLACE_SEED.filter(p => p && p.kind === 'country' && p.name && p.name !== country && p.lat != null && p.lon != null);
    const scored = countries.map(p => {
      const dx = (+p.lat - +anchor.lat), dy = (+p.lon - +anchor.lon);
      const dist = Math.sqrt(dx*dx + dy*dy);
      const prof = typeof domainProfile === 'function' ? domainProfile(p.name) : {air:0.4, sea:0.3, land:0.4};
      const tier = typeof countryTierSeed === 'function' ? countryTierSeed(p.name) : 3;
      const potency = 0.34*(prof.air||0) + 0.22*(prof.sea||0) + 0.24*(prof.land||0) + 0.20*clamp31((6-tier)/5,0,1);
      return {name:p.name, lat:+p.lat, lon:+p.lon, potency, dist};
    }).sort((a,b) => (a.dist - b.dist) - 8*(a.potency - b.potency));
    return scored.slice(0, count);
  }

  function coalitionSupport31(country, role){
    const allies = nearestCoalition(country, 3);
    let air=0, sea=0, land=0, defense=0;
    allies.forEach((a, idx) => {
      const prof = typeof domainProfile === 'function' ? domainProfile(a.name) : {air:0.35, sea:0.25, land:0.35};
      const weight = (role === 'def' ? 0.24 : 0.18) * (1 - 0.13*idx) * clamp31(1/(1+a.dist/55), 0.25, 1);
      air += weight * (prof.air || 0.3);
      sea += weight * (prof.sea || 0.25);
      land += weight * (prof.land || 0.3);
      defense += weight * (0.55*(prof.air||0.3) + 0.45*(prof.land||0.3));
    });
    return {air, sea, land, defense, allies};
  }

  function activeBattle31(){
    const fc = (typeof forecastFromBalance === 'function') ? forecastFromBalance() : null;
    if(!fc || !fc.bal) return null;
    const atk = fc.bal.atk.country, def = fc.bal.def.country;
    const atkCoal = coalitionSupport31(atk, 'atk');
    const defCoal = coalitionSupport31(def, 'def');
    const atkState = (typeof ensureDomainWarState === 'function') ? ensureDomainWarState(atk) : null;
    const defState = (typeof ensureDomainWarState === 'function') ? ensureDomainWarState(def) : null;
    const atkOps = (typeof ensureOpsV26 === 'function') ? ensureOpsV26(atk) : null;
    const defOps = (typeof ensureOpsV26 === 'function') ? ensureOpsV26(def) : null;
    const atkNode = (typeof nodeBindingSummary === 'function') ? nodeBindingSummary(atk) : {air:0,sea:0,land:0,defense:0};
    const defNode = (typeof nodeBindingSummary === 'function') ? nodeBindingSummary(def) : {air:0,sea:0,land:0,defense:0};
    const atkAirDef = clamp31(0.62*(fc.bal.atkIntegrated||0) + 0.38*(fc.bal.attackAir||0) + atkCoal.defense*0.55, 0, 1.45);
    const defAirDef = clamp31(0.72*(fc.bal.defIntegrated||0) + 0.52*(fc.bal.defAir||0) + defCoal.defense*0.72, 0, 1.5);
    const atkPressure = clamp31(0.44*(1-fc.defP) + 0.26*(fc.bal.attackLand||0) + 0.14*(atkState&&atkState.logistics?atkState.logistics.health:0.55) + 0.16*atkCoal.land, 0, 1.2);
    const defPressure = clamp31(0.44*(1-fc.atkP) + 0.26*(fc.bal.defLand||0) + 0.14*(defState&&defState.logistics?defState.logistics.health:0.55) + 0.16*defCoal.land, 0, 1.2);
    return {fc, atkCoal, defCoal, atkState, defState, atkOps, defOps, atkNode, defNode, atkAirDef, defAirDef, atkPressure, defPressure};
  }

  function glyph31(x, y, type, color, scale){
    if(!ctx) return;
    ctx.save();
    ctx.translate(x,y);
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = Math.max(1.1, scale*0.22);
    if(type === 'naval'){
      ctx.beginPath();
      ctx.moveTo(-1.2*scale, 0.55*scale); ctx.lineTo(1.2*scale, 0.55*scale); ctx.lineTo(0.55*scale, -0.45*scale); ctx.lineTo(-0.55*scale, -0.45*scale); ctx.closePath();
      ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-0.35*scale,-0.45*scale); ctx.lineTo(-0.05*scale,-1.05*scale); ctx.lineTo(0.25*scale,-0.45*scale); ctx.stroke();
    }else if(type === 'air'){
      ctx.beginPath();
      ctx.moveTo(0,-1.1*scale); ctx.lineTo(0.95*scale,0.95*scale); ctx.lineTo(0,0.25*scale); ctx.lineTo(-0.95*scale,0.95*scale); ctx.closePath();
      ctx.stroke();
    }else if(type === 'land'){
      ctx.strokeRect(-0.95*scale,-0.7*scale,1.9*scale,1.4*scale);
      ctx.beginPath(); ctx.moveTo(-1.15*scale,0.9*scale); ctx.lineTo(1.15*scale,0.9*scale); ctx.stroke();
    }else if(type === 'defense'){
      ctx.beginPath();
      ctx.moveTo(0,-1.05*scale); ctx.lineTo(0.88*scale,-0.35*scale); ctx.lineTo(0.58*scale,0.98*scale); ctx.lineTo(-0.58*scale,0.98*scale); ctx.lineTo(-0.88*scale,-0.35*scale); ctx.closePath();
      ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0,-0.55*scale); ctx.lineTo(0,0.48*scale); ctx.moveTo(-0.38*scale,-0.02*scale); ctx.lineTo(0.38*scale,-0.02*scale); ctx.stroke();
    }
    ctx.restore();
  }

  function glowDisc31(pr, radius, color){
    if(!pr || !ctx) return;
    const g = ctx.createRadialGradient(pr.x, pr.y, radius*0.18, pr.x, pr.y, radius);
    g.addColorStop(0, glowAlpha31(color, 0.22));
    g.addColorStop(1, glowAlpha31(color, 0.0));
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(pr.x, pr.y, radius, 0, Math.PI*2); ctx.fill();
  }

  function drawCountryStateOverlay31(){
    const battle = activeBattle31();
    if(!battle || typeof project !== 'function') return;
    const {fc} = battle;
    const actors = [
      {country:fc.bal.atk.country, signal: fc.atkP - fc.defP, drawBias: fc.exP, radius: 76 + 34*(fc.atkP||0), outline:'#ff8f8f'},
      {country:fc.bal.def.country, signal: fc.defP - fc.atkP, drawBias: fc.exP, radius: 76 + 34*(fc.defP||0), outline:'#8fe0ff'}
    ];
    actors.forEach((a, idx) => {
      const anchor = typeof getCountryAnchor === 'function' ? getCountryAnchor(a.country) : null;
      if(!anchor) return;
      const pr = project(ll2v(anchor.lat, anchor.lon, 1.012));
      if(!pr.visible) return;
      const fill = areaColor31(a.signal, a.drawBias);
      glowDisc31(pr, a.radius, fill);
      ctx.save();
      ctx.strokeStyle = a.outline || (idx===0?'#ff9e88':'#8fe0ff');
      ctx.lineWidth = 1.3;
      ctx.setLineDash([6,5]);
      ctx.beginPath(); ctx.arc(pr.x, pr.y, a.radius*0.88, 0, Math.PI*2); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = 'rgba(235,244,255,0.9)';
      ctx.font = 'bold 11px Arial';
      ctx.textAlign='center';
      const status = a.drawBias > 0.56 ? 'DRAW PRESSURE' : (a.signal > 0.18 ? 'GAINING' : a.signal < -0.18 ? 'LOSING' : 'CONTESTED');
      ctx.fillText(status, pr.x, pr.y - a.radius + 10);
      ctx.restore();
    });
  }

  function drawIntensityGlyphs31(){
    const battle = activeBattle31();
    if(!battle) return;
    const items = [
      {country:battle.fc.bal.atk.country, color:'#ff9d8c', bias:-1},
      {country:battle.fc.bal.def.country, color:'#8fe0ff', bias:1}
    ];
    items.forEach(pack => {
      const nodes = typeof getCountryTheaterNodes === 'function' ? getCountryTheaterNodes(pack.country) : [];
      const anchor = typeof getCountryAnchor === 'function' ? getCountryAnchor(pack.country) : null;
      if(!anchor) return;
      const prof = typeof domainProfile === 'function' ? domainProfile(pack.country) : {air:0.35,sea:0.25,land:0.35};
      const est = typeof estimateAssetCounts === 'function' ? estimateAssetCounts(pack.country) : {squadrons:0,fleets:0,brigades:0,batteries:0};
      const primary = project(ll2v(anchor.lat, anchor.lon, 1.02));
      if(primary.visible){
        const ad = pack.country===battle.fc.bal.atk.country ? battle.atkAirDef : battle.defAirDef;
        glyph31(primary.x + 28*pack.bias, primary.y - 26, 'defense', pack.color, 7 + 6*clamp31(ad,0,1));
      }
      (nodes || []).slice(0,4).forEach((n, idx) => {
        const pr = project(ll2v(n.lat, n.lon, 1.012));
        if(!pr.visible) return;
        const spread = 9 + idx*1.8;
        glyph31(pr.x - spread, pr.y + 2, 'air', pack.color, 5.5 + 5*(prof.air||0));
        glyph31(pr.x + spread, pr.y + 2, 'land', pack.color, 5.2 + 4.5*(prof.land||0));
        if(idx < 2) glyph31(pr.x, pr.y + 12, 'naval', pack.color, 5.3 + 4.8*(prof.sea||0));
      });
      if(primary.visible){
        ctx.save();
        ctx.fillStyle = 'rgba(8,18,30,0.82)';
        ctx.strokeStyle = pack.color; ctx.lineWidth=1;
        const bx = primary.x + 16*pack.bias - 48, by = primary.y + 20, bw = 96, bh = 34, br = 10;
        ctx.beginPath(); ctx.moveTo(bx+br,by); ctx.lineTo(bx+bw-br,by); ctx.quadraticCurveTo(bx+bw,by,bx+bw,by+br); ctx.lineTo(bx+bw,by+bh-br); ctx.quadraticCurveTo(bx+bw,by+bh,bx+bw-br,by+bh); ctx.lineTo(bx+br,by+bh); ctx.quadraticCurveTo(bx,by+bh,bx,by+bh-br); ctx.lineTo(bx,by+br); ctx.quadraticCurveTo(bx,by,bx+br,by); ctx.fill(); ctx.stroke();
        ctx.fillStyle = '#eaf4ff'; ctx.font = 'bold 10px Arial'; ctx.textAlign='center';
        const ad = pack.country===battle.fc.bal.atk.country ? battle.atkAirDef : battle.defAirDef;
        ctx.fillText('AD '+pct31(ad)+'%', primary.x + 16*pack.bias, primary.y + 34);
        ctx.fillStyle = '#9bb3ca'; ctx.font = '9px Arial';
        ctx.fillText('✈ '+(est.squadrons||0)+'  ⚓ '+(est.fleets||0)+'  ⌂ '+(est.brigades||0), primary.x + 16*pack.bias, primary.y + 47);
        ctx.restore();
      }
    });
  }

  function drawAllianceOverlay31(){
    const battle = activeBattle31();
    if(!battle) return;
    [
      {country:battle.fc.bal.atk.country, coal:battle.atkCoal, color:'rgba(255,146,146,0.78)'},
      {country:battle.fc.bal.def.country, coal:battle.defCoal, color:'rgba(143,224,255,0.78)'}
    ].forEach(side => {
      const anchor = typeof getCountryAnchor === 'function' ? getCountryAnchor(side.country) : null;
      if(!anchor) return;
      const apr = project(ll2v(anchor.lat, anchor.lon, 1.015));
      if(!apr.visible) return;
      side.coal.allies.forEach((ally, idx) => {
        const pr = project(ll2v(ally.lat, ally.lon, 1.01));
        if(!pr.visible) return;
        ctx.save();
        ctx.strokeStyle = side.color; ctx.lineWidth = 1; ctx.setLineDash([4,5]);
        ctx.beginPath(); ctx.moveTo(pr.x, pr.y); ctx.lineTo(apr.x, apr.y); ctx.stroke();
        ctx.setLineDash([]);
        const r = 4.5 + 3.5*ally.potency;
        ctx.fillStyle = side.color; ctx.beginPath(); ctx.arc(pr.x, pr.y, r, 0, Math.PI*2); ctx.fill();
        ctx.strokeStyle = 'rgba(255,255,255,0.18)'; ctx.stroke();
        ctx.fillStyle = 'rgba(230,242,255,0.9)'; ctx.font='bold 9px Arial'; ctx.textAlign='center';
        ctx.fillText('AL'+(idx+1), pr.x, pr.y - 7);
        ctx.restore();
      });
    });
  }

  function rowHtml31(label, a, d, colorA, colorD, suffix='%'){
    const total = Math.max(0.001, a + d);
    const lp = 100*a/total;
    return '<div class="v31-row"><div class="v31-rowhead"><span>'+label+'</span><span>'+Math.round(a*100)+suffix+' • '+Math.round(d*100)+suffix+'</span></div><div class="v31-meter"><div class="v31-fill" style="width:'+lp+'%;background:'+colorA+'"></div><div class="v31-fill" style="width:'+(100-lp)+'%;background:'+colorD+'"></div></div></div>';
  }

  function supportCard31(title, value, note){
    return '<div class="v31-k">'+title+'<b>'+value+'</b><div>'+note+'</div></div>';
  }

  function updateV31Panel(){
    ensureV31Panel();
    const battle = activeBattle31();
    if(!battle){
      gid('v31Headline').textContent = 'Waiting for a live exchange.';
      gid('v31DuelBars').innerHTML = '';
      gid('v31SupportGrid').innerHTML = '';
      gid('v31CoalitionRows').innerHTML = '';
      gid('v31Legend').innerHTML = '<span class="v31-chip"><span class="v31-dot" style="background:#8fe0ff"></span>air defense intensity</span><span class="v31-chip"><span class="v31-dot" style="background:#74c0ff"></span>air wing glyph</span><span class="v31-chip"><span class="v31-dot" style="background:#6fd3b0"></span>naval group glyph</span><span class="v31-chip"><span class="v31-dot" style="background:#ffd48a"></span>land deployment glyph</span>';
      return;
    }
    const {fc, atkCoal, defCoal, atkState, defState, atkNode, defNode, atkAirDef, defAirDef, atkPressure, defPressure} = battle;
    const atkColor = '#ff9d8c', defColor = '#8fe0ff';
    gid('v31Headline').innerHTML = '<b style="color:#eaf4ff">'+escapeHtml(fc.bal.atk.country)+'</b> and <b style="color:#eaf4ff">'+escapeHtml(fc.bal.def.country)+'</b> are both being graded across strike edge, shield depth, naval projection, airwing pressure, land deployment, coalition lift, and node stress. Countries can both be bleeding at once.';
    gid('v31DuelBars').innerHTML = [
      '<div class="v31-card"><div class="v31-side" style="color:'+atkColor+'">'+escapeHtml(fc.bal.atk.country)+'</div><div class="v31-sub">offensive side / counter-defense posture</div>'+ 
        '<div class="v31-meter"><div class="v31-fill" style="width:'+pct31(fc.atkP)+'%;background:linear-gradient(90deg,#5a1111,'+atkColor+')"></div></div>'+
        '<div class="v31-mini">'+
          supportCard31('Win arc', pct31(fc.atkP)+'%', 'attack-side forecast')+
          supportCard31('Air shield', pct31(atkAirDef)+'%', 'AD intensity + ally cover')+
          supportCard31('Sea push', pct31((fc.bal.attackSea||0)+atkCoal.sea)+'%', 'fleet reach + convoy lift')+
          supportCard31('Land mass', pct31((fc.bal.attackLand||0)+atkCoal.land)+'%', 'brigade pressure')+
        '</div></div>',
      '<div class="v31-card"><div class="v31-side" style="color:'+defColor+'">'+escapeHtml(fc.bal.def.country)+'</div><div class="v31-sub">defending side / counterstrike survival</div>'+ 
        '<div class="v31-meter"><div class="v31-fill" style="width:'+pct31(fc.defP)+'%;background:linear-gradient(90deg,#0d3550,'+defColor+')"></div></div>'+
        '<div class="v31-mini">'+
          supportCard31('Hold arc', pct31(fc.defP)+'%', 'defensive forecast')+
          supportCard31('Air shield', pct31(defAirDef)+'%', 'AD intensity + intercept mesh')+
          supportCard31('Sea hold', pct31((fc.bal.defSea||0)+defCoal.sea)+'%', 'naval persistence')+
          supportCard31('Land hold', pct31((fc.bal.defLand||0)+defCoal.land)+'%', 'ground staying power')+
        '</div></div>'
    ].join('');
    gid('v31SupportGrid').innerHTML = [
      supportCard31('Draw gravity', pct31(fc.exP)+'%', 'both sides can sag together'),
      supportCard31('Atk coalition', (atkCoal.allies.length||0)+' cells', 'escort / lift / EW spillover'),
      supportCard31('Def coalition', (defCoal.allies.length||0)+' cells', 'intercepts / replenishment'),
      supportCard31('Atk node stress', pct31(1-((atkState&&atkState.logistics&&atkState.logistics.health)||0.65))+'%', 'ops drag + closures'),
      supportCard31('Def node stress', pct31(1-((defState&&defState.logistics&&defState.logistics.health)||0.65))+'%', 'ops drag + closures'),
      supportCard31('Dominance drift', (Math.round(fc.dominance*100)/100).toFixed(2), 'green/blue edge vs red/orange slip')
    ].join('');
    gid('v31CoalitionRows').innerHTML = [
      rowHtml31('Air defense intensity', clamp31(atkAirDef,0.02,1), clamp31(defAirDef,0.02,1), 'linear-gradient(90deg,#5d1b1b,#ff9d8c)', 'linear-gradient(90deg,#113a53,#8fe0ff)'),
      rowHtml31('Naval presence', clamp31((fc.bal.attackSea||0)+atkCoal.sea,0.02,1), clamp31((fc.bal.defSea||0)+defCoal.sea,0.02,1), 'linear-gradient(90deg,#6b3b1c,#ffb36b)', 'linear-gradient(90deg,#0f3f56,#68d8ff)'),
      rowHtml31('Air force pressure', clamp31((fc.bal.attackAir||0)+atkCoal.air,0.02,1), clamp31((fc.bal.defAir||0)+defCoal.air,0.02,1), 'linear-gradient(90deg,#6f2444,#ff83c1)', 'linear-gradient(90deg,#184865,#8fe0ff)'),
      rowHtml31('Land / marine deployment', clamp31((fc.bal.attackLand||0)+atkCoal.land,0.02,1), clamp31((fc.bal.defLand||0)+defCoal.land,0.02,1), 'linear-gradient(90deg,#6c4617,#ffd07a)', 'linear-gradient(90deg,#27553a,#8dffbe)'),
      rowHtml31('Area pressure', clamp31(atkPressure,0.02,1), clamp31(defPressure,0.02,1), 'linear-gradient(90deg,#7a2c16,#ff8b5f)', 'linear-gradient(90deg,#0f4e5f,#7ce7ff)', ''),
      '<div class="v31-row"><div class="v31-rowhead"><span>Allied support cells</span><span>'+escapeHtml(fc.bal.atk.country)+' / '+escapeHtml(fc.bal.def.country)+'</span></div>'+
        atkCoal.allies.map((a,i)=>'<div class="v31-ally"><span><b>ATK AL'+(i+1)+'</b> '+escapeHtml(a.name)+'</span><span>support '+Math.round(100*a.potency)+'%</span></div>').join('') +
        defCoal.allies.map((a,i)=>'<div class="v31-ally"><span><b>DEF AL'+(i+1)+'</b> '+escapeHtml(a.name)+'</span><span>support '+Math.round(100*a.potency)+'%</span></div>').join('') +
      '</div>'
    ].join('');
    gid('v31Legend').innerHTML = '<span class="v31-chip"><span class="v31-dot" style="background:#8fe0ff"></span>shield glyph = air defense intensity</span>'+
      '<span class="v31-chip"><span class="v31-dot" style="background:#ff83c1"></span>air wing glyph = air force pressure</span>'+
      '<span class="v31-chip"><span class="v31-dot" style="background:#68d8ff"></span>naval glyph = fleets / maritime lanes</span>'+
      '<span class="v31-chip"><span class="v31-dot" style="background:#ffd07a"></span>land glyph = brigades / marine ground pressure</span>'+
      '<span class="v31-chip"><span class="v31-dot" style="background:#ff9d8c"></span>country tint = losing / gaining / draw strain</span>'+
      '<span class="v31-chip"><span class="v31-dot" style="background:#ffffff"></span>dashed ally lines = coalition help / intercept assist</span>';
  }

  const _drawGlobe_v31_prev = drawGlobe;
  drawGlobe = function(){
    _drawGlobe_v31_prev();
    try { drawCountryStateOverlay31(); drawAllianceOverlay31(); drawIntensityGlyphs31(); } catch(e){}
  };
  const _updateHud_v31_prev = updateHud;
  updateHud = function(){
    _updateHud_v31_prev();
    try { updateV31Panel(); } catch(e){}
  };
  const _updateEngagementPanel_v31_prev = updateEngagementPanel;
  updateEngagementPanel = function(){
    _updateEngagementPanel_v31_prev();
    try {
      const battle = activeBattle31();
      if(!battle) return;
      engagementSummary.innerHTML += '<br><div style="color:#ffe18e;font-size:11px;margin-bottom:4px">Command Mosaic</div>'+
        '<div style="color:#a9bdd3">Air-defense intensity <span style="color:#9fe7ff">'+pct31(battle.defAirDef)+'%</span> on the defender and <span style="color:#ffb0b0">'+pct31(battle.atkAirDef)+'%</span> on the attacker. Coalition cells visible on-globe can pad interception and projection pressure, while country tint shows gain, loss, or draw strain rather than pretending only one side can bleed.</div>';
    } catch(e){}
  };
  window.addEventListener('load', () => setTimeout(updateV31Panel, 260));
  if(typeof addLog === 'function') addLog('V31 UI MOSAIC ONLINE: area-state tint, ally support lines, shield/naval/air/land glyphs, and stronger multi-domain stats are now live.', 'good-entry');
})();


/* ═══════════════════════════════════════════════════════
   V32 AUTOWAR + WAR ROOM UI
   Head-to-head simulation, coalition joining, strategic escalation,
   stronger live stats, and richer command-map overlays.
   ═══════════════════════════════════════════════════════ */
(function(){
  var SIM32 = window.SIM32 || {
    active:false, mode:'duel', rootA:'', rootB:'', sides:{A:[],B:[]},
    participants:{}, joins:[], history:[], startedAt:0, lastLaunch:0,
    nextLaunchAt:0, nextJoinAt:0, lastSide:'B', winner:'', reason:'',
    autoJoin:true, allowNukes:false, escalation:0, cycle:0,
    maxParticipants:14, launchCount:0, roundLabel:'', uiReady:false,
    baseline:{}, allyLedger:{A:[],B:[]}
  };
  window.SIM32=SIM32;

  function sim32Now(){ return (typeof performance!=='undefined' && performance.now) ? performance.now() : Date.now(); }
  function sim32Clamp(x,a,b){ return Math.max(a, Math.min(b, x)); }
  function sim32Mean(arr){ return arr&&arr.length ? arr.reduce((a,b)=>a+(+b||0),0)/arr.length : 0; }
  function sim32Pct(x){ return Math.round(sim32Clamp(x||0,0,1.5)*100); }
  function sim32FmtList(arr){ return (arr||[]).filter(Boolean).join(', '); }
  function sim32CountryList(){
    const set=new Set();
    (Object.keys(ARSENAL||{})).forEach(c=>set.add(normalizeCountryName(c)));
    (PLACE_SEED||[]).forEach(p=>{ if(p&&p.kind==='country'&&p.name) set.add(normalizeCountryName(p.name)); });
    return Array.from(set).filter(Boolean).sort((a,b)=>a.localeCompare(b));
  }
  function sim32Anchor(country){ return (typeof getCountryAnchor==='function' ? getCountryAnchor(country) : null) || (typeof resolveSeedPlaceFast==='function' ? resolveSeedPlaceFast(country) : null); }
  function sim32InvFrac(country, kind){
    const st=typeof getCountryState==='function' ? getCountryState(country) : null;
    if(!st) return 0.5;
    const bucket=st[kind]||{};
    const vals=Object.values(bucket);
    if(!vals.length) return 0.5;
    let rem=0, ini=0;
    vals.forEach(v=>{ rem += +v.remaining||0; ini += +v.initial||0; });
    return ini>0 ? sim32Clamp(rem/ini,0,1) : 0.5;
  }
  function sim32WarState(country){ return (typeof ensureDomainWarState==='function') ? ensureDomainWarState(country) : null; }
  function sim32KillChain(country){
    if(typeof ensureKChain==='function') return ensureKChain(country);
    if(typeof ensureKillChainV29==='function') return ensureKillChainV29(country);
    if(typeof ensureKillChainState==='function') return ensureKillChainState(country);
    if(typeof ensureKillChain==='function') return ensureKillChain(country);
    return null;
  }
  function sim32Ops(country){ return (typeof ensureOpsV26==='function') ? ensureOpsV26(country) : null; }
  function sim32CountryScore(country){
    if(!country) return 0;
    const prof=typeof domainProfile==='function' ? domainProfile(country) : {air:0.35,sea:0.25,land:0.35,logistics:0.35,integrated:0.35};
    const ws=sim32WarState(country);
    const kc=sim32KillChain(country);
    const ops=sim32Ops(country);
    const off=sim32InvFrac(country,'offense');
    const de=sim32InvFrac(country,'defense');
    const air=ws ? (typeof domainAssetFactor==='function' ? domainAssetFactor(ws.air) : ((ws.air.ready||1)/(ws.air.max||1))) : 0.55;
    const sea=ws ? (typeof domainAssetFactor==='function' ? domainAssetFactor(ws.sea) : ((ws.sea.ready||1)/(ws.sea.max||1))) : 0.40;
    const land=ws ? (typeof domainAssetFactor==='function' ? domainAssetFactor(ws.land) : ((ws.land.ready||1)/(ws.land.max||1))) : 0.52;
    const airDef=ws ? (typeof domainAssetFactor==='function' ? domainAssetFactor(ws.airDefense) : ((ws.airDefense.ready||1)/(ws.airDefense.max||1))) : 0.50;
    const logi=ws && ws.logistics ? sim32Clamp((ws.logistics.health||0.5)*(1-0.35*(ws.logistics.strain||0)),0.05,1.2) : (prof.logistics||0.45);
    const c2=ws && ws.c2 ? sim32Clamp((ws.c2.health||0.5)*(1-0.4*(ws.c2.degraded||0)),0.05,1.2) : (prof.integrated||0.45);
    const kcHealth=kc ? sim32Clamp(0.22*(kc.radar||0.5)+0.22*(kc.isr||0.5)+0.18*(kc.sat||kc.satellite||0.5)+0.18*(kc.comm||kc.comms||0.5)+0.20*(kc.ewDef||kc.ewShield||0.5),0.05,1.2) : 0.6;
    const opsAir=ops?sim32Clamp(1-0.55*(ops.lostCityShare||0)-0.22*(ops.repairLoad||0)/2,0.05,1.2):0.7;
    const opsSea=ops?sim32Clamp(1-0.55*(ops.lostCityShare||0)-0.15*(ops.repairLoad||0)/2,0.05,1.2):0.7;
    const base=0.18*off + 0.18*de + 0.08*air + 0.06*sea + 0.08*land + 0.08*airDef + 0.10*logi + 0.10*c2 + 0.08*kcHealth + 0.04*opsAir + 0.02*opsSea;
    const profileBoost=0.08*(0.30*(prof.air||0)+0.18*(prof.sea||0)+0.22*(prof.land||0)+0.30*(prof.integrated||0));
    return sim32Clamp(base + profileBoost, 0.03, 1.25);
  }
  function sim32SideScore(side){
    const arr=(SIM32.sides[side]||[]).filter(Boolean);
    if(!arr.length) return 0;
    let total=0;
    arr.forEach((c,idx)=>{
      const w=idx===0 ? 1.0 : (0.62 - Math.min(0.34, idx*0.05));
      total += w*sim32CountryScore(c);
    });
    return total / Math.max(1, arr.length*0.72);
  }
  function sim32FrontBalance(){
    const a=sim32SideScore('A'), b=sim32SideScore('B');
    const sum=Math.max(0.0001,a+b);
    return {a,b,aP:a/sum,bP:b/sum,delta:a-b};
  }
  function sim32StrategicEligible(w){
    const txt=((w&&w.name)||' '+(w&&w.type)||'').toLowerCase();
    return /icbm|slbm|strategic|nuclear|trident|minuteman|m51|sarmat|yars|df-41|hwasong|jericho iii/.test(txt);
  }
  function sim32ConventionalEligible(w){ return !sim32StrategicEligible(w); }
  function sim32WeaponPool(country){
    const ar=ARSENAL&&ARSENAL[country];
    if(!ar||!ar.offense) return [];
    const st=typeof getCountryState==='function' ? getCountryState(country) : null;
    return ar.offense.filter(w=>!st || !st.offense[w.name] || st.offense[w.name].remaining>0);
  }
  function sim32PickWeapon(country, enemyCountry, rolePressure){
    let pool=sim32WeaponPool(country);
    if(!pool.length) return null;
    const strategicWanted=!!SIM32.allowNukes && (SIM32.escalation>=2 || rolePressure>0.72 || sim32CountryScore(country)<0.26);
    const conventional=pool.filter(sim32ConventionalEligible);
    const strategic=pool.filter(sim32StrategicEligible);
    if(strategicWanted && strategic.length){
      pool=strategic.slice().sort((a,b)=>(b.mach||0)-(a.mach||0));
      return pool[Math.min(pool.length-1, Math.floor((SIM32.cycle||0)%Math.max(1,pool.length)))];
    }
    pool=(conventional.length?conventional:pool).slice().sort((a,b)=>{
      const ea=(a.mach||1)*(a.evasion||0.4)*(sim32StrategicEligible(a)?0.85:1.0);
      const eb=(b.mach||1)*(b.evasion||0.4)*(sim32StrategicEligible(b)?0.85:1.0);
      return eb-ea;
    });
    return pool[Math.min(pool.length-1, Math.floor((SIM32.cycle||0)%Math.max(1,pool.length)))];
  }
  function sim32BestNode(country, enemyCountry, mode){
    if(mode==='origin' && typeof chooseCounterstrikeOrigin==='function') return chooseCounterstrikeOrigin(country, enemyCountry, null) || sim32Anchor(country);
    const nodes=(typeof getCityDefenseNodes==='function') ? getCityDefenseNodes(country, sim32Anchor(country)) : [];
    if(nodes && nodes.length){
      const ranked=nodes.slice().sort((a,b)=>((b.weight||b.importance||0.5)-(a.weight||a.importance||0.5)));
      return ranked[0];
    }
    return sim32Anchor(country);
  }
  function sim32CandidateJoiners(rootCountry, side){
    const existing=new Set([...(SIM32.sides.A||[]), ...(SIM32.sides.B||[])]);
    const near=(typeof nearestCoalition==='function') ? nearestCoalition(rootCountry, 8) : [];
    const candidates=[];
    near.forEach((n,idx)=>{
      const c=normalizeCountryName(n.name||'');
      if(!c || existing.has(c) || c===rootCountry) return;
      const prof=typeof domainProfile==='function' ? domainProfile(c) : {integrated:0.4};
      const doc=typeof getDoctrineForCountry==='function' ? getDoctrineForCountry(c) : {c2:0.6};
      const band=(typeof inferCountryBand==='function') ? inferCountryBand(c) : 'regional';
      const affinity=((band===inferCountryBand(rootCountry))?0.16:0.05) + 0.10*(doc.c2||0.6) + 0.08*(prof.integrated||0.4);
      const distBoost=sim32Clamp(1/(1+(n.dist||80)/45),0.18,1);
      candidates.push({country:c, score:affinity*distBoost*(1-idx*0.06)});
    });
    return candidates.sort((a,b)=>b.score-a.score).slice(0,5);
  }
  function sim32TryJoin(side){
    if(!SIM32.autoJoin) return;
    const root=side==='A'?SIM32.rootA:SIM32.rootB;
    if(!root) return;
    const enemySide=side==='A'?'B':'A';
    if((SIM32.sides[side]||[]).length>=SIM32.maxParticipants) return;
    const bal=sim32FrontBalance();
    const losing = side==='A' ? (bal.aP<0.47) : (bal.bP<0.47);
    const pressure = side==='A' ? (1-bal.aP) : (1-bal.bP);
    const rolls=sim32CandidateJoiners(root, side);
    if(!rolls.length) return;
    const pick=rolls.find(r => (SIM32.sides[enemySide]||[]).indexOf(r.country)<0);
    if(!pick) return;
    const chance=sim32Clamp((losing?0.62:0.34) + pressure*0.30 + pick.score*0.35,0,0.92);
    if(Math.random() < chance){
      SIM32.sides[side].push(pick.country);
      SIM32.allyLedger[side].push(pick.country);
      SIM32.participants[pick.country]=side;
      SIM32.baseline[pick.country]=sim32CountryScore(pick.country);
      addLog('COALITION JOIN: '+escapeHtml(pick.country)+' reinforces Side '+side+' with projected multi-domain support.', 'good-entry');
    }
  }
  function sim32ChooseCountry(side){
    const arr=(SIM32.sides[side]||[]).filter(Boolean);
    if(!arr.length) return '';
    const ranked=arr.slice().sort((a,b)=>sim32CountryScore(b)-sim32CountryScore(a));
    const losing=ranked.slice().sort((a,b)=>sim32CountryScore(a)-sim32CountryScore(b));
    return (SIM32.cycle%3===0 ? losing[0] : ranked[0]) || arr[0];
  }
  function sim32ChooseTargetCountry(side){
    const enemy=side==='A' ? 'B' : 'A';
    const arr=(SIM32.sides[enemy]||[]).filter(Boolean);
    if(!arr.length) return '';
    return arr.slice().sort((a,b)=>sim32CountryScore(a)-sim32CountryScore(b))[0] || arr[0];
  }
  function sim32LaunchOne(){
    if(!SIM32.active || SIM32.winner) return;
    const bal=sim32FrontBalance();
    const side = (SIM32.lastSide==='A') ? 'B' : 'A';
    const attacker=sim32ChooseCountry(side);
    const defender=sim32ChooseTargetCountry(side);
    if(!attacker || !defender || attacker===defender) return;
    const from=sim32BestNode(attacker, defender, 'origin');
    const to=sim32BestNode(defender, attacker, 'target');
    if(!from || from.lat==null || !to || to.lat==null) return;
    const rolePressure = side==='A' ? (1-bal.aP) : (1-bal.bP);
    const weapon=sim32PickWeapon(attacker, defender, rolePressure);
    if(!weapon) return;
    SIM32.lastSide=side;
    SIM32.cycle += 1;
    const strategic=sim32StrategicEligible(weapon);
    const attack=launchProjectedAttack({from:from,to:to,weapon:weapon,attackerCountry:attacker,defenderCountry:defender,autoCounterEnabled:true,tag:'sim32'});
    if(attack){
      SIM32.launchCount += 1;
      SIM32.lastLaunch = sim32Now();
      addLog('SIM WAR: Side '+side+' '+escapeHtml(attacker)+' launches '+escapeHtml(weapon.name)+' toward '+escapeHtml(defender)+(strategic?' [strategic escalation]':'')+'.', strategic ? 'warn-entry' : 'fire-entry');
    }
  }
  function sim32Exhausted(country){
    const score=sim32CountryScore(country);
    const off=sim32InvFrac(country,'offense'), de=sim32InvFrac(country,'defense');
    return score<0.17 || (off<0.08 && de<0.10);
  }
  function sim32CheckWinner(){
    if(!SIM32.active || SIM32.winner) return;
    const now=sim32Now();
    const bal=sim32FrontBalance();
    const aAlive=(SIM32.sides.A||[]).some(c=>!sim32Exhausted(c));
    const bAlive=(SIM32.sides.B||[]).some(c=>!sim32Exhausted(c));
    if(!aAlive && !bAlive){ SIM32.winner='DRAW'; SIM32.reason='mutual exhaustion'; }
    else if(!aAlive){ SIM32.winner='B'; SIM32.reason='Side A collapse'; }
    else if(!bAlive){ SIM32.winner='A'; SIM32.reason='Side B collapse'; }
    else if(SIM32.history.length>14){
      const recent=SIM32.history.slice(-10);
      const aMean=sim32Mean(recent.map(x=>x.aP)), bMean=sim32Mean(recent.map(x=>x.bP));
      if(aMean>0.74 && recent.every(x=>x.aP>0.68)){ SIM32.winner='A'; SIM32.reason='sustained dominance'; }
      else if(bMean>0.74 && recent.every(x=>x.bP>0.68)){ SIM32.winner='B'; SIM32.reason='sustained dominance'; }
    }
    if(!SIM32.winner && now-SIM32.startedAt > 420000){
      if(Math.abs(bal.delta)<0.08) { SIM32.winner='DRAW'; SIM32.reason='campaign timeout'; }
      else { SIM32.winner = bal.delta>0 ? 'A' : 'B'; SIM32.reason='campaign points'; }
    }
    if(SIM32.winner){
      addLog('AUTOWAR END: '+escapeHtml(SIM32.winner==='DRAW'?'Draw':('Side '+SIM32.winner+' wins'))+' by '+escapeHtml(SIM32.reason)+'.', SIM32.winner==='DRAW' ? 'warn-entry' : 'good-entry');
      SIM32.active=false;
      const btn=$('btnSimWar'); if(btn) btn.textContent='AUTO WAR';
    }
  }
  function sim32Tick(){
    if(!SIM32.active) return;
    const now=sim32Now();
    const bal=sim32FrontBalance();
    SIM32.escalation = !SIM32.allowNukes ? 0 : (bal.aP<0.30 || bal.bP<0.30 ? 2 : ((bal.aP<0.42 || bal.bP<0.42) ? 1 : 0));
    SIM32.roundLabel = bal.delta>0.12 ? 'Side A gaining' : (bal.delta<-0.12 ? 'Side B gaining' : 'contested');
    SIM32.history.push({t:now,a:bal.a,b:bal.b,aP:bal.aP,bP:bal.bP,esc:SIM32.escalation});
    if(SIM32.history.length>180) SIM32.history.shift();
    if(now>=SIM32.nextJoinAt){ sim32TryJoin('A'); sim32TryJoin('B'); SIM32.nextJoinAt = now + 9000 + Math.random()*6000; }
    const launchGap = $('realisticMode')&&$('realisticMode').checked ? (3600 + Math.random()*2200) : (1400 + Math.random()*1000);
    if(now>=SIM32.nextLaunchAt){ sim32LaunchOne(); SIM32.nextLaunchAt = now + launchGap; }
    sim32CheckWinner();
  }
  function sim32Reset(){
    SIM32.active=false; SIM32.mode='duel'; SIM32.rootA=''; SIM32.rootB=''; SIM32.sides={A:[],B:[]}; SIM32.participants={};
    SIM32.joins=[]; SIM32.history=[]; SIM32.startedAt=0; SIM32.lastLaunch=0; SIM32.nextLaunchAt=0; SIM32.nextJoinAt=0;
    SIM32.lastSide='B'; SIM32.winner=''; SIM32.reason=''; SIM32.escalation=0; SIM32.cycle=0; SIM32.launchCount=0; SIM32.roundLabel=''; SIM32.baseline={}; SIM32.allyLedger={A:[],B:[]};
  }
  function sim32InferCountry(raw, fallback){
    raw=(raw||'').trim();
    let c=raw ? inferCountryFromPlaceName(raw)||normalizeCountryName(raw) : '';
    if(c && ((ARSENAL&&ARSENAL[c]) || sim32CountryList().indexOf(c)>=0)) return c;
    return fallback||'';
  }
  function sim32AutoEnemyFor(country){
    const all=sim32CountryList().filter(c=>c!==country);
    const aAnchor=sim32Anchor(country);
    const ranked=all.map(c=>{
      const p=typeof domainProfile==='function' ? domainProfile(c) : {integrated:0.4};
      const an=sim32Anchor(c);
      let dist=999;
      if(aAnchor&&an&&gcDistMiles) dist=gcDistMiles([aAnchor.lat,aAnchor.lon],[an.lat,an.lon]);
      const power=sim32CountryScore(c);
      return {c, score:power*(dist>900?1.15:0.84)+(dist<250?0.12:0)};
    }).sort((x,y)=>y.score-x.score);
    return ranked.length ? ranked[0].c : '';
  }
  function sim32Start(mode){
    const selA=$('simSideA'), selB=$('simSideB');
    const a=sim32InferCountry(selA && selA.value || fromInput.value, inferCountryFromPlaceName(fromInput.value)||'United States');
    let b=sim32InferCountry(selB && selB.value || toInput.value, inferCountryFromPlaceName(toInput.value)||'');
    if(!a){ addLog('AUTOWAR: resolve Side A country first.', 'warn-entry'); return; }
    if(!b || a===b) b=sim32AutoEnemyFor(a);
    if(!b || a===b){ addLog('AUTOWAR: could not resolve an enemy country.', 'warn-entry'); return; }
    sim32Reset();
    SIM32.active=true; SIM32.mode=mode||'duel'; SIM32.rootA=a; SIM32.rootB=b; SIM32.startedAt=sim32Now();
    SIM32.autoJoin=$('simAutoJoin') ? !!$('simAutoJoin').checked : true;
    SIM32.allowNukes=$('simNukes') ? !!$('simNukes').checked : false;
    SIM32.sides.A=[a]; SIM32.sides.B=[b]; SIM32.participants[a]='A'; SIM32.participants[b]='B';
    SIM32.baseline[a]=sim32CountryScore(a); SIM32.baseline[b]=sim32CountryScore(b);
    SIM32.nextLaunchAt=SIM32.startedAt+400; SIM32.nextJoinAt=SIM32.startedAt+6500;
    const btn=$('btnSimWar'); if(btn) btn.textContent='AUTO WAR: RUNNING';
    addLog('AUTOWAR START: Side A '+escapeHtml(a)+' vs Side B '+escapeHtml(b)+' • '+escapeHtml(SIM32.allowNukes?'strategic escalation enabled':'conventional ladder')+'.', 'good-entry');
    if(mode==='chaos'){
      SIM32.nextJoinAt=SIM32.startedAt+2500;
      addLog('FREE ESCALATION: coalition entry cadence shortened, expect extra joiners.', 'warn-entry');
    }
  }
  function sim32Stop(){
    if(SIM32.active || SIM32.winner){
      SIM32.active=false;
      const btn=$('btnSimWar'); if(btn) btn.textContent='AUTO WAR';
      addLog('AUTOWAR STOPPED: simulation halted by user.', 'warn-entry');
    }
  }

  function sim32InjectUI(){
    if(SIM32.uiReady) return;
    SIM32.uiReady=true;
    const style=document.createElement('style');
    style.textContent=`
      .sim32-panel{margin-top:8px;border:1px solid #22344c;background:linear-gradient(180deg,#08111d,#06101a);border-radius:14px;padding:10px;box-shadow:inset 0 0 0 1px rgba(255,255,255,.02)}
      .sim32-title{font-size:11px;font-weight:900;letter-spacing:1.4px;color:#ffe28f;margin-bottom:8px}
      .sim32-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
      .sim32-grid label{margin-top:0;font-size:10px;color:#85a0bb}
      .sim32-select,.sim32-panel select{width:100%;background:#091321;border:1px solid #24384e;border-radius:10px;color:#d9e8f7;padding:8px 10px;font-size:12px}
      .sim32-checks{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;color:#aac1d7;font-size:11px}
      .sim32-btns{display:flex;gap:6px;margin-top:8px}
      .sim32-btn{flex:1;padding:10px 12px;border-radius:10px;border:none;font-weight:900;font-size:11px;cursor:pointer}
      #btnSimWar{background:linear-gradient(135deg,#5fffc1,#7ec7ff);color:#041019}
      #btnChaosWar{background:linear-gradient(135deg,#ffc25b,#ff6e6e);color:#180a00}
      #btnStopWar{background:#102134;color:#d7e7f5;border:1px solid #24384e}
      .war-room{position:absolute;right:12px;top:112px;width:370px;max-height:78%;overflow:auto;background:rgba(3,8,14,.82);border:1px solid rgba(120,160,205,.18);border-radius:16px;padding:12px 12px 10px;backdrop-filter:blur(5px);box-shadow:0 14px 34px rgba(0,0,0,.35)}
      .war-room h4{margin:0 0 8px;font-size:13px;color:#ffe28f;letter-spacing:1px}
      .war-row{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px}
      .war-card{background:rgba(10,18,29,.92);border:1px solid rgba(116,154,198,.12);border-radius:12px;padding:8px}
      .war-card .k{font-size:9px;letter-spacing:1.2px;color:#89a5bf;text-transform:uppercase}
      .war-card .v{font-size:18px;font-weight:900;color:#f4fbff;margin-top:2px}
      .war-bar{height:10px;border-radius:999px;background:#091321;border:1px solid #24384e;overflow:hidden;position:relative}
      .war-fillA,.war-fillB{height:100%}
      .war-fillA{background:linear-gradient(90deg,#55ffd2,#7ecbff)}
      .war-fillB{background:linear-gradient(90deg,#ff9d5d,#ff5d8f)}
      .war-side{font-size:11px;color:#d8e7f7;margin:6px 0 4px;display:flex;justify-content:space-between;gap:10px}
      .war-micro{font-size:10px;color:#9cb4ca;line-height:1.45}
      .war-legend{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
      .war-chip{font-size:10px;padding:4px 7px;border-radius:999px;background:#0b1521;border:1px solid #24384e;color:#cfe0ef}
      .war-mini{display:flex;justify-content:space-between;gap:8px;font-size:10px;color:#cfe0ef;margin:4px 0}
      .war-room::-webkit-scrollbar{width:10px}.war-room::-webkit-scrollbar-thumb{background:#1a2c40;border-radius:999px}
    `;
    document.head.appendChild(style);

    const leftStack=document.querySelector('.row .stack');
    if(leftStack){
      const panel=document.createElement('div');
      panel.className='sim32-panel';
      panel.innerHTML=`<div class="sim32-title">AUTO WAR SIMULATION</div>
        <div class="sim32-grid">
          <div><label>SIDE A COUNTRY</label><select id="simSideA"></select></div>
          <div><label>SIDE B COUNTRY</label><select id="simSideB"></select></div>
        </div>
        <div class="sim32-checks">
          <label><input type="checkbox" id="simAutoJoin" checked> auto-join allies</label>
          <label><input type="checkbox" id="simNukes"> strategic nuclear escalation</label>
        </div>
        <div class="sim32-btns">
          <button class="sim32-btn" id="btnSimWar" type="button">AUTO WAR</button>
          <button class="sim32-btn" id="btnChaosWar" type="button">FREE ESCALATION</button>
          <button class="sim32-btn" id="btnStopWar" type="button">STOP</button>
        </div>
        <div class="war-micro" style="margin-top:8px">AUTO WAR keeps firing, counter-firing, and pulling in coalition help until a winner or draw emerges. FREE ESCALATION accelerates outside entry and strategic ladder pressure for game mode.</div>`;
      leftStack.insertBefore(panel, leftStack.children[1]||null);
      const opts=sim32CountryList();
      const html='<option value="">Auto / infer from panel</option>'+opts.map(c=>'<option>'+escapeHtml(c)+'</option>').join('');
      $('simSideA').innerHTML=html; $('simSideB').innerHTML=html;
      $('simSideA').value=sim32InferCountry(fromInput.value, 'United States') || 'United States';
      $('simSideB').value=sim32InferCountry(toInput.value, '') || 'Russia';
      $('btnSimWar').onclick=()=>sim32Start('duel');
      $('btnChaosWar').onclick=()=>sim32Start('chaos');
      $('btnStopWar').onclick=()=>sim32Stop();
      fromInput.addEventListener('change',()=>{ if(!$('simSideA').value) $('simSideA').value=sim32InferCountry(fromInput.value,'United States')||'United States'; });
      toInput.addEventListener('change',()=>{ if(!$('simSideB').value) $('simSideB').value=sim32InferCountry(toInput.value,'')||sim32AutoEnemyFor($('simSideA').value||'United States'); });
    }

    const wrap=document.querySelector('.cnv-wrap');
    if(wrap){
      const room=document.createElement('div');
      room.className='war-room';
      room.id='warRoom32';
      room.innerHTML='<h4>WAR ROOM</h4><div class="war-micro">Choose sides and launch AUTO WAR. The panel will promote live campaign control, attrition, alliances, escalation, and domain posture here.</div>';
      wrap.appendChild(room);
    }
  }

  function sim32SideDetails(side){
    const arr=(SIM32.sides[side]||[]).filter(Boolean);
    const root=side==='A'?SIM32.rootA:SIM32.rootB;
    const rootScore=root?sim32CountryScore(root):0;
    const off=arr.length?sim32Mean(arr.map(c=>sim32InvFrac(c,'offense'))):0;
    const de=arr.length?sim32Mean(arr.map(c=>sim32InvFrac(c,'defense'))):0;
    const ws=arr.length?sim32Mean(arr.map(c=>{ const w=sim32WarState(c); return w&&w.logistics?sim32Clamp((w.logistics.health||0.5)*(1-0.35*(w.logistics.strain||0)),0,1.2):0.5; })):0;
    const c2=arr.length?sim32Mean(arr.map(c=>{ const w=sim32WarState(c); return w&&w.c2?sim32Clamp((w.c2.health||0.5)*(1-0.4*(w.c2.degraded||0)),0,1.2):0.5; })):0;
    const kc=arr.length?sim32Mean(arr.map(c=>{ const k=sim32KillChain(c); return k?sim32Clamp(0.22*(k.radar||0.5)+0.22*(k.isr||0.5)+0.18*(k.satellite||0.5)+0.18*(k.comms||0.5)+0.20*(k.ewShield||0.5),0,1.2):0.5; })):0;
    const stress=arr.length?sim32Mean(arr.map(c=>{ const base=SIM32.baseline[c]||sim32CountryScore(c); return sim32Clamp(1-sim32CountryScore(c)/Math.max(0.08, base),0,1.2); })):0;
    return {countries:arr,root,rootScore,off,de,log:ws,c2,kc,stress,score:sim32SideScore(side)};
  }
  function sim32UpdateRoom(){
    const room=$('warRoom32'); if(!room) return;
    if(!SIM32.active && !SIM32.winner){
      room.innerHTML='<h4>WAR ROOM</h4><div class="war-micro">AUTO WAR waits for your order. Set Side A and Side B, then let the engine drive attacks, defenses, coalition entry, and escalation by itself.</div><div class="war-legend"><span class="war-chip">shield = air defense intensity</span><span class="war-chip">hull = naval groups</span><span class="war-chip">wing = air force</span><span class="war-chip">block = land / marine</span><span class="war-chip">country glow = gaining / losing / contested</span></div>';
      return;
    }
    const bal=sim32FrontBalance();
    const A=sim32SideDetails('A'), B=sim32SideDetails('B');
    const head=(SIM32.winner ? ('RESULT: '+(SIM32.winner==='DRAW'?'DRAW':('SIDE '+SIM32.winner+' WINS'))+' • '+SIM32.reason.toUpperCase()) : ('AUTOWAR LIVE • '+SIM32.roundLabel.toUpperCase()));
    const runtime=SIM32.startedAt ? Math.max(0, Math.floor((sim32Now()-SIM32.startedAt)/1000)) : 0;
    const bar=(a,b)=>`<div class="war-bar"><div class="war-fillA" style="width:${Math.round(100*sim32Clamp(a,0,1))}%"></div><div class="war-fillB" style="width:${Math.round(100*sim32Clamp(b,0,1))}%;position:absolute;right:0;top:0"></div></div>`;
    const sideBox=(side, data, colorLabel)=>`<div class="war-card"><div class="k">Side ${side} • ${escapeHtml(colorLabel)}</div><div class="v">${sim32Pct(data.score)}%</div><div class="war-micro">${escapeHtml(data.root)}${data.countries.length>1?' + '+(data.countries.length-1)+' allies':''}</div>${bar(data.off,data.de)}<div class="war-mini"><span>offense ${sim32Pct(data.off)}%</span><span>defense ${sim32Pct(data.de)}%</span></div><div class="war-mini"><span>log ${sim32Pct(data.log)}%</span><span>C2 ${sim32Pct(data.c2)}%</span></div><div class="war-mini"><span>kill-chain ${sim32Pct(data.kc)}%</span><span>stress ${sim32Pct(data.stress)}%</span></div><div class="war-micro" style="margin-top:4px">${escapeHtml(sim32FmtList(data.countries.slice(0,5)))}${data.countries.length>5?' …':''}</div></div>`;
    room.innerHTML=`<h4>${head}</h4>
      <div class="war-row">
        <div class="war-card"><div class="k">campaign runtime</div><div class="v">${runtime}s</div><div class="war-micro">launches ${SIM32.launchCount} • escalation ${SIM32.escalation}/2 • ${escapeHtml(SIM32.allowNukes?'strategic ladder live':'conventional ladder')}</div></div>
        <div class="war-card"><div class="k">forecast</div><div class="v">A ${sim32Pct(bal.aP)}% / B ${sim32Pct(bal.bP)}%</div><div class="war-micro">${Math.abs(bal.delta)<0.08?'draw strain rising':(bal.delta>0?'Side A pressure edge':'Side B pressure edge')}</div></div>
      </div>
      <div class="war-side"><span>Side A war-power</span><span>${sim32Pct(A.score)}%</span></div>${bar(A.score,B.score)}
      <div class="war-side"><span>Side B war-power</span><span>${sim32Pct(B.score)}%</span></div>
      <div class="war-row">${sideBox('A',A,'attacker / coalition')} ${sideBox('B',B,'defender / coalition')}</div>
      <div class="war-card"><div class="k">allied entry & state tint</div><div class="war-micro">Country glow now tracks local campaign drift rather than a fake single winner. Both camps can bleed, hold, or recover at the same time. Dashed ally links show coalition help arriving into air defense, sea projection, or land pressure.</div><div class="war-mini"><span>Side A joins</span><span>${escapeHtml(sim32FmtList(SIM32.allyLedger.A.slice(-4)))||'—'}</span></div><div class="war-mini"><span>Side B joins</span><span>${escapeHtml(sim32FmtList(SIM32.allyLedger.B.slice(-4)))||'—'}</span></div></div>
      <div class="war-legend"><span class="war-chip">AUTO WAR = hands-off duel</span><span class="war-chip">FREE ESCALATION = faster coalition joins</span><span class="war-chip">winner = collapse, dominance, points, or draw</span></div>`;
  }

  function sim32DrawCountryGlow(country, side){
    const anchor=sim32Anchor(country); if(!anchor||anchor.lat==null) return;
    const pr=projectLL(anchor.lat, anchor.lon, 1.016); if(!pr.visible) return;
    const base=SIM32.baseline[country] || sim32CountryScore(country) || 0.4;
    const score=sim32CountryScore(country);
    const drift=sim32Clamp((score-base)/Math.max(0.08,base), -1, 1);
    const losing=drift<0 ? -drift : 0;
    const gaining=drift>0 ? drift : 0;
    const pulse=0.88+0.12*Math.sin(sim32Now()*0.002 + stableHash01(country)*6.28);
    const r=28 + 36*Math.abs(drift) + 12*((SIM32.participants[country]&&country!== (side==='A'?SIM32.rootA:SIM32.rootB))?1:0);
    const color = gaining>0.08 ? (side==='A'?'rgba(100,255,218,':'rgba(255,176,110,') : (losing>0.08 ? 'rgba(255,88,88,' : 'rgba(245,220,120,');
    ctx.save();
    const g=ctx.createRadialGradient(pr.x,pr.y,0,pr.x,pr.y,r*1.35*pulse);
    g.addColorStop(0,color+(0.16+0.16*Math.max(gaining,losing))+')');
    g.addColorStop(1,color+'0)');
    ctx.fillStyle=g; ctx.beginPath(); ctx.arc(pr.x,pr.y,r*1.35*pulse,0,Math.PI*2); ctx.fill();
    ctx.globalAlpha=0.72; ctx.strokeStyle=color+'0.85)'; ctx.lineWidth=1.4; ctx.setLineDash(Math.abs(drift)<0.08?[4,5]:[]); ctx.beginPath(); ctx.arc(pr.x,pr.y,r*pulse,0,Math.PI*2); ctx.stroke();
    ctx.restore();
  }
  function sim32DrawAllies(side){
    const root=side==='A'?SIM32.rootA:SIM32.rootB;
    const rootAnchor=sim32Anchor(root); if(!rootAnchor||rootAnchor.lat==null) return;
    const rootPr=projectLL(rootAnchor.lat, rootAnchor.lon, 1.012); if(!rootPr.visible) return;
    const color=side==='A'?'rgba(104,255,221,0.9)':'rgba(255,168,96,0.9)';
    (SIM32.sides[side]||[]).forEach((country, idx)=>{
      const anchor=sim32Anchor(country); if(!anchor||anchor.lat==null) return;
      const pr=projectLL(anchor.lat, anchor.lon, 1.012); if(!pr.visible) return;
      sim32DrawCountryGlow(country, side);
      const prof=typeof domainProfile==='function' ? domainProfile(country) : {air:0.35,sea:0.25,land:0.35};
      const scale=5 + 5*Math.max(prof.air||0, prof.sea||0, prof.land||0);
      if(typeof glyph31==='function'){
        glyph31(pr.x-10, pr.y, 'defense', color, scale*0.75);
        glyph31(pr.x+10, pr.y-2, 'naval', color, scale*0.72);
        glyph31(pr.x, pr.y-11, 'air', color, scale*0.72);
        glyph31(pr.x, pr.y+11, 'land', color, scale*0.70);
      }
      if(country!==root){
        ctx.save(); ctx.strokeStyle=color; ctx.globalAlpha=0.42; ctx.lineWidth=1.1; ctx.setLineDash([5,5]); ctx.beginPath(); ctx.moveTo(rootPr.x, rootPr.y); ctx.lineTo(pr.x, pr.y); ctx.stroke(); ctx.restore();
      }
      ctx.save(); ctx.fillStyle='rgba(240,247,255,0.88)'; ctx.font='10px ui-monospace, monospace'; ctx.textAlign='center'; ctx.fillText(country.toUpperCase().slice(0,12), pr.x, pr.y-18-scale); ctx.restore();
    });
  }
  function sim32DrawAutoWarOverlay(){
    if(!SIM32.active && !SIM32.winner) return;
    ctx.save();
    sim32DrawAllies('A');
    sim32DrawAllies('B');
    ctx.restore();
  }

  const _drawGlobe_v32_prev = drawGlobe;
  drawGlobe = function(){ _drawGlobe_v32_prev(); try{ sim32DrawAutoWarOverlay(); }catch(e){} };
  const _updateHud_v32_prev = updateHud;
  updateHud = function(){ _updateHud_v32_prev(); try{ if(SIM32.active || SIM32.winner){ const bal=sim32FrontBalance(); hud.innerHTML += '<br>AUTOWAR <span class="val">'+escapeHtml(SIM32.winner?('RESULT '+(SIM32.winner==='DRAW'?'DRAW':'SIDE '+SIM32.winner)):SIM32.roundLabel.toUpperCase())+'</span>'+' • A <span class="val">'+sim32Pct(bal.aP)+'%</span> vs B <span class="val">'+sim32Pct(bal.bP)+'%</span>'+' • escalation <span class="val">'+SIM32.escalation+'/2</span>'; } }catch(e){} };
  const _loop_v32_prev = loop;
  loop = function(){ try{ sim32Tick(); }catch(e){} _loop_v32_prev(); try{ sim32UpdateRoom(); }catch(e){} };
  const _btnClear_v32_prev = $('btnClear').onclick;
  $('btnClear').onclick = ()=>{ sim32Reset(); const btn=$('btnSimWar'); if(btn) btn.textContent='AUTO WAR'; _btnClear_v32_prev(); };
  window.SIM32 = SIM32;
  window.sim32Now = sim32Now;
  window.sim32Tick = sim32Tick;
  window.sim32TryJoin = sim32TryJoin;
  window.sim32ChooseCountry = sim32ChooseCountry;
  window.sim32ChooseTargetCountry = sim32ChooseTargetCountry;
  window.sim32PickWeapon = sim32PickWeapon;
  window.sim32FrontBalance = sim32FrontBalance;
  window.sim32SideDetails = sim32SideDetails;
  window.sim32Anchor = sim32Anchor;
  window.sim32InjectUI = sim32InjectUI;
  window.sim32UpdateRoom = sim32UpdateRoom;
  window.sim32Reset = sim32Reset;
  window.sim32CountryScore = sim32CountryScore;
  window.getCityDefenseNodes = window.getCityDefenseNodes || getCityDefenseNodes;
  window.getCityDefenseNode = window.getCityDefenseNode || getCityDefenseNode;
  window.chooseCounterstrikeOrigin = window.chooseCounterstrikeOrigin || chooseCounterstrikeOrigin;
  window.chooseCounterstrikeTarget = window.chooseCounterstrikeTarget || chooseCounterstrikeTarget;
  window.addEventListener('load', ()=>{ setTimeout(sim32InjectUI, 40); addLog('AUTOWAR COMMAND LAYER ONLINE: hands-off duel, coalition joins, and strategic ladder panel ready.', 'good-entry'); });
})();
</script>
'''

EXTRA_V33_JS = r'''
<script>
(()=>{
  var AI33 = window.AI33 = Object.assign({enabled:false,busy:false,lastCall:0,cadenceMs:12000,plan:null,cfg:null}, window.AI33||{});
  function ai33Clamp(x,a,b){ x=+x; if(!isFinite(x)) x=(a+b)/2; return Math.max(a, Math.min(b, x)); }
  function ai33SideState(side){
    const info = typeof sim32SideDetails==='function' ? sim32SideDetails(side) : {root:'',countries:[],score:0.5,off:0.5,de:0.5,log:0.5,c2:0.5,kc:0.5,stress:0.5};
    return {root:info.root,countries:info.countries||[],score:info.score||0.5,offense:info.off||0.5,defense:info.de||0.5,logistics:info.log||0.5,c2:info.c2||0.5,kill_chain:info.kc||0.5,stress:info.stress||0.5};
  }
  async function ai33LoadConfig(){
    try{ const r=await fetch('/api/ai_config'); const j=await r.json(); AI33.cfg=j; AI33.cadenceMs=Math.max(4000,(+j.cadence_seconds||12)*1000); }
    catch(e){ AI33.cfg={configured:false,model:'gpt-5.4'}; }
    ai33UpdatePanel();
  }
  function ai33Payload(){
    const bal=typeof sim32FrontBalance==='function' ? sim32FrontBalance() : {aP:0.5,bP:0.5,delta:0};
    return {ts: Date.now(),mode: SIM32.mode||'duel',allow_nukes: !!SIM32.allowNukes,escalation: +SIM32.escalation||0,sideA: ai33SideState('A'),sideB: ai33SideState('B'),forecast: {a:bal.aP||0.5,b:bal.bP||0.5,delta:bal.delta||0},recent_history: (SIM32.history||[]).slice(-10),launches: +SIM32.launchCount||0,cycle: +SIM32.cycle||0,objective: $('aiDirectiveObj') ? $('aiDirectiveObj').value : 'Balance tempo, alliances, escalation, and targeting for cinematic but coherent gameplay.'};
  }
  async function ai33CallDirector(force){
    if(!AI33.enabled || AI33.busy) return;
    const now=Date.now(); if(!force && (now-AI33.lastCall)<AI33.cadenceMs) return;
    AI33.busy=true; ai33UpdatePanel();
    try{ const r=await fetch('/api/ai_director',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(ai33Payload())}); const j=await r.json(); AI33.plan=(j&&j.plan)||null; AI33.lastCall=Date.now(); if(AI33.plan){ addLog('AI DIRECTOR: '+escapeHtml((AI33.plan.summary||'new steering plan received'))+'.', 'info-entry'); } }catch(e){ addLog('AI DIRECTOR: request failed, keeping previous steering.', 'warn-entry'); }
    AI33.busy=false; ai33UpdatePanel();
  }
  function ai33GetSidePlan(side){ const p=(AI33.plan||{}); return side==='A'?(p.sideA||{}):(p.sideB||{}); }
  function ai33ApplyGlobal(){ const g=(AI33.plan&&AI33.plan.global)||{}; SIM32.aiTempo = ai33Clamp(g.tempo||1,0.5,1.8); SIM32.aiJoinBias = ai33Clamp(g.join_bias||1,0.5,1.8); SIM32.aiEscalationBias = ai33Clamp(g.escalation_bias||1,0.5,1.8); SIM32.aiCeasefireBias = ai33Clamp(g.ceasefire_bias||0,0,1); }
  const _sim32Tick_v33_prev = (window.sim32Tick || (typeof sim32Tick!=='undefined' ? sim32Tick : function(){}));
  window.sim32Tick = sim32Tick = function(){ if(AI33.enabled && SIM32.active){ ai33ApplyGlobal(); ai33CallDirector(false); } _sim32Tick_v33_prev(); if(SIM32.active){ if(SIM32.aiCeasefireBias>0.72 && Math.random()<0.01 && Math.abs((sim32FrontBalance().delta||0))<0.04){ SIM32.winner='DRAW'; SIM32.reason='AI-directed ceasefire'; } if(SIM32.aiTempo && SIM32.nextLaunchAt){ const now=sim32Now(); const remaining=SIM32.nextLaunchAt-now; if(remaining>250){ SIM32.nextLaunchAt = now + remaining/Math.max(0.7,SIM32.aiTempo); } } if(SIM32.aiJoinBias && SIM32.nextJoinAt){ const now=sim32Now(); const remaining=SIM32.nextJoinAt-now; if(remaining>1200){ SIM32.nextJoinAt = now + remaining/Math.max(0.75,SIM32.aiJoinBias); } } if(SIM32.allowNukes && SIM32.aiEscalationBias){ const bal=sim32FrontBalance(); if((bal.aP<0.36||bal.bP<0.36) && SIM32.aiEscalationBias>1.15){ SIM32.escalation=Math.min(2, Math.max(SIM32.escalation,1)); } } } };
  const _sim32TryJoin_v33_prev = (window.sim32TryJoin || (typeof sim32TryJoin!=='undefined' ? sim32TryJoin : function(){}));
  window.sim32TryJoin = sim32TryJoin = function(side){ const before=((SIM32.sides[side]||[]).length); _sim32TryJoin_v33_prev(side); const plan=ai33GetSidePlan(side), j=ai33Clamp(plan.join_bias||1,0.5,1.8); if(AI33.enabled && SIM32.active && j>1.12 && ((SIM32.sides[side]||[]).length)===before && Math.random()<Math.min(0.45,(j-1)*0.7)){ _sim32TryJoin_v33_prev(side); } };
  const _sim32ChooseCountry_v33_prev = (window.sim32ChooseCountry || (typeof sim32ChooseCountry!=='undefined' ? sim32ChooseCountry : function(){ return ''; }));
  window.sim32ChooseCountry = sim32ChooseCountry = function(side){ const arr=(SIM32.sides[side]||[]).filter(Boolean); if(!arr.length) return _sim32ChooseCountry_v33_prev(side); const plan=ai33GetSidePlan(side), mode=(plan.target_priority||'').toLowerCase(); const rankedStrong=arr.slice().sort((a,b)=>sim32CountryScore(b)-sim32CountryScore(a)); const rankedWeak=arr.slice().sort((a,b)=>sim32CountryScore(a)-sim32CountryScore(b)); if(mode==='strongest') return rankedStrong[0]||_sim32ChooseCountry_v33_prev(side); if(mode==='highest_pressure') return rankedWeak[0]||_sim32ChooseCountry_v33_prev(side); return (plan.aggression||1)>1.08 ? (rankedStrong[0]||_sim32ChooseCountry_v33_prev(side)) : _sim32ChooseCountry_v33_prev(side); };
  const _sim32ChooseTarget_v33_prev = (window.sim32ChooseTargetCountry || (typeof sim32ChooseTargetCountry!=='undefined' ? sim32ChooseTargetCountry : function(){ return ''; }));
  window.sim32ChooseTargetCountry = sim32ChooseTargetCountry = function(side){ const enemy=side==='A'?'B':'A'; const arr=(SIM32.sides[enemy]||[]).filter(Boolean); if(!arr.length) return _sim32ChooseTarget_v33_prev(side); const plan=ai33GetSidePlan(side), mode=(plan.target_priority||'').toLowerCase(); const weak=arr.slice().sort((a,b)=>sim32CountryScore(a)-sim32CountryScore(b)); const strong=arr.slice().sort((a,b)=>sim32CountryScore(b)-sim32CountryScore(a)); const capitalish=arr.slice().sort((a,b)=>((sim32Anchor(b)||{}).capital?1:0)-((sim32Anchor(a)||{}).capital?1:0)); if(mode==='strongest') return strong[0]||_sim32ChooseTarget_v33_prev(side); if(mode==='capital') return capitalish[0]||weak[0]||_sim32ChooseTarget_v33_prev(side); return weak[0]||_sim32ChooseTarget_v33_prev(side); };
  const _sim32PickWeapon_v33_prev = (window.sim32PickWeapon || (typeof sim32PickWeapon!=='undefined' ? sim32PickWeapon : function(){ return null; }));
  window.sim32PickWeapon = sim32PickWeapon = function(country, enemyCountry, rolePressure){ const side = (SIM32.sides.A||[]).includes(country) ? 'A' : 'B'; const plan=ai33GetSidePlan(side), p=ai33Clamp(plan.nuke_bias||1,0.5,1.8); if(AI33.enabled && SIM32.allowNukes && p>1.18 && SIM32.escalation>=1){ rolePressure=Math.max(rolePressure||0, 0.82); } if(AI33.enabled && (plan.aggression||1)>1.18){ rolePressure=Math.max(rolePressure||0, 0.68); } return _sim32PickWeapon_v33_prev(country, enemyCountry, rolePressure); };
  const _sim32UpdateRoom_v33_prev = sim32UpdateRoom;
  sim32UpdateRoom = function(){ _sim32UpdateRoom_v33_prev(); ai33UpdatePanel(); };
  function ai33InjectPanel(){ if($('aiDirectorPanel')) return; const parent=document.querySelector('.stack:last-child') || document.querySelector('.stack'); if(!parent) return; const panel=document.createElement('div'); panel.className='pnl'; panel.id='aiDirectorPanel'; panel.innerHTML=`<h3>AI DIRECTOR</h3><div class="hint" style="margin-bottom:8px">Server-side OpenAI director can steer tempo, alliances, targeting, and escalation. The key stays on the server side through an environment variable, not in the browser.</div><div class="grid2"><div><label>CADENCE</label><input type="text" id="aiCadenceLabel" value="12s" readonly></div><div><label>MODEL</label><input type="text" id="aiModelLabel" value="loading..." readonly></div></div><label style="margin-top:8px">DIRECTIVE</label><input type="text" id="aiDirectiveObj" value="Balance tempo, alliances, escalation, and targeting for cinematic but coherent gameplay."><div class="chkrow"><input type="checkbox" id="aiDirectorEnable"><div>Enable AI Director<div class="hint">When AUTO WAR is running, the director periodically sends compact game state to the backend and returns steering multipliers.</div></div></div><div class="btns" style="margin-top:8px"><button class="btn btn-random" id="btnAiPulse" type="button">PULSE AI NOW</button></div><div id="aiDirectorStatus" class="preview-note"><b>AI STATUS</b><br>Waiting for configuration.</div>`; parent.insertBefore(panel, parent.children[1]||null); $('btnAiPulse').onclick=()=>ai33CallDirector(true); $('aiDirectorEnable').onchange=(e)=>{ AI33.enabled=!!e.target.checked; ai33UpdatePanel(); if(AI33.enabled) ai33CallDirector(true); }; }
  function ai33UpdatePanel(){ const box=$('aiDirectorStatus'); if(!box) return; if($('aiCadenceLabel')) $('aiCadenceLabel').value=Math.round(AI33.cadenceMs/1000)+'s'; if($('aiModelLabel')) $('aiModelLabel').value=((AI33.cfg&&AI33.cfg.model)||'gpt-5.4') + (((AI33.cfg&&AI33.cfg.configured) ? ' • key ok' : ' • fallback')); const plan=AI33.plan||{}; const src=plan._source||((AI33.cfg&&AI33.cfg.configured)?'openai':'fallback'); box.innerHTML='<b>AI STATUS</b><br>'+ (AI33.busy ? 'Consulting director...' : (AI33.enabled ? 'Director armed.' : 'Director idle.')) + '<br><span class="mini">source: '+escapeHtml(src)+' • last pulse: '+(AI33.lastCall?Math.round((Date.now()-AI33.lastCall)/1000)+'s ago':'never')+'</span>' + '<br><span class="mini">'+escapeHtml(plan.summary||'No plan yet.')+'</span>' + (plan.narrative?'<br><span class="mini">'+escapeHtml(plan.narrative)+'</span>':''); }
  window.addEventListener('load', ()=>{ setTimeout(ai33InjectPanel, 90); setTimeout(ai33LoadConfig, 180); });
})();
</script>
'''


EXTRA_V46_JS = r'''
<script>
(function(){
  function ai46Clamp(v,a,b){ return (typeof sim32Clamp==='function') ? sim32Clamp(v,a,b) : Math.max(a, Math.min(b, Number(v)||0)); }
  function ai46Mean(arr){ return arr && arr.length ? arr.reduce((s,v)=>s+(+v||0),0)/arr.length : 0; }
  function ai46SideOfCountry(country){ if((SIM32.sides.A||[]).includes(country)) return 'A'; if((SIM32.sides.B||[]).includes(country)) return 'B'; return ''; }
  function ai46InventoryTotals(country){
    const st=(typeof getCountryState==='function') ? getCountryState(country) : null;
    const offVals=st&&st.offense ? Object.values(st.offense) : [];
    const defVals=st&&st.defense ? Object.values(st.defense) : [];
    const offRem=offVals.reduce((s,e)=>s+((e&&e.remaining)||0),0), offInit=offVals.reduce((s,e)=>s+((e&&e.initial)||0),0);
    const defRem=defVals.reduce((s,e)=>s+((e&&e.remaining)||0),0), defInit=defVals.reduce((s,e)=>s+((e&&e.initial)||0),0);
    return {offRem, offInit, defRem, defInit, offFrac:offInit?offRem/offInit:0.5, defFrac:defInit?defRem/defInit:0.5};
  }
  function ai46EnsureCountryState(country){
    const st=(typeof getCountryState==='function') ? getCountryState(country) : null;
    if(!st) return null;
    if(!st.aiState){
      const d=st.doctrine||{};
      const inv=ai46InventoryTotals(country);
      st.aiState={readiness: ai46Clamp(0.58 + 0.18*(d.training||0.74) + 0.14*(d.maintenance||0.74), 0.20, 1.05),repair_rate: ai46Clamp(0.42 + 0.28*(d.maintenance||0.74), 0.05, 1.00),sensor_confidence: ai46Clamp(0.48 + 0.24*(d.sensorFusion!=null?d.sensorFusion:(d.c2||0.74)) + 0.08*(d.c2||0.74), 0.10, 1.00),uncertainty: ai46Clamp(0.34 - 0.10*(d.sensorFusion||0.74) + 0.12*(1-inv.defFrac), 0.05, 0.95),reserve_release: ai46Clamp(0.30 + 0.22*(1-inv.offFrac), 0.00, 1.00),stock_burn: ai46Clamp(0.38 + 0.16*(1-inv.offFrac), 0.00, 1.00),morale: ai46Clamp(0.56 + 0.10*(d.training||0.74) - 0.08*(1-inv.defFrac), 0.20, 1.00),lastRepairTick: 0};
    }
    return st.aiState;
  }
  const _initCountryCampaign_v46_prev = window.initCountryCampaign || (typeof initCountryCampaign!=='undefined' ? initCountryCampaign : function(c){ return CAMPAIGN_STATE&&CAMPAIGN_STATE.countries&&CAMPAIGN_STATE.countries[c]; });
  window.initCountryCampaign = initCountryCampaign = function(country){ const st=_initCountryCampaign_v46_prev(country); if(st) ai46EnsureCountryState(country||st.country); return st; };
  const _resetCampaignState_v46_prev = window.resetCampaignState || (typeof resetCampaignState!=='undefined' ? resetCampaignState : function(){});
  window.resetCampaignState = resetCampaignState = function(){ _resetCampaignState_v46_prev(); Object.keys((CAMPAIGN_STATE&&CAMPAIGN_STATE.countries)||{}).forEach(ai46EnsureCountryState); if(AI33){ AI33.feedback={A:{attacks:0,leaks:0,intercepts:0,shots:0},B:{attacks:0,leaks:0,intercepts:0,shots:0}}; AI33.lastWeaveAt=0; } };
  Object.keys((CAMPAIGN_STATE&&CAMPAIGN_STATE.countries)||{}).forEach(ai46EnsureCountryState);
  const _sim32SideDetails_v46_prev = window.sim32SideDetails || (typeof sim32SideDetails!=='undefined' ? sim32SideDetails : function(side){ return {countries:(SIM32.sides[side]||[]), score:0.5, off:0.5, de:0.5, log:0.5, c2:0.5, kc:0.5, stress:0.5}; });
  window.sim32SideDetails = sim32SideDetails = function(side){ const d=_sim32SideDetails_v46_prev(side) || {}; const arr=(SIM32.sides[side]||[]).filter(Boolean); const extras=arr.map(c=>{ const s=ai46EnsureCountryState(c)||{}; const inv=ai46InventoryTotals(c); return {readiness:s.readiness||0.5, repair:s.repair_rate||0.5, sensor:s.sensor_confidence||0.5, uncertainty:s.uncertainty||0.35, reserve:ai46Clamp(0.55*(inv.offFrac||0.5)+0.45*(inv.defFrac||0.5)-0.15*(s.reserve_release||0),0,1), burn:s.stock_burn||0.4, morale:s.morale||0.5}; }); d.readiness = extras.length ? ai46Mean(extras.map(x=>x.readiness)) : 0.5; d.repair = extras.length ? ai46Mean(extras.map(x=>x.repair)) : 0.5; d.sensor = extras.length ? ai46Mean(extras.map(x=>x.sensor)) : 0.5; d.uncertainty = extras.length ? ai46Mean(extras.map(x=>x.uncertainty)) : 0.35; d.reserve = extras.length ? ai46Mean(extras.map(x=>x.reserve)) : 0.5; d.stockBurn = extras.length ? ai46Mean(extras.map(x=>x.burn)) : 0.4; d.morale = extras.length ? ai46Mean(extras.map(x=>x.morale)) : 0.5; return d; };
  window.ai33SideState = ai33SideState = function(side){ const info=sim32SideDetails(side); const fb=(AI33&&AI33.feedback&&AI33.feedback[side]) ? AI33.feedback[side] : {attacks:0,leaks:0,intercepts:0,shots:0}; return {root:info.root,countries:info.countries||[],score:info.score||0.5,offense:info.off||0.5,defense:info.de||0.5,logistics:info.log||0.5,c2:info.c2||0.5,kill_chain:info.kc||0.5,stress:info.stress||0.5,readiness:info.readiness||0.5,repair_rate:info.repair||0.5,sensor_confidence:info.sensor||0.5,uncertainty:info.uncertainty||0.35,reserve:info.reserve||0.5,stock_burn:info.stockBurn||0.4,morale:info.morale||0.5,attack_effectiveness: fb.attacks ? ai46Clamp(1 - (fb.leaks / Math.max(1, fb.attacks)), 0, 1) : 0.5,defense_effectiveness: fb.shots ? ai46Clamp(fb.intercepts / Math.max(1, fb.shots), 0, 1) : 0.5,leakage_rate: fb.attacks ? ai46Clamp(fb.leaks / Math.max(1, fb.attacks), 0, 1) : 0.5}; };
  const _ai33ApplyGlobal_v46_prev = (typeof ai33ApplyGlobal==='function' ? ai33ApplyGlobal : function(){});
  window.ai33ApplyGlobal = ai33ApplyGlobal = function(){ _ai33ApplyGlobal_v46_prev(); const g=(AI33.plan&&AI33.plan.global)||{}; SIM32.aiUncertaintyTolerance = ai46Clamp(g.uncertainty_tolerance!=null ? g.uncertainty_tolerance : 0.35, 0, 1); };
  function ai46Plan(side){ return (typeof ai33GetSidePlan==='function') ? (ai33GetSidePlan(side)||{}) : {}; }
  function ai46TickCountry(country, side, dtSec){ const st=getCountryState(country); if(!st) return; const ai=ai46EnsureCountryState(country); if(!ai) return; const plan=ai46Plan(side); const inv=ai46InventoryTotals(country); const reserveState=ai46Clamp(0.55*(inv.offFrac||0.5)+0.45*(inv.defFrac||0.5)-0.15*(ai.reserve_release||0),0,1); const sideStats=sim32SideDetails(side); const fatigue = dtSec * (0.002 + 0.004*(plan.aggression||1) + 0.003*(plan.stockpile_burn||0.4) + 0.002*(sideStats.stress||0)); const repairGain = dtSec * (0.003 + 0.006*(plan.repair_priority||0.5) + 0.004*(plan.logistics_push||0.5)) * (0.75 + 0.4*(ai.repair_rate||0.5)); const floor = ai46Clamp(0.20 + 0.50*(plan.readiness_floor||0.45), 0.18, 0.82); ai.readiness = ai46Clamp(ai.readiness + repairGain - fatigue, floor, 1.05); ai.sensor_confidence = ai46Clamp(ai.sensor_confidence + dtSec*(0.004 + 0.006*(plan.sensor_focus||0.5) + 0.002*(plan.deception_budget||0.2) - 0.006*(ai.uncertainty||0.3) - 0.004*(sideStats.stress||0)), 0.10, 1.00); const uncertaintyDrift = dtSec*(0.003 + 0.006*(plan.uncertainty_bias||0.3) + 0.004*(1-ai.sensor_confidence) + 0.004*(1-reserveState) - 0.004*(AI33&&AI33.plan&&AI33.plan.global ? (AI33.plan.global.uncertainty_tolerance||0.3) : 0.3)); ai.uncertainty = ai46Clamp(ai.uncertainty + uncertaintyDrift, 0.04, 0.95); ai.reserve_release = ai46Clamp(ai.reserve_release + dtSec*(0.005*(plan.reserve_commitment||0.4) + 0.003*(sideStats.pressure||0.3) - 0.002*reserveState), 0, 1); ai.stock_burn = ai46Clamp((ai.stock_burn||0.4)*0.92 + 0.08*ai46Clamp(plan.stockpile_burn!=null ? plan.stockpile_burn : 0.4, 0, 1), 0, 1); ai.repair_rate = ai46Clamp(ai.repair_rate*0.97 + 0.03*ai46Clamp(0.35 + 0.55*(plan.logistics_push||0.5),0,1), 0.05, 1.0); ai.morale = ai46Clamp(ai.morale + dtSec*(0.002*(ai.readiness-0.5) - 0.003*(sideStats.stress||0) - 0.002*(1-reserveState) + 0.0015*(plan.aggression||1)), 0.15, 1.0); st.doctrine = st.doctrine || {}; st.doctrine.maintenance = ai46Clamp(0.52 + 0.30*ai.readiness + 0.10*(plan.repair_priority||0.5), 0.35, 1.05); st.doctrine.training = ai46Clamp(0.54 + 0.26*ai.readiness + 0.08*ai.morale, 0.35, 1.05); st.doctrine.sensorFusion = ai46Clamp(0.46 + 0.40*ai.sensor_confidence - 0.10*ai.uncertainty + 0.06*(plan.sensor_focus||0.5), 0.20, 1.05); st.doctrine.shotDiscipline = ai46Clamp(0.46 + 0.26*(plan.shot_discipline||0.6) + 0.14*ai.readiness - 0.12*ai.uncertainty, 0.20, 1.05); st.doctrine.reloadElasticity = ai46Clamp(0.40 + 0.28*(plan.logistics_push||0.5) + 0.18*ai.readiness - 0.08*ai.uncertainty, 0.20, 1.10); st.doctrine.raidCapacityNorm = ai46Clamp(0.44 + 0.24*(plan.defense_posture||0.5) + 0.18*ai.sensor_confidence + 0.08*ai.readiness, 0.20, 1.10); st.doctrine.c2 = ai46Clamp(0.48 + 0.24*ai.readiness + 0.20*ai.sensor_confidence - 0.12*ai.uncertainty, 0.20, 1.05); st.doctrine.concurrentChannels = Math.max(2, Math.round(2 + 5*(0.40 + 0.35*ai.sensor_confidence + 0.15*(plan.defense_posture||0.5) + 0.10*ai.readiness))); const replenPulse = dtSec * (0.010 + 0.018*(plan.repair_priority||0.5) + 0.012*(plan.logistics_push||0.5)); ai.lastRepairTick = (ai.lastRepairTick||0) + replenPulse; if(ai.lastRepairTick > 1.0){ ai.lastRepairTick = 0; const pickPool = (inv.defFrac < inv.offFrac ? Object.values(st.defense||{}) : Object.values(st.offense||{})).filter(e=>e && e.remaining < e.initial); const pick = pickPool.sort((a,b)=>(a.remaining/a.initial)-(b.remaining/b.initial))[0]; if(pick) pick.remaining = Math.min(pick.initial, pick.remaining + 1); } }
  function ai46WeaveCampaign(dtSec){ ['A','B'].forEach(side=>((SIM32.sides[side]||[]).filter(Boolean)).forEach(country=>ai46TickCountry(country, side, dtSec))); }
  const _sim32Tick_v46_prev = window.sim32Tick || (typeof sim32Tick!=='undefined' ? sim32Tick : function(){});
  window.sim32Tick = sim32Tick = function(){ _sim32Tick_v46_prev(); if(AI33.enabled && SIM32.active){ const now=(typeof sim32Now==='function') ? sim32Now() : Date.now(); const prev=AI33.lastWeaveAt || now; const dtSec=ai46Clamp((now-prev)/1000, 0.02, 1.5); AI33.lastWeaveAt = now; ai46WeaveCampaign(dtSec); } };
  const _sim32PickWeapon_v46_prev = window.sim32PickWeapon || (typeof sim32PickWeapon!=='undefined' ? sim32PickWeapon : function(){ return null; });
  window.sim32PickWeapon = sim32PickWeapon = function(country, enemyCountry, rolePressure){ let chosen=_sim32PickWeapon_v46_prev(country, enemyCountry, rolePressure); const pool=(typeof sim32WeaponPool==='function') ? sim32WeaponPool(country) : []; const side=ai46SideOfCountry(country), plan=ai46Plan(side), state=ai46EnsureCountryState(country), st=(typeof getCountryState==='function') ? getCountryState(country) : null; if(!AI33.enabled || !pool.length || !state || !st) return chosen; const burn=ai46Clamp(plan.stockpile_burn!=null ? plan.stockpile_burn : state.stock_burn, 0, 1); const reserveCommit=ai46Clamp(plan.reserve_commitment!=null ? plan.reserve_commitment : state.reserve_release, 0, 1); const aggression=ai46Clamp((plan.aggression||1)-0.5, 0, 1.3); const ranked=pool.slice().sort((a,b)=>{ const ea=(st.offense&&st.offense[a.name])||{}, eb=(st.offense&&st.offense[b.name])||{}; const af=ea.initial ? ea.remaining/ea.initial : 0.5, bf=eb.initial ? eb.remaining/eb.initial : 0.5; const ar=(ea.reliability!=null?ea.reliability:0.8), br=(eb.reliability!=null?eb.reliability:0.8); const ak=((a.mach||1)*(0.55 + 0.45*(a.evasion||0.4))), bk=((b.mach||1)*(0.55 + 0.45*(b.evasion||0.4))); const as=(typeof sim32StrategicEligible==='function' && sim32StrategicEligible(a)) ? 1 : 0; const bs=(typeof sim32StrategicEligible==='function' && sim32StrategicEligible(b)) ? 1 : 0; const scoreA=(0.40 + 0.40*burn + 0.20*aggression)*ak + (0.25 + 0.35*(1-burn))*af + 0.18*ar - 0.28*(1-reserveCommit)*as; const scoreB=(0.40 + 0.40*burn + 0.20*aggression)*bk + (0.25 + 0.35*(1-burn))*bf + 0.18*br - 0.28*(1-reserveCommit)*bs; return scoreB-scoreA; }); return ranked[0] || chosen; };
  const _makeAttackObject_v46_prev = window.makeAttackObject || (typeof makeAttackObject!=='undefined' ? makeAttackObject : function(){ return null; });
  window.makeAttackObject = makeAttackObject = function(from,to,weapon,opts){ const p=_makeAttackObject_v46_prev(from,to,weapon,opts); if(!p) return p; const side=ai46SideOfCountry(p.attackerCountry), plan=ai46Plan(side), st=ai46EnsureCountryState(p.attackerCountry); if(AI33.enabled && st){ const quality = ai46Clamp(0.82 + 0.16*st.readiness + 0.08*(plan.deception_budget||0.2) - 0.12*st.uncertainty, 0.55, 1.12); p.systemReliability = ai46Clamp((p.systemReliability||0.82) * quality, 0.30, 0.995); p.evasiveness = ai46Clamp((p.evasiveness||0) + 0.10*(plan.deception_budget||0.2) - 0.05*st.uncertainty, 0, 1); p.aiLaunchQuality = quality; } return p; };
  const _projectile_updateScalarStep_v46_prev = Projectile.prototype.updateScalarStep;
  Projectile.prototype.updateScalarStep = function(){ if(this.alive && !this._ai46Bound){ const side=ai46SideOfCountry(this.attackerCountry), plan=ai46Plan(side), st=ai46EnsureCountryState(this.attackerCountry); if(AI33.enabled && st){ this.systemReliability = ai46Clamp((this.systemReliability||0.82) * (0.90 + 0.10*st.readiness + 0.05*(plan.shot_discipline||0.6) - 0.08*st.uncertainty), 0.30, 0.995); this.evasiveness = ai46Clamp((this.evasiveness||0) + 0.06*(plan.deception_budget||0.2) - 0.03*st.uncertainty, 0, 1); } this._ai46Bound=true; } return _projectile_updateScalarStep_v46_prev.call(this); };
  const _interceptor_updateScalarStep_v46_prev = Interceptor.prototype.updateScalarStep;
  Interceptor.prototype.updateScalarStep = function(){ if(!this._ai46Bound){ const side=ai46SideOfCountry(this.defenderCountry), plan=ai46Plan(side), st=ai46EnsureCountryState(this.defenderCountry); if(AI33.enabled && st){ this.sensorQuality = ai46Clamp((this.sensorQuality||0.65) * (0.88 + 0.16*st.sensor_confidence + 0.10*(plan.sensor_focus||0.5) - 0.10*st.uncertainty), 0.20, 0.995); this.pkBase = ai46Clamp((this.pkBase||0.45) * (0.90 + 0.10*st.readiness + 0.10*(plan.defense_posture||0.5) + 0.06*(plan.shot_discipline||0.6) - 0.10*st.uncertainty), 0.03, 0.995); this.launchDelay = Math.max(0, (this.launchDelay||0) * (1.10 - 0.20*(plan.defense_posture||0.5) - 0.12*(plan.sensor_focus||0.5) + 0.18*st.uncertainty)); } this._ai46Bound=true; } return _interceptor_updateScalarStep_v46_prev.call(this); };
  const _registerAttackOutcome_v46_prev = window.registerAttackOutcome || (typeof registerAttackOutcome!=='undefined' ? registerAttackOutcome : function(){});
  window.registerAttackOutcome = registerAttackOutcome = function(p){ _registerAttackOutcome_v46_prev(p); if(!p) return; AI33.feedback = AI33.feedback || {A:{attacks:0,leaks:0,intercepts:0,shots:0},B:{attacks:0,leaks:0,intercepts:0,shots:0}}; const atk=ai46SideOfCountry(p.attackerCountry), def=ai46SideOfCountry(p.defenderCountry); if(atk && AI33.feedback[atk]){ AI33.feedback[atk].attacks += 1; if(!p.intercepted) AI33.feedback[atk].leaks += 1; } if(def && AI33.feedback[def] && p.intercepted){ AI33.feedback[def].intercepts += 1; } };
  const _registerInterceptorOutcome_v46_prev = window.registerInterceptorOutcome || (typeof registerInterceptorOutcome!=='undefined' ? registerInterceptorOutcome : function(){});
  window.registerInterceptorOutcome = registerInterceptorOutcome = function(i){ _registerInterceptorOutcome_v46_prev(i); AI33.feedback = AI33.feedback || {A:{attacks:0,leaks:0,intercepts:0,shots:0},B:{attacks:0,leaks:0,intercepts:0,shots:0}}; const side=ai46SideOfCountry(i&&i.defenderCountry); if(side && AI33.feedback[side]){ AI33.feedback[side].shots += 1; if(i && i.hit) AI33.feedback[side].intercepts += 1; } };
  const _sim32UpdateRoom_v46_prev = window.sim32UpdateRoom || (typeof sim32UpdateRoom!=='undefined' ? sim32UpdateRoom : function(){});
  window.sim32UpdateRoom = sim32UpdateRoom = function(){ _sim32UpdateRoom_v46_prev(); const room=$('warRoom32'); if(!room || !SIM32.active) return; const A=sim32SideDetails('A'), B=sim32SideDetails('B'); const card=(side,d)=>`<div class="war-card"><div class="k">AI weave side ${side}</div><div class="war-mini"><span>reserve ${sim32Pct(d.reserve||0)}%</span><span>readiness ${sim32Pct(d.readiness||0)}%</span></div><div class="war-mini"><span>sensor ${sim32Pct(d.sensor||0)}%</span><span>uncertainty ${sim32Pct(d.uncertainty||0)}%</span></div><div class="war-mini"><span>repair ${sim32Pct(d.repair||0)}%</span><span>burn ${sim32Pct(d.stockBurn||0)}%</span></div><div class="war-mini"><span>morale ${sim32Pct(d.morale||0)}%</span><span>${escapeHtml(((ai33GetSidePlan(side)||{}).target_priority||'weakest'))}</span></div></div>`; room.innerHTML += `<div class="war-row" style="margin-top:8px">${card('A',A)}${card('B',B)}</div>`; };
})();
</script>
'''

EXTRA_V47_JS = r'''
<script>
(function(){
  function ai47Clamp(v,a,b){ return (typeof sim32Clamp==='function') ? sim32Clamp(v,a,b) : Math.max(a, Math.min(b, Number(v)||0)); }
  function ai47Wilson(success,total,z){ total=Math.max(0,+total||0); success=Math.max(0,Math.min(total,+success||0)); if(!total) return {p:0.5, lo:0.0, hi:1.0}; z=(+z||1.64); const ph=success/total, d=1+(z*z)/total, c=(ph + (z*z)/(2*total))/d, h=(z*Math.sqrt((ph*(1-ph)/total) + (z*z)/(4*total*total)))/d; return {p:ph, lo:Math.max(0,c-h), hi:Math.min(1,c+h)}; }
  function ai47Stock(country){ return (typeof ai46InventoryTotals==='function') ? ai46InventoryTotals(country) : {offRem:0,offInit:0,defRem:0,defInit:0,offFrac:0.5,defFrac:0.5}; }
  function ai47EnsureFB(){
    var mk=()=>({attacks:0, leaks:0, shots:0, intercepts:0, attackWins:0, impacts:0, recentAttacks:[], recentDefense:[], calibExpected:0, calibObserved:0, calibCount:0, doctrineDelta:0});
    window.AI33 = window.AI33 || {};
    AI33.feedback = AI33.feedback || {A:mk(), B:mk()};
    ['A','B'].forEach(function(side){
      var fb=AI33.feedback[side]||{}; var base=mk(); Object.keys(base).forEach(function(k){ if(fb[k]==null) fb[k]=base[k]; }); AI33.feedback[side]=fb;
    });
    return AI33.feedback;
  }
  function ai47Push(arr, val, maxLen){ arr=arr||[]; arr.push(val); while(arr.length>(maxLen||18)) arr.shift(); return arr; }
  function ai47Mean(arr){ return arr&&arr.length ? arr.reduce((s,v)=>s+(+v||0),0)/arr.length : 0; }
  function ai47SideOfCountry(country){ return (typeof ai46SideOfCountry==='function') ? ai46SideOfCountry(country) : (((SIM32.sides.A||[]).includes(country))?'A':(((SIM32.sides.B||[]).includes(country))?'B':'')); }
  function ai47OutcomeNudge(country, mode, amount){
    if(!country || typeof getCountryState!=='function' || typeof ai46EnsureCountryState!=='function') return;
    const st=getCountryState(country), ai=ai46EnsureCountryState(country); if(!st || !ai) return;
    const a=ai47Clamp(amount||0, 0, 0.2); st.doctrine = st.doctrine || {};
    if(mode==='attack_success'){ ai.morale=ai47Clamp(ai.morale + 0.08*a, 0.15, 1); ai.readiness=ai47Clamp(ai.readiness + 0.05*a, 0.18, 1.05); ai.uncertainty=ai47Clamp(ai.uncertainty - 0.05*a, 0.04, 0.95); }
    else if(mode==='attack_fail'){ ai.uncertainty=ai47Clamp(ai.uncertainty + 0.08*a, 0.04, 0.95); ai.morale=ai47Clamp(ai.morale - 0.05*a, 0.15, 1); }
    else if(mode==='defense_success'){ ai.sensor_confidence=ai47Clamp(ai.sensor_confidence + 0.08*a, 0.1, 1); ai.morale=ai47Clamp(ai.morale + 0.05*a, 0.15, 1); ai.uncertainty=ai47Clamp(ai.uncertainty - 0.05*a, 0.04, 0.95); }
    else if(mode==='defense_fail'){ ai.sensor_confidence=ai47Clamp(ai.sensor_confidence - 0.06*a, 0.1, 1); ai.uncertainty=ai47Clamp(ai.uncertainty + 0.08*a, 0.04, 0.95); ai.morale=ai47Clamp(ai.morale - 0.04*a, 0.15, 1); }
    st.doctrine.sensorFusion = ai47Clamp((st.doctrine.sensorFusion!=null?st.doctrine.sensorFusion:0.6)*0.96 + 0.04*ai.sensor_confidence, 0.2, 1.05);
    st.doctrine.training = ai47Clamp((st.doctrine.training!=null?st.doctrine.training:0.6)*0.97 + 0.03*ai.readiness, 0.2, 1.05);
    st.doctrine.shotDiscipline = ai47Clamp((st.doctrine.shotDiscipline!=null?st.doctrine.shotDiscipline:0.6)*0.96 + 0.04*(1-ai.uncertainty), 0.2, 1.05);
  }
  function ai47SideSummary(side){
    ai47EnsureFB();
    const info=(typeof sim32SideDetails==='function') ? sim32SideDetails(side) : {};
    const fb=AI33.feedback[side];
    const countries=(info.countries||[]).filter(Boolean);
    const inv=countries.reduce((acc,c)=>{ const t=ai47Stock(c); acc.offRem+=t.offRem||0; acc.offInit+=t.offInit||0; acc.defRem+=t.defRem||0; acc.defInit+=t.defInit||0; return acc; }, {offRem:0,offInit:0,defRem:0,defInit:0});
    const leakCI=ai47Wilson(fb.leaks, fb.attacks, 1.64), defCI=ai47Wilson(fb.intercepts, fb.shots, 1.64);
    const calErr = fb.calibCount ? Math.abs((fb.calibObserved/fb.calibCount) - (fb.calibExpected/fb.calibCount)) : 0;
    return {
      attacks:fb.attacks, leaks:fb.leaks, shots:fb.shots, intercepts:fb.intercepts,
      leakRate: leakCI.p, leakLo: leakCI.lo, leakHi: leakCI.hi,
      defenseRate: defCI.p, defenseLo: defCI.lo, defenseHi: defCI.hi,
      rollingLeak: ai47Mean(fb.recentAttacks), rollingDefense: ai47Mean(fb.recentDefense),
      calibrationError: calErr,
      stockOffFrac: inv.offInit?inv.offRem/inv.offInit:0.5,
      stockDefFrac: inv.defInit?inv.defRem/inv.defInit:0.5,
      offRem:inv.offRem, offInit:inv.offInit, defRem:inv.defRem, defInit:inv.defInit,
      readiness: info.readiness||0.5, sensor: info.sensor||0.5, uncertainty: info.uncertainty||0.35, reserve: info.reserve||0.5, morale: info.morale||0.5, repair: info.repair||0.5, burn: info.stockBurn||0.4
    };
  }
  const _resetCampaignState_v47_prev = window.resetCampaignState || (typeof resetCampaignState!=='undefined' ? resetCampaignState : function(){});
  window.resetCampaignState = resetCampaignState = function(){ _resetCampaignState_v47_prev(); ai47EnsureFB(); AI33.lastWeaveAt=0; };
  const _registerAttackOutcome_v47_prev = window.registerAttackOutcome || (typeof registerAttackOutcome!=='undefined' ? registerAttackOutcome : function(){});
  window.registerAttackOutcome = registerAttackOutcome = function(p){
    _registerAttackOutcome_v47_prev(p); if(!p) return; ai47EnsureFB();
    const atk=ai47SideOfCountry(p.attackerCountry), def=ai47SideOfCountry(p.defenderCountry);
    const sev=ai47Clamp((((p.getMach&&p.getMach()) || p.cmdMach || 6)/25) * (p.systemReliability||0.82), 0.03, 0.18);
    if(atk && AI33.feedback[atk]){ const fb=AI33.feedback[atk]; fb.attacks += 1; if(!p.intercepted){ fb.leaks += 1; fb.attackWins += 1; fb.recentAttacks = ai47Push(fb.recentAttacks, 1, 20); } else { fb.recentAttacks = ai47Push(fb.recentAttacks, 0, 20); } }
    if(def && AI33.feedback[def] && !p.intercepted){ const fb=AI33.feedback[def]; fb.impacts += 1; }
    if(!p.intercepted){ ai47OutcomeNudge(p.attackerCountry, 'attack_success', sev); ai47OutcomeNudge(p.defenderCountry, 'defense_fail', sev); }
    else { ai47OutcomeNudge(p.attackerCountry, 'attack_fail', sev); }
  };
  const _registerInterceptorOutcome_v47_prev = window.registerInterceptorOutcome || (typeof registerInterceptorOutcome!=='undefined' ? registerInterceptorOutcome : function(){});
  window.registerInterceptorOutcome = registerInterceptorOutcome = function(i){
    _registerInterceptorOutcome_v47_prev(i); ai47EnsureFB(); const side=ai47SideOfCountry(i&&i.defenderCountry); if(!side || !AI33.feedback[side]) return; const fb=AI33.feedback[side];
    const pkEst = ai47Clamp(i && (i.pkNow!=null ? i.pkNow : ((i.pkBase||0.45) * (i.sensorQuality||0.65))), 0, 1);
    fb.shots += 1; fb.calibExpected += pkEst; fb.calibObserved += (i&&i.hit)?1:0; fb.calibCount += 1;
    if(i&&i.hit){ fb.intercepts += 1; fb.recentDefense = ai47Push(fb.recentDefense, 1, 20); ai47OutcomeNudge(i.defenderCountry, 'defense_success', ai47Clamp(pkEst,0.03,0.16)); }
    else { fb.recentDefense = ai47Push(fb.recentDefense, 0, 20); ai47OutcomeNudge(i&&i.defenderCountry, 'defense_fail', ai47Clamp(1-pkEst,0.03,0.16)); }
  };
  window.ai33SideState = ai33SideState = function(side){
    const info=(typeof sim32SideDetails==='function') ? sim32SideDetails(side) : {root:'',countries:[],score:0.5,off:0.5,de:0.5,log:0.5,c2:0.5,kc:0.5,stress:0.5};
    const s=ai47SideSummary(side);
    return {root:info.root,countries:info.countries||[],score:info.score||0.5,offense:info.off||0.5,defense:info.de||0.5,logistics:info.log||0.5,c2:info.c2||0.5,kill_chain:info.kc||0.5,stress:info.stress||0.5,readiness:s.readiness,repair_rate:s.repair,sensor_confidence:s.sensor,uncertainty:s.uncertainty,reserve:s.reserve,stock_burn:s.burn,morale:s.morale,attack_effectiveness:1-s.leakRate,defense_effectiveness:s.defenseRate,leakage_rate:s.leakRate,rolling_leak_rate:s.rollingLeak,rolling_defense_rate:s.rollingDefense,calibration_error:s.calibrationError,stock_off_frac:s.stockOffFrac,stock_def_frac:s.stockDefFrac,stock_off_remaining:s.offRem,stock_off_initial:s.offInit,stock_def_remaining:s.defRem,stock_def_initial:s.defInit,attacks:s.attacks,shots:s.shots};
  };
  window.ai33Payload = ai33Payload = function(){
    const bal=typeof sim32FrontBalance==='function' ? sim32FrontBalance() : {aP:0.5,bP:0.5,delta:0};
    const A=ai33SideState('A'), B=ai33SideState('B');
    return {ts: Date.now(),mode: SIM32.mode||'duel',allow_nukes: !!SIM32.allowNukes,escalation: +SIM32.escalation||0,sideA:A,sideB:B,forecast:{a:bal.aP||0.5,b:bal.bP||0.5,delta:bal.delta||0},recent_history:(SIM32.history||[]).slice(-10),launches:+SIM32.launchCount||0,cycle:+SIM32.cycle||0,feedback_summary:{A:{attacks:A.attacks||0,leakRate:A.leakage_rate||0,defenseRate:A.defense_effectiveness||0,calibration:A.calibration_error||0,stockOff:A.stock_off_frac||0.5,stockDef:A.stock_def_frac||0.5},B:{attacks:B.attacks||0,leakRate:B.leakage_rate||0,defenseRate:B.defense_effectiveness||0,calibration:B.calibration_error||0,stockOff:B.stock_off_frac||0.5,stockDef:B.stock_def_frac||0.5}},objective: $('aiDirectiveObj') ? $('aiDirectiveObj').value : 'Blend reserves, readiness, repair, fog-of-war, and statistical memory for coherent fictional gameplay.'};
  };
  function ai47FmtBand(lo,hi){ return Math.round((lo||0)*100)+'-'+Math.round((hi||0)*100)+'%'; }
  function ai47InjectPanel(){
    if($('aiCampaignPanel')) return; const parent=document.querySelector('.stack:last-child') || document.querySelector('.stack'); if(!parent) return;
    const panel=document.createElement('div'); panel.className='pnl'; panel.id='aiCampaignPanel';
    panel.innerHTML='<h3>AI CAMPAIGN MEMORY</h3><div class="hint" style="margin-bottom:8px">Rolling memory for stockpiles, leakage, defense confidence, and calibration drift. This lets the director learn from synthetic outcomes instead of one-shot guesses.</div><div id="aiCampaignBody" class="preview-note"><b>Awaiting battle data.</b></div>';
    parent.insertBefore(panel, $('aiDirectorPanel') ? $('aiDirectorPanel').nextSibling : (parent.children[2]||null));
  }
  function ai47Card(side, s){
    const plan=(typeof ai33GetSidePlan==='function') ? (ai33GetSidePlan(side)||{}) : {};
    return '<div class="war-card"><div class="k">Side '+side+' campaign state</div>'+
      '<div class="war-mini"><span>off '+Math.round(s.offRem)+'/'+Math.round(s.offInit||0)+'</span><span>def '+Math.round(s.defRem)+'/'+Math.round(s.defInit||0)+'</span></div>'+
      '<div class="war-mini"><span>reserve '+Math.round((s.reserve||0)*100)+'%</span><span>burn '+Math.round((s.burn||0)*100)+'%</span></div>'+
      '<div class="war-mini"><span>leak '+Math.round((s.leakRate||0)*100)+'%</span><span>band '+ai47FmtBand(s.leakLo,s.leakHi)+'</span></div>'+
      '<div class="war-mini"><span>defense '+Math.round((s.defenseRate||0)*100)+'%</span><span>band '+ai47FmtBand(s.defenseLo,s.defenseHi)+'</span></div>'+
      '<div class="war-mini"><span>rolling leak '+Math.round((s.rollingLeak||0)*100)+'%</span><span>rolling defense '+Math.round((s.rollingDefense||0)*100)+'%</span></div>'+
      '<div class="war-mini"><span>readiness '+Math.round((s.readiness||0)*100)+'%</span><span>sensor '+Math.round((s.sensor||0)*100)+'%</span></div>'+
      '<div class="war-mini"><span>uncertainty '+Math.round((s.uncertainty||0)*100)+'%</span><span>cal drift '+Math.round((s.calibrationError||0)*100)+'%</span></div>'+
      '<div class="war-mini"><span>morale '+Math.round((s.morale||0)*100)+'%</span><span>'+escapeHtml((plan.target_priority||'weakest'))+'</span></div></div>';
  }
  function ai47UpdatePanel(){
    const box=$('aiCampaignBody'); if(!box) return; const A=ai47SideSummary('A'), B=ai47SideSummary('B');
    box.innerHTML='<div class="war-row">'+ai47Card('A',A)+ai47Card('B',B)+'</div>';
    const status=$('aiDirectorStatus');
    if(status){
      const src=((AI33.plan||{})._source)||((AI33.cfg&&AI33.cfg.configured)?'openai':'fallback');
      status.innerHTML='<b>AI STATUS</b><br>'+(AI33.busy ? 'Consulting director...' : (AI33.enabled ? 'Director armed.' : 'Director idle.'))+
        '<br><span class="mini">source: '+escapeHtml(src)+' • last pulse: '+(AI33.lastCall?Math.round((Date.now()-AI33.lastCall)/1000)+'s ago':'never')+'</span>'+
        '<br><span class="mini">A off '+Math.round(A.offRem)+'/'+Math.round(A.offInit||0)+' • def '+Math.round(A.defRem)+'/'+Math.round(A.defInit||0)+' • leak '+Math.round((A.leakRate||0)*100)+'%</span>'+
        '<br><span class="mini">B off '+Math.round(B.offRem)+'/'+Math.round(B.offInit||0)+' • def '+Math.round(B.defRem)+'/'+Math.round(B.defInit||0)+' • leak '+Math.round((B.leakRate||0)*100)+'%</span>'+
        '<br><span class="mini">'+escapeHtml((AI33.plan&&AI33.plan.summary)||'No plan yet.')+'</span>'+
        ((AI33.plan&&AI33.plan.narrative)?'<br><span class="mini">'+escapeHtml(AI33.plan.narrative)+'</span>':'');
    }
  }
  const _sim32UpdateRoom_v47_prev = window.sim32UpdateRoom || (typeof sim32UpdateRoom!=='undefined' ? sim32UpdateRoom : function(){});
  window.sim32UpdateRoom = sim32UpdateRoom = function(){ _sim32UpdateRoom_v47_prev(); ai47UpdatePanel(); };
  window.addEventListener('load', function(){ setTimeout(ai47EnsureFB, 120); setTimeout(ai47InjectPanel, 220); setTimeout(ai47UpdatePanel, 480); });
})();
</script>
'''


LOCAL_GEOCODE, PLACE_SEED, PLACE_OPTIONS = build_place_seed()
FRONTEND_SEED = [item for item in PLACE_SEED if "lat" in item and "lon" in item]
HTML = HTML_TEMPLATE.replace(
    "__DATALIST_OPTIONS__",
    "\n".join(f'<option value="{html.escape(v, quote=True)}"></option>' for v in PLACE_OPTIONS),
).replace("__PLACE_SEED_JSON__", json.dumps(FRONTEND_SEED)).replace("</body>", EXTRA_V26_JS + EXTRA_V27_JS + EXTRA_V28_JS + EXTRA_V29_JS + EXTRA_V30_JS + EXTRA_V31_JS + EXTRA_V33_JS + EXTRA_V46_JS + EXTRA_V47_JS + "\n</body>")


class Geocoder:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()
        self.last_nominatim_call = 0.0

    def _parse_latlon(self, text: str):
        m = LATLON_RE.match((text or "").strip())
        if not m:
            return None
        lat = float(m.group(1))
        lon = float(m.group(2))
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        return {"name": f"{lat:.4f}, {lon:.4f}", "lat": lat, "lon": lon, "provider": "manual", "kind": "coordinates"}

    def _nominatim_search(self, query: str, limit: int):
        params = {
            "q": query,
            "format": "jsonv2",
            "limit": str(max(1, min(limit, 6))),
            "addressdetails": "1",
            "accept-language": "en",
        }
        url = NOMINATIM_URL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with self.lock:
            wait = 1.05 - (time.time() - self.last_nominatim_call)
            if wait > 0:
                time.sleep(wait)
            self.last_nominatim_call = time.time()
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self.last_nominatim_call = time.time()
        out = []
        for item in data:
            try:
                lat = float(item["lat"])
                lon = float(item["lon"])
            except Exception:
                continue
            name = item.get("display_name") or item.get("name") or query
            kind = item.get("type") or item.get("class") or "place"
            out.append({"name": name, "lat": lat, "lon": lon, "provider": "nominatim", "kind": kind})
        return out

    def resolve(self, query: str, limit: int = 1):
        query = (query or "").strip()
        if not query:
            return []
        cache_key = ("resolve", _norm_key(query), int(limit))
        if cache_key in self.cache:
            return self.cache[cache_key]
        direct = self._parse_latlon(query)
        if direct:
            result = [direct]
        elif _norm_key(query) in LOCAL_GEOCODE:
            result = [LOCAL_GEOCODE[_norm_key(query)]]
        elif _norm_key(query) in BUILTIN_GEOCODE:
            result = [BUILTIN_GEOCODE[_norm_key(query)]]
        else:
            key = _norm_key(query)
            local_hits = []
            for item in PLACE_SEED:
                nm = _norm_key(item.get("name", ""))
                if key and (nm.startswith(key) or key in nm):
                    local_hits.append(item)
                if len(local_hits) >= max(3, limit):
                    break
            try:
                remote_hits = self._nominatim_search(query, limit=max(1, min(limit, 6))) if len(query) >= 2 else []
            except Exception:
                remote_hits = []
            seen = set()
            result = []
            for item in local_hits + remote_hits:
                nm = _norm_key(item.get("name", ""))
                if nm and nm not in seen:
                    seen.add(nm)
                    result.append(item)
            result = result[: max(1, min(limit, 8))]
        self.cache[cache_key] = result
        return result

    def suggest(self, query: str, limit: int = 5):
        query = (query or "").strip()
        if not query:
            return []
        cache_key = ("suggest", _norm_key(query), int(limit))
        if cache_key in self.cache:
            return self.cache[cache_key]
        direct = self._parse_latlon(query)
        if direct:
            result = [direct]
        else:
            key = _norm_key(query)
            local_hits = []
            for item in PLACE_SEED:
                nm = _norm_key(item.get("name", ""))
                if key and (nm.startswith(key) or key in nm):
                    local_hits.append(item)
                if len(local_hits) >= max(4, limit):
                    break
            try:
                remote_hits = self._nominatim_search(query, limit=max(1, min(limit, 6)))
            except Exception:
                remote_hits = []
            seen = set()
            result = []
            for item in local_hits + remote_hits:
                nm = _norm_key(item.get("name", ""))
                if nm and nm not in seen:
                    seen.add(nm)
                    result.append(item)
            result = result[: max(1, min(limit, 8))]
        self.cache[cache_key] = result
        return result


GAME_AI_CONFIG_TEMPLATE = {
    "enabled": True,
    "provider": "openai",
    "model": "gpt-5.4",
    "api_key_env_var": "OPENAI_API_KEY",
    "responses_api_url": "https://api.openai.com/v1/responses",
    "director": {
        "system_prompt": "You are a strategic game director for a fictional multi-domain war game. Keep outputs game-focused, concise, and numerical. Do not give real-world operational advice. Return JSON only.",
        "max_output_tokens": 500,
        "temperature": 0.6,
        "cadence_seconds": 12
    }
}


def ensure_game_ai_config_files(base_dir: str):
    cfg_path = os.path.join(base_dir, 'openai_game_config.json')
    template_path = os.path.join(base_dir, 'openai_game_config.template.json')
    env_example = os.path.join(base_dir, '.env.example')
    if not os.path.exists(template_path):
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(GAME_AI_CONFIG_TEMPLATE, f, indent=2)
    if not os.path.exists(env_example):
        with open(env_example, 'w', encoding='utf-8') as f:
            f.write('OPENAI_API_KEY=put_your_key_here\n')
    return cfg_path


def load_game_ai_config(base_dir: str):
    cfg = json.loads(json.dumps(GAME_AI_CONFIG_TEMPLATE))
    cfg_path = os.path.join(base_dir, 'openai_game_config.json')
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                        cfg[k].update(v)
                    else:
                        cfg[k] = v
        except Exception:
            pass
    return cfg


def _load_dotenv_if_present(base_dir: str):
    env_path = os.path.join(base_dir, '.env')
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


def resolve_game_ai_key(cfg: dict, base_dir: str):
    _load_dotenv_if_present(base_dir)
    env_name = (cfg or {}).get('api_key_env_var') or 'OPENAI_API_KEY'
    env_key = os.environ.get(env_name) or os.environ.get('OPENAI_API_KEY')
    if env_key:
        return env_key.strip(), 'env'
    return '', 'missing'


def _extract_json_object(text: str):
    text = (text or '').strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


def _bounded_float(value, default, low, high):
    try:
        v = float(value)
    except Exception:
        v = float(default)
    if v != v:
        v = float(default)
    return max(float(low), min(float(high), v))


def _normalize_priority(value, default='weakest'):
    allowed = {'weakest', 'strongest', 'capital', 'highest_pressure', 'closest'}
    value = str(value or default).strip().lower()
    return value if value in allowed else default


def _side_pressure(side_payload: dict):
    side_payload = side_payload or {}
    offense = _bounded_float(side_payload.get('offense'), 0.5, 0.0, 1.2)
    defense = _bounded_float(side_payload.get('defense'), 0.5, 0.0, 1.2)
    logistics = _bounded_float(side_payload.get('logistics'), 0.5, 0.0, 1.2)
    c2 = _bounded_float(side_payload.get('c2'), 0.5, 0.0, 1.2)
    kill_chain = _bounded_float(side_payload.get('kill_chain'), 0.5, 0.0, 1.2)
    stress = _bounded_float(side_payload.get('stress'), 0.3, 0.0, 1.2)
    readiness = _bounded_float(side_payload.get('readiness'), 0.64, 0.0, 1.2)
    reserve = _bounded_float(side_payload.get('reserve'), 0.55, 0.0, 1.0)
    uncertainty = _bounded_float(side_payload.get('uncertainty'), 0.34, 0.0, 1.0)
    repair_rate = _bounded_float(side_payload.get('repair_rate'), 0.52, 0.0, 1.0)
    sensor_confidence = _bounded_float(side_payload.get('sensor_confidence'), 0.62, 0.0, 1.2)
    stock_burn = _bounded_float(side_payload.get('stock_burn'), 0.45, 0.0, 1.0)
    attack_effectiveness = _bounded_float(side_payload.get('attack_effectiveness'), 0.5, 0.0, 1.0)
    defense_effectiveness = _bounded_float(side_payload.get('defense_effectiveness'), 0.5, 0.0, 1.0)
    leakage_rate = _bounded_float(side_payload.get('leakage_rate'), 0.5, 0.0, 1.0)
    calibration_error = _bounded_float(side_payload.get('calibration_error'), 0.18, 0.0, 1.0)
    stock_off_frac = _bounded_float(side_payload.get('stock_off_frac'), reserve, 0.0, 1.0)
    stock_def_frac = _bounded_float(side_payload.get('stock_def_frac'), reserve, 0.0, 1.0)
    pressure = max(0.0, min(1.2,
        0.20 * (1.0 - offense) + 0.20 * (1.0 - defense) + 0.14 * (1.0 - logistics) + 0.10 * (1.0 - c2) +
        0.07 * (1.0 - kill_chain) + 0.08 * stress + 0.06 * (1.0 - readiness) + 0.05 * (1.0 - reserve) +
        0.04 * uncertainty + 0.03 * leakage_rate + 0.02 * calibration_error + 0.01 * (1.0 - defense_effectiveness)
    ))
    strike_energy = max(0.0, min(1.2,
        0.30 * offense + 0.16 * kill_chain + 0.12 * c2 + 0.12 * logistics + 0.10 * readiness + 0.06 * sensor_confidence +
        0.05 * stock_burn + 0.05 * attack_effectiveness + 0.02 * stock_off_frac + 0.02 * (1.0 - leakage_rate)
    ))
    return {
        'pressure': pressure,
        'strike_energy': strike_energy,
        'stress': stress,
        'readiness': readiness,
        'reserve': reserve,
        'uncertainty': uncertainty,
        'repair_rate': repair_rate,
        'sensor_confidence': sensor_confidence,
        'stock_burn': stock_burn,
        'attack_effectiveness': attack_effectiveness,
        'defense_effectiveness': defense_effectiveness,
        'leakage_rate': leakage_rate,
        'calibration_error': calibration_error,
        'stock_off_frac': stock_off_frac,
        'stock_def_frac': stock_def_frac,
    }


def sanitize_ai_director_plan(plan: dict, payload: dict | None = None, source: str = 'fallback'):
    payload = payload or {}
    forecast = payload.get('forecast') or {}
    a_p = _bounded_float(forecast.get('a'), 0.5, 0.0, 1.0)
    b_p = _bounded_float(forecast.get('b'), 0.5, 0.0, 1.0)
    a_side = _side_pressure(payload.get('sideA') or {})
    b_side = _side_pressure(payload.get('sideB') or {})
    side_a_payload = payload.get('sideA') or {}
    side_b_payload = payload.get('sideB') or {}
    plan = plan if isinstance(plan, dict) else {}
    global_in = plan.get('global') or {}
    side_a_in = plan.get('sideA') or {}
    side_b_in = plan.get('sideB') or {}
    max_pressure = max(a_side['pressure'], b_side['pressure'])

    def _clean_side(side_in, side_payload, side_stats, own_p, enemy_p):
        reserve = _bounded_float(side_payload.get('reserve'), 0.55, 0.0, 1.0)
        readiness = _bounded_float(side_payload.get('readiness'), 0.64, 0.0, 1.2)
        sensor = _bounded_float(side_payload.get('sensor_confidence'), 0.62, 0.0, 1.2)
        uncertainty = _bounded_float(side_payload.get('uncertainty'), 0.34, 0.0, 1.0)
        repair = _bounded_float(side_payload.get('repair_rate'), 0.52, 0.0, 1.0)
        burn = _bounded_float(side_payload.get('stock_burn'), 0.50, 0.0, 1.0)
        losing = own_p < enemy_p
        return {
            'aggression': _bounded_float(side_in.get('aggression'), 0.90 + 0.20 * side_stats['strike_energy'] + 0.08 * side_stats['pressure'] - 0.08 * side_stats['stress'] + (0.04 if losing else -0.02), 0.5, 1.8),
            'defense_bias': _bounded_float(side_in.get('defense_bias'), 0.90 + 0.20 * side_stats['pressure'] + 0.08 * (1.0 - own_p) + 0.06 * uncertainty, 0.5, 1.8),
            'join_bias': _bounded_float(side_in.get('join_bias'), 0.95 + 0.18 * side_stats['pressure'] + (0.10 if losing else 0.0), 0.5, 1.8),
            'nuke_bias': _bounded_float(side_in.get('nuke_bias'), 0.80 + (0.14 if own_p < 0.32 else 0.0) + 0.06 * _bounded_float(payload.get('escalation'), 0, 0, 3), 0.5, 1.8),
            'target_priority': _normalize_priority(side_in.get('target_priority'), 'highest_pressure' if own_p < enemy_p else ('strongest' if side_stats['strike_energy'] > 0.72 else 'weakest')),
            'reserve_commitment': _bounded_float(side_in.get('reserve_commitment'), 0.40 + 0.32 * side_stats['pressure'] + 0.18 * (1.0 - reserve) + (0.08 if losing else 0.0), 0.0, 1.0),
            'logistics_push': _bounded_float(side_in.get('logistics_push'), 0.42 + 0.28 * repair + 0.16 * side_stats['pressure'] + 0.06 * burn, 0.0, 1.0),
            'repair_priority': _bounded_float(side_in.get('repair_priority'), 0.46 + 0.26 * (1.0 - readiness) + 0.18 * (1.0 - own_p), 0.0, 1.0),
            'sensor_focus': _bounded_float(side_in.get('sensor_focus'), 0.44 + 0.22 * (1.0 - sensor) + 0.10 * uncertainty + 0.08 * side_stats['pressure'] + 0.12 * side_stats['leakage_rate'] + 0.08 * side_stats['calibration_error'], 0.0, 1.0),
            'defense_posture': _bounded_float(side_in.get('defense_posture'), 0.40 + 0.24 * side_stats['pressure'] + 0.12 * uncertainty + 0.10 * side_stats['leakage_rate'] + 0.08 * (1.0 - side_stats['defense_effectiveness']) + (0.08 if losing else 0.0), 0.0, 1.0),
            'deception_budget': _bounded_float(side_in.get('deception_budget'), 0.28 + 0.18 * side_stats['strike_energy'] + 0.10 * uncertainty, 0.0, 1.0),
            'stockpile_burn': _bounded_float(side_in.get('stockpile_burn'), 0.30 + 0.22 * side_stats['strike_energy'] + 0.10 * (1.0 - reserve) + 0.08 * side_stats['attack_effectiveness'] - 0.08 * side_stats['stock_off_frac'], 0.0, 1.0),
            'shot_discipline': _bounded_float(side_in.get('shot_discipline'), 0.54 + 0.16 * readiness - 0.12 * uncertainty + 0.08 * sensor + 0.10 * side_stats['defense_effectiveness'] - 0.06 * side_stats['calibration_error'], 0.0, 1.0),
            'readiness_floor': _bounded_float(side_in.get('readiness_floor'), 0.42 + 0.24 * reserve + 0.10 * repair, 0.0, 1.0),
            'uncertainty_bias': _bounded_float(side_in.get('uncertainty_bias'), 0.34 + 0.22 * uncertainty - 0.10 * sensor, 0.0, 1.0),
        }

    clean = {
        'summary': str(plan.get('summary') or f"AI {source} director active. Side A {round(a_p*100)}% vs Side B {round(b_p*100)}%.")[:260],
        'narrative': str(plan.get('narrative') or 'Gameplay steering kept bounded and internally consistent.')[:420],
        'global': {
            'tempo': _bounded_float(global_in.get('tempo'), 1.0 + min(0.30, abs(a_p - b_p) * 0.55), 0.5, 1.8),
            'join_bias': _bounded_float(global_in.get('join_bias'), 1.05 + min(0.20, max_pressure * 0.25), 0.5, 1.8),
            'escalation_bias': _bounded_float(global_in.get('escalation_bias'), 1.0 + 0.12 * _bounded_float(payload.get('escalation'), 0, 0, 3), 0.5, 1.8),
            'ceasefire_bias': _bounded_float(global_in.get('ceasefire_bias'), 0.12 if abs(a_p - b_p) < 0.05 else 0.03, 0.0, 1.0),
            'uncertainty_tolerance': _bounded_float(global_in.get('uncertainty_tolerance'), 0.26 + 0.22 * max_pressure + 0.10 * abs(a_p - b_p), 0.0, 1.0),
        },
        'sideA': _clean_side(side_a_in, side_a_payload, a_side, a_p, b_p),
        'sideB': _clean_side(side_b_in, side_b_payload, b_side, b_p, a_p),
    }
    return clean


def default_ai_director_plan(payload: dict):
    payload = payload or {}
    forecast = payload.get('forecast') or {}
    a_p = _bounded_float(forecast.get('a'), 0.5, 0.0, 1.0)
    b_p = _bounded_float(forecast.get('b'), 0.5, 0.0, 1.0)
    delta = a_p - b_p
    a_side = _side_pressure(payload.get('sideA') or {})
    b_side = _side_pressure(payload.get('sideB') or {})
    side_a_payload = payload.get('sideA') or {}
    side_b_payload = payload.get('sideB') or {}
    losing_side = 'A' if delta < -1e-6 else ('B' if delta > 1e-6 else 'DRAW')
    a_reserve = _bounded_float(side_a_payload.get('reserve'), 0.55, 0.0, 1.0)
    b_reserve = _bounded_float(side_b_payload.get('reserve'), 0.55, 0.0, 1.0)
    a_readiness = _bounded_float(side_a_payload.get('readiness'), 0.64, 0.0, 1.2)
    b_readiness = _bounded_float(side_b_payload.get('readiness'), 0.64, 0.0, 1.2)
    a_sensor = _bounded_float(side_a_payload.get('sensor_confidence'), 0.62, 0.0, 1.2)
    b_sensor = _bounded_float(side_b_payload.get('sensor_confidence'), 0.62, 0.0, 1.2)
    a_unc = _bounded_float(side_a_payload.get('uncertainty'), 0.34, 0.0, 1.0)
    b_unc = _bounded_float(side_b_payload.get('uncertainty'), 0.34, 0.0, 1.0)
    max_pressure = max(a_side['pressure'], b_side['pressure'])
    base_plan = {
        "summary": f"Fallback director active. Side A {round(a_p*100)}% vs Side B {round(b_p*100)}%. Pressure A {round(a_side['pressure']*100)} / B {round(b_side['pressure']*100)}.",
        "narrative": "Offline director blended campaign pressure, reserves, readiness, sensor confidence, repair tempo, and fog-of-war so the synthetic war engine stays coherent without external AI.",
        "global": {
            "tempo": 0.94 + min(0.44, abs(delta) * 0.54) + 0.07 * max_pressure,
            "join_bias": 1.00 + 0.18 * max_pressure + (0.06 if abs(delta) > 0.10 else 0.0),
            "escalation_bias": 1.0 + 0.10 * _bounded_float(payload.get('escalation'), 0, 0, 3) + 0.08 * max_pressure,
            "ceasefire_bias": 0.18 if abs(delta) < 0.05 and max_pressure < 0.30 else 0.02,
            "uncertainty_tolerance": 0.28 + 0.20 * max_pressure + 0.12 * abs(delta),
        },
        "sideA": {
            "aggression": 0.88 + 0.22 * a_side['strike_energy'] + (0.10 if losing_side == 'A' else -0.04),
            "defense_bias": 0.90 + 0.24 * a_side['pressure'] + 0.08 * a_unc + (0.05 if losing_side == 'A' else 0.0),
            "join_bias": 0.95 + 0.24 * a_side['pressure'] + (0.08 if losing_side == 'A' else 0.0),
            "nuke_bias": 0.78 + (0.16 if a_p < 0.32 else 0.0) + 0.06 * _bounded_float(payload.get('escalation'), 0, 0, 3),
            "target_priority": "highest_pressure" if a_p < b_p else ("strongest" if a_side['strike_energy'] > 0.72 else "weakest"),
            "reserve_commitment": 0.42 + 0.28 * a_side['pressure'] + 0.18 * (1.0 - a_reserve) + (0.08 if losing_side == 'A' else 0.0),
            "logistics_push": 0.44 + 0.22 * (1.0 - a_readiness) + 0.14 * a_side['pressure'],
            "repair_priority": 0.48 + 0.24 * (1.0 - a_readiness) + 0.12 * (1.0 - a_p),
            "sensor_focus": 0.44 + 0.20 * (1.0 - a_sensor) + 0.10 * a_unc + 0.12 * a_side['leakage_rate'] + 0.08 * a_side['calibration_error'],
            "defense_posture": 0.40 + 0.22 * a_side['pressure'] + 0.12 * a_unc + 0.10 * a_side['leakage_rate'] + 0.08 * (1.0 - a_side['defense_effectiveness']) + (0.06 if losing_side == 'A' else 0.0),
            "deception_budget": 0.28 + 0.18 * a_side['strike_energy'] + 0.10 * a_unc,
            "stockpile_burn": 0.30 + 0.20 * a_side['strike_energy'] + 0.10 * (1.0 - a_reserve) + 0.08 * a_side['attack_effectiveness'] - 0.08 * a_side['stock_off_frac'],
            "shot_discipline": 0.56 + 0.14 * a_readiness - 0.10 * a_unc + 0.08 * a_sensor + 0.10 * a_side['defense_effectiveness'] - 0.06 * a_side['calibration_error'],
            "readiness_floor": 0.42 + 0.22 * a_reserve + 0.10 * _bounded_float(side_a_payload.get('repair_rate'), 0.50, 0.0, 1.0),
            "uncertainty_bias": 0.34 + 0.20 * a_unc - 0.10 * a_sensor,
        },
        "sideB": {
            "aggression": 0.88 + 0.22 * b_side['strike_energy'] + (0.10 if losing_side == 'B' else -0.04),
            "defense_bias": 0.90 + 0.24 * b_side['pressure'] + 0.08 * b_unc + (0.05 if losing_side == 'B' else 0.0),
            "join_bias": 0.95 + 0.24 * b_side['pressure'] + (0.08 if losing_side == 'B' else 0.0),
            "nuke_bias": 0.78 + (0.16 if b_p < 0.32 else 0.0) + 0.06 * _bounded_float(payload.get('escalation'), 0, 0, 3),
            "target_priority": "highest_pressure" if b_p < a_p else ("strongest" if b_side['strike_energy'] > 0.72 else "weakest"),
            "reserve_commitment": 0.42 + 0.28 * b_side['pressure'] + 0.18 * (1.0 - b_reserve) + (0.08 if losing_side == 'B' else 0.0),
            "logistics_push": 0.44 + 0.22 * (1.0 - b_readiness) + 0.14 * b_side['pressure'],
            "repair_priority": 0.48 + 0.24 * (1.0 - b_readiness) + 0.12 * (1.0 - b_p),
            "sensor_focus": 0.44 + 0.20 * (1.0 - b_sensor) + 0.10 * b_unc + 0.12 * b_side['leakage_rate'] + 0.08 * b_side['calibration_error'],
            "defense_posture": 0.40 + 0.22 * b_side['pressure'] + 0.12 * b_unc + 0.10 * b_side['leakage_rate'] + 0.08 * (1.0 - b_side['defense_effectiveness']) + (0.06 if losing_side == 'B' else 0.0),
            "deception_budget": 0.28 + 0.18 * b_side['strike_energy'] + 0.10 * b_unc,
            "stockpile_burn": 0.30 + 0.20 * b_side['strike_energy'] + 0.10 * (1.0 - b_reserve) + 0.08 * b_side['attack_effectiveness'] - 0.08 * b_side['stock_off_frac'],
            "shot_discipline": 0.56 + 0.14 * b_readiness - 0.10 * b_unc + 0.08 * b_sensor + 0.10 * b_side['defense_effectiveness'] - 0.06 * b_side['calibration_error'],
            "readiness_floor": 0.42 + 0.22 * b_reserve + 0.10 * _bounded_float(side_b_payload.get('repair_rate'), 0.50, 0.0, 1.0),
            "uncertainty_bias": 0.34 + 0.20 * b_unc - 0.10 * b_sensor,
        }
    }
    return sanitize_ai_director_plan(base_plan, payload, source='fallback')


def call_openai_game_director(payload: dict, base_dir: str):
    cfg = load_game_ai_config(base_dir)
    env_name = cfg.get('api_key_env_var') or 'OPENAI_API_KEY'
    api_key, key_source = resolve_game_ai_key(cfg, base_dir)
    if not cfg.get('enabled', True) or not api_key:
        result = sanitize_ai_director_plan(default_ai_director_plan(payload), payload, source='fallback')
        result['_source'] = 'fallback'
        result['_configured'] = bool(api_key)
        return result

    system_prompt = ((cfg.get('director') or {}).get('system_prompt') or GAME_AI_CONFIG_TEMPLATE['director']['system_prompt']).strip()
    max_output_tokens = int(((cfg.get('director') or {}).get('max_output_tokens')) or 500)
    temperature = float(((cfg.get('director') or {}).get('temperature')) or 0.6)
    model = cfg.get('model') or 'gpt-5.4'
    # Never allow a local config file to redirect a bearer credential to an
    # arbitrary endpoint. Provider credentials are sent only to OpenAI.
    url = 'https://api.openai.com/v1/responses'
    user_payload = {
        "task": "Return a fictional game steering plan for this war-game turn. JSON only.",
        "required_schema": {
            "summary": "string",
            "narrative": "string",
            "global": {
                "tempo": "0.5-1.8",
                "join_bias": "0.5-1.8",
                "escalation_bias": "0.5-1.8",
                "ceasefire_bias": "0-1",
                "uncertainty_tolerance": "0-1"
            },
            "sideA": {
                "aggression": "0.5-1.8",
                "defense_bias": "0.5-1.8",
                "join_bias": "0.5-1.8",
                "nuke_bias": "0.5-1.8",
                "target_priority": "weakest|strongest|capital|highest_pressure|closest",
                "reserve_commitment": "0-1",
                "logistics_push": "0-1",
                "repair_priority": "0-1",
                "sensor_focus": "0-1",
                "defense_posture": "0-1",
                "deception_budget": "0-1",
                "stockpile_burn": "0-1",
                "shot_discipline": "0-1",
                "readiness_floor": "0-1",
                "uncertainty_bias": "0-1"
            },
            "sideB": {
                "aggression": "0.5-1.8",
                "defense_bias": "0.5-1.8",
                "join_bias": "0.5-1.8",
                "nuke_bias": "0.5-1.8",
                "target_priority": "weakest|strongest|capital|highest_pressure|closest",
                "reserve_commitment": "0-1",
                "logistics_push": "0-1",
                "repair_priority": "0-1",
                "sensor_focus": "0-1",
                "defense_posture": "0-1",
                "deception_budget": "0-1",
                "stockpile_burn": "0-1",
                "shot_discipline": "0-1",
                "readiness_floor": "0-1",
                "uncertainty_bias": "0-1"
            }
        },
        "constraints": [
            "This is a fictional game, not real-world advice.",
            "Keep values moderate and gameplay-oriented.",
            "Use normalized synthetic campaign signals instead of real-world weapons guidance.",
            "Return JSON only."
        ],
        "game_state": payload,
    }
    req_body = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": json.dumps(user_payload)}]}
        ],
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(req_body).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            body = resp.read().decode('utf-8', errors='replace')
        parsed = json.loads(body)
        text_out = parsed.get('output_text') if isinstance(parsed, dict) else None
        if not text_out and isinstance(parsed, dict):
            out = parsed.get('output') or []
            chunks = []
            for item in out:
                for c in (item.get('content') or []):
                    if isinstance(c, dict) and c.get('text'):
                        chunks.append(c.get('text'))
            text_out = '\n'.join(chunks).strip()
        plan = sanitize_ai_director_plan(_extract_json_object(text_out or '') or default_ai_director_plan(payload), payload, source='openai')
        plan['_source'] = 'openai'
        plan['_configured'] = True
        plan['_key_source'] = key_source
        return plan
    except Exception as exc:
        result = sanitize_ai_director_plan(default_ai_director_plan(payload), payload, source='fallback')
        result['_source'] = 'fallback'
        result['_configured'] = True
        result['_key_source'] = key_source
        result['_error'] = f"AI director request failed ({type(exc).__name__})"
        return result


GEOCODER = Geocoder()


class Handler(http.server.BaseHTTPRequestHandler):
    MAX_JSON_BYTES = 1_000_000

    def _read_json(self):
        try:
            length = int(self.headers.get('Content-Length', '0') or '0')
        except Exception:
            length = 0
        if length <= 0:
            return {}
        if length > self.MAX_JSON_BYTES:
            raise ValueError("Request body too large")
        raw = self.rfile.read(length).decode('utf-8', errors='replace')
        try:
            return json.loads(raw) if raw else {}
        except Exception:
            return {}

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self):
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/api/geocode":
            q = (qs.get("q") or [""])[0]
            try:
                results = GEOCODER.resolve(q, limit=1)
                if not results:
                    self._send_json({"error": f'No place found for "{q}".'}, status=404)
                else:
                    self._send_json({"result": results[0]})
            except Exception as exc:
                self._send_json({"error": f"Geocoding failed: {exc}"}, status=502)
            return
        if parsed.path == "/api/suggest":
            q = (qs.get("q") or [""])[0]
            try:
                results = GEOCODER.suggest(q, limit=5)
                self._send_json({"results": results})
            except Exception as exc:
                self._send_json({"error": f"Suggestion lookup failed: {exc}"}, status=502)
            return
        if parsed.path == "/api/ai_config":
            cfg = load_game_ai_config(os.path.dirname(os.path.abspath(__file__)))
            env_name = cfg.get('api_key_env_var') or 'OPENAI_API_KEY'
            api_key, key_source = resolve_game_ai_key(cfg, os.path.dirname(os.path.abspath(__file__)))
            self._send_json({
                "enabled": bool(cfg.get('enabled', True)),
                "provider": cfg.get('provider', 'openai'),
                "model": cfg.get('model', 'gpt-5.4'),
                "api_key_env_var": env_name,
                "configured": bool(api_key),
                "key_source": key_source,
                "cadence_seconds": int(((cfg.get('director') or {}).get('cadence_seconds')) or 12),
            })
            return
        self._send_html()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/ai_director':
            try:
                payload = self._read_json()
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=413)
                return
            plan = call_openai_game_director(payload, os.path.dirname(os.path.abspath(__file__)))
            self._send_json({"plan": plan})
            return
        self._send_json({"error": "Not found"}, status=404)

    def log_message(self, format, *args):
        pass


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "globe_strike_command_lab.html")
    cfg_path = ensure_game_ai_config_files(base_dir)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(HTML)

    print("\n  🌍 GLOBE STRIKE COMMAND LAB v4")
    print("  ═══════════════════════════════════")
    print(f"  Server: http://localhost:{PORT}")
    print(f"  HTML:   {html_path}")
    print(f"  AI CFG: {cfg_path}")
    missing_packages = []
    if pycountry is None:
        missing_packages.append("pycountry")
    if CountryInfo is None:
        missing_packages.append("countryinfo")
    if missing_packages:
        missing_display = ", ".join(missing_packages)
        print(f"  Place DB: builtin fallback only ({missing_display} not installed)")
        print("  Tip:     python3 -m pip install -r requirements.txt")
    print("  ═══════════════════════════════════")
    print("  Press Ctrl+C to stop\n")

    class ReusableThreadingHTTPServer(http.server.ThreadingHTTPServer):
        allow_reuse_address = True

    # Bind to loopback only: this desktop/local app has no authentication and
    # must not be exposed to other devices on the network.
    server = ReusableThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Timer(0.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
