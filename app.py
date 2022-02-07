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
    TEMPLATES_AUTO_RELOAD=True
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
    str(scss_dir / "menu.scss"),
    str(scss_dir / "board.scss"),
]
css_file = str(CWD / "static" / "css" / "styles.css")

assets = Environment(app)
assets.url = app.static_url_path
scss = Bundle(scss_list, filters='pyscss', output=css_file)
assets.register('styles', scss)
# </scss>

# <db>
app.config.update(
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_DATABASE_URI="sqlite:///forum.db"
)
DB = SQLAlchemy(app)
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
# TODO: indexes
class Statuses(DB.Model):
    __tablename__ = 'statuses'

    id = DB.Column(DB.Integer, primary_key=True)
    status = DB.Column(DB.String(DEFAULT_LENGTH), unique=True, nullable=False)

    users = DB.relationship('Users', backref='has_status')

    def __repr__(self):
        return f"<status: {self.status}>"

class Resource_types(DB.Model):
    __tablename__ = 'resource_types'

    id = DB.Column(DB.Integer, primary_key=True)
    resource_type = DB.Column(DB.String(DEFAULT_LENGTH), unique=True)

    resources = DB.relationship('Resources', backref='has_type')

    def __repr__(self):
        return f"<resource type: {self.resource_type}>"

class Boards(DB.Model):
    __tablename__ = 'boards'

    id = DB.Column(DB.Integer, primary_key=True)
    short = DB.Column(DB.String(DEFAULT_LENGTH), unique=True)
    name = DB.Column(DB.String(DEFAULT_LENGTH), unique=True)
    description = DB.Column(DB.String(100))
    thread_count = DB.Column(DB.Integer, default=0)

    threads = DB.relationship('Threads', backref='on_board')

    def __repr__(self):
        return f"<board: {self.short}>"

class Threads(DB.Model): # TODO: thread theme
    __tablename__ = 'threads'

    id = DB.Column(DB.Integer, primary_key=True)
    board_id = DB.Column(DB.Integer, DB.ForeignKey(Boards.id, onupdate='CASCADE', ondelete='RESTRICT'))
    date = DB.Column(DB.DateTime, default=datetime.datetime.now)
    updated = DB.Column(DB.DateTime, default=datetime.datetime.now)
    post_count = DB.Column(DB.Integer, default=0)
    archivated = DB.Column(DB.Boolean, default=False)

    posts = DB.relationship('Posts', backref='in_thread')

    def __repr__(self):
        return f"<thread: {self.id} (board {self.board_id})>"

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
    registered = DB.Column(DB.DateTime, default=datetime.datetime.now)

    resources = DB.relationship('Resources', backref='uploaded_by')
    posts = DB.relationship('Posts', backref='author')

    def __repr__(self):
        return f"<user: {self.login}>"

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
    date = DB.Column(DB.DateTime, default=datetime.datetime.now)
    text = DB.Column(DB.Text, default="&nbsp;")
    has_files = DB.Column(DB.Boolean, default=False)

    files = DB.relationship('Resources', secondary=attachments, backref='in_posts')

    def __repr__(self):
        return f"<post: {self.id}>"

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
    uploaded = DB.Column(DB.DateTime, default=datetime.datetime.now)

    def __repr__(self):
        return f"<resource: {self.resource}>"
# </db>


