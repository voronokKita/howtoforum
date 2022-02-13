# HOWTO Forum, work in progress

My imageboard-like forum on Flask.

0. pipenv install<br>
1. pipenv shell<br>
2. FLASK_APP=app.py FLASK_ENV=development flask run

The goal is to learn the Flask + Apache-server + SQL deployment.

## A sort of journal

#### update one

I ran into trouble with deployment of Flask on Apache. I decided that it isn't worth it to waste time solving them and drop the Apache. Still, I managed to learn basics of Apache and deploy two static sites via virtual hosts.<br>
I also ran into Pipenv and find it very good.<br>
Basics chassi for the forum is ready, now going to learn SQL.

#### update two

I took a basic SQL course. It turned out that the main difference with SQLite is the way of deploymend and access a db through the web interface.<br>
I think that this is sufficient knowledge for my level. Switching to SQLite, simply for ease of distribution.<br>
I learned and clarified the things I wanted to. Now I'll just write a working forum.

#### update three

There's so much depth in sites development, even the simplest thing can be a rabbit hole to endless variants of implementation and new fields of knowledge.<br>
Need in multiple forms lead me to WTForms package, that I going to learn now.
