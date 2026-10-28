from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    jsonify,
    flash,
    g,
    url_for,
)
from datetime import datetime, timezone
from extensions import db, bcrypt
from models import User, Comment, Post, followers
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
    /follow/<username>

"""
main_bp = Blueprint("main", __name__)


@main_bp.before_request
def load_logged_in_user():
    if "username" in session:
        g.current_user = User.query.filter_by(username=session["username"]).first()
    else:
        g.current_user = None


@main_bp.route("/")
def fyp():
    if "username" in session:
        followed_usernames = [u.username for u in g.current_user.followed.all()]  # type:ignore

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
        return redirect(url_for("main.login"))


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


@main_bp.route("/profile/<username>")
def profile(username):
    profile_user = User.query.filter_by(username=username).first_or_404()
    posts = (
        Post.query.filter_by(username=username).order_by(Post.timestamp.desc()).all()
    )
    comments = Comment.query.order_by(Comment.timestamp).all()
    
    is_following = False
    
    if "username" in session:
        is_following = (
            g.current_user.followed.filter(
                followers.c.followed_id == profile_user.id
            ).count()
            > 0
        )  # type:ignore

    return render_template(
        "profile.html",
        profile_user=profile_user,
        posts=posts,
        is_following=is_following,
        comments=comments
    )


@main_bp.route("/follow/<username>", methods=["POST"])
def follow_toggle(username):
    if "username" not in session:
        return redirect(url_for("main.login"))

    current_user = User.query.filter_by(username=session["username"]).first()
    target_user = User.query.filter_by(username=username).first_or_404()

    if current_user.id == target_user.id:  # type: ignore
        return redirect(url_for("main.profile", username=username))

    is_following = (
        current_user.followed.filter(followers.c.followed_id == target_user.id).count() # type: ignore
        > 0
    )  

    if is_following:
        current_user.followed.remove(target_user)  # type: ignore
    else:
        current_user.followed.append(target_user)  # type: ignore

    db.session.commit()

    # Send them right back to the profile page they were looking at
    return redirect(url_for("main.profile", username=username))


@main_bp.route("/like/<int:post_id>", methods=["POST"])
def like(post_id):
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = User.query.filter_by(username=session["username"]).first_or_404()
    post = Post.query.get_or_404(post_id)

    if post in current_user.liked_posts:
        current_user.liked_posts.remove(post)
        liked = False
    else:
        current_user.liked_posts.append(post)
        liked = True

    db.session.commit()

    new_like_count = post.liked_by.count()

    return jsonify({"success": True, "liked": liked, "new_likes": new_like_count})


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
            return redirect(url_for("main.login"))
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
            return redirect(url_for("main.login"))

        except IntegrityError as e:
            flash("User already exists, please try other username", "warning")
            return redirect(url_for("main.signup"))

    else:
        return render_template("signup.html")


@main_bp.route("/logout")
def logout():
    session.pop("username")
    return redirect(url_for("main.signup"))
