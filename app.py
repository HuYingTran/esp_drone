import os
import sqlite3
import threading
import time
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify

UPLOAD_FOLDER = 'static/uploads'
DB_FILE = 'drone.db'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'replace-with-a-secure-key'

# -------------------------
# Database helpers (sqlite)
# -------------------------
def init_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        timestamp TEXT,
        lat REAL,
        lon REAL,
        note TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        run_at TEXT,
        lat REAL,
        lon REAL,
        action TEXT,
        created_at TEXT
    )
    ''')
    con.commit()
    con.close()


def add_image(filename, lat=None, lon=None, note=''):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute('INSERT INTO images (filename, timestamp, lat, lon, note) VALUES (?, ?, ?, ?, ?)',
                (filename, datetime.utcnow().isoformat(), lat, lon, note))
    con.commit()
    con.close()


def get_images():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute('SELECT id, filename, timestamp, lat, lon, note FROM images ORDER BY id DESC')
    rows = cur.fetchall()
    con.close()
    return rows


def add_schedule(name, run_at_iso, lat, lon, action):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute('INSERT INTO schedules (name, run_at, lat, lon, action, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (name, run_at_iso, lat, lon, action, datetime.utcnow().isoformat()))
    con.commit()
    con.close()


def get_schedules():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute('SELECT id, name, run_at, lat, lon, action, created_at FROM schedules ORDER BY run_at DESC')
    rows = cur.fetchall()
    con.close()
    return rows


def remove_schedule(schedule_id):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
    con.commit()
    con.close()

# -------------------------
# Drone simulation
# -------------------------
DRONE_STATE = {
    'connected': True,  # cho drone mặc định đang kết nối
    'battery': 92.0,  # phần trăm pin (float để dễ giảm dần)
    'signal_strength': 56.0,  # % tín hiệu
    'sd_present': True,  # có thẻ SD
    'sd_used': 1024.0,  # dung lượng đã dùng (MB)
    'sd_total': 8192.0,  # tổng dung lượng (MB)
    'position': {
        'lat': 21.070735,   # Vĩ độ Bắc Ninh
        'lon': 105.383553,  # Kinh độ Bắc Ninh
        'alt': 100.0        # độ cao hiện tại (m)
    },
    'orientation': {
        'yaw': 1.01,    # hướng quay
        'pitch': 6.89,  # góc nghiêng trước/sau
        'roll': 0.67    # góc nghiêng trái/phải
    },
    'sensors': {
        'temperature': 25.0,  # °C
        'pressure': 1013.25   # hPa
    },
    'camera_latest': None,  # file ảnh gần nhất
    'flying': True,  # đang bay
}


def connect_drone():
    DRONE_STATE['connected'] = True
    print("Drone connected (mock)")

def disconnect_drone():
    DRONE_STATE['connected'] = False
    print("Drone disconnected (mock)")

def get_drone_status():
    if DRONE_STATE['connected']:
        DRONE_STATE['battery'] = max(0, DRONE_STATE['battery'] - random.uniform(0, 0.05))
        DRONE_STATE['signal_strength'] = max(10, 100 - random.uniform(0, 1))
        DRONE_STATE['sensors']['temperature'] += random.uniform(-0.1, 0.1)
        DRONE_STATE['sensors']['pressure'] += random.uniform(-0.5, 0.5)
        DRONE_STATE['orientation']['yaw'] = (DRONE_STATE['orientation']['yaw'] + random.uniform(-1, 1)) % 360
    return DRONE_STATE

def drone_takeoff():
    if not DRONE_STATE['connected']:
        return False
    DRONE_STATE['flying'] = True
    DRONE_STATE['position']['alt'] = 10.0
    print("Takeoff command (mock)")
    return True

def drone_land():
    if not DRONE_STATE['connected']:
        return False
    DRONE_STATE['flying'] = False
    DRONE_STATE['position']['alt'] = 0.0
    print("Land command (mock)")
    return True

def drone_move(direction):
    pos = DRONE_STATE['position']
    if not DRONE_STATE['flying']:
        return False
    step = 0.0001
    if direction == 'up': pos['alt'] += 1
    elif direction == 'down': pos['alt'] = max(0, pos['alt'] - 1)
    elif direction == 'left': pos['lon'] -= step
    elif direction == 'right': pos['lon'] += step
    elif direction == 'forward': pos['lat'] += step
    elif direction == 'backward': pos['lat'] -= step
    return True

def drone_capture_image(lat=None, lon=None):
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f'img_{ts}.txt'
    path = os.path.join(UPLOAD_FOLDER, filename)
    with open(path, 'w') as f:
        f.write(f"Simulated image at {ts}\nlat:{lat}\nlon:{lon}\n")
    add_image(filename, lat, lon, note='Simulated capture')
    DRONE_STATE['camera_latest'] = filename
    DRONE_STATE['sd_used'] += 10
    return filename

# -------------------------
# Scheduler
# -------------------------
def scheduler_loop(poll_interval=15):
    while True:
        try:
            schedules = get_schedules()
            now = datetime.utcnow()
            for s in schedules:
                sid, name, run_at, lat, lon, action, created_at = s
                run_at_dt = datetime.fromisoformat(run_at)
                if now >= run_at_dt and (now - run_at_dt) < timedelta(seconds=poll_interval + 60):
                    print(f"Executing schedule {sid}: {action}")
                    if action == 'capture': drone_capture_image(lat, lon)
                    elif action == 'takeoff': drone_takeoff()
                    elif action == 'land': drone_land()
                    remove_schedule(sid)
        except Exception as e:
            print("Scheduler error:", e)
        time.sleep(poll_interval)

# -------------------------
# Flask routes
# -------------------------
@app.route('/')
def home():
    status = get_drone_status()
    latest_img = status.get('camera_latest')
    latest_path = url_for('uploaded_file', filename=latest_img) if latest_img else None
    return render_template('home.html', status=status, latest_img=latest_img, latest_path=latest_path)

@app.route('/control', methods=['POST'])
def control():
    cmd = request.form.get('cmd')
    if cmd == 'connect': connect_drone(); flash('Drone connected.')
    elif cmd == 'disconnect': disconnect_drone(); flash('Drone disconnected.')
    elif cmd == 'takeoff': drone_takeoff(); flash('Takeoff command sent.')
    elif cmd == 'land': drone_land(); flash('Land command sent.')
    elif cmd == 'capture': pos = DRONE_STATE['position']; fname = drone_capture_image(pos['lat'], pos['lon']); flash(f'Captured {fname}')
    elif cmd in ['up','down','left','right','forward','backward']: drone_move(cmd); flash(f'Moved {cmd}.')
    return redirect(url_for('home'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/settings', methods=['GET','POST'])
def settings():
    if request.method == 'POST':
        name = request.form.get('name') or 'Mission'
        run_at = request.form.get('run_at')
        lat = float(request.form.get('lat') or 0)
        lon = float(request.form.get('lon') or 0)
        action = request.form.get('action')
        try:
            dt = datetime.fromisoformat(run_at) if 'T' in run_at else datetime.strptime(run_at, '%Y-%m-%d %H:%M')
        except Exception:
            flash('Invalid datetime format.')
            return redirect(url_for('settings'))
        add_schedule(name, dt.isoformat(), lat, lon, action)
        flash('Schedule added.')
        return redirect(url_for('settings'))
    return render_template('settings.html', schedules=get_schedules())

@app.route('/gallery')
def gallery():
    return render_template('gallery.html', images=get_images(), schedules=get_schedules())

@app.route('/api/status')
def api_status():
    return jsonify(get_drone_status())

import sqlite3
from datetime import datetime
import os

DB_FILE = 'drone.db'

UPLOAD_FOLDER = 'static/uploads'

# -------------------------
if __name__ == '__main__':
    init_db()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
