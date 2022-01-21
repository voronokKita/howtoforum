from flask import Flask, url_for, request, render_template, make_response
from markupsafe import escape

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True


@app.route("/")
def index():
    return render_template("index.html"), 200


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


@app.route('/login')
@app.route('/login/<string:username>')
def login(username=None):
    error = None
    if username:
        return f"User {escape(username)} login"
    else:
        return 'Invalid username/password'


with app.test_request_context():
    print("hello")

with app.test_request_context("/"):
    assert request.path == '/'
    assert request.method == 'GET'
    print("OK index")
