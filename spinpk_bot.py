#!/usr/bin/env python3
"""
SpinPK Auto Bot - GitHub Actions Edition
Cooldown: 4h 50m (17400 sec) between spins per token
"""

import requests
import json
import os
import sys
import time
from datetime import datetime, timedelta

# ==================== CONFIG ====================
DEVICE_ID = os.environ.get("SPINPK_DEVICE_ID", "f607b24295e557fe")
TOKENS_ENV = os.environ.get("SPINPK_TOKENS", "")

DEFAULT_TOKENS = [
    "1f5587940e9546229e1c1426cea08f9a88e89a48db6f018d04420a5e0e6e04db",
    "e769d7bbd9248e64e43f3331f5d49306b4d998d75919d90871ba76746a244409",
    "5b83c211940a0df1b36a78ba341b8f0b596847c40331f28e12378677296e31fa",
    "10768a197a98f8137172d7fcb8de19b4022bb3b70abe554ed36ccc96eb6ed550",
    "64d7a52e79dc3c8512e7dac79dbbd8d6f9db7ce91a8ea7c593ad8437d76971c8",
]

TOKENS = [t.strip() for t in TOKENS_ENV.split(",") if t.strip()] or DEFAULT_TOKENS

BASE_URL = "https://spinpk.net/api"
AUTH_URL = f"{BASE_URL}/auth.php"
HEARTBEAT_URL = f"{BASE_URL}/me.php"
SPIN_URL = f"{BASE_URL}/spin.php"

# Cooldown: 4h 50m = 17400 sec
SPIN_INTERVAL_SEC = 17400
# GitHub Action cron runs every 5h; we only do ONE spin per token per run
# because next spin needs 4h50m cooldown.

# ==================== HEADERS ====================
def get_headers(token):
    return {
        'sec-ch-ua-platform': '"Android"',
        'authorization': f'Bearer {token}',
        'x-device-id': DEVICE_ID,
        'user-agent': 'Mozilla/5.0 (Linux; Android 11; Infinix X659B Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/152.0.7977.42 Mobile Safari/537.36',
        'sec-ch-ua': '"Chromium";v="152", "Not?A_Brand";v="24", "Android WebView";v="152"',
        'content-type': 'application/json',
        'sec-ch-ua-mobile': '?1',
        'accept': '*/*',
        'origin': 'null',
        'x-requested-with': 'com.spinpk.app',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'accept-encoding': 'gzip, deflate, zstd',
        'accept-language': 'en-US,en;q=0.9',
        'priority': 'u=1, i'
    }

# ==================== PRINT ====================
def p_success(m): print(f" ✅ {m}", flush=True)
def p_error(m): print(f" ❌ {m}", flush=True)
def p_info(m): print(f" ℹ️  {m}", flush=True)
def p_warning(m): print(f" ⚠️  {m}", flush=True)

def short(t): return f"{t[:8]}...{t[-6:]}"

# ==================== API ====================
def check_token(token):
    try:
        r = requests.post(AUTH_URL, headers=get_headers(token), json={"action": "me"}, timeout=15)
        if r.status_code == 200:
            return r.json().get('ok', False)
        return False
    except Exception as e:
        p_error(f"check_token: {e}")
        return False

def auth_me(token):
    try:
        r = requests.post(AUTH_URL, headers=get_headers(token), json={"action": "me"}, timeout=30)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def heartbeat(token):
    try:
        r = requests.post(HEARTBEAT_URL, headers=get_headers(token), json={"action": "heartbeat"}, timeout=30)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def spin(token):
    try:
        r = requests.post(SPIN_URL, headers=get_headers(token), json={"action": "play"}, timeout=30)
        return r.json() if r.status_code == 200 else None
    except:
        return None

# ==================== HELPERS ====================
def show_user(result, token):
    if not result or 'user' not in result:
        p_warning(f"No user data for {short(token)}")
        return
    u = result['user']
    print(f"   📛 {u.get('name','N/A')} | 📞 {u.get('phone','N/A')}", flush=True)
    print(f"   🪙 Balance: {u.get('balance','N/A')} PKR | 🎰 Spins: {u.get('spin_count','N/A')}", flush=True)

