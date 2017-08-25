from unittest import TestCase
from model import connect_to_db, db, example_data
from server import app
from flask import session


class FlaskTests(TestCase):

    def setUp(self):
        """Stuff to do before every test."""

        self.client = app.test_client()
        app.config['TESTING'] = True

    def test_homepage(self):
        """Test homepage page."""

        result = self.client.get("/")
        self.assertIn("Welcome", result.data)


class FlaskTestsDatabase(TestCase):
    """Flask tests that use the database."""

    def setUp(self):
        """Stuff to do before every test."""

        # Get the Flask test client
        self.client = app.test_client()
        app.config['TESTING'] = True

        # Connect to test database
        connect_to_db(app, "postgresql:///vidtester")

        # Create tables and add sample data
        db.create_all()
        example_data()


    def tearDown(self):
        """Do at end of every test."""

        db.session.close()
        db.drop_all()


    def test_login(self):
        """Test login page."""

        result = self.client.post("/login",
                                  data={"email": "bob@gmail.com", "password": "123"},
                                  follow_redirects=True)
        self.assertIn("Register a new case", result.data)


    def test_case_no_permission(self):
        """Make sure user can't see cases they aren't connected to"""

        result = self.client.post("/login",
                                  data={"email": "jane@gmail.com", "password": "123"},
                                  follow_redirects=True)
        self.assertNotIn("Cats v. Dogs", result.data)


    def test_case_permission(self):
        """Make sure user can see cases they are connected to"""

        result = self.client.post("/login",
                                  data={"email": "bob@gmail.com", "password": "123"},
                                  follow_redirects=True)
        self.assertNotIn("Cats v. Dogs", result.data)


    def test_case_video(self):
        """Check if a video shows up for case"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 1

            result = self.client.get('/cases/1', follow_redirects=True)

            self.assertIn('Test Video 1', result.data)


    def test_video_clip(self):
        """Check if a clip shows up for a video"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 1

            # Video 1 should display Test Clip 1
            resultClip1 = self.client.get('/clips/1', follow_redirects=True)
            self.assertIn('Test Clip 1', resultClip1.data)

            # Video 2 should not show Test Clip 1
            resultClip2 = self.client.get('clips/2', follow_redirects=True)
            self.assertNotIn('Test Clip 1', resultClip2.data)

    def test_casetag(self):
        """Check if a tag shows up for a case"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 1

            # Awesome is a tag for Case 1
            resultTag1 = self.client.get('/case-settings/1', follow_redirects=True)
            self.assertIn('Awesome', resultTag1.data)
            self.assertNotIn('Cats', resultTag1.data)
   



if __name__ == "__main__":
    import unittest

    unittest.main()