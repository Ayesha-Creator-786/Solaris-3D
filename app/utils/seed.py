import datetime
from app import db
from app.models import User, SolarData, WeatherData, Alert, Prediction
import random

def seed_database():
    # 1. Create Default Users if they don't exist
    admin = User.query.filter_by(email='admin@solariq.com').first()
    if not admin:
        admin = User(name='System Admin', email='admin@solariq.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)

    user = User.query.filter_by(email='user@solariq.com').first()
    if not user:
        user = User(name='John Doe', email='user@solariq.com', role='user')
        user.set_password('user123')
        db.session.add(user)
    
    db.session.commit()

    # Retrieve admin/user IDs
    admin_id = User.query.filter_by(email='admin@solariq.com').first().id
    user_id = User.query.filter_by(email='user@solariq.com').first().id

    # 2. Check if SolarData already exists. If yes, skip to save time.
    if SolarData.query.count() > 0:
        return

    print("Seeding sample solar and weather records...")
    
    # 3. Create Solar Records for the last 30 days
    today = datetime.date.today()
    for days_ago in range(30, -1, -1):
        record_date = today - datetime.timedelta(days=days_ago)
        
        # We can seed multiple hours of solar output for each day (e.g., 9 AM, 12 PM, 3 PM)
        # to show diurnal patterns, or store average daily values.
        # Let's seed hourly entries for key times: 9, 12, 15 (3 PM)
        hours = [9, 12, 15]
        for hr in hours:
            # Weather variables depending on month/day
            month = record_date.month
            
            # Base variables
            temp = float(random.randint(26, 38))
            humidity = float(random.randint(40, 80))
            cloud_cover = float(random.randint(0, 100))
            
            # Predictable irradiance based on cloud cover
            # Peak irradiance around 12 PM
            base_irr = 850 if hr == 12 else 550
            irradiance = float(max(10, int(base_irr * (1 - 0.007 * cloud_cover) + random.randint(-50, 50))))
            
            # Theoretical solar output modeled roughly
            # Maximum system capacity is around 6kW
            theoretical = (irradiance / 1000.0) * 5.5 * (1 - 0.003 * (temp - 25))
            
            # actual output might have efficiency drops
            # Let's simulate a periodic drop around 10-15 days ago to trigger maintenance alerts
            efficiency_modifier = 1.0
            if 10 <= days_ago <= 15:
                # Panel was dirty
                efficiency_modifier = 0.72  # 28% drop!
            
            actual_output = max(0.0, round(theoretical * efficiency_modifier + random.uniform(-0.1, 0.1), 2))
            predicted_output = max(0.0, round(theoretical, 2))
            
            # Avoid divide by zero
            eff_score = 0.0
            if predicted_output > 0:
                eff_score = round((actual_output / predicted_output) * 100, 1)

            solar_rec = SolarData(
                date=record_date,
                temperature=temp,
                humidity=humidity,
                cloud_cover=cloud_cover,
                irradiance=irradiance,
                hour=hr,
                month=month,
                solar_output=actual_output,
                predicted_output=predicted_output,
                efficiency_score=eff_score
            )
            db.session.add(solar_rec)

    # 4. Seed Weather Data
    weather_cities = ['Karachi', 'Lahore', 'Islamabad']
    for city in weather_cities:
        w_data = WeatherData(
            city=city,
            temperature=float(random.randint(28, 36)),
            humidity=float(random.randint(45, 75)),
            cloud_cover=float(random.randint(5, 80)),
            wind_speed=float(random.randint(5, 25)),
            description="Clear sky" if random.random() > 0.5 else "Scattered clouds",
            icon="01d" if random.random() > 0.5 else "03d"
        )
        db.session.add(w_data)

    # 5. Seed Alerts
    alerts = [
        Alert(
            alert_type='maintenance',
            title='Performance Drop Alert',
            message='Severe solar output degradation detected (efficiency fell to ~72%). Clean panels recommended.',
            severity='warning',
            user_id=user_id,
            is_read=False
        ),
        Alert(
            alert_type='weather_risk',
            title='High Cloud Coverage Forecast',
            message='Tomorrow is expected to have 85% cloud coverage. Solar generation will drop by estimated 60%.',
            severity='info',
            user_id=user_id,
            is_read=False
        ),
        Alert(
            alert_type='low_output',
            title='Critical Low Output Warning',
            message='Solar efficiency score fell below critical 60% threshold at 12:00 PM today.',
            severity='danger',
            user_id=user_id,
            is_read=True
        )
    ]
    for alt in alerts:
        db.session.add(alt)

    db.session.commit()
    print("Database seeding completed.")
