from flask import Flask, render_template, request
from flask_login import LoginManager, UserMixin, login_required, current_user
from models import db, User
from auth import auth as auth_blueprint
import joblib
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import csv
import plotly.express as px
import plotly.graph_objects as go
from prediction import Prediction

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_BINDS'] = {
    'predictions': 'sqlite:///predictions.db'
}



db.init_app(app)
with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(auth_blueprint)

model = joblib.load("model.pkl")

def generate_feature_plot(df, x_feature, y_feature, predicted_price, timestamp, show_current_dot=True):
    fig = px.scatter(
        df, x=x_feature, y=y_feature,
        title=f"{x_feature} vs. {y_feature}",
        template="plotly_white",
        labels={x_feature: x_feature.replace("_", " ").title(), y_feature: "Price (₹)"}
    )

    if show_current_dot and predicted_price:
        fig.add_scatter(
            x=[df[x_feature].iloc[-1]],
            y=[df[y_feature].iloc[-1]],
            mode='markers+text',
            marker=dict(color='red', size=12),
            text=["Your Prediction"],
            textposition="top center",
            name="Prediction"
        )

    fig.write_html(f"static/{x_feature}_{timestamp}.html")
    fig.write_image(f"static/{x_feature}_{timestamp}.png")

@app.route('/')
@login_required
def home():
    return render_template('index.html')


@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    if request.method == 'GET':
        return render_template("Prediction_Page.html")
    elif request.method == 'POST':
        try:
            total_area = float(request.form['total_area'])
            res_land_percent = float(request.form['residential_land_percent'])
            residential_land = (res_land_percent / 100) * total_area

            base_price = float(request.form['base_price'])
            expected_price = float(request.form['expected_price'])

            avg_rooms = float(request.form["avg_rooms"])
            crime_rate = float(request.form["crime_rate"])
            offices = int(request.form["offices"])
            rivers = 1 if request.form["rivers"].lower() == "yes" else 0
            cafes = int(request.form["cafes"])
            school_type = 1 if request.form["school_type"].lower() == "private" else 0
            num_schools = float(request.form["num_schools"])
            malls = int(request.form["malls"])
            comm_land = 1 if request.form["comm_land"].lower() == "yes" else 0

            features = [residential_land, avg_rooms, crime_rate, offices, rivers,
                        cafes, school_type, num_schools, malls, comm_land]

            prediction = model.predict([features])[0]
            prediction = max(prediction, 0)
            price_in_inr = prediction * 83

            # Manual adjustment
            manual_price = 0
            manual_price += base_price * residential_land
            manual_price += 5000 * num_schools if school_type == 1 else 3500 * num_schools
            manual_price += 2000 * malls
            manual_price += 4000 * cafes
            manual_price += 50000 if rivers == 1 else 0

            if 0 <= crime_rate < 10:
                manual_price -= 50000
            elif 10 <= crime_rate < 20:
                manual_price -= 100000
            elif 20 <= crime_rate < 30:
                manual_price -= 150000
            else:
                manual_price -= 200000

            price_in_inr += manual_price
            price_in_inr = max(price_in_inr, 0)  # ⛔ Prevent negative values

            expected_price = max(expected_price, 0)  # Just in case user input is bad

            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

            # 🟧 Print for Debugging
            print("🔍 Prediction (raw):", prediction)
            print("🧮 Manual adj.:", manual_price)
            print("💰 Final price:", price_in_inr)

            # Comparison Plot
            comparison_fig = go.Figure(data=[
                go.Bar(name='Expected Price', x=['Price'], y=[expected_price], marker_color='lightblue'),
                go.Bar(name='Predicted Price', x=['Price'], y=[price_in_inr], marker_color='orange')
            ])
            comparison_fig.update_layout(
                title="Expected vs Predicted Price",
                yaxis_title="Price (₹)",
                barmode='group',
                template="plotly_white"
            )
            comp_html_file = f"static/comp_{timestamp}.html"
            comparison_fig.write_html(comp_html_file)

            # Save to DB
            new_prediction = Prediction(
                user_id=current_user.id,
                res_land=residential_land,
                avg_rooms=avg_rooms,
                crime_rate=crime_rate,
                offices=offices,
                rivers=rivers,
                cafes=cafes,
                school_type=school_type,
                num_schools=num_schools,
                malls=malls,
                comm_land=comm_land,
                price_in_inr=price_in_inr
            )
            db.session.add(new_prediction)
            db.session.commit()

            # Save to CSV
            os.makedirs("predictions", exist_ok=True)
            file_path = "predictions/predictions.csv"
            file_exists = os.path.exists(file_path)
            with open(file_path, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        "residential_land", "avg_rooms", "crime_rate", "offices", "rivers",
                        "cafes", "school_type", "num_schools", "malls", "comm_land", "PRICE"
                    ])
                writer.writerow(features + [round(price_in_inr, 2)])

            # Generate Plots
            df = pd.read_csv(file_path)
            generate_feature_plot(df, "avg_rooms", "PRICE", price_in_inr, timestamp)
            generate_feature_plot(df, "crime_rate", "PRICE", price_in_inr, timestamp)
            generate_feature_plot(df, "res_land", "PRICE", price_in_inr, timestamp)

            note = ""
            if price_in_inr > 50000000:
                note = "Note: This seems unusually high. Please check input values."

            return render_template("result.html", prediction=round(price_in_inr, 2), timestamp=timestamp, note=note, expected_price=round(expected_price, 2))

        except Exception as e:
            return f"Error: {str(e)}"

@app.route('/show_previous')
@login_required
def show_previous():
    try:
        # Fetch data from DB for the current user
        predictions = Prediction.query.filter_by(user_id=current_user.id).all()
        if not predictions:
            return "No previous predictions found."

        # Convert to DataFrame
        data = [{
            "res_land": p.res_land,
            "avg_rooms": p.avg_rooms,
            "crime_rate": p.crime_rate,
            "offices": p.offices,
            "rivers": p.rivers,
            "cafes": p.cafes,
            "school_type": p.school_type,
            "num_schools": p.num_schools,
            "malls": p.malls,
            "comm_land": p.comm_land,
            "PRICE": p.price_in_inr
        } for p in predictions]

        df = pd.DataFrame(data)
        timestamp = "previous"

        # Generate plots
        generate_feature_plot(df, "avg_rooms", "PRICE", None, timestamp, show_current_dot=False)
        generate_feature_plot(df, "crime_rate", "PRICE", None, timestamp, show_current_dot=False)
        generate_feature_plot(df, "res_land", "PRICE", None, timestamp, show_current_dot=False)

        return render_template("previous_predictions.html", timestamp=timestamp)

    except Exception as e:
        return f"Error showing previous predictions: {e}"

if __name__ == "__main__":
    with app.app_context():
        
        db.create_all()
    app.run(debug=True)
