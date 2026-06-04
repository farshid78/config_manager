from config.path_manager import paths


print("Base:", paths.APP.parent)

print("Database:", paths.DATABASE_FILE)

print("Users:", paths.USERS_JSON)