from flask import Flask, url_for, request, session, redirect, render_template, make_response, flash
from markupsafe import escape

from flask_assets import Environment, Bundle

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc

from flask_session import Session

from helpers import *

# TODO: transactions and ACID

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
class Statuses(DB.Model):
    __tablename__ = 'statuses'

    id = DB.Column(DB.Integer, primary_key=True)
    status = DB.Column(DB.String(DEFAULT_LENGTH), unique=True, nullable=False)

    users = DB.relationship('Users', backref='get_status')

    def __repr__(self):
        return f"<status: {self.status}>"


class Resource_types(DB.Model):
    __tablename__ = 'resource_types'

    id = DB.Column(DB.Integer, primary_key=True)
    type = DB.Column(DB.String(DEFAULT_LENGTH), unique=True, nullable=False)

    resources = DB.relationship('Resources', backref='get_type')

    def __repr__(self):
        return f"<resource type: {self.type}>"


class Boards(DB.Model):
    __tablename__ = 'boards'

    id = DB.Column(DB.Integer, primary_key=True)
    short = DB.Column(DB.String(DEFAULT_LENGTH), unique=True, index=True, nullable=False)
    name = DB.Column(DB.String(DEFAULT_LENGTH), unique=True, nullable=False)
    description = DB.Column(DB.String(100), nullable=False)
    thread_count = DB.Column(DB.Integer, default=0, nullable=False)

    threads = DB.relationship('Threads', backref='get_board')

    def __repr__(self):
        return f"<board: {self.short}>"


class Threads(DB.Model):
    __tablename__ = 'threads'

    id = DB.Column(DB.Integer, primary_key=True)
    board_id = DB.Column(DB.Integer, \
        DB.ForeignKey(Boards.id, onupdate='CASCADE', ondelete='RESTRICT'), index=True, nullable=False)
    date = DB.Column(DB.DateTime, default=datetime.datetime.now, nullable=False)
    updated = DB.Column(DB.DateTime, default=datetime.datetime.now, nullable=False)
    post_count = DB.Column(DB.Integer, default=0, nullable=False)
    archivated = DB.Column(DB.Boolean, default=False, nullable=False)

    posts = DB.relationship('Posts', backref='get_thread')

    def __repr__(self):
        return f"<thread: {self.id} (board {self.board_id})>"


class Users(DB.Model):
    __tablename__ = 'users'

    id = DB.Column(DB.Integer, primary_key=True, index=True)
    login = DB.Column(DB.String(USERNAME_LENGTH), unique=True, nullable=False)
    password = DB.Column(DB.String(USER_PASSWORD_LENGTH), nullable=False)
    status = DB.Column(DB.Integer, \
        DB.ForeignKey(Statuses.id, onupdate='CASCADE', ondelete='RESTRICT'), \
        default=STATUS_USER, nullable=False)
    registered = DB.Column(DB.DateTime, default=datetime.datetime.now)

    resources = DB.relationship('Resources', backref='get_user')
    posts = DB.relationship('Posts', backref='get_user')

    def __repr__(self):
        return f"<user: {self.login}>"


attachments = DB.Table(
    'attachments',
    DB.Column('post_id', DB.Integer, DB.ForeignKey('posts.id'), index=True, nullable=False),
    DB.Column('resource_id', DB.Integer, DB.ForeignKey('resources.id'), nullable=False)
)

class Posts(DB.Model):
    __tablename__ = 'posts'

    id = DB.Column(DB.Integer, primary_key=True)
    thread_id = DB.Column(DB.Integer, \
        DB.ForeignKey(Threads.id, onupdate='CASCADE', ondelete='RESTRICT'), index=True, nullable=False)
    user_id = DB.Column(DB.Integer, \
        DB.ForeignKey(Users.id, onupdate='CASCADE', ondelete='SET NULL'), default=None)
    password = DB.Column(DB.String(ANON_PASSWORD_LENGTH), default=None)
    date = DB.Column(DB.DateTime, default=datetime.datetime.now, nullable=False)
    theme = DB.Column(DB.String(DEFAULT_LENGTH), default=None)
    text = DB.Column(DB.Text, default="&nbsp;")
    has_files = DB.Column(DB.Boolean, default=False, nullable=False)

    files = DB.relationship('Resources', secondary=attachments, backref='get_posts')

    def __repr__(self):
        return f"<post: {self.id}>"


