"""Video Trimmer"""

from jinja2 import StrictUndefined

from flask import Flask, render_template, request, redirect, flash, session, url_for, g

from functools import wraps

from flask_debugtoolbar import DebugToolbarExtension

from model import db, connect_to_db, User, Video, Case, UserCase, SubClip

from datetime import datetime

import boto3

import os

app = Flask(__name__)

AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
AWS_SECRET_KEY = os.environ['AWS_SECRET_KEY']

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

    # get the user id from the session
    user_id = session.get('user_id')
    # if there is an id in the session - get the user object
    if user_id:
        g.current_user = User.query.get(user_id)
    # otherwise return None
    else:
        g.current_user = None


@app.route('/')
def homepage():
    """Load homepage"""

    return render_template('index.html')

# CASES ------------------------------------------------------------------------

@app.route('/cases')
@login_required
def show_cases():
    """Show user a list of cases they are associated with"""

    # get all cases associated with the logged in user id
    cases = db.session.query(Case.case_name, 
                             UserCase.case_id).join(UserCase).filter(
                             UserCase.user_id == g.current_user.user_id).all()
    # cases = [('Us v. Them, et al', 123), ('Your mom v. All slams', 456), ('Puppies v. Kittens', 789)]
    return render_template('/cases.html', cases=cases)


@app.route('/cases/<case_id>')
@login_required
def show_case_vids(case_id):
    """Show all full videos associated with this case"""

    # vids = Video.query.filter_by(case_id=case_id).all()
    vids = db.session.query(Video.vid_url, Video.vid_name).filter(Video.case_id==case_id).all()
    this_case = Case.query.get(case_id)

    return render_template('case-vids.html', videos=vids, case=this_case)

# VIDEOS -----------------------------------------------------------------------
#sample code to upload video obj
#quinny = Video(case_id=1, vid_url='https://s3-us-west-1.amazonaws.com/videotrim/quinny.mov', added_by=1, added_at=datetime(2007, 12, 5))

@app.route('/upload-video', methods=["GET"])
@login_required
def show_upload_form():
    """Load form for user to upload new video"""

    case_id = request.args.get('case_id')

    return render_template('upload-video.html', case_id=case_id)


@app.route('/upload-video', methods=["POST"])
@login_required
def upload_video():
    """Uploads video to aws"""

    session = boto3.session.Session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    s3 = session.resource('s3')
    video_file = request.files.get("rawvid")
    video_name = video_file.filename
    s3.Bucket('videotrim').put_object(Key=video_name, Body=video_file)

    base_url = "https://s3-us-west-1.amazonaws.com/videotrim/"

    whole_url = base_url+video_name
    date_added = datetime.now()

    new_vid = Video(case_id=1, vid_name=video_name, vid_url=whole_url, added_by=g.current_user.user_id, added_at=date_added)
    db.session.add(new_vid)
    db.session.commit()

    return redirect('/cases')



# USER REGISTRATION/LOGIN-------------------------------------------------------
@app.route('/register-case', methods=["GET"])
@login_required
def show_case_reg_form():
    """Show user a form to register a new case"""

    return render_template('/register-case.html')


@app.route('/register-case', methods=["POST"])
@login_required
def register_case():
    """Adds a new case to the database"""

    case_name = request.form.get('case_name')
    other_users = request.form.get('user-list')
    current_user = g.current_user.email

    #instantiate a new case in the db
    new_case = Case(case_name=case_name, owner_id=g.current_user.user_id)
    #prime and commit the case to the db
    db.session.add(new_case)
    db.session.commit()

    # now add the userCase associations
    user_emails = other_users.split(", ")
    user_emails.append(current_user)

    #get the newly created case obj so we can use it to associate people with it
    this_case = Case.query.filter_by(case_name=case_name).first()

    for email in user_emails:
        #check if a user with that email exists already
        #gets the user object for that email address
        user_check = User.query.filter_by(email=email).first()

        # if user already exists associate the user with the new case
        if user_check is None:
            #if the user is not registered - add them to the database
            #they can add their password and name when they officially register
            user = User(email=email)
            #prime user to be added to db
            db.session.add(user)
            #commit user to db
            db.session.commit()
            user_check = User.query.filter_by(email=email).first()

        #create an association in the usercases table
        user_case = UserCase(case_id=this_case.case_id, user_id=user_check.user_id)
        db.session.add(user_case)
        db.session.commit()

    return redirect('/cases')


@app.route('/login', methods=["POST"])
def handle_login():
    """Check is user is registered"""

    # get email and password info
    email = request.form.get("email")
    password = request.form.get("password")

    #check if user is in db
    user_check = User.query.filter_by(email=email).first()

    # if user already exists check the password
    if user_check:
        if user_check.password == password:
            #set flash message telling them login successful
            flash("You have successfully logged in")
            #add user's ID num to the session
            session['user_id'] = user_check.user_id
            #send them to their own page
            return redirect('/cases')
        else:
            # tell them the password doesn't match
            flash("That password does not match our records.")
            # redirect back to login so they can try again
            return redirect("/")
    else:
        flash("No user is registered with that email. Please register.")
        return redirect('/register')


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

    #check if user exists in db
    user_check = User.query.filter_by(email=email).first()
    if user_check:
        if user_check.password != None:
            #let us know user exists already and redirect to homepage to login
            flash('You have already registered. Please log in.')
        else:
            user_check.password = password
            user_check.fname = fname
            user_check.lname = lname

            db.session.commit()
            flash('You have successfully registered. Please log in.')

    else:
        #create user
        user = User(email=email,
                    password=password,
                    fname=fname,
                    lname=lname)
        #prime user to be added to db
        db.session.add(user)
        #commit user to db
        db.session.commit()
        flash('You have successfully registered. Please log in.')
    return redirect("/")


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the
    # point that we invoke the DebugToolbarExtension
    app.debug = True
    app.jinja_env.auto_reload = app.debug  # make sure templates, etc. are not cached in debug mode

    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)

    app.run(port=5000, host='0.0.0.0')
