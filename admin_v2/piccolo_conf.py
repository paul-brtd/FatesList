from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine
import sys
sys.path.append("..")
from config import pg_user, pg_pwd

DB = PostgresEngine(config={
    "database": "fateslist",
    "user": pg_user,
    "password": pg_pwd
})


# A list of paths to piccolo apps
# e.g. ['blog.piccolo_app']
APP_REGISTRY = AppRegistry(apps=["admin_v2.piccolo_app", "piccolo.apps.user.piccolo_app", "piccolo_admin.piccolo_app"])
