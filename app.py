from flask import Flask
from flask import session, redirect, render_template, request
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, calculate_level, xp_until_next_level
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

    (name, correct_guesses) = cursor.execute("SELECT username, correct_guesses FROM users WHERE id = ?", (uid,)).fetchall()[0]
    
    # Get user's level and XP

    xp = correct_guesses*100
    level = calculate_level(xp)

    # Get XP until next level

    xp_need = xp_until_next_level(xp)
    polls_needed = int(xp_need/100)

    # get the users polls

    polls = cursor.execute("SELECT id, question, category FROM polls WHERE creator_id = ?", (uid,)).fetchall()

    # get the users notifications

    notifications = cursor.execute("SELECT poll_id, message FROM notifications WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall()


    return render_template("index.html", name=name, level=level, xp=xp, polls_needed=polls_needed, polls=polls, notifications=notifications, uid=uid)

@app.route("/users/<int:uid>")
def user(uid):
    
    cursor = connection.cursor()
    user_id = session.get("user_id")
    
    # Get user profile
    
    try:
        [name, completed, participated] = cursor.execute("SELECT username, correct_guesses, polls_participated FROM users WHERE id = ?", (uid,)).fetchall()[0]
    except IndexError:
        return render_template("error.html", message="User not found")
    
    level = calculate_level(completed*100)
    xp = completed*100

    # Get the users polls

    polls = cursor.execute("SELECT id, question, category FROM polls WHERE creator_id = ?", (uid,)).fetchall()

    return render_template("user.html", user_id=user_id, name=name, completed=completed, participated=participated, xp=xp , polls=polls, level=level)

@app.route("/search", methods=["GET", "POST"])
def search():
        query = request.args.get("query")
        category = request.args.get("category")

        print (query, category)
        cursor = connection.cursor()
        
        if (not query or query == "") and category:
            polls = cursor.execute("SELECT id, question, category FROM polls WHERE category = ? ORDER BY id DESC", (category,)).fetchall()

        elif query:
            polls = cursor.execute("SELECT id, question, category FROM polls WHERE question LIKE ? AND category = ? ORDER BY id DESC", (f'%{query}%', category)).fetchall()
        else :
            return render_template("search.html", polls=[], query=query, categories=categories, uid=session.get("user_id"))
        
        return render_template("search.html", polls=polls, query=query, categories=categories, uid=session.get("user_id"))

@app.route("/delete/<int:pid>", methods=["POST"])
@login_required
def delete(pid):
    cursor = connection.cursor()

    # Check user is creator of poll

    creator_id = cursor.execute("SELECT creator_id FROM polls WHERE id = ?", (pid,)).fetchall()[0][0]

    if creator_id != session["user_id"]:
        return render_template("error.html", message="You are not the creator of this poll")

    votes = cursor.execute("SELECT user_id FROM poll_votes WHERE poll_id = ?", (pid,)).fetchall()
    poll_name = cursor.execute("SELECT question FROM polls WHERE id = ?", (pid,)).fetchall()[0][0]

    # Delete poll

    cursor.execute("DELETE FROM polls WHERE id = ?", (pid,))
    cursor.execute("DELETE FROM poll_options WHERE poll_id = ?", (pid,))
    
    # Send notification to all users who participated in the poll

    for vote in votes:
        cursor.execute("INSERT INTO notifications (user_id, message, poll_id) VALUES (?, ?, ?)", (vote[0], f'Poll "{poll_name}" has been deleted', pid, ))

    connection.commit()

    return redirect("/")

@app.route("/end/<int:pid>", methods=["POST"])
@login_required
def end(pid):
    
    cursor = connection.cursor()
    win = int(request.form.get("win"))

    # Check user is creator of poll

    creator_id = cursor.execute("SELECT creator_id FROM polls WHERE id = ?", (pid,)).fetchall()[0][0]

    if creator_id != session["user_id"]:
        return render_template("error.html", message="You are not the creator of this poll")

    # End poll

    cursor.execute("UPDATE polls SET over = 1 WHERE id = ?", (pid,))

    # Get poll votes and poll name

    votes = cursor.execute("SELECT user_id, option_id FROM poll_votes WHERE poll_id = ?", (pid,)).fetchall()
    poll_name = cursor.execute("SELECT question FROM polls WHERE id = ?", (pid,)).fetchall()[0][0]

    # Send notifications to users who voted

    for (user_id, option_id) in votes:
        cursor.execute("UPDATE users SET polls_participated = correct_guesses + 1 WHERE id = ?", (user_id,))
        
        if option_id == win:
            cursor.execute("UPDATE users SET correct_guesses = correct_guesses + 1 WHERE id = ?", (user_id,))
            cursor.execute("INSERT INTO notifications (user_id, poll_id, message) VALUES (?, ?, ?)", (user_id, pid, f'Your prediction in poll "{poll_name}" was correct!'))
        
        else:
            cursor.execute("INSERT INTO notifications (user_id, poll_id, message) VALUES (?, ?, ?)", (user_id, pid, f'Your prediction in poll "{poll_name}" was incorrect!'))
    
    connection.commit()
    return redirect("/")

@app.route("/poll/<int:pid>", methods=["GET", "POST"])
def poll(pid):
    uid = session.get("user_id")
    
    if request.method == "POST":
        
        if uid is None:
            return redirect("/login")

        option = request.form.get("option")

        # Check for client-side hacks
        
        if not option:
            return render_template("error.html", message="Please select an option")
        
        if option == "":
            return render_template("error.html", message="Please select an option")

        # Query database for option
        
        cursor = connection.cursor()
        option_exists = cursor.execute("SELECT EXISTS(SELECT id FROM poll_options WHERE id = ?)", (option,)).fetchall()
        
        # Check if poll exists

        try:
            (expires, over) = cursor.execute("SELECT expires, over FROM polls WHERE id = ?", (pid,)).fetchall()[0]
        except IndexError:
            return render_template("error.html", message="Poll does not exist")

        # Check if poll is still open
        
        if expires < datetime.now().timestamp() or over == 1:
            return render_template("error.html", message="Poll is closed")

        # Check user is not creator of poll

        creator_id = cursor.execute("SELECT creator_id FROM polls WHERE id = ?", (pid,)).fetchall()[0][0]
        if creator_id == uid:
            return render_template("error.html", message="You are the creator of this poll")

        # Check if user has already voted

        voted = cursor.execute("SELECT EXISTS(SELECT id FROM poll_votes WHERE user_id = ? AND poll_id = ?)", (uid, pid)).fetchall()

        if voted == 0:
            return render_template("error.html", message="You have already voted in this poll")

        # Insert prediction into database

        cursor.execute("INSERT INTO poll_votes (user_id, option_id, poll_id) VALUES (?, ?, ?)", (uid, option, pid))
        connection.commit()

        return redirect("/poll/" + str(pid))
    else:
        closed = False

        # Query database for poll
        
        cursor = connection.cursor()
        
        # Check if poll exists
        
        try:
            (id, question, category, creator_id, expires, over) = cursor.execute("SELECT id, question, category, creator_id, expires, over FROM polls WHERE id = ?", (pid,)).fetchall()[0]
        except IndexError:
            return render_template("error.html", message="Poll not found, it may have been deleted. If not, check the URL and try again.")
        
        # Query database for options
        
        options = cursor.execute("SELECT id, option_text FROM poll_options WHERE poll_id = ?", (pid,)).fetchall()

        # Check if user is the creator of the poll
        
        creator = (uid == creator_id)

        # Get number of votes

        votes = cursor.execute("SELECT COUNT(*) FROM poll_votes WHERE poll_id = ?", (pid,)).fetchall()[0][0]

        if expires < datetime.now().timestamp() or over == 1:
            closed = True

        # See what user has voted

        if uid is None:
            vote = None
        else:
            try:
                vote = cursor.execute("SELECT id FROM poll_votes WHERE user_id = ? AND poll_id = ?", (uid, pid)).fetchall()[0][0]
            except IndexError:
                vote = None
        
        
        return render_template("poll.html", poll=[id, question, category], options=options, voted=vote, votes=votes, creator=creator, closed=closed)

@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        
        title = request.form.get("title")
        category = request.form.get("category")
        options = request.form.getlist("options")
        expires_date = request.form.get("expires_date")
        expires_time = request.form.get("expires_time")

        #convert date and time to unix timestamp

        try:
            expires = expires_date + " " + expires_time
            expires = datetime.strptime(expires, "%Y-%m-%d %H:%M")
            expires = expires.timestamp()
        except ValueError:
            return render_template("error.html", message="Please enter a valid date and time")

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

        cursor = connection.cursor()
        username = request.form.get("username")
        password = request.form.get("password")

        # Check for client-side hacks

        if not username or not password:
            return render_template("error.html", message="Please fill in all fields")
        
        if username == "" or password == "":
            return render_template("error.html", message="Please fill in all fields")

        # Query database for username
        
        user_exists = cursor.execute("SELECT EXISTS(SELECT id FROM users WHERE username = ?)", (username,)).fetchall()

        if user_exists[0][0] == 0:
            return render_template("error.html", message="User does not exist")

        (id, hash) = cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,)).fetchall()[0]
        
        if not check_password_hash(hash, password):
            return render_template("error.html", message="Invalid username and/or password")
        
        # Remember which user has logged in

        session["user_id"] = id

        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Check for client-side hacks

        if not username or not password or not confirmation:
            return render_template("error.html", message="Please fill in all fields")
        
        if username == "" or password == "" or confirmation == "":
            return render_template("error.html", message="Please fill in all fields")
        
        if password != confirmation:
            return render_template("error.html", message="Passwords do not match")
        
        # Query database for username
       
        cursor = connection.cursor()
        user_exists = cursor.execute("SELECT EXISTS (SELECT username FROM users WHERE username = ?)", (username,)).fetchall()

        if user_exists == 1:
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