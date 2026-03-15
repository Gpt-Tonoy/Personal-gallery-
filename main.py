from flask import Flask, redirect, url_for, session, request, jsonify, render_template_string
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'drivepool-secret-123')

HTML = '''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DrivePool</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: Arial, sans-serif; background: #0f0f1a; color: white; }
.header { background: #1a1a2e; padding: 20px; text-align: center; }
.header h1 { color: #6c63ff; font-size: 28px; }
.header p { color: #aaa; margin-top: 5px; }
.cards { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 20px; }
.card { background: #1a1a2e; border-radius: 15px; padding: 20px; text-align: center; }
.card h2 { font-size: 32px; color: #6c63ff; }
.card p { color: #aaa; font-size: 12px; margin-top: 5px; }
.btn { display: block; margin: 10px auto; padding: 12px 30px; background: #6c63ff; color: white; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; text-decoration: none; text-align: center; }
.coming { color: #aaa; text-align: center; padding: 20px; font-size: 14px; }
</style>
</head>
<body>
<div class="header">
<h1>☁️ DrivePool</h1>
<p>Your unified cloud storage</p>
</div>
<div class="cards">
<div class="card"><h2>0</h2><p>Total Files</p></div>
<div class="card"><h2>0 GB</h2><p>Used Storage</p></div>
<div class="card"><h2>0</h2><p>Accounts</p></div>
<div class="card"><h2>0 GB</h2><p>Free Storage</p></div>
</div>
<a href="#" class="btn">+ Connect Google Drive</a>
<p class="coming">Full Google Drive integration coming soon!</p>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
