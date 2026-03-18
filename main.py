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

def get_flow():
    flow = Flow.from_client_config(
        {"web": {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
                 "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                 "token_uri": "https://oauth2.googleapis.com/token"}},
        scopes=SCOPES, redirect_uri=REDIRECT_URI)
    flow.code_verifier = ''
    return flow

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
body{font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;background:#000;color:#fff;min-height:100vh;overflow-x:hidden}
.header{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(0,0,0,0.9);backdrop-filter:blur(10px);padding:12px 16px;display:flex;align-items:center;justify-content:space-between}
.header h1{font-size:20px;font-weight:600;color:#fff}
.header-btns{display:flex;gap:10px}
.icon-btn{background:rgba(255,255,255,0.1);border:none;color:#fff;width:36px;height:36px;border-radius:50%;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center}
.storage-bar{background:rgba(255,255,255,0.05);padding:8px 16px;margin-top:60px;display:flex;gap:10px;overflow-x:auto;scrollbar-width:none}
.storage-bar::-webkit-scrollbar{display:none}
.storage-chip{background:rgba(255,255,255,0.1);border-radius:20px;padding:6px 12px;font-size:11px;white-space:nowrap;display:flex;align-items:center;gap:6px}
.storage-chip .dot{width:8px;height:8px;border-radius:50%;background:#4285f4}
.tabs{display:flex;background:#111;border-bottom:1px solid #222;position:sticky;top:60px;z-index:99}
.tab{flex:1;padding:12px;text-align:center;font-size:13px;color:#888;cursor:pointer;border-bottom:2px solid transparent}
.tab.active{color:#fff;border-bottom:2px solid #fff}
.section{display:none;padding-bottom:80px}.section.active{display:block}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;padding:2px}
.media-item{position:relative;aspect-ratio:1;cursor:pointer;overflow:hidden;background:#111}
.media-item img{width:100%;height:100%;object-fit:cover;transition:opacity 0.2s}
.media-item:active img{opacity:0.7}
.play-icon{position:absolute;bottom:6px;left:6px;background:rgba(0,0,0,0.7);border-radius:4px;padding:2px 6px;font-size:10px}
.media-duration{position:absolute;bottom:6px;right:6px;background:rgba(0,0,0,0.7);border-radius:4px;padding:2px 5px;font-size:10px}
.upload-fab{position:fixed;bottom:20px;right:20px;z-index:200;background:#4285f4;border:none;color:#fff;width:56px;height:56px;border-radius:50%;font-size:24px;cursor:pointer;box-shadow:0 4px 20px rgba(66,133,244,0.5);display:flex;align-items:center;justify-content:center}
.modal{display:none;position:fixed;inset:0;z-index:300;background:rgba(0,0,0,0.98);flex-direction:column}
.modal.open{display:flex}
.modal-header{padding:16px;display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,0.5)}
.modal-close{background:none;border:none;color:#fff;font-size:24px;cursor:pointer}
.modal-title{font-size:16px;font-weight:500}
.modal-body{flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden}
.modal-body img{max-width:100%;max-height:100%;object-fit:contain}
.modal-body iframe{width:100%;height:100%;border:none}
.modal-footer{padding:16px;display:flex;gap:12px;justify-content:center;background:rgba(0,0,0,0.5)}
.modal-btn{background:rgba(255,255,255,0.15);border:none;color:#fff;padding:10px 20px;border-radius:25px;cursor:pointer;font-size:14px;display:flex;align-items:center;gap:6px}
.modal-btn.primary{background:#4285f4}
.upload-modal{display:none;position:fixed;inset:0;z-index:300;background:rgba(0,0,0,0.9);flex-direction:column;align-items:center;justify-content:center;padding:20px}
.upload-modal.open{display:flex}
.upload-box{background:#111;border-radius:20px;padding:30px;width:100%;max-width:400px;text-align:center}
.upload-box h2{font-size:18px;margin-bottom:20px}
.upload-area{border:2px dashed #333;border-radius:12px;padding:30px;margin-bottom:15px;cursor:pointer}
.upload-area input{display:none}
.acc-list{padding:16px}
.acc-card{background:#111;border-radius:12px;padding:16px;margin-bottom:12px}
.acc-email{font-size:14px;margin-bottom:8px}
.acc-bar{background:#222;border-radius:4px;height:4px;margin-bottom:6px}
.acc-fill{background:#4285f4;border-radius:4px;height:4px}
.acc-info{font-size:11px;color:#888;display:flex;justify-content:space-between}
.connect-btn{width:100%;background:#4285f4;border:none;color:#fff;padding:14px;border-radius:12px;font-size:15px;cursor:pointer;margin-top:12px}
.remove-btn{background:rgba(255,59,48,0.2);border:1px solid rgba(255,59,48,0.3);color:#ff3b30;padding:5px 12px;border-radius:20px;font-size:11px;cursor:pointer;float:right}
.empty{text-align:center;padding:60px 20px;color:#555}
.empty-icon{font-size:48px;margin-bottom:12px}
.progress{display:none;position:fixed;top:0;left:0;right:0;height:3px;background:#4285f4;z-index:999;animation:progress 2s ease infinite}
@keyframes progress{0%{width:0%}100%{width:100%}}
</style>
</head>
<body>

<div class="header">
  <h1>📸 M. Tonoy</h1>
  <div class="header-btns">
    <button class="icon-btn" onclick="showAccounts()">👤</button>
    <button class="icon-btn" onclick="openUpload()">☁️</button>
  </div>
</div>

<div class="storage-bar" id="storageBar">
  <div class="storage-chip">Loading...</div>
</div>

<div class="tabs">
  <div class="tab active" onclick="showTab(\'photos\')">Photos</div>
  <div class="tab" onclick="showTab(\'videos\')">Videos</div>
  <div class="tab" onclick="showTab(\'all\')">All Files</div>
  <div class="tab" onclick="showTab(\'accounts\')">Drives</div>
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

<div id="accounts" class="section">
  <div class="acc-list" id="accList"></div>
  <div style="padding:0 16px">
    <button class="connect-btn" onclick="window.location.href=\'/auth\'">+ Connect Google Drive</button>
  </div>
</div>

<button class="upload-fab" onclick="openUpload()">+</button>

<!-- Media Modal -->
<div class="modal" id="mediaModal">
  <div class="modal-header">
    <button class="modal-close" onclick="closeModal()">✕</button>
    <span class="modal-title" id="modalTitle">Photo</span>
    <span></span>
  </div>
  <div class="modal-body" id="modalBody"></div>
  <div class="modal-footer">
    <button class="modal-btn" onclick="downloadFile()">⬇️ Download</button>
    <button class="modal-btn primary" onclick="saveToGallery()">🖼️ Save to Gallery</button>
  </div>
</div>

<!-- Upload Modal -->
<div class="upload-modal" id="uploadModal">
  <div class="upload-box">
    <h2>Upload Files</h2>
    <div class="upload-area" onclick="document.getElementById(\'fileInput\').click()">
      <div style="font-size:40px;margin-bottom:10px">📤</div>
      <div style="color:#888;font-size:14px">Tap to select files</div>
      <input type="file" id="fileInput" multiple accept="image/*,video/*">
    </div>
    <div id="uploadStatus" style="color:#888;font-size:13px;margin-bottom:15px"></div>
    <button class="connect-btn" onclick="uploadFiles()">Upload</button>
    <button class="modal-btn" onclick="closeUpload()" style="width:100%;margin-top:10px;justify-content:center">Cancel</button>
  </div>
</div>

<div class="progress" id="progress"></div>

<script>
let currentFile = null
let allFiles = []

async function loadFiles(){
  document.getElementById(\'progress\').style.display=\'block\'
  try{
    const d = await(await fetch(\'/drive/files\')).json()
    allFiles = d.files || []
    
    // Storage bar
    const sb = document.getElementById(\'storageBar\')
    if(d.accounts && d.accounts.length){
      sb.innerHTML = d.accounts.map(a=>`
        <div class="storage-chip">
          <div class="dot"></div>
          ${a.email.split(\'@\')[0]} · ${a.used}/${a.total}
        </div>`).join(\'\')
    } else {
      sb.innerHTML=\'<div class="storage-chip">No drives connected</div>\'
    }
    
    // Photos
    const photos = allFiles.filter(f=>/\\.(jpg|jpeg|png|gif|webp|heic)/i.test(f.name))
    const pg = document.getElementById(\'photoGrid\')
    pg.innerHTML = photos.length ? photos.map(f=>`
      <div class="media-item" onclick="openMedia(\'${f.id}\',\'${f.name}\',\'photo\',\'${f.url}\',\'${f.thumb}\')">
        <img src="${f.thumb||f.url}" loading="lazy" onerror="this.src=\'data:image/svg+xml,<svg xmlns=\\"http://www.w3.org/2000/svg\\" viewBox=\\"0 0 100 100\\"><rect fill=\\"#222\\"/><text y=\\"55\\" x=\\"50\\" text-anchor=\\"middle\\" fill=\\"#666\\" font-size=\\"30\\">📷</text></svg>\'">
      </div>`).join(\'\') : \'<div class="empty" style="grid-column:span 3"><div class="empty-icon">📷</div><div>No photos yet</div></div>\'
    
    // Videos
    const videos = allFiles.filter(f=>/\\.(mp4|mov|avi|mkv|webm|3gp)/i.test(f.name))
    const vg = document.getElementById(\'videoGrid\')
    vg.innerHTML = videos.length ? videos.map(f=>`
      <div class="media-item" onclick="openMedia(\'${f.id}\',\'${f.name}\',\'video\',\'${f.url}\',\'${f.thumb}\')">
        <img src="${f.thumb||\'data:image/svg+xml,<svg xmlns=\\"http://www.w3.org/2000/svg\\" viewBox=\\"0 0 100 100\\"><rect fill=\\"#1a1a1a\\"/><text y=\\"55\\" x=\\"50\\" text-anchor=\\"middle\\" fill=\\"#666\\" font-size=\\"30\\">🎬</text></svg>\'}" loading="lazy">
        <div class="play-icon">▶</div>
      </div>`).join(\'\') : \'<div class="empty" style="grid-column:span 3"><div class="empty-icon">🎬</div><div>No videos yet</div></div>\'
    
    // All files
    const al = document.getElementById(\'allList\')
    al.innerHTML = allFiles.length ? allFiles.map(f=>`
      <div style="display:flex;align-items:center;gap:12px;padding:12px;background:#111;border-radius:10px;margin-bottom:8px">
        <div style="font-size:24px">${/\\.(jpg|jpeg|png|gif|webp)/i.test(f.name)?\'🖼️\':/\\.(mp4|mov|avi|mkv|webm)/i.test(f.name)?\'🎬\':\'📄\'}</div>
        <div style="flex:1;overflow:hidden">
          <div style="font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${f.name}</div>
        </div>
        <button onclick="window.open(\'${f.url}\')" style="background:rgba(255,255,255,0.1);border:none;color:#fff;padding:6px 12px;border-radius:20px;font-size:11px;cursor:pointer">⬇️</button>
      </div>`).join(\'\') : \'<div class="empty"><div class="empty-icon">📁</div><div>No files yet</div></div>\'
    
    // Accounts
    showAccList(d.accounts || [])
    
  }catch(e){console.log(e)}
  document.getElementById(\'progress\').style.display=\'none\'
}

function showAccList(accounts){
  const al = document.getElementById(\'accList\')
  al.innerHTML = accounts.length ? accounts.map(a=>`
    <div class="acc-card">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div class="acc-email">${a.email}</div>
        <button class="remove-btn" onclick="removeAcc(\'${a.email}\')">Remove</button>
      </div>
      <div class="acc-bar"><div class="acc-fill" style="width:${a.percent}%"></div></div>
      <div class="acc-info"><span>${a.used} used</span><span>${a.total} total</span></div>
    </div>`).join(\'\') : \'<div class="empty"><div class="empty-icon">☁️</div><div>No drives connected</div></div>\'
}

function openMedia(id, name, type, url, thumb){
  currentFile = {id, name, type, url, thumb}
  document.getElementById(\'modalTitle\').textContent = name
  const body = document.getElementById(\'modalBody\')
  if(type === \'photo\'){
    body.innerHTML = `<img src="${url||thumb}" style="max-width:100%;max-height:80vh;object-fit:contain">`
  } else {
    body.innerHTML = `<iframe src="https://drive.google.com/file/d/${id}/preview" allowfullscreen style="width:100%;height:60vh"></iframe>`
  }
  document.getElementById(\'mediaModal\').classList.add(\'open\')
}

function closeModal(){
  document.getElementById(\'mediaModal\').classList.remove(\'open\')
  document.getElementById(\'modalBody\').innerHTML = \'\'
  currentFile = null
}

function downloadFile(){
  if(currentFile) window.open(currentFile.url)
}

function saveToGallery(){
  if(!currentFile) return
  const a = document.createElement(\'a\')
  a.href = currentFile.url
  a.download = currentFile.name
  a.click()
}

function openUpload(){ document.getElementById(\'uploadModal\').classList.add(\'open\') }
function closeUpload(){ document.getElementById(\'uploadModal\').classList.remove(\'open\') }

document.getElementById(\'fileInput\').addEventListener(\'change\', function(){
  const count = this.files.length
  document.getElementById(\'uploadStatus\').textContent = count > 0 ? `${count} file(s) selected` : \'\'
})

async function uploadFiles(){
  const files = document.getElementById(\'fileInput\').files
  if(!files.length) return alert(\'Select files first!\')
  document.getElementById(\'uploadStatus\').textContent = \'Uploading...\'
  document.getElementById(\'progress\').style.display = \'block\'
  const fd = new FormData()
  for(let f of files) fd.append(\'files\', f)
  try{
    await fetch(\'/drive/upload\', {method:\'POST\', body:fd})
    document.getElementById(\'uploadStatus\').textContent = \'Upload complete! ✅\'
    setTimeout(()=>{ closeUpload(); loadFiles() }, 1000)
  }catch(e){
    document.getElementById(\'uploadStatus\').textContent = \'Upload failed ❌\'
  }
  document.getElementById(\'progress\').style.display = \'none\'
}

async function removeAcc(email){
  await fetch(\'/auth/disconnect\', {method:\'POST\', headers:{\'Content-Type\':\'application/json\'}, body:JSON.stringify({email})})
  loadFiles()
}

function showTab(name){
  document.querySelectorAll(\'.tab\').forEach((t,i)=>t.classList.toggle(\'active\',[\'photos\',\'videos\',\'all\',\'accounts\'][i]===name))
  document.querySelectorAll(\'.section\').forEach(s=>s.classList.remove(\'active\'))
  document.getElementById(name).classList.add(\'active\')
}

function showAccounts(){ showTab(\'accounts\') }

loadFiles()
</script>
</body>
</html>'''

@app.route('/')
def home():
    return render_template_string(HTML)

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
                'used': f'{used/1e9:.1f} GB',
                'total': f'{total/1e9:.1f} GB',
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
