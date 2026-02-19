import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import joblib

# Step 1: Load the dataset
df = pd.read_csv("new_data.csv",sep = "\t")
print("Available columns:", df.columns.tolist())
df.columns = df.columns.str.strip()  # Removes extra spaces before/after column names


# Step 2: Clean column names (remove extra spaces)
df.columns = df.columns.str.strip()

# Step 3: Rename the target column to make it easy to work with
df.rename(columns={"Predicted Price (in lakhs)": "PRICE"}, inplace=True)

# Step 4: Convert categorical columns to numeric
df["Rivers Nearby"] = df["Rivers Nearby"].map({"Yes": 1, "No": 0})
df["Private Or Government Schools"] = df["Private Or Government Schools"].map({"Private": 1, "Government": 0})
df["Commercial or Industrial Land"] = df["Commercial or Industrial Land"].map({"Yes": 1, "No": 0})

# Step 5: Reorder and keep only relevant columns
df = df[[
    "Proportion of Residential Land (in acres)",
    "Average Number of Rooms",
    "Crime Rate",
    "Number of Offices Nearby",
    "Rivers Nearby",
    "Cafes Nearby",
    "Private Or Government Schools",
    "Number of Schools Nearby",
    "Malls Nearby",
    "Commercial or Industrial Land",
    "PRICE"
]]

# Step 6: Split data into input (X) and output (y)
X = df.drop("PRICE", axis=1)
y = df["PRICE"]

# Step 7: Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Step 8: Train the Linear Regression model
model = LinearRegression()
model.fit(X_train, y_train)

# Step 9: Show model coefficients (for your logic verification)
print("\nModel Coefficients:")
for feature, coef in zip(X.columns, model.coef_):
    print(f"{feature}: {coef:.2f}")

# Step 10: Save the trained model to a file
joblib.dump(model, "model.pkl")
print("\n✅ Model trained and saved successfully as model.pkl.")
