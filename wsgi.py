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

app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)

application = DispatcherMiddleware(
    app,
    {'/cschub': app}
)