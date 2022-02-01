from flask import Flask, url_for, request, render_template, make_response
from flask_assets import Environment, Bundle
from flask_sqlalchemy import SQLAlchemy
from markupsafe import escape

from datetime import datetime, timedelta
from pprint import pprint
import secrets
import hashlib
import pathlib
import helpers

CWD = pathlib.Path.cwd()
STATUS_USER = 1
STATUS_MOD = 2
STATUS_ADMIN = 3

app = Flask(__name__)
app.config.update(
    ENV='development',
    DEBUG=True,
    SECRET_KEY=secrets.token_hex(),
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=1),
    TEMPLATES_AUTO_RELOAD=True,

    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_DATABASE_URI="sqlite:///forum.db"
)

# <scss>
scss_dir = CWD / "scss"
scss_list = [
    str(scss_dir / "main.scss"),
    str(scss_dir / "footer.scss"),
    str(scss_dir / "index.scss"),
    str(scss_dir / "login.scss"),
    str(scss_dir / "board.scss"),
]
css_file = str(CWD / "static" / "css" / "styles.css")

assets = Environment(app)
assets.url = app.static_url_path
scss = Bundle(scss_list, filters='pyscss', output=css_file)
assets.register('styles', scss)
# </scss>

# <db>
db = SQLAlchemy(app)
"""
statuses, users, resources,
resource_types, threads, posts, attachments

statuses    -- one-to-many -<   users
users       -- one-to-many -<   posts
users       -- one-to-many -<   resources
resource_types one-to-many -<   resources
threads     -- one-to-many -<   posts
posts       > many-to-many -<   resources
  posts     -- one-to-many -<   attachments
  resources -- one-to-many -<   attachments
"""
DEFAULT_LENGTH = 30
USERNAME_LENGTH = 20
USER_PASSWROD_LENGTH = 200
ANON_PASSWROD_LENGTH = 100
RESOURCE_LENGTH = 200

class Statuses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(DEFAULT_LENGTH), unique=True, nullable=False)
    users = db.relationship('Users', backref='statuses')

class Resource_types(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resource_type = db.Column(db.String(DEFAULT_LENGTH), unique=True, nullable=False)
    resources = db.relationship('Resources', backref='resource_types')

class Threads(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=helpers.time_now, nullable=False)
    updated = db.Column(db.DateTime, default=helpers.time_now, nullable=False)
    post_count = db.Column(db.Integer, default=0, nullable=False)
    archivated = db.Column(db.Boolean, default=False, nullable=False)
    posts = db.relationship('Posts', backref='threads')

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(USERNAME_LENGTH), unique=True, nullable=False)
    password = db.Column(db.String(USER_PASSWROD_LENGTH), nullable=False)
    status = db.Column(db.Integer,
        db.ForeignKey('statuses.id', onupdate='CASCADE', ondelete='RESTRICT'),
        default=STATUS_USER, nullable=False)
    registered = db.Column(db.DateTime, default=helpers.time_now, nullable=True)
    resources = db.relationship('Resources', backref='users')
    posts = db.relationship('Posts', backref='users')

class Resources(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resource = db.Column(db.String(RESOURCE_LENGTH), nullable=False)
    resource_type = db.Column(db.Integer,
        db.ForeignKey('resource_types.id', onupdate='CASCADE', ondelete='RESTRICT'),
        default='image', nullable=False)
    user_id = db.Column(db.Integer,
        db.ForeignKey('users.id', onupdate='CASCADE', ondelete='SET NULL'),
        nullable=True)
    uploaded = db.Column(db.DateTime, default=helpers.time_now, nullable=True)
    posts = db.relationship('Posts', backref='resources')
    attachments = db.relationship('Attachments', backref='resources')

class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer,
        db.ForeignKey('threads.id', onupdate='CASCADE', ondelete='RESTRICT'),
        nullable=True)
    user_id = db.Column(db.Integer,
        db.ForeignKey('users.id', onupdate='CASCADE', ondelete='SET NULL'),
        default=None, nullable=True)
    password = db.Column(db.String(ANON_PASSWROD_LENGTH), default=None, nullable=True)
    date = db.Column(db.DateTime, default=helpers.time_now, nullable=False)
    text = db.Column(db.Text, default=" ", nullable=False)
    files = db.Column(db.Boolean, default=False, nullable=False)
    attachments = db.relationship('Attachments', backref='posts')

class Attachments(db.Model):
    post_id = db.Column(db.Integer,
              db.ForeignKey('posts.id', onupdate='CASCADE', ondelete='SET NULL'),
              primary_key=True)
    resource_id = db.Column(db.Integer,
              db.ForeignKey('resources.id', onupdate='CASCADE', ondelete='SET NULL'),
              primary_key=True)
# </db>

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


if __name__ == '__main__':
    app.run()

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
