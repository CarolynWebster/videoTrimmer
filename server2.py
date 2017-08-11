"""Video Trimmer"""
import imageio
imageio.plugins.ffmpeg.download()

from moviepy.editor import *

from jinja2 import StrictUndefined

from flask import Flask, render_template, request, redirect, flash, session, url_for, g

from functools import wraps

from flask_debugtoolbar import DebugToolbarExtension

from model import db, connect_to_db, User, Video, Case, UserCase, SubClip

from datetime import datetime

import boto3

import os

import threading

app = Flask(__name__)

AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
AWS_SECRET_KEY = os.environ['AWS_SECRET_KEY']

#aws bucket name
BUCKET_NAME = 'videotrim'


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
    vids = db.session.query(Video.vid_name, Video.vid_id).filter(Video.case_id==case_id).all()
    this_case = Case.query.get(case_id)

    return render_template('case-vids.html', videos=vids, case=this_case)

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

    print "\n\n\n\n\n\n\n STARTED \n\n\n\n\n\n\n"
    case_id = request.form.get('case_id')
    video_file = request.files.get("rawvid")
    video_name = video_file.filename

    upload = threading.Thread(target=upload_aws_db, args=(video_file, video_name)).start()

    return redirect('/cases/'+str(case_id))

def upload_aws_db(video_file, video_name):
    """Handles upload to aws and addition to the db"""

    video_file = video_file.read()
    video_name = video_name

    session = boto3.session.Session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    s3 = session.resource('s3')
    print "\n\n\n\n\n\n\n THREADING MOTHER FUCKER", BUCKET_NAME, video_name, "\n\n\n\n\n\n\n"
    #print video_file.closed
    s3.Bucket(BUCKET_NAME).put_object(Key=video_name, Body=video_file)
    print "\n\n\n\nfinished\n\n\n\n"
    date_added = datetime.now()

    #TO DO - check if video url exists already

    new_vid = Video(case_id=case_id, vid_name=video_name, 
                    added_by=g.current_user.user_id, added_at=date_added)
    db.session.add(new_vid)
    db.session.commit()

    redir_url = '/cases/{}'.format(case_id)
    print "\n\n\n\n\n\n\n FILE UPLOAD enDeD \n\n\n\n\n\n\n"

@app.route('/show-video/<vid_id>')
@login_required
def show_video(vid_id):
    vid_to_trim = Video.query.get(vid_id)
    vid_name = vid_to_trim.vid_name

    #establish connection with s3
    s3C = boto3.client('s3')

    url = s3C.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': BUCKET_NAME,
            'Key': vid_name
        }
    )

    return render_template('show-video.html', vid_id=vid_id, orig_vid=vid_name, vid_url=url)



# MAKING CLIPS -----------------------------------------------------------------
@app.route('/trim-video/<vid_id>')
@login_required
def trim_video(vid_id):
    vid_to_trim = Video.query.get(vid_id)
    vid_name = vid_to_trim.vid_name

    #establish connection with s3
    s3C = boto3.client('s3')

    url = s3C.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': BUCKET_NAME,
            'Key': vid_name
        }
    )

    return render_template('trim-form.html', vid_id=vid_id, orig_vid=vid_name, vid_url=url)

@app.route('/make-clips', methods=["POST"])
def get_clip_source():
    """Gets the video to be clipped from aws - passes to make-clips function"""
    
    # get video obj from db
    # TO DO make sure the vid exists
    vid_id = request.form.get('vid_id')
    vid_to_trim = Video.query.get(vid_id)
    vid_name = vid_to_trim.vid_name

    #get the user id
    user_id = g.current_user.user_id

    clip_list = request.form.get('clip-list')
    clips = clip_list.split(", ")

    #establish connection with s3
    s3C = boto3.client('s3')

    # Generate the URL to get 'key-name' from 'bucket-name'
    # this temporarily grants access to the requested video
    url = s3C.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': BUCKET_NAME,
            'Key': vid_name
        }
    )

    s3 = boto3.resource('s3')
    save_loc = 'static/temp/'+vid_name
    if os.path.isfile(save_loc):
        make_clips(save_loc, clips, vid_id, user_id)
    else:
        s3.meta.client.download_file(BUCKET_NAME, vid_name, save_loc, Callback=make_clips(save_loc, clips, vid_id, user_id))
    
    return redirect('/clips/{}'.format(vid_id))


