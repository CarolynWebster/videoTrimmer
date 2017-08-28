"""User functions for video trimmer"""

from model import Case, db, UserCase, User

from flask import session, flash

from gmail import send_email


def validate_usercase(case_id, user_id):
    """Validate is user is permitted access to a specifc case"""

    # check if the usercase exists already
    case_user_check = db.session.query(UserCase).filter(UserCase.case_id == case_id,
                                                     UserCase.user_id == user_id).first()
    return case_user_check


def update_usercase(case_id, user_id):
    """Checks for user in database and adds if new - returns new usercase obj"""

    # check if the usercase exists already
    case_user_check = validate_usercase(case_id, user_id)

    # if the relationship doesn't exist - create it
    if case_user_check is None:
        #create an association in the usercases table
        user_case = UserCase(case_id=case_id, user_id=user_id)
        user = User.query.get(user_id)
        send_email(user.email, None, "add_to_case")
        db.session.add(user_case)
        db.session.commit()

    # return case_user_check so we can determine if the association is new or not
    # if case_user_check is None - we can use that in the add-users route
    return case_user_check


def create_user(user_check, email, fname, lname, password):
    """Updates an invited but unregistered user or creates a new one

    Takes in a db user object - if it is none create a new user instance in the db
    or update an existing db user with a name and password.

    """

    # if the user has not been added to an existing case - create new user
    if user_check is None:
        #create user
        user = User(email=email,
                    password=password,
                    fname=fname,
                    lname=lname)
        # prime user to be added to db
        db.session.add(user)
        # commit user to db
        db.session.commit()
        flash('You have successfully registered.')
        # add user's ID num to the session
        session['user_id'] = user.user_id
    # if the user has been invited, but hasn't yet registered - update user in db
    else:
        if user_check.password is not None:
            #let us know user exists already and redirect to homepage to login
            flash('You have already registered. Please log in.')
        else:
            user_check.password = password
            user_check.fname = fname
            user_check.lname = lname

            db.session.commit()

            flash('You have successfully registered.')
            session['user_id'] = user_check.user_id



def get_user_by_email(email):
    """Creates new user and returns new or exisiting user object"""

    #check if a user with that email exists already
    #gets the user object for that email address
    user_check = db.session.query(User).filter(User.email == email).first()

    # if user already exists associate the user with the new case
    if user_check is None:
        #if the user is not registered - add them to the database
        #they can add their password and name when they officially register
        # make all emails lowercase to reduce doubled entries
        user_check = User(email=email.lower())
        # send email to notify user they have been added
        send_email(email, None, "new_user")
        #prime user to be added to db
        db.session.add(user_check)
        #commit user to db
        db.session.commit()

    return user_check
