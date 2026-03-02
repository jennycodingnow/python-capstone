import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import altair as alt



df_weather = pd.read_csv("data/raw/weather_data.csv")
df_climate = pd.read_csv("data/raw/climate_data.csv")

df_weather['date'] = pd.to_datetime(df_weather['date'], format="%b %d, %Y", errors='coerce')


#side bar for filters
st.sidebar.header("Filters")
city = st.sidebar.selectbox("Select city", df_climate['city'].unique())
metric = st.sidebar.selectbox("Select annual climate metric for city comparison", df_climate['metric'].unique())
weather_metric = st.sidebar.selectbox(
    "Select current weather metric for comparison", 
    ["current_temp", "humidity", "wind"]
)

# Section 1: Compare climate metric across all cities-bar chart
st.header(f"Climate Metric Comparison: '{metric}' Across Cities")
df_metric = df_climate[df_climate['metric'] == metric].copy()

unit_map = {
    "Hottest Month": "°F",
    "Coldest Month": "°F",
    "Wettest Month": "inches",
    "Windiest Month": "mph",
    "Annual precip.": "inches"
}

unit = unit_map.get(metric, "")

chart = alt.Chart(df_metric).mark_bar().encode(
    x=alt.X('city:N', title='City'),
    y=alt.Y('value:Q', title=f'{metric} ({unit})'),
    color=alt.condition(
        alt.datum.city == city,
        alt.value("orange"),
        alt.value("lightgray")
    ),
    tooltip=['city', 'month', alt.Tooltip('value:Q', title=f'Value ({unit})')]
)

st.altair_chart(chart, use_container_width=True)


# Section 2: Current weather comparison across all cities-bar chart
st.header("Current Weather Comparison Across Cities")

df_latest_weather = (
    df_weather
    .sort_values('date')
    .groupby('city')
    .last()
    .reset_index()
)
st.subheader(f"{weather_metric.capitalize()} Comparison")
unit_map = {
    "current_temp": "°F",
    "humidity": "%",
    "wind": "mph",
}
unit = unit_map.get(weather_metric, "")
chart = alt.Chart(df_latest_weather).mark_bar().encode(
    x=alt.X('city:N', title='City'),
    y=alt.Y(f'{weather_metric}:Q',
            title=f'{weather_metric.capitalize()} ({unit})'),
    color=alt.condition(
        alt.datum.city == city,
        alt.value("orange"),
        alt.value("lightgray")
    ),
    tooltip=[
        alt.Tooltip('city:N', title='City'),
        alt.Tooltip(f'{weather_metric}:Q', title=f'Value ({unit})')
    ]
)
st.altair_chart(chart, use_container_width=True)


# Section 3: Multiple weather metrics side by side-bar chart
st.header("Temperature, Humidity, and Wind Across Cities")
st.bar_chart(df_latest_weather.set_index('city')[['current_temp', 'humidity', 'wind']])


# Section 4: Forecast distribution across cities-pie chart
st.header("Current Forecast Across Cities")
df_latest_weather = df_weather.sort_values('date').groupby('city').last().reset_index()
forecast_counts = df_latest_weather['forecast'].value_counts()

fig, ax = plt.subplots(figsize=(5,5))
ax.pie(forecast_counts, labels=forecast_counts.index, autopct='%1.1f%%', startangle=90)
ax.set_title("Forecast Distribution Across Cities")
st.pyplot(fig)


# Section 5: Temperature vs Humidity-scatter plot
st.header("Temperature vs Humidity (Scatter)")
scatter_df = df_weather.dropna(subset=['current_temp', 'humidity'])

st.scatter_chart(
    scatter_df,
    x='current_temp',
    y='humidity',
    color='city'
)
