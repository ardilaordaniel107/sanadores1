import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# -------------------------------
# Configuración de Supabase
# -------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------------
# Login básico (usuario = oficina)
# -------------------------------
def login():
    st.sidebar.title("🔑 Iniciar sesión")
    username = st.sidebar.text_input("Oficina", "")
    if st.sidebar.button("Entrar"):
        if username.strip() == "":
            st.sidebar.error("Debes ingresar un nombre de oficina")
        else:
            st.session_state.logged_in = True
            st.session_state.username = username.strip()

# -------------------------------
# Guardar un registro en la DB
# -------------------------------
def guardar_registro(consultas, controles, ingreso, semana):
    data = {
        "oficina": st.session_state.username,
        "consultas": consultas,
        "controles": controles,
        "ingreso": ingreso,
        "semana": semana,
        "fecha_registro": datetime.utcnow().isoformat()
    }
    supabase.table("registros").insert(data).execute()
    st.success("✅ Registro guardado correctamente")

# -------------------------------
# Mostrar registros de la oficina
# -------------------------------
def mostrar_registros():
    response = supabase.table("registros") \
        .select("*") \
        .eq("oficina", st.session_state.username) \
        .order("fecha_registro", desc=True) \
        .execute()

    registros = response.data
    if registros:
        st.subheader("📄 Registros")
        st.dataframe(registros)
    else:
        st.info("No hay registros aún.")

# -------------------------------
# Pantalla principal
# -------------------------------
def main():
    st.set_page_config(page_title="App Sanadores", layout="wide")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login()
    else:
        st.sidebar.markdown(f"👤 Oficina: **{st.session_state.username}**")
        if st.sidebar.button("Cerrar sesión"):
            st.session_state.logged_in = False
            st.rerun()

        st.title("📊 Panel de Registros")

        with st.form("formulario"):
            consultas = st.number_input("Número de consultas", min_value=0, step=1)
            controles = st.number_input("Número de controles", min_value=0, step=1)
            ingreso = st.number_input("Ingreso ($)", min_value=0.0, step=0.1)
            semana = st.text_input("Semana (ej: 2025-W36)", "")

            submitted = st.form_submit_button("Guardar Registro")
            if submitted:
                if semana.strip() == "":
                    st.error("Debes ingresar la semana")
                else:
                    guardar_registro(consultas, controles, ingreso, semana)

        mostrar_registros()

# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    main()
