"""Video Trimmer"""

# will consolidate after initial development - easier to keep track this way
import imageio
imageio.plugins.ffmpeg.download()

from moviepy.editor import *

from jinja2 import StrictUndefined

from flask import Flask, render_template, request, redirect, flash, session, url_for, g

from functools import wraps

from flask_debugtoolbar import DebugToolbarExtension

from model import db, connect_to_db, User, Video, Case, UserCase, Clip, Tag, ClipTag, db_session, Transcript, TextPull

from datetime import datetime

import boto3

import os

import zipfile

import threading

import smtplib

import arrow

from email.mime.text import MIMEText

from ppt import create_slide_deck, find_text_by_page_line

from cases import create_case

from users import update_usercase, create_user, validate_usercase, get_user_by_email

from tags import get_tags, add_tags, delete_cliptags

from videos import upload_aws_db, update_vid_status, get_vid_url

app = Flask(__name__)

AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
AWS_SECRET_KEY = os.environ['AWS_SECRET_KEY']

#aws bucket name
BUCKET_NAME = 'videotrim'


# Required to use Flask sessions and the debug toolbar
app.secret_key = "ABC"

app.jinja_env.undefined = StrictUndefined


# BEFORE REQUEST/LOGIN WRAPPER -------------------------------------------------

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
        if g.current_user is not None:
            g.user_cases = g.current_user.cases

    # otherwise return None
    else:
        g.current_user = None


# HOMEPAGE ---------------------------------------------------------------------


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

    user_permitted = validate_usercase(case_id, g.current_user.user_id)

    if user_permitted:
        # get all videos that match the provided case_id
        vids = Video.query.filter(Video.case_id == case_id).all()

        # get the case object for the provided case_id
        this_case = Case.query.get(case_id)

        return render_template('case-vids.html', videos=vids, case=this_case)
    else:
        flash("You don't have permission to view that case")
        return redirect('/cases')


@app.route('/register-case', methods=["GET", "POST"])
@login_required
def register_case():
    """Handles form and registration of new case"""

    #if it's a get - render registration form
    if request.method == "GET":
        # render registration form
        return render_template('/register-case.html')

    #otherwise register case in db
    if request.method == "POST":

        # get the case name, list of user emails and the current user
        case_name = request.form.get('case_name')
        other_users = request.form.get('user-list')
        current_user = g.current_user

        # strip out spaces from the email's input into the form
        other_users = other_users.replace(" ", "")
        # split on the comma
        user_emails = other_users.split(",")

        # append the existing user to the list of approved users
        user_emails.append(current_user.email)

        # instantiate a new case in the db
        # create_case() returns the newly created case object
        case = create_case(case_name, current_user.user_id)

        # cycle through the provided emails
        for email in user_emails:
            # get_user_by_email gets the user object for that email address
            # or registers a new user if the email doesn't exist already
            user = get_user_by_email(email)

            #create an association in the usercases table
            update_usercase(case_id=case.case_id, user_id=user.user_id)

        return redirect('/cases')


@app.route('/case-settings/<case_id>')
def show_case_settings(case_id):
    """Shows user settings for chosen case"""

    # check if the user has permission to view this case
    user_permitted = validate_usercase(case_id, g.current_user.user_id)

    owner_id = Case.query.get(case_id).owner_id
    owner = User.query.get(owner_id)

    if user_permitted:
        # get all users associated with this case id
        users = db.session.query(User.fname, User.lname, User.email, User.user_id).join(
                                UserCase).filter(UserCase.case_id == case_id).all()

        # get the tags for this case and the default tags
        tags = get_tags(case_id)

        return render_template('case-settings.html', users=users, case_id=case_id, tags=tags, owner=owner)
    else:
        flash("You don't have permission to view that case")
        return redirect('/cases')


# USER/USER CASES ---------------------------------------------------------------


