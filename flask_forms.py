from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField, HiddenField, TextAreaField, validators

from constants import *


class LoginForm(FlaskForm):
    name = StringField("Name", [
        validators.DataRequired(message="Empty input."),
        validators.Length(min=USERNAME_MIN, max=USERNAME_LENGTH, \
            message="The username length doesn't match.")
    ])
    password = PasswordField("Password", [
        validators.DataRequired(message="Empty input."),
        validators.Length(min=USER_PASSWORD_MIN, max=USER_PASSWORD_LENGTH, \
            message="The password length doesn't match.")
    ])
    submit = SubmitField()


class AnonymizeForm(FlaskForm):
    anonymize = HiddenField("Anonymize", [validators.DataRequired(message="Wrong input.")])
    anon_submit = SubmitField()


class ChangePassword(FlaskForm):
    old_password = PasswordField("Old password", [
        validators.DataRequired(message="Empty input."),
        validators.Length(min=USER_PASSWORD_MIN, max=USER_PASSWORD_LENGTH, \
            message="The password length doesn't match.")
    ])
    new_password = PasswordField("New password", [
        validators.DataRequired(message="Empty input."),
        validators.Length(min=USER_PASSWORD_MIN, max=USER_PASSWORD_LENGTH, \
            message="The password length doesn't match."),
        validators.EqualTo('confirmation', message="The password confirmation doesn't match.")
    ])
    confirmation = PasswordField("Repeat password", [
        validators.DataRequired(message="Empty input."),
        validators.Length(min=USER_PASSWORD_MIN, max=USER_PASSWORD_LENGTH, \
            message="The password length doesn't match.")
    ])
    submit = SubmitField()


class RegisterForm(FlaskForm):
    name = StringField("Name", [
        validators.DataRequired(message="Empty input."),
        validators.Length(min=USERNAME_MIN, max=USERNAME_LENGTH, \
            message="The username length doesn't match.")
    ])
    password = PasswordField("Password", [
        validators.DataRequired(message="Empty input."),
        validators.Length(min=USER_PASSWORD_MIN, max=USER_PASSWORD_LENGTH, \
            message="The password length doesn't match."),
        validators.EqualTo('confirmation', message="The password confirmation doesn't match.")
    ])
    confirmation = PasswordField("Repeat password", [
        validators.DataRequired(message="Empty input."),
        validators.Length(min=USER_PASSWORD_MIN, max=USER_PASSWORD_LENGTH, \
            message="The password length doesn't match.")
    ])
    submit = SubmitField()
