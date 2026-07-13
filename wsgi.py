"""WSGI entrypoint for gunicorn-style deployments (Render, Heroku, PythonAnywhere)."""
from app import app

if __name__ == "__main__":
    app.run()
