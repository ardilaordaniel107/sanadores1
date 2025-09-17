import streamlit as st
from supabase import create_client, Client
from datetime import date
import pandas as pd
import plotly.express as px

# -------------------------------
# Configuración
# -------------------------------
st.set_page_config(page_title="App Sanadores", page_icon="🌿", layout="wide")

# Asegúrate de definir estos secretos en Streamlit (o en .streamlit/secrets.toml localmente)
# SUPABASE_URL, SUPABASE_KEY, ADMIN_PASSWORD
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
        color: #f1f1f1;
        font-weight: bold;
    }
    .card {
        background: #1e1e1e;
        padding: 20px;
        border-radius: 16px;
        text-align: center;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.3);
    }
    .metric-label {
        font-size: 16px;
        color: #bbb;
    }
    .metric-value {
        font-size: 22px;
        font-weight: bold;
        color: #fff;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------
# Helpers
# -------------------------------
def parse_consultantes_texto(texto: str):
    """
    A partir del texto del textarea, devuelve una lista de líneas limpias.
    Permite separar por saltos de línea o por comas.
    """
    if not texto:
        return []
    # Convertir comas en saltos para normalizar y luego splitlines
    normalized = texto.replace(",", "\n")
    lines = [ln.strip() for ln in normalized.splitlines() if ln.strip()]
    return lines

def metric_card(label, value):
    st.markdown(f"""
        <div class="card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# -------------------------------
# Login
# -------------------------------
def login():
    st.sidebar.title("🔑 Iniciar sesión")
    username = st.sidebar.text_input("Usuario / Oficina")
    password = st.sidebar.text_input("Contraseña (solo admin)", type="password")

    if st.sidebar.button("Entrar"):
        if username.strip().lower() == "admin":
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
                st.sidebar.success(f"✅ Bienvenido, oficina {username.strip()}")

# -------------------------------
# Guardar registro (robusta y con debug)
# -------------------------------
def guardar_registro(consultas, controles, mensajes, llamadas, canto, consultantes_texto):
    # Validación previa de sesión
    if "username" not in st.session_state or not st.session_state.username:
        st.error("⚠️ No hay usuario en sesión. Inicia sesión primero.")
        return

    # Normalizar fecha
    today = date.today()
    fecha = today.strftime("%d-%m-%Y")  # mantiene el formato actual del app

    # Convertir/castear valores numéricos con fallback
    try:
        consultas_val = int(consultas) if consultas is not None else 0
        controles_val = int(controles) if controles is not None else 0
        mensajes_val = int(mensajes) if mensajes is not None else 0
        llamadas_val = int(llamadas) if llamadas is not None else 0
        canto_val = float(canto) if canto is not None else 0.0
    except Exception as e:
        st.error(f"⚠️ Error al convertir valores numéricos: {e}")
        return

    # Preparar registro (NO incluir fecha_registro para dejar que Postgres use DEFAULT now())
    registro = {
        "oficina": st.session_state.username,
        "consultas": consultas_val,
        "controles": controles_val,
        "mensajes": mensajes_val,
        "llamadas": llamadas_val,
        "canto": canto_val,
        "fecha": fecha
    }

    # DEBUG: mostrar lo que se va a enviar
    st.write("🛠 DEBUG → Registro a insertar en 'registros':")
    st.json(registro)

    try:
        # Insert registro
        response = supabase.table("registros").insert(registro).execute()
        st.write("📥 Respuesta Supabase (registros):", response)

        if not getattr(response, "data", None):
            st.error("❌ La API no devolvió data tras el INSERT. Revisa el esquema en Supabase.")
            return

        registro_id = response.data[0]["id"]

        # Insertar consultantes (si hay)
        consultantes_list = parse_consultantes_texto(consultantes_texto)
        if consultantes_list:
            payload = [{"registro_id": registro_id, "detalle": c} for c in consultantes_list]
            try:
                resp_cons = supabase.table("consultantes").insert(payload).execute()
                st.write("📥 Respuesta Supabase (consultantes):", resp_cons)
            except Exception as e:
                st.error(f"⚠️ Error al guardar consultantes: {e}")
                st.write("Payload consultantes:", payload)

        st.success(f"✅ Registro guardado ({fecha})")

    except Exception as e:
        st.error(f"❌ Error al guardar el registro: {e}")
        st.write("Registro que se intentó enviar:", registro)

# -------------------------------
# Mostrar registros de oficina
# -------------------------------
def mostrar_registros_oficina():
    try:
        registros_resp = supabase.table("registros").select("*").eq("oficina", st.session_state.username).order("fecha_registro", desc=True).execute()
        registros = registros_resp.data or []
    except Exception as e:
        st.error(f"❌ Error al obtener registros: {e}")
        return

    st.markdown("<div class='big-title'>📄 Registros de la Oficina</div>", unsafe_allow_html=True)

    if registros:
        df = pd.DataFrame(registros)

        # Traer consultantes y unirlos al DataFrame
        try:
            consultantes = supabase.table("consultantes").select("*").execute().data or []
            df_cons = pd.DataFrame(consultantes)
        except Exception as e:
            st.error(f"❌ Error al obtener consultantes: {e}")
            df_cons = pd.DataFrame([])

        if not df_cons.empty:
            df = df.merge(
                df_cons.groupby("registro_id")["detalle"].apply(lambda x: " | ".join(x)).reset_index(),
                left_on="id", right_on="registro_id", how="left"
            )
            df.drop(columns=["registro_id"], inplace=True, errors="ignore")
            df.rename(columns={"detalle": "consultantes"}, inplace=True)

        st.dataframe(df, use_container_width=True)

        resumen = df.groupby("fecha").agg({
            "consultas": "sum",
            "controles": "sum",
            "mensajes": "sum",
            "llamadas": "sum",
            "canto": "sum"
        }).reset_index()
        resumen["ganancia"] = resumen["canto"] / 2

        st.divider()
        st.markdown("### 📈 Resumen por Día")
        st.table(resumen)

        total_consultas = int(resumen["consultas"].sum())
        total_controles = int(resumen["controles"].sum())
        total_mensajes = int(resumen["mensajes"].sum())
        total_llamadas = int(resumen["llamadas"].sum())
        total_canto = float(resumen["canto"].sum())
        total_ganancia = float(resumen["ganancia"].sum())

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1: metric_card("📋 Total Consultas", total_consultas)
        with c2: metric_card("✅ Total Controles", total_controles)
        with c3: metric_card("💬 Total Mensajes", total_mensajes)
        with c4: metric_card("📞 Total Llamadas", total_llamadas)
        with c5: metric_card("🎶 Total Canto", f"${total_canto:,.0f}")
        with c6: metric_card("📈 Total Ganancia", f"${total_ganancia:,.0f}")
    else:
        st.info("No hay registros aún.")

# -------------------------------
# Mostrar registros admin
# -------------------------------
def mostrar_registros_admin():
    try:
        registros_resp = supabase.table("registros").select("*").order("fecha_registro", desc=True).execute()
        registros = registros_resp.data or []
    except Exception as e:
        st.error(f"❌ Error al obtener registros: {e}")
        return

    st.markdown("<div class='big-title'>🌍 Dashboard Global</div>", unsafe_allow_html=True)

    if registros:
        df = pd.DataFrame(registros)

        # Traer consultantes y unirlos al DataFrame
        try:
            consultantes = supabase.table("consultantes").select("*").execute().data or []
            df_cons = pd.DataFrame(consultantes)
        except Exception as e:
            st.error(f"❌ Error al obtener consultantes: {e}")
            df_cons = pd.DataFrame([])

        if not df_cons.empty:
            df = df.merge(
                df_cons.groupby("registro_id")["detalle"].apply(lambda x: " | ".join(x)).reset_index(),
                left_on="id", right_on="registro_id", how="left"
            )
            df.drop(columns=["registro_id"], inplace=True, errors="ignore")
            df.rename(columns={"detalle": "consultantes"}, inplace=True)

        oficinas = ["Todas"] + sorted(df["oficina"].unique().tolist())
        filtro = st.selectbox("🔎 Filtrar por oficina", oficinas)

        if filtro != "Todas":
            df = df[df["oficina"] == filtro]

        st.dataframe(df, use_container_width=True)

        resumen = df.groupby("fecha").agg({
            "consultas": "sum",
            "controles": "sum",
            "mensajes": "sum",
            "llamadas": "sum",
            "canto": "sum"
        }).reset_index()
        resumen["ganancia"] = resumen["canto"] / 2

        st.divider()
        st.markdown("### 📊 Resumen por Día")
        st.table(resumen)

        total_consultas = int(resumen["consultas"].sum())
        total_controles = int(resumen["controles"].sum())
        total_mensajes = int(resumen["mensajes"].sum())
        total_llamadas = int(resumen["llamadas"].sum())
        total_canto = float(resumen["canto"].sum())
        total_ganancia = float(resumen["ganancia"].sum())

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1: metric_card("📋 Total Consultas", total_consultas)
        with c2: metric_card("✅ Total Controles", total_controles)
        with c3: metric_card("💬 Total Mensajes", total_mensajes)
        with c4: metric_card("📞 Total Llamadas", total_llamadas)
        with c5: metric_card("🎶 Total Canto", f"${total_canto:,.0f}")
        with c6: metric_card("📈 Total Ganancia", f"${total_ganancia:,.0f}")

        st.divider()
        st.markdown("### 📊 Canto por Día")
        fig = px.bar(resumen, x="fecha", y="canto",
                     title="Canto Total por Día",
                     text="canto", labels={"canto": "Canto ($)"},
                     color="canto", color_continuous_scale="Blues")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay registros aún.")

# -------------------------------
# Nueva función: Ver registros con consultantes
# -------------------------------
def obtener_registros():
    try:
        registros_resp = supabase.table("registros").select("*").order("fecha_registro", desc=True).execute()
        registros = registros_resp.data or []

        if not registros:
            st.info("ℹ️ No hay registros disponibles.")
            return

        consultantes_resp = supabase.table("consultantes").select("*").execute()
        consultantes = consultantes_resp.data or []

        consultantes_map = {}
        for c in consultantes:
            rid = c["registro_id"]
            consultantes_map.setdefault(rid, []).append(c["detalle"])

        st.markdown("<div class='big-title'>📖 Registros Detallados</div>", unsafe_allow_html=True)

        for reg in registros:
            st.markdown("---")
            st.subheader(f"📌 Registro ID: {reg['id']} - Oficina: {reg['oficina']}")
            st.write(f"🗓️ Fecha: {reg['fecha']}")
            st.write(f"🔢 Consultas: {reg['consultas']}, Controles: {reg['controles']}, "
                     f"Mensajes: {reg['mensajes']}, Llamadas: {reg['llamadas']}, Canto: {reg['canto']}")
            st.write(f"⏰ Registrado en: {reg.get('fecha_registro')}")

            detalles = consultantes_map.get(reg["id"], [])
            if detalles:
                st.write("👥 Consultantes:")
                for d in detalles:
                    st.write(f"- {d}")
            else:
                st.write("👤 No se registraron consultantes.")
    except Exception as e:
        st.error(f"❌ Error al obtener registros: {e}")

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
            with st.form("form_registro"):
                consultas = st.number_input("📋 Consultas", min_value=0, step=1)
                controles = st.number_input("✅ Controles", min_value=0, step=1)
                mensajes = st.number_input("💬 Mensajes", min_value=0, step=1)
                llamadas = st.number_input("📞 Llamadas", min_value=0, step=1)
                canto = st.number_input("🎶 Canto ($)", min_value=0.0, step=0.1)

                consultantes_texto = st.text_area("👥 Consultantes (nombre, teléfono, etc.)",
                                                  placeholder="Ej: Juan - 3123123\nMaría - 987654\nTambién acepta coma separada: juan, maria")

                submitted = st.form_submit_button("💾 Guardar Registro")
                if submitted:
                    guardar_registro(consultas, controles, mensajes, llamadas, canto, consultantes_texto)

            mostrar_registros_oficina()

            st.divider()
            if st.button("📖 Ver registros detallados"):
                obtener_registros()
        else:
            mostrar_registros_admin()

            st.divider()
            if st.button("📖 Ver registros detallados"):
                obtener_registros()

if __name__ == "__main__":
    main()
