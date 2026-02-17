import streamlit as st

st.set_page_config(page_title="Gesundheit Tracker", layout="centered")

st.title("Gesundheit & Performance Tracker")

st.markdown("### Etappenziele")
st.write("09.04.2026 – Badeferien")
st.write("26.09.2026 – Badeferien")

st.markdown("---")

st.header("Gewicht")
weight = st.number_input("Heutiges Gewicht (kg)", 50.0, 200.0, 100.0, 0.1)
if st.button("Gewicht speichern"):
    st.success(f"{weight} kg gespeichert (Demo-Version)")

st.markdown("---")

st.header("Ernährung")
kcal = st.number_input("Kalorien heute", 0, 5000, 0, 10)
protein = st.number_input("Protein (g)", 0, 300, 0, 1)
if st.button("Ernährung speichern"):
    st.success("Ernährung gespeichert (Demo-Version)")

st.markdown("---")

st.header("Training")
exercise = st.text_input("Übung")
sets = st.number_input("Sätze", 1, 10, 3)
reps = st.number_input("Wiederholungen", 1, 30, 8)
weight_training = st.number_input("Gewicht (kg)", 0.0, 500.0, 0.0, 2.5)
if st.button("Training speichern"):
    st.success("Training gespeichert (Demo-Version)")

st.markdown("---")

st.header("Schulter-Check")
pain = st.slider("Schmerz bei Überkopfdrücken (0–10)", 0, 10, 0)
if pain >= 4:
    st.warning("Kein schweres Overhead-Drücken heute.")
else:
    st.success("Überkopftraining möglich.")
