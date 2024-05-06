# VIN Decoder Application README

## Overview
The VIN Decoder Application automates the process of retrieving and organizing vehicle information from Vehicle Identification Numbers (VINs) using Python, Flask, and Selenium. This tool is designed for Brown & Riding to enhance their insurance underwriting process by providing quick and reliable access to vehicle data, including type, body class, and weight.

## System Requirements
- RAM: At least 4GB
- Disk Space: At least 100MB
- Python 3.8 or higher installed
- Google Chrome and compatible Chrome WebDriver installed

## Installation
1. Clone the repository to your local machine or download the ZIP file and extract it.
2. Install the required Python packages:
   ```
   pip install Flask selenium pandas
   ```
3. Ensure that Google Chrome and the corresponding version of Chrome WebDriver are installed on your system. Place the Chrome WebDriver executable in a location recognized by the system PATH or in the project directory.

## Running the Application
1. Navigate to the project directory in the command prompt.
2. Start the application by running:
   ```
   python app.py
   ```
3. The application will automatically open the default web browser to `http://127.0.0.1:5000/`.

## Usage
- Upon launch, the application presents a web form where VIN numbers can be entered.
- Input the VIN numbers, one per line, in the provided text area.
- Click the `Decode` button to submit the VINs.
- The application processes the VINs, retrieves the vehicle data, and presents it as a downloadable CSV file.

## Application Components
- **app.py**: Contains the Flask server, routes, and the main functions for processing VINs and serving the web interface.
- **templates/index.html**: HTML file for the web interface where users input VIN numbers.
- **static/**: Directory for static files like CSS and JavaScript, if needed.

## Key Functions
- **open_browser()**: Opens the default web browser at the application's home page.
- **scrape_vin_data(vin_numbers)**: Takes a list of VIN numbers, uses Selenium to scrape vehicle data from the NHTSA website, and stores it in a pandas DataFrame.
- **index()**: Renders the front-end template to display the home page.
- **submit()**: Handles the form submission, invokes the scraping function, and returns a CSV file with the processed data.

## Maintenance and Troubleshooting
- **Website Updates**: If the NHTSA website updates its layout, the Selenium XPaths in `scrape_vin_data` may need adjustments to accurately locate and extract data.
- **Selenium Compatibility**: Ensure the Chrome WebDriver is compatible with the installed version of Google Chrome.
- **Python and Flask**: Keep the environment updated to maintain compatibility and security.
- **Logging and Errors**: The application logs errors and important process information, which should be checked if any issues arise.

## Common Issues
- **CSV File Not Generating**: Ensure the Flask routes are correctly set, and the memory buffer used for the CSV is properly handled.
- **Web Page Not Displaying**: Verify Flask routing, template rendering, and server status.
- **Application Not Starting**: Check for syntax errors, ensure all dependencies are installed, and verify the setup of the Python environment.

## Version History
- 1.0: Initial release with basic functionality for scraping and data processing.

For detailed maintenance instructions and additional troubleshooting, refer to the accompanying `maintenance.txt` file included in the project directory.
