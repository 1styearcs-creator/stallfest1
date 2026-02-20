from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import random

app = Flask(__name__)
app.secret_key = "secret123"
DB = "stall_data.db"

# ------------------ DB Init ------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS inventory(
        name TEXT PRIMARY KEY,
        qty INTEGER,
        cp INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS stats(
        id INTEGER PRIMARY KEY,
        revenue INTEGER,
        g20 INTEGER,
        battle INTEGER,
        g150 INTEGER,
        g250 INTEGER,
        money_games INTEGER,
        money_profit INTEGER
    )""")
    if c.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]==0:
        items = [
            ("Turtle", 56, 27), ("Mini Rabbit", 30, 27), ("Parrot", 20, 27),
            ("Heart", 21, 27), ("Dog", 50, 27), ("Cat", 75, 27),
            ("Giraffe", 20, 40), ("Elephant", 20, 40),
            ("Rabbit Big", 20, 42), ("Camel", 20, 40),
            ("Mini Teddy", 20, 45), ("Spandex Toy", 9, 90),
            ("Penguin", 1, 150), ("Giant Teddy", 1, 1500)
        ]
        c.executemany("INSERT INTO inventory VALUES (?,?,?)", items)
    if c.execute("SELECT COUNT(*) FROM stats").fetchone()[0]==0:
        c.execute("INSERT INTO stats VALUES (1,0,0,0,0,0,0,0)")
    conn.commit()
    conn.close()

# ------------------ Inventory ------------------
def get_inventory():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM inventory")
    inv = {r[0]: {"qty": r[1], "cp": r[2]} for r in c.fetchall()}
    conn.close()
    return inv

def update_qty(name, new_qty):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE inventory SET qty=? WHERE name=?", (new_qty, name))
    conn.commit()
    conn.close()

# ------------------ Stats ------------------
def get_stats():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM stats WHERE id=1")
    s = c.fetchone()
    conn.close()
    return s

def update_stats(revenue=0, g20=0, battle=0, g150=0, g250=0, money_games=0, money_profit=0):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""UPDATE stats SET
        revenue = revenue + ?,
        g20 = g20 + ?,
        battle = battle + ?,
        g150 = g150 + ?,
        g250 = g250 + ?,
        money_games = money_games + ?,
        money_profit = money_profit + ?
        WHERE id=1""", (revenue, g20, battle, g150, g250, money_games, money_profit))
    conn.commit()
    conn.close()

# ------------------ Prize ------------------
def give_prize(name):
    inv = get_inventory()
    if not name or inv.get(name, {"qty": 0})["qty"] <= 0:
        return None
    update_qty(name, inv[name]["qty"] - 1)
    return name

def auto_27():
    inv = get_inventory()
    items = [k for k in inv if inv[k]["cp"] == 27 and inv[k]["qty"] > 0]
    if not items:
        return None
    max_qty = max(inv[k]["qty"] for k in items)
    max_items = [k for k in items if inv[k]["qty"] == max_qty]
    chosen = random.choice(max_items)
    update_qty(chosen, inv[chosen]["qty"] - 1)
    return chosen

# ------------------ Routes ------------------
@app.route("/", methods=["GET", "POST"])
def index():
    inv = get_inventory()
    stats = get_stats()
    message = ""

    if request.method == "POST":
        game = request.form.get("game")
        result = request.form.get("result")
        winner = request.form.get("winner")
        loser = request.form.get("loser")
        money_ball = request.form.get("money_ball")

        g20 = battle = g150 = g250 = money_games = money_profit = 0
        revenue = 0
        prize_msg = ""

        # 20₹ GAME
        if game == "20":
            revenue = 20
            g20 = 1
            if result == "Win":
                prize = give_prize(winner)
                prize_msg = f"🎉 Winner: {prize}"
            else:
                prize_msg = "😞 Loser gets no prize"

        # BATTLE
        elif game == "Battle":
            revenue = 220
            battle = 1
            win = give_prize(winner)
            if not loser or loser == "AUTO":
                lose = auto_27()
            else:
                lose = give_prize(loser)
            prize_msg = f"🏆 Winner: {win} | 🎁 Loser: {lose}"

        # 150₹ GAME
        elif game == "150":
            revenue = 150
            g150 = 1
            if result == "Win":
                prize = give_prize("Spandex Toy")
                prize_msg = f"🎉 Winner: {prize}"
            else:
                if not loser or loser == "AUTO":
                    lose = auto_27()
                else:
                    lose = give_prize(loser)
                prize_msg = f"🎁 Loser got: {lose}"

        # 250₹ GAME
        elif game == "250":
            revenue = 250
            g250 = 1
            if result == "Win":
                # First prize = winner category
                prize1 = give_prize(winner)
                # Second prize = loser category or auto max 27₹
                if not loser or loser == "AUTO":
                    prize2 = auto_27()
                else:
                    prize2 = give_prize(loser)
                prize_msg = f"🎉 Winner got: {prize1} + {prize2}"
            else:
                # Lose case, optional loser prize
                if not loser or loser == "AUTO":
                    lose = auto_27()
                else:
                    lose = give_prize(loser)
                prize_msg = f"🎁 Loser got: {lose}"

        # MONEY GAME
        elif game == "Money":
            # MONEY GAME
            money_games = 1
            if not money_ball:
                prize_msg = "Select Ball Outcome"
                return render_template("index.html", inventory=inv, stats=stats, message=prize_msg)
            
            if money_ball == "0":
                revenue = 100
                money_profit = 100
                prize_msg = "0 Ball: Revenue +100, Profit +100"
            elif money_ball == "1":
                revenue = 0
                money_profit = 0
                prize_msg = "1 Ball: Revenue 0, Profit 0"
            elif money_ball == "2":
                revenue = -900
                money_profit = -900
                prize_msg = "2 Ball: Revenue -900, Profit -900"

        # Update stats
        update_stats(revenue, g20, battle, g150, g250, money_games, money_profit)
        session['message'] = prize_msg
        return redirect(url_for('index'))

    message = session.pop('message', '')
    return render_template("index.html", inventory=inv, stats=stats, message=message)

@app.route("/report")
def report():
    stats = get_stats()
    inv = get_inventory()

    initial_items = {
        "Turtle": 56, "Mini Rabbit": 30, "Parrot": 20,
        "Heart": 21, "Dog": 50, "Cat": 75,
        "Giraffe": 20, "Elephant": 20,
        "Rabbit Big": 20, "Camel": 20,
        "Mini Teddy": 20, "Spandex Toy": 9,
        "Penguin": 1, "Giant Teddy": 1
    }

    spent = 0
    for name, data in inv.items():
        init_qty = initial_items.get(name, data["qty"])
        spent += (init_qty - data["qty"]) * data["cp"]

    total_profit = stats[1] - spent + stats[7]

    return render_template("report.html", stats=stats, inventory=inv, profit=total_profit)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
