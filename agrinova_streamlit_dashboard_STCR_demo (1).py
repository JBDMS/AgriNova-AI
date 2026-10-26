
from datetime import datetime
import time
import csv
from pathlib import Path

import serial
import streamlit as st

# AgriNova AI — ESP32 sensors + STCR demonstration panel
PORT = "COM3"
BAUD = 115200
REFRESH_SECONDS = 2

LOG_FILE = Path(__file__).resolve().parent / "agrinova_sensor_data.csv"


def save_reading(values):
    file_exists = LOG_FILE.exists() and LOG_FILE.stat().st_size > 0

    with open(LOG_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "soil_moisture_raw",
                "air_temperature_c",
                "humidity_percent",
                "light_lux",
                "soil_temperature_c",
            ])

        writer.writerow([
            datetime.now().astimezone().isoformat(timespec="seconds"),
            *values,
        ])


st.set_page_config(
    page_title="AgriNova AI | Rice Health",
    page_icon="🌾",
    layout="wide",
)

st.title("🌾 AgriNova AI")
st.subheader("Rice Crop Health & STCR Demonstration")
st.caption(
    "Live ESP32 sensor data • STCR inputs are for demonstration "
    "until local equations and field data are verified."
)

# -------------------- STCR DEMO INPUTS --------------------
st.header("1. STCR fertilizer-planning panel")
st.info(
    "Demonstration only: the target yield is temporary, not a verified "
    "UP recommendation. Use coefficients from a relevant agricultural "
    "university, KVK, or ICAR source."
)

left, right = st.columns(2)

with left:
    crop = st.selectbox("Crop", ["Rice (paddy)"])

    target_yield = st.number_input(
        "Target yield (tonnes/ha) — temporary demo value",
        min_value=1.0,
        max_value=12.0,
        value=5.0,
        step=0.5,
    )

    st.caption(
        "Replace this example target with your trial target when known."
    )

with right:
    st.write("**Soil-test values (demo inputs)**")

    soil_n = st.number_input(
        "Available soil N (kg/ha)",
        min_value=0.0,
        value=200.0,
        step=5.0,
    )
    soil_p = st.number_input(
        "Available soil P (kg/ha)",
        min_value=0.0,
        value=15.0,
        step=1.0,
    )
    soil_k = st.number_input(
        "Available soil K (kg/ha)",
        min_value=0.0,
        value=180.0,
        step=5.0,
    )

st.subheader("Locally validated STCR equation coefficients")
st.caption(
    "Enter coefficients from a published rice STCR equation. "
    "Do not guess coefficients."
)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("**Nitrogen (N)**")
    n_intercept = st.number_input(
        "N intercept", value=0.0, step=1.0, key="n_intercept"
    )
    n_soil_coef = st.number_input(
        "N soil coefficient", value=0.0, step=0.01, key="n_soil_coef"
    )
    n_yield_coef = st.number_input(
        "N yield coefficient", value=0.0, step=0.01, key="n_yield_coef"
    )

with c2:
    st.markdown("**Phosphate (P₂O₅)**")
    p_intercept = st.number_input(
        "P₂O₅ intercept", value=0.0, step=1.0, key="p_intercept"
    )
    p_soil_coef = st.number_input(
        "P₂O₅ soil coefficient", value=0.0, step=0.01, key="p_soil_coef"
    )
    p_yield_coef = st.number_input(
        "P₂O₅ yield coefficient", value=0.0, step=0.01, key="p_yield_coef"
    )

with c3:
    st.markdown("**Potash (K₂O)**")
    k_intercept = st.number_input(
        "K₂O intercept", value=0.0, step=1.0, key="k_intercept"
    )
    k_soil_coef = st.number_input(
        "K₂O soil coefficient", value=0.0, step=0.01, key="k_soil_coef"
    )
    k_yield_coef = st.number_input(
        "K₂O yield coefficient", value=0.0, step=0.01, key="k_yield_coef"
    )

if st.button("Calculate demonstration fertilizer doses"):
    coefficients_entered = any(
        abs(x) > 0
        for x in [
            n_intercept, n_soil_coef, n_yield_coef,
            p_intercept, p_soil_coef, p_yield_coef,
            k_intercept, k_soil_coef, k_yield_coef,
        ]
    )

    if not coefficients_entered:
        st.warning(
            "No STCR coefficients entered. Add validated coefficients "
            "before calculating fertilizer doses."
        )
    else:
        # Generic template only. Verify equation form and units
        # against the applicable published rice STCR source.
        n_dose = (
            n_intercept - n_soil_coef * soil_n
            + n_yield_coef * target_yield
        )
        p_dose = (
            p_intercept - p_soil_coef * soil_p
            + p_yield_coef * target_yield
        )
        k_dose = (
            k_intercept - k_soil_coef * soil_k
            + k_yield_coef * target_yield
        )

        st.warning(
            "Template calculation only. Verify the equation, units, "
            "coefficients, and soil-test method against your published "
            "rice STCR source before using these values."
        )

        d1, d2, d3 = st.columns(3)
        d1.metric("N dose (kg/ha)", f"{max(0, n_dose):.1f}")
        d2.metric("P₂O₅ dose (kg/ha)", f"{max(0, p_dose):.1f}")
        d3.metric("K₂O dose (kg/ha)", f"{max(0, k_dose):.1f}")

