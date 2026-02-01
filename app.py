import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# 1. Configuración al principio del todo
st.set_page_config(page_title="Mecánica Pro", layout="wide")

# 2. Inicialización del estado (Session State)
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 3. Función para limpiar el formulario (evita errores de renderizado)
def borrar_todo():
    st.session_state.carrito = []
    st.rerun()

st.title("🔧 Mecánica Pro")

# 4. Datos del Cliente (Usamos claves únicas 'key')
with st.container(border=True):
    st.subheader("👤 Datos del Cliente")
    col1, col2, col3 = st.columns(3)
    cliente = col1.text_input("Nombre", key="input_cliente")
    vehiculo = col2.text_input("Vehículo", key="input_vehiculo")
    patente = col3.text_input("Patente", key="input_patente")

# 5. Agregar Items
st.subheader("🛠️ Detalle del Presupuesto")
with st.container(border=True):
    c1, c2, c3 = st.columns([3, 1, 1])
    desc = c1.text_input("Descripción", key="input_desc")
    cant = c2.number_input("Cant.", min_value=1, value=1, key="input_cant")
    precio = c3.number_input("Precio Unit.", min_value=0.0, step=100.0, key="input_precio")
    
    # El truco: No hacemos rerun aquí adentro, dejamos que el flujo siga
    if st.button("➕ Agregar Item", key="btn_agregar"):
        if desc and precio > 0:
            st.session_state.carrito.append({
                "ID": str(len(st.session_state.carrito) + 1),
                "Descripción": desc,
                "Cantidad": cant,
                "Precio Unit.": precio,
                "Subtotal": cant * precio
            })
            st.rerun()

# 6. Mostrar el carrito de forma estable
if st.session_state.carrito:
    st.divider()
    df_carrito = pd.DataFrame(st.session_state.carrito)
    
    # Usamos dataframe en lugar de table para evitar el error de 'removeChild'
    st.dataframe(df_carrito, use_container_width=True, hide_index=True)
    
    total = df_carrito["Subtotal"].sum()
    st.metric(label="TOTAL A PAGAR", value=f"$ {total:,.2f}")

    col_save, col_del = st.columns([1, 4])
    
    if col_save.button("💾 Guardar", key="btn_guardar"):
        st.success("Guardado exitosamente (Simulado)")
        # Aquí irá la conexión a GSheets
        
    if col_del.button("🗑️ Vaciar", on_click=borrar_todo, key="btn_vaciar"):
        pass # La función borrar_todo hace el trabajo
