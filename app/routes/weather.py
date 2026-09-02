from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import WeatherData, db, ActivityLog, Alert
import requests

weather_bp = Blueprint('weather', __name__)

@weather_bp.route('/weather', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        # Trigger Weather Sync
        city = request.form.get('city', 'Karachi')
        api_key = current_app.config['OPENWEATHER_API_KEY']
        
        success = False
        humidity = 50.0
        temp = 30.0
        cloud_cover = 20.0
        wind = 12.0
        desc = "Clear weather (Simulated)"
        icon = "01d"

        # Check OpenWeather API key validity
        if api_key and api_key != 'your_openweather_api_key_here' and len(api_key.strip()) > 5:
            try:
                url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    temp = float(data['main']['temp'])
                    humidity = float(data['main']['humidity'])
                    cloud_cover = float(data['clouds']['all'])
                    wind = float(data['wind']['speed'])
                    desc = data['weather'][0]['description']
                    icon = data['weather'][0]['icon']
                    success = True
                else:
                    flash(f"OpenWeather API responded with error code {response.status_code}. Loaded cached simulation values.", 'warning')
            except Exception as e:
                flash(f"Error accessing OpenWeather API: {str(e)}. Switched to weather prediction simulator.", 'warning')
        else:
            # Simulated weather generation
            import random
            temp = float(random.randint(28, 38))
            humidity = float(random.randint(40, 85))
            cloud_cover = float(random.randint(0, 100))
            wind = float(random.randint(5, 25))
            
            if cloud_cover > 75:
                desc = "Overcast clouds"
                icon = "04d"
                # Generate weather alert if cloud output is high
                new_w_alert = Alert(
                    alert_type='weather_risk',
                    title='Weather Risk Alert: Overcast Conditions',
                    message=f"Overcast clouds detected in {city} (Cloud cover: {cloud_cover}%). Solar power production expected to be low today.",
                    severity='warning',
                    user_id=current_user.id
                )
                db.session.add(new_w_alert)
            elif cloud_cover > 40:
                desc = "Scattered clouds"
                icon = "03d"
            else:
                desc = "Clear sky"
                icon = "01d"
            
            success = True

        if success:
            w_record = WeatherData(
                city=city,
                temperature=temp,
                humidity=humidity,
                cloud_cover=cloud_cover,
                wind_speed=wind,
                description=desc.capitalize(),
                icon=icon
            )
            db.session.add(w_record)
            
            # Log action
            log = ActivityLog(
                action=f"Synced weather for: {city} (Temp: {temp}°C, Humidity: {humidity}%)",
                user_email=current_user.email,
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()
            
            flash(f"Weather data successfully updated for {city}!", "success")
        return redirect(url_for('weather.index'))

    # Load recent weather configurations
    history = WeatherData.query.order_by(WeatherData.recorded_at.desc()).limit(15).all()
    city = current_app.config['WEATHER_CITY']
    return render_template('weather.html', history=history, current_city=city)
