"""Video Trimmer"""

# will consolidate after initial development - easier to keep track this way
import imageio
imageio.plugins.ffmpeg.download()

from moviepy.editor import *

from jinja2 import StrictUndefined

from flask import Flask, render_template, request, redirect, flash, session, url_for, g, jsonify

from functools import wraps

from flask_debugtoolbar import DebugToolbarExtension

from model import db, connect_to_db, User, Video, Case, UserCase, Clip, Tag, Transcript

from datetime import datetime, time, timedelta

import os

import threading

from cases import create_case

from users import update_usercase, create_user, validate_usercase, get_user_by_email

from tags import get_tags, add_tags, delete_cliptags, get_tagged_clips

from videos import upload_aws_db, download_from_aws, get_vid_url
from videos import add_clip_to_db, make_clip_ppt, download_all_files, delete_all_files

app = Flask(__name__)

# AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
# AWS_SECRET_KEY = os.environ['AWS_SECRET_KEY']

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

        for vid in vids:
            vid.recorded_at = datetime.strftime(vid.recorded_at, '%Y-%m-%d')

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
@login_required
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

        tag_counts = {}

        for tag in tags:
            # get tagged clips returns a list of clip ids - convert to a string
            # and it will be used as a value on a download link
            tag.matching_clips = get_tagged_clips(tag, case_id)
            
            # count the clip ids to get a total count
            tag_counts[tag.tag_name] = len(tag.matching_clips)

            # convert the list to a string to use as a value on the button
            # we do this bc the handle-clips route parses a string into a
            tag.matching_clips = str(tag.matching_clips)[1:-1]

        print tag_counts

        return render_template('case-settings.html', users=users, case_id=case_id, tags=tags, owner=owner, tag_counts=tag_counts)
    else:
        flash("You don't have permission to view that case")
        return redirect('/cases')


# USER/USER CASES ---------------------------------------------------------------


@app.route('/add-usercase', methods=["POST"])
@login_required
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
    update_users = ""

    # loop through the emails
    for email in user_emails:
        # get the user obj for the email
        # a new user be created if the user is not registered yet
        user_check = get_user_by_email(email)

        # Create usercase assocation
        # update_usercase returns None if the usercase is new
        case_user_check = update_usercase(case_id, user_check.user_id)

        close_btn = '<td><button type="button" id="' + str(user_check.user_id) + '" class="close new-user-x" aria-label="Close"><span aria-hidden="true">&times;</span></button></td>'

        # if it's a new assocation - add it as a <td> to response string
        if case_user_check is None:
            update_users = update_users + "<tr id ='User_" + str(user_check.user_id) + "'>" + close_btn + "<td>"+user_check.fname + " " + user_check.lname +"</td>" + "<td>"+email+"</td> </tr>"

    # add the closing row tag once all the tds are done
    # update_users = update_users + "</tr>"

    return update_users


@app.route('/remove-usercase', methods=["POST"])
@login_required
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


@app.route('/user-settings', methods=["GET", "POST"])
@login_required
def show_user_settings():
    """Shows user info and allows updates"""

    user = g.current_user

    if request.method == "GET":
        """Show user info page"""

        return render_template('/user-settings.html', user=user)

    if request.method == "POST":
        """Update user info in db"""

        user_id = request.form.get('user_id')
        user = User.query.get(user_id)
        print user
        # make sure the current user is editing the right profile
        if g.current_user.user_id == int(user_id):
            fname = request.form.get('fname')
            lname = request.form.get('lname')
            email = request.form.get('email')
            password = request.form.get('pass')

            print password

            if user.fname != fname:
                user.fname = fname

            if user.lname != lname:
                user.lname = lname

            if user.email != email:
                user.email = email

            if password != "":
                user.password = password

            print "\n\n\n\n\n UPDATING \n\n\n\n\n"

            db.session.commit()

            return "Success"
        else:
            return "Failure"





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
        return "Success"


# TAGS/CLIPTAGS ----------------------------------------------------------------