@app.route('/add-usercase', methods=["POST"])
def add_users_to_case():
    """Adds a user to a specific case"""

    # get data
    case_id = request.form.get('case_id')
    user_emails = request.form.get('new_users')

    #nix any spaces
    user_emails = user_emails.replace(" ", "")
    #split up the emails
    user_emails = user_emails.split(",")

    # start the return string with a <tr> tag
    update_users = "<tr>"

    # loop through the emails
    for email in user_emails:
        # get the user obj for the email
        # a new user be created if the user is not registered yet
        user_check = get_user_by_email(email)

        # Create usercase assocation
        # update_usercase returns None if the usercase is new
        case_user_check = update_usercase(case_id, user_check.user_id)

        # if it's a new assocation - add it as a <td> to response string
        if case_user_check is None:
            update_users = update_users + "<td>"+email+"</td>"

    # add the closing row tag once all the tds are done
    update_users = update_users + "</tr>"

    return update_users


@app.route('/remove-usercase', methods=["POST"])
def remove_user_from_case():
    """Removes a user from a specific case"""

    # get data
    case_id = request.form.get('case_id')
    user_id = request.form.get('del_user')

    # use validate usercase to return the usercase obj for this user/case
    usercase = validate_usercase(case_id, user_id)
    db.session.delete(usercase)
    db.session.commit()

    return "Usercase removed"


# USER REGISTRATION/LOGIN ------------------------------------------------------


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


@app.route('/register', methods=['GET', 'POST'])
def register_user():
    """User registration"""

    # if it's a get - render registration form
    if request.method == "GET":
        """Shows new user a registration form"""

        return render_template('registration.html')

    # otherwise register user in db
    if request.method == "POST":
        """Checks db for user and adds user if new"""

        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get("email")
        password = request.form.get("password")

        # check if user exists in db already
        # this would happen if they were added to a case
        # but haven't actually registered yet
        user_check = User.query.filter_by(email=email).first()

        # create user or update the existing unregistered
        create_user(user_check, email, fname, lname, password)

        # send them to their own page
        return redirect('/cases')


# TAGS/CLIPTAGS ----------------------------------------------------------------


@app.route('/add-tags', methods=["POST"])
def add_tags_to_case():
    """Adds a tag to a specific case"""

    case_id = request.form.get('case_id')
    tags = request.form.get('new_tags')

    #nix any spaces
    tags = tags.replace(" ", "")

    #split up the emails
    tags = tags.split(",")

    for tag in tags:
        add_tags(tag, case_id)

    return "Tags were added successfully"


@app.route('/delete-tag', methods=['POST'])
def delete_tag():
    """Removes a tag from a case and removes cliptag associations"""

    # get data
    tag_id = request.form.get('del_tag')

    # get tag
    tag = Tag.query.get(tag_id)

    # delete the tag itself from the db
    db.session.delete(tag)
    db.session.commit()

    return "tag removed"


@app.route('/add-cliptags', methods=["POST"])
def add_cliptags():
    """Adds a tag to a specific clip"""

    #get clip id and tag from request
    clip_id = request.form.get('clip_id')
    req_tag = request.form.get('tag')

    #get the tag obj that matches the requested tag
    tag = Tag.query.filter(Tag.tag_name == req_tag).first()
    clip = Clip.query.get(clip_id)

    #check if that tag is associated with that clip already
    #tag_check = ClipTag.query.filter(ClipTag.tag_id == tag.tag_id, ClipTag.clip_id == clip_id).first()
    if tag not in clip.tags:
        clip.tags.append(tag)
        db.session.commit()

        #return the tag to be added to the html
        return tag.tag_name


# VIDEO ------------------------------------------------------------------------


