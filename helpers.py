import re
import datetime
import secrets
import hashlib
import pathlib
from tempfile import mkdtemp
from pprint import pprint
from time import sleep

GLOBAL_SALT = """So, with sadness in my heart
Feel the best thing I could do
Is end it all and leave forever
What's done is done, it feels so bad
What once was happy now is sad
I'll never love again
My world is ending..."""

STATUS_USER = 1
STATUS_MOD = 2
STATUS_ADMIN = 3

USERNAME_MIN = 2
USERNAME_LENGTH = 20
DEFAULT_LENGTH = 30
USER_PASSWORD_MIN = 6
USER_PASSWORD_LENGTH = 200
ANON_PASSWORD_LENGTH = 100
RESOURCE_LENGTH = 200

USERNAME_PATTERN = '[A-Za-z0-9_-]+'
TIME_FORMAT = '%A, %-d day of %B %Y'
FOOTER = []
THREADS_ON_PAGE = 10

FORM_LOGIN = ['Name', 'Password']
FORM_REGISTER = ['Name', 'Password', 'Repeat password']
FORM_PASSWORD = ['Old password', 'New password', 'Repeat new password']
FORM_THREAD = ['Theme', 'Text', 'File', 'File', 'File', 'Password']


def check_login_form(input_name, input_password, input_confirmation=None):
    messages = []
    if not input_name or not input_password:
        messages.append("Wrong input.")
    else:
        if not USERNAME_MIN <= len(input_name) <= USERNAME_LENGTH:
            messages.append("The username length doesn't match.")
        if not re.search(USERNAME_PATTERN, input_name):
            messages.append("The username format doesn't match.")
        if not USER_PASSWORD_MIN <= len(input_password) <= USER_PASSWORD_LENGTH:
            messages.append("The password length doesn't match.")
        if input_confirmation and not input_password == input_confirmation:
            messages.append("The password fields doesn't match.")
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


if __name__ == '__main__':
    pass
