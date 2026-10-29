"""Development entry point for StatusWatch."""
from statuswatch import create_app
from statuswatch.scheduler import start_scheduler

app = create_app()

if __name__ == "__main__":
    start_scheduler(app)
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
