# /// script
# requires-python = ">=3.9"
# dependencies = ["playwright>=1.45"]
# ///
"""Fill missing TimeWatch (c.timewatch.co.il) attendance days.

Port of the TI-TimeWatch Chrome extension: log in, open the monthly
attendance report, and for every past day marked "missing entry/exit"
set a fixed start/end time (through the end of the month by default).

Credentials:
  company  : --company / TIMEWATCH_COMPANY      (default 4630)
  employee : --employee / TIMEWATCH_EMPLOYEE    (or config.json)
  password : TIMEWATCH_PASSWORD, else macOS Keychain (service "timewatch")
  If the employee number or password is missing (or --setup is passed), macOS
  dialogs ask for them and save them to config.json and the Keychain.
Optional config: ~/.config/timewatch_skill/config.json
  {"companyNum": "4630", "employeeNum": "123", "start": "09:00", "end": "18:00"}
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

TIMEWATCH_URL = "https://c.timewatch.co.il/punch/punch.php"
MISSING_TEXT = "חסרה כניסה/יציאה"
SUBMIT_DAILY_TEXT = "עדכן"
CONFIG_PATH = Path(os.environ.get("TIMEWATCH_CONFIG") or Path.home() / ".config" / "timewatch_skill" / "config.json")
KEYCHAIN_SERVICE = "timewatch"


def load_config(args):
    cfg = {}
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text())
    company = args.company or os.environ.get("TIMEWATCH_COMPANY") or cfg.get("companyNum") or "4630"
    employee = args.employee or os.environ.get("TIMEWATCH_EMPLOYEE") or cfg.get("employeeNum")
    if args.setup or not employee:
        company = ask_dialog("TimeWatch company number:", default=company)
        employee = ask_dialog("TimeWatch employee number (3 digits):", default=employee or "")
        cfg.update(companyNum=company, employeeNum=employee)
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
        print(f"saved company and employee number to {CONFIG_PATH}")
    password = os.environ.get("TIMEWATCH_PASSWORD")
    if not password and not args.setup:
        password = keychain_password(employee)
    if not password:
        password = ask_dialog(f"TimeWatch password for employee {employee}:", hidden=True)
        save_keychain_password(employee, password)
        print(f"saved password to Keychain (service '{KEYCHAIN_SERVICE}')")
    start = args.start or cfg.get("start") or "09:00"
    end = args.end or cfg.get("end") or "18:00"
    return company, employee, password, parse_time(start), parse_time(end)


def keychain_password(employee):
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", employee, "-w"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def ask_dialog(prompt, default="", hidden=False):
    # GUI prompt so first-run setup works even when no terminal is attached.
    script = """on run argv
        set r to display dialog (item 1 of argv) default answer (item 2 of argv) ¬
            with title "TimeWatch" HIDDEN
        return text returned of r
    end run""".replace("HIDDEN", "with hidden answer" if hidden else "")
    out = subprocess.run(["osascript", "-e", script, prompt, default], capture_output=True, text=True)
    value = out.stdout.strip()
    if out.returncode != 0 or not value:
        sys.exit("ERROR: setup cancelled - no value entered")
    return value


def save_keychain_password(employee, password):
    # Pass the command on stdin to `security -i` so the password doesn't show
    # up in the process list.
    cmd = f'add-generic-password -U -s {KEYCHAIN_SERVICE} -a "{employee}" -w "{password}"\n'
    subprocess.run(["security", "-i"], input=cmd, text=True, capture_output=True, check=True)


def forget_keychain_password(employee):
    subprocess.run(["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE, "-a", employee],
                   capture_output=True)


def parse_time(value):
    hh, mm = value.split(":")
    return f"{int(hh):02d}", f"{int(mm):02d}"


def set_field(page, selector, value):
    # The dialog fields may be <select> or <input>; set the value and fire
    # the events the page listens to, like jQuery .val() did in the extension.
    page.eval_on_selector(
        selector,
        """(el, v) => {
            el.value = v;
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        }""",
        value,
    )


def login_if_needed(page, company, employee, password):
    if page.locator("#login-comp-input").count() == 0:
        return
    print("logging in...")
    page.fill("#login-comp-input", company)
    page.fill("#login-name-input", employee)
    page.fill("#login-pw-input", password)
    page.click("#cpick button[type=submit]")
    page.wait_for_load_state("networkidle")
    if page.locator("#login-comp-input").count() > 0:
        # Drop the saved password so the next run asks for it again.
        forget_keychain_password(employee)
        sys.exit("ERROR: login failed - check credentials. Run again to re-enter them.")


def open_report(page):
    link = page.locator(".edit-info .new-link").first
    link.wait_for(timeout=15000)
    # The link may navigate in place or open a new tab.
    try:
        with page.context.expect_page(timeout=3000) as new_page_info:
            link.click()
        report = new_page_info.value
    except PlaywrightTimeout:
        report = page
    report.wait_for_load_state("networkidle")
    return report


def is_future(date_str):
    # Rows look like "30-11-2026 ב"; the page doesn't always flag future rows.
    try:
        return datetime.strptime(date_str.split()[0], "%d-%m-%Y").date() > date.today()
    except (ValueError, IndexError):
        return False


def missing_rows(page, include_future=False):
    """Return [(date_str, row_index)] for days missing entry/exit."""
    rows = page.evaluate(
        """(missing) => {
            const out = [];
            const rows = Array.from(document.querySelectorAll('tr'));
            rows.forEach((tr, i) => {
                const cell = Array.from(tr.querySelectorAll('td'))
                    .find(td => td.textContent.includes(missing));
                if (!cell) return;
                if (tr.getAttribute('data-error') === 'show-error') return; // future day
                const first = tr.querySelector('td');
                out.push([first ? first.textContent.trim() : `row ${i}`, i]);
            });
            return out;
        }""",
        MISSING_TEXT,
    )
    return [(d, i) for d, i in rows if include_future or not is_future(d)]


def fill_day(page, row_index, start, end):
    row = page.locator("tr").nth(row_index)
    row.locator("td", has_text=MISSING_TEXT).first.click()
    page.locator("#ehh0").wait_for(timeout=5000)
    set_field(page, "#ehh0", start[0])
    set_field(page, "#emm0", start[1])
    set_field(page, "#xhh0", end[0])
    set_field(page, "#xmm0", end[1])
    page.locator("button", has_text=SUBMIT_DAILY_TEXT).first.click()
    try:
        page.locator(".modal-dialog").wait_for(state="detached", timeout=8000)
    except PlaywrightTimeout:
        pass
    page.wait_for_load_state("networkidle")


def launch(p, headed):
    # Prefer the installed Google Chrome so no browser download is needed.
    try:
        return p.chromium.launch(channel="chrome", headless=not headed)
    except PlaywrightError:
        pass
    try:
        return p.chromium.launch(headless=not headed)
    except PlaywrightError as e:
        if "Executable doesn't exist" not in str(e):
            raise
        print("installing chromium for playwright...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        return p.chromium.launch(headless=not headed)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="list missing days, change nothing")
    ap.add_argument("--start", help="start time HH:MM (default 09:00)")
    ap.add_argument("--end", help="end time HH:MM (default 18:00)")
    ap.add_argument("--company")
    ap.add_argument("--employee")
    ap.add_argument("--until-today", action="store_true",
                    help="skip days after today (default: fill until end of month)")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    ap.add_argument("--setup", action="store_true", help="re-enter employee number and password")
    ap.add_argument("--screenshot", help="save a final screenshot to this path")
    args = ap.parse_args()

    company, employee, password, start, end = load_config(args)

    with sync_playwright() as p:
        browser = launch(p, args.headed)
        page = browser.new_page()
        page.goto(TIMEWATCH_URL)
        page.wait_for_load_state("networkidle")
        login_if_needed(page, company, employee, password)
        page = open_report(page)

        days = missing_rows(page, not args.until_today)
        if not days:
            print("No missing days - report is complete.")
        else:
            print(f"Missing days ({len(days)}): " + ", ".join(d for d, _ in days))

        filled, failed, attempted = [], [], set()
        if not args.dry_run:
            # The page may re-render after each submit, so re-scan every round.
            while True:
                pending = [(d, i) for d, i in missing_rows(page, not args.until_today) if d not in attempted]
                if not pending:
                    break
                date_str, idx = pending[0]
                attempted.add(date_str)
                print(f"filling {date_str} {start[0]}:{start[1]}-{end[0]}:{end[1]}...")
                try:
                    fill_day(page, idx, start, end)
                    filled.append(date_str)
                except (PlaywrightTimeout, PlaywrightError) as e:
                    print(f"  failed: {e.__class__.__name__}: {str(e).splitlines()[0]}")
                    failed.append(date_str)
                    page.keyboard.press("Escape")
            # Reload so the final check reflects what the server saved, not the
            # page's in-memory state.
            page.reload()
            page.wait_for_load_state("networkidle")
            still = [d for d, _ in missing_rows(page, not args.until_today)]
            print(f"Filled: {len(filled)}  Failed: {len(failed)}  Still missing: {len(still)}")
            if still:
                print("Still missing: " + ", ".join(still))

        if args.screenshot:
            page.screenshot(path=args.screenshot, full_page=True)
            print(f"screenshot: {args.screenshot}")
        browser.close()


if __name__ == "__main__":
    main()
