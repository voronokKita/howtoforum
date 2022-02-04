from flask import Flask, url_for, request, session, redirect, render_template, make_response, flash
from markupsafe import escape

from flask_assets import Environment, Bundle

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc

from flask_session import Session

from helpers import *


CWD = pathlib.Path.cwd()
app = Flask(__name__)
app.config.update(
    ENV='development',
    DEBUG=True,
    SECRET_KEY=secrets.token_hex(),
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=1),
    TEMPLATES_AUTO_RELOAD=True,

    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_DATABASE_URI="sqlite:///forum.db"
)

# <sessions>
app.config['SESSION_FILE_DIR'] = mkdtemp()
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
# </sessions>

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

# <DB>
DB = SQLAlchemy(app)
"""
statuses, users, resources,
resource_types, threads, posts, attachments

statuses    -- one-to-many -<   users
users       -- one-to-many -<   posts
users       -- one-to-many -<   resources
resource_types one-to-many -<   resources
threads     -- one-to-many -<   posts
posts       >- attachments -<DB   resources
"""
class Statuses(DB.Model):
    __tablename__ = 'statuses'

    id = DB.Column(DB.Integer, primary_key=True)
    status = DB.Column(DB.String(DEFAULT_LENGTH), unique=True)

    users = DB.relationship('Users', backref='has_status')

class Resource_types(DB.Model):
    __tablename__ = 'resource_types'

    id = DB.Column(DB.Integer, primary_key=True)
    resource_type = DB.Column(DB.String(DEFAULT_LENGTH), unique=True)

    resources = DB.relationship('Resources', backref='has_type')

class Threads(DB.Model):
    __tablename__ = 'threads'

    id = DB.Column(DB.Integer, primary_key=True)
    date = DB.Column(DB.DateTime, default=time_now)
    updated = DB.Column(DB.DateTime, default=time_now)
    post_count = DB.Column(DB.Integer, default=0)
    archivated = DB.Column(DB.Boolean, default=False)

    posts = DB.relationship('Posts', backref='in_thread')

class Users(DB.Model):
    __tablename__ = 'users'

    id = DB.Column(DB.Integer, primary_key=True)
    login = DB.Column(DB.String(USERNAME_LENGTH), unique=True)
    password = DB.Column(DB.String(USER_PASSWORD_LENGTH))
    status = DB.Column(
        DB.Integer,
        DB.ForeignKey(Statuses.id, onupdate='CASCADE', ondelete='RESTRICT'),
        default=STATUS_USER
    )
    registered = DB.Column(DB.DateTime, default=time_now)

    resources = DB.relationship('Resources', backref='uploaded_by')
    posts = DB.relationship('Posts', backref='author')

attachments = DB.Table(
    'attachments',
    DB.Column('post_id', DB.Integer, DB.ForeignKey('posts.id')),
    DB.Column('resource_id', DB.Integer, DB.ForeignKey('resources.id'))
)

class Posts(DB.Model):
    __tablename__ = 'posts'

    id = DB.Column(DB.Integer, primary_key=True)
    thread_id = DB.Column(DB.Integer, DB.ForeignKey(Threads.id, onupdate='CASCADE', ondelete='RESTRICT'))
    user_id = DB.Column(
        DB.Integer,
        DB.ForeignKey(Users.id, onupdate='CASCADE', ondelete='SET NULL'),
        default=None
    )
    password = DB.Column(DB.String(ANON_PASSWORD_LENGTH), default=None)
    date = DB.Column(DB.DateTime, default=time_now)
    text = DB.Column(DB.Text, default=" ")
    has_files = DB.Column(DB.Boolean, default=False)

    files = DB.relationship('Resources', secondary=attachments, backref='in_posts')

class Resources(DB.Model):
    __tablename__ = 'resources'

    id = DB.Column(DB.Integer, primary_key=True)
    resource = DB.Column(DB.String(RESOURCE_LENGTH))
    resource_type = DB.Column(
        DB.Integer,
        DB.ForeignKey(Resource_types.id, onupdate='CASCADE', ondelete='RESTRICT'),
        default='image'
    )
    user_id = DB.Column(DB.Integer, DB.ForeignKey(Users.id, onupdate='CASCADE', ondelete='SET NULL'))
    uploaded = DB.Column(DB.DateTime, default=time_now)
# </DB>


@app.route("/")
@app.route("/index")
def index():
    #r = Statuses(status="user")
    #DB.session.add(r)
    #DB.session.commit()
    #r = Statuses.query.filter_by(status="user").first()
    #a = Posts(thread_id=1, user_id=1, text="Kon'nichiwa!", has_files=True)
    #b = Resources(resource='images', resource_type=1, user_id=1)
    #DB.session.add_all([a, b])
    #a.files.append(b)
    #DB.session.commit()
    return render_template("index.html"), 200


@app.route("/introduction", methods=['GET', 'POST'])
def introduction():
    template_form = None

    if request.method == 'GET':
        username = session.get('username')
        if username:
            return redirect(url_for('index')), 303
        else:
            template_form = FORM_LOGIN
            code = 200

    else:
        input_name = request.form.get(FORM_LOGIN[0])
        input_password = request.form.get(FORM_LOGIN[1])
        escape_name = escape(input_name)

        messages = check_login_form(input_name, input_password)

        if not messages:
            result = Users.query.filter_by(login=escape_name).first()
            if not result:
                messages.append("Username not found.")
            elif not hash_password(input_password, input_name) == result.password:
                messages.append("Incorrect password.")

        if messages:
            for message in messages:
                flash(message)
            template_form = FORM_LOGIN
            code = 400
        else:
            session['username'] = escape_name
            flash(f"Welcome back, {escape_name}!")
            code = 200

    return render_template(
        "introduction.html", form=template_form,
        user_min=USERNAME_MIN, user_max=USERNAME_LENGTH,
        pass_min=USER_PASSWORD_MIN, pass_max=USER_PASSWORD_LENGTH,
        pattern=USERNAME_PATTERN
    ), code


@app.route("/anonymization", methods=['GET', 'POST'])
def anonymization():
    username = session.get('username')
    if request.method == 'GET':
        if not username:
            return redirect(url_for('index')), 303
        else:
            return render_template("anonymization.html", form="anonymize"), 200
    else:
        if request.form.get("anonymize"):
            session['username'] = None
        return redirect(url_for('index')), 303


@app.route("/register", methods=['GET', 'POST'])
def register():
    template_form = None

    if request.method == 'GET':
        username = session.get('username')
        if username:
            return redirect(url_for('index')), 303
        else:
            template_form = FORM_REGISTER
            code = 200

    else:
        input_name = request.form.get(FORM_REGISTER[0])
        input_password = request.form.get(FORM_REGISTER[1])
        input_confirmation = request.form.get(FORM_REGISTER[2])
        escape_name = escape(input_name)

        messages = check_login_form(input_name, input_password, input_confirmation)

        if not messages:
            u = Users(login=escape_name, password=hash_password(input_password, input_name))
            DB.session.add(u)
            try:
                DB.session.commit()
            except exc.IntegrityError:
                messages.append("Username already exist.")
            except exc.SQLAlchemyError:
                messages.append("Wrong request.")

        if messages:
            for message in messages:
                flash(message)
            template_form = FORM_REGISTER
            code = 400
        else:
            session['username'] = escape_name
            flash(f"Hello, {escape_name}!")
            code = 200

    return render_template(
        "register.html", form=template_form,
        user_min=USERNAME_MIN, user_max=USERNAME_LENGTH,
        pass_min=USER_PASSWORD_MIN, pass_max=USER_PASSWORD_LENGTH,
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
