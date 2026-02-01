import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Mecánica Pro", layout="wide")

# IMPORTANTE: Cambia esto por tu URL real
URL_SHEET = "https://docs.google.com/spreadsheets/d/TU_ID_AQUÍ/edit"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- INICIALIZAR SESSION STATE ---
if 'carrito_repuestos' not in st.session_state:
    st.session_state.carrito_repuestos = []

st.title("🔧 Mecánica Pro: Sistema de Presupuestos")

# --- FORMULARIO DE CLIENTE ---
with st.container(border=True):
    st.subheader("👤 Datos del Cliente")
    c1, c2, c3 = st.columns(3)
    cliente = c1.text_input("Nombre del Cliente")
    vehiculo = c2.text_input("Vehículo")
    patente = c3.text_input("Patente")

# --- AGREGAR ITEMS ---
st.subheader("🛠️ Detalles del Trabajo")
with st.container(border=True):
    r1, r2, r3 = st.columns([3, 1, 1])
    desc = r1.text_input("Descripción (Repuesto o Servicio)")
    cant = r2.number_input("Cant.", min_value=1, value=1)
    precio = r3.number_input("Precio Unitario", min_value=0.0, step=100.0)
    
    if st.button("➕ Agregar Item"):
        if desc and precio > 0:
            # Añadimos a la lista
            nuevo_item = {
                "descripcion": desc,
                "cantidad": cant,
                "precio": precio,
                "subtotal": cant * precio
            }
            st.session_state.carrito_repuestos.append(nuevo_item)
            st.rerun() # Forzamos refresco limpio para evitar el error de Node
        else:
            st.warning("Escribe descripción y precio.")

# --- LISTA DE TRABAJO ---
if st.session_state.carrito_repuestos:
    st.divider()
    df_items = pd.DataFrame(st.session_state.carrito_repuestos)
    
    # Usamos un contenedor dedicado para la tabla
    with st.container():
        st.table(df_items)
        
        total_general = df_items['subtotal'].sum()
        st.header(f"Total: ${total_general:,.2f}")

        col_save, col_clear = st.columns(2)
        
        if col_save.button("💾 GUARDAR PRESUPUESTO"):
            # Aquí generamos el ID para vincular todo
            id_presupuesto = str(uuid.uuid4())[:8].upper()
            
            # TODO: Lógica de guardado en Google Sheets (Hoja Resumen y Detalles)
            
            st.success(f"✅ Guardado como Presupuesto #{id_presupuesto}")
            st.balloons()
            # No limpiamos el carrito inmediatamente para que el usuario vea el éxito
            
        if col_clear.button("🗑️ Borrar Todo"):
            st.session_state.carrito_repuestos = []
            st.rerun()
