"""Models and database functions for video trimmer."""

from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# This is the connection to the PostgreSQL database; we're getting this through
# the Flask-SQLAlchemy helper library. On this, we can find the `session`
# object, where we do most of our interactions (like committing, etc.)

db = SQLAlchemy()

engine = create_engine('postgresql:///vidtrimmer')

db_session = scoped_session(sessionmaker(bind=engine))


##############################################################################
# Model definitions

class User(db.Model):
    """User info"""

    __tablename__ = "users"

    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    email = db.Column(db.String(64), nullable=False)
    password = db.Column(db.String(64))
    fname = db.Column(db.String(50), default='')
    lname = db.Column(db.String(50), default='Not registered')

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

    users = db.relationship('User', secondary="usercases", backref="cases")

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
    # vid_url = db.Column(db.String(100), nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    added_at = db.Column(db.DateTime, nullable=False)
    vid_status = db.Column(db.String(10), default='Processing')
    recorded_at = db.Column(db.DateTime)
    deponent = db.Column(db.String(50))

    case = db.relationship("Case", backref="videos")

    def __repr__(self):
        """useful video info"""

        return "<Video vid_id={} case_id={} name={}>".format(self.vid_id,
                                                           self.case_id,
                                                           self.vid_name)


class Clip(db.Model):
    """A clip created from a full video"""

    __tablename__ = "clips"

    clip_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    vid_id = db.Column(db.Integer, db.ForeignKey('videos.vid_id'), nullable=False)
    clip_name = db.Column(db.String(100), nullable=False)
    start_at = db.Column(db.String(20))
    end_at = db.Column(db.String(20))
    # clip_url = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    clip_status = db.Column(db.String(10), default='Processing')

    user = db.relationship("User", backref="subclips")
    video = db.relationship("Video", backref="subclips")

    def __repr__(self):
        """useful clip info"""

        return "<Clip clip_id={} clip_name={}>".format(self.clip_id,
                                                          self.clip_name)


class Tag(db.Model):
    """A tag for clips"""

    __tablename__ = "tags"

    tag_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    tag_name = db.Column(db.String(30), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.case_id'))

    case = db.relationship('Case', backref="tags")
    clips = db.relationship('Clip', secondary="cliptags", backref="tags")

    def __repr__(self):
        """useful tag info"""

        return "<Tag tag_id={} tag_name={}>".format(self.tag_id, self.tag_name)


class ClipTag(db.Model):
    """Tags associated with specific subclips"""

    __tablename__ = "cliptags"

    cliptag_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.tag_id'))
    clip_id = db.Column(db.Integer, db.ForeignKey('clips.clip_id'))

    clip = db.relationship('Clip', backref="clip_tags")
    tag = db.relationship('Tag', backref="clip_tags")

    def __repr__(self):
        """useful cliptag info"""

        return "<ClipTag cliptag_id={} clip_id ={}>".format(self.cliptag_id,
                                                                self.clip_id)

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