def make_clips(file_loc, clips, vid_id, user_id):
    """Makes the designated clips once the file is downloaded"""

    print "\n\n\n\n\n\n\n\n CALLBACK \n\n\n\n\n\n\n\n\n"

    #make a videoFileClip object using temp location path from make-clips route
    my_clip = VideoFileClip(file_loc)

    # trim path to remove the file ext
    clip_name_base = file_loc[0:-4]

    # save the ext separately
    file_ext = file_loc[-4:]

    # make a list to hold the new clips so we can upload at the end
    clips_to_upload = []

    # loop through the clips list and make clips for all the time codes given
    for clip in clips:
        # split the start and end times
        clip = clip.split('-')
        # replace the : with _ since the : cause a filename issue
        start_time = clip[0].replace(":", "_")
        end_time = clip[1].replace(":", "_")
        # stitch together base name with times in file name
        clip_name = clip_name_base + "-" + start_time + "-" + end_time + file_ext
        #get just the filename for the aws key
        key_name = clip_name[clip_name.rfind('/')+1:]
        # add to the list of files to upload
        clips_to_upload.append(clip_name)
        # create the new subclip
        new_clip = my_clip.subclip(t_start=clip[0], t_end=clip[1])
        # save the clip to our temp file location
        new_clip.write_videofile(clip_name, codec="libx264")
        # add the clip to our db
        db_clip = SubClip(vid_id=vid_id, start_at=clip[0], end_at=clip[1], created_by=user_id, clip_name=key_name)
        db.session.add(db_clip)
        db.session.commit()

    #establish session with aws
    session = boto3.session.Session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    s3 = session.resource('s3')
    while len(clips_to_upload) > 0:
        # pop the clip from the front of the list
        clip_path = clips_to_upload.pop(0)
        # if that file exists in the temp folder - upload it
        if os.path.isfile(clip_path):
            video_file = clip_path
            video_name = clip_path.split('/')
            video_name = video_name[-1]
            print "\n\n\n\n\n\n\n", video_file, video_name, "\n\n\n\n\n\n\n"
            s3.meta.client.upload_file(video_file, BUCKET_NAME, video_name, Callback=file_done())
            #s3.Bucket(BUCKET_NAME).upload_file(video_file, video_name)
            #s3.Bucket(BUCKET_NAME).put_object(Key=video_name, Body=video_file, Callback=remove_file(video_file))
            #s3.Bucket(BUCKET_NAME).put_object(Key=video_name, Body=video_file)
        else:
            #if it wasn't done being written yet - add it back to the list
            clips_to_upload.append(clip_path)

def file_done():
    print "\n\n\n\n\n\n\n FILE DONE \n\n\n\n\n\n\n"


@app.route('/clips/<vid_id>')
@login_required
def show_all_clips(vid_id):
    """loads page with a list of all clips for that vid id"""

    #video = Video.query.get(vid_id)
    #get a list of all the clips associated with that video id
    # TO DO join query to get user name who created clip
    clips = SubClip.query.filter(SubClip.vid_id == vid_id).all()
    main_vid = Video.query.get(vid_id)

    return render_template('vid-clips.html', main_vid=main_vid, clips=clips)

@app.route('/show-clip/<clip_id>')
@login_required
def show_clip(clip_id):
    """Plays the clip in a separate window"""

    clip_to_show = SubClip.query.get(clip_id)
    clip_name = clip_to_show.clip_name

    #establish connection with s3
    s3C = boto3.client('s3')

    url = s3C.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': BUCKET_NAME,
            'Key': clip_name
        }
    )

    return render_template('show-video.html', vid_id=clip_id, orig_vid=clip_name, vid_url=url)

def remove_file(file_path):
    """removes file from temp folder once uploaded"""
    
    os.remove(file_path)

# USER REGISTRATION/LOGIN-------------------------------------------------------


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
