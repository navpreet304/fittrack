from flask import g, current_app


def get_db():
    """Return a DB session scoped to the current request (cached in g)."""
    if "db" not in g:
        Session = current_app.config["SessionLocal"]
        g.db = Session()
    return g.db