st.divider()

# -------------------- LIVE ESP32 READINGS --------------------
st.header("2. Live field sensor readings")
st.caption(
    "Connect the ESP32 by USB. Close Arduino Serial Monitor and stop "
    "any Jupyter cell reading COM3 first."
)


@st.cache_resource
def open_serial(port, baud):
    return serial.Serial(port, baud, timeout=3)


def read_sensor_row(connection):
    while True:
        line = connection.readline().decode(
            "utf-8", errors="ignore"
        ).strip()

        if not line:
            continue

        values = line.split(",")

        if len(values) != 5:
            continue

        try:
            return [float(value) for value in values]
        except ValueError:
            # Skip header or non-numeric serial messages.
            continue


try:
    connection = open_serial(PORT, BAUD)
    st.success(f"Connected to ESP32 on {PORT} at {BAUD} baud.")

    moisture_col, air_col, humidity_col, light_col, soiltemp_col = (
        st.columns(5)
    )

    moisture_metric = moisture_col.empty()
    air_metric = air_col.empty()
    humidity_metric = humidity_col.empty()
    light_metric = light_col.empty()
    soiltemp_metric = soiltemp_col.empty()

    latest_table = st.empty()
    plant_status = st.empty()

    while True:
        moisture, air_temp, humidity, light, soil_temp = (
            read_sensor_row(connection)
        )

        # Save each sensor reading to CSV.
        save_reading([
            moisture, air_temp, humidity, light, soil_temp
        ])

        moisture_metric.metric(
            "Soil moisture (raw)", f"{moisture:.0f}"
        )
        air_metric.metric(
            "Air temperature",
            "—" if air_temp < -100 else f"{air_temp:.1f} °C",
        )
        humidity_metric.metric(
            "Humidity",
            "—" if humidity < 0 else f"{humidity:.1f} %",
        )
        light_metric.metric(
            "Light",
            "Not connected" if light < 0 else f"{light:.1f} lux",
        )
        soiltemp_metric.metric(
            "Soil temperature",
            "—" if soil_temp < -100 else f"{soil_temp:.2f} °C",
        )

        latest_table.table([
            {
                "Sensor": "Soil moisture (raw ADC)",
                "Reading": f"{moisture:.0f}",
            },
            {
                "Sensor": "Air temperature",
                "Reading": (
                    "Not available" if air_temp < -100
                    else f"{air_temp:.1f} °C"
                ),
            },
            {
                "Sensor": "Humidity",
                "Reading": (
                    "Not available" if humidity < 0
                    else f"{humidity:.1f} %"
                ),
            },
            {
                "Sensor": "Light",
                "Reading": (
                    "Not available" if light < 0
                    else f"{light:.1f} lux"
                ),
            },
            {
                "Sensor": "Soil temperature",
                "Reading": (
                    "Not available" if soil_temp < -100
                    else f"{soil_temp:.2f} °C"
                ),
            },
        ])

        # Demonstration status only; not a validated diagnosis.
        if moisture < 1200:
            moisture_note = (
                "Raw moisture reading is relatively low; check sensor "
                "calibration and pot soil."
            )
        elif moisture > 3000:
            moisture_note = (
                "Raw moisture reading is relatively high; check drainage "
                "and sensor calibration."
            )
        else:
            moisture_note = (
                "Moisture reading is in the demonstration range; "
                "confirm with a calibrated sensor."
            )

        plant_status.info(
            f"🪴 Potted rice-plant demo: {moisture_note} "
            "This is not a crop-health diagnosis. Calibrate the soil "
            "sensor in your own pot soil."
        )

        time.sleep(REFRESH_SECONDS)

except serial.SerialException as error:
    st.error(f"Could not open {PORT}: {error}")
    st.info(
        "Close Arduino Serial Monitor and stop the Jupyter cell reading "
        "COM3. Only one application can use COM3 at a time. Keep the "
        "ESP32 connected, then refresh this page. If needed, change "
        "PORT near the top of this file."
    )

except KeyboardInterrupt:
    st.info("Dashboard stopped.")
