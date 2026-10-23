from flask import Flask, flash, redirect, render_template, request, url_for, session, abort
import secrets
import hmac
from pymysql import MySQLError, IntegrityError
from pymongo.errors import PyMongoError
from services.validation import integer, parse_trade_items

from config import Config
from services import mongo as mongo_service
from services import relational as sql_service

app = Flask(__name__)
app.config.from_object(Config)


@app.before_request
def protect_forms():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    if request.method == "POST":
        supplied = request.form.get("csrf_token", "")
        if not hmac.compare_digest(session["csrf_token"], supplied):
            abort(400, description="Form expired. Reload the page and try again.")


@app.errorhandler(400)
def bad_request(exc):
    return render_template("error.html", message=exc.description), 400


def selected_user_id(default=1):
    return integer(request.values.get("user_id", default), "User")


@app.context_processor
def inject_users():
    try:
        return {"all_users": sql_service.list_users()}
    except Exception:
        return {"all_users": []}


@app.route("/")
def index():
    name = request.args.get("name", "")
    set_id = request.args.get("set_id", "")
    card_type = request.args.get("card_type", "")
    rarity = request.args.get("rarity", "")
    min_hp_raw = request.args.get("min_hp", "").strip()
    min_hp = integer(min_hp_raw, "Minimum HP", 0, 10000) if min_hp_raw else None
    cards = sql_service.search_cards(name, set_id, card_type, rarity, min_hp, limit=100)
    sets, types, rarities = sql_service.list_filters()
    return render_template(
        "index.html", cards=cards, sets=sets, types=types, rarities=rarities,
        filters={"name": name, "set_id": set_id, "card_type": card_type, "rarity": rarity, "min_hp": min_hp_raw},
    )


@app.route("/card/<card_id>")
def card_detail(card_id):
    card = sql_service.get_card(card_id)
    if not card:
        return "Card not found", 404
    try:
        nested = mongo_service.card_detail(card_id)
    except PyMongoError:
        nested = None
        flash("Nested card details are temporarily unavailable.", "error")
    return render_template("card_detail.html", card=card, nested=nested)


@app.route("/collection", methods=["GET", "POST"])
def collection():
    user_id = selected_user_id()
    if request.method == "POST":
        action = request.form.get("action")
        card_id = request.form.get("card_id", "").strip()
        try:
            if action == "remove":
                sql_service.remove_collection(user_id, card_id)
            elif action == "upsert":
                quantity = request.form.get("quantity", "1")
                trade_quantity = request.form.get("trade_quantity", "0")
                sql_service.upsert_collection(user_id, card_id, quantity, trade_quantity)
            else:
                raise ValueError("Unknown collection action.")
            flash("Collection updated.", "success")
        except Exception as exc:
            mutation_error(exc)
        return redirect(url_for("collection", user_id=user_id))
    return render_template("collection.html", user_id=user_id, rows=sql_service.collection(user_id))


@app.route("/wishlist", methods=["GET", "POST"])
def wishlist():
    user_id = selected_user_id()
    if request.method == "POST":
        action = request.form.get("action")
        card_id = request.form.get("card_id", "").strip()
        try:
            if action == "remove":
                sql_service.remove_wishlist(user_id, card_id)
            elif action == "upsert":
                priority = request.form.get("priority", "3")
                sql_service.upsert_wishlist(user_id, card_id, priority)
            else:
                raise ValueError("Unknown wishlist action.")
            flash("Wishlist updated.", "success")
        except Exception as exc:
            mutation_error(exc)
        return redirect(url_for("wishlist", user_id=user_id))
    return render_template("wishlist.html", user_id=user_id, rows=sql_service.wishlist(user_id))


@app.route("/trade-matches")
def trade_matches():
    user_id = selected_user_id()
    matches = sql_service.trade_matches(user_id)
    reciprocal = sql_service.reciprocal_trade_matches(user_id)
    return render_template("trade_matches.html", user_id=user_id, matches=matches, reciprocal=reciprocal,
                           unavailable=sql_service.unavailable_wishes(user_id))


