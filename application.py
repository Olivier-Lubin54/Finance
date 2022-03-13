import os
import datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    holdings = []
    rows = db.excute(" SELECT symbol, SUM(shares) as c_shares FROM transactions WHERE user_id = ? AND shares > 0; ", session["user_id"])
    crows = db.execute(" SELECT cash FROM user WHERE id = ?", session["user_id"])
    cash = usd(crows[0]["cash"])
    for row in rows: 
        stock = lookup(row["symbol"])
        holdings.append({
            "symbol": stock["symbol"]
            "name": stock["name"] 
            "shares": row["shares"]
            "price": stock["price"]
            "total": row[shares] * stock["price"]
            })
        assets = usd(cash + (row[shares] * stock["price"]))
    return render_template("index.html", holdings=holdings, cash=cash, assets = assets )


@app.route("/buy", methods=["GET", "POST"]) 
@login_required
def buy():
    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("must provide a company symbol", 403)

        if not request.form.get("shares"):
            return apology("must provide total shares to purchase", 403)

        symbol = request.form.get("symbol")
        shares = (request.form.get("shares"))
        stock = lookup(symbol)

        if not shares.isdigit():
            return apology("invalid amount of shares", 403)
        shares = float(shares)
        if not stock:
            return apology("must provide a company symbol", 403)

        cash_obj = db.execute("SELECT cash FROM users WHERE id= ?", session["user_id"] )

        cash = float(cash_obj[0]["cash"])

        #if cash < (stock["price"] * shares) :
        if cash < (56 * shares):
            return apology("insufficient funds", 403)

        p_price = usd(stock["price"] * shares)

        new_cash = usd(cash - p_price)



        db.execute("UPDATE users SET cash = ? WHERE id= ?", new_cash, session["user_id"] )
        print("before update")

        response = db.execute("UPDATE holdings SET shares = (? + (SELECT shares FROM holdings WHERE symbol = ? AND user = ?) ) WHERE symbol = ? AND user = ? ", shares, symbol, session["user_id"], symbol, session["user_id"] )

        if response == 0:
            #did not find
            db.execute("INSERT INTO holdings (symbol,shares,user) VALUES (?,?,?)", symbol, shares, session["user_id"])


        trans_time = datetime.datetime.now()

        print(trans_time)

        db.execute("INSERT INTO transactions (symbol,price,datetime,shares,type,user) VALUES (?,?,?,?,?,?)", symbol, p_price, trans_time, shares, "buy", session["user_id"])

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    transactions = db.execute(" SELECT symbol, price, datetime, shares, type FROM transactions WHERE user_id = ?"; user_id)
    return render_template("history.html", transactions=transactions)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":


        if not request.form.get("username"):
            return apology("must provide username", 403)

        if not request.form.get("password") or not request.form.get("confirmation")  :
            return apology("must provide password", 403)

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) != 0:

             return apology("this is an existing user", 403)

        if request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 403)

        else:
            hash1 = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users (username,hash) VALUES(?, ?)", request.form.get("username"), hash1)

            rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
            session["user_id"] = rows[0]["id"]

            return redirect("/")
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Invalid username and/or password!!!", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide stock symbol", 403)
        else:
            symbol = request.form.get("symbol")
            stock_data = lookup(symbol)
            if stock_data is None:
              return apology("incorrect symbol", 403)
            else:
                return render_template("quoted.html", stock_data=stock_data)
    else:
        return render_template("quote.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide a company symbol", 403)

        if not request.form.get("shares"):
            return apology("must provide total shares to sell", 403)

        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        stock = lookup(symbol)

        print(shares)

        if not shares.isdigit():
            return apology("invalid amount of shares", 403)
        if stock == None:
            return apology("must provide a company symbol", 403)

        cash_obj = db.execute("SELECT cash FROM users WHERE id= ?", session["user_id"] )

        cash = float(cash_obj[0]["cash"])
        
        if int(shares) <= 0:
            return apology("invalid amount of shares", 403)


        c_shares = db.execute("SELECT shares FROM holdings WHERE symbol = ? AND user = ? ", symbol, session["user_id"])

        #if c_shares == shares:
        price = stock["price"]
        new_cash = usd(cash + (price * float(shares)))
        
        

        db.execute("UPDATE users SET cash = ? WHERE id= ?", new_cash, session["user_id"] )

        #h_shares = db.execute("UPDATE holdings SET shares = ((SELECT shares FROM holdings WHERE symbol = ? AND user = ?) ) WHERE symbol = ? AND user = ? ", symbol, session["user_id"], shares, symbol, session["user_id"] )


        db.execute("UPDATE holdings SET shares = shares - ? WHERE symbol = ? AND user = ?", shares, symbol, session["user_id"])

        trans_time = datetime.datetime.now()


        db.execute("INSERT INTO transactions (symbol,price,datetime,shares,type,user) VALUES (?,?,?,?,?,?)", symbol, price, trans_time, shares, "sell", session["user_id"])

        return redirect("/")

    else:
        return render_template("sell.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