@app.route('/upload-video', methods=["GET","POST"])
@login_required
def upload_video():
    """Handle file uploads"""

    # if it's a get - render registration form
    if request.method == "GET":
        """Load form for user to upload new video"""

        case_id = request.args.get('case_id')

        return render_template('upload-video.html', case_id=case_id)

    # otherwise register user in db
    if request.method == "POST":
        """Uploads video to aws"""

        case_id = request.form.get('case_id')
        video_file = request.files.get("rawvid")
        video_name = video_file.filename
        try:
            transcript_file = request.files.get("tscript")
        except:
            transcript_file = None
        user_id = g.current_user.user_id

        #get deponent name and recorded date
        deponent = request.form.get('name')
        recorded_at = request.form.get('date-taken')

        # add the video to the db
        date_added = datetime.now()
        new_vid = Video(case_id=case_id, vid_name=video_name, added_by=user_id,
                        added_at=date_added, deponent=deponent, recorded_at=recorded_at)
        db.session.add(new_vid)
        db.session.commit()

        if transcript_file:
            # add the transcript if there is one
            # we use readlines so we can search it easier
            script_text = transcript_file.readlines()
            new_script = Transcript(vid_id=new_vid.vid_id, text=script_text)
            db.session.add(new_script)
            db.session.commit()

        # send the upload to a separate thread to upload while the user moves on
        upload = threading.Thread(target=upload_aws_db, args=(video_file, video_name, case_id, user_id, BUCKET_NAME)).start()

        return redirect('/cases/'+str(case_id))


@app.route('/show-video/<vid_id>')
@login_required
def show_video(vid_id):
    """Streams the selected video"""

    #get the video object
    vid_to_trim = Video.query.get(vid_id)
    vid_name = vid_to_trim.vid_name
    case_id = vid_to_trim.case.case_id

    user_permitted = validate_usercase(case_id, g.current_user.user_id)

    if user_permitted:
        # get temporary url for that video
        url = get_vid_url(vid_name)

        return render_template('show-video.html', vid_id=vid_id, orig_vid=vid_name, vid_url=url)
    else:
        flash("You don't have permission to view that case")
        return redirect('/cases')


# @app.route('/handle-videos', methods=['POST'])
# @login_required
# def handle_videos():
#     """handle the selected full videos and perform action based on btn clicked"""

#     # get the list of requested clips
#     selected_vids = request.form.get('clips')
#     selected_vids = selected_vids.strip()
#     selected_vids = selected_vids.split(",")

#     print "\n\n\n\n\n\n", selected_vids, "\n\n\n\n\n\n"

#     # find all the requested videos based on the vid_ids provided
#     req_vids = Video.query.filter(Video.vid_id.in_(selected_vids)).all()

#     # since all requested videos are from the same case
#     # we can collect case info from the first video returned
#     case_id = req_vids[0].case.case_id
#     folder_name = req_vids[0].case.case_name

#     # make some adjustments to the case name so we can use it as a folder name
#     folder_name = folder_name.replace(" ", "_")
#     folder_name = folder_name.replace(".", "_")

#     # identify if we are downloading or deleting
#     func_to_perform = request.form.get('call_func')

#     if func_to_perform == 'downloadClips':
#         download_all_files(req_vids, case_name, g.current_user)
#     elif func_to_perform == 'deleteClips':
#         delete_all_files(req_vids, "vids")

#     return redirect('/cases/{}'.format(case_id))


# CLIPS ------------------------------------------------------------------------


