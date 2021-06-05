from piccolo.apps.migrations.auto import MigrationManager


ID = "2021-04-24T18:25:36"
VERSION = "0.17.5"


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="")

    def run():
        print(f"running {ID}")

    manager.add_raw(run)

    return manager
