"""Models and database functions for video trimmer."""

from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

# This is the connection to the PostgreSQL database; we're getting this through
# the Flask-SQLAlchemy helper library. On this, we can find the `session`
# object, where we do most of our interactions (like committing, etc.)

db = SQLAlchemy()


##############################################################################
# Model definitions

class User(db.Model):
    """User info"""

    __tablename__ = "users"

    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    email = db.Column(db.String(64), nullable=False)
    password = db.Column(db.String(64))
    fname = db.Column(db.String(50))
    lname = db.Column(db.String(50))

    def __repr__(self):
        """Provide userful user information"""

        return "<User user_id={} email={} name={} {}>".format(self.user_id, 
                                                              self.email,
                                                              self.fname,
                                                              self.lname)


class Case(db.Model):
    """Case info"""

    __tablename__ = "cases"

    case_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    owner_id = db.Column(db.Integer, nullable=True)
    case_name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        """Provide userful user information"""

        return "<Case case_id={} name={}>".format(self.case_id, self.case_name)


class UserCase(db.Model):
    """Links users and their associated cases"""

    __tablename__ = "usercases"

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.case_id'), nullable=False)

    case = db.relationship("Case", backref='userCases')
    user = db.relationship("User", backref='userCases')

    def __repr__(self):
        """Provide case/user connection"""

        return "<UserCase case_id={} user_id={}>".format(self.case_id,
                                                         self.user_id)


class Video(db.Model):
    """A full video"""

    __tablename__ = "videos"

    vid_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    vid_name = db.Column(db.String(75), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.case_id'), nullable=False)
    vid_url = db.Column(db.String(100), nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    added_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        """useful video info"""

        return "<Video vid_id={} case_id={} url={}".format(self.vid_id,
                                                           self.case_id,
                                                           self.vid_url)


class SubClip(db.Model):
    """A clip created from a full video"""

    __tablename__ = "clips"

    clip_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    vid_id = db.Column(db.Integer, db.ForeignKey('videos.vid_id'), nullable=False)
    start_at = db.Column(db.String(20))
    end_at = db.Column(db.String(20))
    clip_url = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)


##############################################################################
# Helper functions

def connect_to_db(app):
    """Connect the database to our Flask app."""

    # Configure to use our PstgreSQL database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///vidtrimmer'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.app = app
    db.init_app(app)


if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app
    connect_to_db(app)
    print "Connected to DB."