@app.route('/handle-clips', methods=['POST'])
@login_required
def handle_clips():
    """handle the selected clips and perform action based on btn clicked"""

    # get the list of requested clips
    selected_clips = request.form.get('clips')
    selected_clips = selected_clips.strip()
    selected_clips = selected_clips.split(",")

    # get the function we are trying to do (delete, download, etc)
    func_to_perform = request.form.get('call_func')

    # get vid_type to know if we are working with full videos or clips
    vid_type = request.form.get('vid_type')

    # req_clips = []

    if vid_type == "clip":
        #get the vid id
        vid_id = int(request.form.get('vid_id'))

        #get the full video name
        folder_name = Video.query.get(vid_id).vid_name[:-4]

        # get a list of the clip objects from the db [(clip_name, clip_id)]
        req_clips = db.session.query(Clip.clip_name, Clip.clip_id).join(Video).filter(
                                    (Clip.clip_id.in_(selected_clips)) &
                                    (Video.vid_id == vid_id)).all()

        # stitch clip and create deck are only availble for clips
        # the true is to trigger the stitch function
        if func_to_perform == 'stitchClips':
            download_all_files(req_clips, vid_name, g.current_user, vid_type, True)
        elif func_to_perform == 'createDeck':
            make_clip_ppt(req_clips, vid_name, g.current_user)

        # return redirect('/clips/{}'.format(vid_id))

    # if it's a video do these things
    elif vid_type == "video":
        # find all the requested videos based on the vid_ids provided
        req_clips = Video.query.filter(Video.vid_id.in_(selected_clips)).all()

        # since all requested videos are from the same case
        # we can collect case info from the first video returned
        case_id = req_clips[0].case.case_id
        folder_name = req_clips[0].case.case_name

        # make some adjustments to the case name so we can use it as a folder name
        folder_name = folder_name.replace(" ", "_")
        folder_name = folder_name.replace(".", "_")

    print "\n\n\n\n\n\n\n\n", req_clips, "\n\n\n\n\n\n"
    # call the appropriate function
    if func_to_perform == 'downloadClips':
        download_all_files(req_clips, folder_name, g.current_user, vid_type)
    elif func_to_perform == 'deleteClips':
        delete_all_files(req_clips, vid_type)
    return "request complete"


@app.route('/trim-video/<vid_id>')
@login_required
def trim_video(vid_id):
    """Load form to get user clip requests"""

    vid_to_trim = Video.query.get(vid_id)
    vid_name = vid_to_trim.vid_name
    case_id = vid_to_trim.case.case_id

    # check if user is permitted to see this content
    user_permitted = validate_usercase(case_id, g.current_user.user_id)

    if user_permitted:
        # get temporary url
        url = get_vid_url(vid_name)

        return render_template('trim-form.html', vid_id=vid_id, orig_vid=vid_name, vid_url=url)
    else:
        flash("You don't have permission to view that case")
        return redirect('/cases')


@app.route('/make-clips', methods=["POST"])
def get_clip_source():
    """Gets the video to be clipped from aws - passes to make-clips function"""

    # get video obj from db
    # TO DO make sure the vid exists
    vid_id = request.form.get('vid_id')
    vid_to_trim = Video.query.get(vid_id)
    vid_name = vid_to_trim.vid_name
    case_id = vid_to_trim.case.case_id

    #get the user id
    user_id = g.current_user.user_id

    user_permitted = validate_usercase(case_id, user_id)

    if user_permitted:
        # get the clip list from the form
        clip_list = request.form.get('clip-list')
        clips = clip_list.split(", ")
        print clips
        # get if the user is using timecodes or page-line nums
        trim_method = request.form.get('trim_method')

        # make pathname for location to save temp video
        save_loc = 'static/temp/'+vid_name

        # trim path to remove the file ext
        clip_name_base = save_loc[0:-4]

        # save the ext separately
        # file_ext = save_loc[-4:]
        file_ext = ".mov"

        # make a list to hold the clip db objects
        clips_to_process = []

        # add the clips to the db - they will show up as processing until they are complete
        for clip in clips:
            # split the start and end times
            clip = clip.split('-')
            # replace the : with _ since the : cause a filename issue
            start_time = clip[0].replace(":", "_")
            end_time = clip[1].replace(":", "_")
            # stitch together base name with times in file name
            clip_name = clip_name_base + "-" + start_time + "-" + end_time + file_ext
            # get just the filename for the aws key
            key_name = clip_name[clip_name.rfind('/')+1:]

            #check if the clip exists already
            clip_check = Clip.query.filter_by(clip_name=key_name).first()
            if clip_check is None or clip_check.clip_status != "Ready":
                # add the clip to our db
                if trim_method == "time":
                    db_clip = Clip(vid_id=vid_id, start_at=clip[0], end_at=clip[1], created_by=user_id, clip_name=key_name)
                elif trim_method == "page":
                    db_clip = Clip(vid_id=vid_id, start_pl=clip[0], end_pl=clip[1], created_by=user_id, clip_name=key_name)
                db.session.add(db_clip)
                db.session.commit()

                clips_to_process.append(db_clip)
        print "pro", clips_to_process
        # send the upload to a separate thread to upload while the user moves on
        download = threading.Thread(target=download_from_aws, args=(save_loc, clips_to_process, vid_id, user_id, vid_name)).start()

        return redirect('/clips/{}'.format(vid_id))
    else:
        flash("You don't have permission to view that case")
        return redirect('/cases')


