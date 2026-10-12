"""Manage the nightly scrape in your user crontab.

  python schedule.py install    # add the nightly job (02:00, machine time)
  python schedule.py status     # show whether it is installed
  python schedule.py uninstall  # remove it

Only the line tagged with MARKER is ever touched; the rest of your crontab is left alone.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
MARKER = "# casino-bonus-scraper"
TIME = "0 2"  # minute hour -> 02:00 every night
LINE = f'{TIME} * * * cd "{HERE}" && "{HERE}/.venv/bin/python" scrape.py >> "{HERE}/data/cron.log" 2>&1 {MARKER}'


def read_crontab() -> list[str]:
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else []  # no crontab yet -> empty


def write_crontab(lines: list[str]) -> None:
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n" if lines else "", text=True, check=True)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    current = read_crontab()
    others = [l for l in current if MARKER not in l]
    installed = len(others) != len(current)

    if cmd == "install":
        (HERE / "data").mkdir(exist_ok=True)
        write_crontab(others + [LINE])
        print(f"Installed: runs every night at 02:00 (machine time).\nLogs: {HERE}/data/cron.log")
    elif cmd == "uninstall":
        write_crontab(others)
        print("Removed." if installed else "Nothing to remove.")
    elif cmd == "status":
        print("Installed:\n" + LINE if installed else "Not installed. Run: python schedule.py install")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
