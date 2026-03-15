from flask import Flask, render_template_string, request, jsonify, send_file
import os, json, base64
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = '/tmp/uploads'
NOTES_FILE = '/tmp/notes.json'
TODO_FILE = '/tmp/todos.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_json(path):
    try:
        with open(path) as f: return json.load(f)
    except: return []

def save_json(path, data):
    with open(path, 'w') as f: json.dump(data, f)

HTML = '''<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DrivePool</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#0a0a14;color:white;min-height:100vh}
.header{background:linear-gradient(135deg,#1a1a3e,#0d0d2b);padding:20px;text-align:center;border-bottom:1px solid #2a2a5a}
.logo{font-size:28px;font-weight:bold;color:#7c6fff}.logo span{color:white}
.tabs{display:flex;background:#111125;border-bottom:1px solid #2a2a5a;overflow-x:auto}
.tab{flex:1;padding:12px 5px;text-align:center;font-size:12px;color:#888;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap}
.tab.active{color:#7c6fff;border-bottom:2px solid #7c6fff}
.section{display:none;padding:15px}
.section.active{display:block}
.card{background:#1a1a3e;border:1px solid #2a2a5a;border-radius:12px;padding:15px;margin-bottom:10px}
.btn{width:100%;padding:12px;background:linear-gradient(135deg,#7c6fff,#5a4fcf);color:white;border:none;border-radius:10px;font-size:14px;font-weight:bold;cursor:pointer;margin-top:8px}
.btn-red{background:linear-gradient(135deg,#ff4757,#c0392b)}
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
</style>
</head>
<body>
<div class="header">
  <div class="logo">☁️ Drive<span>Pool</span></div>
</div>
<div class="tabs">
  <div class="tab active" onclick="showTab('files')">📁 Files</div>
  <div class="tab" onclick="showTab('photos')">🖼️ Photos</div>
  <div class="tab" onclick="showTab('notes')">📝 Notes</div>
  <div class="tab" onclick="showTab('todos')">✅ To-Do</div>
</div>

<!-- FILES -->
<div id="files" class="section active">
  <div class="card">
    <div class="upload-area">📤 Upload any file</div>
    <input type="file" id="fileInput" multiple>
    <button class="btn" onclick="uploadFiles()">Upload Files</button>
  </div>
  <div id="fileList"></div>
</div>

<!-- PHOTOS -->
<div id="photos" class="section">
  <div class="card">
    <input type="file" id="photoInput" accept="image/*" multiple>
    <button class="btn" onclick="uploadPhotos()">Upload Photos</button>
  </div>
  <div class="photo-grid" id="photoGrid"></div>
</div>

<!-- NOTES -->
<div id="notes" class="section">
  <div class="card">
    <input type="text" id="noteTitle" placeholder="Title">
    <textarea id="noteText" placeholder="Write your note..."></textarea>
    <button class="btn" onclick="saveNote()">Save Note</button>
  </div>
  <div id="noteList"></div>
</div>

<!-- TODOS -->
<div id="todos" class="section">
  <div class="card">
    <input type="text" id="todoInput" placeholder="Add new task..." onkeypress="if(event.key=='Enter')addTodo()">
    <button class="btn" onclick="addTodo()">Add Task</button>
  </div>
  <div id="todoList"></div>
</div>

<script>
function showTab(name){
  document.querySelectorAll('.tab').forEach((t,i)=>{
    t.classList.toggle('active', ['files','photos','notes','todos'][i]===name)
  })
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'))
  document.getElementById(name).classList.add('active')
  if(name==='files')loadFiles()
  if(name==='photos')loadPhotos()
  if(name==='notes')loadNotes()
  if(name==='todos')loadTodos()
}

async function uploadFiles(){
  const files=document.getElementById('fileInput').files
  if(!files.length)return alert('Select files first!')
  const fd=new FormData()
  for(let f of files)fd.append('files',f)
  await fetch('/upload',{method:'POST',body:fd})
  loadFiles()
}

async function loadFiles(){
  const r=await fetch('/files')
  const data=await r.json()
  const el=document.getElementById('fileList')
  if(!data.length){el.innerHTML='<div class="empty">No files yet</div>';return}
  el.innerHTML=data.map(f=>`
    <div class="file-item">
      <span>📄 ${f}</span>
      <button class="dl-btn" onclick="downloadFile('${f}')">⬇️</button>
      <button class="del-btn" onclick="deleteFile('${f}')">🗑️</button>
    </div>`).join('')
}

function downloadFile(name){window.open('/download/'+name)}
async function deleteFile(name){
  await fetch('/delete/'+name,{method:'DELETE'})
  loadFiles()
}

async function uploadPhotos(){
  const files=document.getElementById('photoInput').files
  if(!files.length)return alert('Select photos!')
  const fd=new FormData()
  for(let f of files)fd.append('files',f)
  await fetch('/upload',{method:'POST',body:fd})
  loadPhotos()
}

async function loadPhotos(){
  const r=await fetch('/files')
  const data=await r.json()
  const imgs=data.filter(f=>/\.(jpg|jpeg|png|gif|webp)$/i.test(f))
  const el=document.getElementById('photoGrid')
  if(!imgs.length){el.innerHTML='<div class="empty" style="grid-column:span 2">No photos yet</div>';return}
  el.innerHTML=imgs.map(f=>`<img src="/download/${f}" onclick="window.open('/download/${f}')">`).join('')
}

async function saveNote(){
  const title=document.getElementById('noteTitle').value
  const text=document.getElementById('noteText').value
  if(!text)return alert('Write something!')
  await fetch('/notes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,text})})
  document.getElementById('noteTitle').value=''
  document.getElementById('noteText').value=''
  loadNotes()
}

async function loadNotes(){
  const r=await fetch('/notes')
  const data=await r.json()
  const el=document.getElementById('noteList')
  if(!data.length){el.innerHTML='<div class="empty">No notes yet</div>';return}
  el.innerHTML=data.map((n,i)=>`
    <div class="note-item">
      <strong>${n.title||'Note'}</strong>
      <p>${n.text}</p>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:5px">
        <small>${n.date}</small>
        <button class="del-btn" onclick="deleteNote(${i})">🗑️</button>
      </div>
    </div>`).join('')
}

async function deleteNote(i){
  await fetch('/notes/'+i,{method:'DELETE'})
  loadNotes()
}

async function addTodo(){
  const text=document.getElementById('todoInput').value
  if(!text)return
  await fetch('/todos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})})
  document.getElementById('todoInput').value=''
  loadTodos()
}

async function loadTodos(){
  const r=await fetch('/todos')
  const data=await r.json()
  const el=document.getElementById('todoList')
  if(!data.length){el.innerHTML='<div class="empty">No tasks yet</div>';return}
  el.innerHTML=data.map((t,i)=>`
    <div class="todo-item">
      <input type="checkbox" ${t.done?'checked':''} onchange="toggleTodo(${i})">
      <span class="${t.done?'done':''}">${t.text}</span>
      <button class="del-btn" onclick="deleteTodo(${i})">🗑️</button>
    </div>`).join('')
}

async function toggleTodo(i){
  await fetch('/todos/'+i,{method:'PATCH'})
  loadTodos()
}

async function deleteTodo(i){
  await fetch('/todos/'+i,{method:'DELETE'})
  loadTodos()
}

loadFiles()
</script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/upload', methods=['POST'])
def upload():
    for f in request.files.getlist('files'):
        f.save(os.path.join(UPLOAD_FOLDER, f.filename))
    return jsonify({'ok': True})

@app.route('/files')
def list_files():
    try: return jsonify(os.listdir(UPLOAD_FOLDER))
    except: return jsonify([])

@app.route('/download/<name>')
def download(name):
    return send_file(os.path.join(UPLOAD_FOLDER, name), as_attachment=False)

@app.route('/delete/<name>', methods=['DELETE'])
def delete_file(name):
    try: os.remove(os.path.join(UPLOAD_FOLDER, name))
    except: pass
    return jsonify({'ok': True})

@app.route('/notes', methods=['GET','POST'])
def notes():
    if request.method == 'POST':
        data = load_json(NOTES_FILE)
        note = request.json
        note['date'] = datetime.now().strftime('%d %b %Y')
        data.append(note)
        save_json(NOTES_FILE, data)
        return jsonify({'ok': True})
    return jsonify(load_json(NOTES_FILE))

@app.route('/notes/<int:i>', methods=['DELETE'])
def delete_note(i):
    data = load_json(NOTES_FILE)
    if i < len(data): data.pop(i)
    save_json(NOTES_FILE, data)
    return jsonify({'ok': True})

@app.route('/todos', methods=['GET','POST'])
def todos():
    if request.method == 'POST':
        data = load_json(TODO_FILE)
        data.append({'text': request.json['text'], 'done': False})
        save_json(TODO_FILE, data)
        return jsonify({'ok': True})
    return jsonify(load_json(TODO_FILE))

@app.route('/todos/<int:i>', methods=['DELETE','PATCH'])
def todo_action(i):
    data = load_json(TODO_FILE)
    if i < len(data):
        if request.method == 'DELETE': data.pop(i)
        else: data[i]['done'] = not data[i]['done']
    save_json(TODO_FILE, data)
    return jsonify({'ok': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
