import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Gesundheit Tracker", layout="centered")

ETAPPE_1 = date(2026, 4, 9)
ETAPPE_2 = date(2026, 9, 26)

def to_float(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return None

@st.cache_resource
def get_sheets():
    import json

    sa_info = json.loads(st.secrets["gcp_service_account"])
    sa_info["private_key"] = sa_info["private_key"].replace("\\n", "\n")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["1WfXRyq7wy3wzweA_EyJF5Dy94OT2ZiXoSn8jYX6dhsI"])
    return {
        "weight": sh.worksheet("weight"),
        "nutrition": sh.worksheet("nutrition"),
        "training": sh.worksheet("training"),
        "shoulder": sh.worksheet("shoulder"),
    }

def append_row(ws, row):
    ws.append_row(row, value_input_option="USER_ENTERED")

def fetch_df(ws):
    values = ws.get_all_values()
    if not values or len(values) < 2:
        return pd.DataFrame(columns=values[0] if values else [])
    header = values[0]
    rows = values[1:]
    return pd.DataFrame(rows, columns=header)

st.title("Gesundheit & Performance Tracker")

sheets = get_sheets()
today = date.today()

st.markdown("### Etappenziele")
st.write(f"{ETAPPE_1.isoformat()} – Badeferien")
st.write(f"{ETAPPE_2.isoformat()} – Badeferien")

tabs = st.tabs(["Dashboard", "Gewicht", "Ernährung", "Training", "Schulter"])

with tabs[0]:
    st.subheader("Heute auf einen Blick")

    df_w = fetch_df(sheets["weight"])
    df_n = fetch_df(sheets["nutrition"])

    last_weight = None
    w7 = None

    if not df_w.empty:
        df_w2 = df_w.copy()
        df_w2["date"] = pd.to_datetime(df_w2["date"], errors="coerce")
        df_w2["weight_kg"] = df_w2["weight_kg"].apply(to_float)
        df_w2 = df_w2.dropna(subset=["date", "weight_kg"]).sort_values("date")
        if not df_w2.empty:
            last_weight = float(df_w2.iloc[-1]["weight_kg"])
            last7 = df_w2[df_w2["date"] >= (pd.Timestamp(today) - pd.Timedelta(days=6))]
            if not last7.empty:
                w7 = float(last7["weight_kg"].mean())

    c1, c2 = st.columns(2)
    c1.metric("Letzte Messung", f"{last_weight:.1f} kg" if last_weight else "—")
    c2.metric("7-Tage-Schnitt", f"{w7:.1f} kg" if w7 else "—")

    ate_kcal = 0
    ate_pro = 0
    if not df_n.empty:
        df_n2 = df_n.copy()
        df_n2["date"] = pd.to_datetime(df_n2["date"], errors="coerce").dt.date
        df_n2["kcal"] = df_n2["kcal"].apply(to_float)
        df_n2["protein_g"] = df_n2["protein_g"].apply(to_float)
        today_rows = df_n2[df_n2["date"] == today]
        if not today_rows.empty:
            ate_kcal = int(sum([x for x in today_rows["kcal"] if x is not None]))
            ate_pro = int(sum([x for x in today_rows["protein_g"] if x is not None]))

    st.write(f"**Heute erfasst:** {ate_kcal} kcal, {ate_pro} g Protein")

with tabs[1]:
    st.subheader("Gewicht eintragen")
    w = st.number_input("Gewicht (kg)", 50.0, 200.0, 100.0, 0.1)
    kfa = st.number_input("KFA (%) optional", 0.0, 60.0, 0.0, 0.1)
    waist = st.number_input("Taille (cm) optional", 0.0, 200.0, 0.0, 0.5)
    notes = st.text_input("Notiz (optional)", "")

    if st.button("Speichern", type="primary"):
        row = [today.isoformat(), w, (kfa if kfa > 0 else ""), (waist if waist > 0 else ""), notes]
        append_row(sheets["weight"], row)
        st.success("Gespeichert.")

    df_w = fetch_df(sheets["weight"])
    if not df_w.empty:
        df_w2 = df_w.copy()
        df_w2["date"] = pd.to_datetime(df_w2["date"], errors="coerce")
        df_w2["weight_kg"] = df_w2["weight_kg"].apply(to_float)
        df_w2 = df_w2.dropna(subset=["date", "weight_kg"]).sort_values("date")
        st.line_chart(df_w2.set_index("date")["weight_kg"])

with tabs[2]:
    st.subheader("Ernährung loggen (pro Eintrag)")
    kcal = st.number_input("Kalorien (kcal)", 0, 5000, 0, 10)
    protein = st.number_input("Protein (g)", 0, 300, 0, 1)
    fat = st.number_input("Fett (g) optional", 0, 300, 0, 1)
    carbs = st.number_input("Kohlenhydrate (g) optional", 0, 600, 0, 1)
    notes = st.text_input("Notiz", "")

    if st.button("Eintrag speichern", type="primary"):
        row = [today.isoformat(), kcal, protein, (fat if fat > 0 else ""), (carbs if carbs > 0 else ""), notes]
        append_row(sheets["nutrition"], row)
        st.success("Gespeichert.")

    df_n = fetch_df(sheets["nutrition"])
    if not df_n.empty:
        df_n2 = df_n.copy()
        df_n2["date"] = pd.to_datetime(df_n2["date"], errors="coerce").dt.date
        df_n2["kcal"] = df_n2["kcal"].apply(to_float)
        df_n2["protein_g"] = df_n2["protein_g"].apply(to_float)
        df_sum = df_n2.groupby("date", as_index=False).agg({"kcal": "sum", "protein_g": "sum"})
        st.dataframe(df_sum.sort_values("date", ascending=False), use_container_width=True)

with tabs[3]:
    st.subheader("Training loggen")
    day = st.selectbox("Trainingstag", ["A", "B", "C", "Rest"])
    exercise = st.text_input("Übung", "")
    sets = st.number_input("Sätze", 1, 10, 3, 1)
    reps = st.number_input("Wiederholungen", 1, 30, 8, 1)
    weight_kg = st.number_input("Gewicht (kg)", 0.0, 500.0, 0.0, 2.5)
    rir = st.number_input("RIR (0–5)", 0, 5, 2, 1)
    pain = st.number_input("Schmerz (0–10)", 0, 10, 0, 1)
    notes = st.text_input("Notiz (optional)", "")

    if st.button("Training speichern", type="primary"):
        row = [today.isoformat(), day, exercise, sets, reps, weight_kg, rir, pain, notes]
        append_row(sheets["training"], row)
        st.success("Gespeichert.")

    df_t = fetch_df(sheets["training"])
    if not df_t.empty:
        st.dataframe(df_t.tail(50), use_container_width=True)

with tabs[4]:
    st.subheader("Schulter-Check & Routine")
    pain_press = st.number_input("Schmerz bei Drücken (0–10)", 0, 10, 0, 1)
    pain_oh = st.number_input("Schmerz bei Überkopf (0–10)", 0, 10, 0, 1)
    routine_done = st.checkbox("10-Min-Routine erledigt")
    trigger = st.text_input("Trigger", "")
    notes = st.text_input("Notiz (optional)", "")

    if st.button("Schulter speichern", type="primary"):
        row = [today.isoformat(), pain_press, pain_oh, ("yes" if routine_done else "no"), trigger, notes]
        append_row(sheets["shoulder"], row)
        st.success("Gespeichert.")

    st.markdown("**Regel:** Wenn Überkopf-Schmerz ≥ 4/10 → kein schweres Overhead-Drücken.")
