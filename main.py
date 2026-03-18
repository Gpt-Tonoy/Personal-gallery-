import os, io, json
import requests as req
from flask import Flask, redirect, request, session, url_for, jsonify, render_template_string
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = 'tonoy-secret-2026'
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='None'
)

CLIENT_ID = '565165560969-k126trc6ugj7lp2au2l438k5di2ppg64.apps.googleusercontent.com'
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = 'https://personal-gallery-production-e2b9.up.railway.app/callback'
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email'
]

def get_flow():
    return Flow.from_client_config(
        {"web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }},
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

def get_credentials():
    if 'credentials' not in session:
        return None
    return Credentials(**{k: v for k, v in session['credentials'].items() if k != 'scopes'})

@app.route('/')
def home():
    return render_template_string(open('/app/templates/index.html').read() if os.path.exists('/app/templates/index.html') else HTML)

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
        flow.fetch_token(authorization_response=request.url.replace('http://', 'https://'))
        creds = flow.credentials
        session['credentials'] = {
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
        accounts[email] = session['credentials']
        session['accounts'] = accounts
        return redirect('/')
    except Exception as e:
        return f'Error: {str(e)}'

@app.route('/drive/files')
def drive_files():
    accounts = session.get('accounts', {})
    if not accounts:
        return jsonify({'files': [], 'accounts': []})
    all_files = []
    account_info = []
    for email, creds_data in accounts.items():
        try:
            creds = Credentials(**{k: v for k, v in creds_data.items() if k != 'scopes'})
            service = build('drive', 'v3', credentials=creds)
            results = service.files().list(pageSize=50, fields="files(id,name,mimeType,webViewLink,thumbnailLink)").execute()
            for f in results.get('files', []):
                all_files.append({'id': f['id'], 'name': f['name'], 'url': f.get('webViewLink',''), 'thumb': f.get('thumbnailLink','')})
            about = service.about().get(fields='storageQuota').execute()
            quota = about.get('storageQuota', {})
            used = int(quota.get('usage', 0))
            total = int(quota.get('limit', 16106127360))
            account_info.append({'email': email, 'used': f'{used/1e9:.1f} GB', 'total': f'{total/1e9:.1f} GB', 'percent': min(100, int(used/total*100))})
        except:
            pass
    return jsonify({'files': all_files, 'accounts': account_info})

@app.route('/drive/upload', methods=['POST'])
def drive_upload():
    accounts = session.get('accounts', {})
    if not accounts:
        return jsonify({'error': 'No accounts'})
    creds_data = list(accounts.values())[0]
    creds = Credentials(**{k: v for k, v in creds_data.items() if k != 'scopes'})
    service = build('drive', 'v3', credentials=creds)
    for f in request.files.getlist('files'):
        media = MediaIoBaseUpload(io.BytesIO(f.read()), mimetype=f.content_type)
        service.files().create(body={'name': f.filename}, media_body=media).execute()
    return jsonify({'ok': True})

@app.route('/drive/delete/<file_id>', methods=['DELETE'])
def drive_delete(file_id):
    accounts = session.get('accounts', {})
    for email, creds_data in accounts.items():
        try:
            creds = Credentials(**{k: v for k, v in creds_data.items() if k != 'scopes'})
            service = build('drive', 'v3', credentials=creds)
            service.files().delete(fileId=file_id).execute()
            break
        except:
            pass
    return jsonify({'ok': True})

@app.route('/auth/disconnect', methods=['POST'])
def disconnect():
    email = request.json.get('email')
    accounts = session.get('accounts', {})
    if email in accounts:
        del accounts[email]
    session['accounts'] = accounts
    return jsonify({'ok': True})

@app.route('/notes', methods=['GET', 'POST'])
def notes():
    from datetime import datetime
    NOTES_FILE = '/tmp/notes.json'
    def load():
        try:
            with open(NOTES_FILE) as f: return json.load(f)
        except: return []
    def save(d):
        with open(NOTES_FILE, 'w') as f: json.dump(d, f)
    if request.method == 'POST':
        data = load()
        note = request.json
        note['date'] = datetime.now().strftime('%d %b %Y')
        data.append(note)
        save(data)
        return jsonify({'ok': True})
    return jsonify(load())

@app.route('/notes/<int:i>', methods=['DELETE'])
def delete_note(i):
    NOTES_FILE = '/tmp/notes.json'
    try:
        with open(NOTES_FILE) as f: data = json.load(f)
    except: data = []
    if i < len(data): data.pop(i)
    with open(NOTES_FILE, 'w') as f: json.dump(data, f)
    return jsonify({'ok': True})

@app.route('/todos', methods=['GET', 'POST'])
def todos():
    TODO_FILE = '/tmp/todos.json'
    def load():
        try:
            with open(TODO_FILE) as f: return json.load(f)
        except: return []
    def save(d):
        with open(TODO_FILE, 'w') as f: json.dump(d, f)
    if request.method == 'POST':
        data = load()
        data.append({'text': request.json['text'], 'done': False})
        save(data)
        return jsonify({'ok': True})
    return jsonify(load())

@app.route('/todos/<int:i>', methods=['DELETE', 'PATCH'])
def todo_action(i):
    TODO_FILE = '/tmp/todos.json'
    def load():
        try:
            with open(TODO_FILE) as f: return json.load(f)
        except: return []
    def save(d):
        with open(TODO_FILE, 'w') as f: json.dump(d, f)
    data = load()
    if i < len(data):
        if request.method == 'DELETE': data.pop(i)
        else: data[i]['done'] = not data[i]['done']
    save(data)
    return jsonify({'ok': True})

HTML = '''<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>M. Tonoy\'s Gallery</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:\'Segoe UI\',sans-serif;background:#0a0a14;color:white;min-height:100vh}
.header{background:linear-gradient(135deg,#1a1a3e,#0d0d2b);padding:20px;text-align:center;border-bottom:1px solid #2a2a5a}
.logo{font-size:28px;font-weight:bold;color:#7c6fff}.logo span{color:white}
.tabs{display:flex;background:#111125;border-bottom:1px solid #2a2a5a;overflow-x:auto}
.tab{flex:1;padding:12px 5px;text-align:center;font-size:12px;color:#888;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap}
.tab.active{color:#7c6fff;border-bottom:2px solid #7c6fff}
.section{display:none;padding:15px}.section.active{display:block}
.card{background:#1a1a3e;border:1px solid #2a2a5a;border-radius:12px;padding:15px;margin-bottom:10px}
.btn{width:100%;padding:12px;background:linear-gradient(135deg,#7c6fff,#5a4fcf);color:white;border:none;border-radius:10px;font-size:14px;font-weight:bold;cursor:pointer;margin-top:8px}
.btn-google{background:linear-gradient(135deg,#4285f4,#34a853)}
.btn-red{background:linear-gradient(135deg,#ff4757,#c0392b);width:auto;padding:5px 10px;font-size:11px;margin:0}
input,textarea{width:100%;padding:10px;background:#0d0d2b;border:1px solid #2a2a5a;border-radius:8px;color:white;font-size:14px;margin-top:6px}
textarea{height:80px;resize:none}
.file-item{display:flex;align-items:center;justify-content:space-between;padding:10px;background:#0d0d2b;border-radius:8px;margin-bottom:8px}
.file-item span{font-size:13px;color:#aaa;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dl-btn{padding:5px 10px;background:#7c6fff;border:none;border-radius:6px;color:white;font-size:11px;cursor:pointer;margin-left:8px}
.del-btn{padding:5px 10px;background:#ff4757;border:none;border-radius:6px;color:white;font-size:11px;cursor:pointer;margin-left:4px}
.note-item{background:#0d0d2b;border-radius:8px;padding:10px;margin-bottom:8px}
.note-item p{font-size:13px;color:#ccc;margin-bottom:5px}
.note-item small{color:#555;font-size:11px}
.todo-item{display:flex;align-items:center;gap:10px;padding:10px;background:#0d0d2b;border-radius:8px;margin-bottom:8px}
.todo-item input[type=checkbox]{width:18px;height:18px;cursor:pointer}
.todo-item span{flex:1;font-size:13px}
.done{text-decoration:line-through;color:#555!important}
.photo-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.photo-grid img{width:100%;height:120px;object-fit:cover;border-radius:8px;border:1px solid #2a2a5a}
.empty{text-align:center;color:#555;padding:30px;font-size:13px}
.upload-area{border:2px dashed #2a2a5a;border-radius:12px;padding:20px;text-align:center;color:#555;margin-bottom:10px}
.account-card{background:#0d0d2b;border:1px solid #2a2a5a;border-radius:10px;padding:12px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between}
.storage-bar{background:#2a2a5a;border-radius:5px;height:6px;margin-top:5px}
.storage-fill{background:#7c6fff;border-radius:5px;height:6px}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:15px}
.stat-card{background:#1a1a3e;border:1px solid #2a2a5a;border-radius:10px;padding:15px;text-align:center}
.stat-card h2{font-size:24px;color:#7c6fff}
.stat-card p{color:#888;font-size:11px;margin-top:4px;text-transform:uppercase}
</style>
</head>
<body>
<div class="header">
  <div class="logo">☁️ M. Tonoy\'s <span>Gallery</span></div>
</div>
<div class="tabs">
  <div class="tab active" onclick="showTab(\'drive\')">☁️ Drive</div>
  <div class="tab" onclick="showTab(\'photos\')">🖼️ Photos</div>
  <div class="tab" onclick="showTab(\'notes\')">📝 Notes</div>
  <div class="tab" onclick="showTab(\'todos\')">✅ To-Do</div>
</div>
<div id="drive" class="section active">
  <div class="stats">
    <div class="stat-card"><h2 id="totalFiles">0</h2><p>Total Files</p></div>
    <div class="stat-card"><h2 id="totalStorage">0 GB</h2><p>Used Storage</p></div>
  </div>
  <div class="card">
    <div id="accountList"><p style="color:#888;font-size:13px">No accounts connected</p></div>
    <button class="btn btn-google" onclick="window.location.href=\'/auth\'">+ Connect Google Drive</button>
  </div>
  <div class="card">
    <div class="upload-area">📤 Upload to Drive</div>
    <input type="file" id="driveFileInput" multiple>
    <button class="btn" onclick="uploadToDrive()">Upload to Drive</button>
  </div>
  <div id="driveFileList"></div>
</div>
<div id="photos" class="section">
  <div class="card">
    <input type="file" id="photoInput" accept="image/*" multiple>
    <button class="btn" onclick="uploadPhotos()">Upload Photos</button>
  </div>
  <div class="photo-grid" id="photoGrid"></div>
</div>
<div id="notes" class="section">
  <div class="card">
    <input type="text" id="noteTitle" placeholder="Title">
    <textarea id="noteText" placeholder="Write your note..."></textarea>
    <button class="btn" onclick="saveNote()">Save Note</button>
  </div>
  <div id="noteList"></div>
</div>
<div id="todos" class="section">
  <div class="card">
    <input type="text" id="todoInput" placeholder="Add new task..." onkeypress="if(event.key==\'Enter\')addTodo()">
    <button class="btn" onclick="addTodo()">Add Task</button>
  </div>
  <div id="todoList"></div>
</div>
<script>
function showTab(name){
  document.querySelectorAll(\'.tab\').forEach((t,i)=>{t.classList.toggle(\'active\',[\'drive\',\'photos\',\'notes\',\'todos\'][i]===name)})
  document.querySelectorAll(\'.section\').forEach(s=>s.classList.remove(\'active\'))
  document.getElementById(name).classList.add(\'active\')
  if(name===\'drive\')loadDrive()
  if(name===\'photos\')loadPhotos()
  if(name===\'notes\')loadNotes()
  if(name===\'todos\')loadTodos()
}
async function loadDrive(){
  try{
    const r=await fetch(\'/drive/files\')
    const data=await r.json()
    const el=document.getElementById(\'driveFileList\')
    const acc=document.getElementById(\'accountList\')
    if(!data.accounts||!data.accounts.length){acc.innerHTML=\'<p style="color:#888;font-size:13px">No accounts connected</p>\';el.innerHTML=\'\';return}
    document.getElementById(\'totalFiles\').textContent=data.files?data.files.length:0
    acc.innerHTML=data.accounts.map(a=>`<div class="account-card"><div><p style="font-size:13px">${a.email}</p><div class="storage-bar"><div class="storage-fill" style="width:${a.percent}%"></div></div><p style="font-size:11px;color:#888;margin-top:3px">${a.used}/${a.total}</p></div><button class="btn-red btn" onclick="disconnectAccount(\'${a.email}\')">Remove</button></div>`).join(\'\')
    if(!data.files||!data.files.length){el.innerHTML=\'<div class="empty">No files yet</div>\';return}
    el.innerHTML=data.files.map(f=>`<div class="file-item"><span>📄 ${f.name}</span><button class="dl-btn" onclick="window.open(\'${f.url}\')">⬇️</button><button class="del-btn" onclick="deleteFile(\'${f.id}\')">🗑️</button></div>`).join(\'\')
  }catch(e){}
}
async function uploadToDrive(){
  const files=document.getElementById(\'driveFileInput\').files
  if(!files.length)return alert(\'Select files!\')
  const fd=new FormData()
  for(let f of files)fd.append(\'files\',f)
  await fetch(\'/drive/upload\',{method:\'POST\',body:fd})
  loadDrive()
}
async function deleteFile(id){await fetch(\'/drive/delete/\'+id,{method:\'DELETE\'});loadDrive()}
async function disconnectAccount(email){await fetch(\'/auth/disconnect\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({email})});loadDrive()}
async function uploadPhotos(){
  const files=document.getElementById(\'photoInput\').files
  if(!files.length)return alert(\'Select photos!\')
  const fd=new FormData()
  for(let f of files)fd.append(\'files\',f)
  await fetch(\'/drive/upload\',{method:\'POST\',body:fd})
  loadPhotos()
}
async function loadPhotos(){
  try{
    const r=await fetch(\'/drive/files\')
    const data=await r.json()
    const el=document.getElementById(\'photoGrid\')
    if(!data.files||!data.files.length){el.innerHTML=\'<div class="empty" style="grid-column:span 2">Connect Google Drive first</div>\';return}
    const imgs=data.files.filter(f=>/\\.(jpg|jpeg|png|gif|webp)/i.test(f.name))
    if(!imgs.length){el.innerHTML=\'<div class="empty" style="grid-column:span 2">No photos yet</div>\';return}
    el.innerHTML=imgs.map(f=>`<img src="${f.thumb||f.url}" onclick="window.open(\'${f.url}\')">`).join(\'\')
  }catch(e){}
}
async function saveNote(){
  const title=document.getElementById(\'noteTitle\').value
  const text=document.getElementById(\'noteText\').value
  if(!text)return alert(\'Write something!\')
  await fetch(\'/notes\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({title,text})})
  document.getElementById(\'noteTitle\').value=\'\'
  document.getElementById(\'noteText\').value=\'\'
  loadNotes()
}
async function loadNotes(){
  const r=await fetch(\'/notes\')
  const data=await r.json()
  const el=document.getElementById(\'noteList\')
  if(!data.length){el.innerHTML=\'<div class="empty">No notes yet</div>\';return}
  el.innerHTML=data.map((n,i)=>`<div class="note-item"><strong>${n.title||\'Note\'}</strong><p>${n.text}</p><div style="display:flex;justify-content:space-between;margin-top:5px"><small>${n.date}</small><button class="del-btn" onclick="deleteNote(${i})">🗑️</button></div></div>`).join(\'\')
}
async function deleteNote(i){await fetch(\'/notes/\'+i,{method:\'DELETE\'});loadNotes()}
async function addTodo(){
  const text=document.getElementById(\'todoInput\').value
  if(!text)return
  await fetch(\'/todos\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({text})})
  document.getElementById(\'todoInput\').value=\'\'
  loadTodos()
}
async function loadTodos(){
  const r=await fetch(\'/todos\')
  const data=await r.json()
  const el=document.getElementById(\'todoList\')
  if(!data.length){el.innerHTML=\'<div class="empty">No tasks yet</div>\';return}
  el.innerHTML=data.map((t,i)=>`<div class="todo-item"><input type="checkbox" ${t.done?\'checked\':\'\'} onchange="toggleTodo(${i})"><span class="${t.done?\'done\':\'\'}">${t.text}</span><button class="del-btn" onclick="deleteTodo(${i})">🗑️</button></div>`).join(\'\')
}
async function toggleTodo(i){await fetch(\'/todos/\'+i,{method:\'PATCH\'});loadTodos()}
async function deleteTodo(i){await fetch(\'/todos/\'+i,{method:\'DELETE\'});loadTodos()}
loadDrive()
</script>
</body>
</html>'''

@app.route('/')
def home():
    return render_template_string(HTML)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)import os, io, json
import requests as req
from flask import Flask, redirect, request, session, url_for, jsonify, render_template_string
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = 'tonoy-secret-2026'
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='None'
)

CLIENT_ID = '565165560969-k126trc6ugj7lp2au2l438k5di2ppg64.apps.googleusercontent.com'
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = 'https://personal-gallery-production-e2b9.up.railway.app/callback'
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email'
]

