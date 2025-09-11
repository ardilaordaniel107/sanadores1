import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import datetime

# -----------------------------
# Base de datos
# -----------------------------
def init_db():
    conn = sqlite3.connect("registros.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oficina TEXT,
            consultas INTEGER,
            controles INTEGER,
            mensajes INTEGER,
            llamadas INTEGER,
            canto REAL,
            semana TEXT,
            fecha_registro TEXT,
            consultantes TEXT -- guardamos JSON
        )
    """)
    conn.commit()
    conn.close()

def guardar_registro(oficina, consultas, controles, mensajes, llamadas, canto, semana, consultantes):
    conn = sqlite3.connect("registros.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO registros (oficina, consultas, controles, mensajes, llamadas, canto, semana, fecha_registro, consultantes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        oficina,
        consultas,
        controles,
        mensajes,
        llamadas,
        canto,
        semana,
        datetime.utcnow().isoformat(),
        json.dumps(consultantes)  # Guardamos lista como JSON
    ))
    conn.commit()
    conn.close()

def obtener_registros():
    conn = sqlite3.connect("registros.db")
    df = pd.read_sql_query("SELECT * FROM registros", conn)
    conn.close()
    return df

# -----------------------------
# Expansión de consultantes
# -----------------------------
def expandir_consultantes(df):
    if "consultantes" not in df.columns:
        return df
    
    consultores_expandidos = []
    for i, row in df.iterrows():
        try:
            consultantes = json.loads(row["consultantes"])
            fila = row.drop("consultantes").to_dict()
            for j, c in enumerate(consultantes, start=1):
                fila[f"Consultante{j}_Nombre"] = c.get("nombre", "")
                fila[f"Consultante{j}_Telefono"] = c.get("telefono", "")
            consultores_expandidos.append(fila)
        except:
            consultores_expandidos.append(row.to_dict())
    return pd.DataFrame(consultores_expandidos)

# -----------------------------
# Interfaz Streamlit
# -----------------------------
def main():
    st.set_page_config(page_title="Gestión de Oficinas", layout="wide")
    init_db()

    st.title("📊 Sistema de Registros")

    # Formulario
    with st.form("registro_form"):
        oficina = st.text_input("Oficina / Usuario")
        consultas = st.number_input("Consultas", min_value=0, value=0)
        controles = st.number_input("Controles", min_value=0, value=0)
        mensajes = st.number_input("Mensajes", min_value=0, value=0)
        llamadas = st.number_input("Llamadas", min_value=0, value=0)
        canto = st.number_input("Canto", min_value=0.0, value=0.0)

        semana = datetime.utcnow().strftime("%Y-W%U")

        st.markdown("### 👥 Consultantes")
        consultantes = []
        num_consultantes = st.number_input("Número de consultantes", min_value=1, value=1)
        for i in range(num_consultantes):
            nombre = st.text_input(f"Consultante {i+1} - Nombre", key=f"nombre{i}")
            telefono = st.text_input(f"Consultante {i+1} - Teléfono", key=f"tel{i}")
            consultantes.append({"nombre": nombre, "telefono": telefono})

        submitted = st.form_submit_button("💾 Guardar Registro")
        if submitted:
            guardar_registro(oficina, consultas, controles, mensajes, llamadas, canto, semana, consultantes)
            st.success(f"✅ Registro guardado (Semana {semana})")

    # Mostrar registros
    st.subheader("📑 Registros de la Oficina")
    df = obtener_registros()
    if not df.empty:
        df_expandido = expandir_consultantes(df)
        st.dataframe(df_expandido, use_container_width=True)

        # Métricas
        st.subheader("📊 Resumen por Semana")
        resumen = df.groupby("semana").agg({
            "consultas": "sum",
            "controles": "sum",
            "mensajes": "sum",
            "llamadas": "sum",
            "canto": "sum"
        }).reset_index()
        resumen["ganancia"] = resumen["canto"] / 2

        st.dataframe(resumen, use_container_width=True)

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("📝 Total Consultas", int(df["consultas"].sum()))
        with col2:
            st.metric("✅ Total Controles", int(df["controles"].sum()))
        with col3:
            st.metric("📩 Total Mensajes", int(df["mensajes"].sum()))
        with col4:
            st.metric("📞 Total Llamadas", int(df["llamadas"].sum()))
        with col5:
            st.metric("🎵 Total Canto", f"${df['canto'].sum():,.0f}")
        with col6:
            st.metric("💵 Total Ganancia", f"${(df['canto'].sum()/2):,.0f}")

if __name__ == "__main__":
    main()
