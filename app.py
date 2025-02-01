import os
import re
import torch
import uuid
import json

from transformers import pipeline, Conversation
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
app.secret_key = "your-secret-key"  # For session usage

# Force caching in /tmp in case the environment variable isn't set outside
os.environ["TRANSFORMERS_CACHE"] = "/tmp"

# =====================
# 1) Load Hugging Face model for fallback
chat_model = pipeline(
    "conversational",
    model="microsoft/DialoGPT-medium",
    device=0 if torch.cuda.is_available() else -1,
    cache_dir="/tmp"  # Also specify explicitly
)

# 2) Basic emission factors (demo)
EMISSION_FACTORS = {
    "car": 0.2,         # ~kg CO2/km
    "chicken": 6.9,     # ~kg CO2/kg
    "beef": 27.0,
    "phone_charge": 0.00003  # kg CO2 per Wh
}

def get_equivalent(co2_amount):
    """
    Returns a small message comparing the CO2 amount to some everyday activity.
    """
    phone_charge_co2 = 0.005  # Example: 1 phone charge might be ~0.005 kg CO2
    phone_charges = co2_amount / phone_charge_co2
    if phone_charges < 1:
        return ""
    return f"That's like charging a smartphone ~{int(phone_charges)} times!"

def parse_and_calculate_carbon(user_text: str) -> str:
    text = user_text.lower()

    # 1) Example: "I drive my car for 10 km"
    car_match = re.search(r"drive\s.*?(\d+)\s?(km|kilometers?)", text)
    if car_match:
        distance = float(car_match.group(1))
        emission = distance * EMISSION_FACTORS["car"]
        eq_msg = get_equivalent(emission)
        return f"Driving {distance} km emits about {emission:.2f} kg CO₂e. {eq_msg}"

    # 2) "I eat 300 g of chicken"
    food_match = re.search(r"eat\s.*?(\d+)\s?g\s(of\s)?(chicken|beef)", text)
    if food_match:
        grams = float(food_match.group(1))
        meat_type = food_match.group(3)  # chicken or beef
        kg = grams / 1000.0
        emission = kg * EMISSION_FACTORS[meat_type]
        eq_msg = get_equivalent(emission)
        return f"Eating {grams} g of {meat_type} ~ {emission:.2f} kg CO₂e. {eq_msg}"

    # 3) "charge my phone with a 40 watt charger for 2 hours"
    phone_match = re.search(r"(\d+)\s?watt.*?(\d+)\s?hour", text)
    if phone_match:
        watts = float(phone_match.group(1))
        hours = float(phone_match.group(2))
        wh = watts * hours
        co2 = wh * EMISSION_FACTORS["phone_charge"]
        eq_msg = get_equivalent(co2)
        return (
            f"Charging a {watts:.0f}-watt phone charger for {hours:.0f} hour(s) "
            f"emits about {co2:.4f} kg CO₂e. {eq_msg}"
        )

    return ""

# For session-based multi-turn
USER_SESSIONS = {}

def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]

FLOW_STEPS = [
    "1. Do you drive a car? If so, about how many km daily?",
    "2. How about your diet? Do you eat meat? If yes, about how many grams daily?",
    "3. Do you often charge large devices or have other big energy usage?",
    "That's all for now! Type 'done' to see your total."
]

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

