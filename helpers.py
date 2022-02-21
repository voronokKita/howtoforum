from database import db, Statuses, Resource_types, Boards, Threads, Users, Posts, Resources

from sqlalchemy.exc import IntegrityError

from constants import *


def hash_password(password, salt=""):
    if salt:
        password = hashlib.sha3_512(password.encode()).hexdigest()
        s = password + salt + GLOBAL_SALT
        return hashlib.sha3_512(s.encode()).hexdigest()
    else:
        password = hashlib.sha3_224(password.encode()).hexdigest()
        s = password + GLOBAL_SALT
        return hashlib.sha3_224(s.encode()).hexdigest()


def make_a_post(form, board, user, thread=None):  # TODO empty post error
    """ makes a new thread or a new post, saves files """
    date = datetime.datetime.now()

    if not thread:
        thread = Threads(get_board=board, date=date, updated=date)
        db.session.add(thread)
        db.session.commit()
        thread = Threads.query.filter(Threads.board_id == board.id, \
                    Threads.post_count == 0, Threads.date == date).first()

    password = None
    theme = None
    if not user and form.password.data:
        password = hash_password(form.password.data)
    if form.theme.data and len(form.theme.data) <= DEFAULT_LENGTH:
        theme = escape(form.theme.data)

    post = Posts(get_thread=thread, password=password, date=date, \
            theme=theme, text=escape(form.text.data), has_files=True)
    db.session.add(post)

    if user:
        user = Users.query.filter_by(login=user['name']).first()
        user.posts.append(post)

    db.session.commit()

    files = [form.file1.data, form.file2.data, form.file3.data]
    if not files[0] and not files[1] and not files[2]:
        # the file by default for empty posts
        file = Resources.query.filter_by(id=1).first()
        post.files.append(file)

    else:
        files = [f for f in files if f is not None]
        load_files(files, post, user)

    thread.updated = date
    thread.post_count += 1
    board.thread_count += 1
    db.session.commit()
    return board


def load_files(files, post, user=None):
    for file in files:
        filename = secure_filename(file.filename)
        tmp_file_location = FILE_STORAGE / "tmp" / filename
        file.save(tmp_file_location)

        mime = file.mimetype.split("/")
        if mime[0] == "image":
            resource_type = FILE_TYPE_IMAGE
        elif mime[0] == "text" or mime[1] in ANOTHER_TEXT_TYPES or "vnd" in mime[1]:
            resource_type = FILE_TYPE_TEXT
        elif mime[0] == "audio":
            resource_type = FILE_TYPE_AUDIO
        elif mime[0] == "video":
            resource_type = FILE_TYPE_VIDEO
        else:
            resource_type = FILE_TYPE_OTHER
        resource_type = Resource_types.query.filter_by(type=resource_type).first()

        while True:
            duplicate = Resources.query.filter_by(resource=filename).first()
            if duplicate:
                extension = pathlib.Path(filename).suffix
                filename = ''.join(random.choices(string.ascii_letters + string.digits, k=15))
                filename += extension
            else:
                break
        file = Resources(get_type=resource_type, resource=filename)

        if user:
            user.resources.append(file)
        post.files.append(file)
        db.session.commit()
        tmp_file_location.rename(FILE_STORAGE / resource_type.type / file.resource)


def generete_board_page(page, board):
    start = page * 10 - 10
    stop = page * 10
    threads_on_page = Threads.query.filter(Threads.board_id == board.id, Threads.post_count > 0) \
                        .order_by(Threads.updated.desc()).slice(start, stop).all()

    if not threads_on_page:
        if page != 1:
            raise PageOutOfRangeError("error")
        else:
            raise BoardIsEmptyError("error")
    else:
        pages_total = int(board.thread_count / 10) + (board.thread_count % 10 > 0)
        pages_total = [i for i in range(1, pages_total + 1)]

        threads_with_posts = fill_board(threads_on_page)

    return pages_total, threads_with_posts


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
             'archivated': thread.archivated, 'posts': [op] + last_posts, 'id': thread.id}
        threads_with_posts.append(t)

    # fill posts with data
    for thread in threads_with_posts:
        old_list = thread['posts']
        new_list = []

        for post in old_list:
            username = post.get_user.login if post.user_id else None
            theme = Markup(post.theme) if post.theme else None

            files = []
            if post.has_files:
                for f in post.files:
                    p = f"/static/data/{f.get_type.type}/"
                    files.append({'name': f.resource, 'path': p})

            p = {'id': post.id, 'date': post.date.strftime(TIME_FORMAT),
                 'author': username, 'theme': theme, 'text': Markup(post.text), 'files': files}
            new_list.append(p)

        thread['posts'] = new_list

    return threads_with_posts


