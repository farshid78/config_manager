import json
import os

FILE = "admins.json"


def load_admins() -> set:
    if not os.path.exists(FILE):
        return set()

    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except:
        return set()


def save_admins(admins: set):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(list(admins), f, ensure_ascii=False, indent=2)