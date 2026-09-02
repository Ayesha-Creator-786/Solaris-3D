import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import joblib

def main():
    print("Generating synthetic solar dataset...")
    # Seed for reproducibility
    np.random.seed(42)
    
    # Generate 1000 records
    n_samples = 1000
    
    # Month (1-12)
    month = np.random.randint(1, 13, n_samples)
    # Hour of day (6 to 18 representing daytime)
    hour = np.random.randint(6, 19, n_samples)
    
    # Temperature: higher in summer (months 5-8), lower in winter
    temp_base = 20 + 10 * np.sin((month - 1) * np.pi / 6)
    temperature = temp_base + np.random.normal(0, 3, n_samples)
    
    # Humidity: higher contextually, 30% to 90%
    humidity = np.random.randint(30, 91, n_samples)
    
    # Cloud cover: 0 to 100%
    cloud_cover = np.random.randint(0, 101, n_samples)
    
    # Irradiance: based on hour, month, and cloud cover
    # Peak at midday (hour 12-13), lower near 6 and 18
    hour_factor = np.sin((hour - 6) * np.pi / 12)
    # Seasonal factor
    month_factor = 0.7 + 0.3 * np.sin((month - 1) * np.pi / 6)
    # Cloud factor: 100% cloud cover drops irradiance to 10%
    cloud_factor = 1.0 - 0.9 * (cloud_cover / 100.0)
    
    irradiance_max = 1000.0 # W/m2 base
    irradiance = irradiance_max * hour_factor * month_factor * cloud_factor
    # Add noise & clamp to min 0
    irradiance = np.clip(irradiance + np.random.normal(0, 50, n_samples), 0, 1100)
    
    # Solar Output: proportional to irradiance, affected slightly by temperature (efficiency drops slightly at very high temps)
    # Peak solar output is around 6.0 kW
    temp_efficiency = 1.0 - 0.004 * np.clip(temperature - 25, 0, None)
    solar_output = (irradiance / 1000.0) * 6.0 * temp_efficiency
    # Add minor noise
    solar_output = np.clip(solar_output + np.random.normal(0, 0.2, n_samples), 0, 7.0)
    
    # Construct DataFrame
    df = pd.DataFrame({
        'temperature': np.round(temperature, 1),
        'humidity': humidity,
        'cloud_cover': cloud_cover,
        'irradiance': np.round(irradiance, 1),
        'hour': hour,
        'month': month,
        'solar_output': np.round(solar_output, 2)
    })
    
    # Save dirs
    os.makedirs('ai/dataset', exist_ok=True)
    os.makedirs('ai/models', exist_ok=True)
    
    dataset_path = 'ai/dataset/solar_dataset.csv'
    df.to_csv(dataset_path, index=False)
    print(f"Dataset generated and saved to {dataset_path}")
    
    # Select features and target
    X = df[['temperature', 'humidity', 'cloud_cover', 'irradiance', 'hour', 'month']]
    y = df['solar_output']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Random Forest Regressor model...")
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    predictions = model.predict(X_test)
    r2 = r2_score(y_test, predictions)
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    
    print(f"Evaluation Metrics:")
    print(f"  R² Score: {r2:.4f} ({r2*100:.2f}% Accuracy)")
    print(f"  MAE (Mean Absolute Error): {mae:.4f} kW")
    print(f"  RMSE (Root Mean Squared Error): {rmse:.4f} kW")
    
    # Save model
    model_path = 'ai/models/solar_model.pkl'
    joblib.dump(model, model_path)
    print(f"Model successfully saved to {model_path}")

if __name__ == "__main__":
    main()