@app.before_first_request
def before_first_request():
    global FOOTER
    FOOTER = [b.short for b in Boards.query.all()]

    if not Statuses.query.first():
        one = Statuses(status="user")
        two = Statuses(status="moderator")
        three = Statuses(status="administrator")
        DB.session.add_all([one, two, three])
        DB.session.commit()
        print("db: filled statuses table")

    if not Resource_types.query.first():
        one = Resource_types(resource_type="image")
        two = Resource_types(resource_type="text")
        three = Resource_types(resource_type="other")
        DB.session.add_all([one, two, three])
        DB.session.commit()
        print("db: filled resource types")

    if not Boards.query.first():
        one = Boards(short="b", name="brotherhood", description="polite communication")
        two = Boards(short="a", name="animation", description="Japanese and other kinds of anime")
        three = Boards(short="u", name="university", description="knowledge exchange")
        DB.session.add_all([one, two, three])
        DB.session.commit()
        print("db: filled boards list")

    if not Users.query.first():
        one = Users(login="senpai", password=hash_password("qwerty", "senpai"), status=3)
        DB.session.add(one)
        DB.session.commit()
        print("db: filled users list")

    # TODO: fill threads and posts
    """
    i = 31
    while i <= 122:
        print(i)
        t = Threads(board_id=1, post_count=1)
        DB.session.add(t)
        DB.session.commit()
        p = Posts(thread_id=i, text="test")
        DB.session.add(p)
        DB.session.commit()
        b = Boards.query.filter_by(id=1).first()
        b.thread_count += 1
        DB.session.commit()
        sleep(1)
        i += 1
    """


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
    #username = "senpai"
    #u = Users.query.filter_by(login=username).first()
    #u1, u2 = DB.session.query(Users.login, Statuses.status).join(Statuses).filter(Users.login==username).first()
    #print(u1, u2)
    session['user'] = {'name': "senpai", 'status': "administrator"}
    return render_template("index.html", nav=FOOTER), 200


@app.route("/introduction", methods=['GET', 'POST'])
def introduction():
    template_form = None

    if request.method == 'GET':
        user = session.get('user')
        if user:
            return redirect(url_for('index')), 303
        else:
            template_form = FORM_LOGIN
            code = 200

    else:
        input_name = request.form.get(FORM_LOGIN[0])
        input_password = request.form.get(FORM_LOGIN[1])
        escape_name = escape(input_name)
        # check for dirty input
        messages = check_login_form(input_name, input_password)

        status = None
        if not messages:
            user, status = DB.session.query(Users, Statuses.status). \
                join(Statuses).filter(Users.login == escape_name).first()
            if not user:
                messages.append("Username not found.")
            elif not hash_password(input_password, input_name) == user.password:
                messages.append("Incorrect password.")

        if messages:
            for message in messages:
                flash(message)
            template_form = FORM_LOGIN
            code = 400
        else:
            session['user'] = {'name': escape_name, 'status': status}
            flash(f"Welcome back, {escape_name}!")
            code = 200

    return render_template(
        "introduction.html", nav=FOOTER, form=template_form,
        user_min=USERNAME_MIN, user_max=USERNAME_LENGTH,
        pass_min=USER_PASSWORD_MIN, pass_max=USER_PASSWORD_LENGTH,
        pattern=USERNAME_PATTERN
    ), code


@app.route("/anonymization", methods=['GET', 'POST'])
def anonymization():
    user = session.get('user')
    if request.method == 'GET':
        if not user:
            return redirect(url_for('index')), 303
        else:
            return render_template("anonymization.html", nav=FOOTER, form="anonymize"), 200

    else:
        if request.form.get("anonymize"):
            session['user'] = None
        return redirect(url_for('index')), 303


