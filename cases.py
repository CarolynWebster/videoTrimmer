from model import db, Case

def create_case(case_name, owner_id):
    """Creates a new case in the database"""

    # check if that case name already exists
    case_check = Case.query.filter(Case.case_name == case_name).first()

    if case_check is None:
        #instantiate a new case in the db
        new_case = Case(case_name=case_name, owner_id=owner_id)
        #prime and commit the case to the db
        db.session.add(new_case)
        db.session.commit()

        #get the newly assigned case_id
        case_id = new_case.case_id

        #close the session
        # db_session.remove()

        #return the case object
        return Case.query.get(case_id)

    # otherwise return the existing case
    return case_check