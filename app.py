from flask import url_for, request, session, redirect, render_template, flash
from markupsafe import escape

from sqlalchemy import exc

from flask_config import app
from database import db, Statuses, Resource_types, Boards, Threads, Users, Posts, Resources
from flask_forms import LoginForm, AnonymizeForm, ChangePassword, RegisterForm
from helpers import check_form, hash_password, fill_the_database
from constants import *

# TODO: transactions and ACID
# TODO pep8


@app.before_first_request
def before_first_request():
    # fill_the_database()
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
        messages = check_form(form.name.data, form.password.data)

        user = None
        if not messages:
            user = Users.query.filter(Users.login == escape(form.name.data)).first()
            if not user:
                messages.append("Username not found.")
            elif not user.password == hash_password(form.password.data, form.name.data):
                messages.append("Incorrect password.")

        if messages:
            for message in messages:
                flash(message)
            code = 400
        else:
            session['user'] = {'name': user.login, 'status': user.get_status.status}
            flash(f"Welcome back, {user.login}!")
            form = None

    return render_template("introduction.html", nav=FOOTER, form=form, \
        usr_pattern=USERNAME_PATTERN, pass_pattern=PASSWORD_PATTERN), code


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
        messages = check_form("none", form.old_password.data)
        messages += check_form("none", form.new_password.data, form.confirmation.data)

        hashed = None
        if not messages:
            user = Users.query.filter(Users.login == user['name']).first()

            if not user.password == hash_password(form.old_password.data, user.login):
                messages.append("Check out your old password.")
            else:
                hashed = hash_password(form.new_password.data, user.login)
                if user.password == hashed:
                    messages.append("This is the same old password.")

        if not messages:
            user.password = hashed
            try:
                db.session.commit()
            except exc.SQLAlchemyError:
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
        pass_pattern=PASSWORD_PATTERN, pass_min=USER_PASSWORD_MIN, pass_max=USER_PASSWORD_LENGTH), code


@app.route("/register", methods=['GET', 'POST'])
def register():
    user = session.get('user')
    form = RegisterForm()
    code = 200

    if request.method == 'GET' and user:
        return redirect(url_for('index')), 303

    elif form.validate_on_submit():
        messages = check_form(form.name.data, form.password.data, form.confirmation.data)

        if not messages:
            status = Statuses.query.first()
            user = Users(login=escape(form.name.data), get_status=status, \
                password=hash_password(form.password.data, form.name.data))
            db.session.add(user)
            try:
                db.session.commit()
            except exc.IntegrityError:
                messages.append("Username already exist.")
            except exc.SQLAlchemyError:
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

    return render_template(
        "register.html", nav=FOOTER, form=form,
        user_min=USERNAME_MIN, user_max=USERNAME_LENGTH,
        pass_min=USER_PASSWORD_MIN, pass_max=USER_PASSWORD_LENGTH,
        usr_pattern=USERNAME_PATTERN, pass_pattern=PASSWORD_PATTERN
    ), code


@app.route("/board/<board>/")
@app.route("/board/<board>/<int:page>/")
def board(board, page=1):
    board = Boards.query.filter(Boards.short == escape(board)).first()
    if not board:
        return redirect(url_for('index')), 303
    elif page <= 0:
        return redirect(url_for('board', board=board.short, page=1)), 303

    start = page * 10 - 10
    stop = page * 10
    threads_on_page = Threads.query.filter(Threads.board_id == board.id). \
        order_by(Threads.updated.desc()).slice(start, stop).all()
    if not threads_on_page:
        return redirect(url_for('board', board=board.short, page=1)), 303

    pages_total = int(board.thread_count / 10) + (board.thread_count % 10 > 0)
    pages_total = [i for i in range(1, pages_total + 1)]
    base_url = f"/board/{board.short}/"

    # fill threads with data and posts
    threads_with_posts = []
    for thread in threads_on_page:
        op = thread.posts[0]

        last_posts = []
        hidden_posts = False
        if thread.post_count > 1:
            posts = thread.posts[1:]
            l = len(posts)
            n = POSTS_PER_THREAD * -1 if l >= POSTS_PER_THREAD else l * -1
            last_posts = posts[n:]

            if l > POSTS_PER_THREAD:
                hidden_posts = thread.post_count - POSTS_PER_THREAD - 1

        t = {'post_count': thread.post_count, 'hidden_posts': hidden_posts,
             'archivated': thread.archivated, 'posts': [op] + last_posts}
        threads_with_posts.append(t)

    # fill posts with data
    for thread in threads_with_posts:
        old_list = thread['posts']

        new_list = []
        for post in old_list:
            username = post.get_user.login if post.user_id else None

            files = []
            if post.has_files:
                for f in post.files:
                    p = f"/static/data/{f.get_type.type}/"
                    files.append({'name': f.resource, 'path': p})

            p = {'id': post.id, 'date': post.date.strftime(TIME_FORMAT),
                 'author': username, 'theme': post.theme, 'text': post.text, 'files': files}
            new_list.append(p)

        thread['posts'] = new_list

    return render_template(
        "board.html", nav=FOOTER, thread_count=board.thread_count,
        short_name=board.short, long_name=board.name,
        description=board.description, base_url=base_url,
        threads=threads_with_posts, pages=pages_total
    ), 200


if __name__ == '__main__':
    app.run()
