import os
import sys
import math
import re
import uuid
import json
import torch
from flask import Flask, render_template, request, jsonify, session
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "your-secret-key"

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
# 2) Chatbot Setup
# ---------------------
try:
    # Initialize DialoGPT model (for general conversation)
    chat_model = pipeline(
        "text-generation",
        model="microsoft/DialoGPT-small",
        device=0 if torch.cuda.is_available() else -1
    )
    print("Successfully loaded DialoGPT-small model")
except Exception as e:
    print(f"Error loading DialoGPT model: {e}", file=sys.stderr)
    chat_model = None

try:
    # Initialize DeepSeek-R1 model (for carbon footprint queries)
    carbon_model = pipeline(
        "text-generation",
        model="DeepSeek-R1",
        device=0 if torch.cuda.is_available() else -1
    )
    print("Successfully loaded DeepSeek-R1 model")
except Exception as e:
    print(f"Error loading DeepSeek-R1 model: {e}", file=sys.stderr)
    carbon_model = None

USER_SESSIONS = {}

def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]

def parse_and_calculate_carbon(user_text: str) -> str:
    """
    A simple parser that only detects driving statements.
    For example: "drive my car for 10 km" -> returns an approximate CO₂ emission.
    """
    text = user_text.lower()

    # Example: "drive ... 10 km"
    car_match = re.search(r"drive\s.*?(\d+)\s?(km|kilometers?)", text)
    if car_match:
        dist = float(car_match.group(1))
        co2 = dist * 0.2  # approximately 0.2 kg CO₂ per km
        return f"Driving {dist} km emits about {co2:.2f} kg CO₂e."
    
    # (Additional regex patterns for other carbon-related activities can be added here.)

    return ""

def is_carbon_query(text: str) -> bool:
    """
    Check if the user's text likely relates to a carbon footprint query.
    """
    keywords = ["drive", "car", "km", "emission", "carbon", "footprint", "meat", "charger", "phone", "battery", "consumption"]
    return any(keyword in text.lower() for keyword in keywords)

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "POST":
        user_message = request.form.get("message", "").strip()
        session_id = get_session_id()
        
        if session_id not in USER_SESSIONS:
            USER_SESSIONS[session_id] = {
                "carbon_total": 0.0,
                "conversation_history": []
            }

        # First, try our simple parser (e.g. for driving statements)
        carbon_reply = parse_and_calculate_carbon(user_message)
        if carbon_reply:
            return jsonify({"response": carbon_reply})

        # If the query appears related to carbon issues and the carbon model is available, use it.
        if is_carbon_query(user_message) and carbon_model is not None:
            try:
                prompt = "Calculate the carbon footprint based on the following information: " + user_message
                generated = carbon_model(
                    prompt,
                    max_length=150,
                    num_return_sequences=1,
                    temperature=0.7,
                    pad_token_id=carbon_model.tokenizer.eos_token_id,
                    do_sample=True,
                    top_k=50,
                    top_p=0.95
                )
                reply = generated[0]["generated_text"]
                # Remove the prompt from the response if present
                if reply.startswith(prompt):
                    reply = reply[len(prompt):].strip()
                USER_SESSIONS[session_id]["conversation_history"].append({
                    "user": user_message,
                    "bot": reply
                })
                return jsonify({"response": reply})
            except Exception as e:
                print(f"Error generating carbon response: {e}", file=sys.stderr)
                # If something goes wrong with the carbon model, fall back to DialoGPT.
                pass

        # Fallback: use DialoGPT for general conversation.
        if chat_model is None:
            return jsonify({"response": "Chat model is currently unavailable. Please try again later."})
        try:
            generated = chat_model(
                user_message,
                max_length=100,
                num_return_sequences=1,
                temperature=0.9,
                pad_token_id=chat_model.tokenizer.eos_token_id,
                do_sample=True,
                top_k=50,
                top_p=0.95
            )
            reply = generated[0]["generated_text"]
            if reply.startswith(user_message):
                reply = reply[len(user_message):].strip()
            USER_SESSIONS[session_id]["conversation_history"].append({
                "user": user_message,
                "bot": reply
            })
            return jsonify({"response": reply})
        except Exception as e:
            print(f"Error generating response: {e}", file=sys.stderr)
            return jsonify({"response": "I apologize, but I'm having trouble processing your request. Please try again."})

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
