from flask import url_for, request, session, redirect, render_template, flash

from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from flask_config import app
from database import db, Statuses, Resource_types, Boards, Threads, Users, Posts, Resources
from flask_forms import LoginForm, AnonymizeForm, ChangePassword, RegisterForm, MakePost, MakeThread
from constants import *
import helpers

# TODO: file size
# TODO: transactions and ACID
# TODO: pep8
# TODO: color theme
# TODO: clear and simplify input
# TODO: style posts width


@app.before_first_request
def before_first_request():
    helpers.fill_the_database()
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


@app.route("/user/<username>", methods=['GET', 'POST'])
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


@app.route("/board/<board>/", methods=['GET', 'POST'])
@app.route("/board/<board>/<int:page>/")
def board(board, page=1):
    board = Boards.query.filter_by(short=escape(board)).first()
    if not board:
        return redirect(url_for('index')), 303
    elif page <= 0:
        return redirect(url_for('board', board=board.short, page=1)), 303
    else:
        form_thread = MakeThread()
        base_url = f"/board/{board.short}/"

    if form_thread.validate_on_submit():
        user = session.get('user')
        board = helpers.make_a_post(form_thread, board, user)

    try:
        pages_total, threads_with_posts = helpers.generete_page(page, board)
    except PageDoesNotExistError:
        redirect(url_for('board', board=board.short, page=1)), 303
    except BoardIsEmptyError:
        redirect(url_for('index')), 303

    return render_template("board.html",  # TODO user don't ned to see a password field
        nav=FOOTER, form_thread=form_thread, base_url=base_url,
        thread_count=board.thread_count, short_name=board.short,
        long_name=board.name, description=board.description,
        threads=threads_with_posts, pages=pages_total,
        pass_max=ANON_PASSWORD_LENGTH, theme_max=DEFAULT_LENGTH, filesize=MAX_FILE_SIZE,
    ), 200


if __name__ == '__main__':
    app.run()
