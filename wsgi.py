# from app import create_app
# from werkzeug.middleware.proxy_fix import ProxyFix
# import os

# config_name = os.environ.get('FLASK_CONFIG', 'default')  # optional: choose config via env var
# app = create_app(config_name)
# app.wsgi_app = ProxyFix(app.wsgi_app)
# application = app
from app import create_app
from werkzeug.middleware.proxy_fix import ProxyFix
import os

config_name = os.environ.get('FLASK_CONFIG', 'production')
app = create_app(config_name)

# ProxyFix handles X-Forwarded-* headers from Nginx.
# x_prefix=1 reads X-Forwarded-Prefix and sets SCRIPT_NAME so that
# url_for() generates the correct sub-path URLs (e.g. /cschub/students/).
# Do NOT set APPLICATION_ROOT here — DispatcherMiddleware or the proxy
# sets SCRIPT_NAME directly; setting APPLICATION_ROOT as well doubles
# the prefix and breaks all redirects/links on the cloud server.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

application = app