from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)
DB = "stall_data.db"

# --- Initialize DB ---
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # Inventory table
    c.execute("""CREATE TABLE IF NOT EXISTS inventory(
        name TEXT PRIMARY KEY,
        qty INTEGER,
        cp INTEGER
    )""")
    # Stats table
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
    # Default inventory
    if c.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]==0:
        items=[
            ("Turtle",56,27),("Mini Rabbit",30,27),("Parrot",20,27),
            ("Heart",21,27),("Dog",50,27),("Cat",75,27),
            ("Giraffe",20,40),("Elephant",20,40),
            ("Rabbit Big",20,42),("Camel",20,40),
            ("Mini Teddy",20,45),("Spandex Toy",9,90),
            ("Penguin",1,150),("Giant Teddy",1,1500)
        ]
        c.executemany("INSERT INTO inventory VALUES (?,?,?)", items)
    # Default stats
    if c.execute("SELECT COUNT(*) FROM stats").fetchone()[0]==0:
        c.execute("INSERT INTO stats VALUES (1,0,0,0,0,0,0,0)")
    conn.commit()
    conn.close()

def get_inventory():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM inventory")
    inv = {r[0]:{"qty":r[1],"cp":r[2]} for r in c.fetchall()}
    conn.close()
    return inv

def update_qty(name,new_qty):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE inventory SET qty=? WHERE name=?",(new_qty,name))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM stats WHERE id=1")
    s = c.fetchone()
    conn.close()
    return s

def update_stats(revenue=0,g20=0,battle=0,g150=0,g250=0,money_games=0,money_profit=0):
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
        WHERE id=1""",(revenue,g20,battle,g150,g250,money_games,money_profit))
    conn.commit()
    conn.close()

def give_prize(name):
    inv = get_inventory()
    if not name or inv.get(name,{"qty":0})["qty"]<=0:
        return None
    update_qty(name,inv[name]["qty"]-1)
    return name

def auto_27():
    inv = get_inventory()
    items=[k for k in inv if inv[k]["cp"]==27 and inv[k]["qty"]>0]
    if not items: return None
    return max(items,key=lambda x:inv[x]["qty"])

# --- Routes ---
@app.route("/", methods=["GET","POST"])
def index():
    inv = get_inventory()
    stats = get_stats()
    message=""
    selected_buttons={}

    if request.method=="POST":
        game = request.form.get("game")
        result = request.form.get("result")
        winner = request.form.get("winner")
        loser = request.form.get("loser") or auto_27()
        money_ball = request.form.get("money_ball")

        g20=battle=g150=g250=money_games=money_profit=0
        revenue=0
        prize_msg=""

        if game=="20":
            revenue=20; g20=1
            if result=="Win":
                prize = give_prize(winner)
                prize_msg=f"🎉 Winner: {prize}"
                selected_buttons["winner"]=winner
            elif result=="Lose":
                prize_msg=f"😞 Loser gets no prize"
        elif game=="Battle":
            revenue=220; battle=1
            win = give_prize(winner)
            lose = give_prize(loser)
            prize_msg=f"🏆 Winner: {win} | 🎁 Loser: {lose}"
            selected_buttons["winner"]=winner
            selected_buttons["loser"]=loser
        elif game=="150":
            revenue=150; g150=1
            if result=="Win":
                prize = give_prize("Spandex Toy")
                prize_msg=f"🎉 Winner: {prize}"
                selected_buttons["winner"]="Spandex Toy"
            else:
                lose = give_prize(loser)
                prize_msg=f"🎁 Loser got: {lose}"
                selected_buttons["loser"]=lose
        elif game=="250":
            revenue=250; g250=1
            if result=="Win":
                prize1 = give_prize(winner)
                prize2 = give_prize(loser) or auto_27()
                prize_msg=f"🎉 Winner: {prize1} + {prize2}"
                selected_buttons["winner"]=prize1
                selected_buttons["loser"]=prize2
            else:
                lose = give_prize(loser)
                prize_msg=f"🎁 Loser got: {lose}"
                selected_buttons["loser"]=lose
        elif game=="Money":
            revenue=100; money_games=1
            if money_ball=="0":
                money_profit=100; prize_msg="0 Ball: Profit +100"
            elif money_ball=="1":
                money_profit=0; prize_msg="1 Ball: Profit 0"
            elif money_ball=="2":
                money_profit=-1000; prize_msg="2 Ball: Profit -1000"
            selected_buttons["money_ball"]=money_ball

        update_stats(revenue,g20,battle,g150,g250,money_games,money_profit)
        message=prize_msg

    return render_template("index.html",inventory=inv,stats=get_stats(),
                           message=message,selected_buttons=selected_buttons)

@app.route("/report")
def report():
    stats = get_stats()
    inv = get_inventory()
    
    # Total cost of given toys
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT name, qty, cp FROM inventory")
    current_inv = c.fetchall()
    conn.close()

    # Total cost spent = initial inventory cost - current inventory cost
    initial_items = {
        "Turtle":(56,27),"Mini Rabbit":(30,27),"Parrot":(20,27),
        "Heart":(21,27),"Dog":(50,27),"Cat":(75,27),
        "Giraffe":(20,40),"Elephant":(20,40),
        "Rabbit Big":(20,42),"Camel":(20,40),
        "Mini Teddy":(20,45),"Spandex Toy":(9,90),
        "Penguin":(1,150),"Giant Teddy":(1,1500)
    }
    spent = 0
    for name, qty, cp in current_inv:
        init_qty, cost = initial_items[name]
        spent += (init_qty - qty)*cost

    total_profit = stats[1] - spent + stats[7]  # revenue - cost + money_profit

    return render_template("report.html",stats=stats,inventory=inv,profit=total_profit)

if __name__=="__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
