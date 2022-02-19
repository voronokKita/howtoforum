import re
import datetime
import secrets
import hashlib
import pathlib
from tempfile import mkdtemp
from pprint import pprint
from time import sleep


CWD = pathlib.Path.cwd()
FILE_STORAGE = CWD / "static" / "data"

USERNAME_MIN = 2
USERNAME_LENGTH = 20
DEFAULT_LENGTH = 30
USER_PASSWORD_MIN = 6
USER_PASSWORD_LENGTH = 200
ANON_PASSWORD_LENGTH = 100
RESOURCE_LENGTH = 200
MAX_FILE_SIZE = 30

USERNAME_PATTERN = '[A-Za-z0-9_-]+'
PASSWORD_PATTERN = '[^ ]+'
TIME_FORMAT = '%A, %-d day of %B %Y | %-H:%M:%S'
ANOTHER_TEXT_TYPES = ["json", "javascript", "pdf", "xml", "msword"]
FOOTER = []
THREADS_ON_PAGE = 10
POSTS_PER_THREAD = 5

GLOBAL_SALT = """So, with sadness in my heart
Feel the best thing I could do
Is end it all and leave forever
What's done is done, it feels so bad
What once was happy now is sad
I'll never love again
My world is ending..."""