# Calculator route
@app.route('/calculator', methods=['GET', 'POST'])
def calculator():
    if request.method == 'POST':
        try:
            # Home Energy
            home_type = request.form.get('home_type')
            appliances = request.form.getlist('appliances[]')
            electricity_bill = request.form.get('electricity_bill')
            
            # Transportation
            has_vehicle = request.form.get('has_vehicle')
            vehicle_efficiency = request.form.get('vehicle_efficiency')
            public_transport = request.form.get('public_transport')
            short_flights = int(request.form.get('short_flights', 0))
            long_flights = int(request.form.get('long_flights', 0))
            
            # Food and Diet
            diet_type = request.form.get('diet_type')
            food_source = request.form.get('food_source')
            food_waste = request.form.get('food_waste')
            
            # Waste Management
            waste_bags = request.form.get('waste_bags')
            recycling = request.form.getlist('recycling[]')
            
            # Lifestyle
            clothing_frequency = request.form.get('clothing_frequency')
            electronics_frequency = request.form.get('electronics_frequency')
            second_hand = request.form.get('second_hand')

            # Calculation factors
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
                'appliances': {
                    'ac': 1000,
                    'heating': 800,
                    'dishwasher': 300,
                    'dryer': 400
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

            # Calculate emissions
            home_emissions = factors['home_type'][home_type] * factors['electricity'][electricity_bill]
            transport_emissions = (
                factors['vehicle'][vehicle_efficiency] * 1000 if has_vehicle == 'yes' else 0
            ) + factors['public_transport'][public_transport]
            flight_emissions = short_flights * 500 + long_flights * 1500
            food_emissions = factors['diet'][diet_type] * factors['food_source'][food_source]
            waste_emissions = factors['waste'][waste_bags] * (0.8 if len(recycling) > 2 else 1.0)

            total_emissions = (
                home_emissions +
                transport_emissions +
                flight_emissions +
                food_emissions +
                waste_emissions
            )

            return render_template('results.html', data={
                'total_emissions': round(total_emissions, 2),
                'breakdown': {
                    'Home': round(home_emissions, 2),
                    'Transport': round(transport_emissions, 2),
                    'Flights': round(flight_emissions, 2),
                    'Food': round(food_emissions, 2),
                    'Waste': round(waste_emissions, 2)
                }
            })

        except Exception as e:
            return render_template('calculator.html', error=str(e))

    return render_template('calculator.html')

@app.route('/scope_emissions')
def scope_emissions():
    return render_template('scope_emissions.html')

@app.route('/current_scenario')
def current_scenario():
    return render_template('current_scenario.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        user_message = request.form.get('message', '').strip()
        session_id = get_session_id()

        if session_id not in USER_SESSIONS:
            USER_SESSIONS[session_id] = {
                "flow_step": 0,
                "carbon_total": 0.0
            }

        user_data = USER_SESSIONS[session_id]
        flow_index = user_data["flow_step"]
        carbon_sum = user_data["carbon_total"]

        # 1) Attempt direct parse
        carbon_reply = parse_and_calculate_carbon(user_message)
        if carbon_reply:
            match_em = re.search(r"([\d\.]+)\s?kg CO₂e", carbon_reply)
            if match_em:
                amount = float(match_em.group(1))
                user_data["carbon_total"] = carbon_sum + amount
            return jsonify({"response": f"{carbon_reply}\nRunning total: ~{user_data['carbon_total']:.2f} kg CO₂e."})

        # 2) Multi-turn flow
        if user_message.lower() == "start" and flow_index == 0:
            user_data["flow_step"] = 1
            return jsonify({"response": "Let's begin your carbon check. " + FLOW_STEPS[0]})
        elif user_message.lower() == "done":
            total_reply = f"Your total so far is {carbon_sum:.2f} kg CO₂e."
            if carbon_sum > 50:
                total_reply += " That's quite high! Consider reducing meat or driving less to offset."
            else:
                total_reply += " You're doing fairly well. Keep it up!"
            return jsonify({"response": total_reply})

        if 1 <= flow_index < len(FLOW_STEPS):
            user_data["flow_step"] += 1
            next_step = user_data["flow_step"]
            if next_step <= len(FLOW_STEPS):
                return jsonify({"response": FLOW_STEPS[next_step - 1]})

        # 3) Dictionary-based
        responses = {
            'carbon footprint': 'A carbon footprint is the total amount of greenhouse gases emitted.',
            'reduce': 'You can reduce your footprint by using energy-efficient appliances, reducing meat consumption, using public transport, and recycling.',
            'calculate': 'Our calculator helps estimate your emissions based on your lifestyle.',
            'scope': 'Scope 1 (direct), Scope 2 (indirect energy), and Scope 3 (other indirect) emissions.',
            'help': 'I can explain carbon footprints, emission scopes, or guide you through calculations.',
            'diet': 'Diet impacts emissions through food production, transport, and waste.',
            'transport': 'Transportation emissions come from vehicles, public transit, and flights.',
            'energy': 'Home energy use includes electricity, heating, and appliances.'
        }
        user_msg_lower = user_message.lower()
        for key, val in responses.items():
            if key in user_msg_lower:
                return jsonify({"response": val})

        # 4) Fallback to Hugging Face model
        conv = Conversation(user_message)
        response_model = chat_model(conv)
        if response_model and response_model.generated_responses:
            final_reply = response_model.generated_responses[-1]
        else:
            final_reply = "I'm not sure how to respond."
        return jsonify({"response": final_reply})

    return render_template('chat.html')


if __name__ == '__main__':
    app.run(debug=True)
