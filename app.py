from flask import Flask, request, Response, render_template, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, WebDriverException
import pandas as pd
import webbrowser
import re
from io import BytesIO
from threading import Timer
import time
import os
import signal
import numpy as np

app = Flask(__name__)

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

def scrape_vin_data(vin_numbers):
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://vpic.nhtsa.dot.gov/decoder/")
    df = pd.DataFrame(columns=['VIN', 'Vehicle Type', 'Body Class', 'Weight'])

    for vin in vin_numbers:
        vin_input = driver.find_element(By.ID, "VIN")
        vin_input.clear()
        vin_input.send_keys(vin)
        decode_button = driver.find_element(By.ID, "btnSubmit")
        decode_button.click()
        time.sleep(2) 

        try:
            vehicle_type = driver.find_element(By.XPATH, "/html/body/div[2]/div[3]/div[2]/div/div[2]/div[2]/div[1]/p[3]").text

            body_class = driver.find_element(By.XPATH, "/html/body/div[2]/div[3]/div[2]/div/div[2]/div[2]/div[1]/p[7]").text

            if "INCOMPLETE VEHICLE" in vehicle_type:
                weight = driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/div[2]/div[1]/div").text
            elif "TRAILER" in vehicle_type:
                weight = driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/div[2]/p[2]").text
            elif "MOTORCYCLE" in vehicle_type:
                weight = driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/div[2]/p[2]").text
            elif "BUS" in vehicle_type:
                weight = driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/div[2]/div[2]/div[2]").text
            else:
                weight = driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/div[2]/div[2]/div[1]").text
                                                        
        except (NoSuchElementException, WebDriverException) as e:
            vehicle_type = "Check VIN"
            body_class = ""
            weight = ""
        
        new_row = pd.DataFrame({'VIN': [vin], 'Vehicle Type': [vehicle_type], 'Body Class': [body_class], 'Weight': [weight]})
        df = pd.concat([df, new_row], ignore_index=True)

        driver.refresh()        

    driver.quit()
    return df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shutdown', methods=['POST'])
def shutdown():
    os.kill(os.getpid(), signal.SIGTERM)
    return jsonify({'status': 'shutting down'})

