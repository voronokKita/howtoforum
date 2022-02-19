from flask_sqlalchemy import SQLAlchemy

from flask_config import app
from constants import *


app.config.update(
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_DATABASE_URI="sqlite:///forum.db"
)
db = SQLAlchemy(app)
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
class Statuses(db.Model):
    __tablename__ = 'statuses'

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(DEFAULT_LENGTH), unique=True, nullable=False)

    users = db.relationship('Users', backref='get_status')

    def __repr__(self):
        return f"<status: {self.status}>"


class Resource_types(db.Model):
    __tablename__ = 'resource_types'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(DEFAULT_LENGTH), unique=True, nullable=False) # TODO index, constants

    resources = db.relationship('Resources', backref='get_type')

    def __repr__(self):
        return f"<resource type: {self.type}>"


class Boards(db.Model):
    __tablename__ = 'boards'

    id = db.Column(db.Integer, primary_key=True)
    short = db.Column(db.String(DEFAULT_LENGTH), unique=True, index=True, nullable=False)
    name = db.Column(db.String(DEFAULT_LENGTH), unique=True, nullable=False)
    description = db.Column(db.String(100), nullable=False)
    thread_count = db.Column(db.Integer, default=0, nullable=False)

    threads = db.relationship('Threads', backref='get_board')

    def __repr__(self):
        return f"<board: {self.short}>"


class Threads(db.Model):
    __tablename__ = 'threads'

    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, \
        db.ForeignKey(Boards.id, onupdate='CASCADE', ondelete='RESTRICT'), index=True, nullable=False)
    date = db.Column(db.DateTime, default=datetime.datetime.now, nullable=False)
    updated = db.Column(db.DateTime, default=datetime.datetime.now, nullable=False)
    post_count = db.Column(db.Integer, default=0, nullable=False)
    archivated = db.Column(db.Boolean, default=False, nullable=False)

    posts = db.relationship('Posts', backref='get_thread')

    def __repr__(self):
        return f"<thread: {self.id} (board {self.board_id})>"


class Users(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, index=True)
    login = db.Column(db.String(USERNAME_LENGTH), unique=True, nullable=False)
    password = db.Column(db.String(USER_PASSWORD_LENGTH), nullable=False)
    status = db.Column(db.Integer, \
        db.ForeignKey(Statuses.id, onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    registered = db.Column(db.DateTime, default=datetime.datetime.now)

    resources = db.relationship('Resources', backref='get_user')
    posts = db.relationship('Posts', backref='get_user')

    def __repr__(self):
        return f"<user: {self.login}>"


attachments = db.Table(
    'attachments',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), index=True, nullable=False),
    db.Column('resource_id', db.Integer, db.ForeignKey('resources.id'), nullable=False)
)

class Posts(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, \
        db.ForeignKey(Threads.id, onupdate='CASCADE', ondelete='RESTRICT'), index=True, nullable=False)
    user_id = db.Column(db.Integer, \
        db.ForeignKey(Users.id, onupdate='CASCADE', ondelete='SET NULL'), default=None)
    password = db.Column(db.String(ANON_PASSWORD_LENGTH), default=None)
    date = db.Column(db.DateTime, default=datetime.datetime.now, nullable=False)
    theme = db.Column(db.String(DEFAULT_LENGTH), default=None)
    text = db.Column(db.Text, default="&nbsp;")
    has_files = db.Column(db.Boolean, default=False, nullable=False)

    files = db.relationship('Resources', secondary=attachments, backref='get_posts')

    def __repr__(self):
        return f"<post: {self.id}>"


class Resources(db.Model):
    __tablename__ = 'resources'

    id = db.Column(db.Integer, primary_key=True, index=True)
    resource = db.Column(db.String(RESOURCE_LENGTH), nullable=False)
    type = db.Column(db.Integer, \
        db.ForeignKey(Resource_types.id, onupdate='CASCADE', ondelete='RESTRICT'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(Users.id, onupdate='CASCADE', ondelete='SET NULL'))
    uploaded = db.Column(db.DateTime, default=datetime.datetime.now)

    def __repr__(self):
        return f"<resource: {self.resource}>"
