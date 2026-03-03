from app import create_app
from werkzeug.middleware.proxy_fix import ProxyFix
import os

config_name = os.environ.get('FLASK_CONFIG', 'default')  # optional: choose config via env var
app = create_app(config_name)
app.wsgi_app = ProxyFix(app.wsgi_app)
application = app
