import os
import joblib
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ai', 'models', 'solar_model.pkl')

def get_solar_prediction(temp, humidity, cloud_cover, irradiance, hour, month):
    """
    Predict expected Solar Output (kW) using the trained Random Forest model.
    Falls back to a robust physics-based estimation if model is not trained yet.
    """
    # Try loading the saved Random Forest Regressor
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            # Input features shape: [[temp, humidity, cloud_cover, irradiance, hour, month]]
            features = np.array([[temp, humidity, cloud_cover, irradiance, hour, month]], dtype=float)
            prediction = model.predict(features)[0]
            return round(float(prediction), 2)
        except Exception as e:
            print(f"Error loading AI model: {e}. Falling back to physics estimator.")
            
    # Fallback physics-based estimator
    # Peak output base capacity = 5.8 kW
    # Irradiance directly affects output (max irradiance 1000 W/m2)
    # Diurnal peak at 12 PM (normalized factor based on hour)
    hour_factor = np.sin((hour - 6) * np.pi / 12) if 6 <= hour <= 18 else 0.0
    
    # Temperature coefficient: solar panel efficiency drops by 0.4% per degree C above 25 C
    temp_coff = 1.0 - 0.004 * max(0.0, temp - 25.0)
    
    # Cloud coverage reduces irradiance and efficiency
    cloud_factor = 1.0 - 0.7 * (cloud_cover / 100.0)
    
    estimated_irradiance = irradiance if irradiance is not None else (1000.0 * hour_factor * cloud_factor)
    
    output = (estimated_irradiance / 1000.0) * 5.5 * temp_coff
    output = max(0.0, min(6.5, output))
    return round(float(output), 2)


def get_smart_recommendation(predicted_output, weather_description=None):
    """
    Generate recommendations based on predicted solar energy generation.
    """
    rec_list = []
    
    if predicted_output >= 4.5:
        rec_list.append("High Solar Production: Excellent time to run heavy appliances like washing machines, heavy load induction cookers, water heaters, and EV chargers (Recommended window: 11 AM - 3 PM).")
        rec_list.append("Consider cooling the house/running air conditioners during peak hours to maximize use of available solar power and minimize grid draw.")
    elif predicted_output >= 2.5:
        rec_list.append("Moderate Solar Production: Ideal for running light to moderate loads (laptops, refrigerators, fans, dishwashers).")
        rec_list.append("Spread out heavy appliance usage to avoid exceeding current production capacity.")
    else:
        rec_list.append("Low Solar Production: Avoid running energy-intensive heavy appliances. Rely on grid or energy storage systems.")
        rec_list.append("Turn off non-essential appliances to save battery backups or reduce electric bills.")

    if weather_description and any(keyword in weather_description.lower() for keyword in ['rain', 'cloud', 'storm', 'overcast']):
        rec_list.append("Weather alert: Cloudy/rainy weather detected. Expected low capacity. Minimize energy draw from solar panels.")
        
    return rec_list
