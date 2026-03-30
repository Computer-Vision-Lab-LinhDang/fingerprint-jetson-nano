#!/usr/bin/env python3
"""
Interactive CLI for Fingerprint Jetson Nano Worker.
Works entirely over SSH — no GUI or PyQt5 required.
Requires the Backend (uvicorn) to be running on localhost:8000.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error


# ── ANSI Colors ──────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"


BASE_URL = "http://localhost:8000/api/v1"


# ── Helpers ──────────────────────────────────────────────────
def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")


def api_request(method, endpoint, data=None, timeout=15):
    url = "{}{}".format(BASE_URL, endpoint)
    headers = {"Content-Type": "application/json"}

    req_data = None
    if data:
        req_data = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body)
    except urllib.error.HTTPError as e:
        res_body = e.read().decode("utf-8")
        try:
            return json.loads(res_body)
        except Exception:
            return {"success": False, "error": "HTTP {}: {}".format(e.code, res_body[:200])}
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_backend():
    """Quick check if backend is alive."""
    res = api_request("GET", "/system/health")
    return res.get("success", False)


# ── Banner ───────────────────────────────────────────────────
def print_banner():
    print("""
{cyan}{bold}╔══════════════════════════════════════════════════╗
║      🔐  FINGERPRINT WORKER — CLI                ║
╚══════════════════════════════════════════════════╝{reset}
""".format(cyan=C.CYAN, bold=C.BOLD, reset=C.RESET))


# ── Menu ─────────────────────────────────────────────────────
def print_menu():
    # Check backend connection
    res = api_request("GET", "/system/health")
    if res.get("success"):
        status = "{green}● CONNECTED{reset}".format(green=C.GREEN, reset=C.RESET)
        data = res.get("data", {})
        users = data.get("total_users", "?")
        sensor = data.get("sensor_connected", False)
        sensor_str = "{green}● Online{reset}".format(green=C.GREEN, reset=C.RESET) if sensor else "{red}● Offline{reset}".format(red=C.RED, reset=C.RESET)
    else:
        status = "{red}● DISCONNECTED{reset}".format(red=C.RED, reset=C.RESET)
        users = "?"
        sensor_str = "{dim}?{reset}".format(dim=C.DIM, reset=C.RESET)

    print("  {dim}Backend{reset}  │  {status}  │  {dim}Users:{reset} {bold}{users}{reset}  │  {dim}Sensor:{reset} {sensor}".format(
        dim=C.DIM, reset=C.RESET, status=status, bold=C.BOLD, users=users, sensor=sensor_str))
    print("  {dim}Endpoint:{reset} {url}".format(dim=C.DIM, reset=C.RESET, url=BASE_URL))
    print()
    print("  {yellow}{line}{reset}".format(yellow=C.YELLOW, line="─" * 48, reset=C.RESET))
    print("  {bold}[1]{reset}  🖥️   System Status".format(bold=C.BOLD, reset=C.RESET))
    print("  {bold}[2]{reset}  👥  List Users".format(bold=C.BOLD, reset=C.RESET))
    print("  {bold}[3]{reset}  📝  Register New User".format(bold=C.BOLD, reset=C.RESET))
    print("  {bold}[4]{reset}  ✋  Enroll Fingerprint".format(bold=C.BOLD, reset=C.RESET))
    print("  {bold}[5]{reset}  🔍  Verify 1:1".format(bold=C.BOLD, reset=C.RESET))
    print("  {bold}[6]{reset}  🔎  Identify 1:N".format(bold=C.BOLD, reset=C.RESET))
    print("  {bold}[7]{reset}  🧠  Model Info".format(bold=C.BOLD, reset=C.RESET))
    print("  {bold}[8]{reset}  🧹  Clear Screen".format(bold=C.BOLD, reset=C.RESET))
    print("  {bold}[0]{reset}  🚪  Exit".format(bold=C.BOLD, reset=C.RESET))
    print("  {yellow}{line}{reset}".format(yellow=C.YELLOW, line="─" * 48, reset=C.RESET))


# ── [1] System Status ───────────────────────────────────────
def cmd_status():
    print("\n  {cyan}{bold}═══ SYSTEM STATUS ═══{reset}\n".format(cyan=C.CYAN, bold=C.BOLD, reset=C.RESET))

    health = api_request("GET", "/system/health")
    if not health.get("success"):
        print("  {red}✗ Backend unreachable: {err}{reset}".format(red=C.RED, err=health.get("error", ""), reset=C.RESET))
        return

    d = health["data"]
    print("  {dim}{'─' * 40}{reset}".format(dim=C.DIM, reset=C.RESET))

    for label, key, color in [
        ("Device ID",    "device_id",           C.WHITE),
        ("Version",      "version",             C.WHITE),
        ("Uptime",       "uptime_seconds",      C.GREEN),
        ("MQTT",         "mqtt_connected",       C.GREEN),
        ("Sensor",       "sensor_connected",    C.GREEN),
        ("Total Users",  "total_users",         C.MAGENTA),
        ("Total Prints", "total_fingerprints",  C.MAGENTA),
        ("Active Model", "active_model",        C.CYAN),
    ]:
        val = d.get(key, "—")
        if isinstance(val, bool):
            if val:
                val_str = "{green}● Yes{reset}".format(green=C.GREEN, reset=C.RESET)
            else:
                val_str = "{red}● No{reset}".format(red=C.RED, reset=C.RESET)
        elif key == "uptime_seconds" and isinstance(val, (int, float)):
            mins = int(val) // 60
            secs = int(val) % 60
            val_str = "{}m {}s".format(mins, secs)
        else:
            val_str = str(val) if val else "{dim}(none){reset}".format(dim=C.DIM, reset=C.RESET)

        print("  {label:<17} {val}".format(label=label, val=val_str))

    # Config section
    cfg = api_request("GET", "/system/config")
    if cfg.get("success"):
        cd = cfg["data"]
        print()
        print("  {bold}▸ Configuration{reset}".format(bold=C.BOLD, reset=C.RESET))
        print("  {dim}{'─' * 40}{reset}".format(dim=C.DIM, reset=C.RESET))
        for label, key in [("Backend", "backend"), ("Model Path", "model_path"), ("Threshold", "verify_threshold")]:
            print("  {label:<17} {val}".format(label=label, val=cd.get(key, "—")))

    # Stats section
    stats = api_request("GET", "/system/stats")
    if stats.get("success"):
        sd = stats["data"]
        print()
        print("  {bold}▸ Statistics{reset}".format(bold=C.BOLD, reset=C.RESET))
        print("  {dim}{'─' * 40}{reset}".format(dim=C.DIM, reset=C.RESET))
        for label, key in [
            ("Verifications", "total_verifications"),
            ("Avg Latency",   "avg_latency_ms"),
            ("Success Rate",  "success_rate"),
        ]:
            val = sd.get(key, "—")
            if key == "avg_latency_ms" and isinstance(val, (int, float)):
                val = "{:.1f} ms".format(val)
            elif key == "success_rate" and isinstance(val, (int, float)):
                val = "{:.1f}%".format(val * 100)
            print("  {label:<17} {val}".format(label=label, val=val))
    print()


# ── [2] List Users ──────────────────────────────────────────
def cmd_list_users():
    print("\n  {cyan}{bold}═══ USER LIST ═══{reset}\n".format(cyan=C.CYAN, bold=C.BOLD, reset=C.RESET))

    res = api_request("GET", "/users?limit=50")
    if not res.get("success"):
        print("  {red}✗ Error: {err}{reset}".format(red=C.RED, err=res.get("error", ""), reset=C.RESET))
        return

    users = res.get("data", {}).get("users", [])
    pagination = res.get("data", {}).get("pagination", {})

    if not users:
        print("  {dim}No users found in the database.{reset}".format(dim=C.DIM, reset=C.RESET))
        return

    print("  {dim}{hdr}{reset}".format(
        dim=C.DIM, reset=C.RESET,
        hdr="{:<8} {:<20} {:<12} {:<10} {}".format("#", "Name", "Emp ID", "Status", "Fingers")))
    print("  {dim}{line}{reset}".format(dim=C.DIM, line="─" * 65, reset=C.RESET))

    for i, u in enumerate(users, 1):
        fingers = len(u.get("enrolled_fingers", []))
        is_active = u.get("is_active", True)
        status_str = "{green}active{reset}".format(green=C.GREEN, reset=C.RESET) if is_active else "{red}inactive{reset}".format(red=C.RED, reset=C.RESET)
        finger_str = "{mag}{n} enrolled{reset}".format(mag=C.MAGENTA, n=fingers, reset=C.RESET) if fingers > 0 else "{dim}(none){reset}".format(dim=C.DIM, reset=C.RESET)
        print("  {bold}[{i}]{reset}  {name:<20} {eid:<12} {status:<22} {fingers}".format(
            bold=C.BOLD, reset=C.RESET, i=i,
            name=u.get("full_name", "")[:18],
            eid=u.get("employee_id", "")[:10],
            status=status_str,
            fingers=finger_str))

    total = pagination.get("total", len(users))
    print("\n  {dim}Showing {n}/{total} users{reset}".format(dim=C.DIM, n=len(users), total=total, reset=C.RESET))
    print()


# ── [3] Register User ──────────────────────────────────────
def cmd_register():
    print("\n  {cyan}{bold}═══ REGISTER NEW USER ═══{reset}\n".format(cyan=C.CYAN, bold=C.BOLD, reset=C.RESET))

    emp_id = input("  {yellow}▸ Employee ID:{reset} ".format(yellow=C.YELLOW, reset=C.RESET)).strip()
    name = input("  {yellow}▸ Full Name:{reset} ".format(yellow=C.YELLOW, reset=C.RESET)).strip()
    dept = input("  {yellow}▸ Department (optional):{reset} ".format(yellow=C.YELLOW, reset=C.RESET)).strip()

    if not emp_id or not name:
        print("  {red}✗ Employee ID and Name are required.{reset}".format(red=C.RED, reset=C.RESET))
        return

    payload = {"employee_id": emp_id, "full_name": name}
    if dept:
        payload["department"] = dept

    print("\n  {dim}Creating user...{reset}".format(dim=C.DIM, reset=C.RESET))
    res = api_request("POST", "/users", payload)

    if not res.get("success"):
        detail = res.get("detail", res.get("error", str(res)))
        print("  {red}✗ Failed: {d}{reset}".format(red=C.RED, d=detail, reset=C.RESET))
        return

    user = res["data"]
    print("  {green}✓ User created successfully!{reset}".format(green=C.GREEN, reset=C.RESET))
    print("    User ID  : {bold}{uid}{reset}".format(bold=C.BOLD, uid=user["id"], reset=C.RESET))
    print("    Name     : {}".format(user.get("full_name")))
    print("    Emp ID   : {}".format(user.get("employee_id")))
    print()


# ── [4] Enroll Fingerprint ──────────────────────────────────
def cmd_enroll():
    print("\n  {cyan}{bold}═══ ENROLL FINGERPRINT ═══{reset}\n".format(cyan=C.CYAN, bold=C.BOLD, reset=C.RESET))

    # List users first
    res = api_request("GET", "/users?limit=50")
    users = res.get("data", {}).get("users", []) if res.get("success") else []

    if users:
        print("  {bold}▸ Available Users:{reset}".format(bold=C.BOLD, reset=C.RESET))
        for i, u in enumerate(users, 1):
            fingers = len(u.get("enrolled_fingers", []))
            print("    {bold}[{i}]{reset} {name} ({eid}) — {n} finger(s)".format(
                bold=C.BOLD, reset=C.RESET, i=i,
                name=u.get("full_name", ""), eid=u.get("employee_id", ""), n=fingers))
        print()

        try:
            idx = int(input("  {yellow}▸ Select user [1-{n}]: {reset}".format(
                yellow=C.YELLOW, n=len(users), reset=C.RESET)).strip()) - 1
            if idx < 0 or idx >= len(users):
                print("  {red}✗ Invalid selection{reset}".format(red=C.RED, reset=C.RESET))
                return
            user_id = users[idx]["id"]
        except (ValueError, EOFError):
            print("  {red}✗ Invalid input{reset}".format(red=C.RED, reset=C.RESET))
            return
    else:
        user_id = input("  {yellow}▸ Enter User ID: {reset}".format(yellow=C.YELLOW, reset=C.RESET)).strip()

    if not user_id:
        return

    fingers = ["right_index", "right_middle", "right_thumb", "left_index", "left_middle", "left_thumb"]
    print()
    print("  {bold}▸ Select Finger:{reset}".format(bold=C.BOLD, reset=C.RESET))
    for i, f in enumerate(fingers, 1):
        print("    {bold}[{i}]{reset} {f}".format(bold=C.BOLD, reset=C.RESET, i=i, f=f))

    try:
        f_idx = int(input("  {yellow}▸ Finger [1-{n}]: {reset}".format(
            yellow=C.YELLOW, n=len(fingers), reset=C.RESET)).strip()) - 1
        if f_idx < 0 or f_idx >= len(fingers):
            f_idx = 0
    except (ValueError, EOFError):
        f_idx = 0

    finger = fingers[f_idx]

    print()
    print("  {yellow}⏳ Place your finger on the sensor...{reset}".format(yellow=C.YELLOW, reset=C.RESET))
    print("  {dim}   (3 samples will be captured){reset}".format(dim=C.DIM, reset=C.RESET))
    print()

    res = api_request("POST", "/users/{}/enroll-finger".format(user_id), {
        "finger": finger,
        "num_samples": 3,
    }, timeout=30)

    if res.get("success"):
        d = res["data"]
        print("  {green}✓ Enrollment successful!{reset}".format(green=C.GREEN, reset=C.RESET))
        print("    Finger   : {}".format(d.get("finger", finger)))
        print("    Quality  : {:.1f}".format(d.get("quality_score", 0)))
        print("    Templates: {}".format(d.get("template_count", "?")))
    else:
        detail = res.get("detail", res.get("error", str(res)))
        print("  {red}✗ Enrollment failed: {d}{reset}".format(red=C.RED, d=detail, reset=C.RESET))
    print()


# ── [5] Verify 1:1 ──────────────────────────────────────────
def cmd_verify():
    print("\n  {cyan}{bold}═══ 1:1 VERIFICATION ═══{reset}\n".format(cyan=C.CYAN, bold=C.BOLD, reset=C.RESET))

    # List users
    res = api_request("GET", "/users?limit=50")
    users = res.get("data", {}).get("users", []) if res.get("success") else []
    enrolled = [u for u in users if len(u.get("enrolled_fingers", [])) > 0]

    if enrolled:
        print("  {bold}▸ Users with enrolled fingerprints:{reset}".format(bold=C.BOLD, reset=C.RESET))
        for i, u in enumerate(enrolled, 1):
            fingers = ", ".join([f.get("finger", "?") for f in u.get("enrolled_fingers", [])])
            print("    {bold}[{i}]{reset} {name} ({eid}) — {fingers}".format(
                bold=C.BOLD, reset=C.RESET, i=i,
                name=u.get("full_name", ""), eid=u.get("employee_id", ""),
                fingers=fingers))
        print()

        try:
            idx = int(input("  {yellow}▸ Select user [1-{n}]: {reset}".format(
                yellow=C.YELLOW, n=len(enrolled), reset=C.RESET)).strip()) - 1
            if idx < 0 or idx >= len(enrolled):
                print("  {red}✗ Invalid selection{reset}".format(red=C.RED, reset=C.RESET))
                return
            user_id = enrolled[idx]["id"]
        except (ValueError, EOFError):
            print("  {red}✗ Invalid input{reset}".format(red=C.RED, reset=C.RESET))
            return
    else:
        user_id = input("  {yellow}▸ Enter User ID: {reset}".format(yellow=C.YELLOW, reset=C.RESET)).strip()

    if not user_id:
        return

    print()
    print("  {yellow}⏳ Place your finger on the sensor...{reset}".format(yellow=C.YELLOW, reset=C.RESET))

    res = api_request("POST", "/verify", {"user_id": user_id}, timeout=20)

    if not res.get("success"):
        detail = res.get("detail", res.get("error", str(res)))
        print("  {red}✗ Error: {d}{reset}".format(red=C.RED, d=detail, reset=C.RESET))
        return

    d = res["data"]
    score = d.get("score", 0)
    threshold = d.get("threshold", 0)

    print()
    if d.get("matched"):
        print("  {green}{bold}┌─────────────────────────────────┐{reset}".format(green=C.GREEN, bold=C.BOLD, reset=C.RESET))
        print("  {green}{bold}│     ✅  MATCH — VERIFIED        │{reset}".format(green=C.GREEN, bold=C.BOLD, reset=C.RESET))
        print("  {green}{bold}└─────────────────────────────────┘{reset}".format(green=C.GREEN, bold=C.BOLD, reset=C.RESET))
    else:
        print("  {red}{bold}┌─────────────────────────────────┐{reset}".format(red=C.RED, bold=C.BOLD, reset=C.RESET))
        print("  {red}{bold}│     ❌  REJECTED — NO MATCH     │{reset}".format(red=C.RED, bold=C.BOLD, reset=C.RESET))
        print("  {red}{bold}└─────────────────────────────────┘{reset}".format(red=C.RED, bold=C.BOLD, reset=C.RESET))

    print("    Score     : {bold}{score:.4f}{reset}".format(bold=C.BOLD, score=score, reset=C.RESET))
    print("    Threshold : {:.2f}".format(threshold))
    print("    Latency   : {:.0f} ms".format(d.get("latency_ms", 0)))
    print()


# ── [6] Identify 1:N ────────────────────────────────────────
def cmd_identify():
    print("\n  {cyan}{bold}═══ 1:N IDENTIFICATION ═══{reset}\n".format(cyan=C.CYAN, bold=C.BOLD, reset=C.RESET))

    print("  {yellow}⏳ Place your finger on the sensor...{reset}".format(yellow=C.YELLOW, reset=C.RESET))

    res = api_request("POST", "/identify", {"top_k": 5}, timeout=20)

    if not res.get("success"):
        detail = res.get("detail", res.get("error", str(res)))
        print("  {red}✗ Error: {d}{reset}".format(red=C.RED, d=detail, reset=C.RESET))
        return

    d = res["data"]
    candidates = d.get("candidates", [])

    print()
    if d.get("matched") and candidates:
        best = candidates[0]
        print("  {green}{bold}┌─────────────────────────────────┐{reset}".format(green=C.GREEN, bold=C.BOLD, reset=C.RESET))
        print("  {green}{bold}│     ✅  IDENTIFIED              │{reset}".format(green=C.GREEN, bold=C.BOLD, reset=C.RESET))
        print("  {green}{bold}└─────────────────────────────────┘{reset}".format(green=C.GREEN, bold=C.BOLD, reset=C.RESET))
        print("    User ID   : {bold}{uid}{reset}".format(bold=C.BOLD, uid=best.get("user_id", "?"), reset=C.RESET))
        print("    Score     : {bold}{score:.4f}{reset}".format(bold=C.BOLD, score=best.get("score", 0), reset=C.RESET))

        if len(candidates) > 1:
            print()
            print("  {dim}Other candidates:{reset}".format(dim=C.DIM, reset=C.RESET))
            for c in candidates[1:]:
                print("    {dim}• {uid}  (score: {score:.4f}){reset}".format(
                    dim=C.DIM, uid=c.get("user_id", "?"), score=c.get("score", 0), reset=C.RESET))
    else:
        print("  {red}{bold}┌─────────────────────────────────┐{reset}".format(red=C.RED, bold=C.BOLD, reset=C.RESET))
        print("  {red}{bold}│     ❌  NO MATCH FOUND          │{reset}".format(red=C.RED, bold=C.BOLD, reset=C.RESET))
        print("  {red}{bold}└─────────────────────────────────┘{reset}".format(red=C.RED, bold=C.BOLD, reset=C.RESET))

    print("    Latency   : {:.0f} ms".format(d.get("latency_ms", 0)))
    print()


# ── [7] Model Info ──────────────────────────────────────────
def cmd_models():
    print("\n  {cyan}{bold}═══ MODEL INFO ═══{reset}\n".format(cyan=C.CYAN, bold=C.BOLD, reset=C.RESET))

    res = api_request("GET", "/models")
    if not res.get("success"):
        print("  {red}✗ Error: {err}{reset}".format(red=C.RED, err=res.get("error", ""), reset=C.RESET))
        return

    data = res.get("data", {})
    models = data.get("models", [])
    active = data.get("active_model")

    if not models:
        print("  {dim}No models found in the models directory.{reset}".format(dim=C.DIM, reset=C.RESET))
        print("  {dim}Models will be downloaded from orchestrator via MQTT.{reset}".format(dim=C.DIM, reset=C.RESET))
        return

    print("  {dim}{hdr}{reset}".format(dim=C.DIM, reset=C.RESET,
        hdr="{:<30} {:<10} {}".format("Name", "Size", "Status")))
    print("  {dim}{line}{reset}".format(dim=C.DIM, line="─" * 55, reset=C.RESET))

    for m in models:
        name = m.get("name", "?")
        size = m.get("size_mb", 0)
        is_active = (name == active)

        if is_active:
            status = "{green}● ACTIVE{reset}".format(green=C.GREEN, reset=C.RESET)
        else:
            status = "{dim}idle{reset}".format(dim=C.DIM, reset=C.RESET)

        print("  {name:<30} {size:<10} {status}".format(
            name=name, size="{:.1f} MB".format(size), status=status))

    print()


# ── Main CLI Loop ───────────────────────────────────────────
def run_cli():
    clear_screen()
    print_banner()

    # Quick connectivity check
    if check_backend():
        print("  {green}✓ Backend is running!{reset}".format(green=C.GREEN, reset=C.RESET))
    else:
        print("  {red}✗ Cannot reach backend at {url}{reset}".format(red=C.RED, url=BASE_URL, reset=C.RESET))
        print("  {dim}Make sure uvicorn is running:{reset}".format(dim=C.DIM, reset=C.RESET))
        print("  {dim}  source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000{reset}".format(dim=C.DIM, reset=C.RESET))

    print()
    input("  {dim}Press Enter to open main menu...{reset}".format(dim=C.DIM, reset=C.RESET))

    clear_screen()
    print_banner()

    actions = {
        "1": cmd_status,
        "2": cmd_list_users,
        "3": cmd_register,
        "4": cmd_enroll,
        "5": cmd_verify,
        "6": cmd_identify,
        "7": cmd_models,
        "8": lambda: (clear_screen(), print_banner()),
    }

    while True:
        print_menu()
        try:
            choice = input("\n  {yellow}{bold}▸ Select [0-8]: {reset}".format(
                yellow=C.YELLOW, bold=C.BOLD, reset=C.RESET)).strip()
        except (KeyboardInterrupt, EOFError):
            choice = "0"

        if choice == "0":
            print("\n  {dim}Exiting...{reset}".format(dim=C.DIM, reset=C.RESET))
            break

        action = actions.get(choice)
        if action:
            action()
            input("\n  {dim}Press Enter to continue...{reset}".format(dim=C.DIM, reset=C.RESET))
            clear_screen()
            print_banner()
        else:
            print("  {red}Invalid choice!{reset}".format(red=C.RED, reset=C.RESET))

    print("  {green}👋 CLI stopped.{reset}\n".format(green=C.GREEN, reset=C.RESET))


if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        print("\n  Exiting...")
        sys.exit(0)
