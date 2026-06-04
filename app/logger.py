from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent

LOG_DIR = BASE_DIR / "storage" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_log_file():

    today = datetime.now().strftime("%Y-%m-%d")

    return LOG_DIR / f"bot_{today}.log"


def write_log(user_id: int, command: str):

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    line = (
        f"{now} | USER:{user_id} | COMMAND:{command}\n"
    )

    log_file = get_log_file()

    with open(log_file, "a", encoding="utf-8") as file:
        file.write(line)