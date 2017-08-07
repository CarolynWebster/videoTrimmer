"""Video Trimmer"""

from jinja2 import StrictUndefined

from flask import Flask, render_template, request, redirect, flash, session, url_for, g

from functools import wraps

from flask_debugtoolbar import DebugToolbarExtension

app = Flask(__name__)

# Required to use Flask sessions and the debug toolbar
app.secret_key = "ABC"

app.jinja_env.undefined = StrictUndefined


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.current_user is None:
            # if the user isn't logged in - reroute to homepage/login page
            flash('You have to be logged in to see that content')
            return redirect(url_for('homepage', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def pre_process_all_requests():
    """Setup the request context"""

    user_email = session.get('user_email')
    g.current_user = user_email

    # user_id = session.get('user_id')
    # if user_id:
    #     g.current_user = User.query.get(user_id)
    # else:
    #     g.current_user = None

@app.route('/')
def homepage():
    """Load homepage"""

    return render_template('index.html')


@app.route('/cases')
@login_required
def show_cases():
    """Show user a list of cases they are associated with"""

    cases = [('Us v. Them, et al', 123), ('Your mom v. All slams', 456), ('Puppies v. Kittens', 789)]
    return render_template('/cases.html', cases=cases)

@app.route('/login', methods=["POST"])
def handle_login():
    """Check is user is registered"""

    # get email and password info
    email = request.form.get("email")
    password = request.form.get("password")

    #TEMP - add user to session - will add DB check later
    session['user_email'] = email

    #set flash message telling them login successful
    flash("You have successfully logged in")

    return redirect('/cases')

    #check if user is in db
    #user_check = User.query.filter_by(email=email).first()

    #if user already exists check the password
    # if user_check:
    #     if user_check.password == password:
    #         #set flash message telling them login successful
    #         flash("You have successfully logged in")
    #         #add user's email to the session
    #         session['user_email'] = email
    #         #get the url for that user's info
    #         user_url = "/users/" + str(user_check.user_id)
    #         #send them to their own page
    #         return redirect(user_url)
    #     else:
    #         # tell them the password doesn't match
    #         flash("That password does not match our records.")
    #         # redirect back to login so they can try again
    #         return redirect("/login")
    # else:
    #     flash("No user is registered with that email. Please register.")
    #     return redirect('/register')


@app.route('/logout')
def logout_user():
    """Logs a user out"""

    # clear email from the session
    session.clear()

    # tell the user they are logged out
    flash("You have successfully logged out")

    return redirect('/')


@app.route('/register', methods=["GET"])
def show_reg_form():
    """Shows new user a registration form"""

    return render_template('registration.html')

@app.route('/register', methods=['POST'])
def register_user():
    """Checks db for user and adds user if new"""

    fname = request.form.get('fname')
    lname = request.form.get('lname')
    email = request.form.get("email")
    password = request.form.get("password")

    # will add db portion later
    return redirect('/')
    # return redirect('/login')

    #check if user exists in db
    # user_check = User.query.filter_by(email=email).first()
    # if user_check:
    #     #let us know user exists already
    #     flash('You have already registered. Please log in.')
    #     return redirect('/login')
    # else:
    #     #create user
    #     user = User(email=email,
    #                 password=password,
    #                 age=age,
    #                 zipcode=zipcode)
    #     #prime user to be added to db
    #     db.session.add(user)
    #     #commit user to db
    #     db.session.commit()

    #     return redirect("/")


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the
    # point that we invoke the DebugToolbarExtension
    app.debug = True
    app.jinja_env.auto_reload = app.debug  # make sure templates, etc. are not cached in debug mode

    #connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)

    app.run(port=5000, host='0.0.0.0')
