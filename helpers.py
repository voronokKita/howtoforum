from markupsafe import escape
from werkzeug.utils import secure_filename

from database import db, Statuses, Resource_types, Boards, Threads, Users, Posts, Resources

from constants import *


def check_form(name, password, confirmation=None):
    """ WTForms Regexp didn't work properly """
    messages = []
    if not re.fullmatch(USERNAME_PATTERN, name):
        messages.append("The username format doesn't match.")
    if not re.fullmatch(PASSWORD_PATTERN, password):
        messages.append("The password format doesn't match.")
    if confirmation and not re.fullmatch(PASSWORD_PATTERN, confirmation):
        messages.append("The password confirmation format doesn't match.")
    return messages


def hash_password(password, salt=""):
    if salt:
        password = hashlib.sha3_512(password.encode()).hexdigest()
        s = password + salt + GLOBAL_SALT
        return hashlib.sha3_512(s.encode()).hexdigest()
    else:
        password = hashlib.sha3_224(password.encode()).hexdigest()
        s = password + GLOBAL_SALT
        return hashlib.sha3_224(s.encode()).hexdigest()


def make_a_post(form, board, user):
    """ makes a new thread or a new post, saves files """
    date = datetime.datetime.now()

    thread = Threads(get_board=board, date=date, updated=date)
    db.session.add(thread)
    db.session.commit()
    thread = Threads.query.filter(Threads.board_id == board.id, \
                Threads.post_count == 0, Threads.date == date).first()

    password = None
    if not user and form.password.data:
        password = hash_password(form.password.data)

    theme = None
    if form.theme.data and len(form.theme.data) <= DEFAULT_LENGTH:
        theme = form.theme.data

    post = Posts(get_thread=thread, password=password, date=date, theme=theme, \
            text=form.text.data, has_files=True)
    db.session.add(post)

    if user:
        user = Users.query.filter_by(login=user['name']).first()
        user.posts.append(post)
    db.session.commit()

    files = [form.file1.data, form.file2.data, form.file3.data]
    if not files[0] and not files[1] and not files[2]:
        file = Resources.query.filter_by(resource="054634534.jpg").first()
        post.files.append(file)
    else:
        files = [f for f in files if f is not None]
        for file in files:  # TODO file size
            filename = secure_filename(file.filename)
            tmp_file_location = FILE_STORAGE / "tmp" / filename
            file.save(tmp_file_location)

            mime = file.mimetype.split("/")
            if mime[0] == "image":
                resource_type = "image"
            elif mime[0] == "text" or mime[1] in ANOTHER_TEXT_TYPES or "vnd" in mime[1]:
                resource_type = "text"
            else:
                resource_type = "other"
            resource_type = Resource_types.query.filter_by(type=resource_type).first()

            file = Resources(get_type=resource_type, resource=filename)
            if user:
                user.resources.append(file)
            post.files.append(file)
            db.session.commit()
            tmp_file_location.rename(FILE_STORAGE / resource_type.type / file.resource)

    thread.post_count += 1
    board.thread_count += 1
    db.session.commit()
    return board


def fill_board(threads_on_page):
    """ fill threads with data and posts """
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

    return threads_with_posts