@app.route('/add-tags', methods=["POST"])
@login_required
def add_tags_to_case():
    """Adds a tag to a specific case"""

    case_id = request.form.get('case_id')
    tags = request.form.get('new_tags')

    # #nix any spaces
    # tags = tags.replace(" ", "")

    #split up the emails
    tags = tags.split(", ")

    for tag in tags:
        add_tags(tag, case_id)

    return "Tags were added successfully"


@app.route('/delete-tag', methods=['POST'])
@login_required
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
@login_required
def add_cliptags():
    """Adds a tag to a specific clip"""

    #get clip id and tag from request
    clip_id = request.form.get('clip_id')
    req_tag = request.form.get('tag_id')

    #get the tag obj that matches the requested tag
    tag = Tag.query.get(req_tag)
    clip = Clip.query.get(clip_id)

    #check if that tag is associated with that clip already
    #tag_check = ClipTag.query.filter(ClipTag.tag_id == tag.tag_id, ClipTag.clip_id == clip_id).first()
    if tag not in clip.tags:
        clip.tags.append(tag)
        db.session.commit()

        response = {'tag_id': tag.tag_id, 'tag_name': tag.tag_name, 'clip_id': clip_id}
        #return the tag to be added to the html
        return jsonify(response)

@app.route('/remove-cliptag', methods=["POST"])
@login_required
def remove_cliptag():
    """Removes a clip tag"""

    #get clip id and tag from request
    clip_id = request.form.get('clip_id')
    req_tag = request.form.get('tag_id')

    return delete_cliptags(clip_id, req_tag)
    


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
        print "\n\n\n\n\n\n\n", request, "\n\n\n\n\n\n"
        video_file = request.files['media']
        print "\n\n\n\n\n\n\n", video_file, "\n\n\n\n\n\n"
        case_id = request.form.get('case_id')
        # video_file = request.files.get("rawvid")
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
            script_text = transcript_file.readlines()
            new_script = Transcript(vid_id=new_vid.vid_id, text=script_text)
            db.session.add(new_script)
            db.session.commit()

        # send the upload to a separate thread to upload while the user moves on
        upload = threading.Thread(target=upload_aws_db, args=(video_file, video_name, case_id, user_id)).start()

        return jsonify(case_id)


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


@app.route('/show-transcript/<vid_id>')
@login_required
def show_tscript(vid_id):
    """Shows transcript for selected video"""

    vid = Video.query.get(vid_id)
    print vid.case_id, g.current_user.user_id
    user_permitted = validate_usercase(vid.case_id, g.current_user.user_id)
    
    if user_permitted:
        tscript_obj = Transcript.query.filter(Transcript.vid_id == vid_id).first()
        tscript = tscript_obj.text
        tscript = tscript.split('\n","\n')

        return render_template('/tscript-preview.html', tscript=tscript, vid_id=vid_id)

@app.route('/add-transcript/<vid_id>', methods=["GET", "POST"])
@login_required
def add_tscript(vid_id):
    """Adds a transcript to a video"""

    if request.method == "GET":

        return render_template('/tscript-upload.html', vid_id=vid_id)

    if request.method == "POST":
        transcript_file = request.files.get("tscript")
        # add the transcript if there is one
        # we use readlines so we can search it easier
        script_text = transcript_file.readlines()
        new_script = Transcript(vid_id=vid_id, text=script_text)
        db.session.add(new_script)
        db.session.commit()

    return "Success"


@app.route('/remove-transcript', methods=["POST"])
@login_required
def remove_tscript():
    """Removes a transcript from a video"""
    
    vid_id = request.form.get('vid_id')
    vid = Video.query.get(vid_id)
    tscript = Transcript.query.filter(Transcript.vid_id == vid_id).first()
    db.session.delete(tscript)
    db.session.commit()



# CLIPS ------------------------------------------------------------------------