def get_flow():
    return Flow.from_client_config(
        {"web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }},
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

def get_credentials():
    if 'credentials' not in session:
        return None
    return Credentials(**{k: v for k, v in session['credentials'].items() if k != 'scopes'})

@app.route('/')
def home():
    return render_template_string(open('/app/templates/index.html').read() if os.path.exists('/app/templates/index.html') else HTML)

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
        flow.fetch_token(authorization_response=request.url.replace('http://', 'https://'))
        creds = flow.credentials
        session['credentials'] = {
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
        accounts[email] = session['credentials']
        session['accounts'] = accounts
        return redirect('/')
    except Exception as e:
        return f'Error: {str(e)}'

@app.route('/drive/files')
def drive_files():
    accounts = session.get('accounts', {})
    if not accounts:
        return jsonify({'files': [], 'accounts': []})
    all_files = []
    account_info = []
    for email, creds_data in accounts.items():
        try:
            creds = Credentials(**{k: v for k, v in creds_data.items() if k != 'scopes'})
            service = build('drive', 'v3', credentials=creds)
            results = service.files().list(pageSize=50, fields="files(id,name,mimeType,webViewLink,thumbnailLink)").execute()
            for f in results.get('files', []):
                all_files.append({'id': f['id'], 'name': f['name'], 'url': f.get('webViewLink',''), 'thumb': f.get('thumbnailLink','')})
            about = service.about().get(fields='storageQuota').execute()
            quota = about.get('storageQuota', {})
            used = int(quota.get('usage', 0))
            total = int(quota.get('limit', 16106127360))
            account_info.append({'email': email, 'used': f'{used/1e9:.1f} GB', 'total': f'{total/1e9:.1f} GB', 'percent': min(100, int(used/total*100))})
        except:
            pass
    return jsonify({'files': all_files, 'accounts': account_info})

@app.route('/drive/upload', methods=['POST'])
def drive_upload():
    accounts = session.get('accounts', {})
    if not accounts:
        return jsonify({'error': 'No accounts'})
    creds_data = list(accounts.values())[0]
    creds = Credentials(**{k: v for k, v in creds_data.items() if k != 'scopes'})
    service = build('drive', 'v3', credentials=creds)
    for f in request.files.getlist('files'):
        media = MediaIoBaseUpload(io.BytesIO(f.read()), mimetype=f.content_type)
        service.files().create(body={'name': f.filename}, media_body=media).execute()
    return jsonify({'ok': True})

@app.route('/drive/delete/<file_id>', methods=['DELETE'])
def drive_delete(file_id):
    accounts = session.get('accounts', {})
    for email, creds_data in accounts.items():
        try:
            creds = Credentials(**{k: v for k, v in creds_data.items() if k != 'scopes'})
            service = build('drive', 'v3', credentials=creds)
            service.files().delete(fileId=file_id).execute()
            break
        except:
            pass
    return jsonify({'ok': True})

@app.route('/auth/disconnect', methods=['POST'])
def disconnect():
    email = request.json.get('email')
    accounts = session.get('accounts', {})
    if email in accounts:
        del accounts[email]
    session['accounts'] = accounts
    return jsonify({'ok': True})

@app.route('/notes', methods=['GET', 'POST'])
def notes():
    from datetime import datetime
    NOTES_FILE = '/tmp/notes.json'
    def load():
        try:
            with open(NOTES_FILE) as f: return json.load(f)
        except: return []
    def save(d):
        with open(NOTES_FILE, 'w') as f: json.dump(d, f)
    if request.method == 'POST':
        data = load()
        note = request.json
        note['date'] = datetime.now().strftime('%d %b %Y')
        data.append(note)
        save(data)
        return jsonify({'ok': True})
    return jsonify(load())

@app.route('/notes/<int:i>', methods=['DELETE'])
def delete_note(i):
    NOTES_FILE = '/tmp/notes.json'
    try:
        with open(NOTES_FILE) as f: data = json.load(f)
    except: data = []
    if i < len(data): data.pop(i)
    with open(NOTES_FILE, 'w') as f: json.dump(data, f)
    return jsonify({'ok': True})

@app.route('/todos', methods=['GET', 'POST'])
def todos():
    TODO_FILE = '/tmp/todos.json'
    def load():
        try:
            with open(TODO_FILE) as f: return json.load(f)
        except: return []
    def save(d):
        with open(TODO_FILE, 'w') as f: json.dump(d, f)
    if request.method == 'POST':
        data = load()
        data.append({'text': request.json['text'], 'done': False})
        save(data)
        return jsonify({'ok': True})
    return jsonify(load())

@app.route('/todos/<int:i>', methods=['DELETE', 'PATCH'])
def todo_action(i):
    TODO_FILE = '/tmp/todos.json'
    def load():
        try:
            with open(TODO_FILE) as f: return json.load(f)
        except: return []
    def save(d):
        with open(TODO_FILE, 'w') as f: json.dump(d, f)
    data = load()
    if i < len(data):
        if request.method == 'DELETE': data.pop(i)
        else: data[i]['done'] = not data[i]['done']
    save(data)
    return jsonify({'ok': True})

HTML = '''<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>M. Tonoy\'s Gallery</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:\'Segoe UI\',sans-serif;background:#0a0a14;color:white;min-height:100vh}
.header{background:linear-gradient(135deg,#1a1a3e,#0d0d2b);padding:20px;text-align:center;border-bottom:1px solid #2a2a5a}
.logo{font-size:28px;font-weight:bold;color:#7c6fff}.logo span{color:white}
.tabs{display:flex;background:#111125;border-bottom:1px solid #2a2a5a;overflow-x:auto}
.tab{flex:1;padding:12px 5px;text-align:center;font-size:12px;color:#888;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap}
.tab.active{color:#7c6fff;border-bottom:2px solid #7c6fff}
.section{display:none;padding:15px}.section.active{display:block}
.card{background:#1a1a3e;border:1px solid #2a2a5a;border-radius:12px;padding:15px;margin-bottom:10px}
.btn{width:100%;padding:12px;background:linear-gradient(135deg,#7c6fff,#5a4fcf);color:white;border:none;border-radius:10px;font-size:14px;font-weight:bold;cursor:pointer;margin-top:8px}
.btn-google{background:linear-gradient(135deg,#4285f4,#34a853)}
.btn-red{background:linear-gradient(135deg,#ff4757,#c0392b);width:auto;padding:5px 10px;font-size:11px;margin:0}
input,textarea{width:100%;padding:10px;background:#0d0d2b;border:1px solid #2a2a5a;border-radius:8px;color:white;font-size:14px;margin-top:6px}
textarea{height:80px;resize:none}
.file-item{display:flex;align-items:center;justify-content:space-between;padding:10px;background:#0d0d2b;border-radius:8px;margin-bottom:8px}
.file-item span{font-size:13px;color:#aaa;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dl-btn{padding:5px 10px;background:#7c6fff;border:none;border-radius:6px;color:white;font-size:11px;cursor:pointer;margin-left:8px}
.del-btn{padding:5px 10px;background:#ff4757;border:none;border-radius:6px;color:white;font-size:11px;cursor:pointer;margin-left:4px}
.note-item{background:#0d0d2b;border-radius:8px;padding:10px;margin-bottom:8px}
.note-item p{font-size:13px;color:#ccc;margin-bottom:5px}
.note-item small{color:#555;font-size:11px}
.todo-item{display:flex;align-items:center;gap:10px;padding:10px;background:#0d0d2b;border-radius:8px;margin-bottom:8px}
.todo-item input[type=checkbox]{width:18px;height:18px;cursor:pointer}
.todo-item span{flex:1;font-size:13px}
.done{text-decoration:line-through;color:#555!important}
.photo-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.photo-grid img{width:100%;height:120px;object-fit:cover;border-radius:8px;border:1px solid #2a2a5a}
.empty{text-align:center;color:#555;padding:30px;font-size:13px}
.upload-area{border:2px dashed #2a2a5a;border-radius:12px;padding:20px;text-align:center;color:#555;margin-bottom:10px}
.account-card{background:#0d0d2b;border:1px solid #2a2a5a;border-radius:10px;padding:12px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between}
.storage-bar{background:#2a2a5a;border-radius:5px;height:6px;margin-top:5px}
.storage-fill{background:#7c6fff;border-radius:5px;height:6px}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:15px}
.stat-card{background:#1a1a3e;border:1px solid #2a2a5a;border-radius:10px;padding:15px;text-align:center}
.stat-card h2{font-size:24px;color:#7c6fff}
.stat-card p{color:#888;font-size:11px;margin-top:4px;text-transform:uppercase}
</style>
</head>
<body>
<div class="header">
  <div class="logo">☁️ M. Tonoy\'s <span>Gallery</span></div>
</div>
<div class="tabs">
  <div class="tab active" onclick="showTab(\'drive\')">☁️ Drive</div>
  <div class="tab" onclick="showTab(\'photos\')">🖼️ Photos</div>
  <div class="tab" onclick="showTab(\'notes\')">📝 Notes</div>
  <div class="tab" onclick="showTab(\'todos\')">✅ To-Do</div>
</div>
<div id="drive" class="section active">
  <div class="stats">
    <div class="stat-card"><h2 id="totalFiles">0</h2><p>Total Files</p></div>
    <div class="stat-card"><h2 id="totalStorage">0 GB</h2><p>Used Storage</p></div>
  </div>
  <div class="card">
    <div id="accountList"><p style="color:#888;font-size:13px">No accounts connected</p></div>
    <button class="btn btn-google" onclick="window.location.href=\'/auth\'">+ Connect Google Drive</button>
  </div>
  <div class="card">
    <div class="upload-area">📤 Upload to Drive</div>
    <input type="file" id="driveFileInput" multiple>
    <button class="btn" onclick="uploadToDrive()">Upload to Drive</button>
  </div>
  <div id="driveFileList"></div>
</div>
<div id="photos" class="section">
  <div class="card">
    <input type="file" id="photoInput" accept="image/*" multiple>
    <button class="btn" onclick="uploadPhotos()">Upload Photos</button>
  </div>
  <div class="photo-grid" id="photoGrid"></div>
</div>
<div id="notes" class="section">
  <div class="card">
    <input type="text" id="noteTitle" placeholder="Title">
    <textarea id="noteText" placeholder="Write your note..."></textarea>
    <button class="btn" onclick="saveNote()">Save Note</button>
  </div>
  <div id="noteList"></div>
</div>
<div id="todos" class="section">
  <div class="card">
    <input type="text" id="todoInput" placeholder="Add new task..." onkeypress="if(event.key==\'Enter\')addTodo()">
    <button class="btn" onclick="addTodo()">Add Task</button>
  </div>
  <div id="todoList"></div>
</div>
<script>
function showTab(name){
  document.querySelectorAll(\'.tab\').forEach((t,i)=>{t.classList.toggle(\'active\',[\'drive\',\'photos\',\'notes\',\'todos\'][i]===name)})
  document.querySelectorAll(\'.section\').forEach(s=>s.classList.remove(\'active\'))
  document.getElementById(name).classList.add(\'active\')
  if(name===\'drive\')loadDrive()
  if(name===\'photos\')loadPhotos()
  if(name===\'notes\')loadNotes()
  if(name===\'todos\')loadTodos()
}
async function loadDrive(){
  try{
    const r=await fetch(\'/drive/files\')
    const data=await r.json()
    const el=document.getElementById(\'driveFileList\')
    const acc=document.getElementById(\'accountList\')
    if(!data.accounts||!data.accounts.length){acc.innerHTML=\'<p style="color:#888;font-size:13px">No accounts connected</p>\';el.innerHTML=\'\';return}
    document.getElementById(\'totalFiles\').textContent=data.files?data.files.length:0
    acc.innerHTML=data.accounts.map(a=>`<div class="account-card"><div><p style="font-size:13px">${a.email}</p><div class="storage-bar"><div class="storage-fill" style="width:${a.percent}%"></div></div><p style="font-size:11px;color:#888;margin-top:3px">${a.used}/${a.total}</p></div><button class="btn-red btn" onclick="disconnectAccount(\'${a.email}\')">Remove</button></div>`).join(\'\')
    if(!data.files||!data.files.length){el.innerHTML=\'<div class="empty">No files yet</div>\';return}
    el.innerHTML=data.files.map(f=>`<div class="file-item"><span>📄 ${f.name}</span><button class="dl-btn" onclick="window.open(\'${f.url}\')">⬇️</button><button class="del-btn" onclick="deleteFile(\'${f.id}\')">🗑️</button></div>`).join(\'\')
  }catch(e){}
}
async function uploadToDrive(){
  const files=document.getElementById(\'driveFileInput\').files
  if(!files.length)return alert(\'Select files!\')
  const fd=new FormData()
  for(let f of files)fd.append(\'files\',f)
  await fetch(\'/drive/upload\',{method:\'POST\',body:fd})
  loadDrive()
}
async function deleteFile(id){await fetch(\'/drive/delete/\'+id,{method:\'DELETE\'});loadDrive()}
async function disconnectAccount(email){await fetch(\'/auth/disconnect\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({email})});loadDrive()}
async function uploadPhotos(){
  const files=document.getElementById(\'photoInput\').files
  if(!files.length)return alert(\'Select photos!\')
  const fd=new FormData()
  for(let f of files)fd.append(\'files\',f)
  await fetch(\'/drive/upload\',{method:\'POST\',body:fd})
  loadPhotos()
}
async function loadPhotos(){
  try{
    const r=await fetch(\'/drive/files\')
    const data=await r.json()
    const el=document.getElementById(\'photoGrid\')
    if(!data.files||!data.files.length){el.innerHTML=\'<div class="empty" style="grid-column:span 2">Connect Google Drive first</div>\';return}
    const imgs=data.files.filter(f=>/\\.(jpg|jpeg|png|gif|webp)/i.test(f.name))
    if(!imgs.length){el.innerHTML=\'<div class="empty" style="grid-column:span 2">No photos yet</div>\';return}
    el.innerHTML=imgs.map(f=>`<img src="${f.thumb||f.url}" onclick="window.open(\'${f.url}\')">`).join(\'\')
  }catch(e){}
}
async function saveNote(){
  const title=document.getElementById(\'noteTitle\').value
  const text=document.getElementById(\'noteText\').value
  if(!text)return alert(\'Write something!\')
  await fetch(\'/notes\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({title,text})})
  document.getElementById(\'noteTitle\').value=\'\'
  document.getElementById(\'noteText\').value=\'\'
  loadNotes()
}
async function loadNotes(){
  const r=await fetch(\'/notes\')
  const data=await r.json()
  const el=document.getElementById(\'noteList\')
  if(!data.length){el.innerHTML=\'<div class="empty">No notes yet</div>\';return}
  el.innerHTML=data.map((n,i)=>`<div class="note-item"><strong>${n.title||\'Note\'}</strong><p>${n.text}</p><div style="display:flex;justify-content:space-between;margin-top:5px"><small>${n.date}</small><button class="del-btn" onclick="deleteNote(${i})">🗑️</button></div></div>`).join(\'\')
}
async function deleteNote(i){await fetch(\'/notes/\'+i,{method:\'DELETE\'});loadNotes()}
async function addTodo(){
  const text=document.getElementById(\'todoInput\').value
  if(!text)return
  await fetch(\'/todos\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({text})})
  document.getElementById(\'todoInput\').value=\'\'
  loadTodos()
}
async function loadTodos(){
  const r=await fetch(\'/todos\')
  const data=await r.json()
  const el=document.getElementById(\'todoList\')
  if(!data.length){el.innerHTML=\'<div class="empty">No tasks yet</div>\';return}
  el.innerHTML=data.map((t,i)=>`<div class="todo-item"><input type="checkbox" ${t.done?\'checked\':\'\'} onchange="toggleTodo(${i})"><span class="${t.done?\'done\':\'\'}">${t.text}</span><button class="del-btn" onclick="deleteTodo(${i})">🗑️</button></div>`).join(\'\')
}
async function toggleTodo(i){await fetch(\'/todos/\'+i,{method:\'PATCH\'});loadTodos()}
async function deleteTodo(i){await fetch(\'/todos/\'+i,{method:\'DELETE\'});loadTodos()}
loadDrive()
</script>
</body>
</html>'''

@app.route('/')
def home():
    return render_template_string(HTML)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
