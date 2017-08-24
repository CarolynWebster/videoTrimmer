"""Video functions"""

from model import db_session, Video

import os

import boto3

#aws bucket name
BUCKET_NAME = 'videotrim'

AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
AWS_SECRET_KEY = os.environ['AWS_SECRET_KEY']


def upload_aws_db(video_file, video_name, case_id, user_id, BUCKET_NAME):
    """Handles upload to aws and addition to the db"""

    print "\n\n\n\n\n\n\n UPLOAD \n\n\n\n\n\n\n"

    # read the contents of the filestorage obj
    video_file = video_file.read()

    #start a connection with aws
    session = boto3.session.Session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    s3 = session.resource('s3')

    # Put the video on aws
    s3.Bucket(BUCKET_NAME).put_object(Key=video_name, Body=video_file)

    # once the upload is complete - update the db status
    update_vid_status(video_name)


def update_vid_status(vid_name):
    """Updates the video status once upload is complete"""

    print "\n\n\n\n\n\n\n  STATUS UPDATE \n\n\n\n\n\n\n"

    # start db session
    scoped_session = db_session()

    #get the video based on the name
    vid = scoped_session.query(Video).filter(Video.vid_name == vid_name).first()

    #update the status to be ready
    vid.vid_status = 'Ready'
    scoped_session.commit()

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


