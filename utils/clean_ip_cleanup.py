import os
import time

FOLDER = "storage/clean_ips"

def cleanup_old_clean_ips():

    if not os.path.exists(FOLDER):
        return

    now = time.time()

    for file in os.listdir(FOLDER):

        path = os.path.join(FOLDER, file)

        if not os.path.isfile(path):
            continue

        age = now - os.path.getmtime(path)

        if age > 5 * 24 * 60 * 60:

            os.remove(path)