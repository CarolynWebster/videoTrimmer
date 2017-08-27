"""Tag functions for video trimmer"""

from model import Case, db, Tag, ClipTag, db_session

from flask import session, flash


def get_tags(case_id):
    """Returns the tags associated with a case and the default tags"""

    # query the db for the DEFAULT case
    default_case = db.session.query(Case).filter(Case.case_name == "DEFAULT").first()
    # find all the tags for this provided case as well as default tags
    tags = db.session.query(Tag).filter((Tag.case_id == case_id) |
                                     (Tag.case_id == default_case.case_id)).all()

    # return a list of tags
    return tags


def add_tags(tag, case_id):
    """Adds a tag to a case"""

    #check if the tag exists
    #gets the user object for that email address
    tag_check = db.session.query(Tag).filter(Tag.tag_name == tag, 
                                                 Tag.case_id == case_id).first()
    # if user already exists associate the user with the new case
    if tag_check is None:
        #if the user is not registered - add them to the database
        #they can add their password and name when they officially register
        tag = Tag(tag_name=tag, case_id=case_id)
        #prime user to be added to db
        db.session.add(tag)
        #commit user to db
        db.session.commit()


def delete_cliptags(clip_id, tag_name):
    """Deletes a tag from a case and any associated clips"""

    scoped_session = db_session()

    tag_id = scoped_session.query(Tag.tag_id).filter(Tag.tag_name == tag_name)

    # get the cliptag object to be deleted
    cliptag = scoped_session.query(ClipTag).filter(ClipTag.clip_id == clip_id,
                                   ClipTag.tag_id == tag_id).first()
    # delete the cliptag
    scoped_session.delete(cliptag)
    scoped_session.commit()

    return "Success"
