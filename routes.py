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
from models import User, Comment, Post, followers, post_likes
from sqlalchemy import func, select
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

POSTS_PER_PAGE = 10


@main_bp.before_request
def load_logged_in_user():
    if "username" in session:
        g.current_user = User.query.filter_by(username=session["username"]).first()
    else:
        g.current_user = None


def get_followed_usernames(user):
    """Usernames `user` follows, in a single query."""
    if user is None:
        return set()
    return set(
        db.session.scalars(
            select(User.username)
            .join(followers, followers.c.followed_id == User.id)
            .where(followers.c.follower_id == user.id)
        )
    )


def load_page_extras(posts):
    """
    Everything the post cards need (comments, like counts, which posts the
    current user liked), fetched for ONLY the posts on this page, in 3 queries
    total instead of several queries per post.
    """
    comments_by_post, like_counts, liked_ids = {}, {}, set()
    post_ids = [p.id for p in posts]
    if not post_ids:
        return comments_by_post, like_counts, liked_ids

    comments = (
        Comment.query.filter(Comment.post_id.in_(post_ids))
        .order_by(Comment.timestamp)
        .all()
    )
    for c in comments:
        comments_by_post.setdefault(c.post_id, []).append(c)

    rows = db.session.execute(
        select(post_likes.c.post_id, func.count())
        .where(post_likes.c.post_id.in_(post_ids))
        .group_by(post_likes.c.post_id)
    ).all()
    like_counts = {post_id: n for post_id, n in rows}

    if g.current_user:
        liked_ids = set(
            db.session.scalars(
                select(post_likes.c.post_id).where(
                    post_likes.c.user_id == g.current_user.id,
                    post_likes.c.post_id.in_(post_ids),
                )
            )
        )
    return comments_by_post, like_counts, liked_ids


def render_feed(pagination, followed_usernames):
    comments, like_counts, liked_ids = load_page_extras(pagination.items)
    return render_template(
        "feed.html",
        pagination=pagination,
        posts=pagination.items,
        comments=comments,
        like_counts=like_counts,
        liked_ids=liked_ids,
        followed_usernames=followed_usernames,
    )


@main_bp.route("/")
def fyp():
    if g.current_user:
        followed_usernames = get_followed_usernames(g.current_user)

        page = request.args.get("page", 1, type=int)
        pagination = (
            Post.query.filter(Post.username.in_(list(followed_usernames)))
            .order_by(Post.timestamp.desc(), Post.id.desc())
            .paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
        )
        return render_feed(pagination, followed_usernames)
    else:
        flash("Please Login To continue", "warning")
        return redirect(url_for("main.login"))


@main_bp.route("/global")
def globalfyp():
    if g.current_user:
        page = request.args.get("page", 1, type=int)
        pagination = Post.query.order_by(
            Post.timestamp.desc(), Post.id.desc()
        ).paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
        return render_feed(pagination, get_followed_usernames(g.current_user))
    else:
        return render_template("login.html")


@main_bp.route("/profile/<username>")
def profile(username):
    profile_user = User.query.filter_by(username=username).first_or_404()

    page = request.args.get("page", 1, type=int)
    pagination = (
        Post.query.filter_by(username=username)
        .order_by(Post.timestamp.desc(), Post.id.desc())
        .paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
    )
    comments, like_counts, liked_ids = load_page_extras(pagination.items)

    followed_usernames = get_followed_usernames(g.current_user)
    is_following = profile_user.username in followed_usernames

    return render_template(
        "profile.html",
        profile_user=profile_user,
        pagination=pagination,
        posts=pagination.items,
        is_following=is_following,
        comments=comments,
        like_counts=like_counts,
        liked_ids=liked_ids,
        followed_usernames=followed_usernames,
    )


@main_bp.route("/follow/<username>", methods=["POST"])
def follow_toggle(username):
    current_user = g.current_user  
    if current_user is None:
        return redirect(url_for("main.login"))
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


    return redirect(url_for("main.profile", username=username))


@main_bp.route("/like/<int:post_id>", methods=["POST"])
def like(post_id):
    if g.current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    db.get_or_404(Post, post_id)
    user_id = g.current_user.id


    already_liked = db.session.execute(
        select(post_likes).where(
            post_likes.c.user_id == user_id, post_likes.c.post_id == post_id
        )
    ).first()

    if already_liked:
        db.session.execute(
            post_likes.delete().where(
                post_likes.c.user_id == user_id, post_likes.c.post_id == post_id
            )
        )
        liked = False
    else:
        db.session.execute(post_likes.insert().values(user_id=user_id, post_id=post_id))
        liked = True

    db.session.commit()

    new_like_count = db.session.scalar(
        select(func.count()).select_from(post_likes).where(post_likes.c.post_id == post_id)
    )

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
