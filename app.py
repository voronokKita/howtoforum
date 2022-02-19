from flask import url_for, request, session, redirect, render_template, flash

from sqlalchemy import exc

from markupsafe import escape
from werkzeug.utils import secure_filename

from flask_config import app
from database import db, Statuses, Resource_types, Boards, Threads, Users, Posts, Resources
from flask_forms import LoginForm, AnonymizeForm, ChangePassword, RegisterForm, MakePost, MakeThread
from helpers import check_form, hash_password, fill_the_database, fill_board  # ? fix
from constants import *

# TODO: file handling
# TODO: transactions and ACID
# TODO: pep8
# TODO: color theme
# TODO: clear and simplify input
# TODO: style posts width


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


@app.route("/board/<board>/", methods=['GET', 'POST'])
@app.route("/board/<board>/<int:page>/")
def board(board, page=1):
    board = Boards.query.filter(Boards.short == escape(board)).first()
    if not board:
        return redirect(url_for('index')), 303
    elif page <= 0:
        return redirect(url_for('board', board=board.short, page=1)), 303
    else:
        form_thread = MakeThread()
        base_url = f"/board/{board.short}/"

    # <WIP>
    if form_thread.validate_on_submit():  # TODO: abstract in another place
        date = datetime.datetime.now()

        t = Threads(get_board=board, date=date, updated=date)
        db.session.add(t)
        db.session.commit()

        t = Threads.query.filter(Threads.board_id == board.id, \
                Threads.post_count == 0, Threads.date == date).first()

        user = session.get('user')
        password = None
        if not user and form_thread.password.data:
            password = hash_password(form_thread.password.data)

        theme = None
        if form_thread.theme.data and len(form_thread.theme.data) <= DEFAULT_LENGTH:
            theme = form_thread.theme.data

        p = Posts(get_thread=t, password=password, date=date, theme=theme, \
                text=form_thread.text.data, has_files=True)
        db.session.add(p)

        if user:
            user = Users.query.filter(Users.login == user['name']).first()
            user.posts.append(p)

        files = [form_thread.file1.data, form_thread.file2.data, form_thread.file3.data]
        if not files[0] and not files[1] and not files[2]:
            file = Resources.query.filter(Resources.resource == "054634534.jpg").first()
            p.files.append(file)
        else:
            files = [f for f in files if f is not None]
            for file in files:  # TODO file size
                mime = file.mimetype.split("/")
                if mime[0] == "image":
                    file_type = "image"
                elif mime[0] == "text" or mime[1] in ANOTHER_TEXT_TYPES or "vnd" in mime[1]:
                    file_type = "text"
                else:
                    file_type = "other"

                filename = secure_filename(file.filename)
                tmp_file_location = FILE_STORAGE / "tmp" / filename
                file.save(tmp_file_location)

                f_type = Resource_types.query.filter_by(type=file_type).first()
                f = Resources(get_type=f_type, resource=filename)
                if user:
                    user.resources.append(f)
                p.files.append(f)
                tmp_file_location.rename(FILE_STORAGE / file_type / filename)

        t.post_count += 1
        board.thread_count += 1
        db.session.commit()

        #</WIP>

    # generete a page content
    start = page * 10 - 10
    stop = page * 10
    threads_on_page = Threads.query.filter(Threads.board_id == board.id, Threads.post_count > 0). \
                        order_by(Threads.updated.desc()).slice(start, stop).all()
    if not threads_on_page:
        if page != 1:
            return redirect(url_for('board', board=board.short, page=1)), 303
        else:
            return redirect(url_for('index')), 303
    else:
        pages_total = int(board.thread_count / 10) + (board.thread_count % 10 > 0)
        pages_total = [i for i in range(1, pages_total + 1)]

        threads_with_posts = fill_board(threads_on_page)

    return render_template(
        "board.html", nav=FOOTER, thread_count=board.thread_count,
        short_name=board.short, long_name=board.name,
        description=board.description, base_url=base_url,
        threads=threads_with_posts, pages=pages_total,
        pass_max=ANON_PASSWORD_LENGTH, theme_max=DEFAULT_LENGTH,
        filesize=MAX_FILE_SIZE, form_thread=form_thread
    ), 200


if __name__ == '__main__':
    app.run()