@app.route("/trades", methods=["GET", "POST"])
def trades():
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "create":
                requester_id = integer(request.form.get("requester_id"), "Requester")
                recipient_id = integer(request.form.get("recipient_id"), "Recipient")
                requester_items = parse_trade_items(request.form.get("requester_items"))
                recipient_items = parse_trade_items(request.form.get("recipient_items"))
                trade_id = sql_service.create_trade(requester_id, recipient_id, requester_items, recipient_items)
                flash(f"Trade {trade_id} created.", "success")
            elif action == "complete":
                sql_service.complete_trade(integer(request.form.get("trade_id"), "Trade"), request.form.get("actor_id"))
                flash("Trade completed atomically and collections were updated.", "success")
            else:
                status_map = {"accept": "ACCEPTED", "reject": "REJECTED", "cancel": "CANCELLED"}
                sql_service.set_trade_status(integer(request.form.get("trade_id"), "Trade"), status_map.get(action), request.form.get("actor_id"))
                flash("Trade status updated.", "success")
        except Exception as exc:
            mutation_error(exc)
        return redirect(url_for("trades"))
    return render_template("trades.html", rows=sql_service.list_trades())


@app.route("/query-demo")
def query_demo():
    from services.query_demo import QUERIES, run_query
    user_id = selected_user_id()
    selected = request.args.get("query", "trade_matches")
    rows = run_query(selected, user_id)
    return render_template("query_demo.html", queries=QUERIES, query=QUERIES[selected],
                           selected=selected, user_id=user_id, rows=rows)


@app.route("/analytics")
def analytics():
    user_id = selected_user_id()
    keyword = request.args.get("keyword", "draw").strip()
    if len(keyword) > 200:
        raise ValueError("Keyword must be at most 200 characters.")
    min_damage = request.args.get("min_damage", "100")
    damage_value = integer(min_damage, "Minimum damage", 0, 100000)

    mongo_error = None
    try:
        weakness = mongo_service.weakness_distribution()
        legality = mongo_service.legality_distribution()
        avg_attacks = mongo_service.average_attack_count_by_type()
        keyword_results = mongo_service.nested_keyword_search(keyword, limit=20) if keyword else []
        high_damage = mongo_service.cards_with_attack_damage_at_least(damage_value, limit=20)
    except Exception as exc:
        app.logger.exception("MongoDB analytics failed")
        mongo_error = "MongoDB analytics are temporarily unavailable. Check Status and the server log."
        weakness = legality = avg_attacks = keyword_results = high_damage = []

    return render_template(
        "analytics.html",
        user_id=user_id,
        summary=sql_service.collection_summary(),
        completion=sql_service.set_completion(user_id),
        weakness=weakness,
        legality=legality,
        avg_attacks=avg_attacks,
        keyword=keyword,
        keyword_results=keyword_results,
        min_damage=damage_value,
        high_damage=high_damage,
        mongo_error=mongo_error,
    )


def mutation_error(exc):
    if isinstance(exc, ValueError):
        message = str(exc)
    elif isinstance(exc, IntegrityError):
        message = "Choose an existing user and card, and check the quantities."
    else:
        app.logger.exception("Database update failed")
        message = "The update could not be saved. Check Status and retry; no partial trade was saved."
    flash(message, "error")


@app.errorhandler(ValueError)
def invalid_input(exc):
    return render_template("error.html", message=str(exc)), 400


@app.errorhandler(MySQLError)
def database_error(exc):
    app.logger.exception("MariaDB request failed")
    return render_template("error.html", message="MariaDB is unavailable. Check Status and your local setup."), 503


@app.route("/health")
def health():
    from db import mysql_cursor, mongo_database
    checks = {}
    for name in ("MariaDB", "MongoDB"):
        try:
            if name == "MariaDB":
                with mysql_cursor() as (_, cur):
                    cur.execute("SELECT COUNT(*) AS cards FROM cards")
                    checks[name] = {"ok": True, "cards": cur.fetchone()["cards"]}
            else:
                client, database = mongo_database()
                try:
                    client.admin.command("ping")
                    checks[name] = {"ok": True, "cards": database.card_details.count_documents({})}
                finally:
                    client.close()
        except (MySQLError, PyMongoError):
            checks[name] = {"ok": False}
    return render_template("health.html", checks=checks), (200 if all(c["ok"] for c in checks.values()) else 503)


if __name__ == "__main__":
    app.run(debug=Config.DEBUG)
