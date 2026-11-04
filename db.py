"""Conexão com o banco SQLite, uma por requisição."""
import sqlite3

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_erro=None):
    conexao = g.pop("db", None)
    if conexao is not None:
        conexao.close()


def init_app(app):
    app.teardown_appcontext(close_db)
