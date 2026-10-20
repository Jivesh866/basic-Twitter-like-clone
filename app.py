from flask import Flask, render_template, request, redirect, session, jsonify
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
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), db.ForeignKey('user.username'), nullable=False)
    content = db.Column(db.String(200), nullable=False)
    likes = db.Column(db.Integer,default=0)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    username = db.Column(db.String(20), db.ForeignKey('user.username'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)


@app.template_filter("time_ago")
def time_ago(utc_dt):
  if not utc_dt:
    return ""
  
  if utc_dt.tzinfo is None:
    utc_dt = utc_dt.replace(tzinfo=timezone.utc)

  now = datetime.now(timezone.utc)
  diff = now - utc_dt

  seconds = int(diff.total_seconds())

  if seconds < 60:
    return "just now"
  minutes = seconds // 60
  if minutes < 60:
    return f"{minutes}m ago" if minutes == 1 else f"{minutes}m ago"
  hours = minutes // 60
  if hours < 24:
    return f"{hours}h ago"
  days = hours // 24
  if days < 30:
    return f"{days}d ago"
  months = days // 30
  if months < 12:
    return f"{months}mo ago"

  years = days // 365
  return f"{years}y ago"

@app.route("/", methods=["POST", "GET"])
def fyp():
    if 'username' in session:
        if request.method == "POST":
            content = request.form["content"]
            if not content:
                return "Enter Something to post", 400
            post = Post(content=content,username=session['username'])  # type:ignore 
            try:
                db.session.add(post)
                db.session.commit()
                return redirect("/")

            except Exception as e:
                print(f"ERROR: {e}")
                return f"ERROR: {e}"

        else:
            page = request.args.get('page', 1, type=int)
            pagination = Post.query.order_by(Post.timestamp.desc()).paginate(page=page, per_page=10, error_out=False)
            posts = pagination.items
            comments= Comment.query.order_by(Comment.timestamp).all()
            return render_template("feed.html",pagination=pagination, posts=posts, comments=comments)
    else:
        return render_template("login.html")

    
@app.route("/like/<int:post_id>",methods=["POST"])
def like(post_id):
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    post = Post.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    
    return jsonify({
        "success": True,
        "new_likes": post.likes
    })

@app.route("/comment/<int:post_id>",methods=["POST"])
def comment(post_id):
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    comment_text = request.form.get("comment") or request.json.get("comment")

    if not comment_text:
        return jsonify({"error": "Comment cannot be empty"}), 400

    new_comment = Comment(
        content=comment_text, #type:ignore
        post_id=post_id, #type:ignore
        username=session["username"], #type:ignore
    ) 
    db.session.add(new_comment)
    db.session.commit()
    # Return the data needed for the frontend to render it instantly
    return jsonify({
        "success": True,
        "username": session.get("username"),
        "content": new_comment.content,
        "timestamp": datetime.now(timezone.utc), 
    })
    

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
    return redirect("/signup")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