def download_from_aws(save_loc, clips, vid_id, user_id, vid_name):
    """Downloads file from aws"""

    print "dl", clips
    # if the video hasn't been downloaded already - download it
    if os.path.isfile(save_loc) is False:
        client = boto3.client('s3')
        client.download_file(BUCKET_NAME, vid_name, save_loc)
        while os.path.isfile(save_loc) is False:
            #wait for it to download
            print "downloading"

    # gets the corresponding text for that clip if there is any
    pulled_text = pull_text(clips, vid_id)
    #once the file is available, make clips
    make_clips(save_loc, clips, vid_id, user_id)


def pull_text(clips, vid_id):
    """Goes to video transcript and pulls relevant text"""

    # hook up to db
    scoped_session = db_session()

    # list to hold all pull tuples
    all_pulls = []

    # get the transcript for the selected video
    transcript = scoped_session.query(Transcript).filter(Transcript.vid_id == vid_id).first()

    if transcript:
        for clip in clips:
            # if the clip object has a page line num
            if clip.start_pl is not None:
                # get the timecodes and text for the request page-line nums
                pull = find_text_by_page_line(clip.start_pl, clip.end_pl, transcript.text)
                
                # a tuple is returned for pull (start_at, end_at, pulled_text)
                start_at, end_at, pull_text = pull

                # rebind to the db connected clip obj
                clip = scoped_session.query(Clip).get(clip.clip_id)
                clip.start_at = start_at
                clip.end_at = end_at

                print "pull clip", clip
                # make a new pull obj for the db
                new_pull = TextPull(clip_id=clip.clip_id, pull_text=pull_text)
                scoped_session.add(new_pull)

                # add new pull and update clip obj with timecodes from transcript
                scoped_session.commit()
                print pull_text
    # close scoped session
    db_session.remove()


def make_clips(file_loc, clips, vid_id, user_id):
    """Makes the designated clips once the file is downloaded"""

    print "\n\n\n\n\n\n\n\n MAKING CLIPS", file_loc, "\n\n\n\n\n\n\n\n\n"

    # make a videoFileClip object using temp location path from make-clips route
    # this is the main video we will make clips from
    main_vid = VideoFileClip(file_loc)

    # trim path to remove the file ext
    clip_name_base = file_loc[0:-4]

    # save the ext separately
    # file_ext = file_loc[-4:]
    file_ext = ".mov"

    # make a list to hold the new clips so we can upload at the end
    clips_to_upload = []

    scoped_session = db_session()

    print clips
    # loop through the clips list and make clips for all the time codes given
    for clip in clips:
        print clip
        # rebind to the db connected clip obj
        clip = scoped_session.query(Clip).filter(Clip.clip_id == clip.clip_id).first()
        print clip
        clip_name = clip.clip_name
        clip_path = 'static/temp/'+clip_name
        print clip_path
        # add to the list of files to upload
        clips_to_upload.append(clip_path)
        print "times", clip.start_at, clip.end_at
        # create the new subclip
        new_clip = main_vid.subclip(t_start=clip.start_at, t_end=clip.end_at)
        # save the clip to our temp file location
        new_clip.write_videofile(clip_path, codec="libx264")

    db_session.remove()
    #establish session with aws
    s3session = boto3.session.Session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    s3 = s3session.resource('s3')
    while len(clips_to_upload) > 0:
        # pop the clip from the front of the list
        clip_path = clips_to_upload.pop(0)
        # if that file exists in the temp folder - upload it
        if os.path.isfile(clip_path):
            video_file = clip_path
            video_name = clip_path.split('/')
            video_name = video_name[-1]
            s3.meta.client.upload_file(video_file, BUCKET_NAME, video_name, Callback=file_done(video_name))
        else:
            #if it wasn't done being written yet - add it back to the list
            clips_to_upload.append(clip_path)


