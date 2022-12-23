from flask import Flask
from flask import session, redirect, render_template, request
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required
import sqlite3
from datetime import datetime

# Configure application

app = Flask(__name__)
connection = sqlite3.connect("database.db", check_same_thread=False)

# Configure session to use the filesystem

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Important variables

categories = ["Sports", "Politics", "Entertainment", "Science", "Technology", "Business", "Other"]

@app.route("/")
@login_required
def index():
    
    cursor = connection.cursor()
    uid = session["user_id"]

    username = cursor.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchall()[0][0]

    polls = cursor.execute("SELECT * FROM polls WHERE creator_id = ?", (uid,)).fetchall()
    print(polls)

    return render_template("index.html", name=username, polls=polls)

@app.route("/users/<int:uid>")
def user(uid):
    
    # Get user profile
    cursor = connection.cursor()
    user = cursor.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchall()

    if len(user) != 1:
        return render_template("error.html", message="User not found")

    # Get the users polls
    polls = cursor.execute("SELECT * FROM polls WHERE creator_id = ?", (uid,)).fetchall()

    return render_template("user.html", user=user[0], polls=polls)

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.form.get("query")
        category = request.form.get("category")

        cursor = connection.cursor()
        
        if not query or query == "":
            polls = cursor.execute("SELECT * FROM polls WHERE category = ?", (category,)).fetchall()
        
        else:
            polls = cursor.execute("SELECT * FROM polls WHERE question LIKE ? AND category = ?", ('%' + query + '%', category)).fetchall()

        return render_template("search.html", polls=polls, query=query, categories=categories)
    else:
        return render_template("search.html", categories=categories)

@app.route("/delete/<int:pid>", methods=["POST"])
@login_required
def delete(pid):
    cursor = connection.cursor()
    cid = cursor.execute("SELECT creator_id FROM polls WHERE id = ?", (pid,)).fetchall()[0][0]

    if cid != session["user_id"]:
        return render_template("error.html", message="You are not the creator of this poll")

    cursor.execute("DELETE FROM polls WHERE id = ?", (pid,))
    cursor.execute("DELETE FROM poll_options WHERE poll_id = ?", (pid,))
    connection.commit()

    return redirect("/")

@app.route("/end/<int:pid>", methods=["POST"])
@login_required
def end(pid):

    cursor = connection.cursor()
    cid = cursor.execute("SELECT creator_id FROM polls WHERE id = ?", (pid,)).fetchall()[0][0]

    if cid != session["user_id"]:
        return render_template("error.html", message="You are not the creator of this poll")

    cursor.execute("UPDATE polls SET over = 1 WHERE id = ?", (pid,))
    connection.commit()

    votes = cursor.execute("SELECT * FROM poll_votes WHERE poll_id = ?", (pid,)).fetchall()
    pollname = cursor.execute("SELECT question FROM polls WHERE id = ?", (pid,)).fetchall()[0][0]

    for vote in votes:
        if vote[3] == win:
            cursor.execute("UPDATE users SET polls_won = polls_won + 1 WHERE id = ?", (vote[2],))
            cursor.execute("INSERT INTO notifications (user_id, poll_id, message) VALUES (?, ?)", (vote[2], pid, "Your prediction in poll \"" + pollname + "\" was correct!"))

    return redirect("/")

