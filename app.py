import json
from datetime import date, datetime
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Gesundheit Tracker", layout="centered")

# ----------------------------
# Konfiguration
# ----------------------------
ETAPPE_1 = date(2026, 4, 9)
ETAPPE_2 = date(2026, 9, 26)

DEFAULT_TARGETS = {
    "kcal": 2400,
    "protein_g": 220,
    "fat_g": 70,
    "carbs_g": 0, # optional, wird gerechnet wenn 0
}

# ----------------------------
# Google Sheets Zugriff
# ----------------------------
def get_gspread_client():
    # Streamlit Secrets: st.secrets["gcp_service_account"] muss existieren
    sa_info = dict(st.secrets["gcp_service_account"])
    scopes = [
"https://www.googleapis.com/auth/spreadsheets",
"https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_resource
def get_sheet():
    gc = get_gspread_client()
    sheet_name = st.secrets["app"]["sheet_name"]
    sh = gc.open(sheet_name)
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

def to_float(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return None

# ----------------------------
# UI
# ----------------------------
st.title("Gesundheit & Performance Tracker")

sheets = get_sheet()

# Sidebar: Ziele
st.sidebar.header("Ziele (Editierbar)")
kcal_target = st.sidebar.number_input("Kalorienziel (kcal)", 1200, 5000, DEFAULT_TARGETS["kcal"], 50)
protein_target = st.sidebar.number_input("Proteinziel (g)", 100, 350, DEFAULT_TARGETS["protein_g"], 5)
fat_target = st.sidebar.number_input("Fettziel (g)", 30, 200, DEFAULT_TARGETS["fat_g"], 5)
carbs_target = st.sidebar.number_input("Kohlenhydrate (g, optional)", 0, 600, DEFAULT_TARGETS["carbs_g"], 10)

today = date.today()
days_to_e1 = (ETAPPE_1 - today).days
days_to_e2 = (ETAPPE_2 - today).days

st.sidebar.markdown("---")
st.sidebar.write(f"Etappe 1: **{ETAPPE_1.isoformat()}** (in **{days_to_e1}** Tagen)")
st.sidebar.write(f"Etappe 2: **{ETAPPE_2.isoformat()}** (in **{days_to_e2}** Tagen)")

tabs = st.tabs(["Dashboard", "Gewicht", "Ernährung", "Training", "Schulter"])

# ----------------------------
# Dashboard
# ----------------------------
with tabs[0]:
    st.subheader("Heute auf einen Blick")

    df_w = fetch_df(sheets["weight"])
    df_n = fetch_df(sheets["nutrition"])

    # Gewicht Trend
    weight_today = None
    w7 = None
    if not df_w.empty and "date" in df_w.columns and "weight_kg" in df_w.columns:
        df_w2 = df_w.copy()
        df_w2["date"] = pd.to_datetime(df_w2["date"], errors="coerce")
        df_w2["weight_kg"] = df_w2["weight_kg"].apply(to_float)
        df_w2 = df_w2.dropna(subset=["date", "weight_kg"]).sort_values("date")
        if not df_w2.empty:
            # aktueller Wert (letzte Messung)
            weight_today = df_w2.iloc[-1]["weight_kg"]
            # 7-Tage-Schnitt
            last7 = df_w2[df_w2["date"] >= (pd.Timestamp(today) - pd.Timedelta(days=6))]
            if not last7.empty:
                w7 = float(last7["weight_kg"].mean())

    c1, c2, c3 = st.columns(3)
    c1.metric("Gewicht letzte Messung", f"{weight_today:.1f} kg" if weight_today else "—")
    c2.metric("7-Tage-Schnitt", f"{w7:.1f} kg" if w7 else "—")
    c3.metric("Kalorienziel heute", f"{kcal_target} kcal")

    # Ernährung heute
    ate_kcal = ate_pro = 0
    if not df_n.empty and "date" in df_n.columns:
        df_n2 = df_n.copy()
        df_n2["date"] = pd.to_datetime(df_n2["date"], errors="coerce").dt.date
        df_n2["kcal"] = df_n2.get("kcal", pd.Series()).apply(to_float)
        df_n2["protein_g"] = df_n2.get("protein_g", pd.Series()).apply(to_float)
        today_rows = df_n2[df_n2["date"] == today]
        if not today_rows.empty:
            ate_kcal = int(sum([x for x in today_rows["kcal"] if x is not None]))
            ate_pro = int(sum([x for x in today_rows["protein_g"] if x is not None]))

    st.write("**Heute erfasst:**")
    st.write(f"- Kalorien: **{ate_kcal} / {kcal_target}**")
    st.write(f"- Protein: **{ate_pro} / {protein_target} g**")

    # Ampel
    protein_ok = ate_pro >= protein_target
    kcal_ok = ate_kcal <= kcal_target
    st.write("**Status:**")
    st.success("Protein erfüllt") if protein_ok else st.warning("Protein noch offen")
    st.success("Kalorien im Ziel") if kcal_ok else st.warning("Kalorien über Ziel")

# ----------------------------
# Gewicht
# ----------------------------
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

# ----------------------------
# Ernährung
# ----------------------------
with tabs[2]:
    st.subheader("Ernährung loggen (pro Eintrag / Mahlzeit)")
    kcal = st.number_input("Kalorien (kcal)", 0, 5000, 0, 10)
    protein = st.number_input("Protein (g)", 0, 300, 0, 1)
    fat = st.number_input("Fett (g) optional", 0, 300, 0, 1)
    carbs = st.number_input("Kohlenhydrate (g) optional", 0, 600, 0, 1)
    notes = st.text_input("Notiz (optional)", "")

    if st.button("Eintrag speichern", type="primary"):
        row = [today.isoformat(), kcal, protein, (fat if fat > 0 else ""), (carbs if carbs > 0 else ""), notes]
        append_row(sheets["nutrition"], row)
        st.success("Gespeichert.")

    df_n = fetch_df(sheets["nutrition"])
    if not df_n.empty and "date" in df_n.columns:
        df_n2 = df_n.copy()
        df_n2["date"] = pd.to_datetime(df_n2["date"], errors="coerce").dt.date
        df_n2["kcal"] = df_n2["kcal"].apply(to_float)
        df_n2["protein_g"] = df_n2["protein_g"].apply(to_float)
        df_sum = df_n2.groupby("date", as_index=False).agg({"kcal": "sum", "protein_g": "sum"})
        st.dataframe(df_sum.sort_values("date", ascending=False), use_container_width=True)

# ----------------------------
# Training
# ----------------------------
with tabs[3]:
    st.subheader("Training loggen")
    day = st.selectbox("Trainingstag", ["A", "B", "C", "Rest"])
    exercise = st.text_input("Übung", "")
    sets = st.number_input("Sätze", 1, 10, 3, 1)
    reps = st.number_input("Wiederholungen", 1, 30, 8, 1)
    weight_kg = st.number_input("Gewicht (kg)", 0.0, 500.0, 0.0, 2.5)
    rir = st.number_input("RIR (0–5)", 0, 5, 2, 1)
    pain = st.number_input("Schmerz (0–10)", 0, 10, 0, 1)
    notes = st.text_input("Notiz", "")

    if st.button("Training speichern", type="primary"):
        row = [today.isoformat(), day, exercise, sets, reps, weight_kg, rir, pain, notes]
        append_row(sheets["training"], row)
        st.success("Gespeichert.")

    st.caption("Progressionslogik (MVP): Wenn du bei gleicher Übung 4×5–8 schaffst und RIR ≥ 1, erhöhe beim nächsten Mal um +2.5 kg.")

    df_t = fetch_df(sheets["training"])
    if not df_t.empty:
        st.dataframe(df_t.tail(50), use_container_width=True)

# ----------------------------
# Schulter
# ----------------------------
with tabs[4]:
    st.subheader("Schulter-Check & Routine")
    pain_press = st.number_input("Schmerz bei Drücken (0–10)", 0, 10, 0, 1)
    pain_oh = st.number_input("Schmerz bei Überkopf (0–10)", 0, 10, 0, 1)
    routine_done = st.checkbox("10-Min-Routine erledigt")
    trigger = st.text_input("Trigger (z. B. Overhead, Maschine, Winkel)", "")
    notes = st.text_input("Notiz (optional)", "")

    if st.button("Schulter speichern", type="primary"):
        row = [today.isoformat(), pain_press, pain_oh, ("yes" if routine_done else "no"), trigger, notes]
        append_row(sheets["shoulder"], row)
        st.success("Gespeichert.")

    st.markdown("**Regel (klar):** Wenn Überkopf-Schmerz ≥ 4/10 → kein schweres Overhead-Drücken, stattdessen Stabilität + Varianten ohne Schmerz.")
    st.markdown("**10-Min-Routine Vorschlag:** Face Pull 3×12, Außenrotation 3×12, Y-Raise 2×12, Serratus (Wall Slides) 2×10.")
