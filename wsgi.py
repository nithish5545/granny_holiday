"""
WSGI entry point for production deployment.
Usage with Gunicorn:  gunicorn wsgi:app
Usage with Waitress:  waitress-serve --port=8000 wsgi:app
"""
from app import app

if __name__ == "__main__":
    app.run()
