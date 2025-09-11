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
def guardar_registro(consultas, controles, canto, mensajes, llamadas, consultantes):
    today = date.today()
    year, week, _ = today.isocalendar()
    semana = f"{year}-W{week:02d}"

    data = {
        "oficina": st.session_state.username,
        "consultas": consultas,
        "controles": controles,
        "canto": canto,
        "mensajes": mensajes,
        "llamadas": llamadas,
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
    max_consultantes = 0
    for idx, row in df.iterrows():
        consultantes = row.get("consultantes", [])
        if isinstance(consultantes, str):
            try:
                consultantes = ast.literal_eval(consultantes)
            except:
                consultantes = []
        if not isinstance(consultantes, list):
            consultantes = []
        df.at[idx, "consultantes"] = consultantes
        max_consultantes = max(max_consultantes, len(consultantes))

    for i in range(max_consultantes):
        df[f"Consultante{i+1}_Nombre"] = df["consultantes"].apply(
            lambda x: x[i]["nombre"] if i < len(x) else None
        )
        df[f"Consultante{i+1}_Teléfono"] = df["consultantes"].apply(
            lambda x: x[i]["telefono"] if i < len(x) else None
        )

    return df.drop(columns=["consultantes"], errors="ignore")

# -------------------------------
# Mostrar registros con métricas
# -------------------------------
def mostrar_registros(df, titulo):
    st.markdown(f"<div class='big-title'>{titulo}</div>", unsafe_allow_html=True)

    if df.empty:
        st.info("No hay registros aún.")
        return

    df = expandir_consultantes(df)
    st.dataframe(df, use_container_width=True)

    resumen = df.groupby("semana").agg({
        "consultas": "sum",
        "controles": "sum",
        "canto": "sum",
        "mensajes": "sum",
        "llamadas": "sum"
    }).reset_index()
    resumen["ganancia"] = resumen["canto"] / 2

    st.divider()
    st.markdown("### 📈 Resumen por Semana")
    st.table(resumen)

    total_consultas = int(resumen["consultas"].sum())
    total_controles = int(resumen["controles"].sum())
    total_canto = float(resumen["canto"].sum())
    total_mensajes = int(resumen["mensajes"].sum())
    total_llamadas = int(resumen["llamadas"].sum())
    total_ganancia = float(resumen["ganancia"].sum())

    c1, c2, c3 = st.columns(3)
    with c1: metric_card("📋 Total Consultas", total_consultas)
    with c2: metric_card("✅ Total Controles", total_controles)
    with c3: metric_card("🎵 Total Canto", f"${total_canto:,.0f}")

    c4, c5, c6 = st.columns(3)
    with c4: metric_card("💬 Total Mensajes", total_mensajes)
    with c5: metric_card("📞 Total Llamadas", total_llamadas)
    with c6: metric_card("📈 Total Ganancia", f"${total_ganancia:,.0f}")

    return resumen

# -------------------------------
# Mostrar registros de oficina
# -------------------------------
def mostrar_registros_oficina():
    response = supabase.table("registros") \
        .select("*") \
        .eq("oficina", st.session_state.username) \
        .order("fecha_registro", desc=True) \
        .execute()
    df = pd.DataFrame(response.data)
    mostrar_registros(df, "📄 Registros de la Oficina")

# -------------------------------
# Mostrar registros admin
# -------------------------------
def mostrar_registros_admin():
    response = supabase.table("registros") \
        .select("*") \
        .order("fecha_registro", desc=True) \
        .execute()
    df = pd.DataFrame(response.data)

    oficinas = ["Todas"] + sorted(df["oficina"].unique().tolist())
    filtro = st.selectbox("🔎 Filtrar por oficina", oficinas)

    if filtro != "Todas":
        df = df[df["oficina"] == filtro]

    resumen = mostrar_registros(df, "🌍 Dashboard Global")

    if resumen is not None and not resumen.empty:
        st.divider()
        st.markdown("### 📊 Canto por Semana")
        fig = px.bar(resumen, x="semana", y="canto",
                     title="Canto Total por Semana",
                     text="canto", labels={"canto": "Canto ($)"},
                     color="canto", color_continuous_scale="Blues")
        st.plotly_chart(fig, use_container_width=True)

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
                canto = st.number_input("🎵 Canto ($)", min_value=0.0, step=0.1)
                mensajes = st.number_input("💬 Mensajes", min_value=0, step=1)
                llamadas = st.number_input("📞 Llamadas", min_value=0, step=1)

                consultantes = []
                for i in range(consultas):
                    nombre = st.text_input(f"👤 Nombre consultante {i+1}", key=f"nombre_{i}")
                    telefono = st.text_input(f"📱 Teléfono consultante {i+1}", key=f"telefono_{i}")
                    if nombre or telefono:
                        consultantes.append({"nombre": nombre, "telefono": telefono})

                submitted = st.form_submit_button("💾 Guardar Registro")
                if submitted:
                    guardar_registro(consultas, controles, canto, mensajes, llamadas, consultantes)

            mostrar_registros_oficina()
        else:
            mostrar_registros_admin()

if __name__ == "__main__":
    main()
