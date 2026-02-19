from datetime import datetime
from models import db

class Prediction(db.Model):
    __bind_key__ = 'predictions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    res_land = db.Column(db.Float)
    avg_rooms = db.Column(db.Float)
    crime_rate = db.Column(db.Float)
    offices = db.Column(db.Integer)
    rivers = db.Column(db.Integer)
    cafes = db.Column(db.Integer)
    school_type = db.Column(db.Integer)
    num_schools = db.Column(db.Float)
    malls = db.Column(db.Integer)
    comm_land = db.Column(db.Integer)
    expected_price = db.Column(db.Float)
    price_in_inr = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.now)  # ✅ Add this line
