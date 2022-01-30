from flask import Flask, url_for, request, render_template, make_response
from flask_assets import Environment, Bundle
from flask_sqlalchemy import SQLAlchemy
from markupsafe import escape

from pprint import pprint
import secrets
from datetime import datetime, timedelta, timezone
import helpers

app = Flask(__name__)
app.config.update(
    ENV='development',
    DEBUG=True,
    SECRET_KEY=secrets.token_hex(),
    SESSION_COOKIE_SAMESITE='Lax',
    # SESSION_COOKIE_SECURE=True,
    PERMANENT_SESSION_LIFETIME=timedelta(days=1),
    TEMPLATES_AUTO_RELOAD=True,

    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_DATABASE_URI="sqlite:///forum.db"
)
# scss, paths are relative to /static directory
assets = Environment(app)
assets.url = app.static_url_path
scss = Bundle(
    "../scss/main.scss", "../scss/footer.scss", "../scss/index.scss",
    "../scss/login.scss", "../scss/board.scss",
    filters='pyscss', output="css/styles.css"
)
assets.register('styles', scss)

db = SQLAlchemy(app)
"""
users, statuses, resourses, posts
statuses    -> one-to-many ->   users
users       -> one-to-many ->   posts
users       -> one-to-many ->   resourses
resourses   -> one-to-many ->   posts
Post may have internal relationships:
head post (thread) and responses (comments),
comments have an id of their thread (response_in_id)
and threads have a date of a last comment (updated)
"""

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.Sring(26), unique=True, nullable=False)
    password = db.Column(db.Sring(100), nullable=False)
    status = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, timezone=True, default=helpers.TIME_NOW, nullable=True)

class Statuses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Sring(20), unique=True, nullable=False)

class Resources(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resource = db.Column(db.LargeBinary(), nullable=False)
    user_id = db.Column(db.Sring(26), nullable=True)
    date = db.Column(db.DateTime, timezone=True, default=helpers.TIME_NOW, nullable=True)

class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    password = db.Column(db.Sring(30), nullable=True)
    date = db.Column(db.DateTime, timezone=True, default=helpers.TIME_NOW, nullable=False)
    response_in_id = db.Column(db.Integer, nullable=True)
    updated = db.Column(db.DateTime, timezone=True, default=helpers.TIME_NOW, nullable=True)
    text = db.Column(db.Text, nullable=False)  # ~16000 of unicode
    resource_one = db.Column(db.Integer, nullable=True)
    resource_two = db.Column(db.Integer, nullable=True)
    resource_three = db.Column(db.Integer, nullable=True)


@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html"), 200


@app.route("/brotherhood/")
@app.route("/b/")
@app.route("/b")
def brotherhood():
    return render_template("brotherhood.html"), 200


@app.route("/animation/")
@app.route("/a/")
@app.route("/a")
def animation():
    return render_template("animation.html"), 200


@app.route("/university/")
@app.route("/u/")
@app.route("/u")
def university():
    return render_template("university.html"), 200


@app.route("/login")
def login():
    return render_template("login.html"), 200


"""
@app.route("/<int:id>")
def show_id(id):
    return f"ID: {id}"

@app.route("/<path:subpath>")
def show_subpath(subpath):
    return f"Path: {escape(subpath)}"

@app.route("/projects/")
def projects():
    return "The project page"

@app.route('/about')
def about():
    return 'The about page'

@app.route('/user/<username>')
def profile(username):
    return f'{escape(username)}\'s profile'

@app.errorhandler(404)
def page_not_found(error):
    return "404"

with app.test_request_context():
    print("hello")

with app.test_request_context("/"):
    assert request.path == '/'
    assert request.method == 'GET'
    print("OK index")
"""