class Resources(DB.Model):
    __tablename__ = 'resources'

    id = DB.Column(DB.Integer, primary_key=True, index=True)
    resource = DB.Column(DB.String(RESOURCE_LENGTH), nullable=False)
    type = DB.Column(DB.Integer, \
        DB.ForeignKey(Resource_types.id, onupdate='CASCADE', ondelete='RESTRICT'), \
        default='image', nullable=False)
    user_id = DB.Column(DB.Integer, DB.ForeignKey(Users.id, onupdate='CASCADE', ondelete='SET NULL'))
    uploaded = DB.Column(DB.DateTime, default=datetime.datetime.now)

    def __repr__(self):
        return f"<resource: {self.resource}>"
# </db>


@app.before_first_request
def before_first_request():
    DB.create_all()
    if not Statuses.query.first():
        one = Statuses(status="user")
        two = Statuses(status="moderator")
        three = Statuses(status="administrator")
        DB.session.add_all([one, two, three])
        DB.session.commit()
        print("db: filled statuses table")

    if not Resource_types.query.first():
        one = Resource_types(type="image")
        two = Resource_types(type="text")
        three = Resource_types(type="other")
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
        s = Statuses.query.all()
        one = Users(login="senpai", password=hash_password("qwerty", "senpai"), get_status=s[2])
        two = Users(login="maika", password=hash_password("qwerty", "maika"), get_status=s[1])
        three = Users(login="megumin", password=hash_password("qwerty", "megumin"), get_status=s[1])
        four = Users(login="aoba", password=hash_password("qwerty", "aoba"), get_status=s[0])
        five = Users(login="nene", password=hash_password("qwerty", "nene"), get_status=s[0])
        DB.session.add_all([one, two, three, four, five])
        DB.session.commit()
        print("db: filled users list")

    if not Resources.query.first():
        t = Resource_types.query.filter(Resource_types.type == "image").first()
        u = Users.query.all()
        one = Resources(resource="436456345.png", get_type=t, get_user=u[0])
        two = Resources(resource="126693345.png", get_type=t, get_user=u[1])
        three = Resources(resource="164376090060.png", get_type=t, get_user=u[4])
        four = Resources(resource="546567543546.png", get_type=t, get_user=u[2])
        five = Resources(resource="4365466546.png", get_type=t, get_user=u[3])
        six = Resources(resource="054634534.jpg", get_type=t)
        DB.session.add_all([one, two, three, four, five, six])
        DB.session.commit()
        print("db: filled resources list")

    if not Threads.query.first():
        boards = Boards.query.all()
        thread_id = 1
        for board in boards:
            i = 1
            while i <= 142:
                print(f"db: makes thread {thread_id} on board {board.short}")
                t = Threads(id=thread_id, post_count=2, get_board=board)
                DB.session.add(t)
                p1 = Posts(get_thread=t, theme="test", text=f"thread №{thread_id}", has_files=True)
                DB.session.add(p1)
                file = Resources.query.filter(Resources.id == 6).first()
                p1.files.append(file)
                board.thread_count += 1
                DB.session.commit()
                p2 = Posts(get_thread=t, text=f"reply to {thread_id}")
                DB.session.add(p2)
                DB.session.commit()
                thread_id += 1
                i += 1

        print(f"db: makes hello thread")
        b = boards[0]
        t = Threads(get_board=b)
        DB.session.add(t)
        b.thread_count += 1
        DB.session.commit()
        t = Threads.query.order_by(Threads.id.desc()).first()
        users = Users.query.all()

        p1 = Posts(get_thread=t, get_user=users[0], theme="Hello!", text="Kon'nichiwa!", has_files=True)
        DB.session.add(p1)
        file = Resources.query.filter(Resources.id == 1).first()
        p1.files.append(file)
        t.post_count += 1
        DB.session.commit()

        p2 = Posts(get_thread=t, text="First one!")
        DB.session.add(p2)
        t.post_count += 1
        DB.session.commit()

        p3 = Posts(get_thread=t, text="I'm the strongest!")
        DB.session.add(p3)
        t.post_count += 1
        DB.session.commit()

        p4 = Posts(get_thread=t, get_user=users[1], text="I hope you all will behave like a good boys and girls.", has_files=True)
        DB.session.add(p4)
        file = Resources.query.filter(Resources.id == 2).first()
        p4.files.append(file)
        t.post_count += 1
        DB.session.commit()

        p5 = Posts(get_thread=t, get_user=users[4], text="I wish I could become a programmer and create my own forum too.", has_files=True)
        DB.session.add(p5)
        file = Resources.query.filter(Resources.id == 3).first()
        p5.files.append(file)
        t.post_count += 1
        DB.session.commit()

        p6 = Posts(get_thread=t, get_user=users[2], text="You just have to learn something new and practice regularly, and one day you'll definitely become one. Programming is fun!", has_files=True)
        DB.session.add(p6)
        file = Resources.query.filter(Resources.id == 4).first()
        p6.files.append(file)
        t.post_count += 1
        DB.session.commit()

        p7 = Posts(get_thread=t, get_user=users[3], text="I love you all so much!", has_files=True)
        DB.session.add(p7)
        file = Resources.query.filter(Resources.id == 5).first()
        p7.files.append(file)
        t.post_count += 1
        t.updated = datetime.datetime.now()
        DB.session.commit()
        print("db: filled threads and posts lists")

    global FOOTER
    FOOTER = [b.short for b in Boards.query.all()]


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
    #session['user'] = {'name': "senpai", 'status': "administrator"}
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
        input_name = request.form.get(FORM_LOGIN[0]).strip()
        input_password = request.form.get(FORM_LOGIN[1]).strip()
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
        usr_pattern=USERNAME_PATTERN, pass_pattern=PASSWORD_PATTERN
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
        input_password = request.form.get(FORM_PASSWORD[0]).strip()
        input_new_password = request.form.get(FORM_PASSWORD[1]).strip()
        input_confirmation = request.form.get(FORM_PASSWORD[2]).strip()
        # check for dirty input
        messages = check_login_form("none", input_password)
        messages += check_login_form("none", input_new_password, input_confirmation)

        usr = None
        hashed = None
        if not messages:
            usr = Users.query.filter(Users.login == user['name']).first()
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
        pass_min=USER_PASSWORD_MIN, pass_max=USER_PASSWORD_LENGTH,
        pass_pattern=PASSWORD_PATTERN
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
        input_name = request.form.get(FORM_REGISTER[0]).strip()
        input_password = request.form.get(FORM_REGISTER[1]).strip()
        input_confirmation = request.form.get(FORM_REGISTER[2]).strip()
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
        usr_pattern=USERNAME_PATTERN, pass_pattern=PASSWORD_PATTERN
    ), code


