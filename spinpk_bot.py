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
]

TOKENS = [t.strip() for t in TOKENS_ENV.split(",") if t.strip()] or DEFAULT_TOKENS

BASE_URL = "https://spinpk.net/api"
AUTH_URL = f"{BASE_URL}/auth.php"
HEARTBEAT_URL = f"{BASE_URL}/me.php"
SPIN_URL = f"{BASE_URL}/spin.php"

# Cooldown: 4h 50m = 17400 sec
SPIN_INTERVAL_SEC = 17400

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
        if r.status_code == 200:
            data = r.json()
            print(f"   🔍 RAW: {json.dumps(data)[:500]}", flush=True)
            return data
        return None
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

def get_balance(result):
    try:
        return float(result['user'].get('balance', 0))
    except:
        return 0.0

# ==================== PER-TOKEN ====================
def run_token(token, index, total):
    print("\n" + "=" * 60, flush=True)
    print(f" 🎯 TOKEN {index}/{total}: {short(token)}", flush=True)
    print("=" * 60, flush=True)

    result = {
        "token": short(token), "auth": False, "spin": False,
        "balance": "N/A", "next_spin": None, "won": 0
    }

    if not check_token(token):
        p_error(f"Token invalid/expired: {short(token)}")
        return result

    p_success("Token valid")
    result["auth"] = True

    auth = auth_me(token)
    if auth:
        save_json(f"auth_{index}.json", auth)
        show_user(auth, token)

    bal_before = get_balance(auth) if auth else 0.0

    heartbeat(token)

    res = spin(token)
    if res:
        result["spin"] = True

        # Try to extract reward fields from multiple possible keys
        data = res.get('data', res) if isinstance(res, dict) else {}
        coins = data.get('coins', data.get('reward', data.get('amount', data.get('points', '?'))))
        prize = data.get('prize', data.get('prize_name', data.get('reward_name', '?')))
        msg = data.get('message', data.get('msg', ''))
        print(f"   🎰 Spin OK: coins={coins} prize={prize} msg={msg}", flush=True)

        time.sleep(2)
        final = auth_me(token)
        bal_after = bal_before
        if final and 'user' in final:
            bal_after = get_balance(final)
            result["balance"] = final['user'].get('balance', 'N/A')
            save_json(f"final_{index}.json", final)

        won = round(bal_after - bal_before, 2)
        result["won"] = won
        print(f"   💰 Balance: {bal_before} → {bal_after} | Won: {won} PKR", flush=True)

        result["next_spin"] = next_spin_time()
        print(f"   ⏭️  Next spin available at: {result['next_spin']}", flush=True)
        print(f"   ⏳ Cooldown: 4h 50m ({SPIN_INTERVAL_SEC} sec)", flush=True)
    else:
        p_warning("Spin failed or on cooldown")

    p_success(f"Done {short(token)} | Balance: {result['balance']} PKR | Won: {result['won']}")
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
            results.append({"token": short(tok), "auth": False, "spin": False, "balance": "N/A", "next_spin": None, "won": 0})

    print("\n" + "=" * 60, flush=True)
    print(" 📊 FINAL SUMMARY", flush=True)
    print("=" * 60, flush=True)
    ok_spins = 0
    total_won = 0
    for r in results:
        s = "✅" if r["spin"] else ("⚠️" if r["auth"] else "❌")
        print(f" {s} {r['token']} | Bal: {r['balance']} PKR | Won: {r.get('won',0)} | Next: {r['next_spin']}", flush=True)
        if r["spin"]: ok_spins += 1
        total_won += r.get("won", 0)
    dur = (datetime.utcnow() - start).total_seconds()
    print("-" * 60, flush=True)
    print(f" 🎰 Successful spins: {ok_spins}/{len(results)}", flush=True)
    print(f" 💰 Total won this run: {round(total_won, 2)} PKR", flush=True)
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
