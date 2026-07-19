import os
import sys
import time
import uuid
import json
import queue
import random
import struct
import asyncio
import threading
from datetime import datetime, timezone
from typing import Optional, Tuple

import aiohttp
import requests
from flask import Flask, jsonify, request, render_template_string
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

try:
    from Pb2 import MajoRLoGinrEq_pb2
    from Pb2 import MajoRLoGinrEs_pb2
    from Pb2 import PorTs_pb2
    from Pb2 import DEcwHisPErMsG_pb2
    PB2_AVAILABLE = True
except Exception:
    PB2_AVAILABLE = False

STATIC_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
STATIC_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
CLIENT_VERSION = "1.123.17"

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Render Chat Listener</title>
  <style>
    :root { color-scheme: dark; --bg:#0b1220; --card:#131c31; --muted:#93a4c3; --text:#eef4ff; --line:#22304f; --primary:#46c2a8; --danger:#ff6b7a; }
    *{box-sizing:border-box} body{margin:0;font-family:Inter,system-ui,sans-serif;background:linear-gradient(180deg,#08101d,#0d1730);color:var(--text)}
    .wrap{max-width:1100px;margin:auto;padding:24px} .grid{display:grid;grid-template-columns:360px 1fr;gap:20px} @media(max-width:900px){.grid{grid-template-columns:1fr}}
    .card{background:rgba(19,28,49,.92);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:0 10px 30px rgba(0,0,0,.25)}
    h1,h2,h3{margin:0 0 10px} p{color:var(--muted)} label{display:block;font-size:14px;margin:12px 0 6px;color:#c9d6f0}
    input,textarea,select{width:100%;padding:12px 14px;border-radius:12px;border:1px solid var(--line);background:#0b1220;color:var(--text)}
    textarea{min-height:110px;resize:vertical} button{border:0;border-radius:12px;padding:12px 14px;font-weight:700;cursor:pointer}
    .primary{background:var(--primary);color:#06231e}.ghost{background:#15213d;color:var(--text);border:1px solid var(--line)}.danger{background:var(--danger);color:#2b0810}
    .row{display:flex;gap:10px;flex-wrap:wrap}.status{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.pill{padding:10px 12px;border-radius:12px;background:#0b1220;border:1px solid var(--line)}
    .mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.logs{height:520px;overflow:auto;white-space:pre-wrap;background:#0b1220;border:1px solid var(--line);border-radius:14px;padding:14px}
    .hint{font-size:13px;color:var(--muted)} .ok{color:#84f5d2}.bad{color:#ff98a3}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Render Chat Listener</h1>
    <p>Web wrapper for the uploaded Python listener. Add the missing <span class="mono">Pb2/</span> folder and <span class="mono">xC4.py</span> to make full login, packet decode, and sending work.</p>
    <div class="grid">
      <section class="card">
        <h2>Control</h2>
        <label>Bot UID</label>
        <input id="uid" placeholder="Enter bot UID">
        <label>Password</label>
        <input id="password" type="password" placeholder="Enter bot password">
        <label>Region</label>
        <select id="region"><option>BD</option><option>SG</option><option>IND</option><option>BR</option><option>ME</option></select>
        <div class="row" style="margin-top:14px">
          <button class="primary" onclick="startBot()">Start</button>
          <button class="danger" onclick="stopBot()">Stop</button>
          <button class="ghost" onclick="refreshStatus()">Refresh</button>
        </div>
        <label style="margin-top:18px">Reply message</label>
        <textarea id="message" placeholder="Type reply to last sender"></textarea>
        <div class="row" style="margin-top:10px">
          <button class="primary" onclick="sendReply()">Send reply</button>
        </div>
        <p class="hint">For Render, keep credentials in environment variables when possible. This UI is mainly for quick control and testing.</p>
      </section>
      <section class="card">
        <h2>Status</h2>
        <div class="status" id="status"></div>
        <h3 style="margin-top:18px">Logs</h3>
        <div class="logs mono" id="logs"></div>
      </section>
    </div>
  </div>
<script>
async function api(path, options={}){ const res = await fetch(path,{headers:{'Content-Type':'application/json'},...options}); return res.json(); }
function drawStatus(data){
  const box=document.getElementById('status');
  box.innerHTML=`
    <div class="pill"><strong>Running</strong><div class="${data.running?'ok':'bad'}">${data.running}</div></div>
    <div class="pill"><strong>PB2 ready</strong><div class="${data.pb2_available?'ok':'bad'}">${data.pb2_available}</div></div>
    <div class="pill"><strong>Logged in</strong><div>${data.logged_in}</div></div>
    <div class="pill"><strong>Bot UID</strong><div class="mono">${data.bot_uid||'-'}</div></div>
    <div class="pill"><strong>Last sender</strong><div class="mono">${data.last_sender||'-'}</div></div>
    <div class="pill"><strong>Chat server</strong><div class="mono">${data.chat_server||'-'}</div></div>`;
  document.getElementById('logs').textContent=(data.logs||[]).join('\n');
}
async function refreshStatus(){ drawStatus(await api('/api/status')); }
async function startBot(){
  const payload={uid:uid.value.trim(),password:password.value,region:region.value};
  const data=await api('/api/start',{method:'POST',body:JSON.stringify(payload)}); drawStatus(data);
}
async function stopBot(){ drawStatus(await api('/api/stop',{method:'POST'})); }
async function sendReply(){
  const data=await api('/api/send',{method:'POST',body:JSON.stringify({message:message.value})});
  alert(data.message || (data.ok?'Sent':'Failed')); refreshStatus();
}
refreshStatus(); setInterval(refreshStatus, 5000);
</script>
</body>
</html>
"""

class ListenerState:
    def __init__(self):
        self.running = False
        self.logged_in = False
        self.bot_uid = None
        self.last_sender = None
        self.chat_server = None
        self.thread = None
        self.loop = None
        self.stop_event = None
        self.writer = None
        self.logs = []
        self.key = None
        self.iv = None
        self.jwt_token = None
        self.timestamp = None
        self.uid = None
        self.password = None
        self.region = 'BD'
        self._last_request_time = {}

    def log(self, message: str):
        stamp = datetime.now().strftime('%H:%M:%S')
        line = f'[{stamp}] {message}'
        self.logs.append(line)
        self.logs = self.logs[-200:]
        print(line, flush=True)

state = ListenerState()


def rate_limit_uid(uid: str, min_interval: float = 4.0):
    now = time.time()
    if uid in state._last_request_time:
        elapsed = now - state._last_request_time[uid]
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed + random.uniform(0, 0.5)
            state.log(f'Rate limit sleep {sleep_time:.2f}s for UID {uid}')
            time.sleep(sleep_time)
    state._last_request_time[uid] = time.time()


def random_device_params():
    screens = [(720,1600,'320'), (1080,1920,'420'), (1080,2400,'440'), (1440,2560,'560'), (720,1280,'280')]
    cpus = ['ARMv8 | 2400 | 8', 'ARMv7 VFPv3 NEON VMH | 2400 | 4', 'ARMv8 | 2800 | 8', 'ARMv7 | 2000 | 4']
    gpus = ['Adreno (TM) 640', 'Adreno (TM) 630', 'Mali-G72 MP12', 'PowerVR Rogue GE8320']
    return {
        'screen_width': random.choice(screens)[0],
        'screen_height': random.choice(screens)[1],
        'dpi': random.choice(screens)[2],
        'cpu_info': random.choice(cpus),
        'memory': random.choice([3072, 4096, 6144, 8192]),
        'gpu_renderer': random.choice(gpus),
        'gpu_version': 'OpenGL ES 3.2 V@1.50' if random.random() > 0.5 else 'OpenGL ES 3.0 V@1.0',
        'os_arch': random.choice(['64', '32']),
        'graphics_api': random.choice(['OpenGLES3', 'OpenGLES2']),
        'system_software': random.choice(['Android OS 11 / API-30 (RQ3A.210805.001)', 'Android OS 12 / API-31 (SP1A.210812.016)', 'Android OS 13 / API-33 (TP1A.220624.014)']),
        'telecom_operator': random.choice(['Verizon', 'AT&T', 'T-Mobile', 'Vodafone', 'Airtel']),
        'network_type': random.choice(['WIFI', '4G', '5G']),
        'unique_device_id': f'Google|{uuid.uuid4()}'
    }


async def generate_access(uid: str, password: str) -> Tuple[Optional[str], Optional[str]]:
    url = 'https://100067.connect.garena.com/oauth/guest/token/grant'
    headers = {'User-Agent': 'RAFIN/1.0 (Linux; Android 13)', 'Content-Type': 'application/x-www-form-urlencoded', 'Accept-Encoding': 'gzip, deflate, br', 'Connection': 'close'}
    data = {'uid': uid, 'password': password, 'response_type': 'token', 'client_type': '2', 'client_secret': '2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3', 'client_id': '100067'}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=data) as resp:
            if resp.status != 200:
                state.log(f'OAuth failed with HTTP {resp.status}')
                return None, None
            js = await resp.json()
            return js.get('open_id'), js.get('access_token')


async def encrypt_major_login(open_id: str, access_token: str, region: str = 'BD') -> bytes:
    if not PB2_AVAILABLE:
        raise RuntimeError('Pb2 modules not found. Upload Pb2 folder to deploy this app.')
    dev = random_device_params()
    try:
        ip = requests.get('https://api.ipify.org', timeout=3).text
    except Exception:
        ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"
    major_login = MajoRLoGinrEq_pb2.MajorLogin()
    major_login.event_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    major_login.game_name = 'free fire'
    major_login.platform_id = 2
    major_login.client_version = CLIENT_VERSION
    major_login.client_version_code = '2024010012'
    major_login.system_software = dev['system_software']
    major_login.system_hardware = 'Handheld'
    major_login.device_type = 'Handheld'
    major_login.telecom_operator = dev['telecom_operator']
    major_login.network_operator_a = dev['telecom_operator']
    major_login.network_type = dev['network_type']
    major_login.network_type_a = dev['network_type']
    major_login.screen_width = dev['screen_width']
    major_login.screen_height = dev['screen_height']
    major_login.screen_dpi = dev['dpi']
    major_login.processor_details = dev['cpu_info']
    major_login.cpu_type = 2
    major_login.cpu_architecture = dev['os_arch']
    major_login.memory = dev['memory']
    major_login.gpu_renderer = dev['gpu_renderer']
    major_login.gpu_version = dev['gpu_version']
    major_login.graphics_api = dev['graphics_api']
    major_login.unique_device_id = dev['unique_device_id']
    major_login.client_ip = ip
    major_login.language = 'en'
    major_login.open_id = open_id
    major_login.open_id_type = '4'
    major_login.login_open_id_type = 4
    major_login.access_token = access_token
    major_login.login_by = 3
    major_login.platform_sdk_id = 2
    major_login.origin_platform_type = '4'
    major_login.primary_platform_type = '4'
    major_login.external_storage_total = random.randint(100000, 150000)
    major_login.external_storage_available = random.randint(30000, 60000)
    major_login.internal_storage_total = random.randint(90000, 130000)
    major_login.internal_storage_available = random.randint(15000, 35000)
    major_login.game_disk_storage_total = random.randint(20000, 30000)
    major_login.game_disk_storage_available = random.randint(15000, 25000)
    major_login.external_sdcard_total_storage = random.randint(90000, 140000)
    major_login.external_sdcard_avail_storage = random.randint(20000, 60000)
    major_login.library_path = f'/data/app/~~{random.randint(1000,9999)}/base.apk'
    major_login.library_token = f'{random.randint(1000,9999)}|base.apk'
    major_login.client_using_version = f'{random.randint(10000000,99999999)}'
    major_login.supported_astc_bitset = 16383
    major_login.analytics_detail = b'FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=='
    major_login.loading_time = random.randint(8000, 20000)
    major_login.release_channel = 'android'
    major_login.channel_type = 3
    major_login.reg_avatar = random.randint(1, 10)
    major_login.if_push = 1
    major_login.is_vpn = 0
    major_login.android_engine_init_flag = 110009
    if hasattr(major_login, 'region'):
        major_login.region = region.upper()
    serialized = major_login.SerializeToString()
    cipher = AES.new(STATIC_KEY, AES.MODE_CBC, STATIC_IV)
    return cipher.encrypt(pad(serialized, AES.block_size))


async def major_login(payload: bytes, max_retries: int = 5) -> Optional[bytes]:
    url = 'https://loginbp.ggpolarbear.com/MajorLogin'
    headers = {'User-Agent': 'RAFIN/1.0 (Linux; Android 13)', 'Connection': 'Keep-Alive', 'Accept-Encoding': 'gzip', 'Content-Type': 'application/octet-stream', 'X-Unity-Version': '2018.4.11f1', 'X-GA': 'v1 1', 'ReleaseVersion': 'OB54'}
    base_delay = 2
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload, headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    if resp.status == 400 and attempt < max_retries - 1:
                        sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        state.log(f'MajorLogin 400, retry in {sleep_time:.2f}s')
                        await asyncio.sleep(sleep_time)
                        continue
                    state.log(f'MajorLogin failed with HTTP {resp.status}')
                    return None
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(base_delay * (2 ** attempt) + random.uniform(0, 1))
            else:
                state.log(f'MajorLogin request error: {e}')
    return None


async def decrypt_major_login(data: bytes):
    proto = MajoRLoGinrEs_pb2.MajorLoginRes()
    proto.ParseFromString(data)
    return proto


async def get_login_data(base_url: str, payload: bytes, token: str) -> Optional[bytes]:
    url = f'{base_url}/GetLoginData'
    headers = {'User-Agent': 'RAFIN/1.0 (Linux; Android 13)', 'Connection': 'Keep-Alive', 'Accept-Encoding': 'gzip', 'Authorization': f'Bearer {token}', 'Content-Type': 'application/x-www-form-urlencoded', 'X-Unity-Version': '2018.4.11f1', 'X-GA': 'v1 1', 'ReleaseVersion': 'OB54'}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers) as resp:
            if resp.status == 200:
                return await resp.read()
    return None


async def decrypt_login_data(data: bytes):
    proto = PorTs_pb2.GetLoginData()
    proto.ParseFromString(data)
    return proto


async def enc_packet(hex_data: str, key: bytes, iv: bytes) -> str:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(bytes.fromhex(hex_data), AES.block_size)).hex()


async def dec_packet(hex_data: str, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(bytes.fromhex(hex_data)), AES.block_size)


async def auth_startup(bot_uid: int, token: str, timestamp: int, key: bytes, iv: bytes) -> str:
    uid_hex = hex(bot_uid)[2:]
    uid_len = len(uid_hex)
    encrypted_timestamp = hex(timestamp)[2:]
    encrypted_account_token = token.encode().hex()
    encrypted_packet = await enc_packet(encrypted_account_token, key, iv)
    encrypted_packet_length = hex(len(encrypted_packet) // 2)[2:]
    headers = '0000000'
    if uid_len == 8: headers = '00000000'
    elif uid_len == 10: headers = '000000'
    elif uid_len == 7: headers = '000000000'
    return f'0115{headers}{uid_hex}{encrypted_timestamp}00000{encrypted_packet_length}{encrypted_packet}'


async def chat_loop(ip: str, port: int, auth_token_hex: str):
    while state.running and not state.stop_event.is_set():
        try:
            reader, writer = await asyncio.open_connection(ip, port)
            state.writer = writer
            writer.write(bytes.fromhex(auth_token_hex))
            await writer.drain()
            state.log(f'Connected chat server {ip}:{port}')
            while state.running and not state.stop_event.is_set():
                len_data = await reader.readexactly(2)
                pkt_len = struct.unpack('>H', len_data)[0]
                pkt_data = await reader.readexactly(pkt_len)
                hex_data = pkt_data.hex()
                if hex_data[:4] in ['1200', '1201']:
                    try:
                        decrypted = await dec_packet(hex_data[10:], STATIC_KEY, STATIC_IV)
                        msg = DEcwHisPErMsG_pb2.DecodeWhisper()
                        msg.ParseFromString(decrypted)
                        if msg.Data.chat_type == 2:
                            state.last_sender = msg.Data.uid
                            nickname = getattr(msg.Data.Details, 'Nickname', 'Unknown')
                            text = msg.Data.msg
                            state.log(f'PM from {nickname} ({state.last_sender}): {text}')
                    except Exception as e:
                        state.log(f'Packet decode error: {e}')
        except asyncio.IncompleteReadError:
            state.log('Connection lost, reconnecting...')
        except Exception as e:
            state.log(f'Chat loop error: {e}')
        finally:
            if state.writer:
                try:
                    state.writer.close()
                except Exception:
                    pass
                state.writer = None
            await asyncio.sleep(3)


async def send_private_message(target_uid: int, message: str, bot_uid: int, key: bytes, iv: bytes) -> bool:
    try:
        from xC4 import xSEndMsg
    except Exception:
        state.log('xC4.py missing. Upload it to enable send.')
        return False
    try:
        packet = await xSEndMsg(message, 2, target_uid, bot_uid, key, iv)
        if packet and state.writer:
            state.writer.write(packet)
            await state.writer.drain()
            state.log(f'Sent reply to {target_uid}')
            return True
    except Exception as e:
        state.log(f'Send error: {e}')
    return False


async def runner(uid: str, password: str, region: str):
    state.uid = uid
    state.password = password
    state.region = region
    state.running = True
    state.logged_in = False
    state.stop_event = asyncio.Event()
    if not PB2_AVAILABLE:
        state.log('Pb2 modules not found. Upload Pb2 folder before starting.')
        return
    rate_limit_uid(uid, 4)
    state.log('Getting access token...')
    open_id, access_token = await generate_access(uid, password)
    if not open_id:
        state.log('OAuth failed. Check UID/password.')
        state.running = False
        return
    state.log('Access token obtained.')
    payload = await encrypt_major_login(open_id, access_token, region=region)
    state.log('Sending MajorLogin...')
    login_resp = await major_login(payload)
    if not login_resp:
        state.log('MajorLogin failed.')
        state.running = False
        return
    login_data = await decrypt_major_login(login_resp)
    state.bot_uid = getattr(login_data, 'account_uid', None)
    state.key = getattr(login_data, 'key', None)
    state.iv = getattr(login_data, 'iv', None)
    state.jwt_token = getattr(login_data, 'token', None)
    state.timestamp = getattr(login_data, 'timestamp', None)
    base_url = getattr(login_data, 'url', None)
    state.logged_in = True
    state.log(f'Logged in as UID {state.bot_uid}')
    login_data_resp = await get_login_data(base_url, payload, state.jwt_token)
    if not login_data_resp:
        state.log('GetLoginData failed.')
        state.running = False
        return
    login_data_dec = await decrypt_login_data(login_data_resp)
    chat_ip_port = getattr(login_data_dec, 'AccountIP_Port', '')
    if not chat_ip_port:
        state.log('No chat server returned.')
        state.running = False
        return
    ip, port = chat_ip_port.split(':')
    state.chat_server = chat_ip_port
    auth_token_hex = await auth_startup(int(state.bot_uid), state.jwt_token, int(state.timestamp), state.key, state.iv)
    await chat_loop(ip, int(port), auth_token_hex)


def start_background(uid: str, password: str, region: str):
    if state.running:
        return
    def _target():
        loop = asyncio.new_event_loop()
        state.loop = loop
        asyncio.set_event_loop(loop)
        loop.run_until_complete(runner(uid, password, region))
    state.thread = threading.Thread(target=_target, daemon=True)
    state.thread.start()


def snapshot():
    return {
        'running': state.running,
        'pb2_available': PB2_AVAILABLE,
        'logged_in': state.logged_in,
        'bot_uid': state.bot_uid,
        'last_sender': state.last_sender,
        'chat_server': state.chat_server,
        'logs': state.logs,
    }


@app.get('/')
def home():
    return render_template_string(HTML)


@app.get('/api/status')
def api_status():
    return jsonify(snapshot())


@app.post('/api/start')
def api_start():
    data = request.get_json(silent=True) or {}
    uid = data.get('uid') or os.getenv('BOT_UID', '')
    password = data.get('password') or os.getenv('BOT_PASSWORD', '')
    region = data.get('region') or os.getenv('BOT_REGION', 'BD')
    if not uid or not password:
        state.log('Missing UID or password.')
        return jsonify({**snapshot(), 'error': 'Missing UID or password'}), 400
    start_background(uid, password, region)
    state.log('Background listener started.')
    return jsonify(snapshot())


@app.post('/api/stop')
def api_stop():
    state.running = False
    state.logged_in = False
    if state.stop_event is not None and state.loop is not None:
        state.loop.call_soon_threadsafe(state.stop_event.set)
    if state.writer:
        try:
            state.writer.close()
        except Exception:
            pass
        state.writer = None
    state.log('Listener stopped.')
    return jsonify(snapshot())


@app.post('/api/send')
def api_send():
    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({'ok': False, 'message': 'Message is empty'}), 400
    if state.last_sender is None:
        return jsonify({'ok': False, 'message': 'No last sender available'}), 400
    if not state.loop:
        return jsonify({'ok': False, 'message': 'Listener not running'}), 400
    future = asyncio.run_coroutine_threadsafe(send_private_message(int(state.last_sender), message, int(state.bot_uid), state.key, state.iv), state.loop)
    try:
        ok = future.result(timeout=20)
    except Exception as e:
        ok = False
        state.log(f'Send future error: {e}')
    return jsonify({'ok': ok, 'message': 'Reply sent' if ok else 'Reply failed'})


@app.get('/healthz')
def healthz():
    return {'ok': True, 'running': state.running, 'pb2_available': PB2_AVAILABLE}


if __name__ == '__main__':
    port = int(os.getenv('PORT', '10000'))
    app.run(host='0.0.0.0', port=port)
