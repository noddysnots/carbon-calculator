import math
import re
import uuid
import json
import torch

from flask import Flask, render_template, request, jsonify, session
from transformers import pipeline, Conversation

app = Flask(__name__)
app.secret_key = "your-secret-key"

# -----------------------------------------------
# 1) Optional: Hugging Face Chatbot Setup
# -----------------------------------------------
# If you want to keep your AI chat. Otherwise, remove these lines.
chat_model = pipeline(
    "conversational",
    model="microsoft/DialoGPT-medium",
    device=0 if torch.cuda.is_available() else -1
)

USER_SESSIONS = {}

def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]

def parse_and_calculate_carbon(user_text: str) -> str:
    """Simple parser for user statements about driving/eating/charging."""
    text = user_text.lower()
    # Example regex-based extraction
    car_match = re.search(r"drive\s.*?(\d+)\s?(km|kilometers?)", text)
    if car_match:
        distance = float(car_match.group(1))
        emission = distance * 0.2  # ~0.2 kg CO2 per km
        return f"Driving {distance} km emits about {emission:.2f} kg CO₂e."
    # etc. for chicken, phone charging...
    return ""

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "POST":
        user_message = request.form.get("message", "").strip()
        session_id = get_session_id()

        if session_id not in USER_SESSIONS:
            USER_SESSIONS[session_id] = {"carbon_total": 0.0}

        # Attempt parse
        carbon_reply = parse_and_calculate_carbon(user_message)
        if carbon_reply:
            return jsonify({"response": carbon_reply})

        # Otherwise, fallback to DialoGPT or your custom dictionary
        conv = Conversation(user_message)
        response_model = chat_model(conv)
        if response_model and response_model.generated_responses:
            final_reply = response_model.generated_responses[-1]
        else:
            final_reply = "I'm not sure how to respond."
        return jsonify({"response": final_reply})

    # If GET
    return render_template("chat.html")


# -----------------------------------------------
# 2) Main Pages
# -----------------------------------------------

@app.route("/")
def index():
    """Renders your main index.html with 3D Earth, news ticker, etc."""
    return render_template("index.html")


@app.route("/scope_emissions")
def scope_emissions():
    return render_template("scope_emissions.html")


@app.route("/current_scenario")
def current_scenario():
    return render_template("current_scenario.html")


# -----------------------------------------------
# 3) Calculator Route
# -----------------------------------------------
@app.route("/calculator", methods=["GET", "POST"])
def calculator():
    if request.method == "POST":
        try:
            # 1) Gather form data (both quantitative & qualitative)
            home_type = request.form.get('home_type')
            electricity_bill = request.form.get('electricity_bill')
            renewable_usage = request.form.get('renewable_usage')  # none, partial, mostly
            appliances = request.form.getlist('appliances[]')

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

            # 2) Our base factor dictionaries
            factors = {
                'home_type': {
                    'apartment_small': 0.7,
                    'apartment_large': 1.0,
                    'house_small': 1.2,
                    'house_medium': 1.5,
                    'house_large': 2.0
                },
                'electricity': {
                    'low': 1200,
                    'medium': 3600,
                    'high': 7200,
                    'very_high': 12000
                },
                'vehicle': {
                    'very_efficient': 0.5,
                    'efficient': 0.7,
                    'average': 1.0,
                    'inefficient': 1.3
                },
                'public_transport': {
                    'never': 0,
                    'occasionally': 200,
                    'regularly': 500,
                    'daily': 1000
                },
                'diet': {
                    'vegan': 1000,
                    'vegetarian': 1500,
                    'pescatarian': 1700,
                    'omnivore': 2500,
                    'high_meat': 3500
                },
                'food_source': {
                    'mostly_local': 0.8,
                    'mixed': 1.0,
                    'mostly_imported': 1.2
                },
                'waste': {
                    'minimal': 100,
                    'low': 200,
                    'medium': 400,
                    'high': 800
                }
            }

            # 3) Calculate base emissions
            home_emissions = factors['home_type'][home_type] * factors['electricity'][electricity_bill]

            if has_vehicle == 'yes':
                vehicle_emissions = factors['vehicle'][vehicle_efficiency] * 1000
            else:
                vehicle_emissions = 0

            transport_emissions = vehicle_emissions + factors['public_transport'][public_transport]
            flight_emissions = short_flights * 500 + long_flights * 1500
            food_emissions = factors['diet'][diet_type] * factors['food_source'][food_source]

            base_waste = factors['waste'][waste_bags]
            # small bonus if user recycles more
            if len(recycling) > 2:
                base_waste *= 0.8
            waste_emissions = base_waste

            total_emissions = home_emissions + transport_emissions + flight_emissions + food_emissions + waste_emissions

            # 4) Apply multipliers from qualitative fields
            # renewable_usage
            if renewable_usage == 'partial':
                total_emissions *= 0.95
            elif renewable_usage == 'mostly':
                total_emissions *= 0.90

            # carpool
            if carpool_freq == 'sometimes':
                total_emissions *= 0.98
            elif carpool_freq == 'often':
                total_emissions *= 0.95

            # dine_out_frequency
            if dine_out_frequency == 'moderate':
                total_emissions *= 1.03
            elif dine_out_frequency == 'frequent':
                total_emissions *= 1.06

            # composting
            if composting == 'sometimes':
                total_emissions *= 0.98
            elif composting == 'yes':
                total_emissions *= 0.95

            # vacation_frequency
            if vacation_frequency == 'couple_year':
                total_emissions *= 1.02
            elif vacation_frequency == 'frequent':
                total_emissions *= 1.05

            # clothing_frequency
            if clothing_frequency == 'monthly':
                total_emissions *= 1.02
            elif clothing_frequency == 'weekly':
                total_emissions *= 1.05

            # electronics_frequency
            if electronics_frequency == 'moderate':
                total_emissions *= 1.02
            elif electronics_frequency == 'frequent':
                total_emissions *= 1.05

            # second_hand
            if second_hand == 'mostly':
                total_emissions *= 0.95
            elif second_hand == 'sometimes':
                total_emissions *= 0.98

            # round final
            total_emissions = round(total_emissions, 2)

            # 5) Trees needed => per day
            # Assume total_emissions is "kg CO2 per year"
            # Each tree ~ 20 kg CO2/year
            # => trees_needed_year = total_emissions/20
            # => trees_needed_day = (trees_needed_year/365)
            trees_needed_year = total_emissions / 20.0
            trees_needed_day = round(trees_needed_year / 365.0, 2)

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
    else:
        return render_template("calculator.html")


# If you want a separate /results route for direct test, you can define:
# @app.route("/results")
# def results_example():
#     # Example dummy data
#     data = {
#         'total_emissions': 8000.0,
#         'trees_needed_day': 1.10,
#         'breakdown': {
#             'Home': 2000,
#             'Transport': 2500,
#             'Flights': 1500,
#             'Food': 1200,
#             'Waste': 800
#         }
#     }
#     return render_template("results.html", data=data)


if __name__ == "__main__":
    app.run(debug=True)
