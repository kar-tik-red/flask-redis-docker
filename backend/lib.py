from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token, get_jwt
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import json
import os
from datetime import datetime


def get_db():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database="library",
        user="sharingan",
        password=os.getenv("DB_PASSWORD", "")
    )
    return conn


r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, db=0)

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "superkey"
jwt = JWTManager(app)
CORS(app)


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data["username"]
    password = data["password"]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify("Registered")


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data["username"]
    password = data["password"]

    rate_key = f"ratelimit:{username}"
    attempts = r.get(rate_key)
    if attempts and int(attempts) >= 5:
        return jsonify({"error": "Too many attempts, try again in a minute"}), 429
    r.incr(rate_key)
    r.expire(rate_key, 60)

    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        token = create_access_token(identity=username)
        return jsonify({"token": token})
    return jsonify({"error": "Wrong credentials"})


@app.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    token = get_jwt()
    jti = token["jti"]
    exp = token["exp"]
    now = datetime.timestamp(datetime.now())
    ttl = int(exp - now)
    r.set(f"blacklist:{jti}", "true", ex=ttl)
    return jsonify({"message": "Logged out"})


@app.route("/book", methods=["POST"])
@jwt_required()
def book():
    jti = get_jwt()["jti"]
    if r.get(f"blacklist:{jti}"):
        return jsonify({"error": "Token has been revoked"}), 401

    data = request.get_json()
    if not data or "title" not in data:
        return jsonify("error")
    title = data["title"]
    author = data["author"]
    genre = data["genre"]
    user = get_jwt_identity()
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id FROM users WHERE username = %s", (user,))
    usid = cursor.fetchone()
    cursor.execute(
        "INSERT INTO books (user_id, title, author, genre, read) VALUES (%s, %s, %s, %s, 0)",
        (usid["id"], title, author, genre)
    )
    conn.commit()
    cursor.close()
    conn.close()
    r.delete(f"books:{user}")
    r.publish("new_book", json.dumps({"user": user, "title": title, "author": author}))
    return jsonify({"title": title, "author": author, "genre": genre})


@app.route("/get_book", methods=["GET"])
@jwt_required()
def get_book():
    jti = get_jwt()["jti"]
    if r.get(f"blacklist:{jti}"):
        return jsonify({"error": "Token has been revoked"}), 401

    user = get_jwt_identity()
    cache_key = f"books:{user}"
    cached = r.get(cache_key)
    if cached:
        return jsonify(json.loads(cached))

    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id FROM users WHERE username = %s", (user,))
    usid = cursor.fetchone()
    cursor.execute("SELECT * FROM books WHERE user_id = %s", (usid["id"],))
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    result = [dict(book) for book in books]
    r.set(cache_key, json.dumps(result), ex=60)
    return jsonify(result)


@app.route("/book/<int:book_id>", methods=["DELETE"])
@jwt_required()
def delete_book(book_id):
    jti = get_jwt()["jti"]
    if r.get(f"blacklist:{jti}"):
        return jsonify({"error": "Token has been revoked"}), 401

    user = get_jwt_identity()
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id FROM users WHERE username = %s", (user,))
    usid = cursor.fetchone()
    cursor.execute("DELETE FROM books WHERE id = %s AND user_id = %s", (book_id, usid["id"]))
    conn.commit()
    cursor.close()
    conn.close()
    r.delete(f"books:{user}")
    return jsonify({"message": "Book deleted"})


@app.route("/book/<int:book_id>", methods=["PUT"])
@jwt_required()
def update_book(book_id):
    jti = get_jwt()["jti"]
    if r.get(f"blacklist:{jti}"):
        return jsonify({"error": "Token has been revoked"}), 401

    user = get_jwt_identity()
    data = request.get_json()
    read = data["read"]
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id FROM users WHERE username = %s", (user,))
    usid = cursor.fetchone()
    cursor.execute(
        "UPDATE books SET read = %s WHERE id = %s AND user_id = %s",
        (read, book_id, usid["id"])
    )
    conn.commit()
    cursor.close()
    conn.close()
    r.delete(f"books:{user}")
    return jsonify({"message": "Book updated"})


if __name__ == "__main__":
    app.run(debug=True)
