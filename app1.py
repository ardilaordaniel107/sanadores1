import streamlit as st
from supabase import create_client
import base64
import os
import datetime

# -----------------------------
# CONFIGURACIÓN SUPABASE
# -----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# FONDO PERSONALIZADO
# -----------------------------
def get_base64(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

background_image = os.path.join("assets", "fondo.jpg")  # asegúrate de que exista en tu repo
base64_img = get_base64(background_image)

page_bg = f"""
<style>
.stApp {{
  background-image: url("data:image/jpg;base64,{base64_img}");
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
  color: white;
}}
</style>
"""
st.markdown(page_bg, unsafe_allow_html=True)

# -----------------------------
# LOGIN
# -----------------------------
if "username" not in st.session_state:
    st.session_state.username = None

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if not st.session_state.username:
    st.sidebar.title("🔑 Iniciar sesión")

    user = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Entrar"):
        if password == ADMIN_PASSWORD:
            st.session_state.username = user
            st.session_state.is_admin = True
            st.sidebar.success("Conectado como Admin")
        else:
            st.session_state.username = user
            st.session_state.is_admin = False
            st.sidebar.success(f"Conectado como {user}")

    st.stop()

# -----------------------------
# DASHBOARD
# -----------------------------
st.sidebar.title(f"👤 Oficina: {st.session_state.username}")
if st.sidebar.button("Cerrar sesión"):
    st.session_state.username = None
    st.experimental_rerun()

st.title("📊 Dashboard de Registros")

# FORMULARIO
with st.form("registro_form"):
    consultas = st.number_input("📌 Número de consultas", min_value=0, step=1)
    controles = st.number_input("🩺 Número de controles", min_value=0, step=1)
    ingreso = st.number_input("💰 Ingreso ($)", min_value=0, step=1)

    # semana automática
    semana_actual = datetime.date.today().isocalendar()[1]
    anio_actual = datetime.date.today().year
    semana = f"{anio_actual}-W{semana_actual}"

    st.write(f"📅 Semana detectada automáticamente: **{semana}**")

    submitted = st.form_submit_button("Guardar Registro")

if submitted:
    data = {
        "oficina": st.session_state.username,
        "consultas": consultas,
        "controles": controles,
        "ingreso": ingreso,
        "semana": semana,
        "fecha_registro": datetime.datetime.now().isoformat()
    }
    supabase.table("registros").insert(data).execute()
    st.success("✅ Registro guardado con éxito")

# -----------------------------
# MOSTRAR REGISTROS
# -----------------------------
st.header("📂 Registros")

if st.session_state.is_admin:
    response = supabase.table("registros").select("*").execute()
else:
    response = supabase.table("registros").select("*").eq("oficina", st.session_state.username).execute()

if response.data:
    st.dataframe(response.data)
else:
    st.info("No hay registros aún.")
