import os
import time
while True:
    print(f"Backup DB at {time.time()}")
    try:
        os.system("pg_dump -U backups fateslist | gzip > /home/meow/backup/db/$(date +%Y-%m-%d-%s).psql.gz")
    except:
        print("Backup Failed. See Postgres Logs")
    time.sleep(60 * 60 * 2)