@app.route("/user/<username>", methods=['GET', 'POST'])
def personal(username):
    template_form = None
    user = session.get('user')

    if request.method == 'GET':
        if not user:
            return redirect(url_for('index')), 303
        else:
            template_form = FORM_PASSWORD
            code = 200

    else:
        input_password = request.form.get(FORM_PASSWORD[0])
        input_new_password = request.form.get(FORM_PASSWORD[1])
        input_confirmation = request.form.get(FORM_PASSWORD[2])
        # check for dirty input
        messages = check_login_form("none", input_password)
        messages += check_login_form("none", input_new_password, input_confirmation)

        usr = None
        hashed = None
        if not messages:
            usr = Users.query.filter_by(login = user['name']).first()
            if not usr.password == hash_password(input_password, usr.login):
                messages.append("Check out your old password.")
            else:
                hashed = hash_password(input_new_password, usr.login)
                if usr.password == hashed:
                    messages.append("This is the same password.")

        if not messages:
            usr.password = hashed
            try:
                DB.session.commit()
            except exc.SQLAlchemyError:
                messages.append("Something got wrong :(")

        if messages:
            for message in messages:
                flash(message)
            template_form = FORM_PASSWORD
            code = 400
        else:
            flash(f"Password changed.")
            code = 200

    return render_template(
        "personal.html", nav=FOOTER, form=template_form,
        pass_min=USER_PASSWORD_MIN, pass_max=USER_PASSWORD_LENGTH
    ), code


@app.route("/register", methods=['GET', 'POST'])
def register():
    template_form = None

    if request.method == 'GET':
        user = session.get('user')
        if user:
            return redirect(url_for('index')), 303
        else:
            template_form = FORM_REGISTER
            code = 200

    else:
        input_name = request.form.get(FORM_REGISTER[0])
        input_password = request.form.get(FORM_REGISTER[1])
        input_confirmation = request.form.get(FORM_REGISTER[2])
        escape_name = escape(input_name)
        # check for dirty input
        messages = check_login_form(input_name, input_password, input_confirmation)

        if not messages:
            user = Users(login=escape_name, password=hash_password(input_password, input_name))
            DB.session.add(user)
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

            session['user'] = {'name': escape_name, 'status': STATUS_USER}
            flash(f"Hello, {escape_name}!")
            code = 200

    return render_template(
        "register.html", nav=FOOTER, form=template_form,
        user_min=USERNAME_MIN, user_max=USERNAME_LENGTH,
        pass_min=USER_PASSWORD_MIN, pass_max=USER_PASSWORD_LENGTH,
        pattern=USERNAME_PATTERN
    ), code


@app.route("/board/<board>/")
@app.route("/board/<board>/<int:page>/")
def board(board, page=1):
    code = 200
    board = Boards.query.filter_by(short=escape(board)).first()
    if not board or page <= 0:
        return redirect(url_for('index')), 303

    start = page * 10 - 10
    stop = page * 10
    threads_on_page = Threads.query.filter(Threads.board_id == board.id). \
        order_by(Threads.updated).slice(start, stop).all()
    if not threads_on_page:
        return redirect(url_for('index')), 303

    t = len(Threads.query.all())
    pages_total = int(t / 10) + (t % 10 > 0)
    pages_total = [i for i in range(1, pages_total + 1)]
    base_url = f"/board/{board.short}/"

    # fill threads with data and posts
    threads_with_posts = []
    for thread in threads_on_page:
        first_five_posts = Posts.query.filter(Posts.thread_id == thread.id). \
            order_by(Posts.date.desc()).limit(5).all()

        # turn posts back in order
        if len(first_five_posts) > 1:
            first_five_posts.sort(key=lambda p: p.date)

        t = {'post_count': thread.post_count, 'archivated': thread.archivated, 'posts': first_five_posts}
        threads_with_posts.append(t)

    # TODO: sort threads by updated

    # fill posts with data
    for thread in threads_with_posts:
        new = []
        for post in thread['posts']:
            username = None
            files = []

            if post.user_id: #! fix it
                username = Users.query.filter(Users.id == post.user_id).first()

            if post.has_files:
                for f in post.files:
                    files.append(f.resource)

            p = {'id': post.id, 'date': post.date.strftime(TIME_FORMAT), \
                 'author': username, 'text': post.text, 'files': files}
            new.append(p)

        thread['posts'] = new

    return render_template(
        "board.html", nav=FOOTER,
        short_name=board.short, long_name=board.name,
        description=board.description, base_url=base_url,
        threads=threads_with_posts, pages=pages_total
    ), code


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