@app.route("/poll/<int:pid>", methods=["GET", "POST"])
def poll(pid):
    if request.method == "POST":
        
        if session.get("user_id") is None:
            return redirect("/login")

        option = request.form.get("option")
        uid = session["user_id"]

        # Check for client-side hacks
        if not option:
            return render_template("error.html", message="Please select an option")
        
        if option == "":
            return render_template("error.html", message="Please select an option")

        # Query database for option
        cursor = connection.cursor()
        poll_option = cursor.execute("SELECT * FROM poll_options WHERE id = ?", (option,)).fetchall()
        poll = cursor.execute("SELECT * FROM polls WHERE id = ?", (pid,)).fetchall()

        if len(poll_option) != 1:
            return render_template("error.html", message="Option not found")

        # Check if poll is still open
        if poll[0][4] < datetime.now().timestamp() or poll[0][5] == 1:
            return render_template("error.html", message="Poll is closed")
        
        # Get poll id
        pid = poll_option[0][1]

        # Check if user has already voted
        user_vote = cursor.execute("SELECT * FROM poll_votes WHERE user_id = ? AND poll_id = ?", (uid, pid)).fetchall()

        if len(user_vote) > 0:
            return render_template("error.html", message="You have already voted in this poll")

        # Insert prediction into database
        cursor.execute("INSERT INTO poll_votes (user_id, option_id, poll_id) VALUES (?, ?, ?)", (uid, option, pid))
        cursor.execute("UPDATE TABLE users SET polls_participated = polls_participated + 1 WHERE id = ?", (uid,))
        connection.commit()

        return redirect("/poll/" + str(pid))
    else:
        closed = False

        # Query database for poll
        cursor = connection.cursor()
        poll = cursor.execute("SELECT * FROM polls WHERE id = ?", (pid,)).fetchall()
        
        if len(poll) != 1:
            return render_template("error.html", message="Poll not found")
        
        # Query database for options
        options = cursor.execute("SELECT * FROM poll_options WHERE poll_id = ?", (pid,)).fetchall()

        # Check if user is the creator of the poll
        creator = (session.get("user_id") == poll[0][3])

        # Get number of votes
        votes = cursor.execute("SELECT COUNT(*) FROM poll_votes WHERE poll_id = ?", (pid,)).fetchall()[0][0]

        if poll[0][4] < datetime.now().timestamp() or poll[0][5] == 1:
            closed = True

        # See what user has voted
        if session.get("user_id") is None:
            voted = None
        else:
            voted = cursor.execute("SELECT * FROM poll_votes WHERE user_id = ? AND poll_id = ?", (session["user_id"], pid)).fetchall()
            if len(voted) > 0:
                voted = voted[0][3]
            else:
                voted = None
        
        
        return render_template("poll.html", poll=poll[0], options=options, voted=voted, votes=votes, creator=creator, closed=closed)

@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title")
        options = request.form.getlist("options")
        category = request.form.get("category")
        expires_date = request.form.get("expires_date")
        expires_time = request.form.get("expires_time")

        #convert date and time to unix timestamp
        expires = expires_date + " " + expires_time
        expires = datetime.strptime(expires, "%Y-%m-%d %H:%M")
        expires = expires.timestamp()

        # Check for client-side hacks
        if not title or not options or not category:
            return render_template("error.html", message="Please fill in all fields")
        
        if title == "" or category == "":
            return render_template("error.html", message="Please fill in all fields")
        
        if len(options) < 2:
            return render_template("error.html", message="Please add at least two options")
        
        for option in options:
            if option == "":
                return render_template("error.html", message="Please fill in all fields")
        
        # Insert poll into database
        cursor = connection.cursor()
        cursor.execute("INSERT INTO polls (question, category, expires, creator_id) VALUES (?, ?, ?, ?)", (title, category, expires, session["user_id"]))
        connection.commit()

        # Get poll id
        pid = cursor.execute("SELECT id FROM polls WHERE question = ?", (title,)).fetchall()[0][0]

        # Insert poll options into database
        for option in options:
            cursor.execute("INSERT INTO poll_options (option_text, poll_id) VALUES (?, ?)", (option, pid))
            connection.commit()
        
        return redirect("/")
    else:
        return render_template("create.html", categories=categories)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return render_template("error.html", message="Please fill in all fields")
        
        if username == "" or password == "":
            return render_template("error.html", message="Please fill in all fields")

        # Query database for username
        cursor = connection.cursor()
        rows = cursor.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchall()
        
        if len(rows) != 1 or not check_password_hash(rows[0][2], password):
            return render_template("error.html", message="Invalid username and/or password")
        
        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            return render_template("error.html", message="Please fill in all fields")
        
        if username == "" or password == "" or confirmation == "":
            return render_template("error.html", message="Please fill in all fields")
        
        if password != confirmation:
            return render_template("error.html", message="Passwords do not match")
        
        # Query database for username
        cursor = connection.cursor()
        rows = cursor.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchall()

        if len(rows) != 0:
            return render_template("error.html", message="Username already exists")
        
        # Insert user into database
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, generate_password_hash(password)))
        connection.commit()

        return redirect("/login")
    else:
        return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")