"""Tag functions for video trimmer"""

from model import Case, db_session, Tag, ClipTag

from flask import session, flash


def get_tags(case_id):
    """Returns the tags associated with a case and the default tags"""

    # start db session
    scoped_session = db_session()
    # query the db for the DEFAULT case
    default_case = scoped_session.query(Case).filter(Case.case_name == "DEFAULT").first()
    # find all the tags for this provided case as well as default tags
    tags = scoped_session.query(Tag).filter((Tag.case_id == case_id) |
                                     (Tag.case_id == default_case.case_id)).all()
    print tags
    # close db session
    db_session.remove()
    # return a list of tags
    return tags


def add_tags(tag, case_id):
    """Adds a tag to a case"""

    # start db session
    scoped_session = db_session()

    #check if the tag exists
    #gets the user object for that email address
    tag_check = scoped_session.query(Tag).filter(Tag.tag_name == tag, 
                                                 Tag.case_id == case_id).first()
    # if user already exists associate the user with the new case
    if tag_check is None:
        #if the user is not registered - add them to the database
        #they can add their password and name when they officially register
        tag = Tag(tag_name=tag, case_id=case_id)
        #prime user to be added to db
        scoped_session.add(tag)
        #commit user to db
        scoped_session.commit()

    # close db session
    db_session.remove()


def delete_cliptags(clip_id, tag_id):
    """Deletes a tag from a case and any associated clips"""

    # start a db session
    scoped_session = db_session()

    # get the cliptag object to be deleted
    cliptag = scoped_session.query(ClipTag).filter(ClipTag.clip_id == clip_id,
                                   ClipTag.tag_id == tag_id).first()
    # delete the cliptag
    scoped_session.delete(cliptag)
    scoped_session.commit()

    # close db session
    db_session.remove()
