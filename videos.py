"""Video and Clip functions"""

from model import db, Video, Clip, Transcript, TextPull, db_session

import os

import boto3

import zipfile

import arrow

import boto3

from flask import url_for

from moviepy.editor import *

from ppt import create_slide_deck, find_text_by_page_line

from gmail import send_email

from flask_socketio import emit

# from flask_socketio import SocketIO, send, emit

#aws bucket name
BUCKET_NAME = 'videotrim'

AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
AWS_SECRET_KEY = os.environ['AWS_SECRET_KEY']


def upload_aws_db(video_file, video_name, case_id, user_id, socketio, BUCKET_NAME=BUCKET_NAME):
    """Handles upload to aws and addition to the db"""

    print "\n\n\n\n\n\n\n UPLOAD \n\n\n\n\n\n\n"

    try:
        # read the contents of the filestorage obj
        video_file = video_file.read()
    except:
        video_file = open(video_file).read()

    #start a connection with aws
    session = boto3.session.Session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    s3 = session.resource('s3')
    # Put the video on aws
    s3.Bucket(BUCKET_NAME).put_object(Key=video_name, Body=video_file)
    print "\n\n\n\n\n\n\n UPLOAD DONE \n\n\n\n\n\n\n"
    # once the upload is complete - update the db status
    update_vid_status(video_name, socketio)


def update_vid_status(vid_name, socketio):
    """Updates the video status once upload is complete"""

    print "\n\n\n\n\n\n\n  VIDEO READY \n\n\n\n\n\n\n"

    # start db session
    scoped_session = db_session()

    #get the video based on the name
    vid = scoped_session.query(Video).filter(Video.vid_name == vid_name).first()
    vid_id = vid.vid_id
    #update the status to be ready
    vid.vid_status = 'Ready'
    scoped_session.commit()

    ready_clips = {}
    ready_clips['clips'] = [vid_id]
    socketio.emit('server update', ready_clips)

    # close the scoped session
    db_session.remove()


def get_vid_url(name):
    """Gets a temporary url to play video on the site using video player"""

    #establish connection with s3
    s3C = boto3.client('s3')

    url = s3C.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': BUCKET_NAME,
            'Key': name
        }
    )

    return url


def add_clip_to_db(clip, clip_name_base, file_ext, vid_id, user_id, trim_method):
    """Adds a clip instance to the database"""

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
    clip_check = db.session.query(Clip).filter(Clip.clip_name == key_name).first()

    if clip_check is None or clip_check.clip_status != "Ready":
        # add the clip to our db
        if trim_method == "time":
            db_clip = Clip(vid_id=vid_id, start_at=clip[0], end_at=clip[1], created_by=user_id, clip_name=key_name)
        elif trim_method == "page":
            db_clip = Clip(vid_id=vid_id, start_pl=clip[0], end_pl=clip[1], created_by=user_id, clip_name=key_name)

        # add the new clip instance to the db and commit
        db.session.add(db_clip)
        db.session.commit()

        clip_id = db_clip.clip_id

        # we return the clip if we made one
        # None is returned if clip existed already
        return clip_id

    # return None if clip existed already
    return None


def download_from_aws(save_loc, clips, vid_id, user_id, vid_name, socketio):
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
    make_clips(save_loc, clips, vid_id, user_id, socketio)


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


def make_clips(file_loc, clips, vid_id, user_id, socketio):
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

    # loop through the clips list and make clips for all the time codes given
    for clip in clips:
        # rebind to the db connected clip obj
        clip = scoped_session.query(Clip).filter(Clip.clip_id == clip.clip_id).first()
        
        # get the name and create a temp file path on the server
        clip_name = clip.clip_name
        clip_path = 'static/temp/'+clip_name

        # add to the list of files to upload
        clips_to_upload.append(clip_path)

        # create the new subclip
        new_clip = main_vid.subclip(t_start=clip.start_at, t_end=clip.end_at)

        # save the clip to our temp file location
        new_clip.write_videofile(clip_path, codec="libx264")

    # db_session.remove()
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
            s3.meta.client.upload_file(video_file, BUCKET_NAME, video_name, Callback=file_done(video_name, socketio))
        else:
            #if it wasn't done being written yet - add it back to the list
            clips_to_upload.append(clip_path)


def file_done(vid_name, socketio):
    """Updates the clip status once upload is complete"""

    print "\n\n\n\n\n\n\n  CLIP READY \n\n\n\n\n\n\n"
    # start a scoped session
    scoped_session = db_session()

    # get the clip by name
    clip = scoped_session.query(Clip).filter(Clip.clip_name == vid_name).first()
    clip_id = clip.clip_id
    # update status and commit the change to the db
    clip.clip_status = 'Ready'
    scoped_session.commit()
    
    ready_clips = {}
    ready_clips['clips'] = [clip_id]
    socketio.emit('server update', ready_clips)

    # close the session
    db_session.remove()


# CLIP AND VIDEO DOWNLOADING/DELETING FUNCTIONS --------------------------------

DEFAULT_TEMP = 'static/ppt_temps/Gray_temp.pptx'

def make_clip_ppt(clips, vid_name, user, curr_time):
    """Create a ppt using the clips"""

    # connect to aws
    s3 = boto3.resource('s3')

    # make a list to hold all the clip paths
    clips_for_ppt = []

    for clip in clips:
        # our query returns a tuple (clip_name, clip_id)
        file_name = clip.clip_name

        # make a save location for the downloaded clips in the temp folder
        save_loc = 'static/temp/'+file_name

        if not os.path.exists(save_loc):
            # download file
            s3.meta.client.download_file(BUCKET_NAME, file_name, save_loc)
        
        # add file path to the list
        clips_for_ppt.append(save_loc)

    create_slide_deck(DEFAULT_TEMP, clips_for_ppt, vid_name, curr_time)


def download_all_files(clips, vid_name, user, vid_type, curr_time, stitch=False):
    """Download selected clips and save as a zip"""

    # get data
    user_email = user.email
    user_id = user.user_id

    # get date of zip
    date_zipped = curr_time

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
                file_name = clip.clip_name
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
    send_email(user_email, email_url, 'file_notice')

def delete_all_files(clips, vid_type):
    """Delete selected clips from aws and db"""

    # blank list to hold all files to delete for aws
    delete_aws = []

    #connect to aws
    s3session = boto3.session.Session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    s3 = s3session.resource('s3')
    bucket = s3.Bucket(BUCKET_NAME)

    # db.session = db_session()

    # go through all clip/video ids and delete accordingly
    for clip in clips:
        if vid_type == "clip":
            #use the clip_id part of the tuple to get the clip obj to delete
            file_to_del = db.session.query(Clip).get(clip.clip_id)

            # add the clip name to a list of clips to be deleted from aws
            delete_aws.append({'Key': clip.clip_name})

        # we have to delete clip tags, clip, and then the video if it's a video
        if vid_type == "video":
            file_to_del = db.session.query(Video).get(clip.vid_id)

            # get any clips associated with this video - list of clip objs
            clips = file_to_del.clips

            for clip in clips:
                # add it to list of files to remove from aws
                delete_aws.append({'Key': clip.clip_name})

            # add main vid to list of files to remove from aws
            delete_aws.append({'Key': file_to_del.vid_name})

        # delete the originally selected file
        db.session.delete(file_to_del)
        db.session.commit()


    # delete the files from aws
    response = bucket.delete_objects(Delete={'Objects': delete_aws})
