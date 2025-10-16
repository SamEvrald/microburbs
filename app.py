import os
import requests
from flask import Flask, render_template, request, jsonify


app = Flask(__name__)

# Sandbox API details
API_URL = "https://www.microburbs.com.au/report_generator/api/suburb/properties"

API_HEADERS = {
    "Authorization": "Bearer test",
    "Content-Type": "application/json"
}



def analyze_property_data(data):
    """
    Transforms raw, complex API data into a simple, investor-friendly scorecard.
    This mimics the core job requirement: turning complex data into useful insights.
    """
    print(f"DEBUG: Raw data keys: {list(data.keys())}")
    properties = data.get('results', [])
    
    print(f"DEBUG: Found {len(properties)} properties")
    
    if not properties:
        print("DEBUG: No properties found, returning None")
        return None

   
    
    # 1. Price Index (Using price field as market value)
    sale_prices = [p.get('price', 0) for p in properties if p.get('price') is not None]
    avg_price = round(sum(sale_prices) / len(sale_prices) if sale_prices else 0)

    # 2. Risk/Supply Index (Using listing age as a measure of risk/liquidity)
    # Calculate days since listing
    from datetime import datetime, date
    today = date.today()
    dom_list = []
    for p in properties:
        listing_date_str = p.get('listing_date')
        if listing_date_str:
            try:
                listing_date = datetime.strptime(listing_date_str, '%Y-%m-%d').date()
                days_on_market = (today - listing_date).days
                dom_list.append(days_on_market)
            except:
                continue
    
    avg_dom = round(sum(dom_list) / len(dom_list) if dom_list else 0)
    
   
    risk_score = max(0, min(100, 100 - (avg_dom - 20) * 1.5))
    
    # 3. Growth Potential Index (Using bedrooms from attributes as proxy for family interest/growth potential)
    bedrooms = []
    for p in properties:
        attrs = p.get('attributes', {})
        beds = attrs.get('bedrooms', 0)
        if beds and beds > 0:
            bedrooms.append(beds)
    
    avg_beds = round(sum(bedrooms) / len(bedrooms) if bedrooms else 0, 1)

    
    growth_score = max(0, min(100, (avg_beds / 4) * 100))

    # Summary Statistics for the user interface
    summary = {
        'total_listings': len(properties),
        'avg_sale_price': avg_price,
        'avg_days_on_market': avg_dom,
        'avg_bedrooms': avg_beds
    }
    
 
    scorecard = {
        'liquidity_risk': {
            'label': 'Liquidity Risk Score',
            'value': int(risk_score),
            'explanation': 'Measures how quickly properties are selling (Days on Market). Higher score means lower risk and faster sale times.'
        },
        'family_growth_potential': {
            'label': 'Family Growth Potential',
            'value': int(growth_score),
            'explanation': 'A heuristic based on average property size (bedrooms), indicating stable, long-term family demand.'
        }
    }

    return {'summary': summary, 'scorecard': scorecard, 'raw_properties': properties[:5]}



@app.route('/')
def home():
    """Renders the main single-page application."""
   
    return render_template('index.html')

@app.route('/test')
def test():
    """Test endpoint to debug"""
    return jsonify({"message": "Test endpoint working", "debug": "This is a test"})

@app.route('/api/analyze', methods=['GET'])
def analyze_suburb():
    """
    Proxies the request to the Microburbs API and analyzes the data.
    This is necessary because the frontend cannot directly access the API due to CORS.
    """
    suburb_name = request.args.get('suburb')
    
    if not suburb_name:
        return jsonify({"error": "Suburb name is required."}), 400

    try:
        # Make the request to the external API
        response = requests.get(API_URL, params={"suburb": suburb_name}, headers=API_HEADERS, timeout=10)
        response.raise_for_status()
        raw_data = response.json()
        
        # Transform the data using our custom analysis function
        analysis_result = analyze_property_data(raw_data)

        if analysis_result is None:
            return jsonify({
                "error": f"No property data found for {suburb_name}. Please try a different suburb."
            }), 404

        
        return jsonify({
            'suburb': suburb_name,
            'analysis': analysis_result
        })

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 401:
            error_message = "API Authentication Failed. Please check the Bearer token."
        elif status_code == 404:
            error_message = f"Suburb '{suburb_name}' not found or no data available."
        else:
            error_message = f"An API error occurred: HTTP {status_code}"
        return jsonify({"error": error_message}), status_code
    
    except requests.exceptions.RequestException:
        return jsonify({"error": "Could not connect to the external Microburbs API."}), 503

    except Exception as e:
        return jsonify({"error": "An unexpected server error occurred during analysis."}), 500




if __name__ == '__main__':
   
    app.run(debug=True)


