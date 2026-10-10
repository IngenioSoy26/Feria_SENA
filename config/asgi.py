import os
from pathlib import Path

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

# RESCATE INVERSO V38.2 (vuelta desde V39):
try:
    import django as _django_setup2
    try:
        _django_setup2.setup()
    except Exception:
        pass
except Exception:
    pass
try:
    from apps.usuarios._rescate_sql_vuelta_v38 import SQL_EJECUTAR_RESCATES_V38
    SQL_EJECUTAR_RESCATES_V38()
except Exception:
    pass

application = get_asgi_application()
