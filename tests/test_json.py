from storage.json_manager import JsonManager
from config.path_manager import paths


data = {
    "project": "ConfigManager",
    "status": "running"
}


JsonManager.save(
    paths.USERS_JSON,
    data
)

loaded = JsonManager.load(
    paths.USERS_JSON
)

print(loaded)