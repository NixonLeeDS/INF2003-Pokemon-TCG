from flask import Flask, flash, redirect, render_template, request, url_for

from config import Config
from services import mongo as mongo_service
from services import relational as sql_service

app = Flask(__name__)
app.config.from_object(Config)


def selected_user_id(default=1):
    try:
        return int(request.values.get("user_id", default))
    except (TypeError, ValueError):
        return default


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
    min_hp = int(min_hp_raw) if min_hp_raw.isdigit() else None
    cards = sql_service.search_cards(name, set_id, card_type, rarity, min_hp, limit=100)
    sets, types, rarities = sql_service.list_filters()
    return render_template(
        "index.html", cards=cards, sets=sets, types=types, rarities=rarities,
        filters={"name": name, "set_id": set_id, "card_type": card_type, "rarity": rarity, "min_hp": min_hp_raw},
    )


@app.route("/card/<card_id>")
def card_detail(card_id):
    card = sql_service.get_card(card_id)
    nested = mongo_service.card_detail(card_id)
    if not card:
        return "Card not found", 404
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
            else:
                quantity = int(request.form.get("quantity", 1))
                trade_quantity = int(request.form.get("trade_quantity", 0))
                sql_service.upsert_collection(user_id, card_id, quantity, trade_quantity)
            flash("Collection updated.", "success")
        except Exception as exc:
            flash(f"Collection update failed: {exc}", "error")
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
            else:
                priority = int(request.form.get("priority", 3))
                sql_service.upsert_wishlist(user_id, card_id, priority)
            flash("Wishlist updated.", "success")
        except Exception as exc:
            flash(f"Wishlist update failed: {exc}", "error")
        return redirect(url_for("wishlist", user_id=user_id))
    return render_template("wishlist.html", user_id=user_id, rows=sql_service.wishlist(user_id))


@app.route("/trade-matches")
def trade_matches():
    user_id = selected_user_id()
    matches = sql_service.trade_matches(user_id)
    reciprocal = sql_service.reciprocal_trade_matches(user_id)
    return render_template("trade_matches.html", user_id=user_id, matches=matches, reciprocal=reciprocal)


def parse_trade_items(text):
    """Parse 'base1-1:1,base1-2:2' into [(card_id, quantity), ...]."""
    items = []
    for part in (text or "").split(","):
        part = part.strip()
        if not part:
            continue
        card_id, qty = part.rsplit(":", 1)
        items.append((card_id.strip(), int(qty)))
    return items


@app.route("/trades", methods=["GET", "POST"])
def trades():
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "create":
                requester_id = int(request.form["requester_id"])
                recipient_id = int(request.form["recipient_id"])
                requester_items = parse_trade_items(request.form.get("requester_items"))
                recipient_items = parse_trade_items(request.form.get("recipient_items"))
                trade_id = sql_service.create_trade(requester_id, recipient_id, requester_items, recipient_items)
                flash(f"Trade {trade_id} created.", "success")
            elif action == "complete":
                sql_service.complete_trade(int(request.form["trade_id"]))
                flash("Trade completed atomically and collections were updated.", "success")
            else:
                status_map = {"accept": "ACCEPTED", "reject": "REJECTED", "cancel": "CANCELLED"}
                sql_service.set_trade_status(int(request.form["trade_id"]), status_map[action])
                flash("Trade status updated.", "success")
        except Exception as exc:
            flash(f"Trade action failed: {exc}", "error")
        return redirect(url_for("trades"))
    return render_template("trades.html", rows=sql_service.list_trades())


@app.route("/analytics")
def analytics():
    user_id = selected_user_id()
    keyword = request.args.get("keyword", "draw")
    min_damage = request.args.get("min_damage", "100")
    try:
        damage_value = int(min_damage)
    except ValueError:
        damage_value = 100

    mongo_error = None
    try:
        weakness = mongo_service.weakness_distribution()
        legality = mongo_service.legality_distribution()
        avg_attacks = mongo_service.average_attack_count_by_type()
        keyword_results = mongo_service.nested_keyword_search(keyword, limit=20) if keyword else []
        high_damage = mongo_service.cards_with_attack_damage_at_least(damage_value, limit=20)
    except Exception as exc:
        mongo_error = str(exc)
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


if __name__ == "__main__":
    app.run(debug=Config.DEBUG)
