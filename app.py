import os
# Set ALL environment variables before any other imports
os.environ["TRANSFORMERS_CACHE"] = "/tmp/transformers"
os.environ["HF_HOME"] = "/tmp/hf_home"
os.environ["HF_MODULES_CACHE"] = "/tmp/hf_modules"
os.environ["XDG_CACHE_HOME"] = "/tmp/cache"

import math
import re
import uuid
import json
import torch
from flask import Flask, render_template, request, jsonify, session
from transformers import pipeline

app = Flask(__name__)
app.secret_key = "your-secret-key"

# Create cache directories explicitly
for directory in ["/tmp/transformers", "/tmp/hf_home", "/tmp/hf_modules", "/tmp/cache"]:
    os.makedirs(directory, exist_ok=True)

# ---------------------
# 1) GLOBALS
# ---------------------
VISITOR_COUNT = 0
TOTAL_SITE_FOOTPRINT = 0.0

SUSTAINABILITY_NEWS = [
    {"title": "Major breakthrough in renewable energy storage", "link": "https://example.com/renewable-breakthrough"},
    {"title": "Local community reduces waste by 40% through composting", "link": "https://example.com/local-compost"},
    {"title": "UN warns about record global temperatures this year", "link": "https://example.com/un-temperature-warning"}
]

# ---------------------
# 2) Chatbot with DeepSeek R1
# ---------------------
# Initialize the model with explicit cache directories
chat_model = pipeline(
    "text-generation",
    model="deepseek-ai/DeepSeek-R1",
    trust_remote_code=True,
    cache_dir="/tmp/transformers",
    device=0 if torch.cuda.is_available() else -1
)

USER_SESSIONS = {}

def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]

def parse_and_calculate_carbon(user_text: str) -> str:
    """
    Example parser for carbon-related statements.
    E.g., "drive car 10 km" => returns approximate CO2 emission
    """
    text = user_text.lower()

    # Example: "drive my car for 10 km"
    car_match = re.search(r"drive\s.*?(\d+)\s?(km|kilometers?)", text)
    if car_match:
        dist = float(car_match.group(1))
        co2 = dist * 0.2  # ~0.2 kg CO2 per km
        return f"Driving {dist} km emits about {co2:.2f} kg CO₂e."

    return ""

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "POST":
        user_message = request.form.get("message", "").strip()
        session_id = get_session_id()
        if session_id not in USER_SESSIONS:
            USER_SESSIONS[session_id] = {"carbon_total": 0.0}

        # Attempt parse for carbon activity
        carbon_reply = parse_and_calculate_carbon(user_message)
        if carbon_reply:
            return jsonify({"response": carbon_reply})

        # Generate response from DeepSeek R1
        generated = chat_model(user_message, max_length=100, num_return_sequences=1)
        reply = generated[0]["generated_text"]

        return jsonify({"response": reply})

    return render_template("chat.html")

# ---------------------
# 3) Sustainability News
# ---------------------
@app.route("/news")
def get_news():
    return jsonify(SUSTAINABILITY_NEWS)

# ---------------------
# 4) Main Pages
# ---------------------
@app.route("/")
def index():
    global VISITOR_COUNT
    VISITOR_COUNT += 1
    return render_template(
        "index.html",
        visitor_count=VISITOR_COUNT,
        total_site_footprint=round(TOTAL_SITE_FOOTPRINT, 2)
    )

@app.route("/scope_emissions")
def scope_emissions():
    return render_template("scope_emissions.html")

@app.route("/current_scenario")
def current_scenario():
    return render_template("current_scenario.html")

# ---------------------
# 5) Calculator Route
# ---------------------
@app.route("/calculator", methods=["GET", "POST"])
def calculator():
    if request.method == "POST":
        try:
            home_type = request.form.get('home_type')
            electricity_bill = request.form.get('electricity_bill')
            renewable_usage = request.form.get('renewable_usage')
            has_vehicle = request.form.get('has_vehicle')
            vehicle_efficiency = request.form.get('vehicle_efficiency')
            public_transport = request.form.get('public_transport')
            short_flights = int(request.form.get('short_flights', 0))
            long_flights = int(request.form.get('long_flights', 0))
            carpool_freq = request.form.get('carpool_freq')
            diet_type = request.form.get('diet_type')
            food_source = request.form.get('food_source')
            food_waste = request.form.get('food_waste')
            dine_out_frequency = request.form.get('dine_out_frequency')
            waste_bags = request.form.get('waste_bags')
            recycling = request.form.getlist('recycling[]')
            composting = request.form.get('composting')
            clothing_frequency = request.form.get('clothing_frequency')
            electronics_frequency = request.form.get('electronics_frequency')
            second_hand = request.form.get('second_hand')
            vacation_frequency = request.form.get('vacation_frequency')

            factors = {
                'home_type': {
                    'apartment_small': 0.7, 'apartment_large': 1.0,
                    'house_small': 1.2, 'house_medium': 1.5, 'house_large': 2.0
                },
                'electricity': {'low': 1200, 'medium': 3600, 'high': 7200, 'very_high': 12000},
                'vehicle': {'very_efficient': 0.5, 'efficient': 0.7, 'average': 1.0, 'inefficient': 1.3},
                'public_transport': {'never': 0, 'occasionally': 200, 'regularly': 500, 'daily': 1000},
                'diet': {'vegan': 1000, 'vegetarian': 1500, 'pescatarian': 1700, 'omnivore': 2500, 'high_meat': 3500},
                'food_source': {'mostly_local': 0.8, 'mixed': 1.0, 'mostly_imported': 1.2},
                'waste': {'minimal': 100, 'low': 200, 'medium': 400, 'high': 800}
            }

            home_emissions = factors['home_type'][home_type] * factors['electricity'][electricity_bill]
            vehicle_emissions = factors['vehicle'][vehicle_efficiency] * 1000 if has_vehicle == 'yes' else 0
            transport_emissions = vehicle_emissions + factors['public_transport'][public_transport]
            flight_emissions = short_flights * 500 + long_flights * 1500
            food_emissions = factors['diet'][diet_type] * factors['food_source'][food_source]

            w_base = factors['waste'][waste_bags]
            if len(recycling) > 2:
                w_base *= 0.8
            waste_emissions = w_base

            total_emissions = home_emissions + transport_emissions + flight_emissions + food_emissions + waste_emissions

            # Trees needed
            trees_needed_year = total_emissions / 20.0
            trees_needed_day = round(trees_needed_year / 365.0, 2)

            global TOTAL_SITE_FOOTPRINT
            TOTAL_SITE_FOOTPRINT += total_emissions

            data = {
                'total_emissions': total_emissions,
                'trees_needed_day': trees_needed_day,
                'breakdown': {
                    'Home': round(home_emissions, 2),
                    'Transport': round(transport_emissions, 2),
                    'Flights': round(flight_emissions, 2),
                    'Food': round(food_emissions, 2),
                    'Waste': round(waste_emissions, 2)
                }
            }
            return render_template("results.html", data=data)

        except Exception as e:
            return render_template("calculator.html", error=str(e))

    return render_template("calculator.html")

if __name__ == "__main__":
    app.run(debug=True)