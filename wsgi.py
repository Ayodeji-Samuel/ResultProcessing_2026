# from app import create_app
# from werkzeug.middleware.proxy_fix import ProxyFix
# import os

# config_name = os.environ.get('FLASK_CONFIG', 'default')  # optional: choose config via env var
# app = create_app(config_name)
# app.wsgi_app = ProxyFix(app.wsgi_app)
# application = app
from app import create_app
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.wrappers import Response
import os

config_name = os.environ.get('FLASK_CONFIG', 'default')
app = create_app(config_name)

app.config['APPLICATION_ROOT'] = '/cschub'
app.config['PREFERRED_URL_SCHEME'] = 'https'

# DispatcherMiddleware routes /cschub/* to the Flask app and sets SCRIPT_NAME=/cschub.
# ProxyFix must wrap the *outermost* WSGI layer so it fixes forwarded headers (for=, proto=,
# host=) before any routing happens. x_prefix is 0 because DispatcherMiddleware already
# handles SCRIPT_NAME via path stripping — adding x_prefix=1 here would double the prefix
# (/cschub/cschub) whenever Nginx sends an X-Forwarded-Prefix header.
_dispatcher = DispatcherMiddleware(app, {'/cschub': app})
application = ProxyFix(_dispatcher, x_for=1, x_proto=1, x_host=1, x_prefix=0)