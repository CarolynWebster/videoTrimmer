## Synopsis

Cut to the Point is a video trimming app built with the legal industry in mind. A user can upload deposition videos and trim out clips based on timecodes or page/line numbers, which is how transcripts are often cited. Clips can then be tagged for different phases of trial. They can be downloaded as a merged highlight reel, a zip of individual clips, or a PowerPoint deck. If the user provides a transcript, the matching transcript text can also be included on the PowerPoint slides. Cases can have many team members allowing for a division of labor. Case messages are implemented using socket.io which allows team members to quickly communicate case updates. Cut to the Point allows access to premium trial tools without the premium price.

## Motivation

Many lawyers don't have access to video tools or expensive trial software but firms of all sizes have to deal with excessive amounts of deposition video. This allows for a wider range of lawyers to have access to the tools they need day to day without the costly overhead.

## Technology

Python, JavaScript, jQuery, AJAX, Socket.io, PostgreSQL, SQLAlchemy, Flask, Jinja, Bootstrap, MoviePy, Python PPTX, Boto3, AWS S3 File Storage

## Installation

  * Set up and activate a python virtualenv, and install all dependencies:
    * `pip install -r requirements.txt`
  * Make sure you have PostgreSQL running. Create a new database in psql named lotr:
    * `psql`
    * `createdb vidtrimmer;`
  * Create the tables in your database:
    * `python -i model.py`
    * While in interactive mode, create tables: `db.create_all()`
    * Seed the default case and admin profiles: `seed_defaults()`
  * Now, quit interactive mode. Start up the flask server:
    * `python server.py`
  * Go to localhost:5000 to see the web app

## Using Cut to the Point

  * Login or register a new account
  * Register a new case - you can also invite others to work on the case with you
  * Upload a video to the case
  * Once video is ready click on the scissors to trim a new clip. If the user provided a timecoded transcript with their video, page and line number can be used, otherwise HH:MM:SS timecodes can be used as well. Multiple clips can be made at a time
  * Clips can be tagged with the provided default tags or with custom case-specifc tags
  * From the clips page you can combine clips into a single clip and download as a highlight reel, download a zip of individual clips, delete clips, or download a ppt deck of clips. Note: A ppt deck is not provided with this setup.
  * You can look at case settings to view all clips in the case with a specific tag or create a powerpoint deck of the clips
  * You can send messages to fellow case team members in the case messaging window