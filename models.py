from extensions import db
from datetime import datetime, timezone



followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

db.Index('idx_followers_followed', followers.c.followed_id)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password_hash = db.Column(db.String(60), nullable=False)
    posts = db.relationship("Post", backref="author", lazy=True)
    comments = db.relationship("Comment", backref="author", lazy=True)

    followed = db.relationship(
        'User',
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )



class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), db.ForeignKey("user.username"), nullable=False, index=True)
    content = db.Column(db.String(200), nullable=False)
    likes = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),index=True)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default= lambda: datetime.now(timezone.utc))
    username = db.Column(db.String(20), db.ForeignKey("user.username"), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False, index=True)
