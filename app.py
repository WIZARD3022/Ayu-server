from flask import Flask, render_template, request, redirect
import json
import os
import requests
import pandas as pd
import plotly
import plotly.express as px
import io
from io import BytesIO 

app = Flask(__name__)

DATA_FILE = "data.json"
DETAIL_FILE = "detail.json"

# Load/Save functions
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Load dosha details
def load_dosha_details():
    with open(DETAIL_FILE, "r") as f:
        return json.load(f)

# Fetch CSV data from server
def fetch_csv_data(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(BytesIO(r.content), engine="python")
    return df

# Determine dosha from Pulse rate and Temp
def determine_dosha(pulse, temp):
    pulse = float(pulse)
    temp = float(temp)
    dosha = "Healthy"
    if pulse > 80 and temp < 98.4:
        dosha = "Vat"
    elif pulse > 80 and 98.6 <= temp <= 99:
        dosha = "Vat-Pitta"
    elif 70 <= pulse <= 80 and temp > 99:
        dosha = "Pitta"
    elif 70 <= pulse <= 80 and temp < 98:
        dosha = "Pitta-Kapha"
    elif pulse < 70 and temp < 98:
        dosha = "Kapha"
    elif pulse > 80 and temp < 95:
        dosha = "Kapha-Vat"
    return dosha

# Questions
questions = [
    { "q": "Body frame", "a": "Thin, underweight (A)", "b": "Medium, muscular (B)", "c": "Broad, well-built (C)" },
    { "q": "Skin texture", "a": "Dry, rough, cool (A)", "b": "Soft, warm, may flush easily (B)", "c": "Oily, smooth, thick (C)" },
    { "q": "Hair type", "a": "Dry, coarse, breaks easily (A)", "b": "Fine, soft, early greying (B)", "c": "Thick, oily, slow greying (C)" },
    { "q": "Facial features", "a": "Irregular, small (A)", "b": "Sharp, chiseled (B)", "c": "Rounded, large (C)" },
    { "q": "Eyes", "a": "Small, dry (A)", "b": "Medium, reddish (B)", "c": "Large, calm (C)" },
    { "q": "Nails", "a": "Brittle (A)", "b": "Pinkish (B)", "c": "Strong, thick (C)" },
    { "q": "Voice", "a": "Thin, shaky (A)", "b": "Sharp (B)", "c": "Deep, slow (C)" },
    { "q": "Appetite", "a": "Irregular (A)", "b": "Strong (B)", "c": "Steady (C)" },
    { "q": "Thirst", "a": "Low (A)", "b": "High (B)", "c": "Moderate (C)" },
    { "q": "Digestion", "a": "Irregular (A)", "b": "Strong (B)", "c": "Slow (C)" },
    { "q": "Bowels", "a": "Dry stools (A)", "b": "Loose stools (B)", "c": "Regular (C)" },
    { "q": "Sleep", "a": "Light (A)", "b": "Moderate (B)", "c": "Deep (C)" },
    { "q": "Sweating", "a": "Minimal (A)", "b": "Excessive (B)", "c": "Moderate (C)" },
    { "q": "Menstrual flow", "a": "Scanty (A)", "b": "Moderate (B)", "c": "Heavy (C)" },
    { "q": "Sexual drive", "a": "Fluctuating (A)", "b": "Strong (B)", "c": "Slow (C)" },
    { "q": "Memory", "a": "Quick learner (A)", "b": "Sharp (B)", "c": "Slow learner (C)" },
    { "q": "Thinking", "a": "Creative (A)", "b": "Logical (B)", "c": "Methodical (C)" },
    { "q": "Temperament", "a": "Anxious (A)", "b": "Angry (B)", "c": "Calm (C)" },
    { "q": "Speech", "a": "Fast (A)", "b": "Precise (B)", "c": "Slow (C)" },
    { "q": "Decision-making", "a": "Indecisive (A)", "b": "Fast (B)", "c": "Thoughtful (C)" },
    { "q": "Stress response", "a": "Nervous (A)", "b": "Irritable (B)", "c": "Withdrawn (C)" },
    { "q": "Season reaction", "a": "Dislikes cold (A)", "b": "Dislikes heat (B)", "c": "Dislikes damp (C)" },
    { "q": "Habits", "a": "Irregular (A)", "b": "Organized (B)", "c": "Routine (C)" },
    { "q": "Social nature", "a": "Talkative (A)", "b": "Dominating (B)", "c": "Friendly (C)" },
    { "q": "Dreams", "a": "Flying (A)", "b": "Fire/competition (B)", "c": "Water/nature (C)" }
]

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/create")
def create_user():
    return render_template("create_user.html", questions=questions)

@app.route("/save", methods=["POST"])
def save():
    data = load_data()

    new_entry = {
        "name": request.form["name"],
        "age": request.form["age"],
        "gender": request.form["gender"],
        "mobile": request.form["mobile"],
        "answers": [request.form.get(f"q{i}") for i in range(1, 26)]
    }

    data.append(new_entry)
    save_data(data)

    return redirect("/records")

@app.route("/records")
def records():
    data = load_data()
    return render_template("records.html", data=data)

# --- New: Fetch CSV and show interactive plots ---
CSV_URL = "http://72.60.223.62:5000/download"

def fetch_csv_data(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    return df

def guess_numeric_columns(df):
    numeric_cols = []
    for col in df.columns:
        try:
            coerced = pd.to_numeric(df[col], errors="coerce")
            if coerced.notna().any():
                df[col] = coerced
                numeric_cols.append(col)
        except:
            continue
    return numeric_cols, df

@app.route("/data_json")
def data_json():
    try:
        df = fetch_csv_data(CSV_URL)
        numeric_cols, df = guess_numeric_columns(df)
        if not numeric_cols:
            return "No numeric sensor data found."

        # create interactive Plotly figures for all numeric columns
        graphs = []
        for col in numeric_cols:
            fig = px.line(df, y=col, title=f"Sensor: {col}")
            graphs.append(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

        return render_template("data_json.html", graphs=graphs)
    except Exception as e:
        return f"Error fetching or parsing CSV: {e}"

@app.route("/predict")
def data_predict():
    try:
        df = fetch_csv_data(CSV_URL)

        if df.empty:
            return "CSV is empty."

        # Take last row
        last_row = df.iloc[-1]
        row_data = last_row.to_dict()  # convert to dict

        # Extract sensor values
        ir1 = float(row_data.get("ir1", 0))
        ir2 = float(row_data.get("ir2", 0))
        ir3 = float(row_data.get("ir3", 0))
        pulse = (ir1 + ir2 + ir3) / 3
        temp = float(row_data.get("temperature", 0))  # remove extra apostrophe

        # Determine Dosha
        dosha = determine_dosha(pulse, temp)
        row_data["Dosha"] = dosha

        # Load dosha details
        dosha_details = load_dosha_details().get(dosha, {})

        return render_template("predict.html",
                               row_data=row_data,
                               dosha_details=dosha_details)

    except Exception as e:
        return f"Error fetching or parsing CSV: {e}"


if __name__ == "__main__":
    app.run(debug=True)

