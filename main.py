from flask import Flask, render_template_string
import os

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DrivePool</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#0a0a14;color:white;min-height:100vh}
.header{background:linear-gradient(135deg,#1a1a3e,#0d0d2b);padding:25px 20px;text-align:center;border-bottom:1px solid #2a2a5a}
.logo{font-size:32px;font-weight:bold;color:#7c6fff}
.logo span{color:white}
.subtitle{color:#888;font-size:13px;margin-top:5px}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:20px}
.card{background:linear-gradient(135deg,#1a1a3e,#12122a);border:1px solid #2a2a5a;border-radius:16px;padding:20px;text-align:center}
.card h2{font-size:30px;color:#7c6fff;font-weight:bold}
.card p{color:#888;font-size:11px;margin-top:6px;text-transform:uppercase;letter-spacing:1px}
.section{padding:0 20px 20px}
.section-title{color:#888;font-size:12px;text-transform:uppercase;letter-spacing:2px;margin-bottom:12px}
.account-card{background:#1a1a3e;border:1px solid #2a2a5a;border-radius:12px;padding:15px;display:flex;align-items:center;gap:12px;margin-bottom:10px}
.account-icon{width:40px;height:40px;background:linear-gradient(135deg,#4285f4,#34a853);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px}
.account-info h3{font-size:14px;color:white}
.account-info p{font-size:11px;color:#888;margin-top:2px}
.badge{margin-left:auto;background:#1e3a5f;color:#4fc3f7;font-size:10px;padding:3px 8px;border-radius:20px}
.connect-btn{display:block;margin:0 20px 15px;padding:15px;background:linear-gradient(135deg,#7c6fff,#5a4fcf);color:white;border:none;border-radius:12px;font-size:15px;font-weight:bold;text-align:center;cursor:pointer;text-decoration:none}
.coming{text-align:center;color:#555;font-size:12px;padding:10px 20px 30px}
</style>
</head>
<body>
<div class="header">
  <div class="logo">☁️ Drive<span>Pool</span></div>
  <div class="subtitle">Your unified cloud storage</div>
</div>

<div class="stats">
  <div class="card"><h2>0</h2><p>Total Files</p></div>
  <div class="card"><h2>0 GB</h2><p>Used Storage</p></div>
  <div class="card"><h2>0</h2><p>Accounts</p></div>
  <div class="card"><h2>0 GB</h2><p>Free Storage</p></div>
</div>

<div class="section">
  <div class="section-title">Connected Accounts</div>
  <div class="account-card">
    <div class="account-icon">G</div>
    <div class="account-info">
      <h3>Google Drive</h3>
      <p>No account connected</p>
    </div>
    <span class="badge">+ Add</span>
  </div>
</div>

<a href="#" class="connect-btn">+ Connect Google Drive</a>
<p class="coming">Google Drive integration coming soon!</p>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
