import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, g
)
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "banking_web.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this-secret-key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            card_number TEXT NOT NULL UNIQUE,
            pin_hash TEXT NOT NULL,
            balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            amount INTEGER NOT NULL CHECK (amount > 0),
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        );
    """)
    db.commit()
    db.close()


def csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return session["_csrf_token"]


@app.context_processor
def inject_csrf():
    return {"csrf_token": csrf_token}


@app.before_request
def protect_post_requests():
    if request.method == "POST":
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        expected = session.get("_csrf_token")
        if not sent or not expected or not secrets.compare_digest(sent, expected):
            if request.is_json:
                return jsonify({"error": "Invalid or expired security token. Refresh and try again."}), 400
            flash("Your session security token expired. Please try again.", "error")
            return redirect(request.referrer or url_for("index"))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "account_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def generate_card_number():
    # Generate a 16-digit card number with a 400000 prefix and valid Luhn check digit.
    while True:
        body = "400000" + "".join(str(secrets.randbelow(10)) for _ in range(9))
        total = 0
        for index, char in enumerate(body):
            digit = int(char) * (2 if index % 2 == 0 else 1)
            if digit > 9:
                digit -= 9
            total += digit
        card = body + str((-total) % 10)
        exists = get_db().execute(
            "SELECT 1 FROM accounts WHERE card_number = ?", (card,)
        ).fetchone()
        if not exists:
            return card


def current_account():
    return get_db().execute(
        "SELECT id, full_name, card_number, balance, created_at FROM accounts WHERE id = ?",
        (session["account_id"],)
    ).fetchone()


@app.route("/")
def index():
    if "account_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        pin = request.form.get("pin", "").strip()
        confirm = request.form.get("confirm_pin", "").strip()

        if len(name) < 2 or len(name) > 80:
            flash("Enter a name between 2 and 80 characters.", "error")
        elif len(pin) != 4 or not pin.isdigit():
            flash("Your PIN must contain exactly 4 digits.", "error")
        elif pin != confirm:
            flash("PINs do not match.", "error")
        else:
            card = generate_card_number()
            db = get_db()
            db.execute(
                "INSERT INTO accounts (full_name, card_number, pin_hash) VALUES (?, ?, ?)",
                (name, card, generate_password_hash(pin))
            )
            db.commit()
            flash(f"Account created. Your card number is {card}. Save it safely.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        card = request.form.get("card_number", "").strip()
        pin = request.form.get("pin", "").strip()
        account = get_db().execute(
            "SELECT id, pin_hash FROM accounts WHERE card_number = ?", (card,)
        ).fetchone()

        if account and check_password_hash(account["pin_hash"], pin):
            session.clear()
            session["account_id"] = account["id"]
            csrf_token()
            return redirect(url_for("dashboard"))

        flash("Card number or PIN is incorrect.", "error")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    account = current_account()
    transactions = get_db().execute(
        """SELECT transaction_type, amount, note, created_at
           FROM transactions WHERE account_id = ?
           ORDER BY id DESC LIMIT 8""",
        (session["account_id"],)
    ).fetchall()
    return render_template("dashboard.html", account=account, transactions=transactions)


def read_amount():
    raw = request.form.get("amount", "").strip()
    try:
        amount = int(raw)
    except ValueError:
        return None
    return amount if 0 < amount <= 1_000_000_000 else None


@app.route("/deposit", methods=["POST"])
@login_required
def deposit():
    amount = read_amount()
    if amount is None:
        flash("Enter a valid positive whole-number amount.", "error")
        return redirect(url_for("dashboard"))

    db = get_db()
    account_id = session["account_id"]
    db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
    db.execute(
        "INSERT INTO transactions (account_id, transaction_type, amount, note) VALUES (?, 'DEPOSIT', ?, ?)",
        (account_id, amount, "Cash deposit (demo)")
    )
    db.commit()
    flash(f"₹{amount:,} deposited successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/withdraw", methods=["POST"])
@login_required
def withdraw():
    amount = read_amount()
    if amount is None:
        flash("Enter a valid positive whole-number amount.", "error")
        return redirect(url_for("dashboard"))

    db = get_db()
    account_id = session["account_id"]
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if row is None or amount > row["balance"]:
            db.rollback()
            flash("Insufficient balance.", "error")
            return redirect(url_for("dashboard"))

        db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
        db.execute(
            "INSERT INTO transactions (account_id, transaction_type, amount, note) VALUES (?, 'WITHDRAWAL', ?, ?)",
            (account_id, amount, "Cash withdrawal (demo)")
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    flash(f"₹{amount:,} withdrawn successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/transfer", methods=["POST"])
@login_required
def transfer():
    receiver_card = request.form.get("receiver_card", "").strip()
    amount = read_amount()
    sender_id = session["account_id"]

    if amount is None:
        flash("Enter a valid positive whole-number amount.", "error")
        return redirect(url_for("dashboard"))

    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        sender = db.execute("SELECT id, card_number, balance FROM accounts WHERE id = ?", (sender_id,)).fetchone()
        receiver = db.execute("SELECT id, card_number FROM accounts WHERE card_number = ?", (receiver_card,)).fetchone()

        if receiver is None:
            db.rollback()
            flash("Recipient account was not found.", "error")
            return redirect(url_for("dashboard"))
        if receiver["id"] == sender_id:
            db.rollback()
            flash("You cannot transfer money to your own account.", "error")
            return redirect(url_for("dashboard"))
        if amount > sender["balance"]:
            db.rollback()
            flash("Insufficient balance for this transfer.", "error")
            return redirect(url_for("dashboard"))

        db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, sender_id))
        db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, receiver["id"]))
        db.execute(
            "INSERT INTO transactions (account_id, transaction_type, amount, note) VALUES (?, 'TRANSFER_SENT', ?, ?)",
            (sender_id, amount, f"Sent to card ending {receiver_card[-4:]}")
        )
        db.execute(
            "INSERT INTO transactions (account_id, transaction_type, amount, note) VALUES (?, 'TRANSFER_RECEIVED', ?, ?)",
            (receiver["id"], amount, f"Received from card ending {sender['card_number'][-4:]}")
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    flash(f"₹{amount:,} transferred successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/transactions")
@login_required
def transactions():
    rows = get_db().execute(
        """SELECT transaction_type, amount, note, created_at
           FROM transactions WHERE account_id = ?
           ORDER BY id DESC LIMIT 100""",
        (session["account_id"],)
    ).fetchall()
    return render_template("transactions.html", transactions=rows)


@app.route("/close-account", methods=["POST"])
@login_required
def close_account():
    confirmation = request.form.get("confirmation", "").strip().lower()
    if confirmation != "close":
        flash('Type "close" to confirm account deletion.', "error")
        return redirect(url_for("dashboard"))

    db = get_db()
    db.execute("DELETE FROM accounts WHERE id = ?", (session["account_id"],))
    db.commit()
    session.clear()
    flash("Your demo account has been closed.", "success")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="Page not found."), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
