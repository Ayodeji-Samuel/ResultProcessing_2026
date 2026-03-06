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

app.config['PREFERRED_URL_SCHEME'] = 'https'

# APPLICATION_SUBPATH is an optional environment variable.
# Set it (e.g. APPLICATION_SUBPATH=/cschub) only when the app is reverse-proxied
# at a sub-path and your Nginx/Caddy passes the full path (including the prefix)
# to gunicorn.  On DigitalOcean App Platform and most standard deployments the
# app runs at its own domain root — leave this variable unset (or empty) and
# the app is served cleanly without any prefix.
_sub_path = os.environ.get('APPLICATION_SUBPATH', '').rstrip('/')

if _sub_path:
    # Mount the app only at the configured sub-path so that url_for() generates
    # correct URLs.  A plain 404 response is returned for any request that does
    # NOT start with the prefix (avoids silently serving the app at root too).
    app.config['APPLICATION_ROOT'] = _sub_path
    _dispatcher = DispatcherMiddleware(
        app,
        {_sub_path: app},
    )
    # x_prefix=0 because DispatcherMiddleware already sets SCRIPT_NAME from the
    # matched prefix — letting ProxyFix also apply X-Forwarded-Prefix would
    # double the prefix.
    application = ProxyFix(_dispatcher, x_for=1, x_proto=1, x_host=1, x_prefix=1)
else:
    # Standard root deployment (DigitalOcean App Platform, Railway, Render, etc.)
    # ProxyFix handles X-Forwarded-For / X-Forwarded-Proto from the load balancer.
    application = ProxyFix(app, x_for=1, x_proto=1, x_host=1, x_prefix=0)