@app.route("/board/<board>/")
@app.route("/board/<board>/<int:page>/")
def board(board, page=1):
    board = Boards.query.filter_by(short=escape(board)).first()
    if not board or page <= 0:
        return redirect(url_for('index')), 303

    start = page * 10 - 10
    stop = page * 10
    threads_on_page = Threads.query.filter(Threads.board_id == board.id). \
        order_by(Threads.updated.desc()).slice(start, stop).all()
    if not threads_on_page:
        return redirect(url_for('index')), 303

    pages_total = int(board.thread_count / 10) + (board.thread_count % 10 > 0)
    pages_total = [i for i in range(1, pages_total + 1)]
    base_url = f"/board/{board.short}/"

    # fill threads with data and posts
    threads_with_posts = []
    for thread in threads_on_page:
        op = Posts.query.filter(Posts.thread_id == thread.id).order_by(Posts.date).first()

        last_five_posts = []
        hidden_posts = False
        if thread.post_count > 1:
            last_five_posts = Posts.query.filter(Posts.thread_id == thread.id, Posts.id != op.id). \
                order_by(Posts.date.desc()).limit(5).all()

            # turn posts back in order
            last_five_posts.sort(key=lambda p: p.date)

            if thread.post_count > 6:
                hidden_posts = True

        t = {'post_count': thread.post_count, 'hidden_posts': hidden_posts, 'op': op,
             'archivated': thread.archivated, 'posts': last_five_posts}
        threads_with_posts.append(t)

    # fill posts with data
    for thread in threads_with_posts:
        new = []
        for post in thread['posts']:
            username = None
            files = []

            if post.user_id: # TODO
                u = Users.query.filter(Users.id == post.user_id).first()
                username = u.login

            if post.has_files: # TODO
                for f in post.files:
                    p = "./data/?"
                    files.append({'resource': f.resource, 'path': p})

            p = {'id': post.id, 'date': post.date.strftime(TIME_FORMAT), \
                 'author': username, 'text': post.text, 'files': files}
            new.append(p)

        thread['posts'] = new

    return render_template(
        "board.html", nav=FOOTER,
        short_name=board.short, long_name=board.name,
        description=board.description, base_url=base_url,
        threads=threads_with_posts, pages=pages_total
    ), 200 # TODO threads count and other


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
