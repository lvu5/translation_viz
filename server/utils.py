import asyncio
import datetime
import os
import shutil
import tomllib
from typing import Any

for config_file in ["config.toml", "config.template.toml"]:
    if os.path.exists(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/" + config_file
    ):
        break
else:
    raise FileNotFoundError("No config file found.")

with open(config_file, "rb") as f:
    config_data: dict[str, Any] = tomllib.load(f)


def get_config(key: str, default: Any = "") -> Any:
    return config_data.get(key) or os.getenv(key, default)


CONTRIBUTOR_QUOTA_DEFAULT = get_config("CONTRIBUTOR_QUOTA_DEFAULT", 10)
DB_PATH = get_config("DB_PATH", "data/db.sqlite")
OPENAI_API_KEY = get_config("OPENAI_API_KEY", "")


async def schedule_daily_backup() -> None:
    while True:
        try:
            now = datetime.datetime.now()
            target = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if target <= now:
                target += datetime.timedelta(days=1)
            delay = (target - now).total_seconds()
            hours = int(delay // 3600)
            minutes = int((delay % 3600) // 60)
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Next database backup scheduled in {hours} hours and {minutes} minutes (at {target.strftime('%Y-%m-%d %H:%M')})", flush=True)
            await asyncio.sleep(delay)
            
            # Copy database file
            backup_dir = os.path.join(os.path.dirname(DB_PATH) or "data", "backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_filename = f"db_{timestamp}.sqlite"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            await asyncio.to_thread(shutil.copy, DB_PATH, backup_path)
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Database backup created at {backup_path}", flush=True)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Error in backup schedule loop: {e}", flush=True)
            await asyncio.sleep(60)