def save_json(name, data):
    try:
        with open(name, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass

def next_spin_time():
    return (datetime.utcnow() + timedelta(seconds=SPIN_INTERVAL_SEC)).strftime('%Y-%m-%d %H:%M:%S UTC')

# ==================== PER-TOKEN ====================
def run_token(token, index, total):
    print("\n" + "=" * 60, flush=True)
    print(f" 🎯 TOKEN {index}/{total}: {short(token)}", flush=True)
    print("=" * 60, flush=True)

    result = {"token": short(token), "auth": False, "spin": False, "balance": "N/A", "next_spin": None}

    if not check_token(token):
        p_error(f"Token invalid/expired: {short(token)}")
        return result

    p_success("Token valid")
    result["auth"] = True

    auth = auth_me(token)
    if auth:
        save_json(f"auth_{index}.json", auth)
        show_user(auth, token)

    heartbeat(token)

    # Single spin only (GitHub Actions runs every 5h)
    res = spin(token)
    if res:
        result["spin"] = True
        data = res.get('data', {})
        coins = data.get('coins', '?')
        prize = data.get('prize', '?')
        msg = data.get('message', '')
        print(f"   🎰 Spin OK: coins={coins} prize={prize} msg={msg}", flush=True)

        # Compute next spin time
        result["next_spin"] = next_spin_time()
        print(f"   ⏭️  Next spin available at: {result['next_spin']}", flush=True)
        print(f"   ⏳ Cooldown: 4h 50m ({SPIN_INTERVAL_SEC} sec)", flush=True)
    else:
        p_warning("Spin failed or on cooldown")

    final = auth_me(token)
    if final and 'user' in final:
        result["balance"] = final['user'].get('balance', 'N/A')
        save_json(f"final_{index}.json", final)

    p_success(f"Done {short(token)} | Balance: {result['balance']} PKR")
    return result

# ==================== MAIN ====================
def main():
    start = datetime.utcnow()
    print("\n" + "=" * 60, flush=True)
    print(" 🎰 SPINPK AUTO BOT - GitHub Actions", flush=True)
    print("=" * 60, flush=True)
    print(f" 📱 Tokens: {len(TOKENS)}", flush=True)
    print(f" 📱 Device ID: {DEVICE_ID}", flush=True)
    print(f" ⏱️  Cooldown: 4h 50m ({SPIN_INTERVAL_SEC} sec)", flush=True)
    print(f" 🚀 Started: {start.strftime('%Y-%m-%d %H:%M:%S UTC')}", flush=True)
    print("=" * 60, flush=True)

    results = []
    for i, tok in enumerate(TOKENS, 1):
        try:
            results.append(run_token(tok, i, len(TOKENS)))
        except Exception as e:
            p_error(f"Exception token {i}: {e}")
            results.append({"token": short(tok), "auth": False, "spin": False, "balance": "N/A", "next_spin": None})

    print("\n" + "=" * 60, flush=True)
    print(" 📊 FINAL SUMMARY", flush=True)
    print("=" * 60, flush=True)
    ok_spins = 0
    for r in results:
        s = "✅" if r["spin"] else ("⚠️" if r["auth"] else "❌")
        print(f" {s} {r['token']} | Balance: {r['balance']} PKR | Next: {r['next_spin']}", flush=True)
        if r["spin"]: ok_spins += 1
    dur = (datetime.utcnow() - start).total_seconds()
    print("-" * 60, flush=True)
    print(f" 🎰 Successful spins: {ok_spins}/{len(results)}", flush=True)
    print(f" ⏱️  Duration: {dur:.2f}s", flush=True)
    print(f" ⏭️  Next run in ~5h (cron '0 */5 * * *')", flush=True)
    print("=" * 60, flush=True)
    p_success("ALL DONE")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n ⚠️  Stopped by user", flush=True)
    except Exception as e:
        print(f"\n ❌ Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
