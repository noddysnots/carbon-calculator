import os
from flask import Flask, render_template, request, jsonify
import math

app = Flask(__name__)

@app.route('/')
def home():
    """Main page with 3D Earth, news ticker, etc."""
    return render_template('index.html')

@app.route('/calculator', methods=['GET', 'POST'])
def calculator():
    if request.method == 'POST':
        try:
            # 1) Gather form data
            home_type = request.form.get('home_type')
            electricity_bill = request.form.get('electricity_bill')
            renewable_usage = request.form.get('renewable_usage')  # new
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

            # 3) Calculate base factors
            home_emissions = factors['home_type'][home_type] * factors['electricity'][electricity_bill]

            if has_vehicle == 'yes':
                vehicle_emissions = factors['vehicle'][vehicle_efficiency] * 1000
            else:
                vehicle_emissions = 0

            transport_emissions = vehicle_emissions + factors['public_transport'][public_transport]
            flight_emissions = (short_flights * 500) + (long_flights * 1500)
            food_emissions = factors['diet'][diet_type] * factors['food_source'][food_source]

            base_waste = factors['waste'][waste_bags]
            # If user recycles > 2 items, reduce waste a bit
            if len(recycling) > 2:
                base_waste *= 0.8
            waste_emissions = base_waste

            # Sum initial
            total_emissions = home_emissions + transport_emissions + flight_emissions + food_emissions + waste_emissions

            # 4) Additional multipliers from qualitative fields

            # (a) renewable_usage (slightly reduce home emissions if partial or mostly renewable)
            if renewable_usage == 'partial':
                total_emissions *= 0.95
            elif renewable_usage == 'mostly':
                total_emissions *= 0.90

            # (b) carpool
            if carpool_freq == 'sometimes':
                total_emissions *= 0.98
            elif carpool_freq == 'often':
                total_emissions *= 0.95

            # (c) dine_out_frequency
            if dine_out_frequency == 'moderate':
                total_emissions *= 1.03
            elif dine_out_frequency == 'frequent':
                total_emissions *= 1.06

            # (d) composting
            if composting == 'sometimes':
                total_emissions *= 0.98
            elif composting == 'yes':
                total_emissions *= 0.95

            # (e) vacation_frequency
            if vacation_frequency == 'couple_year':
                total_emissions *= 1.02
            elif vacation_frequency == 'frequent':
                total_emissions *= 1.05

            # (f) clothing_frequency
            if clothing_frequency == 'monthly':
                total_emissions *= 1.02
            elif clothing_frequency == 'weekly':
                total_emissions *= 1.05

            # (g) electronics_frequency
            if electronics_frequency == 'moderate':
                total_emissions *= 1.02
            elif electronics_frequency == 'frequent':
                total_emissions *= 1.05

            # (h) second_hand
            if second_hand == 'mostly':
                total_emissions *= 0.95
            elif second_hand == 'sometimes':
                total_emissions *= 0.98

            # Round
            total_emissions = round(total_emissions, 2)

            # 5) Trees needed calculation
            # Assume ~20 kg CO2/year per tree absorption (very rough)
            # If total_emissions is representing a yearly footprint in kg,
            # we can do:
            trees_per_year = 20.0
            if total_emissions <= 0:
                trees_needed = 0
            else:
                trees_needed = math.ceil(total_emissions / trees_per_year)

            # Decide emission level for color-coding
            # For example, <5000 is "low", <10000 is "med", else "high"
            if total_emissions < 5000:
                level = "low"
            elif total_emissions < 10000:
                level = "medium"
            else:
                level = "high"

            # Pass everything to results template
            return render_template('results.html', data={
                'total_emissions': total_emissions,
                'trees_needed': trees_needed,
                'emission_level': level,
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
    else:
        return render_template('calculator.html')

@app.route('/results')
def results_dummy():
    """If someone directly hits /results. Not usually used, but a fallback."""
    return render_template('results.html')

# OPTIONAL: A route for "news" data
@app.route('/news')
def get_news():
    """
    This is just a placeholder returning static JSON.
    In real usage, you'd fetch from a real API or your DB.
    """
    dummy_news = [
        {"title": "New Climate Report Released", "link": "#"},
        {"title": "Global Emissions Peak in 2025, says Analysis", "link": "#"},
        {"title": "Local Community Starts Composting Initiative", "link": "#"}
    ]
    return jsonify(dummy_news)

if __name__ == "__main__":
    app.run(debug=True)