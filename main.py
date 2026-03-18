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
.btn-g{background:linear-gradient(135deg,#4285f4,#34a853)}
.btn-r{background:linear-gradient(135deg,#ff4757,#c0392b);width:auto;padding:5px 10px;font-size:11px;margin:0}
input,textarea{width:100%;padding:10px;background:#0d0d2b;border:1px solid #2a2a5a;border-radius:8px;color:white;font-size:14px;margin-top:6px}
textarea{height:80px;resize:none}
.fi{display:flex;align-items:center;justify-content:space-between;padding:10px;background:#0d0d2b;border-radius:8px;margin-bottom:8px}
.fi span{font-size:13px;color:#aaa;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.db{padding:5px 10px;background:#7c6fff;border:none;border-radius:6px;color:white;font-size:11px;cursor:pointer;margin-left:8px}
.del{padding:5px 10px;background:#ff4757;border:none;border-radius:6px;color:white;font-size:11px;cursor:pointer;margin-left:4px}
.ni{background:#0d0d2b;border-radius:8px;padding:10px;margin-bottom:8px}
.ni p{font-size:13px;color:#ccc;margin-bottom:5px}
.ni small{color:#555;font-size:11px}
.ti{display:flex;align-items:center;gap:10px;padding:10px;background:#0d0d2b;border-radius:8px;margin-bottom:8px}
.ti input[type=checkbox]{width:18px;height:18px;cursor:pointer}
.ti span{flex:1;font-size:13px}
.done{text-decoration:line-through;color:#555!important}
.pg{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.pg img{width:100%;height:120px;object-fit:cover;border-radius:8px;border:1px solid #2a2a5a}
.empty{text-align:center;color:#555;padding:30px;font-size:13px}
.ua{border:2px dashed #2a2a5a;border-radius:12px;padding:20px;text-align:center;color:#555;margin-bottom:10px}
.ac{background:#0d0d2b;border:1px solid #2a2a5a;border-radius:10px;padding:12px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between}
.sb{background:#2a2a5a;border-radius:5px;height:6px;margin-top:5px}
.sf{background:#7c6fff;border-radius:5px;height:6px}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:15px}
.sc{background:#1a1a3e;border:1px solid #2a2a5a;border-radius:10px;padding:15px;text-align:center}
.sc h2{font-size:24px;color:#7c6fff}
.sc p{color:#888;font-size:11px;margin-top:4px;text-transform:uppercase}
</style>
</head>
<body>
<div class="header"><div class="logo">☁️ M. Tonoy\'s <span>Gallery</span></div></div>
<div class="tabs">
  <div class="tab active" onclick="showTab(\'drive\')">☁️ Drive</div>
  <div class="tab" onclick="showTab(\'photos\')">🖼️ Photos</div>
  <div class="tab" onclick="showTab(\'notes\')">📝 Notes</div>
  <div class="tab" onclick="showTab(\'todos\')">✅ To-Do</div>
</div>
<div id="drive" class="section active">
  <div class="stats">
    <div class="sc"><h2 id="tFiles">0</h2><p>Total Files</p></div>
    <div class="sc"><h2 id="tStorage">0 GB</h2><p>Used Storage</p></div>
  </div>
  <div class="card">
    <div id="accList"><p style="color:#888;font-size:13px">No accounts connected</p></div>
    <button class="btn btn-g" onclick="window.location.href=\'/auth\'">+ Connect Google Drive</button>
  </div>
  <div class="card">
    <div class="ua">📤 Upload to Drive</div>
    <input type="file" id="dfi" multiple>
    <button class="btn" onclick="uploadDrive()">Upload to Drive</button>
  </div>
  <div id="dfl"></div>
</div>
<div id="photos" class="section">
  <div class="card">
    <input type="file" id="pfi" accept="image/*" multiple>
    <button class="btn" onclick="uploadPhotos()">Upload Photos</button>
  </div>
  <div class="pg" id="pg"></div>
</div>
<div id="notes" class="section">
  <div class="card">
    <input type="text" id="nt" placeholder="Title">
    <textarea id="nb" placeholder="Write your note..."></textarea>
    <button class="btn" onclick="saveNote()">Save Note</button>
  </div>
  <div id="nl"></div>
</div>
<div id="todos" class="section">
  <div class="card">
    <input type="text" id="ti" placeholder="Add new task..." onkeypress="if(event.key==\'Enter\')addTodo()">
    <button class="btn" onclick="addTodo()">Add Task</button>
  </div>
  <div id="tl"></div>
</div>
<script>
function showTab(n){
  document.querySelectorAll(\'.tab\').forEach((t,i)=>t.classList.toggle(\'active\',[\'drive\',\'photos\',\'notes\',\'todos\'][i]===n))
  document.querySelectorAll(\'.section\').forEach(s=>s.classList.remove(\'active\'))
  document.getElementById(n).classList.add(\'active\')
  if(n===\'drive\')loadDrive()
  if(n===\'photos\')loadPhotos()
  if(n===\'notes\')loadNotes()
  if(n===\'todos\')loadTodos()
}
async function loadDrive(){
  try{
    const d=await(await fetch(\'/drive/files\')).json()
    const el=document.getElementById(\'dfl\')
    const al=document.getElementById(\'accList\')
    if(!d.accounts||!d.accounts.length){al.innerHTML=\'<p style="color:#888;font-size:13px">No accounts connected</p>\';el.innerHTML=\'\';return}
    document.getElementById(\'tFiles\').textContent=d.files?d.files.length:0
    al.innerHTML=d.accounts.map(a=>`<div class="ac"><div><p style="font-size:13px">${a.email}</p><div class="sb"><div class="sf" style="width:${a.percent}%"></div></div><p style="font-size:11px;color:#888;margin-top:3px">${a.used}/${a.total}</p></div><button class="btn-r btn" onclick="removeAcc(\'${a.email}\')">Remove</button></div>`).join(\'\')
    if(!d.files||!d.files.length){el.innerHTML=\'<div class="empty">No files yet</div>\';return}
    el.innerHTML=d.files.map(f=>`<div class="fi"><span>📄 ${f.name}</span><button class="db" onclick="window.open(\'${f.url}\')">⬇️</button><button class="del" onclick="delFile(\'${f.id}\')">🗑️</button></div>`).join(\'\')
  }catch(e){}
}
async function uploadDrive(){
  const files=document.getElementById(\'dfi\').files
  if(!files.length)return alert(\'Select files!\')
  const fd=new FormData()
  for(let f of files)fd.append(\'files\',f)
  await fetch(\'/drive/upload\',{method:\'POST\',body:fd})
  loadDrive()
}
async function delFile(id){await fetch(\'/drive/delete/\'+id,{method:\'DELETE\'});loadDrive()}
async function removeAcc(email){await fetch(\'/auth/disconnect\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({email})});loadDrive()}
async function uploadPhotos(){
  const files=document.getElementById(\'pfi\').files
  if(!files.length)return alert(\'Select photos!\')
  const fd=new FormData()
  for(let f of files)fd.append(\'files\',f)
  await fetch(\'/drive/upload\',{method:\'POST\',body:fd})
  loadPhotos()
}
async function loadPhotos(){
  try{
    const d=await(await fetch(\'/drive/files\')).json()
    const el=document.getElementById(\'pg\')
    if(!d.files||!d.files.length){el.innerHTML=\'<div class="empty" style="grid-column:span 2">Connect Google Drive first</div>\';return}
    const imgs=d.files.filter(f=>/\\.(jpg|jpeg|png|gif|webp)/i.test(f.name))
    el.innerHTML=imgs.length?imgs.map(f=>`<img src="${f.thumb||f.url}" onclick="window.open(\'${f.url}\')">`).join(\'\'):\'<div class="empty" style="grid-column:span 2">No photos yet</div>\'
  }catch(e){}
}
async function saveNote(){
  const t=document.getElementById(\'nt\').value,b=document.getElementById(\'nb\').value
  if(!b)return alert(\'Write something!\')
  await fetch(\'/notes\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({title:t,text:b})})
  document.getElementById(\'nt\').value=\'\'
  document.getElementById(\'nb\').value=\'\'
  loadNotes()
}
async function loadNotes(){
  const d=await(await fetch(\'/notes\')).json()
  const el=document.getElementById(\'nl\')
  el.innerHTML=d.length?d.map((n,i)=>`<div class="ni"><strong>${n.title||\'Note\'}</strong><p>${n.text}</p><div style="display:flex;justify-content:space-between;margin-top:5px"><small>${n.date}</small><button class="del" onclick="delNote(${i})">🗑️</button></div></div>`).join(\'\'):\'<div class="empty">No notes yet</div>\'
}
async function delNote(i){await fetch(\'/notes/\'+i,{method:\'DELETE\'});loadNotes()}
async function addTodo(){
  const t=document.getElementById(\'ti\').value
  if(!t)return
  await fetch(\'/todos\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({text:t})})
  document.getElementById(\'ti\').value=\'\'
  loadTodos()
}
async function loadTodos(){
  const d=await(await fetch(\'/todos\')).json()
  const el=document.getElementById(\'tl\')
  el.innerHTML=d.length?d.map((t,i)=>`<div class="ti"><input type="checkbox" ${t.done?\'checked\':\'\'} onchange="toggleTodo(${i})"><span class="${t.done?\'done\':\'\'}">${t.text}</span><button class="del" onclick="delTodo(${i})">🗑️</button></div>`).join(\'\'):\'<div class="empty">No tasks yet</div>\'
}
async function toggleTodo(i){await fetch(\'/todos/\'+i,{method:\'PATCH\'});loadTodos()}
async function delTodo(i){await fetch(\'/todos/\'+i,{method:\'DELETE\'});loadTodos()}
loadDrive()
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
            for f in svc.files().list(pageSize=50, fields="files(id,name,mimeType,webViewLink,thumbnailLink,webContentLink)").execute().get('files', []):
                all_files.append({'id': f['id'], 'name': f['name'], 'url': f.get('webContentLink', f.get('webViewLink', '')), 'thumb': f.get('thumbnailLink', '')})
            q = svc.about().get(fields='storageQuota').execute().get('storageQuota', {})
            used, total = int(q.get('usage', 0)), int(q.get('limit', 16106127360))
            account_info.append({'email': email, 'used': f'{used/1e9:.1f} GB', 'total': f'{total/1e9:.1f} GB', 'percent': min(100, int(used/total*100))})
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

@app.route('/notes', methods=['GET', 'POST'])
def notes():
    f = '/tmp/notes.json'
    def load():
        try: return json.load(open(f))
        except: return []
    def save(d): json.dump(d, open(f, 'w'))
    if request.method == 'POST':
        d = load()
        n = request.json
        n['date'] = datetime.now().strftime('%d %b %Y')
        d.append(n); save(d)
        return jsonify({'ok': True})
    return jsonify(load())

@app.route('/notes/<int:i>', methods=['DELETE'])
def del_note(i):
    f = '/tmp/notes.json'
    try: d = json.load(open(f))
    except: d = []
    if i < len(d): d.pop(i)
    json.dump(d, open(f, 'w'))
    return jsonify({'ok': True})

@app.route('/todos', methods=['GET', 'POST'])
def todos():
    f = '/tmp/todos.json'
    def load():
        try: return json.load(open(f))
        except: return []
    def save(d): json.dump(d, open(f, 'w'))
    if request.method == 'POST':
        d = load(); d.append({'text': request.json['text'], 'done': False}); save(d)
        return jsonify({'ok': True})
    return jsonify(load())

@app.route('/todos/<int:i>', methods=['DELETE', 'PATCH'])
def todo_action(i):
    f = '/tmp/todos.json'
    try: d = json.load(open(f))
    except: d = []
    if i < len(d):
        if request.method == 'DELETE': d.pop(i)
        else: d[i]['done'] = not d[i]['done']
    json.dump(d, open(f, 'w'))
    return jsonify({'ok': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
