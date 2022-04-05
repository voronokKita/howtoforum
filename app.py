from flask import url_for, request, session, redirect, render_template, flash

from flask_config import app
from database import db, Statuses, Resource_types, Boards, Threads, Users, Posts, Resources
from flask_forms import LoginForm, AnonymizeForm, ChangePassword, RegisterForm, MakePost, MakeThread, DeletePosts
from constants import *
import helpers

# TODO: transactions and ACID
# TODO: pep8
# TODO: color theme
# TODO: style posts width


@app.before_first_request
def before_first_request():
    #helpers.fill_the_database()
    global FOOTER
    FOOTER = [b.short for b in Boards.query.all()]


@app.route("/")
@app.route("/index")
def index():
    #session['user'] = {'name': "senpai", 'status': "administrator"}
    return render_template("index.html", nav=FOOTER), 200


@app.route("/introduction", methods=['GET', 'POST'])
def introduction():
    form = LoginForm()
    code = 200

    if request.method == 'GET' and session.get('user'):
        return redirect(url_for('index')), 303

    elif form.validate_on_submit():
        messages = []
        if not re.fullmatch(USERNAME_PATTERN, form.name.data):
            messages.append("The username format doesn't match.")

        user = None
        if not messages:
            user = Users.query.filter_by(login=escape(form.name.data)).first()
            if not user:
                messages.append("Username not found.")
            elif not user.password == helpers.hash_password(form.password.data, form.name.data):
                messages.append("Incorrect password.")

        if messages:
            for message in messages:
                flash(message)
            code = 400
        else:
            session['user'] = {'name': user.login, 'status': user.get_status.status}
            flash(f"Welcome back, {user.login}!")
            form = None

    return render_template("introduction.html", nav=FOOTER, form=form, usr_pattern=USERNAME_PATTERN), code


@app.route("/anonymization", methods=['GET', 'POST'])
def anonymization():
    form = AnonymizeForm()

    if request.method == 'GET' and not session.get('user'):
        return redirect(url_for('index')), 303

    elif form.validate_on_submit():
        session['user'] = None
        return redirect(url_for('index')), 303

    return render_template("anonymization.html", nav=FOOTER, form=form), 200


@app.route("/user:<username>", methods=['GET', 'POST'])
def personal(username):
    user = session.get('user')
    form = ChangePassword()
    code = 200

    if request.method == 'GET' and not user:
        return redirect(url_for('index')), 303

    elif form.validate_on_submit():
        hashed = None
        user = Users.query.filter_by(login=user['name']).first()
        messages = []
        if not user.password == helpers.hash_password(form.old_password.data, user.login):
            messages.append("Check out your old password.")
        else:
            hashed = helpers.hash_password(form.new_password.data, user.login)
            if user.password == hashed:
                messages.append("This is the same old password.")

        if not messages:
            user.password = hashed
            try:
                db.session.commit()
            except SQLAlchemyError:
                messages.append("Something got wrong :(")

        if messages:
            for message in messages:
                flash(message)
            code = 400
        else:
            flash(f"Password changed.")
            form = None
            code = 200

    return render_template("personal.html", nav=FOOTER, form=form, \
        pass_min=USER_PASSWORD_MIN, pass_max=USER_PASSWORD_LENGTH), code


@app.route("/register", methods=['GET', 'POST'])
def register():
    user = session.get('user')
    form = RegisterForm()
    code = 200

    if request.method == 'GET' and user:
        return redirect(url_for('index')), 303

    elif form.validate_on_submit():
        messages = []
        if not re.fullmatch(USERNAME_PATTERN, form.name.data):
            messages.append("The username format doesn't match.")

        if not messages:
            status = Statuses.query.first()
            user = Users(login=escape(form.name.data), get_status=status, \
                    password=helpers.hash_password(form.password.data, form.name.data))
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                messages.append("Username already exist.")
            except SQLAlchemyError:
                messages.append("Wrong request.")

        if messages:
            for message in messages:
                flash(message)
            code = 400
        else:
            session['user'] = {'name': user.login, 'status': user.get_status.status}
            flash(f"Hello, {user.login}!")
            form = None
            code = 200

    return render_template("register.html",
        nav=FOOTER, form=form, usr_pattern=USERNAME_PATTERN,
        user_min=USERNAME_MIN, user_max=USERNAME_LENGTH,
        pass_min=USER_PASSWORD_MIN, pass_max=USER_PASSWORD_LENGTH
    ), code