@app.route('/handle-clips', methods=['POST'])
@login_required
def handle_clips():
    """handle the selected videos or clips and perform action based on btn clicked"""

    # get the list of requested clips
    selected_clips = request.form.get('clips')
    selected_clips = selected_clips.strip()
    selected_clips = selected_clips.split(",")

    # get the function we are trying to do (delete, download, etc)
    func_to_perform = request.form.get('call_func')

    # get vid_type to know if we are working with full videos or clips
    vid_type = request.form.get('vid_type')

    curr_time = request.form.get('curr_time')

    # req_clips = []

    if vid_type == "clip":
        # get a list of the clip objects from the db [(clip_name, clip_id)]
        req_clips = Clip.query.filter(Clip.clip_id.in_(selected_clips)).all()

        try:
            #get the vid id
            vid_id = int(request.form.get('vid_id'))

            #get the full video name
            folder_name = Video.query.get(vid_id).vid_name[:-4]
        except:
            # get the case name if this is coming from the case page
            folder_name = req_clips[0].video.case.case_name
            # make some adjustments to the case name so we can use it as a folder name
            folder_name = folder_name.replace(" ", "_")
            folder_name = folder_name.replace(".", "_")
            
        # stitch clip and create deck are only availble for clips
        # the true is to trigger the stitch function
        if func_to_perform == 'stitchClips':
            download_all_files(req_clips, folder_name, g.current_user, vid_type, curr_time, True)
        elif func_to_perform == 'createDeck':
            make_clip_ppt(req_clips, folder_name, g.current_user, curr_time)

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

    # call the appropriate function
    if func_to_perform == 'downloadClips':
        download_all_files(req_clips, folder_name, g.current_user, vid_type, curr_time)
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

    has_transcript = False
    if vid_to_trim.transcript:
        has_transcript = True
    # check if user is permitted to see this content
    user_permitted = validate_usercase(case_id, g.current_user.user_id)

    if user_permitted:
        # get temporary url
        url = get_vid_url(vid_name)

        return render_template('trim-form.html', vid_id=vid_id, orig_vid=vid_name, 
                                vid_url=url, has_transcript=has_transcript)
    else:
        flash("You don't have permission to view that case")
        return redirect('/cases')


@app.route('/make-clips', methods=["POST"])
@login_required
def get_clip_source():
    """Created clips in db - threads to download, pull_text, and make-clips functions"""

    # get video obj from db
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

        # get if the user is using timecodes or page-line nums
        trim_method = request.form.get('trim_method')

        # make pathname for location to save temp video
        save_loc = 'static/temp/'+vid_name

        # trim path to remove the file ext
        clip_name_base = save_loc[0:-4]

        # using mov as native file type as it seems to work the most consistently
        file_ext = ".mov"

        # make a list to hold the clip db objects
        clips_to_process = []

        # add the clips to the db - they will show up as processing until they are complete
        for clip in clips:
            # creates an instance of the clip in the db and returns new clip_id
            # if the clip exists already - None is returned
            db_clip = add_clip_to_db(clip, clip_name_base, file_ext, vid_id,
                                     user_id, trim_method)
            # if a new clip was made 
            if db_clip:
                clips_to_process.append(Clip.query.get(db_clip))

        # send the upload to a separate thread to upload while the user moves on
        download = threading.Thread(target=download_from_aws, args=(save_loc, clips_to_process, vid_id, user_id, vid_name)).start()

        return redirect('/clips/{}'.format(vid_id))
    else:
        flash("You don't have permission to view that case")
        return redirect('/cases')


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

        for clip in clips:
            # get the clip duration
            # if the time includes milliseconds - trim them off
            if clip.start_at is not None:
                start_time = clip.start_at
                if len(start_time) > 8:
                    start_time = start_time[:-4]

                end_time = clip.end_at
                if len(end_time) > 8:
                    end_time = end_time[:-4]

                start_at = datetime.strptime(start_time, '%H:%M:%S')
                end_at = datetime.strptime(end_time, '%H:%M:%S')
                clip.duration = end_at - start_at
            else:
                clip.duration = '--'

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