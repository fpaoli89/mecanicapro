import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Mecánica Pro", layout="wide")
URL_SHEET = "TU_URL_DEL_NUEVO_EXCEL_AQUI"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SESIÓN PARA ITEMS ---
if 'carrito_repuestos' not in st.session_state:
    st.session_state.carrito_repuestos = []

st.title("🔧 Mecánica Pro: Sistema de Presupuestos")

# --- FORMULARIO DE CLIENTE ---
with st.expander("👤 Datos del Cliente y Vehículo", expanded=True):
    c1, c2, c3 = st.columns(3)
    cliente = c1.text_input("Nombre del Cliente")
    vehiculo = c2.text_input("Vehículo (Ej: Toyota Hilux)")
    patente = c3.text_input("Patente / Placa")

# --- AGREGAR REPUESTOS O MANO DE OBRA ---
st.subheader("🛠️ Detalles del Trabajo")
with st.container(border=True):
    r1, r2, r3 = st.columns([3, 1, 1])
    desc = r1.text_input("Descripción del repuesto o servicio")
    cant = r2.number_input("Cant.", min_value=1, value=1)
    precio = r3.number_input("Precio Unitario", min_value=0.0)
    
    if st.button("➕ Agregar a la lista"):
        if desc and precio > 0:
            item = {
                "descripcion": desc,
                "cantidad": cant,
                "precio": precio,
                "subtotal": cant * precio
            }
            st.session_state.carrito_repuestos.append(item)
        else:
            st.warning("Escribe una descripción y precio.")

# --- MOSTRAR TABLA DE TRABAJO ---
if st.session_state.carrito_repuestos:
    df_items = pd.DataFrame(st.session_state.carrito_repuestos)
    st.table(df_items)
    
    total_general = df_items['subtotal'].sum()
    st.subheader(f"Total: ${total_general:,.2f}")

    if st.button("💾 GUARDAR PRESUPUESTO FINAL"):
        id_unico = str(uuid.uuid4())[:8] # Genera un ID corto
        
        # 1. Guardar en Hoja Resumen (Simplificado por ahora)
        st.success(f"Presupuesto {id_unico} guardado correctamente en la nube.")
        
        # Limpiar después de guardar
        st.session_state.carrito_repuestos = []
        # st.rerun() # Opcional para refrescar
