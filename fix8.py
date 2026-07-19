#!/usr/bin/env python3
"""
RAFIN's Chat Listener - COMPLETE FIXED VERSION
- Random device parameters per request
- Per-UID rate limiting (4 sec gap)
- Automatic retry on 400 (exponential backoff)
- Works with Pb2 protobufs
"""

import asyncio
import sys
import struct
import binascii
import time
import random
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

import aiohttp
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ========== PROTOBUF IMPORTS ==========
try:
    from Pb2 import MajoRLoGinrEq_pb2   # request
    from Pb2 import MajoRLoGinrEs_pb2   # response
    from Pb2 import PorTs_pb2           # GetLoginData
    from Pb2 import DEcwHisPErMsG_pb2   # whisper decode
except ImportError:
    print("❌ Pb2 modules not found. Create a 'Pb2' folder with the compiled protobuf files.")
    sys.exit(1)

# ========== CONSTANTS ==========
STATIC_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
STATIC_IV  = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
RIFATx = "1.123.17"

# ========== GLOBALS ==========
whisper_writer = None
last_sender = None
_last_request_time = {}  # rate limiter per UID

# ========== RATE LIMITER ==========
def rate_limit_uid(uid: str, min_interval: float = 4.0):
    """Ensure at least min_interval seconds between requests for same uid."""
    now = time.time()
    if uid in _last_request_time:
        elapsed = now - _last_request_time[uid]
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed + random.uniform(0, 0.5)
            print(f"⏳ Rate limit: sleeping {sleep_time:.2f}s for UID {uid}")
            time.sleep(sleep_time)
    _last_request_time[uid] = time.time()

# ========== DEVICE RANDOMIZATION ==========
def random_device_params():
    """Return randomized device parameters for MajorLogin."""
    screens = [
        (720, 1600, "320"),
        (1080, 1920, "420"),
        (1080, 2400, "440"),
        (1440, 2560, "560"),
        (720, 1280, "280"),
    ]
    cpus = [
        "ARMv8 | 2400 | 8",
        "ARMv7 VFPv3 NEON VMH | 2400 | 4",
        "ARMv8 | 2800 | 8",
        "ARMv7 | 2000 | 4",
    ]
    gpus = [
        "Adreno (TM) 640",
        "Adreno (TM) 630",
        "Mali-G72 MP12",
        "PowerVR Rogue GE8320",
    ]
    ram = [4096, 6144, 8192, 4096, 3072]
    screen = random.choice(screens)
    return {
        "screen_width": screen[0],
        "screen_height": screen[1],
        "dpi": screen[2],
        "cpu_info": random.choice(cpus),
        "memory": random.choice(ram),
        "gpu_renderer": random.choice(gpus),
        "gpu_version": "OpenGL ES 3.2 V@1.50" if random.random() > 0.5 else "OpenGL ES 3.0 V@1.0",
        "os_arch": random.choice(["64", "32"]),
        "graphics_api": random.choice(["OpenGLES3", "OpenGLES2"]),
        "system_software": random.choice([
            "Android OS 11 / API-30 (RQ3A.210805.001)",
            "Android OS 12 / API-31 (SP1A.210812.016)",
            "Android OS 13 / API-33 (TP1A.220624.014)",
        ]),
        "telecom_operator": random.choice(["Verizon", "AT&T", "T-Mobile", "Vodafone", "Airtel"]),
        "network_type": random.choice(["WIFI", "4G", "5G"]),
        "unique_device_id": f"Google|{uuid.uuid4()}",
        "client_ip": "",
    }