def file_done(vid_name):
    """Updates the clip status once upload is complete"""

    print "\n\n\n\n\n\n\n  FILE READY \n\n\n\n\n\n\n"
    scoped_session = db_session()
    clip = scoped_session.query(Clip).filter(Clip.clip_name == vid_name).first()
    clip.clip_status = 'Ready'
    scoped_session.commit()
    db_session.remove()


@app.route('/clips/<vid_id>')
@login_required
def show_all_clips(vid_id):
    """loads page with a list of all clips for that vid id"""

    #get a list of all the clips associated with that video id
    main_vid = Video.query.get(vid_id)
    case_id = main_vid.case.case_id

    user_permitted = validate_usercase(case_id, g.current_user.user_id)

    if user_permitted:
        clips = Clip.query.filter(Clip.vid_id == vid_id).all()

        # get the tags for this case and the default tags
        tags = get_tags(main_vid.case_id)

        return render_template('vid-clips.html', main_vid=main_vid, clips=clips, tags=tags)
    else:
        flash("You don't have permission to view that case")
        return redirect('/cases')


@app.route('/show-clip/<clip_id>')
@login_required
def show_clip(clip_id):
    """Plays the clip in a separate window"""

    # get the clip object 
    clip_to_show = Clip.query.get(clip_id)
    clip_name = clip_to_show.clip_name

    # get the case id associated with this clip
    case_id = clip_to_show.video.case.case_id

    user_permitted = validate_usercase(case_id, g.current_user.user_id)

    if user_permitted:
        # get temporary url
        url = get_vid_url(clip_name)
        
        return render_template('show-video.html', vid_id=clip_id, orig_vid=clip_name, vid_url=url)
    else:
        flash("You don't have permission to view that case")
        return redirect('/cases')


# CLIP AND VIDEO DOWNLOADING/DELETING FUNCTIONS --------------------------------

DEFAULT_TEMP = 'static/ppt_temps/Gray_temp.pptx'

def make_clip_ppt(clips, vid_name, user):
    """Create a ppt using the clips"""

    # connect to aws
    s3 = boto3.resource('s3')

    # make a list to hold all the clip paths
    clips_for_ppt = []

    for clip in clips:
        # our query returns a tuple (clip_name, clip_id)
        file_name = clip[0]

        # make a save location for the downloaded clips in the temp folder
        save_loc = 'static/temp/'+file_name

        if not os.path.exists(save_loc):
            # download file
            s3.meta.client.download_file(BUCKET_NAME, file_name, save_loc)
        
        # add file path to the list
        clips_for_ppt.append(save_loc)

    create_slide_deck(DEFAULT_TEMP, clips_for_ppt)




