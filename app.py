from flask import Flask, render_template, request, jsonify
import json

app = Flask(__name__)

# Home route
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
                'home_type': {'apartment_small': 0.7, 'apartment_large': 1.0, 'house_small': 1.2, 
                             'house_medium': 1.5, 'house_large': 2.0},
                'electricity': {'low': 1200, 'medium': 3600, 'high': 7200, 'very_high': 12000},
                'appliances': {'ac': 1000, 'heating': 800, 'dishwasher': 300, 'dryer': 400},
                'vehicle': {'very_efficient': 0.5, 'efficient': 0.7, 'average': 1.0, 'inefficient': 1.3},
                'public_transport': {'never': 0, 'occasionally': 200, 'regularly': 500, 'daily': 1000},
                'diet': {'vegan': 1000, 'vegetarian': 1500, 'pescatarian': 1700, 
                        'omnivore': 2500, 'high_meat': 3500},
                'food_source': {'mostly_local': 0.8, 'mixed': 1.0, 'mostly_imported': 1.2},
                'waste': {'minimal': 100, 'low': 200, 'medium': 400, 'high': 800}
            }

            # Calculate emissions
            home_emissions = factors['home_type'][home_type] * factors['electricity'][electricity_bill]
            transport_emissions = (factors['vehicle'][vehicle_efficiency] * 1000 if has_vehicle == 'yes' else 0) + \
                                factors['public_transport'][public_transport]
            flight_emissions = short_flights * 500 + long_flights * 1500
            food_emissions = factors['diet'][diet_type] * factors['food_source'][food_source]
            waste_emissions = factors['waste'][waste_bags] * (0.8 if len(recycling) > 2 else 1.0)

            total_emissions = home_emissions + transport_emissions + flight_emissions + \
                            food_emissions + waste_emissions

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

# Other routes
@app.route('/scope_emissions')
def scope_emissions():
    return render_template('scope_emissions.html')

@app.route('/current_scenario')
def current_scenario():
    return render_template('current_scenario.html')

# Chatbot routes
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        user_message = request.form.get('message', '').lower()
        response = get_chatbot_response(user_message)
        return jsonify(response)
    return render_template('chat.html')

def get_chatbot_response(message):
    responses = {
        'carbon footprint': 'A carbon footprint is the total amount of greenhouse gases emitted.',
        'reduce': 'You can reduce your footprint by: using energy-efficient appliances, reducing meat consumption, using public transport, and recycling.',
        'calculate': 'Our calculator helps estimate your emissions based on your lifestyle.',
        'scope': 'Scope 1 (direct), Scope 2 (indirect energy), and Scope 3 (other indirect) emissions.',
        'help': 'I can explain carbon footprints, emission scopes, or guide you through calculations.',
        'diet': 'Diet impacts emissions through food production, transport, and waste.',
        'transport': 'Transportation emissions come from vehicles, public transit, and flights.',
        'energy': 'Home energy use includes electricity, heating, and appliances.'
    }
    
    for key, value in responses.items():
        if key in message:
            return {'response': value}
    return {'response': 'How can I help you understand carbon footprints?'}

if __name__ == '__main__':
    app.run(debug=True)