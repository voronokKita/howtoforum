import re
import datetime
import secrets
import hashlib
import pathlib
import string
import random
from tempfile import mkdtemp
from pprint import pprint
from time import sleep

from markupsafe import Markup, escape
from werkzeug.utils import secure_filename


class PageOutOfRangeError(Exception): pass
class BoardIsEmptyError(Exception): pass
class EmptyPostError(Exception): pass

CWD = pathlib.Path.cwd()
FILE_STORAGE = CWD / "static" / "data"

USER_STATUSES = ["user", "moderator", "administrator"]

FILE_TYPE_IMAGE = 'image'
FILE_TYPE_TEXT = 'text'
FILE_TYPE_AUDIO = 'music'
FILE_TYPE_VIDEO = 'video'
FILE_TYPE_OTHER = 'other'
RESOURCE_TYPES = [FILE_TYPE_IMAGE, FILE_TYPE_TEXT, FILE_TYPE_AUDIO, FILE_TYPE_OTHER]

BOARDS = [
    {'short': "b", 'name': "brotherhood", 'desc': "polite communication"},
    {'short': "a", 'name': "animation", 'desc': "Japanese and other kinds of anime"},
    {'short': "u", 'name': "university", 'desc': "knowledge exchange"}
]

THREADS_ON_PAGE = 10
POSTS_PER_THREAD = 5

USERNAME_MIN = 2
USERNAME_LENGTH = 20
DEFAULT_LENGTH = 30
DB_POST_THEME_EXTENDED = 100
USER_PASSWORD_MIN = 6
USER_PASSWORD_LENGTH = 200
ANON_PASSWORD_LENGTH = 100
RESOURCE_LENGTH = 100
MAX_FILE_SIZE = 30

USERNAME_PATTERN = '[A-Za-z0-9_-]+'
TIME_FORMAT = '%A, %-d day of %B %Y | %-H:%M:%S'
ANOTHER_TEXT_TYPES = ["json", "javascript", "pdf", "xml", "msword"]
FOOTER = []

M_WRONG = "Wrong input."
M_EMPTY = "Empty input."
M_USERNAME_LEN = "The username length doesn't match."
M_PASSWORD_LEN = "The password length doesn't match."
M_PASSWORD_CONFIRM = "The password confirmation doesn't match."
M_POST_THEME_LEN = f"Theme is {DEFAULT_LENGTH} symbols max."
M_POST_PASSWORD_LEN = f"Password is {ANON_PASSWORD_LENGTH} symbols max."
M_INTEGRITY_ERROR = "DB ERROR: data already exists."
M_SQL_ALCHEMY_ERROR = "DB ERROR: something went terrible wrong..."

GLOBAL_SALT = """So, with sadness in my heart
Feel the best thing I could do
Is end it all and leave forever
What's done is done, it feels so bad
What once was happy now is sad
I'll never love again
My world is ending..."""

BASE_USERS = [{'name': "senpai", 'status': 2}, {'name': "maika", 'status': 1}, {'name': "megumin", 'status': 1},
              {'name': "aoba", 'status': 0}, {'name': "nene", 'status': 0}]
BASE_RESOURCES = [
    {'file': "0000000000.jpg", 'user': None},
    {'file': "0000000001.png", 'user': 0},
    {'file': "0000000002.png", 'user': 1},
    {'file': "0000000003.png", 'user': 4},
    {'file': "0000000004.png", 'user': 2},
    {'file': "0000000005.png", 'user': 3},
    {'file': "0000000006.jpg", 'user': 3},
    {'file': "0000000007.png", 'user': 3},
]
HELLO_THREAD = [
    {'user': BASE_RESOURCES[1]['user'], 'theme': "Hello!",
     'text': "Kon'nichiwa!", 'files': [ BASE_RESOURCES[1]['file'] ]},
    {'user': None, 'theme': None, 'text': "First one!", 'files': False},
    {'user': None, 'theme': None, 'text': "I'm the strongest!", 'files': False},
    {'user': BASE_RESOURCES[2]['user'], 'theme': None,
     'text': "I hope you all will behave like a good boys and girls.",
     'files': [ BASE_RESOURCES[2]['file'] ]},
    {'user': BASE_RESOURCES[3]['user'], 'theme': None,
     'text': "I wish I could become a programmer and create my own forum too.",
     'files': [ BASE_RESOURCES[3]['file'] ]},
    {'user': BASE_RESOURCES[4]['user'], 'theme': None,
     'text': "You just have to learn something new and practice regularly, and one day you'll definitely become one. Programming is fun!",
     'files': [ BASE_RESOURCES[4]['file'] ]},
    {'user': BASE_RESOURCES[5]['user'], 'theme': None, 'text': "I love you all so much!",
     'files': [ BASE_RESOURCES[5]['file'], BASE_RESOURCES[6]['file'], BASE_RESOURCES[7]['file'] ]},
]