def download_all_files(clips, vid_name, user, vid_type, stitch=False):
    """Download selected clips and save as a zip"""

    # get data
    user_email = user.email
    user_id = user.user_id

    # get date of zip
    date_zipped = arrow.now('US/Pacific').format('MM-DD-YYYY_hh-mm_A')

    # if we are stitching clips together make a list to hold them
    if stitch is True:
        stitch_clips = []

    # get a url to use in the email without the static prefix
    zip_url = "zips/{}/{}_{}.zip".format(user_id, vid_name, date_zipped)

    # make sure a folder exists for where we will save the zip
    zip_dest = "static/zips/{}/".format(user_id)
    # if it doesn't exist, make the folder
    if not os.path.exists(zip_dest):
        os.makedirs(zip_dest)

    # make zip with either all individual clips or one stitched clip
    with zipfile.ZipFile("static/"+zip_url, 'w') as clipzip:
        for clip in clips:
            if vid_type == "clip":
                # our query returns a tuple (clip_name, clip_id)
                file_name = clip[0]
            elif vid_type == "video":
                file_name = clip.vid_name

            # make a save location for the downloaded clips in the temp folder
            save_loc = 'static/temp/'+file_name

            print "\n\n\n\n\n\n\n", file_name, save_loc, "\n\n\n\n\n\n\n"
            # if we don't have it stored in temp, download it
            if not os.path.exists(save_loc):
                # connect to aws
                s3 = boto3.resource('s3')
                s3.meta.client.download_file(BUCKET_NAME, file_name, save_loc)

            # if we aren't stitching add the individual file to the zip
            if stitch is False:
                clipzip.write(save_loc, vid_name+"/"+file_name)
            else:
                # otherwise add the videofiles to a clip list
                clip_vf = VideoFileClip(save_loc)
                stitch_clips.append(clip_vf)

        # if we are stitching create composite clip
        if stitch is True:
            # concat videos
            stitched_clip = concatenate_videoclips(stitch_clips)

            # make full path with filename
            stitched_url = 'static/temp/'+vid_name+'_compilation.mp4'

            # save the stitched video
            stitched_clip.write_videofile(stitched_url)

            # add the stitched video to the zip
            clipzip.write(stitched_url, vid_name+"/"+vid_name+'_compilation.mp4')

    # get the url for the email
    email_url = url_for('static', filename=zip_url)

    # send email to user that their zip is ready
    send_email(user_email, email_url)

def delete_all_files(clips, vid_type):
    """Delete selected clips from aws and db"""

    # blank list to hold all files to delete for aws
    delete_aws = []
    
    #connect to aws
    s3session = boto3.session.Session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    s3 = s3session.resource('s3')
    bucket = s3.Bucket(BUCKET_NAME)

    scoped_session = db_session()
    
    # go through all clip/video ids and delete accordingly
    for clip in clips:
        if vid_type == "clip":
            #use the clip_id part of the tuple to get the clip obj to delete
            file_to_del = scoped_session.query(Clip).get(clip[1])
            
            # add the clip name to a list of clips to be deleted from aws
            delete_aws.append({'Key': clip[0]})
        
        # we have to delete clip tags, clip, and then the video if it's a video
        if vid_type == "video":
            file_to_del = scoped_session.query(Video).get(clip.vid_id)

            # get any clips associated with this video - list of clip objs
            clips = file_to_del.clips

            for clip in clips:
                # add it to list of files to remove from aws
                delete_aws.append({'Key': clip.clip_name})

            # add main vid to list of files to remove from aws
            delete_aws.append({'Key': file_to_del.vid_name})

        # delete the originally selected file
        scoped_session.delete(file_to_del)
        scoped_session.commit()

    # close session
    db_session.remove()

    # delete the files from aws
    response = bucket.delete_objects(Delete={'Objects': delete_aws})


# EMAIL NOTIFICATIONS ----------------------------------------------------------

# get email info
gmail_user = os.environ['GMAIL_USER']
gmail_password = os.environ['GMAIL_PASS']

def create_message(sender, to, subject, message_text):
    """Create a message for an email.

    Args:
    sender: Email address of the sender.
    to: Email address of the receiver.
    subject: The subject of the email message.
    message_text: The text of the email message.

    Returns:
    An object containing a base64url encoded email object.
    """

    # creates a message to be sent
    message = MIMEText(message_text, 'html')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    
    return message.as_string()


def send_email(recipient, file_url):
    """Sends user a notification email"""

    # set up email content
    sent_from = gmail_user
    to = recipient
    subject = 'Update from Cut To The Point'
    body = 'Hey, Your video is ready! Here is a link <a href=http://localhost:5000{}>to download</a>'.format(file_url)

    # create a message
    email_text = create_message(sent_from, to, subject, body)

    # try sending it
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.sendmail(sent_from, to, email_text)
        server.close()

        print 'Email sent!'
    except:
        print 'Something went wrong...'


# STARTUP FUNCTIONS ------------------------------------------------------------

if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the
    # point that we invoke the DebugToolbarExtension
    app.debug = True
    app.jinja_env.auto_reload = app.debug  # make sure templates, etc. are not cached in debug mode

    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)

    app.run(port=5000, host='0.0.0.0')