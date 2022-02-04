import re
import datetime
import secrets
import hashlib
import pathlib
from pprint import pprint

STATUS_USER = 1
STATUS_MOD = 2
STATUS_ADMIN = 3

USERNAME_MIN = 2
USERNAME_LENGTH = 20
DEFAULT_LENGTH = 30
USER_PASSWORD_MIN = 2
USER_PASSWORD_LENGTH = 200
ANON_PASSWORD_LENGTH = 100
RESOURCE_LENGTH = 200
USERNAME_PATTERN = '[A-Za-z0-9_-]+'
FORM_LOGIN = ['Name', 'Password']
FORM_REGISTER = ['Name', 'Password', 'Repeat password']


def time_now():
    return datetime.now().replace(microsecond=0)


def check_login_form(input_name, input_password, input_confirmation=None):
    messages = []
    if not USERNAME_MIN <= len(input_name) <= USERNAME_LENGTH:
        messages.append("The username length doesn't match.")
    if not re.search(USERNAME_PATTERN, input_name):
        messages.append("The username format doesn't match.")
    if not USER_PASSWORD_MIN <= len(input_password) <= USER_PASSWORD_LENGTH:
        messages.append("The password length doesn't match.")
    if input_confirmation and not input_password == input_confirmation:
        messages.append("The password fields doesn't match.")
    return messages


if __name__ == '__main__':
    pass
