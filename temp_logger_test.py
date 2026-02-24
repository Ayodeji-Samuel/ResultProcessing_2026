from app import create_app
import logging

app = create_app()

with app.app_context():
    logger = logging.getLogger('test')
    try:
        logger.error('Test en-dash – message')
        print('logged ok')
    except Exception as e:
        print('logger error', e)
