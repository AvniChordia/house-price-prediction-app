from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_required, current_user, logout_user
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
app.secret_key = 'house-price-dev-key'
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
    return db.session.get(User, int(user_id))

app.register_blueprint(auth_blueprint)

model = joblib.load("model.pkl")

def generate_feature_plot(df, x_feature, y_feature, predicted_price=None, timestamp=None, show_current_dot=True):
    df = df.dropna(subset=[x_feature, y_feature])
    fig = px.scatter(
        df, x=x_feature, y=y_feature,
        title=f"{x_feature.replace('_', ' ').title()} vs. {y_feature.replace('_', ' ').title()}",
        template="plotly_white",
        labels={
            x_feature: x_feature.replace("_", " ").title(),
            y_feature: "Price (₹)"
        }
    )
    if show_current_dot and predicted_price is not None and timestamp is not None and 'timestamp' in df.columns:
        current_data = df[df['timestamp'] == timestamp]

        if not current_data.empty:
            fig.add_scatter(
                x=current_data[x_feature],
                y=current_data[y_feature],
                mode='markers',
                marker=dict(size=10, color='red'),
                name='Current Prediction'
            )
    return fig


@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template('index.html')
    else:
        return redirect(url_for('auth.login'))

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

            manual_price = 0
            manual_price += base_price * residential_land
            manual_price += 5000 * num_schools if school_type == 1 else 3500 * num_schools
            manual_price += 2000 * malls
            manual_price += 4000 * cafes
            manual_price += 50000 if rivers == 1 else 0

            price_in_inr += manual_price
            price_in_inr = max(price_in_inr, 0)
            expected_price = max(expected_price, 0)

            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

            # Comparison Plot (Expected vs Predicted)
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
                expected_price=expected_price,
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
                        "cafes", "school_type", "num_schools", "malls", "comm_land",
                        "expected_price", "predicted_price", "timestamp"
                    ])
                writer.writerow(features + [expected_price, round(price_in_inr, 2), timestamp])

            # Read CSV and generate feature plots
            df = pd.read_csv(file_path)

            fig1 = generate_feature_plot(df, "avg_rooms", "predicted_price", price_in_inr, timestamp)
            fig2 = generate_feature_plot(df, "crime_rate", "predicted_price", price_in_inr, timestamp)
            fig3 = generate_feature_plot(df, "residential_land", "predicted_price", price_in_inr, timestamp)

            feature_graphs = [
                fig1.to_html(full_html=False),
                fig2.to_html(full_html=False),
                fig3.to_html(full_html=False)
            ]

            note = ""
            if price_in_inr > 50000000:
                note = "Note: This seems unusually high. Please check input values."

            return render_template("result.html",
                                   prediction=round(price_in_inr, 2),
                                   timestamp=timestamp,
                                   note=note,
                                   expected_price=round(expected_price, 2),
                                   feature_graphs=feature_graphs,
                                   comp_graph=f"comp_{timestamp}.html")

        except Exception as e:
            return f"Error: {str(e)}"

@app.route('/show_previous')
@login_required
def show_previous():
    try:
        print(f"Current Logged-in User ID: {current_user.id}")  # Debug

        predictions = Prediction.query.filter_by(user_id=current_user.id).all()
        if not predictions:
            return render_template("previous_predictions.html", predictions=None, timestamp="previous")

        data = []
        for p in predictions:
            data.append({
                "timestamp": p.timestamp.strftime("%Y-%m-%d %H:%M:%S") if p.timestamp else "N/A",
                "residential_land": p.res_land,
                "avg_rooms": p.avg_rooms,
                "crime_rate": p.crime_rate,
                "expected_price": getattr(p, 'expected_price', 0),
                "predicted_price": p.price_in_inr
            })

        df = pd.DataFrame(data)

        figs = []
        figs.append(generate_feature_plot(df, 'residential_land', 'predicted_price', show_current_dot=False))
        figs.append(generate_feature_plot(df, 'avg_rooms', 'predicted_price', show_current_dot=False))
        figs.append(generate_feature_plot(df, 'crime_rate', 'predicted_price', show_current_dot=False))

        graphs_html = [fig.to_html(full_html=False) for fig in figs]

        return render_template("previous_predictions.html",
                               predictions=data,
                               timestamp="previous",
                               graphs=graphs_html)

    except Exception as e:
        return f"Error showing previous predictions: {e}"


@app.route('/debug_predictions')
def debug_predictions():
    predictions = Prediction.query.all()
    output = []
    for p in predictions:
        output.append(f"ID: {p.id}, UserID: {p.user_id}, Price: ₹{p.price_in_inr}")
    return "<br>".join(output)

#  Logout route
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))



if __name__ == "__main__":
    app.run()