@app.route('/submit', methods=['POST'])
def submit():
    vin_input = request.form['vin_numbers']
    vin_numbers = vin_input.splitlines() 
    df = scrape_vin_data(vin_numbers)

    df['Vehicle Type'] = df['Vehicle Type'].str.replace('Vehicle Type: ', '')
    df['Body Class'] = df['Body Class'].str.replace('Body Class: ', '')
    df['Weight'] = df['Weight'].astype(str)
    df['Weight'] = df['Weight'].str.replace('Gross Vehicle Weight Rating: ', '')
    df['Weight'] = df['Weight'].str.replace(r'.*:\s+', '', regex=True)
    df['Weight'] = df['Weight'].str.replace(r'\(.*?\)', '', regex=True).str.strip()

    df.loc[df['Vehicle Type'].str.contains("Vehicle Type:"), 'Vehicle Type'] = "Invalid VIN"
    df.loc[df['Vehicle Type'] == "Invalid VIN", ['Body Class', 'Weight']] = ""

    df.loc[df['Body Class'].str.contains("Body Class:"), 'Body Class'] = "--"
    df.loc[df['Weight'].str.contains("Gross Vehicle Weight Rating:"), 'Weight'] = "--"

    def weight_mean(weight_range):
        if pd.isna(weight_range) or weight_range == "--":
            return None
        weight_bounds = re.findall(r'\d{1,3}(?:,\d{3})*', weight_range)
        weight_bounds = [int(weight.replace(",", "")) for weight in weight_bounds]
        if len(weight_bounds) == 1:
            return weight_bounds[0]
        elif len(weight_bounds) == 2:
            return sum(weight_bounds) / 2
        else:
            return None
        
    df['Weight_mean'] = df['Weight'].apply(weight_mean)
    
    def classify_vehicle(row):
        if row['Vehicle Type'] == "Invalid VIN":
            return "NA/Trailer"
        elif row['Vehicle Type'] == "TRAILER" or row['Body Class'] == "Trailer":
            return "Trailer"
        elif row['Body Class'] == "Truck-Tractor":
            return "Truck-Tractor"
        elif row['Body Class'] == "Cargo Van":
            return "Cargo Van"
        elif (row['Vehicle Type'] == "TRUCK" and row['Weight_mean'] < 10000) or (row['Body Class'] == "Incomplete" and row['Weight_mean'] < 10000) or (row['Body Class'] == "Pickup" and row['Weight_mean'] < 10000):
            return "LT"
        elif row['Vehicle Type'] == "MOTORCYCLE" or row['Vehicle Type'] == "LOW SPEED VEHICLE (LSV)":
            return "Motorcycle"
        elif row['Vehicle Type'] == "PASSENGER CAR" or row['Vehicle Type'] == "MULTIPURPOSE PASSENGER VEHICLE (MPV)":
            return "PP"
        elif 10001 <= row['Weight_mean'] <= 20000 or (row['Body Class'] == "Truck" and 10001 <= row['Weight_mean'] <= 20000):
            return "MT"
        elif row['Body Class'] == "Van":
            return "Van"
        elif 20001 <= row['Weight_mean'] <= 33000 or (row['Body Class'] == "Truck" and 20001 <= row['Weight_mean'] <= 33000):
            return "HT"
        elif row['Weight_mean'] == 33001 and row['Body Class'] != "Truck-Tractor":
            return "EHT"
        else:
            return "OtherNA"

    df['Classification'] = df.apply(classify_vehicle, axis=1)

    invalid_vins = df.loc[df['Vehicle Type'] == "Invalid VIN", 'VIN'].tolist()
    max_rows = len(df)
    df['Invalid VINs'] = invalid_vins + [None] * (max_rows - len(invalid_vins))

    df['valid_LC'] = np.where((df['VIN'].str.len() == 17) &
                            (~df['VIN'].str.contains('I|O|Q', case=False).fillna(False)), 
                                                'VALID', 
                                                'MANUAL')
    
    vin_char_key = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
                'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9, 'S': 2,
                'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9}

    position_weights = {'1': 8, '2': 7, '3': 6, '4': 5, '5': 4, '6': 3, '7': 2, '8': 10,
                    '9': 0, '10': 9, '11': 8, '12': 7, '13': 6, '14': 5, '15': 4,
                    '16': 3, '17': 2}

    def replace_alphas(string, key):
        replaced_alphas = ''.join(str(key[char]) if char in key else char for char in string)
        return replaced_alphas

    def multiply_digits(string, weights):
        factor_vector = np.array(list(string), dtype=int)
        product_vector = factor_vector * np.array(list(weights.values()))
        return np.sum(product_vector)

    df['valid_checkdigit'] = df.apply(lambda row: 'VALID' if row['valid_LC'] == 'VALID' else 'MANUAL', axis=1)

    for i, row in df.iterrows():
        if row['valid_checkdigit'] == 'VALID':
            actual_check_digit = row['VIN'][8]
            auto_vin_check = row['VIN']
            transformed_vector = replace_alphas(auto_vin_check, vin_char_key)
            vin_sums = multiply_digits(transformed_vector, position_weights)
            predicted_check_digit = vin_sums % 11
            predicted_check_digit = 'X' if predicted_check_digit == 10 else str(predicted_check_digit)
            check_digit_match = actual_check_digit == predicted_check_digit
            df.at[i, 'valid_checkdigit'] = 'VALID' if check_digit_match else 'MANUAL'
    
    invalid_vins = df.loc[(df['Vehicle Type'] == "Invalid VIN") | (df['valid_checkdigit'] == 'MANUAL'), 'VIN'].tolist()
    max_rows = len(df)

    df['Invalid VINs'] = invalid_vins + [None] * (max_rows - len(invalid_vins))

    df = df.drop('Weight_mean', axis=1)

    csv_string = df.to_csv(index=False)

    mem = BytesIO()
    mem.write(csv_string.encode('utf-8'))
    mem.seek(0)

    return Response(mem, mimetype='text/csv', headers={"Content-disposition": "attachment; filename=vehicle_data.csv"})

if __name__ == "__main__":
    webbrowser.open_new('http://127.0.0.1:5000/')
    app.run(debug=False, use_reloader=False)