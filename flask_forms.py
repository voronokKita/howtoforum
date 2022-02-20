from flask_wtf import FlaskForm
from flask_wtf.file import FileField

from wtforms import SubmitField, StringField, PasswordField, HiddenField, TextAreaField, validators
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError

from constants import *


class LoginForm(FlaskForm):
    name = StringField("Name", [
        DataRequired(message=M_EMPTY),
        Length(min=USERNAME_MIN, max=USERNAME_LENGTH, message=M_USERNAME_LEN)
    ])
    password = PasswordField("Password", [
        DataRequired(message=M_EMPTY),
        Length(min=USER_PASSWORD_MIN, max=USER_PASSWORD_LENGTH, message=M_PASSWORD_LEN)
    ])
    submit = SubmitField()


class AnonymizeForm(FlaskForm):
    anonymize = HiddenField("Anonymize", [DataRequired(message=M_WRONG)])
    anon_submit = SubmitField()


class ChangePassword(FlaskForm):
    old_password = PasswordField("Old password", [
        DataRequired(message=M_EMPTY),
        Length(min=USER_PASSWORD_MIN, max=USER_PASSWORD_LENGTH, message=M_PASSWORD_LEN)
    ])
    new_password = PasswordField("New password", [
        DataRequired(message=M_EMPTY),
        Length(min=USER_PASSWORD_MIN, max=USER_PASSWORD_LENGTH, message=M_PASSWORD_LEN),
        EqualTo('confirmation', message=M_PASSWORD_CONFIRM)
    ])
    confirmation = PasswordField("Repeat password", [
        DataRequired(message=M_EMPTY),
        Length(min=USER_PASSWORD_MIN, max=USER_PASSWORD_LENGTH, message=M_PASSWORD_LEN)
    ])
    submit = SubmitField()


class RegisterForm(FlaskForm):
    name = StringField("Name", [
        DataRequired(message=M_EMPTY),
        Length(min=USERNAME_MIN, max=USERNAME_LENGTH, message=M_USERNAME_LEN)
    ])
    password = PasswordField("Password", [
        DataRequired(message=M_EMPTY),
        Length(min=USER_PASSWORD_MIN, max=USER_PASSWORD_LENGTH, message=M_PASSWORD_LEN),
        EqualTo('confirmation', message=M_PASSWORD_CONFIRM)
    ])
    confirmation = PasswordField("Repeat password", [
        DataRequired(message=M_EMPTY),
        Length(min=USER_PASSWORD_MIN, max=USER_PASSWORD_LENGTH, message=M_PASSWORD_LEN)
    ])
    submit = SubmitField()


class MakeThread(FlaskForm):
    theme = StringField("Theme", [Length(max=DEFAULT_LENGTH, message=M_POST_THEME_LEN)])
    password = PasswordField("Password", [Length(max=ANON_PASSWORD_LENGTH, message=M_POST_PASSWORD_LEN)])
    text = TextAreaField("Text")
    file1 = FileField("File1")
    file2 = FileField("File2")
    file3 = FileField("File3")
    submit = SubmitField()


class MakePost(MakeThread):
    thread_id = HiddenField("Thread", [DataRequired(message=M_WRONG)])
