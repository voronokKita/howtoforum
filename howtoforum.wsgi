#!/usr/bin/python3
import sys
import logging

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/home/kita/Main/Code/Misc/HowtoForum")

activate_venv = "/home/kita/Main/Code/Misc/HowtoForum/_forum_venv/bin/activate"
with open(activate_venv) as v:
	exec(v.read(), dict(__file__=activate_venv))

from app import app as application

#application.secret_key = '37463654952'
