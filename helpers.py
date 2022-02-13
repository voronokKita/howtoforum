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


if __name__ == '__main__':
    pass
