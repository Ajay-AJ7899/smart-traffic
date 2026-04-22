from django.apps import AppConfig
from django.db.backends.signals import connection_created


def configure_sqlite_connection(sender, connection, **kwargs):
    if connection.vendor != "sqlite":
        return

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=OFF;")


class TrafficConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "traffic"

    def ready(self):
        connection_created.connect(configure_sqlite_connection, dispatch_uid="traffic_sqlite_config")