# ========== OAuth ==========
async def GeNeRaTeAccEss(uid: str, password: str) -> Tuple[Optional[str], Optional[str]]:
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "User-Agent": "RAFIN/1.0 (Linux; Android 13; SM-S918B Build/TP1A.220.624.014)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close"
    }
    data = {
        "uid": uid,
        "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=data) as resp:
            if resp.status != 200:
                return None, None
            js = await resp.json()
            return js.get("open_id"), js.get("access_token")

# ========== BUILD MAJORLOGIN WITH RANDOMIZATION ==========
async def EncRypTMajoRLoGin(open_id: str, access_token: str, region: str = "BD") -> bytes:
    """Build and encrypt MajorLogin protobuf with randomized device data."""
    dev = random_device_params()
    # Try to get public IP
    try:
        ip = requests.get('https://api.ipify.org', timeout=3).text
    except:
        ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"

    major_login = MajoRLoGinrEq_pb2.MajorLogin()
    major_login.event_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    major_login.game_name = "free fire"
    major_login.platform_id = 2
    major_login.client_version = RIFATx
    major_login.client_version_code = "2024010012"
    major_login.system_software = dev["system_software"]
    major_login.system_hardware = "Handheld"
    major_login.device_type = "Handheld"
    major_login.telecom_operator = dev["telecom_operator"]
    major_login.network_operator_a = dev["telecom_operator"]
    major_login.network_type = dev["network_type"]
    major_login.network_type_a = dev["network_type"]
    major_login.screen_width = dev["screen_width"]
    major_login.screen_height = dev["screen_height"]
    major_login.screen_dpi = dev["dpi"]
    major_login.processor_details = dev["cpu_info"]
    major_login.cpu_type = 2
    major_login.cpu_architecture = dev["os_arch"]
    major_login.memory = dev["memory"]
    major_login.gpu_renderer = dev["gpu_renderer"]
    major_login.gpu_version = dev["gpu_version"]
    major_login.graphics_api = dev["graphics_api"]
    major_login.unique_device_id = dev["unique_device_id"]
    major_login.client_ip = ip
    major_login.language = "en"
    major_login.open_id = open_id
    major_login.open_id_type = "4"
    major_login.login_open_id_type = 4
    major_login.access_token = access_token
    major_login.login_by = 3
    major_login.platform_sdk_id = 2
    major_login.origin_platform_type = "4"
    major_login.primary_platform_type = "4"

    # Randomize storage
    major_login.external_storage_total = random.randint(100000, 150000)
    major_login.external_storage_available = random.randint(30000, 60000)
    major_login.internal_storage_total = random.randint(90000, 130000)
    major_login.internal_storage_available = random.randint(15000, 35000)
    major_login.game_disk_storage_total = random.randint(20000, 30000)
    major_login.game_disk_storage_available = random.randint(15000, 25000)
    major_login.external_sdcard_total_storage = random.randint(90000, 140000)
    major_login.external_sdcard_avail_storage = random.randint(20000, 60000)
    major_login.library_path = f"/data/app/~~{random.randint(1000,9999)}/base.apk"
    major_login.library_token = f"{random.randint(1000,9999)}|base.apk"
    major_login.client_using_version = f"{random.randint(10000000,99999999)}"
    major_login.supported_astc_bitset = 16383
    major_login.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    major_login.loading_time = random.randint(8000, 20000)
    major_login.release_channel = "android"
    major_login.channel_type = 3
    major_login.reg_avatar = random.randint(1, 10)
    major_login.if_push = 1
    major_login.is_vpn = 0
    major_login.android_engine_init_flag = 110009
    # Some protobuf versions have region field
    if hasattr(major_login, 'region'):
        major_login.region = region.upper()

    serialized = major_login.SerializeToString()
    cipher = AES.new(STATIC_KEY, AES.MODE_CBC, STATIC_IV)
    padded = pad(serialized, AES.block_size)
    return cipher.encrypt(padded)

# ========== MAJORLOGIN WITH RETRY ==========
async def MajorLogin(payload: bytes, max_retries: int = 5) -> Optional[bytes]:
    """Send MajorLogin with retry on 400."""
    url = "https://loginbp.ggpolarbear.com/MajorLogin"
    headers = {
        "User-Agent": "RAFIN/1.0 (Linux; Android 13; SM-S918B Build/TP1A.220.624.014)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/octet-stream",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB54"
    }
    base_delay = 2
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload, headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    elif resp.status == 400:
                        print(f"⚠️ Attempt {attempt+1}: 400 Bad Request")
                        if attempt < max_retries - 1:
                            sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            print(f"   Retrying in {sleep_time:.2f} seconds...")
                            await asyncio.sleep(sleep_time)
                            continue
                    else:
                        print(f"❌ HTTP {resp.status}")
                        return None
        except Exception as e:
            print(f"⚠️ Request error: {e}")
            if attempt < max_retries - 1:
                sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(sleep_time)
                continue
    return None

# ========== DECRYPT RESPONSES ==========
async def DecRypTMajoRLoGin(data: bytes):
    proto = MajoRLoGinrEs_pb2.MajorLoginRes()
    proto.ParseFromString(data)
    return proto

async def DecRypTLoGinDaTa(data: bytes):
    proto = PorTs_pb2.GetLoginData()
    proto.ParseFromString(data)
    return proto

# ========== GET LOGIN DATA ==========
async def GetLoginData(base_url: str, payload: bytes, token: str) -> Optional[bytes]:
    url = f"{base_url}/GetLoginData"
    headers = {
        "User-Agent": "RAFIN/1.0 (Linux; Android 13; SM-S918B Build/TP1A.220.624.014)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB54"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers) as resp:
            if resp.status == 200:
                return await resp.read()
    return None

# ========== CRYPTO HELPERS FOR CHAT PACKETS ==========
async def EnC_PacKeT(hex_data: str, key: bytes, iv: bytes) -> str:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    raw = bytes.fromhex(hex_data)
    padded = pad(raw, AES.block_size)
    return cipher.encrypt(padded).hex()

async def DEc_PacKeT(hex_data: str, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = bytes.fromhex(hex_data)
    decrypted = cipher.decrypt(encrypted)
    return unpad(decrypted, AES.block_size)

async def xAuThSTarTuP(bot_uid: int, token: str, timestamp: int, key: bytes, iv: bytes) -> str:
    uid_hex = hex(bot_uid)[2:]
    uid_len = len(uid_hex)
    encrypted_timestamp = hex(timestamp)[2:]
    encrypted_account_token = token.encode().hex()
    encrypted_packet = await EnC_PacKeT(encrypted_account_token, key, iv)
    encrypted_packet_length = hex(len(encrypted_packet) // 2)[2:]

    if uid_len == 9:
        headers = '0000000'
    elif uid_len == 8:
        headers = '00000000'
    elif uid_len == 10:
        headers = '000000'
    elif uid_len == 7:
        headers = '000000000'
    else:
        headers = '0000000'
    return f"0115{headers}{uid_hex}{encrypted_timestamp}00000{encrypted_packet_length}{encrypted_packet}"

# ========== CHAT LOOP ==========
def fmt_uid(uid: str) -> str:
    return "💔".join(uid)

async def chat_loop(ip: str, port: int, auth_token_hex: str):
    global whisper_writer, last_sender
    while True:
        try:
            reader, writer = await asyncio.open_connection(ip, port)
            whisper_writer = writer
            auth_bytes = bytes.fromhex(auth_token_hex)
            writer.write(auth_bytes)
            await writer.drain()
            print("✅ Chat server connected. Waiting for packets...")

            while True:
                # Read packet length (2 bytes)
                len_data = await reader.readexactly(2)
                pkt_len = struct.unpack('>H', len_data)[0]
                pkt_data = await reader.readexactly(pkt_len)
                hex_data = pkt_data.hex()

                pkt_type = hex_data[:4]  # first 2 bytes
                if pkt_type in ["1200", "1201"]:
                    encrypted_part = hex_data[10:]  # skip 5-byte header
                    try:
                        decrypted = await DEc_PacKeT(encrypted_part, STATIC_KEY, STATIC_IV)
                        msg = DEcwHisPErMsG_pb2.DecodeWhisper()
                        msg.ParseFromString(decrypted)
                        if msg.Data.chat_type == 2:  # private
                            sender = msg.Data.uid
                            nickname = msg.Data.Details.Nickname
                            message_text = msg.Data.msg
                            print(f"\n📩 [{datetime.now().strftime('%H:%M:%S')}] {nickname} ({fmt_uid(str(sender))}): {message_text}")
                            last_sender = sender
                    except Exception as e:
                        print(f"❌ Decryption error: {e}")
                else:
                    # ignore other packets
                    pass

        except asyncio.IncompleteReadError:
            print("Connection lost, reconnecting...")
        except Exception as e:
            print(f"Error: {e}, reconnecting...")
        finally:
            if whisper_writer:
                try:
                    whisper_writer.close()
                except:
                    pass
                whisper_writer = None
        await asyncio.sleep(3)

# ========== SEND PRIVATE MESSAGE ==========
async def send_private_message(target_uid: int, message: str, bot_uid: int, key: bytes, iv: bytes) -> bool:
    """Send a private message using xSEndMsg from xC4.py (if available)."""
    try:
        from xC4 import xSEndMsg
        packet = await xSEndMsg(message, 2, target_uid, bot_uid, key, iv)
        if packet and whisper_writer:
            whisper_writer.write(packet)
            await whisper_writer.drain()
            return True
    except ImportError:
        print("❌ xC4.py not found. Cannot send messages.")
    except Exception as e:
        print(f"❌ Send error: {e}")
    return False

# ========== MAIN ==========
async def main():
    print("=" * 60)
    print("RAFIN's Chat Listener - COMPLETE FIXED VERSION")
    print("=" * 60)

    uid = input("Bot UID: ").strip()
    password = input("Bot password: ").strip()

    # Rate limit OAuth too
    rate_limit_uid(uid, 4)

    print("[*] Getting access token...")
    open_id, access_token = await GeNeRaTeAccEss(uid, password)
    if not open_id:
        print("❌ OAuth failed. Check UID/password.")
        return
    print("✅ Access token obtained.")

    print("[*] Building MajorLogin with randomized device...")
    login_payload = await EncRypTMajoRLoGin(open_id, access_token, region="BD")

    print("[*] Sending MajorLogin (with retry)...")
    login_resp = await MajorLogin(login_payload)
    if not login_resp:
        print("❌ MajorLogin failed after retries.")
        return
    login_data = await DecRypTMajoRLoGin(login_resp)

    bot_uid = login_data.account_uid
    key = login_data.key
    iv = login_data.iv
    jwt_token = login_data.token
    timestamp = login_data.timestamp
    print(f"✅ Logged in as UID: {bot_uid}")

    print("[*] Getting chat server...")
    base_url = login_data.url
    login_data_resp = await GetLoginData(base_url, login_payload, jwt_token)
    if not login_data_resp:
        print("❌ GetLoginData failed.")
        return
    login_data_dec = await DecRypTLoGinDaTa(login_data_resp)
    chat_ip_port = login_data_dec.AccountIP_Port
    if not chat_ip_port:
        print("❌ No chat server returned.")
        return
    chat_ip, chat_port = chat_ip_port.split(":")
    chat_port = int(chat_port)
    print(f"✅ Chat server: {chat_ip}:{chat_port}")

    print("[*] Building auth token...")
    auth_token_hex = await xAuThSTarTuP(int(bot_uid), jwt_token, int(timestamp), key, iv)

    # Start chat listener
    asyncio.create_task(chat_loop(chat_ip, chat_port, auth_token_hex))

    # Input loop for replies
    print("\n💡 Type a message to reply to the last sender. Type 'exit' to quit.\n")
    while True:
        reply = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        if not reply:
            continue
        reply = reply.strip()
        if reply.lower() == 'exit':
            break
        if last_sender is None:
            print("⚠️ No one has messaged yet.")
            continue
        success = await send_private_message(last_sender, reply, int(bot_uid), key, iv)
        if success:
            print(f"✅ Reply sent to {last_sender}")
        else:
            print("❌ Failed to send.")

if __name__ == "__main__":
    asyncio.run(main())