def generete_thread_page(thread):
    thread = {'post_count': thread.post_count, 'archivated': thread.archivated,
              'posts': thread.posts, 'id': thread.id}
    new_list = []
    for post in thread['posts']:
        username = post.get_user.login if post.user_id else None
        theme = Markup(post.theme) if post.theme else None

        files = []
        if post.has_files:
            for file in post.files:
                path = f"/static/data/{file.get_type.type}/"
                files.append({'name': file.resource, 'path': path})

        p = {'id': post.id, 'date': post.date.strftime(TIME_FORMAT),
             'author': username, 'theme': theme, 'text': Markup(post.text), 'files': files}
        new_list.append(p)

    thread['posts'] = new_list
    return thread


def fill_the_database():
    db.create_all()
    if not Statuses.query.first():
        l = []
        for status in USER_STATUSES:
            s = Statuses(status=status)
            l.append(s)
        db.session.add_all(l)
        db.session.commit()
        print("db: filled statuses table")

        l = []
        for ftype in RESOURCE_TYPES:
            t = Resource_types(type=ftype)
            l.append(t)
        db.session.add_all(l)
        db.session.commit()
        print("db: filled resource types")

        l = []
        for board in BOARDS:
            b = Boards(short=board['short'], name=board['name'], description=board['desc'])
            l.append(b)
        db.session.add_all(l)
        db.session.commit()
        print("db: filled boards list")

        l = []
        statuses = Statuses.query.all()
        for user in BASE_USERS:
            u = Users(login=user['name'], password=hash_password("qwerty", user['name']), \
                    get_status=statuses[ user['status'] ])
            l.append(u)
        db.session.add_all(l)
        db.session.commit()
        print("db: filled users list")

        l = []
        img = Resource_types.query.filter_by(type=FILE_TYPE_IMAGE).first()
        users = Users.query.all()
        for file in BASE_RESOURCES:
            if file['user']:
                r = Resources(resource=file['file'], get_type=img, get_user=users[ file['user'] ])
            else:
                r = Resources(resource=file['file'], get_type=img)
            l.append(r)
        db.session.add_all(l)
        db.session.commit()
        print("db: filled resources list")

        boards = Boards.query.all()
        thread_id = 1
        for board in boards:
            i = 1
            while i <= 142:
                print(f"db: makes thread {thread_id} on board {board.short}")
                new_thread = Threads(id=thread_id, post_count=2, get_board=board)
                db.session.add(new_thread)
                op = Posts(get_thread=new_thread, theme="test", text=f"thread №{thread_id}", has_files=True)
                db.session.add(op)
                file = Resources.query.filter_by(id=1).first()
                op.files.append(file)
                board.thread_count += 1
                db.session.commit()
                post = Posts(get_thread=new_thread, text=f"reply to {thread_id}")
                db.session.add(post)
                db.session.commit()
                thread_id += 1
                i += 1

        print(f"db: makes hello thread")
        thread = Threads(get_board=boards[0])
        db.session.add(thread)
        boards[0].thread_count += 1
        db.session.commit()
        thread = Threads.query.order_by(Threads.id.desc()).first()
        users = Users.query.all()
        for post in HELLO_THREAD:
            has_files = True if post['files'] else False
            user = users[ post['user'] ] if post['user'] else None
            new_post = Posts(get_thread=thread, get_user=user, \
                        theme=post['theme'], text=post['text'], has_files=has_files)
            db.session.add(new_post)
            if has_files:
                for file in post['files']:
                    file = Resources.query.filter_by(resource=file).first()
                    new_post.files.append(file)
            thread.post_count += 1
        thread.updated = datetime.datetime.now()
        db.session.commit()
        print("db: filled threads and posts lists")
