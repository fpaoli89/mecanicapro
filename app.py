import streamlit as st
import pandas as pd

# 1. Configuración de página
st.set_page_config(page_title="Mecanica Pro", layout="centered")

# 2. Inicializar el carrito en la sesión
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 3. FUNCIONES (Separar la lógica de la interfaz ayuda a evitar errores de Node)
def agregar_a_lista():
    # Obtenemos los datos de los inputs usando sus claves (keys)
    d = st.session_state.temp_desc
    c = st.session_state.temp_cant
    p = st.session_state.temp_prec
    
    if d and p > 0:
        st.session_state.carrito.append({
            "Descripción": d,
            "Cantidad": c,
            "Precio": p,
            "Subtotal": c * p
        })
    # Al terminar la función, Streamlit limpia los inputs automáticamente por el clear_on_submit

# --- INTERFAZ ---
st.title("🔧 Mecánica Pro")

# FORMULARIO DE CLIENTE (Simple, sin columnas para máxima estabilidad)
with st.container(border=True):
    st.text_input("Nombre del Cliente", key="cli_nombre")
    st.text_input("Vehículo y Patente", key="cli_vehiculo")

st.write("### 🛠️ Agregar Trabajo o Repuesto")

# FORMULARIO DE CARGA CON KEY ÚNICA
with st.form(key="form_trabajo", clear_on_submit=True):
    st.text_input("Descripción del trabajo/repuesto", key="temp_desc")
    st.number_input("Cantidad", min_value=1, value=1, key="temp_cant")
    st.number_input("Precio Unitario", min_value=0.0, step=100.0, key="temp_prec")
    
    # El botón llama a la función de arriba
    submit = st.form_submit_button("Añadir a la lista", on_click=agregar_a_lista)

# VISUALIZACIÓN (Solo si hay items)
if st.session_state.carrito:
    st.write("---")
    st.write("### 📋 Resumen del Presupuesto")
    
    # Convertimos a DataFrame para mostrarlo
    df = pd.DataFrame(st.session_state.carrito)
    
    # IMPORTANTE: Usamos st.write(df) que es la forma más básica y estable de mostrar tablas
    st.write(df)
    
    total = sum(item['Subtotal'] for item in st.session_state.carrito)
    st.divider()
    st.system_note = f"**TOTAL: ${total:,.2f}**"
    st.markdown(f"## TOTAL: ${total:,.2f}")

    if st.button("🗑️ Vaciar y empezar de nuevo"):
        st.session_state.carrito = []
        st.rerun()
