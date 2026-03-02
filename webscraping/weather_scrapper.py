import re
import os
import sqlite3
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Setup Selenium Driver

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # headless mode
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920x1080')

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )
    return driver



# Scraping Functions

def get_weather_links(driver, cities):
    BASE_URL = "https://www.timeanddate.com/weather/"
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 10)

    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "td a")))
        links = driver.find_elements(By.CSS_SELECTOR, 'td a')
    except Exception as e:
        print(f"Error finding links: {e}")
        return []

    cities_links = []
    seen_urls = set()
    for link in links:
        url = link.get_attribute("href")
        if url:
            for city in cities:
                if city.lower().replace(" ", "-") in url.lower():
                    if url not in seen_urls:
                        seen_urls.add(url)
                        cities_links.append({"city": city, "url": url})
                    break
    return cities_links


def get_current_weather(driver, city_url):
    driver.get(city_url)
    wait = WebDriverWait(driver, 10)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.bk-focus")))

        temp_text = driver.find_element(By.CSS_SELECTOR, "div.h2").text
        temp_text = temp_text.replace('°F', '').strip() 

        forecast = driver.find_element(By.CSS_SELECTOR, "p").text.rstrip('.')

        wind_text = driver.find_element(By.XPATH, "//div[@id='qlook']//p[contains(., 'Wind:')]").text
        match = re.search(r"Wind:\s*(\d+)", wind_text)
        if match:
            wind = match.group(1)
        elif "No wind" in wind_text:
            wind = "0"
        else:
            wind = None

        humidity_elements = driver.find_elements(By.CSS_SELECTOR, "table.table--left.table--inner-borders-rows tbody tr:nth-child(6) td")
        humidity = humidity_elements[0].text.replace('%', '') if humidity_elements else None

        current_time_text = driver.find_element(By.ID, "wtct").text
        date = current_time_text.split(" at ")[0]

        return {
            "city": city_url.split("/")[-1].replace("-", " "),
            "current_temp": temp_text,
            "date": date,
            "humidity": humidity,
            "wind": wind,
            "forecast": forecast
        }

    except Exception as e:
        print(f"Error retrieving weather for {city_url}: {e}")
        return None


def parse_climate_value(text):
    month_match = re.search(r'^[A-Za-z]+', text)
    month = month_match.group(0) if month_match else None
    value_match = re.search(r'(\d+\.?\d*)', text)
    value = float(value_match.group(1)) if value_match else None
    return month, value


def get_climate_info(driver, city_url):
    climate_url = city_url.rstrip("/") + "/climate"
    driver.get(climate_url)
    wait = WebDriverWait(driver, 10)

    try:
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//h3[normalize-space()='Quick Climate Info']")
            )
        )
        data = []
        rows = driver.find_elements(
            By.XPATH,
            "//h3[normalize-space()='Quick Climate Info']/ancestor::table[1]/tbody/tr"
        )

        for row in rows:
            try:
                label = row.find_element(By.XPATH, './th').text
                raw_text = row.find_element(By.XPATH, './td').text
                month, value = parse_climate_value(raw_text)

                data.append({
                    "city": city_url.split("/")[-1].replace("-", " "),
                    "metric": label,
                    "month": month,
                    "value": value
                })

            except Exception as e:
                print(f"Row skipped for {city_url}: {e}")
                continue
        return data

    except Exception as e:
        print(f"Error retrieving climate info for {city_url}: {e}")
        return None


# Cleaning Functions

def clean_weather_data(df):
    df['current_temp'] = pd.to_numeric(df['current_temp'], errors='coerce')
    df['humidity'] = pd.to_numeric(df['humidity'], errors='coerce').fillna(0)
    df['wind'] = pd.to_numeric(df['wind'], errors='coerce').fillna(0)
    df['city'] = df['city'].str.title()  
    df['forecast'] = df['forecast'].fillna("N/A")
    df['date'] = pd.to_datetime(df['date'], format="%b %d, %Y", errors='coerce')
    return df


def clean_climate_data(df):
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df['month'] = df['month'].fillna("Unknown")
    df['city'] = df['city'].str.title()
    df['metric'] = df['metric'].fillna("Unknown")
    return df

# Database Functions 

DATA_DIR = "../data/raw"
DB_PATH = "../database/cities_weather.db" 

# CSV files
WEATHER_CSV = os.path.join(DATA_DIR, "weather_data.csv")
CLIMATE_CSV = os.path.join(DATA_DIR, "climate_data.csv")
CITY_LINKS_CSV = os.path.join(DATA_DIR, "city_links.csv")

# Connect to SQLite

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def import_csv_to_sqlite(csv_path, table_name):
    df = pd.read_csv(csv_path)

    df.columns = [c.replace(" ", "_").lower() for c in df.columns]

    df = df.where(pd.notnull(df), None)

    df.to_sql(table_name, conn, if_exists="replace", index=False)
    print(f"Imported {csv_path}, table '{table_name}'")

import_csv_to_sqlite(CITY_LINKS_CSV, "city_links")
import_csv_to_sqlite(WEATHER_CSV, "weather_data")
import_csv_to_sqlite(CLIMATE_CSV, "climate_data")


cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in database:", tables)


conn.commit()
conn.close()



# Main Function

def main():
    driver = setup_driver()
    output_dir = "../data/raw"
    os.makedirs(output_dir, exist_ok=True)

    cities = ["San Francisco", "Hong Kong", "New York", "Seoul", "Honolulu", "London", "Paris", "Sydney", "Moscow", "Dubai"]

    cities_links = get_weather_links(driver, cities)
    if not cities_links:
        print("No city links found. Exiting.")
        driver.quit()
        return

    df_links = pd.DataFrame(cities_links)
    df_links.to_csv(f"{output_dir}/city_links.csv", index=False)


    weather_data = []
    for city_info in cities_links:
        city_weather = get_current_weather(driver, city_info["url"])
        if city_weather:
            city_weather["city"] = city_info["city"]
            weather_data.append(city_weather)

    if weather_data:
        df_weather = pd.DataFrame(weather_data)
        df_weather = clean_weather_data(df_weather)  
        df_weather.to_csv(f"{output_dir}/weather_data.csv", index=False)


    climate_data = []
    for city_info in cities_links:
        city_climate = get_climate_info(driver, city_info["url"])
        if city_climate:
            climate_data.extend(city_climate)

    if climate_data:
        df_climate = pd.DataFrame(climate_data)
        df_climate = clean_climate_data(df_climate)
        df_climate.to_csv(f"{output_dir}/climate_data.csv", index=False)

    driver.quit()


if __name__ == "__main__":
    main()