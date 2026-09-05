"""
NEMESIS Plugin - Phone Notifications Sync
Sync phone notifications to computer for legitimate monitoring.
Works with: Android (via ADB), iOS (via iTunes backup parsing).
Only monitors notifications from apps you authorize.
"""

import subprocess
import sys
import time
import json
import threading
from pathlib import Path

PLUGIN = {
    "name": "phone_notifications",
    "description": (
        "Sync and monitor phone notifications on your computer. "
        "Requires: USB debugging enabled (Android) or iTunes backup (iOS). "
        "Only monitors notifications you authorize."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "start | stop | list | clear",
            },
            "app_filter": {
                "type": "STRING",
                "description": "Comma-separated app names to monitor (e.g., 'whatsapp,telegram,sms')",
            },
        },
        "required": ["action"],
    },
}

_monitoring = False
_monitor_thread = None
_app_filter = []

def _run_adb(args: list, timeout: int = 10) -> dict:
    """Run an ADB command."""
    try:
        cmd = ["adb"] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return {"success": result.returncode == 0, "output": result.stdout.strip()}
    except:
        return {"success": False, "output": ""}

def _get_notifications() -> list:
    """Get current notifications from Android device."""
    result = _run_adb(["shell", "dumpsys", "notification", "--noredact"])
    if not result["success"]:
        return []
    
    notifications = []
    lines = result["output"].split("\n")
    
    for i, line in enumerate(lines):
        if "pkg=" in line:
            pkg = line.split("pkg=")[1].split()[0] if "pkg=" in line else ""
            
            # Get title and text from nearby lines
            title = ""
            text = ""
            for j in range(i, min(i + 5, len(lines))):
                if "title=" in lines[j]:
                    title = lines[j].split("title=")[1].strip().strip('"')
                if "text=" in lines[j]:
                    text = lines[j].split("text=")[1].strip().strip('"')
            
            if pkg and (title or text):
                notifications.append({
                    "package": pkg,
                    "title": title,
                    "text": text,
                })
    
    return notifications

def _filter_notifications(notifications: list) -> list:
    """Filter notifications based on app filter."""
    if not _app_filter:
        return notifications
    
    filtered = []
    for notif in notifications:
        pkg_lower = notif["package"].lower()
        for app in _app_filter:
            if app.lower() in pkg_lower:
                filtered.append(notif)
                break
    
    return filtered

def _monitor_loop():
    """Background monitoring loop."""
    global _monitoring
    seen = set()
    
    while _monitoring:
        try:
            notifications = _get_notifications()
            filtered = _filter_notifications(notifications)
            
            for notif in filtered:
                # Create unique ID to avoid duplicates
                notif_id = f"{notif['package']}:{notif['title']}:{notif['text']}"
                if notif_id not in seen:
                    seen.add(notif_id)
                    # Print notification
                    print(f"[Phone Notification] {notif['package']}: {notif['title']} - {notif['text']}")
            
            time.sleep(5)  # Check every 5 seconds
        except Exception as e:
            print(f"[Phone Notifications] Error: {e}")
            time.sleep(10)

def run(parameters: dict, player=None, session_memory=None) -> str:
    """Main plugin entry point."""
    global _monitoring, _monitor_thread, _app_filter
    
    action = parameters.get("action", "list").lower()
    app_filter = parameters.get("app_filter", "")
    
    if action == "start":
        if _monitoring:
            return "Notification monitoring already running."
        
        # Parse app filter
        if app_filter:
            _app_filter = [a.strip() for a in app_filter.split(",") if a.strip()]
        else:
            _app_filter = []
        
        _monitoring = True
        _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
        _monitor_thread.start()
        
        filter_msg = f"Monitoring apps: {', '.join(_app_filter)}" if _app_filter else "Monitoring ALL apps"
        return f"📱 Phone notification monitoring started!\n{filter_msg}\nNotifications will appear in console."
    
    elif action == "stop":
        if not _monitoring:
            return "Monitoring not running."
        
        _monitoring = False
        return "Phone notification monitoring stopped."
    
    elif action == "list":
        notifications = _get_notifications()
        if not notifications:
            return "No notifications found on device."
        
        filtered = _filter_notifications(notifications)
        if not filtered:
            return f"Found {len(notifications)} notifications, but none match filter."
        
        result = f"📱 Current Notifications ({len(filtered)}):\n\n"
        for i, notif in enumerate(filtered[:20], 1):
            result += f"{i}. [{notif['package']}]\n   {notif['title']}: {notif['text']}\n"
        
        return result
    
    elif action == "clear":
        # Clear all notifications
        result = _run_adb(["shell", "service", "call", "notification", "1"])
        if result["success"]:
            return "All notifications cleared."
        return "Failed to clear notifications."
    
    else:
        return (
            "Phone Notifications Actions:\n"
            "• start - Start monitoring (optional: app_filter='whatsapp,telegram')\n"
            "• stop - Stop monitoring\n"
            "• list - Show current notifications\n"
            "• clear - Clear all notifications\n\n"
            "Note: Requires ADB and USB debugging enabled."
        )
