from flask import Flask, render_template
from datetime import datetime, timezone
from extensions import db,bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URI")


db.init_app(app)
bcrypt.init_app(app)


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
    return f"{minutes}m ago"
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

"""ERROR HANDLING"""
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404



from routes import main_bp
app.register_blueprint(main_bp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
