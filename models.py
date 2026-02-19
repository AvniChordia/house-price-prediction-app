from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    res_land = db.Column(db.Float, nullable=False)
    avg_rooms = db.Column(db.Float, nullable=False)
    crime_rate = db.Column(db.Float, nullable=False)
    offices = db.Column(db.Integer, nullable=False)
    rivers = db.Column(db.Integer, nullable=False)
    cafes = db.Column(db.Integer, nullable=False)
    school_type = db.Column(db.Integer, nullable=False)
    num_schools = db.Column(db.Float, nullable=False)
    malls = db.Column(db.Integer, nullable=False)
    comm_land = db.Column(db.Integer, nullable=False)
    price_in_inr = db.Column(db.Float, nullable=False)
