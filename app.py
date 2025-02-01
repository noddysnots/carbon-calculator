from flask import Flask, render_template, request, jsonify
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculator', methods=['GET', 'POST'])
def calculator():
    if request.method == 'POST':
        try:
            # Home Energy
            home_type = request.form.get('home_type')
            appliances = request.form.getlist('appliances[]')
            electricity_bill = request.form.get('electricity_bill')

            # NEW or UPDATED
            renewable_usage = request.form.get('renewable_usage')  # none, partial, mostly
            
            # Transportation
            has_vehicle = request.form.get('has_vehicle')
            vehicle_efficiency = request.form.get('vehicle_efficiency')
            public_transport = request.form.get('public_transport')
            short_flights = int(request.form.get('short_flights', 0))
            long_flights = int(request.form.get('long_flights', 0))
            # NEW or UPDATED
            carpool_freq = request.form.get('carpool_freq')  # never, sometimes, often

            # Food and Diet
            diet_type = request.form.get('diet_type')
            food_source = request.form.get('food_source')
            food_waste = request.form.get('food_waste')
            # NEW
            dine_out_frequency = request.form.get('dine_out_frequency')

            # Waste Management
            waste_bags = request.form.get('waste_bags')
            recycling = request.form.getlist('recycling[]')
            # NEW
            composting = request.form.get('composting')

            # Lifestyle
            clothing_frequency = request.form.get('clothing_frequency')
            electronics_frequency = request.form.get('electronics_frequency')
            second_hand = request.form.get('second_hand')
            # NEW
            vacation_frequency = request.form.get('vacation_frequency')

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

            # Basic emission calculations (unchanged from your code)
            home_emissions = factors['home_type'][home_type] * factors['electricity'][electricity_bill]
            transport_emissions = (
                factors['vehicle'][vehicle_efficiency] * 1000 if has_vehicle == 'yes' else 0
            ) + factors['public_transport'][public_transport]
            flight_emissions = short_flights * 500 + long_flights * 1500
            food_emissions = factors['diet'][diet_type] * factors['food_source'][food_source]
            waste_emissions = factors['waste'][waste_bags] * (0.8 if len(recycling) > 2 else 1.0)

            # Start with sum of original components
            total_emissions = home_emissions + transport_emissions + flight_emissions + food_emissions + waste_emissions

            # ============ NEW: Qualitative Adjustments ============

            # 1) renewable_usage factor
            #    If user partially or mostly uses renewable, reduce home emissions a bit
            if renewable_usage == 'partial':
                total_emissions *= 0.95  # 5% cut
            elif renewable_usage == 'mostly':
                total_emissions *= 0.90  # 10% cut

            # 2) Carpool
            #    If user carpools 'often', reduce vehicle portion
            if carpool_freq == 'sometimes':
                total_emissions *= 0.98
            elif carpool_freq == 'often':
                total_emissions *= 0.95

            # 3) Dine out frequency
            #    More dining out can raise footprint (food delivery packaging, restaurant overhead)
            #    This is just an example multiplier
            if dine_out_frequency == 'moderate':
                total_emissions *= 1.03  # small increase
            elif dine_out_frequency == 'frequent':
                total_emissions *= 1.06  # bigger increase

            # 4) Composting
            #    If user composts 'yes', reduce waste portion
            if composting == 'sometimes':
                total_emissions *= 0.98
            elif composting == 'yes':
                total_emissions *= 0.95

            # 5) Vacation frequency
            #    If user travels frequently for leisure, add small multiplier
            if vacation_frequency == 'couple_year':
                total_emissions *= 1.02
            elif vacation_frequency == 'frequent':
                total_emissions *= 1.05

            # ========== OPTIONAL: Weighted clothing & electronics usage ==========

            # If user buys clothes weekly => bigger footprint
            if clothing_frequency == 'monthly':
                total_emissions *= 1.02
            elif clothing_frequency == 'weekly':
                total_emissions *= 1.05

            if electronics_frequency == 'moderate':
                total_emissions *= 1.02
            elif electronics_frequency == 'frequent':
                total_emissions *= 1.05

            # If user mostly buys second-hand => slight reduction
            if second_hand == 'mostly':
                total_emissions *= 0.95
            elif second_hand == 'sometimes':
                total_emissions *= 0.98

            # Round final
            total_emissions = round(total_emissions, 2)

            return render_template('results.html', data={
                'total_emissions': total_emissions,
                'breakdown': {
                    'Home': round(home_emissions, 2),
                    'Transport': round(transport_emissions, 2),
                    'Flights': round(flight_emissions, 2),
                    'Food': round(food_emissions, 2),
                    'Waste': round(waste_emissions, 2)
                },
                # OPTIONAL: show user some extra message
                'qualitative': {
                    'renewable_usage': renewable_usage,
                    'carpool_freq': carpool_freq,
                    'dine_out_frequency': dine_out_frequency,
                    'composting': composting,
                    'vacation_frequency': vacation_frequency
                }
            })
        except Exception as e:
            return render_template('calculator.html', error=str(e))

    return render_template('calculator.html')