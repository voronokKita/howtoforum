from flask import Flask, url_for, request, session, redirect, render_template, make_response, flash
from flask_assets import Environment, Bundle
from flask_sqlalchemy import SQLAlchemy
from markupsafe import escape

from datetime import datetime, timedelta
from pprint import pprint
import secrets
import hashlib
import pathlib
import re
import helpers


CWD = pathlib.Path.cwd()
STATUS_USER = 1
STATUS_MOD = 2
STATUS_ADMIN = 3
DEFAULT_LENGTH = 30
USERNAME_MIN = 2
USERNAME_LENGTH = 20
USERNAME_PATTERN = '[A-Za-z0-9_-]+'
USER_PASSWORD_MIN = 2
USER_PASSWROD_LENGTH = 200
ANON_PASSWROD_LENGTH = 100
RESOURCE_LENGTH = 200
FORM_LOGIN = ['Name', 'Password']

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
posts       >- attachments -<   resources
"""
class Statuses(db.Model):
    __tablename__ = 'statuses'

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(DEFAULT_LENGTH), unique=True)

    users = db.relationship('Users', backref='status')

class Resource_types(db.Model):
    __tablename__ = 'resource_types'

    id = db.Column(db.Integer, primary_key=True)
    resource_type = db.Column(db.String(DEFAULT_LENGTH), unique=True)

    resources = db.relationship('Resources', backref='type')

class Threads(db.Model):
    __tablename__ = 'threads'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=helpers.time_now)
    updated = db.Column(db.DateTime, default=helpers.time_now)
    post_count = db.Column(db.Integer, default=0)
    archivated = db.Column(db.Boolean, default=False)

    posts = db.relationship('Posts', backref='in_thread')

class Users(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(USERNAME_LENGTH), unique=True)
    password = db.Column(db.String(USER_PASSWROD_LENGTH))
    status = db.Column(
        db.Integer,
        db.ForeignKey(Statuses.id, onupdate='CASCADE', ondelete='RESTRICT'),
        default=STATUS_USER
    )
    registered = db.Column(db.DateTime, default=helpers.time_now)

    resources = db.relationship('Resources', backref='uploaded_by')
    posts = db.relationship('Posts', backref='username')

attachments = db.Table(
    'attachments',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id')),
    db.Column('resource_id', db.Integer, db.ForeignKey('resources.id'))
)

class Posts(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey(Threads.id, onupdate='CASCADE', ondelete='RESTRICT'))
    user_id = db.Column(
        db.Integer,
        db.ForeignKey(Users.id, onupdate='CASCADE', ondelete='SET NULL'),
        default=None
    )
    password = db.Column(db.String(ANON_PASSWROD_LENGTH), default=None)
    date = db.Column(db.DateTime, default=helpers.time_now)
    text = db.Column(db.Text, default=" ")
    has_files = db.Column(db.Boolean, default=False)

    files = db.relationship('Resources', secondary=attachments, backref='in_posts')

class Resources(db.Model):
    __tablename__ = 'resources'

    id = db.Column(db.Integer, primary_key=True)
    resource = db.Column(db.String(RESOURCE_LENGTH))
    resource_type = db.Column(
        db.Integer,
        db.ForeignKey(Resource_types.id, onupdate='CASCADE', ondelete='RESTRICT'),
        default='image'
    )
    user_id = db.Column(db.Integer, db.ForeignKey(Users.id, onupdate='CASCADE', ondelete='SET NULL'))
    uploaded = db.Column(db.DateTime, default=helpers.time_now)

# </db>
# TODO: graphics

@app.route("/")
@app.route("/index")
def index():
    #r = Statuses(status="user")
    #db.session.add(r)
    #db.session.commit()
    #r = Statuses.query.filter_by(status="user").first()
    #print(r)
    #print(r.status)
    return render_template("index.html"), 200


@app.route("/login", methods=['GET', 'POST'])
def login():
    template_form = None

    if request.method == 'GET':
        template_form = FORM_LOGIN
        code = 200

    else:
        username = request.form.get('Name')
        user_password = request.form.get('Password')

        error = False
        if not USERNAME_MIN <= len(username) <= USERNAME_LENGTH:
            flash("Please match the username length.")
            error = True
        if not re.search(USERNAME_PATTERN, username):
            flash("Please match the username format.")
            error = True
        if not USER_PASSWORD_MIN <= len(user_password) <= USER_PASSWROD_LENGTH:
            flash("Please match the password length.")
            error = True

        # TODO: db execute SELECT (login, status) FROM users WHERE login = username AND password = user_password;
        #r = Users.query.filter_by(login=username)
        #print(r)

        if error:
            template_form = FORM_LOGIN
            code = 403
        else:
            flash("Welcome back!")
            code = 200

    return render_template(
        "login.html", form=template_form,
        user_min=USERNAME_MIN, user_max=USERNAME_LENGTH,
        pass_min=USER_PASSWORD_MIN, pass_max=USER_PASSWROD_LENGTH,
        pattern=USERNAME_PATTERN
    ), code


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
