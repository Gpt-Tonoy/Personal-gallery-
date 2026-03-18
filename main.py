import os, io, json
import requests as req
from flask import Flask, redirect, request, session, jsonify, render_template_string
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from datetime import datetime

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = 'tonoy-secret-2026'
app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_SAMESITE='None')

CLIENT_ID = '565165560969-k126trc6ugj7lp2au2l438k5di2ppg64.apps.googleusercontent.com'
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = 'https://personal-gallery-production-e2b9.up.railway.app/callback'
SCOPES = ['https://www.googleapis.com/auth/drive', 'openid', 'https://www.googleapis.com/auth/userinfo.email']

PROFILE_FILE = '/tmp/profile.json'

def get_flow():
    flow = Flow.from_client_config(
        {"web": {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
                 "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                 "token_uri": "https://oauth2.googleapis.com/token"}},
        scopes=SCOPES, redirect_uri=REDIRECT_URI)
    flow.code_verifier = ''
    return flow

def load_profile():
    try: return json.load(open(PROFILE_FILE))
    except: return {'name': 'M. Tonoy', 'photo': ''}

def save_profile(d): json.dump(d, open(PROFILE_FILE, 'w'))

HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<title>M. Tonoy Gallery</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;background:#000;color:#fff;min-height:100vh}
.header{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(0,0,0,0.95);backdrop-filter:blur(10px);padding:12px 16px;display:flex;align-items:center;justify-content:space-between}
.header-left{display:flex;align-items:center;gap:10px}
.profile-pic{width:36px;height:36px;border-radius:50%;object-fit:cover;border:2px solid #4285f4;cursor:pointer}
.profile-initial{width:36px;height:36px;border-radius:50%;background:#4285f4;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:bold;cursor:pointer}
.header h1{font-size:18px;font-weight:600}
.header-btns{display:flex;gap:8px}
.icon-btn{background:rgba(255,255,255,0.1);border:none;color:#fff;width:36px;height:36px;border-radius:50%;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center}

/* Storage */
.storage-section{margin-top:62px;padding:12px 16px;background:#111;border-bottom:1px solid #222}
.storage-total{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.storage-total span{font-size:13px;color:#aaa}
.storage-total strong{font-size:14px;color:#fff}
.total-bar{background:#333;border-radius:6px;height:6px;overflow:hidden}
.total-fill{background:linear-gradient(90deg,#4285f4,#34a853);border-radius:6px;height:6px;transition:width 0.5s}
.accounts-toggle{font-size:12px;color:#4285f4;cursor:pointer;margin-top:6px;display:inline-block}
.accounts-detail{display:none;margin-top:10px}
.accounts-detail.open{display:block}
.acc-chip{display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid #222}
.acc-chip:last-child{border-bottom:none}
.acc-chip span{font-size:11px;color:#888}
.acc-chip strong{font-size:11px;color:#aaa}

/* Tabs */
.tabs{display:flex;background:#000;border-bottom:1px solid #222;position:sticky;top:62px;z-index:99}
.tab{flex:1;padding:12px;text-align:center;font-size:13px;color:#666;cursor:pointer;border-bottom:2px solid transparent}
.tab.active{color:#fff;border-bottom:2px solid #fff}

.section{display:none;padding-bottom:80px}.section.active{display:block}

/* Grid */
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;padding:2px}
.media-item{position:relative;aspect-ratio:1;cursor:pointer;overflow:hidden;background:#111;user-select:none}
.media-item img{width:100%;height:100%;object-fit:cover;transition:opacity 0.2s}
.media-item.selected img{opacity:0.5}
.media-item.selected::after{content:\'✓\';position:absolute;top:6px;right:6px;background:#4285f4;border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:12px;color:#fff}
.play-icon{position:absolute;bottom:6px;left:6px;background:rgba(0,0,0,0.7);border-radius:4px;padding:2px 6px;font-size:10px}

/* Selection bar */
.select-bar{display:none;position:fixed;bottom:0;left:0;right:0;z-index:200;background:#1a1a1a;border-top:1px solid #333;padding:12px 16px}
.select-bar.open{display:block}
.select-bar-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.select-bar-btns{display:flex;gap:8px;justify-content:space-around}
.sel-btn{flex:1;background:rgba(255,255,255,0.1);border:none;color:#fff;padding:10px;border-radius:10px;font-size:12px;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:4px}
.sel-btn.danger{background:rgba(255,59,48,0.2);color:#ff3b30}
.sel-btn.success{background:rgba(52,199,89,0.2);color:#34c759}

/* FAB */
.upload-fab{position:fixed;bottom:20px;right:20px;z-index:150;background:#4285f4;border:none;color:#fff;width:56px;height:56px;border-radius:50%;font-size:24px;cursor:pointer;box-shadow:0 4px 20px rgba(66,133,244,0.5)}

/* Modals */
.modal{display:none;position:fixed;inset:0;z-index:300;background:rgba(0,0,0,0.98);flex-direction:column}
.modal.open{display:flex}
.modal-header{padding:16px;display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,0.5)}
.modal-close{background:none;border:none;color:#fff;font-size:24px;cursor:pointer;padding:4px}
.modal-body{flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden}
.modal-body img{max-width:100%;max-height:100%;object-fit:contain}
.modal-body iframe{width:100%;height:100%;border:none}
.modal-footer{padding:16px;display:flex;gap:10px;justify-content:center;background:rgba(0,0,0,0.5);flex-wrap:wrap}
.modal-btn{background:rgba(255,255,255,0.15);border:none;color:#fff;padding:10px 16px;border-radius:25px;cursor:pointer;font-size:13px}
.modal-btn.primary{background:#4285f4}
.modal-btn.danger{background:rgba(255,59,48,0.8)}

/* Upload Modal */
.overlay{display:none;position:fixed;inset:0;z-index:300;background:rgba(0,0,0,0.9);align-items:flex-end;justify-content:center}
.overlay.open{display:flex}
.sheet{background:#1a1a1a;border-radius:20px 20px 0 0;padding:20px;width:100%;max-width:500px}
.sheet h2{font-size:18px;margin-bottom:20px;text-align:center}
.upload-area{border:2px dashed #333;border-radius:12px;padding:30px;text-align:center;cursor:pointer;margin-bottom:15px}
.btn-full{width:100%;background:#4285f4;border:none;color:#fff;padding:14px;border-radius:12px;font-size:15px;cursor:pointer;margin-bottom:8px}
.btn-cancel{width:100%;background:rgba(255,255,255,0.1);border:none;color:#fff;padding:14px;border-radius:12px;font-size:15px;cursor:pointer}

/* Profile Modal */
.profile-modal{display:none;position:fixed;inset:0;z-index:400;background:rgba(0,0,0,0.95);flex-direction:column}
.profile-modal.open{display:flex}
.profile-content{flex:1;overflow-y:auto;padding:20px}
.profile-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}
.profile-avatar-big{width:80px;height:80px;border-radius:50%;object-fit:cover;border:3px solid #4285f4;cursor:pointer}
.profile-initial-big{width:80px;height:80px;border-radius:50%;background:#4285f4;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:bold;cursor:pointer;margin:0 auto 16px}
.profile-name-display{font-size:22px;font-weight:bold;text-align:center;margin-bottom:4px}
.profile-email{font-size:13px;color:#888;text-align:center;margin-bottom:24px}
.settings-section{background:#111;border-radius:12px;margin-bottom:16px;overflow:hidden}
.settings-item{padding:16px;border-bottom:1px solid #222;display:flex;align-items:center;justify-content:space-between;cursor:pointer}
.settings-item:last-child{border-bottom:none}
.settings-item-left{display:flex;align-items:center;gap:12px}
.settings-icon{font-size:20px;width:32px;text-align:center}
.settings-label{font-size:15px}
.settings-value{font-size:13px;color:#888}
input[type=text],input[type=password]{width:100%;padding:12px;background:#222;border:1px solid #333;border-radius:10px;color:#fff;font-size:15px;margin-top:8px}

.progress{display:none;position:fixed;top:0;left:0;right:0;height:3px;background:#4285f4;z-index:999}
.empty{text-align:center;padding:60px 20px;color:#555}
.empty-icon{font-size:48px;margin-bottom:12px}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div id="headerAvatar" onclick="openProfile()"></div>
    <h1 id="headerName">Gallery</h1>
  </div>
<div class="header-btns">
    <button class="icon-btn" onclick="openUpload()">⬆️</button>
    <a href="/auth" class="icon-btn" style="text-decoration:none;display:flex;align-items:center;justify-content:center">➕</a>
</div>
</div>
<div style="position:fixed;top:62px;left:0;right:0;z-index:98;background:#1a1a3e;padding:8px 16px;text-align:center">
  <a href="/auth" style="color:#4285f4;font-size:14px;text-decoration:none">+ Connect Google Drive Account</a>
</div>
<div class="storage-section">
  <div class="storage-total">
    <span id="storageText">Loading...</span>
    <strong id="storagePct">0%</strong>
  </div>
  <div class="total-bar"><div class="total-fill" id="totalFill" style="width:0%"></div></div>
  <span class="accounts-toggle" onclick="toggleAccounts()">▼ Show accounts</span>
  <div class="accounts-detail" id="accDetail"></div>
</div>

<div class="tabs">
  <div class="tab active" onclick="showTab(\'photos\')">Photos</div>
  <div class="tab" onclick="showTab(\'videos\')">Videos</div>
  <div class="tab" onclick="showTab(\'all\')">All</div>
  <div class="tab" onclick="showTab(\'drives\')">Drives</div>
</div>

<div id="photos" class="section active">
  <div class="grid" id="photoGrid"></div>
</div>
<div id="videos" class="section">
  <div class="grid" id="videoGrid"></div>
</div>
<div id="all" class="section">
  <div id="allList" style="padding:8px"></div>
</div>
<div id="drives" class="section">
  <div id="drivesList" style="padding:16px"></div>
  <div style="padding:0 16px 16px">
    <button class="btn-full" onclick="window.location.href=\'/auth\'">+ Connect Google Drive</button>
  </div>
</div>

<button class="upload-fab" id="uploadFab" onclick="openUpload()">+</button>

<!-- Selection Bar -->
<div class="select-bar" id="selectBar">
  <div class="select-bar-top">
    <span id="selectCount" style="font-size:14px;color:#aaa">0 selected</span>
    <div style="display:flex;gap:10px">
      <button onclick="selectAll()" style="background:none;border:none;color:#4285f4;font-size:13px;cursor:pointer">Select All</button>
      <button onclick="cancelSelect()" style="background:none;border:none;color:#ff3b30;font-size:13px;cursor:pointer">Cancel</button>
    </div>
  </div>
  <div class="select-bar-btns">
    <button class="sel-btn" onclick="downloadSelected()">⬇️<span>Download</span></button>
    <button class="sel-btn success" onclick="saveSelectedToGallery()">🖼️<span>Gallery</span></button>
    <button class="sel-btn danger" onclick="deleteSelected()">🗑️<span>Delete</span></button>
  </div>
</div>

<!-- Media Modal -->
<div class="modal" id="mediaModal">
  <div class="modal-header">
    <button class="modal-close" onclick="closeModal()">✕</button>
    <span id="modalTitle" style="font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px"></span>
    <span></span>
  </div>
  <div class="modal-body" id="modalBody"></div>
  <div class="modal-footer">
    <button class="modal-btn" onclick="downloadCurrent()">⬇️ Download</button>
    <button class="modal-btn primary" onclick="saveCurrent()">🖼️ Gallery</button>
    <button class="modal-btn danger" onclick="deleteCurrent()">🗑️ Delete</button>
  </div>
</div>

<!-- Upload Sheet -->
<div class="overlay" id="uploadOverlay">
  <div class="sheet">
    <h2>Upload Files</h2>
    <div class="upload-area" onclick="document.getElementById(\'fileInput\').click()">
      <div style="font-size:40px;margin-bottom:8px">📤</div>
      <div style="color:#888;font-size:14px">Tap to select photos & videos</div>
      <input type="file" id="fileInput" multiple accept="image/*,video/*" style="display:none">
    </div>
    <div id="uploadStatus" style="color:#888;font-size:13px;text-align:center;margin-bottom:12px;min-height:20px"></div>
    <button class="btn-full" onclick="uploadFiles()">Upload</button>
    <button class="btn-cancel" onclick="closeUpload()">Cancel</button>
  </div>
</div>

<!-- Profile Modal -->
<div class="profile-modal" id="profileModal">
  <div style="padding:16px;display:flex;justify-content:space-between;align-items:center">
    <button onclick="closeProfile()" style="background:none;border:none;color:#fff;font-size:24px;cursor:pointer">✕</button>
    <span style="font-size:16px;font-weight:600">Profile</span>
    <button onclick="saveProfile()" style="background:none;border:none;color:#4285f4;font-size:15px;cursor:pointer">Save</button>
  </div>
  <div class="profile-content">
    <div style="text-align:center;margin-bottom:24px">
      <div id="profileAvatarBig" onclick="document.getElementById(\'profilePhotoInput\').click()" style="cursor:pointer;margin:0 auto 12px"></div>
      <input type="file" id="profilePhotoInput" accept="image/*" style="display:none">
      <div style="font-size:12px;color:#4285f4">Tap to change photo</div>
    </div>
    <div class="settings-section">
      <div style="padding:16px">
        <div style="font-size:12px;color:#888;margin-bottom:4px">Display Name</div>
        <input type="text" id="profileNameInput" placeholder="Enter your name">
      </div>
    </div>
    <div class="settings-section">
      <div class="settings-item" onclick="window.location.href=\'/auth\'">
        <div class="settings-item-left">
          <span class="settings-icon">➕</span>
          <span class="settings-label">Add Google Drive</span>
        </div>
        <span style="color:#888">›</span>
      </div>
      <div class="settings-item" onclick="showTab(\'drives\');closeProfile()">
        <div class="settings-item-left">
          <span class="settings-icon">☁️</span>
          <span class="settings-label">Manage Drives</span>
        </div>
        <span style="color:#888">›</span>
      </div>
    </div>
  </div>
</div>

<div class="progress" id="progress"></div>

<script>
let allFiles = []
let selectedIds = new Set()
let selectMode = false
let currentFile = null
let longPressTimer = null
let profileData = {name: \'M. Tonoy\', photo: \'\'}

// Load profile
async function loadProfile(){
  try{
    const d = await(await fetch(\'/profile\')).json()
    profileData = d
    updateProfileUI()
  }catch(e){}
}

function updateProfileUI(){
  const name = profileData.name || \'M. Tonoy\'
  document.getElementById(\'headerName\').textContent = name
  document.getElementById(\'profileNameInput\').value = name
  const avatar = document.getElementById(\'headerAvatar\')
  const avatarBig = document.getElementById(\'profileAvatarBig\')
  if(profileData.photo){
    avatar.innerHTML = `<img src="${profileData.photo}" class="profile-pic" onclick="openProfile()">`
    avatarBig.innerHTML = `<img src="${profileData.photo}" class="profile-avatar-big">`
  } else {
    const initial = name.charAt(0).toUpperCase()
    avatar.innerHTML = `<div class="profile-initial" onclick="openProfile()">${initial}</div>`
    avatarBig.innerHTML = `<div class="profile-initial-big">${initial}</div>`
  }
}

document.getElementById(\'profilePhotoInput\').addEventListener(\'change\', function(){
  const file = this.files[0]
  if(!file) return
  const reader = new FileReader()
  reader.onload = e => {
    profileData.photo = e.target.result
    updateProfileUI()
  }
  reader.readAsDataURL(file)
})

async function saveProfile(){
  profileData.name = document.getElementById(\'profileNameInput\').value || \'M. Tonoy\'
  await fetch(\'/profile\', {method:\'POST\', headers:{\'Content-Type\':\'application/json\'}, body:JSON.stringify(profileData)})
  updateProfileUI()
  closeProfile()
}

function openProfile(){ document.getElementById(\'profileModal\').classList.add(\'open\') }
function closeProfile(){ document.getElementById(\'profileModal\').classList.remove(\'open\') }

// Load files
async function loadFiles(){
  document.getElementById(\'progress\').style.display = \'block\'
  try{
    const d = await(await fetch(\'/drive/files\')).json()
    allFiles = d.files || []
    
    // Total storage
    if(d.accounts && d.accounts.length){
      let totalUsed = 0, totalSpace = 0
      d.accounts.forEach(a=>{
        totalUsed += parseFloat(a.used)
        totalSpace += parseFloat(a.total)
      })
      const pct = totalSpace > 0 ? Math.min(100, (totalUsed/totalSpace*100).toFixed(1)) : 0
      document.getElementById(\'storageText\').textContent = `${totalUsed.toFixed(1)} GB used of ${totalSpace.toFixed(1)} GB`
      document.getElementById(\'storagePct\').textContent = `${pct}%`
      document.getElementById(\'totalFill\').style.width = pct + \'%\'
      
      // Account details
      document.getElementById(\'accDetail\').innerHTML = d.accounts.map(a=>`
        <div class="acc-chip">
          <span>${a.email}</span>
          <strong>${a.used} / ${a.total}</strong>
        </div>`).join(\'\')
      
      // Drives tab
      document.getElementById(\'drivesList\').innerHTML = d.accounts.map(a=>`
        <div style="background:#111;border-radius:12px;padding:16px;margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <span style="font-size:14px">📧 ${a.email}</span>
            <button onclick="removeAcc(\'${a.email}\')" style="background:rgba(255,59,48,0.2);border:1px solid rgba(255,59,48,0.3);color:#ff3b30;padding:4px 10px;border-radius:20px;font-size:11px;cursor:pointer">Remove</button>
          </div>
          <div style="background:#222;border-radius:4px;height:4px;margin-bottom:6px">
            <div style="background:#4285f4;border-radius:4px;height:4px;width:${a.percent}%"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:11px;color:#888">
            <span>${a.used} used</span><span>${a.total} total</span>
          </div>
        </div>`).join(\'\')
    } else {
      document.getElementById(\'storageText\').textContent = \'No drives connected\'
      document.getElementById(\'storagePct\').textContent = \'\'
    }
    
    // Photos
    const photos = allFiles.filter(f=>/\\.(jpg|jpeg|png|gif|webp|heic)/i.test(f.name))
    renderGrid(\'photoGrid\', photos, \'📷\')
    
    // Videos  
    const videos = allFiles.filter(f=>/\\.(mp4|mov|avi|mkv|webm|3gp)/i.test(f.name))
    renderGrid(\'videoGrid\', videos, \'🎬\', true)
    
    // All files
    renderAllList(allFiles)
    
  }catch(e){console.log(e)}
  document.getElementById(\'progress\').style.display = \'none\'
}

function renderGrid(gridId, files, emptyIcon, isVideo=false){
  const grid = document.getElementById(gridId)
  if(!files.length){
    grid.innerHTML = `<div class="empty" style="grid-column:span 3"><div class="empty-icon">${emptyIcon}</div><div>Nothing here yet</div></div>`
    return
  }
  grid.innerHTML = files.map(f=>`
    <div class="media-item" id="item_${f.id}"
      ontouchstart="startLongPress(\'${f.id}\')"
      ontouchend="endLongPress()"
      ontouchmove="endLongPress()"
      onclick="handleClick(\'${f.id}\',\'${f.name}\',\'${isVideo?\'video\':\'photo\'}\',\'${f.url}\',\'${f.thumb}\')">
      <img src="${f.thumb||\'data:image/svg+xml,<svg xmlns=\\"http://www.w3.org/2000/svg\\" viewBox=\\"0 0 100 100\\"><rect fill=\\"#1a1a1a\\"/><text y=\\"55\\" x=\\"50\\" text-anchor=\\"middle\\" fill=\\"#555\\" font-size=\\"30\\">${isVideo?\'🎬\':\'📷\'}</text></svg>\'}" loading="lazy">
      ${isVideo?\'<div class="play-icon">▶</div>\':\'\'} 
    </div>`).join(\'\')
}

function renderAllList(files){
  const al = document.getElementById(\'allList\')
  if(!files.length){
    al.innerHTML = \'<div class="empty"><div class="empty-icon">📁</div><div>No files yet</div></div>\'
    return
  }
  al.innerHTML = files.map(f=>`
    <div style="display:flex;align-items:center;gap:12px;padding:12px;background:#111;border-radius:10px;margin-bottom:8px">
      <div style="font-size:24px">${/\\.(jpg|jpeg|png|gif|webp)/i.test(f.name)?\'🖼️\':/\\.(mp4|mov|avi|mkv|webm)/i.test(f.name)?\'🎬\':\'📄\'}</div>
      <div style="flex:1;overflow:hidden">
        <div style="font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${f.name}</div>
      </div>
      <button onclick="window.open(\'${f.url}\')" style="background:rgba(255,255,255,0.1);border:none;color:#fff;padding:6px 12px;border-radius:20px;font-size:11px;cursor:pointer">⬇️</button>
    </div>`).join(\'\')
}

// Long press for selection
function startLongPress(id){
  longPressTimer = setTimeout(()=>{
    if(!selectMode) enterSelectMode()
    toggleSelect(id)
  }, 600)
}
function endLongPress(){ clearTimeout(longPressTimer) }

function enterSelectMode(){
  selectMode = true
  document.getElementById(\'selectBar\').classList.add(\'open\')
  document.getElementById(\'uploadFab\').style.display = \'none\'
}

function cancelSelect(){
  selectMode = false
  selectedIds.clear()
  document.getElementById(\'selectBar\').classList.remove(\'open\')
  document.getElementById(\'uploadFab\').style.display = \'flex\'
  document.querySelectorAll(\'.media-item\').forEach(el=>el.classList.remove(\'selected\'))
  updateSelectCount()
}

function toggleSelect(id){
  const el = document.getElementById(\'item_\'+id)
  if(!el) return
  if(selectedIds.has(id)){
    selectedIds.delete(id)
    el.classList.remove(\'selected\')
  } else {
    selectedIds.add(id)
    el.classList.add(\'selected\')
  }
  updateSelectCount()
}

function handleClick(id, name, type, url, thumb){
  if(selectMode){
    toggleSelect(id)
  } else {
    openMedia(id, name, type, url, thumb)
  }
}

function selectAll(){
  const activeTab = document.querySelector(\'.section.active\')
  activeTab.querySelectorAll(\'.media-item\').forEach(el=>{
    const id = el.id.replace(\'item_\',\'\')
    selectedIds.add(id)
    el.classList.add(\'selected\')
  })
  updateSelectCount()
}

function updateSelectCount(){
  document.getElementById(\'selectCount\').textContent = `${selectedIds.size} selected`
  if(selectedIds.size === 0 && selectMode) cancelSelect()
}

async function downloadSelected(){
  for(let id of selectedIds){
    const f = allFiles.find(x=>x.id===id)
    if(f) window.open(f.url)
  }
  cancelSelect()
}

async function saveSelectedToGallery(){
  for(let id of selectedIds){
    const f = allFiles.find(x=>x.id===id)
    if(f){
      const a = document.createElement(\'a\')
      a.href = f.url
      a.download = f.name
      a.click()
      await new Promise(r=>setTimeout(r,500))
    }
  }
  cancelSelect()
}

async function deleteSelected(){
  if(!confirm(`Delete ${selectedIds.size} file(s)?`)) return
  for(let id of selectedIds){
    await fetch(\'/drive/delete/\'+id, {method:\'DELETE\'})
  }
  cancelSelect()
  loadFiles()
}

// Media modal
function openMedia(id, name, type, url, thumb){
  currentFile = {id, name, type, url, thumb}
  document.getElementById(\'modalTitle\').textContent = name
  const body = document.getElementById(\'modalBody\')
  if(type === \'photo\'){
    body.innerHTML = `<img src="${url||thumb}" style="max-width:100%;max-height:80vh;object-fit:contain">`
  } else {
    body.innerHTML = `<iframe src="https://drive.google.com/file/d/${id}/preview" allowfullscreen></iframe>`
  }
  document.getElementById(\'mediaModal\').classList.add(\'open\')
}

function closeModal(){
  document.getElementById(\'mediaModal\').classList.remove(\'open\')
  document.getElementById(\'modalBody\').innerHTML = \'\'
  currentFile = null
}

function downloadCurrent(){ if(currentFile) window.open(currentFile.url) }
function saveCurrent(){
  if(!currentFile) return
  const a = document.createElement(\'a\')
  a.href = currentFile.url
  a.download = currentFile.name
  a.click()
}
async function deleteCurrent(){
  if(!currentFile) return
  if(!confirm(\'Delete this file?\')) return
  await fetch(\'/drive/delete/\'+currentFile.id, {method:\'DELETE\'})
  closeModal()
  loadFiles()
}

// Upload
function openUpload(){ document.getElementById(\'uploadOverlay\').classList.add(\'open\') }
function closeUpload(){ document.getElementById(\'uploadOverlay\').classList.remove(\'open\') }

document.getElementById(\'fileInput\').addEventListener(\'change\', function(){
  document.getElementById(\'uploadStatus\').textContent = this.files.length > 0 ? `${this.files.length} file(s) selected` : \'\'
})

async function uploadFiles(){
  const files = document.getElementById(\'fileInput\').files
  if(!files.length) return alert(\'Select files first!\')
  document.getElementById(\'uploadStatus\').textContent = \'Uploading... ⏳\'
  document.getElementById(\'progress\').style.display = \'block\'
  const fd = new FormData()
  for(let f of files) fd.append(\'files\', f)
  try{
    await fetch(\'/drive/upload\', {method:\'POST\', body:fd})
    document.getElementById(\'uploadStatus\').textContent = \'Done! ✅\'
    setTimeout(()=>{ closeUpload(); loadFiles() }, 800)
  }catch(e){
    document.getElementById(\'uploadStatus\').textContent = \'Failed ❌\'
  }
  document.getElementById(\'progress\').style.display = \'none\'
}

async function removeAcc(email){
  if(!confirm(\'Remove this drive?\')) return
  await fetch(\'/auth/disconnect\', {method:\'POST\', headers:{\'Content-Type\':\'application/json\'}, body:JSON.stringify({email})})
  loadFiles()
}

function showTab(name){
  document.querySelectorAll(\'.tab\').forEach((t,i)=>t.classList.toggle(\'active\',[\'photos\',\'videos\',\'all\',\'drives\'][i]===name))
  document.querySelectorAll(\'.section\').forEach(s=>s.classList.remove(\'active\'))
  document.getElementById(name).classList.add(\'active\')
}

function toggleAccounts(){
  const d = document.getElementById(\'accDetail\')
  const btn = document.querySelector(\'.accounts-toggle\')
  if(d.classList.contains(\'open\')){
    d.classList.remove(\'open\')
    btn.textContent = \'▼ Show accounts\'
  } else {
    d.classList.add(\'open\')
    btn.textContent = \'▲ Hide accounts\'
  }
}

loadProfile()
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
        save_profile(request.json)
        return jsonify({'ok': True})
    return jsonify(load_profile())

@app.route('/auth')
def auth():
    flow = get_flow()
    auth_url, state = flow.authorization_url(prompt='consent', access_type='offline')
    session['state'] = state
    return redirect(auth_url)

@app.route('/callback')
def callback():
    try:
        flow = get_flow()
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
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
        svc.permissions().create(
            fileId=file['id'],
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()
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
