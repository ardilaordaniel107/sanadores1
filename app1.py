import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date
import pandas as pd
import plotly.express as px

# -------------------------------
# Configuración de Supabase
# -------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
                st.sidebar.error("❌ Contraseña incorrecta")
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
def guardar_registro(consultas, controles, ingreso):
    # Generar semana automáticamente
    today = date.today()
    year, week, _ = today.isocalendar()
    semana = f"{year}-W{week:02d}"

    data = {
        "oficina": st.session_state.username,
        "consultas": consultas,
        "controles": controles,
        "ingreso": ingreso,
        "semana": semana,
        "fecha_registro": datetime.utcnow().isoformat()
    }
    supabase.table("registros").insert(data).execute()
    st.success(f"✅ Registro guardado (Semana {semana})")

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
    st.subheader(f"📄 Registros de la oficina {st.session_state.username}")

    if registros:
        df = pd.DataFrame(registros)
        st.dataframe(df, use_container_width=True)

        # Resumen por semana
        resumen = df.groupby("semana").agg({
            "consultas": "sum",
            "controles": "sum",
            "ingreso": "sum"
        }).reset_index()
        resumen["ganancia"] = resumen["ingreso"] / 2

        st.markdown("### 📈 Resumen por Semana")
        st.table(resumen)

        # Dashboard
        total_consultas = int(resumen["consultas"].sum())
        total_controles = int(resumen["controles"].sum())
        total_ingreso = float(resumen["ingreso"].sum())
        total_ganancia = float(resumen["ganancia"].sum())

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📋 Total Consultas", total_consultas)
        c2.metric("✅ Total Controles", total_controles)
        c3.metric("💰 Total Ingreso", f"${total_ingreso:,.0f}")
        c4.metric("📈 Total Ganancia", f"${total_ganancia:,.0f}")
    else:
        st.info("No hay registros aún.")

# -------------------------------
# Mostrar registros globales (Admin con filtro)
# -------------------------------
def mostrar_registros_admin():
    response = supabase.table("registros") \
        .select("*") \
        .order("fecha_registro", desc=True) \
        .execute()

    registros = response.data
    st.subheader("🌍 Registros globales")

    if registros:
        df = pd.DataFrame(registros)

        # --- Filtro por oficina ---
        oficinas = ["Todas"] + sorted(df["oficina"].unique().tolist())
        filtro = st.selectbox("🔎 Filtrar por oficina", oficinas)

        if filtro != "Todas":
            df = df[df["oficina"] == filtro]

        st.dataframe(df, use_container_width=True)

        # Resumen por semana
        resumen = df.groupby("semana").agg({
            "consultas": "sum",
            "controles": "sum",
            "ingreso": "sum"
        }).reset_index()
        resumen["ganancia"] = resumen["ingreso"] / 2

        st.markdown("### 📊 Resumen por Semana")
        st.table(resumen)

        # Dashboard
        total_consultas = int(resumen["consultas"].sum())
        total_controles = int(resumen["controles"].sum())
        total_ingreso = float(resumen["ingreso"].sum())
        total_ganancia = float(resumen["ganancia"].sum())

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📋 Total Consultas", total_consultas)
        c2.metric("✅ Total Controles", total_controles)
        c3.metric("💰 Total Ingreso", f"${total_ingreso:,.0f}")
        c4.metric("📈 Total Ganancia", f"${total_ganancia:,.0f}")

        # Gráfico de ingresos
        st.markdown("### 📊 Ingresos por Semana")
        fig = px.bar(resumen, x="semana", y="ingreso",
                     title="Ingresos Totales por Semana",
                     text="ingreso", labels={"ingreso": "Ingreso ($)"})
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No hay registros aún.")

# -------------------------------
# Pantalla principal
# -------------------------------
def main():
    st.set_page_config(page_title="App Sanadores", layout="wide")

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

        st.title("📊 Panel de Registros")

        if not st.session_state.is_admin:
            with st.form("formulario"):
                consultas = st.number_input("Número de consultas", min_value=0, step=1)
                controles = st.number_input("Número de controles", min_value=0, step=1)
                ingreso = st.number_input("Ingreso ($)", min_value=0.0, step=0.1)

                submitted = st.form_submit_button("Guardar Registro")
                if submitted:
                    guardar_registro(consultas, controles, ingreso)

            mostrar_registros_oficina()
        else:
            mostrar_registros_admin()

# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    main()