def fill_the_database():
    if not Statuses.query.first():
        one = Statuses(status="user")
        two = Statuses(status="moderator")
        three = Statuses(status="administrator")
        db.session.add_all([one, two, three])
        db.session.commit()
        print("db: filled statuses table")

        one = Resource_types(type="image")
        two = Resource_types(type="text")
        three = Resource_types(type="other")
        db.session.add_all([one, two, three])
        db.session.commit()
        print("db: filled resource types")

        one = Boards(short="b", name="brotherhood", description="polite communication")
        two = Boards(short="a", name="animation", description="Japanese and other kinds of anime")
        three = Boards(short="u", name="university", description="knowledge exchange")
        db.session.add_all([one, two, three])
        db.session.commit()
        print("db: filled boards list")

        s = Statuses.query.all()
        one = Users(login="senpai", password=hash_password("qwerty", "senpai"), get_status=s[2])
        two = Users(login="maika", password=hash_password("qwerty", "maika"), get_status=s[1])
        three = Users(login="megumin", password=hash_password("qwerty", "megumin"), get_status=s[1])
        four = Users(login="aoba", password=hash_password("qwerty", "aoba"), get_status=s[0])
        five = Users(login="nene", password=hash_password("qwerty", "nene"), get_status=s[0])
        db.session.add_all([one, two, three, four, five])
        db.session.commit()
        print("db: filled users list")

        t = Resource_types.query.filter(Resource_types.type == "image").first()
        u = Users.query.all()
        one = Resources(resource="436456345.png", get_type=t, get_user=u[0])
        two = Resources(resource="126693345.png", get_type=t, get_user=u[1])
        three = Resources(resource="164376090060.png", get_type=t, get_user=u[4])
        four = Resources(resource="546567543546.png", get_type=t, get_user=u[2])
        five = Resources(resource="4365466546.png", get_type=t, get_user=u[3])
        six = Resources(resource="96574552.jpg", get_type=t, get_user=u[3])
        seven = Resources(resource="0192018.png", get_type=t, get_user=u[3])
        eight = Resources(resource="054634534.jpg", get_type=t)
        db.session.add_all([one, two, three, four, five, six, seven, eight])
        db.session.commit()
        print("db: filled resources list")

        boards = Boards.query.all()
        thread_id = 1
        for board in boards:
            i = 1
            while i <= 142:
                print(f"db: makes thread {thread_id} on board {board.short}")
                t = Threads(id=thread_id, post_count=2, get_board=board)
                db.session.add(t)
                p1 = Posts(get_thread=t, theme="test", text=f"thread №{thread_id}", has_files=True)
                db.session.add(p1)
                file = Resources.query.filter(Resources.resource == "054634534.jpg").first()
                p1.files.append(file)
                board.thread_count += 1
                db.session.commit()
                p2 = Posts(get_thread=t, text=f"reply to {thread_id}")
                db.session.add(p2)
                db.session.commit()
                thread_id += 1
                i += 1

        print(f"db: makes hello thread")
        b = boards[0]
        t = Threads(get_board=b)
        db.session.add(t)
        b.thread_count += 1
        db.session.commit()
        t = Threads.query.order_by(Threads.id.desc()).first()
        users = Users.query.all()

        p1 = Posts(get_thread=t, get_user=users[0], theme="Hello!", text="Kon'nichiwa!", has_files=True)
        db.session.add(p1)
        file = Resources.query.filter(Resources.resource == "436456345.png").first()
        p1.files.append(file)
        t.post_count += 1
        db.session.commit()

        p2 = Posts(get_thread=t, text="First one!")
        db.session.add(p2)
        t.post_count += 1
        db.session.commit()

        p3 = Posts(get_thread=t, text="I'm the strongest!")
        db.session.add(p3)
        t.post_count += 1
        db.session.commit()

        p4 = Posts(get_thread=t, get_user=users[1], text="I hope you all will behave like a good boys and girls.", has_files=True)
        db.session.add(p4)
        file = Resources.query.filter(Resources.resource == "126693345.png").first()
        p4.files.append(file)
        t.post_count += 1
        db.session.commit()

        p5 = Posts(get_thread=t, get_user=users[4], text="I wish I could become a programmer and create my own forum too.", has_files=True)
        db.session.add(p5)
        file = Resources.query.filter(Resources.resource == "164376090060.png").first()
        p5.files.append(file)
        t.post_count += 1
        db.session.commit()

        p6 = Posts(get_thread=t, get_user=users[2], text="You just have to learn something new and practice regularly, and one day you'll definitely become one. Programming is fun!", has_files=True)
        db.session.add(p6)
        file = Resources.query.filter(Resources.resource == "546567543546.png").first()
        p6.files.append(file)
        t.post_count += 1
        db.session.commit()

        p7 = Posts(get_thread=t, get_user=users[3], text="I love you all so much!", has_files=True)
        db.session.add(p7)
        file1 = Resources.query.filter(Resources.resource == "4365466546.png").first()
        file2 = Resources.query.filter(Resources.resource == "96574552.jpg").first()
        file3 = Resources.query.filter(Resources.resource == "0192018.png").first()
        p7.files.append(file1)
        p7.files.append(file2)
        p7.files.append(file3)
        t.post_count += 1
        t.updated = datetime.datetime.now()
        db.session.commit()
        print("db: filled threads and posts lists")
