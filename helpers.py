from functools import wraps
from flask import redirect, session

def login_required(f):
    """
    Decorate routes to require login.
    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def calculate_level(xp):
    
    # Calculate level from XP value

    level = 0
    
    while xp >= 0:
        level += 1
        xp -= 200 * level
    
    return level

def xp_until_next_level(xp):
    
    # Calculate XP until next level
    
    level = calculate_level(xp)
    xp_until_next_level = 200 * level - xp
    
    return xp_until_next_level