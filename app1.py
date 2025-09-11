import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client
from pathlib import Path
import base64

# ===============================
# 🎨 Configuración de la página
# ===============================
st.set_page_config(page_title="📊 Dashboard Oficinas", page_icon="🏢", layout="wide")

# ===============================
# 🔑 Configuración de Supabase
# ===============================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===============================
# 🎨 Fondo y estilos personalizados
# ===============================
def get_base64(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Usa tu archivo de fondo (asegúrate de subirlo a la carpeta del repo)
background_image = Path("1d65cc9ce3375d8fe3a993b90a7d41b6.jpg")
base64_img = get_base64(background_image)

st.markdown(f"""
    <style>
    /* Fondo general */
    .stApp {{
        background: url("data:image/jpg;base64,{base64_img}") no-repeat center center fixed;
        background-size: cover;
        color: #f0f0f0;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: rgba(0,0,0,0.6);
        border-radius: 12px;
    }}

    /* Títulos */
    .big-title {{
        text-align: center;
        font-size: 38px !important;
        color: #f9f9f9;
        font-weight: bold;
        text-shadow: 1px 1px 4px #000;
    }}

    /* Tarjetas */
    .card {{
        background: rgba(255,255,255,0.1);
        padding: 20px;
        border-radius: 16px;
        text-align: center;
        backdrop-filter: blur(8px);
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
        margin-bottom: 10px;
    }}

    .metric-label {{
        font-size: 16px;
        color: #ddd;
    }}
    .metric-value {{
        font-size: 22px;
        font-weight: bold;
        color: #fff;
    }}

    /* Tablas */
    .stDataFrame, .stTable {{
        background: rgba(0,0,0,0.5) !important;
        border-radius: 10px;
        color: #fff;
    }}
    </style>
""", unsafe_allow_html=True)

# ===============================
# ⚙ Inicializar session_state
# ===============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.is_admin = False

# ===============================
# 🔐 Pantalla de login
# ===============================
def login_screen():
    st.markdown("<h1 class='big-title'>🔑 Iniciar Sesión</h1>", unsafe_allow_html=True)

    nombre_login = st.text_input("🏢 Nombre de la Oficina")
    password = st.text_input("🔒 Contraseña (solo admin)", type="password")

    if st.button("Ingresar", use_container_width=True):
        if nombre_login.lower() == "admin":
            if password == st.secrets["ADMIN_PASSWORD"]:
                st.session_state.logged_in = True
                st.session_state.username = "admin"
                st.session_state.is_admin = True
                st.success("✅ Bienvenido Administrador")
            else:
                st.error("❌ Contraseña incorrecta")
        elif nombre_login.strip() != "":
            st.session_state.logged_in = True
            st.session_state.username = nombre_login
            st.session_state.is_admin = False
            st.success(f"✅ Bienvenida oficina {nombre_login}")
        else:
            st.error("⚠ Debes ingresar un nombre de oficina")

# ===============================
# 📝 Formulario (solo oficinas)
# ===============================
def formulario_registro():
    st.markdown("### 📝 Registrar Actividad")

    with st.form("formulario", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            consultas = st.number_input("📋 Número de consultas", min_value=0, step=1)
            ingreso = st.number_input("💰 Ingreso ($)", min_value=0, step=100)
        with col2:
            controles = st.number_input("✅ Número de controles", min_value=0, step=1)

        submit = st.form_submit_button("Guardar Registro")

        if submit:
            today = datetime.date.today()
            iso = today.isocalendar()
            semana_val = f"{iso[0]}-W{iso[1]:02d}"  # Semana automática

            data = {
                "oficina": st.session_state.username,
                "consultas": int(consultas),
                "controles": int(controles),
                "ingreso": float(ingreso),
                "semana": semana_val,
            }

            try:
                supabase.table("registros").insert(data).execute()
                st.success(f"✅ Registro guardado para la oficina **{st.session_state.username}** (semana {semana_val})")
            except Exception as e:
                st.error("❌ Error al guardar en Supabase")
                st.exception(e)

# ===============================
# 📑 Mostrar registros
# ===============================
def mostrar_registros():
    st.markdown("## 📑 Registros")

    if not st.session_state.is_admin:
        response = supabase.table("registros").select("*").eq("oficina", st.session_state.username).execute()
    else:
        response = supabase.table("registros").select("*").execute()

    df = pd.DataFrame(response.data)

    if not df.empty:
        st.dataframe(df, use_container_width=True)

        resumen = df.groupby("semana").agg({
            "consultas": "sum",
            "controles": "sum",
            "ingreso": "sum"
        }).reset_index()
        resumen["ganancia"] = resumen["ingreso"] / 2

        st.markdown("### 📈 Resumen por Semana")
        st.table(resumen)

        total_consultas = int(resumen["consultas"].sum())
        total_controles = int(resumen["controles"].sum())
        total_ingreso = float(resumen["ingreso"].sum())
        total_ganancia = float(resumen["ganancia"].sum())

        col1, col2, col3, col4 = st.columns(4)
        col1.markdown("<div class='card'><div class='metric-label'>📋 Total Consultas</div>"
                      f"<div class='metric-value'>{total_consultas}</div></div>", unsafe_allow_html=True)
        col2.markdown("<div class='card'><div class='metric-label'>✅ Total Controles</div>"
                      f"<div class='metric-value'>{total_controles}</div></div>", unsafe_allow_html=True)
        col3.markdown("<div class='card'><div class='metric-label'>💰 Total Ingreso</div>"
                      f"<div class='metric-value'>${total_ingreso:,.0f}</div></div>", unsafe_allow_html=True)
        col4.markdown("<div class='card'><div class='metric-label'>📈 Total Ganancia</div>"
                      f"<div class='metric-value'>${total_ganancia:,.0f}</div></div>", unsafe_allow_html=True)
    else:
        st.info("No hay registros disponibles.")

# ===============================
# 🚀 Main App
# ===============================
if not st.session_state.logged_in:
    login_screen()
else:
    st.sidebar.markdown(f"### 👤 Oficina: {st.session_state.username}")
    if st.sidebar.button("🚪 Cerrar sesión"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.is_admin = False
        st.experimental_rerun()

    st.markdown("<h1 class='big-title'>📊 Registro de Actividad por Oficina</h1>", unsafe_allow_html=True)

    if not st.session_state.is_admin:
        formulario_registro()

    mostrar_registros()
