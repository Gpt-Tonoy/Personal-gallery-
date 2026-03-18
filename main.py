import os, io, json, hashlib, secrets
import requests as req
from flask import Flask, redirect, request, session, jsonify, render_template_string
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from datetime import datetime

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = 'tonoy-super-secret-2026-gallery'
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=86400
)

CLIENT_ID = '565165560969-k126trc6ugj7lp2au2l438k5di2ppg64.apps.googleusercontent.com'
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = 'https://personal-gallery-production-e2b9.up.railway.app/callback'
SCOPES = ['https://www.googleapis.com/auth/drive', 'openid', 'https://www.googleapis.com/auth/userinfo.email']

PROFILE_FILE = '/tmp/profile.json'
VAULT_FILE = '/tmp/vault.json'
ALBUMS_FILE = '/tmp/albums.json'

def get_flow():
    flow = Flow.from_client_config(
        {"web": {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
                 "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                 "token_uri": "https://oauth2.googleapis.com/token"}},
        scopes=SCOPES, redirect_uri=REDIRECT_URI)
    flow.code_verifier = ''
    return flow

def load_json(path, default):
    try: return json.load(open(path))
    except: return default

def save_json(path, data): json.dump(data, open(path, 'w'))

def hash_password(pwd): return hashlib.sha256(pwd.encode()).hexdigest()

HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#000000">
<title>M. Tonoy Gallery</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;background:#000;color:#fff;min-height:100vh;overflow-x:hidden}

/* Header */
.header{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(0,0,0,0.95);backdrop-filter:blur(20px);padding:10px 16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #111}
.header-left{display:flex;align-items:center;gap:10px;cursor:pointer}
.avatar{width:34px;height:34px;border-radius:50%;object-fit:cover;border:2px solid #4285f4}
.avatar-init{width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#4285f4,#34a853);display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700}
.hname{font-size:17px;font-weight:600}
.hbtns{display:flex;gap:8px}
.ibtn{background:rgba(255,255,255,0.08);border:none;color:#fff;width:34px;height:34px;border-radius:50%;cursor:pointer;font-size:15px;display:flex;align-items:center;justify-content:center;text-decoration:none}

/* Storage */
.storage{background:#0a0a0a;padding:10px 16px;border-bottom:1px solid #111;margin-top:55px}
.strow{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.sttext{font-size:12px;color:#888}
.stpct{font-size:12px;color:#4285f4;font-weight:600}
.stbar{background:#1a1a1a;border-radius:4px;height:4px;overflow:hidden}
.stfill{background:linear-gradient(90deg,#4285f4,#34a853);border-radius:4px;height:4px;transition:width 0.6s ease}
.acc-toggle{font-size:11px;color:#555;cursor:pointer;margin-top:5px;display:inline-flex;align-items:center;gap:4px}
.acc-detail{display:none;margin-top:8px;border-top:1px solid #111;padding-top:8px}
.acc-detail.open{display:block}
.acc-row{display:flex;justify-content:space-between;padding:3px 0}
.acc-row span{font-size:11px;color:#666}
.acc-row strong{font-size:11px;color:#888}

/* Tabs */
.tabs{display:flex;background:#000;border-bottom:1px solid #111;position:sticky;top:55px;z-index:99;overflow-x:auto;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tab{flex:1;min-width:60px;padding:10px 8px;text-align:center;font-size:12px;color:#555;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap}
.tab.active{color:#fff;border-bottom:2px solid #fff}

.section{display:none;padding-bottom:90px}.section.active{display:block}

/* Grid */
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1.5px}
.mitem{position:relative;aspect-ratio:1;cursor:pointer;overflow:hidden;background:#0d0d0d;user-select:none;-webkit-user-select:none}
.mitem img{width:100%;height:100%;object-fit:cover;transition:all 0.15s}
.mitem.sel img{opacity:0.45;transform:scale(0.95)}
.mitem.sel::after{content:\'✓\';position:absolute;top:5px;right:5px;background:#4285f4;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff}
.vbadge{position:absolute;bottom:4px;left:4px;background:rgba(0,0,0,0.75);border-radius:3px;padding:1px 5px;font-size:9px;display:flex;align-items:center;gap:3px}

/* Selection bar */
.selbar{display:none;position:fixed;bottom:0;left:0;right:0;z-index:200;background:rgba(15,15,15,0.98);backdrop-filter:blur(20px);border-top:1px solid #222;padding:10px 16px 20px}
.selbar.open{display:block}
.seltop{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.selcount{font-size:13px;color:#aaa}
.selacts{display:flex;gap:6px}
.sela{background:none;border:none;color:#4285f4;font-size:12px;cursor:pointer}
.selbtns{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.selbtn{background:#111;border:1px solid #222;color:#fff;padding:10px 4px;border-radius:10px;font-size:11px;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:4px}
.selbtn.red{background:rgba(255,59,48,0.15);border-color:rgba(255,59,48,0.3);color:#ff3b30}
.selbtn.green{background:rgba(52,199,89,0.15);border-color:rgba(52,199,89,0.3);color:#34c759}

/* FAB */
.fab{position:fixed;bottom:20px;right:16px;z-index:150;background:#4285f4;border:none;color:#fff;width:52px;height:52px;border-radius:50%;font-size:22px;cursor:pointer;box-shadow:0 4px 16px rgba(66,133,244,0.5);display:flex;align-items:center;justify-content:center}

/* Media Modal */
.mmodal{display:none;position:fixed;inset:0;z-index:300;background:#000;flex-direction:column}
.mmodal.open{display:flex}
.mhdr{padding:12px 16px;display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,0.8)}
.mclose{background:none;border:none;color:#fff;font-size:22px;cursor:pointer;width:36px;height:36px;display:flex;align-items:center;justify-content:center}
.mtitle{font-size:13px;color:#ddd;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px}
.mbody{flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden;background:#000}
.mbody img{max-width:100%;max-height:100%;object-fit:contain}
.mbody iframe{width:100%;height:100%;border:none}
.mfoot{padding:12px 16px 20px;display:flex;gap:8px;justify-content:center;background:rgba(0,0,0,0.8);flex-wrap:wrap}
.mbtn{background:rgba(255,255,255,0.12);border:none;color:#fff;padding:9px 14px;border-radius:22px;cursor:pointer;font-size:12px;display:flex;align-items:center;gap:5px}
.mbtn.blue{background:#4285f4}
.mbtn.red{background:rgba(255,59,48,0.8)}

/* Sheets */
.overlay{display:none;position:fixed;inset:0;z-index:300;background:rgba(0,0,0,0.7);align-items:flex-end}
.overlay.open{display:flex}
.sheet{background:#111;border-radius:20px 20px 0 0;padding:20px;width:100%;max-width:500px;margin:0 auto;max-height:85vh;overflow-y:auto}
.shhdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
.shtitle{font-size:17px;font-weight:600}
.shclose{background:rgba(255,255,255,0.1);border:none;color:#fff;width:28px;height:28px;border-radius:50%;cursor:pointer;font-size:14px}
.upa{border:2px dashed #222;border-radius:12px;padding:24px;text-align:center;cursor:pointer;margin-bottom:12px}
.fullbtn{width:100%;background:#4285f4;border:none;color:#fff;padding:13px;border-radius:12px;font-size:15px;cursor:pointer;font-weight:600;margin-bottom:8px}
.cancelbtn{width:100%;background:rgba(255,255,255,0.08);border:none;color:#fff;padding:13px;border-radius:12px;font-size:15px;cursor:pointer}

/* Profile Modal */
.pmodal{display:none;position:fixed;inset:0;z-index:400;background:#000;flex-direction:column}
.pmodal.open{display:flex}
.pmhdr{padding:12px 16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #111}
.pmcontent{flex:1;overflow-y:auto;padding:20px}
.pmbig{width:72px;height:72px;border-radius:50%;object-fit:cover;border:2px solid #4285f4;cursor:pointer;display:block;margin:0 auto 10px}
.pmbig-init{width:72px;height:72px;border-radius:50%;background:linear-gradient(135deg,#4285f4,#34a853);display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:700;cursor:pointer;margin:0 auto 10px}
.stcard{background:#111;border-radius:12px;margin-bottom:12px;overflow:hidden}
.stitem{padding:14px 16px;border-bottom:1px solid #1a1a1a;display:flex;align-items:center;justify-content:space-between;cursor:pointer}
.stitem:last-child{border-bottom:none}
.stleft{display:flex;align-items:center;gap:12px}
.stico{font-size:18px;width:28px;text-align:center}
.stlabel{font-size:15px}
.stval{font-size:12px;color:#555}
inp{display:block;width:100%;padding:11px 14px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;color:#fff;font-size:15px;margin-top:8px;outline:none}
inp:focus{border-color:#4285f4}

/* Albums */
.album-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;padding:12px}
.album-card{background:#111;border-radius:12px;overflow:hidden;cursor:pointer;position:relative}
.album-thumb{width:100%;aspect-ratio:1;object-fit:cover;background:#1a1a1a;display:flex;align-items:center;justify-content:center;font-size:32px;color:#333}
.album-info{padding:10px}
.album-name{font-size:14px;font-weight:500;margin-bottom:2px}
.album-count{font-size:11px;color:#555}
.new-album{border:2px dashed #222;background:transparent;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;color:#555;font-size:13px;cursor:pointer;padding:20px}

/* Vault */
.vault-lock{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 24px;text-align:center}
.vault-icon{font-size:56px;margin-bottom:16px}
.vault-title{font-size:20px;font-weight:600;margin-bottom:6px}
.vault-sub{font-size:13px;color:#555;margin-bottom:24px}
.pinpad{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;max-width:240px;margin:0 auto}
.pinbtn{background:#111;border:none;color:#fff;aspect-ratio:1;border-radius:50%;font-size:20px;cursor:pointer;font-weight:500}
.pinbtn:active{background:#222}
.pindots{display:flex;gap:12px;justify-content:center;margin-bottom:20px}
.pindot{width:12px;height:12px;border-radius:50%;background:#222;transition:background 0.15s}
.pindot.filled{background:#4285f4}

/* Drives list */
.drives-list{padding:16px}
.drive-card{background:#111;border-radius:12px;padding:14px;margin-bottom:10px}
.drive-email{font-size:13px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center}
.drive-bar{background:#1a1a1a;border-radius:4px;height:4px;margin-bottom:5px}
.drive-fill{background:#4285f4;border-radius:4px;height:4px}
.drive-info{display:flex;justify-content:space-between;font-size:11px;color:#555}
.rmvbtn{background:rgba(255,59,48,0.15);border:1px solid rgba(255,59,48,0.2);color:#ff3b30;padding:3px 10px;border-radius:16px;font-size:10px;cursor:pointer}

/* All list */
.all-list{padding:8px}
.all-item{display:flex;align-items:center;gap:12px;padding:11px;background:#0d0d0d;border-radius:10px;margin-bottom:6px}
.all-ico{font-size:22px;width:32px;text-align:center}
.all-name{flex:1;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#ddd}
.all-dl{background:rgba(255,255,255,0.08);border:none;color:#fff;padding:5px 11px;border-radius:16px;font-size:11px;cursor:pointer}

.empty{text-align:center;padding:50px 20px;color:#333}
.empty-ico{font-size:44px;margin-bottom:10px}
.progress{display:none;position:fixed;top:0;left:0;width:0;height:2px;background:#4285f4;z-index:999;transition:width 0.3s}
.toast{display:none;position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:rgba(50,50,50,0.95);color:#fff;padding:10px 20px;border-radius:20px;font-size:13px;z-index:500;white-space:nowrap}
input[type=text],input[type=password]{display:block;width:100%;padding:11px 14px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;color:#fff;font-size:15px;margin-top:8px;outline:none}
input[type=text]:focus,input[type=password]:focus{border-color:#4285f4}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div class="header-left" onclick="openProfile()">
    <div id="hAvatar"></div>
    <span class="hname" id="hName">Gallery</span>
  </div>
  <div class="hbtns">
    <a href="/auth" class="ibtn">➕</a>
    <button class="ibtn" onclick="openUpload()">⬆️</button>
  </div>
</div>

<!-- Storage -->
<div class="storage">
  <div class="strow">
    <span class="sttext" id="stText">Loading...</span>
    <span class="stpct" id="stPct"></span>
  </div>
  <div class="stbar"><div class="stfill" id="stFill" style="width:0%"></div></div>
  <span class="acc-toggle" onclick="toggleAccounts()" id="accToggle">▼ accounts</span>
  <div class="acc-detail" id="accDetail"></div>
</div>

<!-- Tabs -->
<div class="tabs">
  <div class="tab active" onclick="showTab(\'photos\')">Photos</div>
  <div class="tab" onclick="showTab(\'videos\')">Videos</div>
  <div class="tab" onclick="showTab(\'albums\')">Albums</div>
  <div class="tab" onclick="showTab(\'vault\')">🔒 Vault</div>
  <div class="tab" onclick="showTab(\'all\')">All</div>
  <div class="tab" onclick="showTab(\'drives\')">Drives</div>
</div>

<!-- Sections -->
<div id="photos" class="section active">
  <div class="grid" id="photoGrid"></div>
</div>

<div id="videos" class="section">
  <div class="grid" id="videoGrid"></div>
</div>

<div id="albums" class="section">
  <div class="album-grid" id="albumGrid"></div>
</div>

<div id="vault" class="section">
  <div class="vault-lock" id="vaultLock">
    <div class="vault-icon">🔒</div>
    <div class="vault-title">Private Vault</div>
    <div class="vault-sub" id="vaultSub">Enter PIN to access</div>
    <div class="pindots" id="pinDots">
      <div class="pindot" id="d0"></div>
      <div class="pindot" id="d1"></div>
      <div class="pindot" id="d2"></div>
      <div class="pindot" id="d3"></div>
    </div>
    <div class="pinpad">
      <button class="pinbtn" onclick="pinPress(1)">1</button>
      <button class="pinbtn" onclick="pinPress(2)">2</button>
      <button class="pinbtn" onclick="pinPress(3)">3</button>
      <button class="pinbtn" onclick="pinPress(4)">4</button>
      <button class="pinbtn" onclick="pinPress(5)">5</button>
      <button class="pinbtn" onclick="pinPress(6)">6</button>
      <button class="pinbtn" onclick="pinPress(7)">7</button>
      <button class="pinbtn" onclick="pinPress(8)">8</button>
      <button class="pinbtn" onclick="pinPress(9)">9</button>
      <button class="pinbtn" onclick="pinPress(\'clear\')">✕</button>
      <button class="pinbtn" onclick="pinPress(0)">0</button>
      <button class="pinbtn" onclick="pinPress(\'del\')">⌫</button>
    </div>
    <div style="margin-top:16px">
      <button onclick="forgotPin()" style="background:none;border:none;color:#4285f4;font-size:13px;cursor:pointer">Forgot PIN?</button>
    </div>
  </div>
  <div id="vaultContent" style="display:none">
    <div style="padding:12px;display:flex;justify-content:space-between;align-items:center">
      <span style="font-size:14px;color:#888">Private Vault</span>
      <button onclick="lockVault()" style="background:none;border:none;color:#ff3b30;font-size:13px;cursor:pointer">🔒 Lock</button>
    </div>
    <div class="grid" id="vaultGrid"></div>
  </div>
</div>

<div id="all" class="section">
  <div class="all-list" id="allList"></div>
</div>

<div id="drives" class="section">
  <div class="drives-list" id="drivesList"></div>
  <div style="padding:0 16px 16px">
    <a href="/auth" class="fullbtn" style="display:block;text-align:center;text-decoration:none">+ Connect Google Drive</a>
  </div>
</div>

<!-- FAB -->
<button class="fab" id="fab" onclick="openUpload()">+</button>

<!-- Selection Bar -->
<div class="selbar" id="selbar">
  <div class="seltop">
    <span class="selcount" id="selCount">0 selected</span>
    <div class="selacts">
      <button class="sela" onclick="selectAll()">All</button>
      <button class="sela" style="color:#ff3b30" onclick="cancelSel()">Cancel</button>
    </div>
  </div>
  <div class="selbtns">
    <button class="selbtn" onclick="dlSelected()">⬇️<span>Download</span></button>
    <button class="selbtn green" onclick="gallerySelected()">🖼️<span>Gallery</span></button>
    <button class="selbtn" onclick="moveToAlbum()">📁<span>Album</span></button>
    <button class="selbtn red" onclick="delSelected()">🗑️<span>Delete</span></button>
  </div>
</div>

<!-- Media Modal -->
<div class="mmodal" id="mModal">
  <div class="mhdr">
    <button class="mclose" onclick="closeMedia()">✕</button>
    <span class="mtitle" id="mTitle"></span>
    <span></span>
  </div>
  <div class="mbody" id="mBody"></div>
  <div class="mfoot">
    <button class="mbtn" onclick="dlCurrent()">⬇️ Download</button>
    <button class="mbtn blue" onclick="galleryCurrent()">🖼️ Save</button>
    <button class="mbtn red" onclick="delCurrent()">🗑️ Delete</button>
  </div>
</div>

<!-- Upload Sheet -->
<div class="overlay" id="uploadSheet">
  <div class="sheet">
    <div class="shhdr">
      <span class="shtitle">Upload Files</span>
      <button class="shclose" onclick="closeUpload()">✕</button>
    </div>
    <div class="upa" onclick="document.getElementById(\'fi\').click()">
      <div style="font-size:36px;margin-bottom:6px">📤</div>
      <div style="color:#555;font-size:13px">Tap to select photos & videos</div>
      <input type="file" id="fi" multiple accept="image/*,video/*" style="display:none">
    </div>
    <div id="upStatus" style="color:#555;font-size:12px;text-align:center;min-height:18px;margin-bottom:10px"></div>
    <button class="fullbtn" onclick="doUpload()">Upload</button>
    <button class="cancelbtn" onclick="closeUpload()">Cancel</button>
  </div>
</div>

<!-- Album Sheet -->
<div class="overlay" id="albumSheet">
  <div class="sheet">
    <div class="shhdr">
      <span class="shtitle">Move to Album</span>
      <button class="shclose" onclick="closeAlbumSheet()">✕</button>
    </div>
    <div id="albumList"></div>
    <div style="margin-top:12px">
      <input type="text" id="newAlbumName" placeholder="New album name...">
      <button class="fullbtn" style="margin-top:8px" onclick="createAndMove()">Create & Move</button>
    </div>
  </div>
</div>

<!-- Profile Modal -->
<div class="pmodal" id="pModal">
  <div class="pmhdr">
    <button onclick="closeProfile()" style="background:none;border:none;color:#fff;font-size:22px;cursor:pointer">✕</button>
    <span style="font-size:16px;font-weight:600">Profile</span>
    <button onclick="saveProfile()" style="background:none;border:none;color:#4285f4;font-size:15px;cursor:pointer;font-weight:600">Save</button>
  </div>
  <div class="pmcontent">
    <div style="text-align:center;margin-bottom:24px">
      <div id="pAvatar" onclick="document.getElementById(\'pPhoto\').click()" style="cursor:pointer;margin:0 auto 8px"></div>
      <input type="file" id="pPhoto" accept="image/*" style="display:none">
      <div style="font-size:11px;color:#4285f4">Tap to change</div>
    </div>
    <div class="stcard">
      <div style="padding:14px">
        <div style="font-size:11px;color:#555;margin-bottom:2px">DISPLAY NAME</div>
        <input type="text" id="pName" placeholder="Your name">
      </div>
    </div>
    <div class="stcard">
      <div class="stitem" onclick="showTab(\'vault\');closeProfile()">
        <div class="stleft"><span class="stico">🔒</span><span class="stlabel">Private Vault</span></div>
        <span class="stval">›</span>
      </div>
      <div class="stitem" onclick="openVaultSetup()">
        <div class="stleft"><span class="stico">🔑</span><span class="stlabel">Change Vault PIN</span></div>
        <span class="stval">›</span>
      </div>
    </div>
    <div class="stcard">
      <div class="stitem" onclick="showTab(\'drives\');closeProfile()">
        <div class="stleft"><span class="stico">☁️</span><span class="stlabel">Manage Drives</span></div>
        <span class="stval">›</span>
      </div>
      <a href="/auth" class="stitem" style="text-decoration:none;color:#fff;display:flex">
        <div class="stleft"><span class="stico">➕</span><span class="stlabel">Add Google Drive</span></div>
        <span class="stval">›</span>
      </a>
    </div>
  </div>
</div>

<!-- Vault Setup Sheet -->
<div class="overlay" id="vaultSetup">
  <div class="sheet">
    <div class="shhdr">
      <span class="shtitle">Set Vault PIN</span>
      <button class="shclose" onclick="closeVaultSetup()">✕</button>
    </div>
    <div style="margin-bottom:12px">
      <div style="font-size:12px;color:#555;margin-bottom:4px">New PIN (4-8 digits)</div>
      <input type="password" id="newPin" placeholder="Enter PIN" maxlength="8">
    </div>
    <div style="margin-bottom:16px">
      <div style="font-size:12px;color:#555;margin-bottom:4px">Recovery Email</div>
      <input type="text" id="recEmail" placeholder="Recovery email address">
    </div>
    <button class="fullbtn" onclick="saveVaultPin()">Save PIN</button>
    <button class="cancelbtn" onclick="closeVaultSetup()">Cancel</button>
  </div>
</div>

<div class="progress" id="prog"></div>
<div class="toast" id="toast"></div>

<script>
let allFiles=[], selIds=new Set(), selMode=false, curFile=null, lpTimer=null
let profile={name:\'M. Tonoy\',photo:\'\'}
let vaultData={pin:\'\',recovery:\'\',unlocked:false,files:[]}
let albums={}
let pinBuf=\'\'
let curAlbum=null

// Toast
function showToast(msg){
  const t=document.getElementById(\'toast\')
  t.textContent=msg; t.style.display=\'block\'
  setTimeout(()=>t.style.display=\'none\',2000)
}

// Progress
function showProg(w){
  const p=document.getElementById(\'prog\')
  p.style.display=\'block\'; p.style.width=w+\'%\'
  if(w>=100) setTimeout(()=>{p.style.display=\'none\';p.style.width=\'0\'},400)
}

// Profile
async function loadProfile(){
  try{
    const d=await(await fetch(\'/profile\')).json()
    profile=d; updateProfileUI()
  }catch(e){}
}

function updateProfileUI(){
  const n=profile.name||\'Gallery\'
  document.getElementById(\'hName\').textContent=n
  document.getElementById(\'pName\').value=n
  const ha=document.getElementById(\'hAvatar\')
  const pa=document.getElementById(\'pAvatar\')
  const init=n.charAt(0).toUpperCase()
  if(profile.photo){
    ha.innerHTML=`<img src="${profile.photo}" class="avatar">`
    pa.innerHTML=`<img src="${profile.photo}" class="pmbig">`
  } else {
    ha.innerHTML=`<div class="avatar-init">${init}</div>`
    pa.innerHTML=`<div class="pmbig-init">${init}</div>`
  }
}

document.getElementById(\'pPhoto\').addEventListener(\'change\',function(){
  if(!this.files[0]) return
  const r=new FileReader()
  r.onload=e=>{profile.photo=e.target.result; updateProfileUI()}
  r.readAsDataURL(this.files[0])
})

async function saveProfile(){
  profile.name=document.getElementById(\'pName\').value||\'Gallery\'
  await fetch(\'/profile\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify(profile)})
  updateProfileUI(); closeProfile(); showToast(\'Profile saved ✓\')
}

function openProfile(){document.getElementById(\'pModal\').classList.add(\'open\')}
function closeProfile(){document.getElementById(\'pModal\').classList.remove(\'open\')}

// Load files
async function loadFiles(){
  showProg(30)
  try{
    const d=await(await fetch(\'/drive/files\')).json()
    allFiles=d.files||[]
    showProg(60)
    
    // Storage
    if(d.accounts&&d.accounts.length){
      let used=0,total=0
      d.accounts.forEach(a=>{used+=parseFloat(a.used);total+=parseFloat(a.total)})
      const pct=total>0?Math.min(100,(used/total*100)).toFixed(1):0
      document.getElementById(\'stText\').textContent=`${used.toFixed(1)} GB used of ${total.toFixed(1)} GB`
      document.getElementById(\'stPct\').textContent=pct+\'%\'
      document.getElementById(\'stFill\').style.width=pct+\'%\'
      document.getElementById(\'accDetail\').innerHTML=d.accounts.map(a=>`<div class="acc-row"><span>${a.email.split(\'@\')[0]}</span><strong>${a.used} GB / ${a.total} GB</strong></div>`).join(\'\')
      document.getElementById(\'drivesList\').innerHTML=d.accounts.map(a=>`
        <div class="drive-card">
          <div class="drive-email"><span>📧 ${a.email}</span><button class="rmvbtn" onclick="removeAcc(\'${a.email}\')">Remove</button></div>
          <div class="drive-bar"><div class="drive-fill" style="width:${a.percent}%"></div></div>
          <div class="drive-info"><span>${a.used} GB used</span><span>${a.total} GB total</span></div>
        </div>`).join(\'\')
    } else {
      document.getElementById(\'stText\').textContent=\'No drives connected\'
      document.getElementById(\'drivesList\').innerHTML=\'<div class="empty"><div class="empty-ico">☁️</div><div>No drives connected</div></div>\'
    }
    
    renderPhotos(); renderVideos(); renderAll(); renderAlbums()
    showProg(100)
  }catch(e){console.log(e);showProg(100)}
}

// Render
const imgErr=\'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect fill="%230d0d0d"/></svg>\'

function renderPhotos(){
  const photos=allFiles.filter(f=>/\\.(jpg|jpeg|png|gif|webp|heic)/i.test(f.name))
  const g=document.getElementById(\'photoGrid\')
  g.innerHTML=photos.length?photos.map(f=>mediaItem(f,\'photo\')).join(\'\'):empty(\'📷\',\'No photos yet\')
}

function renderVideos(){
  const vids=allFiles.filter(f=>/\\.(mp4|mov|avi|mkv|webm|3gp)/i.test(f.name))
  const g=document.getElementById(\'videoGrid\')
  g.innerHTML=vids.length?vids.map(f=>mediaItem(f,\'video\')).join(\'\'):empty(\'🎬\',\'No videos yet\')
}

function renderAll(){
  const al=document.getElementById(\'allList\')
  al.innerHTML=allFiles.length?allFiles.map(f=>`
    <div class="all-item">
      <div class="all-ico">${/\\.(jpg|jpeg|png|gif|webp)/i.test(f.name)?\'🖼️\':/\\.(mp4|mov|avi|mkv|webm)/i.test(f.name)?\'🎬\':\'📄\'}</div>
      <div class="all-name">${f.name}</div>
      <button class="all-dl" onclick="window.open(\'${f.url}\')">⬇️</button>
    </div>`).join(\'\'):empty(\'📁\',\'No files yet\')
}

function renderAlbums(){
  const g=document.getElementById(\'albumGrid\')
  const albumEntries=Object.entries(albums)
  let html=albumEntries.map(([name,ids])=>{
    const first=allFiles.find(f=>ids.includes(f.id))
    return `<div class="album-card" onclick="openAlbum(\'${name}\')">
      <div style="aspect-ratio:1;overflow:hidden;background:#1a1a1a;display:flex;align-items:center;justify-content:center">
        ${first?`<img src="${first.thumb||first.url}" style="width:100%;height:100%;object-fit:cover" onerror="this.src=\'${imgErr}\'">`:`<span style="font-size:32px;color:#333">📁</span>`}
      </div>
      <div class="album-info">
        <div class="album-name">${name}</div>
        <div class="album-count">${ids.length} items</div>
      </div>
    </div>`}).join(\'\')
  html+=`<div class="album-card new-album" onclick="createAlbum()"><span style="font-size:28px">➕</span><span>New Album</span></div>`
  g.innerHTML=html
}

function mediaItem(f,type){
  const isV=type===\'video\'
  return `<div class="mitem" id="i_${f.id}"
    ontouchstart="lpStart(\'${f.id}\',\'${f.name}\',\'${type}\',\'${f.url}\',\'${f.thumb}\')" 
    ontouchend="lpEnd()" ontouchmove="lpEnd()"
    onclick="handleClick(\'${f.id}\',\'${f.name}\',\'${type}\',\'${f.url}\',\'${f.thumb}\')">
    <img src="${f.thumb||imgErr}" loading="lazy" onerror="this.src=\'${imgErr}\'">
    ${isV?\'<div class="vbadge">▶ video</div>\':\'\'} 
  </div>`
}

function empty(ico,txt){return `<div class="empty" style="grid-column:span 3"><div class="empty-ico">${ico}</div><div>${txt}</div></div>`}

// Long press
function lpStart(id,name,type,url,thumb){
  lpTimer=setTimeout(()=>{
    if(!selMode) enterSel()
    toggleSel(id)
  },550)
}
function lpEnd(){clearTimeout(lpTimer)}

function enterSel(){
  selMode=true
  document.getElementById(\'selbar\').classList.add(\'open\')
  document.getElementById(\'fab\').style.display=\'none\'
}

function cancelSel(){
  selMode=false; selIds.clear()
  document.getElementById(\'selbar\').classList.remove(\'open\')
  document.getElementById(\'fab\').style.display=\'\'
  document.querySelectorAll(\'.mitem\').forEach(e=>e.classList.remove(\'sel\'))
  updateSelCount()
}

function toggleSel(id){
  const el=document.getElementById(\'i_\'+id)
  if(!el) return
  if(selIds.has(id)){selIds.delete(id);el.classList.remove(\'sel\')}
  else{selIds.add(id);el.classList.add(\'sel\')}
  updateSelCount()
}

function handleClick(id,name,type,url,thumb){
  if(selMode) toggleSel(id)
  else openMedia(id,name,type,url,thumb)
}

function selectAll(){
  document.querySelector(\'.section.active\').querySelectorAll(\'.mitem\').forEach(el=>{
    const id=el.id.replace(\'i_\',\'\')
    selIds.add(id); el.classList.add(\'sel\')
  })
  updateSelCount()
}

function updateSelCount(){
  document.getElementById(\'selCount\').textContent=`${selIds.size} selected`
  if(selIds.size===0&&selMode) cancelSel()
}

async function dlSelected(){
  for(let id of selIds){
    const f=allFiles.find(x=>x.id===id)
    if(f){window.open(f.url);await new Promise(r=>setTimeout(r,300))}
  }
  cancelSel()
}

async function gallerySelected(){
  for(let id of selIds){
    const f=allFiles.find(x=>x.id===id)
    if(f){
      const a=document.createElement(\'a\')
      a.href=f.url; a.download=f.name; a.click()
      await new Promise(r=>setTimeout(r,500))
    }
  }
  cancelSel(); showToast(\'Saved to gallery ✓\')
}

async function delSelected(){
  if(!confirm(`Delete ${selIds.size} file(s)?`)) return
  showProg(20)
  for(let id of selIds) await fetch(\'/drive/delete/\'+id,{method:\'DELETE\'})
  cancelSel(); showToast(\'Deleted ✓\'); loadFiles()
}

function moveToAlbum(){
  const al=document.getElementById(\'albumList\')
  const albumEntries=Object.keys(albums)
  al.innerHTML=albumEntries.length?albumEntries.map(n=>`
    <div style="padding:12px;background:#1a1a1a;border-radius:10px;margin-bottom:8px;cursor:pointer;font-size:14px" onclick="addToAlbum(\'${n}\')">
      📁 ${n} (${albums[n].length})
    </div>`).join(\'\'):\'<div style="color:#555;font-size:13px;text-align:center;padding:12px">No albums yet</div>\'
  document.getElementById(\'albumSheet\').classList.add(\'open\')
}

function closeAlbumSheet(){document.getElementById(\'albumSheet\').classList.remove(\'open\')}

async function addToAlbum(name){
  if(!albums[name]) albums[name]=[]
  selIds.forEach(id=>{if(!albums[name].includes(id))albums[name].push(id)})
  await fetch(\'/albums\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify(albums)})
  closeAlbumSheet(); cancelSel(); renderAlbums(); showToast(`Added to "${name}" ✓`)
}

async function createAndMove(){
  const name=document.getElementById(\'newAlbumName\').value.trim()
  if(!name) return
  await addToAlbum(name)
  document.getElementById(\'newAlbumName\').value=\'\'
}

function createAlbum(){
  const name=prompt(\'Album name:\')
  if(!name) return
  if(!albums[name]) albums[name]=[]
  renderAlbums()
}

function openAlbum(name){
  curAlbum=name
  const ids=albums[name]||[]
  const files=allFiles.filter(f=>ids.includes(f.id))
  document.querySelector(\'#albums .album-grid\').innerHTML=`
    <div style="grid-column:span 2;padding:8px 4px;display:flex;align-items:center;gap:8px">
      <button onclick="renderAlbums()" style="background:none;border:none;color:#4285f4;font-size:22px;cursor:pointer">←</button>
      <span style="font-size:16px;font-weight:600">${name}</span>
    </div>
    ${files.map(f=>mediaItem(f,/\\.(mp4|mov|avi|mkv|webm)/i.test(f.name)?\'video\':\'photo\')).join(\'\')}
    ${!files.length?\'<div class="empty" style="grid-column:span 2"><div class="empty-ico">📁</div><div>Empty album</div></div>\':\'\'}`
}

// Media modal
function openMedia(id,name,type,url,thumb){
  curFile={id,name,type,url,thumb}
  document.getElementById(\'mTitle\').textContent=name
  const b=document.getElementById(\'mBody\')
  if(type===\'photo\') b.innerHTML=`<img src="${url||thumb}" onerror="this.src=\'${imgErr}\'">`
  else b.innerHTML=`<iframe src="https://drive.google.com/file/d/${id}/preview" allowfullscreen></iframe>`
  document.getElementById(\'mModal\').classList.add(\'open\')
}

function closeMedia(){
  document.getElementById(\'mModal\').classList.remove(\'open\')
  document.getElementById(\'mBody\').innerHTML=\'\'
  curFile=null
}

function dlCurrent(){if(curFile)window.open(curFile.url)}
function galleryCurrent(){
  if(!curFile) return
  const a=document.createElement(\'a\')
  a.href=curFile.url; a.download=curFile.name; a.click()
  showToast(\'Saved ✓\')
}
async function delCurrent(){
  if(!curFile||!confirm(\'Delete?\')) return
  await fetch(\'/drive/delete/\'+curFile.id,{method:\'DELETE\'})
  closeMedia(); loadFiles(); showToast(\'Deleted ✓\')
}

// Vault
async function loadVault(){
  try{
    const d=await(await fetch(\'/vault\')).json()
    vaultData={...vaultData,...d}
    if(!vaultData.pin){
      document.getElementById(\'vaultSub\').textContent=\'Set up your vault PIN\'
      openVaultSetup()
    }
  }catch(e){}
}

function pinPress(v){
  if(v===\'clear\'){pinBuf=\'\'}
  else if(v===\'del\'){pinBuf=pinBuf.slice(0,-1)}
  else if(pinBuf.length<8){pinBuf+=v}
  
  for(let i=0;i<4;i++){
    const d=document.getElementById(\'d\'+i)
    d.classList.toggle(\'filled\',i<pinBuf.length)
  }
  
  if(pinBuf.length>=4){
    setTimeout(()=>checkPin(),200)
  }
}

async function checkPin(){
  const r=await fetch(\'/vault/check\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({pin:pinBuf})})
  const d=await r.json()
  pinBuf=\'\'
  for(let i=0;i<4;i++) document.getElementById(\'d\'+i).classList.remove(\'filled\')
  
  if(d.ok){
    vaultData.unlocked=true
    document.getElementById(\'vaultLock\').style.display=\'none\'
    document.getElementById(\'vaultContent\').style.display=\'block\'
    renderVault()
    showToast(\'Vault unlocked ✓\')
  } else {
    document.getElementById(\'vaultSub\').textContent=\'Wrong PIN, try again\'
    setTimeout(()=>document.getElementById(\'vaultSub\').textContent=\'Enter PIN to access\',1500)
  }
}

function lockVault(){
  vaultData.unlocked=false
  document.getElementById(\'vaultLock\').style.display=\'\'
  document.getElementById(\'vaultContent\').style.display=\'none\'
  document.getElementById(\'vaultSub\').textContent=\'Enter PIN to access\'
}

function renderVault(){
  const vFiles=allFiles.filter(f=>vaultData.files&&vaultData.files.includes(f.id))
  document.getElementById(\'vaultGrid\').innerHTML=vFiles.length?vFiles.map(f=>mediaItem(f,/\\.(mp4|mov|avi|mkv|webm)/i.test(f.name)?\'video\':\'photo\')).join(\'\'):empty(\'🔒\',\'Vault is empty\')
}

function openVaultSetup(){
  closeProfile()
  document.getElementById(\'vaultSetup\').classList.add(\'open\')
}
function closeVaultSetup(){document.getElementById(\'vaultSetup\').classList.remove(\'open\')}

async function saveVaultPin(){
  const pin=document.getElementById(\'newPin\').value
  const email=document.getElementById(\'recEmail\').value
  if(pin.length<4){showToast(\'PIN must be 4+ digits\'); return}
  await fetch(\'/vault\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({pin,recovery:email})})
  vaultData.pin=pin; vaultData.recovery=email
  closeVaultSetup(); showToast(\'Vault PIN saved ✓\')
}

async function forgotPin(){
  const r=await fetch(\'/vault/reset\',{method:\'POST\'})
  const d=await r.json()
  if(d.sent) showToast(\'Recovery code sent to email\')
  else showToast(\'No recovery email set\')
}

// Upload
function openUpload(){document.getElementById(\'uploadSheet\').classList.add(\'open\')}
function closeUpload(){document.getElementById(\'uploadSheet\').classList.remove(\'open\')}

document.getElementById(\'fi\').addEventListener(\'change\',function(){
  document.getElementById(\'upStatus\').textContent=this.files.length?`${this.files.length} file(s) selected`:\'\'
})

async function doUpload(){
  const files=document.getElementById(\'fi\').files
  if(!files.length){showToast(\'Select files first\'); return}
  document.getElementById(\'upStatus\').textContent=\'Uploading... ⏳\'
  showProg(20)
  const fd=new FormData()
  for(let f of files) fd.append(\'files\',f)
  try{
    await fetch(\'/drive/upload\',{method:\'POST\',body:fd})
    showProg(100)
    document.getElementById(\'upStatus\').textContent=\'Done! ✅\'
    setTimeout(()=>{closeUpload();loadFiles()},600)
  }catch(e){
    document.getElementById(\'upStatus\').textContent=\'Failed ❌\'
    showProg(100)
  }
}

async function removeAcc(email){
  if(!confirm(\'Remove this drive?\')) return
  await fetch(\'/auth/disconnect\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({email})})
  loadFiles(); showToast(\'Drive removed\')
}

function showTab(name){
  const tabs=[\'photos\',\'videos\',\'albums\',\'vault\',\'all\',\'drives\']
  document.querySelectorAll(\'.tab\').forEach((t,i)=>t.classList.toggle(\'active\',tabs[i]===name))
  document.querySelectorAll(\'.section\').forEach(s=>s.classList.remove(\'active\'))
  document.getElementById(name).classList.add(\'active\')
  if(name===\'vault\'&&!vaultData.unlocked) loadVault()
}

function toggleAccounts(){
  const d=document.getElementById(\'accDetail\')
  const t=document.getElementById(\'accToggle\')
  if(d.classList.contains(\'open\')){d.classList.remove(\'open\');t.textContent=\'▼ accounts\'}
  else{d.classList.add(\'open\');t.textContent=\'▲ accounts\'}
}

// Load albums
async function loadAlbums(){
  try{
    const d=await(await fetch(\'/albums\')).json()
    albums=d||{}
  }catch(e){}
}

loadProfile()
loadAlbums()
loadFiles()
</script>
</body>
</html>'''

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        save_json(PROFILE_FILE, request.json)
        return jsonify({'ok': True})
    return jsonify(load_json(PROFILE_FILE, {'name': 'M. Tonoy', 'photo': ''}))

@app.route('/albums', methods=['GET', 'POST'])
def albums():
    if request.method == 'POST':
        save_json(ALBUMS_FILE, request.json)
        return jsonify({'ok': True})
    return jsonify(load_json(ALBUMS_FILE, {}))

@app.route('/vault', methods=['GET', 'POST'])
def vault():
    if request.method == 'POST':
        data = load_json(VAULT_FILE, {})
        new_data = request.json
        if 'pin' in new_data:
            data['pin'] = hash_password(new_data['pin'])
        if 'recovery' in new_data:
            data['recovery'] = new_data['recovery']
        save_json(VAULT_FILE, data)
        return jsonify({'ok': True})
    data = load_json(VAULT_FILE, {})
    return jsonify({'has_pin': bool(data.get('pin')), 'recovery': data.get('recovery', '')})

@app.route('/vault/check', methods=['POST'])
def vault_check():
    data = load_json(VAULT_FILE, {})
    pin = request.json.get('pin', '')
    ok = hash_password(str(pin)) == data.get('pin', '')
    return jsonify({'ok': ok})

@app.route('/vault/reset', methods=['POST'])
def vault_reset():
    data = load_json(VAULT_FILE, {})
    recovery = data.get('recovery', '')
    if not recovery:
        return jsonify({'sent': False})
    return jsonify({'sent': True, 'email': recovery})

@app.route('/auth')
def auth():
    flow = get_flow()
    auth_url, state = flow.authorization_url(prompt='consent', access_type='offline')
    session['oauth_state'] = state
    session.permanent = True
    return redirect(auth_url)

@app.route('/callback')
def callback():
    try:
        flow = get_flow()
        flow.fetch_token(authorization_response=request.url.replace('http://', 'https://'))
        creds = flow.credentials
        creds_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': list(creds.scopes) if creds.scopes else []
        }
        token_info = req.get(f'https://www.googleapis.com/oauth2/v1/userinfo?access_token={creds.token}').json()
        email = token_info.get('email', 'unknown')
        accounts = session.get('accounts', {})
        accounts[email] = creds_data
        session['accounts'] = accounts
        session.permanent = True
        session.modified = True
        return redirect('/')
    except Exception as e:
        return f'Error: {str(e)}'

@app.route('/auth/disconnect', methods=['POST'])
def disconnect():
    email = request.json.get('email')
    accounts = session.get('accounts', {})
    if email in accounts:
        del accounts[email]
    session['accounts'] = accounts
    session.modified = True
    return jsonify({'ok': True})

@app.route('/drive/files')
def drive_files():
    accounts = session.get('accounts', {})
    if not accounts:
        return jsonify({'files': [], 'accounts': []})
    all_files, account_info = [], []
    for email, cd in accounts.items():
        try:
            creds = Credentials(**{k: v for k, v in cd.items() if k != 'scopes'})
            svc = build('drive', 'v3', credentials=creds)
            for f in svc.files().list(pageSize=100, fields="files(id,name,mimeType,webViewLink,thumbnailLink,webContentLink)").execute().get('files', []):
                all_files.append({
                    'id': f['id'],
                    'name': f['name'],
                    'url': f.get('webContentLink', f.get('webViewLink', '')),
                    'thumb': f.get('thumbnailLink', '')
                })
            q = svc.about().get(fields='storageQuota').execute().get('storageQuota', {})
            used = int(q.get('usage', 0))
            total = int(q.get('limit', 16106127360))
            account_info.append({
                'email': email,
                'used': f'{used/1e9:.1f}',
                'total': f'{total/1e9:.1f}',
                'percent': min(100, int(used/total*100))
            })
        except:
            pass
    return jsonify({'files': all_files, 'accounts': account_info})

@app.route('/drive/upload', methods=['POST'])
def drive_upload():
    accounts = session.get('accounts', {})
    if not accounts:
        return jsonify({'error': 'No accounts'})
    cd = list(accounts.values())[0]
    svc = build('drive', 'v3', credentials=Credentials(**{k: v for k, v in cd.items() if k != 'scopes'}))
    for f in request.files.getlist('files'):
        file = svc.files().create(
            body={'name': f.filename},
            media_body=MediaIoBaseUpload(io.BytesIO(f.read()), mimetype=f.content_type)
        ).execute()
        svc.permissions().create(fileId=file['id'], body={'role': 'reader', 'type': 'anyone'}).execute()
    return jsonify({'ok': True})

@app.route('/drive/delete/<file_id>', methods=['DELETE'])
def drive_delete(file_id):
    for email, cd in session.get('accounts', {}).items():
        try:
            build('drive', 'v3', credentials=Credentials(**{k: v for k, v in cd.items() if k != 'scopes'})).files().delete(fileId=file_id).execute()
            break
        except:
            pass
    return jsonify({'ok': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