@app.route("/board:<board>/", methods=['GET', 'POST'])
@app.route("/board:<board>/page:<int:page>/")
def board(board, page=1):
    board = Boards.query.filter_by(short=escape(board)).first()
    if not board:
        return redirect(url_for('index')), 303
    elif page <= 0:
        return redirect(url_for('board', board=board.short, page=1)), 303

    form_thread = MakeThread()
    form_delete = DeletePosts()
    base_url = f"/board:{board.short}/"

    delete_post = False
    if form_delete.validate_on_submit():
        form_delete = form_delete_handler(form_delete)
        delete_post = True
    else:
        form_delete.posts.errors = []

    if not delete_post:
        if form_thread.validate_on_submit():
            form_thread, board = posting_form_handler(form_thread, board)

    try:
        pages_total, threads_with_posts = helpers.generete_board_page(page, board)
    except PageOutOfRangeError:
        return redirect(url_for('board', board=board.short, page=1)), 303
    except BoardIsEmptyError:
        return redirect(url_for('index')), 303

    return render_template("board.html",
        nav=FOOTER, form_main=form_thread, form_delete=form_delete, base_url=base_url, page=page,
        thread_count=board.thread_count, short_name=board.short,
        long_name=board.name, description=board.description,
        threads=threads_with_posts, pages=pages_total,
        pass_max=ANON_PASSWORD_LENGTH, theme_max=DEFAULT_LENGTH, filesize=MAX_FILE_SIZE,
    ), 200


@app.route("/board:<board>/thread:<int:thread>/", methods=['GET', 'POST'])
def thread(board, thread):
    board = Boards.query.filter_by(short=escape(board)).first()
    thread = Threads.query.filter_by(id=escape(thread)).first()
    if not board:
        return redirect(url_for('index')), 303
    elif not thread:
        return redirect(url_for('board', board=board.short, page=1)), 303

    base_url = f"/board:{board.short}/thread:{thread.id}/"
    form_post = MakePost()
    form_post.thread_id.data = thread.id

    if form_post.validate_on_submit():
        if not form_post.thread_id.data == thread.id:
            form_post.thread_id.errors.append(M_WRONG)
        else:
            form_post, board, thread = posting_form_handler(form_post, board, thread)

    thread = helpers.generete_thread_page(thread)

    return render_template("thread.html",
        nav=FOOTER, form_main=form_post, base_url=base_url,
        short_name=board.short, long_name=board.name, thread=thread,
        pass_max=ANON_PASSWORD_LENGTH, theme_max=DEFAULT_LENGTH, filesize=MAX_FILE_SIZE,
    ), 200


@app.route("/board:<board>/thread:<int:thread>/post:<int:post>", methods=['GET'])
def post(board, thread, post):
    board = Boards.query.filter_by(short=escape(board)).first()
    thread = Threads.query.filter_by(id=escape(thread)).first()
    post = Posts.query.filter(Posts.thread_id == thread.id, Posts.id == escape(post)).first()
    if not board:
        return redirect(url_for('index')), 303
    elif not thread:
        return redirect(url_for('board', board=board.short, page=1)), 303
    elif not post:
        return redirect(url_for('thread', board=board.short, thread=thread.id))

    base_url = f"/board:{board.short}/thread:{thread.id}/post:{post.id}"

    p = helpers.fill_post(post)

    return render_template("post.html",
        nav=FOOTER, base_url=base_url, board_long_name=board.name, thread=thread.id, post=p
    ), 200


@app.route("/delete", methods=['POST'])
def delete_posts():
    return "OK"


"""
def moderation(board, page=1, thread=0, post=0):
    user = session.get('user')
    if not user or user['status'] not in (STATUS_MOD, STATUS_ADMIN):
        flash("Access not allowed.")
        return redirect(url_for('index')), 303

    # 1 check input
    error = False
    board = Boards.query.filter_by(short=escape(board)).first()
    post = Posts.query.filter_by(id=escape(post)).first()
    if not board or not post:
        error = True
    elif thread:
         thread = Threads.query.filter_by(id=escape(thread)).first()
         if not thread:
             error = True
    if error:
        flash(M_WRONG)
        return redirect(url_for('index')), 303
    elif not thread and page <= 1:
        page = 1

    # 2 working
    # TODO


    if thread:
        return redirect(url_for('thread', board=board, thread=thread)), 200
    else:
        return redirect(url_for('board', board=board, page=page)), 200
    """


def form_delete_handler(form_delete):
    data = form_delete.posts.data
    datas = [p.strip() for p in data.split(',') if p.strip()]

    numbers = []
    for data in datas:
        try:
            numbers.append(int(data))
        except TypeError:
            continue

    posts = []
    for num in numbers:
        post = Posts.query.filter_by(id=num)
        if post:
            posts.append(post)

    if not posts:
        # error
        pass

    for posts in posts:
        # what is user?
        # what is password?
        # is it a thread?
        pass

    return form_delete


def posting_form_handler(form, board, thread=None):
    user = session.get('user')
    try:
        board = helpers.make_a_post(form, board, user, thread)
    except EmptyPostError as error:
        form.submit.errors.append(error)
    except DataAlreadyExistsError or BaseCriticalError as error:
        form.submit.errors.append(error)
        db.session.rollback()

    return (form, board) if not thread else (form, board, thread)


if __name__ == '__main__':
    app.run()
