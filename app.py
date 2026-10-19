from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from flask_bcrypt import Bcrypt


app = Flask(__name__)
app.secret_key="23476234672364hjugfahdsvfhdvhshfk87r23563t2grkvfwej"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False,unique=True)
    password_hash = db.Column(db.String(60), nullable=False)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,nullable=False)
    content = db.Column(db.String(200), nullable=False)
    likes = db.Column(db.Integer,default=0)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, nullable=False)
    post_id = db.Column(db.Integer, nullable=False)

@app.route("/", methods=["POST", "GET"])
def fyp():
    if 'username' in session:
        if request.method == "POST":
            content = request.form["content"]
            if not content:
                return "Enter Something to post", 400
            post = Post(content=content)  # type:ignore 
            try:
                db.session.add(post)
                db.session.commit()
                return redirect("/")

            except Exception as e:
                print(f"ERROR: {e}")
                return f"ERROR: {e}"

        else:
            posts = Post.query.order_by(Post.timestamp).limit(10).all()
            return render_template("feed.html", posts=posts)
    else:
        return render_template("login.html")

    
@app.route("/like",methods=["POST"])
def like():
    return ""

@app.route("/comment",methods=["POST"])
def comment():
    return ""

@app.route("/login", methods=["POST", "GET"])
def login():

    if request.method == "POST":
        form_username = request.form["username"]
        form_password = request.form["password"]

        user = User.query.filter_by(username=form_username).first()

        if user and bcrypt.check_password_hash(user.password_hash, form_password):
            session['username']=form_username
            return redirect("/")
        else:
            return "Invalid Credentials"
    else:
        return render_template("login.html")


@app.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        form_username = request.form["username"]
        form_password = request.form["password"]

        if not form_username or not form_password:
            return "Please fill out all fields", 400

        hashed_password = bcrypt.generate_password_hash(form_password).decode("utf-8")

        new_user = User(username=form_username, password_hash=hashed_password)  # type: ignore

        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect("/")

        except Exception as e:
            print(f"ERROR: {e}")
            return f"ERROR: {e}"

    else:
        return render_template("signup.html")


@app.route("/logout")
def logout():
    session.pop('username')
    return render_template("signup.html")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
