from flask import Flask, url_for, request, render_template, make_response
from flask_assets import Environment, Bundle
from markupsafe import escape

from pprint import pprint
import secrets
import datetime

app = Flask(__name__)
app.config.update(
    ENV='development',
    DEBUG=True,
    SECRET_KEY=secrets.token_hex(),
    SESSION_COOKIE_SAMESITE='Lax',
    # SESSION_COOKIE_SECURE=True,
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=1),
    TEMPLATES_AUTO_RELOAD=True
)
# scss, paths are relative to /static directory
assets = Environment(app)
assets.url = app.static_url_path
scss = Bundle(
    "../scss/main.scss", "../scss/footer.scss", "../scss/index.scss",
    "../scss/login.scss", "../scss/board.scss",
    filters='pyscss', output="css/styles.css"
)
assets.register('styles', scss)


@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html"), 200


@app.route("/brotherhood/")
@app.route("/b/")
@app.route("/b")
def brotherhood():
    return render_template("brotherhood.html"), 200


@app.route("/animation/")
@app.route("/a/")
@app.route("/a")
def animation():
    return render_template("animation.html"), 200


@app.route("/university/")
@app.route("/u/")
@app.route("/u")
def university():
    return render_template("university.html"), 200


@app.route("/login")
def login():
    return render_template("login.html"), 200


"""
@app.route("/<int:id>")
def show_id(id):
    return f"ID: {id}"

@app.route("/<path:subpath>")
def show_subpath(subpath):
    return f"Path: {escape(subpath)}"

@app.route("/projects/")
def projects():
    return "The project page"

@app.route('/about')
def about():
    return 'The about page'

@app.route('/user/<username>')
def profile(username):
    return f'{escape(username)}\'s profile'

@app.errorhandler(404)
def page_not_found(error):
    return "404"

with app.test_request_context():
    print("hello")

with app.test_request_context("/"):
    assert request.path == '/'
    assert request.method == 'GET'
    print("OK index")
"""
