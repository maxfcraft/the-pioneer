"""
Automated morning report scheduler.

Sends a summary of yesterday's bot activity to Telegram every day at 7:00 AM.
Timezone is configurable via MORNING_REPORT_TIMEZONE env var (default: US/Eastern).
"""

import threading
import time
from datetime import datetime, timezone, timedelta

import config
from activity_tracker import ActivityTracker
from telegram_bot import send_morning_report


# Default to Eastern time (Auburn University timezone)
REPORT_HOUR = config.MORNING_REPORT_HOUR
REPORT_MINUTE = config.MORNING_REPORT_MINUTE

# UTC offset for US/Eastern (simplified: -5 standard, -4 DST)
UTC_OFFSET_HOURS = config.MORNING_REPORT_UTC_OFFSET


def _next_report_time() -> datetime:
    """Calculate the next 7:00 AM report time in UTC."""
    now_utc = datetime.now(timezone.utc)
    # Convert report hour to UTC
    report_utc_hour = REPORT_HOUR - UTC_OFFSET_HOURS  # 7 AM ET = 11 AM UTC (EDT)

    target = now_utc.replace(
        hour=report_utc_hour % 24,
        minute=REPORT_MINUTE,
        second=0,
        microsecond=0,
    )

    # If we already passed today's report time, schedule for tomorrow
    if target <= now_utc:
        target += timedelta(days=1)

    return target


def _report_loop(tracker: ActivityTracker):
    """Background loop that sends the morning report at the scheduled time."""
    print(f"[MORNING REPORT] Scheduler started — reports at {REPORT_HOUR}:00 AM "
          f"(UTC{UTC_OFFSET_HOURS:+d})")

    while True:
        next_time = _next_report_time()
        wait_seconds = (next_time - datetime.now(timezone.utc)).total_seconds()

        print(f"[MORNING REPORT] Next report at {next_time.strftime('%Y-%m-%d %H:%M UTC')} "
              f"({wait_seconds/3600:.1f} hours from now)")

        # Sleep until report time (wake every 60s to check, handles clock drift)
        while True:
            remaining = (next_time - datetime.now(timezone.utc)).total_seconds()
            if remaining <= 0:
                break
            time.sleep(min(remaining, 60))

        # Generate and send
        try:
            report = tracker.format_morning_report()
            success = send_morning_report(report)
            if success:
                print(f"[MORNING REPORT] Sent successfully")
            else:
                print(f"[MORNING REPORT] Failed to send")
        except Exception as e:
            print(f"[MORNING REPORT ERROR] {e}")

        # Wait 61 seconds to avoid double-sending
        time.sleep(61)


def start_morning_report_scheduler(tracker: ActivityTracker):
    """Start the background thread for automated morning reports."""
    thread = threading.Thread(target=_report_loop, args=(tracker,), daemon=True)
    thread.start()
    return thread
