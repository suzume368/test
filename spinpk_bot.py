#!/usr/bin/env python3
"""
SpinPK Auto Bot - GitHub Actions Edition
Uses server's wait_sec to compute exact next spin time
"""

import requests
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

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

DEFAULT_COOLDOWN = 17400  # 4h 50m fallback

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

def utc_now():
    return datetime.now(timezone.utc)

def fmt_utc(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S UTC')

def fmt_pkt(dt):
    pkt = dt.astimezone(timezone(timedelta(hours=5)))
    return pkt.strftime('%Y-%m-%d %H:%M:%S PKT')

def next_spin_str(wait_sec):
    dt = utc_now() + timedelta(seconds=wait_sec)
    return fmt_utc(dt), fmt_pkt(dt)

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
            if not data.get('ok'):
                wait = data.get('wait_sec', 0)
                print(f"   ⏳ Not ready. Wait: {wait}s ({wait//60}m {wait%60}s)", flush=True)
                return None
            return data
        return None
    except Exception as e:
        print(f"   ❌ spin exception: {e}", flush=True)
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
        "balance": "N/A", "next_spin_utc": "-", "next_spin_pkt": "-",
        "won": 0, "big": False
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
        amount = res.get('amount', 0)
        big = res.get('big', False)
        new_balance = res.get('balance', 'N/A')
        wait_sec = res.get('wait_sec', DEFAULT_COOLDOWN)

        result["won"] = amount
        result["balance"] = new_balance
        result["big"] = big

        big_str = " 🎉 BIG WIN!" if big else ""
        print(f"   🎰 Won: {amount} PKR{big_str}", flush=True)
        print(f"   💰 Balance: {bal_before} → {new_balance} PKR", flush=True)

        nxt_utc, nxt_pkt = next_spin_str(wait_sec)
        result["next_spin_utc"] = nxt_utc
        result["next_spin_pkt"] = nxt_pkt
        print(f"   ⏭️  Next spin (UTC): {nxt_utc}", flush=True)
        print(f"   ⏭️  Next spin (PKT): {nxt_pkt}", flush=True)
        print(f"   ⏳ Cooldown: {wait_sec}s ({wait_sec//3600}h {(wait_sec%3600)//60}m)", flush=True)

        history = res.get('history', [])[:3]
        if history:
            print(f"   📜 Recent history:", flush=True)
            for h in history:
                ts = datetime.fromtimestamp(h.get('ts', 0), tz=timezone.utc)
                print(f"      {fmt_pkt(ts)} | +{h.get('amount',0)} PKR | {h.get('note','')}", flush=True)

        save_json(f"spin_{index}.json", res)
    else:
        result["next_spin_utc"] = "cooldown"
        result["next_spin_pkt"] = "cooldown"
        p_warning("Spin not ready or failed")

    p_success(f"Done {short(token)} | Balance: {result['balance']} PKR | Won: {result['won']}")
    return result

# ==================== MAIN ====================
def main():
    start = utc_now()
    print("\n" + "=" * 60, flush=True)
    print(" 🎰 SPINPK AUTO BOT - GitHub Actions", flush=True)
    print("=" * 60, flush=True)
    print(f" 📱 Tokens: {len(TOKENS)}", flush=True)
    print(f" 📱 Device ID: {DEVICE_ID}", flush=True)
    print(f" 🚀 Started (UTC): {fmt_utc(start)}", flush=True)
    print(f" 🚀 Started (PKT): {fmt_pkt(start)}", flush=True)
    print("=" * 60, flush=True)

    results = []
    for i, tok in enumerate(TOKENS, 1):
        try:
            results.append(run_token(tok, i, len(TOKENS)))
        except Exception as e:
            p_error(f"Exception token {i}: {e}")
            results.append({"token": short(tok), "auth": False, "spin": False,
                            "balance": "N/A", "next_spin_utc": "-", "next_spin_pkt": "-",
                            "won": 0, "big": False})

    print("\n" + "=" * 60, flush=True)
    print(" 📊 FINAL SUMMARY", flush=True)
    print("=" * 60, flush=True)
    ok_spins = 0
    total_won = 0
    for r in results:
        s = "✅" if r["spin"] else ("⏳" if r["auth"] else "❌")
        print(f" {s} {r['token']} | Bal: {r['balance']} PKR | Won: {r.get('won',0)}", flush=True)
        print(f"     ⏭️  Next (UTC): {r['next_spin_utc']}", flush=True)
        print(f"     ⏭️  Next (PKT): {r['next_spin_pkt']}", flush=True)
        if r["spin"]: ok_spins += 1
        total_won += r.get("won", 0)
    dur = (utc_now() - start).total_seconds()
    print("-" * 60, flush=True)
    print(f" 🎰 Successful spins: {ok_spins}/{len(results)}", flush=True)
    print(f" 💰 Total won this run: {total_won} PKR", flush=True)
    print(f" ⏱️  Duration: {dur:.2f}s", flush=True)
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
