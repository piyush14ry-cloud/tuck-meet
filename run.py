"""Local entry point:  python run.py  (development server only).

For production, run behind a WSGI server, e.g.:
    gunicorn "app:create_app()"
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Debug is controlled by FLASK_ENV in config; never force it on here.
    app.run(host="127.0.0.1", port=5000)
