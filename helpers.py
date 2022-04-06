from database import db, Statuses, Resource_types, Boards, Threads, Users, Posts, Resources

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


def make_a_post(form, board, user, thread=None):
    """ makes a new thread or a new post, saves files """
    op = True if not thread else False
    date = datetime.datetime.now()

    # 0 understand post content
    tmp_files = [form.file1.data, form.file2.data, form.file3.data]
    tmp_files = [f for f in tmp_files if f is not None]
    text = form.text.data
    if not text and not tmp_files:
        raise EmptyPostError(M_EMPTY)

    # 1 load files
    elif tmp_files:
        tmp_files = load_files(tmp_files)

    # 2 db operation:
    if op:
        thread = Threads(get_board=board, date=date)
        db.session.add(thread)
        thread = Threads.query.filter(Threads.board_id == board.id, \
                    Threads.post_count == 0, Threads.date == date).first()

    password = hash_password(form.password.data) if not user and form.password.data else None
    theme = escape(form.theme.data) if form.theme.data and len(form.theme.data) <= DEFAULT_LENGTH else None

    post = Posts(get_thread=thread, op=op, password=password, date=date, \
            theme=theme, text=escape(form.text.data), has_files=True)
    db.session.add(post)

    if user:
        user = Users.query.filter_by(login=user['name']).first()
        user.posts.append(post)

    if op and not tmp_files:
        # the file by default for empty op
        file = Resources.query.filter_by(id=1).first()
        post.files.append(file)

    elif tmp_files:
        post, user = save_files(tmp_files, post, user)

    if op:
        board.thread_count += 1
    thread.post_count += 1
    if not thread.archivated and thread.post_count < BUMP_LIMIT:
        thread.updated = date
    elif not thread.archivated and thread.post_count >= BUMP_LIMIT:
        thread.archivated = True

    try:
        db.session.commit()
    except IntegrityError:
        raise DataAlreadyExistsError(M_INTEGRITY_ERROR)
    except SQLAlchemyError or Exception:  #TODO
        raise BaseCriticalError(M_SQL_ALCHEMY_ERROR)

    return board


def load_files(files):
    new_file_names = []
    tmp_files = []
    for file in files:
        filename = secure_filename(file.filename)

        # check for file doubles
        if filename not in new_file_names:
            new_file_names.append(filename)
        else:
            continue

        tmp_file_location = FILE_STORAGE / "tmp" / filename
        file.save(tmp_file_location)

        tmp_files.append( {'file': file, 'tmp': tmp_file_location} )

    return tmp_files


def save_files(tmp_files, post, user):
    for file in tmp_files:
        tmp_file_location = file['tmp']
        file = file['file']

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

        filename = secure_filename(file.filename)
        while True:
            duplicate = Resources.query.filter_by(resource=filename).first()
            if duplicate:
                extension = pathlib.Path(filename).suffix
                filename = ''.join( random.choices( string.ascii_letters + string.digits, k=random.randint(6, 20) ) )
                filename += extension
            else:
                break

        file = Resources(get_type=resource_type, resource=filename)

        if user:
            user.resources.append(file)
        post.files.append(file)
        tmp_file_location.rename(FILE_STORAGE / resource_type.type / file.resource)

    return post, user


def delete_a_post(post, user, password):
    will_be_deleted = False
    if password:
        if post.password == password:
            will_be_deleted = True
            print("OKOK")
        else:
            print("wrong password error")

    elif user:
        if post.user_id and post.get_user.login == user.login:
            will_be_deleted = True
            print("OKOK")
        else:
            # check hierarchy
            poster_status = post.get_user.status if post.user_id else USER_STATUSES[STATUS_ANON]
            if user.status > USER_STATUSES[STATUS_USER] and poster_status < user.status:
                will_be_deleted = True
                print("OKOK")
            else:
                print("don't have permissions")

    if will_be_deleted:
        pass


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
    posts = [fill_post(post) for post in thread.posts]

    thread = {'post_count': thread.post_count, 'archivated': thread.archivated,
              'posts': posts, 'id': thread.id}
    return thread


def fill_post(post):
    username = post.get_user.login if post.user_id else None
    theme = Markup(post.theme) if post.theme else None

    files = []
    if post.has_files:
        for file in post.files:
            path = f"/static/data/{file.get_type.type}/"
            files.append({'name': file.resource, 'path': path})

    return {'id': post.id, 'date': post.date.strftime(TIME_FORMAT),
            'author': username, 'theme': theme, 'text': Markup(post.text), 'files': files}


def fill_the_database():
    db.create_all()
    if not Statuses.query.first():
        l = []
        for status in USER_STATUSES[1:]:
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

        print("db: makes some test threads")
        boards = Boards.query.all()
        for board in boards:
            t = 1
            while t <= 142:
                print(f"db: /{board.short}/{t}")
                new_thread = Threads(get_board=board)
                db.session.add(new_thread)
                op = Posts(get_thread=new_thread, op=True, theme="test", text="Just a test thread.", has_files=True)
                db.session.add(op)
                file = Resources.query.filter_by(id=1).first()
                op.files.append(file)
                board.thread_count += 1
                new_thread.post_count += 1
                post = Posts(get_thread=new_thread, text=f"reply to {new_thread.id}")
                db.session.add(post)
                new_thread.post_count += 1
                db.session.commit()
                t += 1

        print(f"db: makes the archivated thread")
        thread = Threads(get_board=boards[0])
        db.session.add(thread)
        boards[0].thread_count += 1
        db.session.commit()
        thread = Threads.query.order_by(Threads.id.desc()).first()
        op = Posts(get_thread=thread, op=True, theme="To The Bump Limit!", \
                text="This thread is going to reach the bump limit!", has_files=True)
        file = Resources.query.filter_by(id=9).first()
        op.files.append(file)
        thread.post_count += 1
        db.session.commit()
        p = 2
        while p <= 510:
            post = Posts(get_thread=thread, text="Bump!")
            thread.post_count += 1
            p += 1
            if p >= BUMP_LIMIT and not thread.archivated:
                thread.updated = datetime.datetime.now()
                thread.archivated = True


        print(f"db: makes the hello thread")
        thread = Threads(get_board=boards[0])
        db.session.add(thread)
        boards[0].thread_count += 1
        db.session.commit()
        thread = Threads.query.order_by(Threads.id.desc()).first()
        users = Users.query.all()
        for i, post in enumerate(HELLO_THREAD):
            has_files = True if post['files'] else False
            user = None if post['user'] is None else users[ post['user'] ]
            op = True if i == 0 else False
            new_post = Posts(get_thread=thread, op=op, get_user=user, \
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
