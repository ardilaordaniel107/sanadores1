import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import ast

# -------------------------------
# Configuración
# -------------------------------
st.set_page_config(page_title="App Sanadores", page_icon="🌿", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------------
# Estilos CSS personalizados
# -------------------------------
st.markdown("""
    <style>
    .big-title {
        text-align: center;
        font-size: 36px !important;
        color: #2c3e50;
        font-weight: bold;
    }
    .card {
        background: #f9f9f9;
        padding: 20px;
        border-radius: 16px;
        text-align: center;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
    }
    .metric-label {
        font-size: 16px;
        color: #555;
    }
    .metric-value {
        font-size: 22px;
        font-weight: bold;
        color: #2c3e50;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------
# Login
# -------------------------------
def login():
    st.sidebar.title("🔑 Iniciar sesión")
    username = st.sidebar.text_input("Usuario / Oficina")
    password = st.sidebar.text_input("Contraseña (solo admin)", type="password")

    if st.sidebar.button("Entrar"):
        if username.lower() == "admin":
            if password == st.secrets["ADMIN_PASSWORD"]:
                st.session_state.logged_in = True
                st.session_state.username = "admin"
                st.session_state.is_admin = True
                st.sidebar.success("✅ Bienvenido, Administrador")
            else:
                st.session_state.logged_in = False
                st.session_state.username = None
                st.session_state.is_admin = False
                st.sidebar.error("❌ Contraseña incorrecta. No puedes acceder como admin.")
        else:
            if username.strip() == "":
                st.sidebar.error("Debes ingresar un nombre de oficina")
            else:
                st.session_state.logged_in = True
                st.session_state.username = username.strip()
                st.session_state.is_admin = False
                st.sidebar.success(f"✅ Bienvenido, oficina {username}")

# -------------------------------
# Guardar un registro
# -------------------------------
def guardar_registro(consultas, controles, canto, consultantes):
    today = date.today()
    year, week, _ = today.isocalendar()
    semana = f"{year}-W{week:02d}"

    data = {
        "oficina": st.session_state.username,
        "consultas": consultas,
        "controles": controles,
        "canto": canto,
        "consultantes": consultantes,
        "semana": semana,
        "fecha_registro": datetime.utcnow().isoformat()
    }
    supabase.table("registros").insert(data).execute()
    st.success(f"✅ Registro guardado (Semana {semana})")

# -------------------------------
# Tarjetas métricas custom
# -------------------------------
def metric_card(label, value):
    st.markdown(f"""
        <div class="card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# -------------------------------
# Expandir consultantes
# -------------------------------
def expandir_consultantes(df):
    if "consultantes" not in df.columns:
        return df

    consultantes_limpios = []
    max_consultantes = 0

    for raw in df["consultantes"]:
        if isinstance(raw, str):
            try:
                parsed = ast.literal_eval(raw)
            except:
                parsed = []
        elif isinstance(raw, list):
            parsed = raw
        else:
            parsed = []

        if not isinstance(parsed, list):
            parsed = []

        consultantes_limpios.append(parsed)
        max_consultantes = max(max_consultantes, len(parsed))

    df = df.copy()
    df["consultantes"] = consultantes_limpios

    for i in range(max_consultantes):
        df[f"Consultante{i+1}_Nombre"] = df["consultantes"].apply(
            lambda x: x[i]["nombre"] if i < len(x) and "nombre" in x[i] else None
        )
        df[f"Consultante{i+1}_Teléfono"] = df["consultantes"].apply(
            lambda x: x[i]["telefono"] if i < len(x) and "telefono" in x[i] else None
        )

    return df.drop(columns=["consultantes"], errors="ignore")

# -------------------------------
# Mostrar registros de oficina
# -------------------------------
def mostrar_registros_oficina():
    response = supabase.table("registros") \
        .select("*") \
        .eq("oficina", st.session_state.username) \
        .order("fecha_registro", desc=True) \
        .execute()

    registros = response.data
    st.markdown("<div class='big-title'>📄 Registros de la Oficina</div>", unsafe_allow_html=True)

    if registros:
        df = pd.DataFrame(registros)
        df = expandir_consultantes(df)
        st.dataframe(df, use_container_width=True)

        resumen = df.groupby("semana").agg({
            "consultas": "sum",
            "controles": "sum",
            "canto": "sum"
        }).reset_index()
        resumen["ganancia"] = resumen["canto"] / 2

        st.divider()
        st.markdown("### 📈 Resumen por Semana")
        st.table(resumen)

        total_consultas = int(resumen["consultas"].sum())
        total_controles = int(resumen["controles"].sum())
        total_canto = float(resumen["canto"].sum())
        total_ganancia = float(resumen["ganancia"].sum())

        c1, c2, c3, c4 = st.columns(4)
        with c1: metric_card("📋 Total Consultas", total_consultas)
        with c2: metric_card("✅ Total Controles", total_controles)
        with c3: metric_card("💰 Total Canto", f"${total_canto:,.0f}")
        with c4: metric_card("📈 Total Ganancia", f"${total_ganancia:,.0f}")
    else:
        st.info("No hay registros aún.")

# -------------------------------
# Mostrar registros admin
# -------------------------------
def mostrar_registros_admin():
    response = supabase.table("registros") \
        .select("*") \
        .order("fecha_registro", desc=True) \
        .execute()

    registros = response.data
    st.markdown("<div class='big-title'>🌍 Dashboard Global</div>", unsafe_allow_html=True)

    if registros:
        df = pd.DataFrame(registros)
        df = expandir_consultantes(df)

        oficinas = ["Todas"] + sorted(df["oficina"].unique().tolist())
        filtro = st.selectbox("🔎 Filtrar por oficina", oficinas)

        if filtro != "Todas":
            df = df[df["oficina"] == filtro]

        st.dataframe(df, use_container_width=True)

        resumen = df.groupby("semana").agg({
            "consultas": "sum",
            "controles": "sum",
            "canto": "sum"
        }).reset_index()
        resumen["ganancia"] = resumen["canto"] / 2

        st.divider()
        st.markdown("### 📊 Resumen por Semana")
        st.table(resumen)

        total_consultas = int(resumen["consultas"].sum())
        total_controles = int(resumen["controles"].sum())
        total_canto = float(resumen["canto"].sum())
        total_ganancia = float(resumen["ganancia"].sum())

        c1, c2, c3, c4 = st.columns(4)
        with c1: metric_card("📋 Total Consultas", total_consultas)
        with c2: metric_card("✅ Total Controles", total_controles)
        with c3: metric_card("💰 Total Canto", f"${total_canto:,.0f}")
        with c4: metric_card("📈 Total Ganancia", f"${total_ganancia:,.0f}")

        st.divider()
        st.markdown("### 📊 Cantos por Semana")
        fig = px.bar(resumen, x="semana", y="canto",
                     title="Cantos Totales por Semana",
                     text="canto", labels={"canto": "Canto ($)"},
                     color="canto", color_continuous_scale="Blues")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No hay registros aún.")

# -------------------------------
# Main
# -------------------------------
def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.is_admin = False

    if not st.session_state.logged_in:
        login()
    else:
        st.sidebar.markdown(f"👤 Usuario: **{st.session_state.username}**")
        if st.sidebar.button("Cerrar sesión"):
            st.session_state.logged_in = False
            st.rerun()

        st.markdown("<div class='big-title'>📊 Panel de Registros</div>", unsafe_allow_html=True)

        if not st.session_state.is_admin:
            with st.form("formulario"):
                consultas = st.number_input("📋 Número de consultas", min_value=0, step=1)
                controles = st.number_input("✅ Número de controles", min_value=0, step=1)
                canto = st.number_input("💰 Canto ($)", min_value=0.0, step=0.1)

                consultantes = []
                for i in range(int(consultas)):
                    st.markdown(f"**👤 Consultante {i+1}**")
                    nombre = st.text_input(f"Nombre del consultante {i+1}", key=f"nombre_{i}")
                    telefono = st.text_input(f"Teléfono del consultante {i+1}", key=f"telefono_{i}")
                    consultantes.append({"nombre": nombre, "telefono": telefono})

                submitted = st.form_submit_button("💾 Guardar Registro")
                if submitted:
                    guardar_registro(consultas, controles, canto, consultantes)

            mostrar_registros_oficina()
        else:
            mostrar_registros_admin()

if __name__ == "__main__":
    main()
