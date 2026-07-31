"""极简用户服务：/users 读写 SQLite。"""
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "users.db"


def get_conn():
    # 写操作等待锁释放最多 5s，避免并发写直接抛 database is locked
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    # WAL 模式：读写不互斥，并发写串行化而非直接失败
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@app.route("/users", methods=["GET"])
def list_users():
    with get_conn() as conn:
        rows = conn.execute("SELECT id, name FROM users").fetchall()
    return jsonify([{"id": r[0], "name": r[1]} for r in rows])


@app.route("/users", methods=["POST"])
def create_user():
    name = request.json["name"]
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO users(name) VALUES (?)", (name,))
        conn.commit()
        new_id = cur.lastrowid
    return jsonify({"id": new_id, "name": name}), 201


if __name__ == "__main__":
    init = sqlite3.connect(DB_PATH)
    init.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT)")
    init.close()
    app.run(host="0.0.0.0", port=5000, threaded=True)
