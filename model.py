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
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    case_id = db.Column(db.Integer, db.ForeignKey('cases.case_id'))

    case = db.relationship("Case", backref='userCases')
    user = db.relationship("User", backref='userCases')

    def __repr__(self):
        """Provide case/user connection"""

        return "<UserCase case_id={} user_id={}>".format(self.case_id,
                                                         self.user_id)


class Zip(db.Model):
    """A zip file of clips"""

    __tablename__ = "zips"

    zip_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    zip_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    vid_id = db.Column(db.Integer, db.ForeignKey('videos.vid_id'))

    user = db.relationship("User", backref="zips")

    def __repr__(self):
        """useful zip info"""

        return "<Zip zip_id={} name={}>".format(self.zip_id, self.zip_name)

class Video(db.Model):
    """A full video"""

    __tablename__ = "videos"

    vid_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    vid_name = db.Column(db.String(75), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.case_id'))
    # vid_url = db.Column(db.String(100), nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    added_at = db.Column(db.DateTime, nullable=False)
    vid_status = db.Column(db.String(10), default='Processing')
    recorded_at = db.Column(db.DateTime)
    deponent = db.Column(db.String(50))

    case = db.relationship("Case", backref="videos")
    clips = db.relationship("Clip", backref="video", cascade="delete")
    transcript = db.relationship("Transcript", backref="video", cascade="delete")

    def __repr__(self):
        """useful video info"""

        return "<Video vid_id={} case_id={} name={}>".format(self.vid_id,
                                                           self.case_id,
                                                           self.vid_name)


class Clip(db.Model):
    """A clip created from a full video"""

    __tablename__ = "clips"

    clip_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    vid_id = db.Column(db.Integer, db.ForeignKey('videos.vid_id'))
    clip_name = db.Column(db.String(100), nullable=False)
    start_pl = db.Column(db.String(10))
    end_pl = db.Column(db.String(10))
    start_at = db.Column(db.String(20))
    end_at = db.Column(db.String(20))
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    clip_status = db.Column(db.String(10), default='Processing')

    user = db.relationship("User", backref="clips")
    # video = db.relationship("Video", backref="clips")
    cliptags = db.relationship('ClipTag', cascade="delete")

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
    cliptags = db.relationship('ClipTag', cascade="delete")

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


class Transcript(db.Model):
    """Holds a full transcript associated with a video"""

    __tablename__ = "transcripts"

    t_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    vid_id = vid_id = db.Column(db.Integer, db.ForeignKey('videos.vid_id'))
    text = db.Column(db.Text, nullable=False)

    # video = db.relationship("Video", backref="transcript")

    def __repr__(self):
        """useful transcript info"""

        return "<Transcript t_id={} vid_id ={}>".format(self.t_id, self.vid_id)


class TextPull(db.Model):

    __tablename__ = "textpulls"

    tp_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    clip_id = db.Column(db.Integer, db.ForeignKey('clips.clip_id'))
    pull_text = db.Column(db.Text, nullable=False)

    clip = db.relationship('Clip', backref="text_pulls")

    def __repr__(self):
        """useful textpull info"""

        return "TextPull tp_id={} clip_name ={}>".format(self.tp_id, self.clip_id)


def example_data():
    """Create some sample data."""

    # In case this is run more than once, empty out existing data
    Clip.query.delete()
    UserCase.query.delete()
    Video.query.delete()
    Case.query.delete()
    User.query.delete()

    bob = User(email="bob@gmail.com", password="123", fname="Bob", lname="Bobson")
    sally = User(email="sally@gmail.com", password="123", fname="Sally", lname="Sallison")
    jane = User(email="jane@gmail.com", password="123", fname="Jane", lname="Janey")

    db.session.add_all([bob, sally, jane])
    db.session.commit()

    case1 = Case(owner_id=bob.user_id, case_name="Us v. Them")
    case2 = Case(owner_id=bob.user_id, case_name="Cats v. Dogs")
    case3 = Case(owner_id=sally.user_id, case_name="Sanity v. Testing")

    db.session.add_all([case1, case2, case3])
    db.session.commit()

    usercase1 = UserCase(case_id=case1.case_id, user_id=sally.user_id)
    usercase2 = UserCase(case_id=case1.case_id, user_id=jane.user_id)
    usercase3 = UserCase(case_id=case2.case_id, user_id=sally.user_id)

    db.session.add_all([usercase1, usercase2, usercase3])
    db.session.commit()

    vid1 = Video(case_id=case1.case_id, vid_name="Test Video 1", added_by=bob.user_id, added_at=datetime.now(), vid_status='Ready', deponent="Sierra Chappell")
    vid2 = Video(case_id=case2.case_id, vid_name="Test Video 2", added_by=bob.user_id, added_at=datetime.now(), vid_status='Ready', deponent="Rose Johns")
    vid3 = Video(case_id=case3.case_id, vid_name="Test Video 3", added_by=sally.user_id, added_at=datetime.now(), vid_status='Ready', deponent="Kristen Stotts")

    db.session.add_all([vid1, vid2, vid3])
    db.session.commit()

    clip1 = Clip(vid_id=vid1.vid_id, clip_name="Test Clip 1", created_by=jane.user_id, clip_status='Ready')
    clip2 = Clip(vid_id=vid2.vid_id, clip_name="Test Clip 2", created_by=bob.user_id, clip_status='Ready')
    clip3 = Clip(vid_id=vid3.vid_id, clip_name="Test Clip 3", created_by=sally.user_id, clip_status='Ready')

    db.session.add_all([clip1, clip2, clip3])
    db.session.commit()

    tag1 = Tag(case_id=case1.case_id, tag_name="Awesome")
    tag2 = Tag(case_id=case2.case_id, tag_name="Cats")

    db.session.add_all([tag1, tag2])
    db.session.commit()

##############################################################################
# Helper functions

def connect_to_db(app, db_uri="postgresql:///vidtrimmer"):
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.app = app
    db.init_app(app)


if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app
    connect_to_db(app)
    print "Connected to DB."