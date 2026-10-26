from flask import Blueprint, render_template, request, redirect, session, jsonify, flash
from datetime import datetime, timezone
from extensions import db, bcrypt
from models import User, Comment, Post
from sqlalchemy.exc import IntegrityError

"""
Routes:
feed->
    /
    /global
user management ->
    /login  
    /signup
    /logout
    /profile/<username>
post management ->
    /like/<post_id>
    /comment/<post_id>

"""
main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def fyp():
    if "username" in session:
        current_user = User.query.filter_by(username=session["username"]).first()

        followed_usernames = [u.username for u in current_user.followed.all()] #type:ignore

        page = request.args.get("page", 1, type=int)
        pagination = (
            Post.query.filter(Post.username.in_(followed_usernames))
            .order_by(Post.timestamp.desc())
            .paginate(page=page, per_page=10, error_out=False)
        )
        posts = pagination.items
        comments = Comment.query.order_by(Comment.timestamp).all()
        return render_template(
            "feed.html", pagination=pagination, posts=posts, comments=comments
        )
    else:
        flash("Please Login To continue", "warning")
        return redirect("/login")


@main_bp.route("/global")
def globalfyp():
    if "username" in session:
        page = request.args.get("page", 1, type=int)
        pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
            page=page, per_page=10, error_out=False
        )
        posts = pagination.items
        comments = Comment.query.order_by(Comment.timestamp).all()
        return render_template(
            "feed.html", pagination=pagination, posts=posts, comments=comments
        )
    else:
        return render_template("login.html")

#eyyyy

@main_bp.route("/profile/<username>")
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    sorted_posts = sorted(user.posts, key=lambda p: p.timestamp, reverse=True)

    return render_template("profile.html", profile_user=user, posts=sorted_posts)


@main_bp.route("/like/<int:post_id>", methods=["POST"])
def like(post_id):
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    post = Post.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()

    return jsonify({"success": True, "new_likes": post.likes})


@main_bp.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    comment_text = request.form.get("comment")

    if not comment_text:
        flash("Comment can't be empty", "warning")
        return jsonify({"error": "Comment cannot be empty"}), 400

    new_comment = Comment(
        content=comment_text,  # type:ignore
        post_id=post_id,  # type:ignore
        username=session["username"],  # type:ignore
    )
    db.session.add(new_comment)
    db.session.commit()
    return jsonify(
        {
            "success": True,
            "username": session.get("username"),
            "content": new_comment.content,
            "timestamp": datetime.now(timezone.utc),
        }
    )


@main_bp.route("/post/", methods=["POST"])
def post():
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    post_text = request.form.get("content")

    if not post_text:
        flash("Post can't be empty", "warning")
        return redirect("/")

    post = Post(content=post_text, username=session["username"])  # type:ignore
    try:
        db.session.add(post)
        db.session.commit()
        flash("Post sent!", "success")
        return redirect("/")

    except Exception as e:
        print(f"ERROR: {e}")
        return f"ERROR: {e}"


@main_bp.route("/login", methods=["POST", "GET"])
def login():

    if request.method == "POST":
        form_username = request.form["username"]
        form_password = request.form["password"]

        user = User.query.filter_by(username=form_username).first()

        if user and bcrypt.check_password_hash(user.password_hash, form_password):
            session["username"] = form_username
            flash("Logged in successfully!", "success")
            return redirect("/")
        else:
            flash("Invalid username or password.", "danger")
            return redirect("/login")
    else:
        return render_template("login.html")


@main_bp.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        form_username = request.form["username"]
        form_password = request.form["password"]

        if not form_username or not form_password:
            flash("Please fill out all fields", "warning")

        hashed_password = bcrypt.generate_password_hash(form_password).decode("utf-8")

        new_user = User(username=form_username, password_hash=hashed_password)  # type: ignore

        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect("/login")

        except IntegrityError as e:
            flash("User already exists, please try other username", "warning")
            return redirect("/signup")

    else:
        return render_template("signup.html")


@main_bp.route("/logout")
def logout():
    session.pop("username")
    return redirect("/signup")
