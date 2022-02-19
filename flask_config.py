from flask import Flask

from flask_session import Session

from flask_assets import Environment, Bundle

from constants import *


app = Flask(__name__)
app.config.update(
    ENV = 'development',
    DEBUG = True,
    SECRET_KEY = secrets.token_hex(),
    SESSION_COOKIE_SAMESITE = 'Lax',
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=1),
    TEMPLATES_AUTO_RELOAD = True,
    UPLOAD_FOLDER = FILE_STORAGE / "tmp",
    MAX_CONTENT_PATH = 50000000
)

# <sessions>
app.config.update(
    SESSION_FILE_DIR = mkdtemp(),
    SESSION_PERMANENT = False,
    SESSION_TYPE = 'filesystem'
)
Session(app)
# </sessions>

# <scss>
scss_list = [
    str(CWD / "scss" / "main.scss"),
    str(CWD / "scss" / "footer.scss"),
    str(CWD / "scss" / "index.scss"),
    str(CWD / "scss" / "menu.scss"),
    str(CWD / "scss" / "board.scss"),
]
css_file = str(CWD / "static" / "css" / "styles.css")

assets = Environment(app)
assets.url = app.static_url_path
scss = Bundle(scss_list, filters='pyscss', output=css_file)
assets.register('styles', scss)
# </scss>
