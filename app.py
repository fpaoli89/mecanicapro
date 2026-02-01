import streamlit as st
import pandas as pd
import uuid

# 1. Configuración obligatoria al inicio
st.set_page_config(page_title="Mecánica Pro", layout="wide")

# 2. Inicialización del estado (Session State)
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- FUNCIONES DE CONTROL ---
def agregar_item(d, c, p):
    if d and p > 0:
        st.session_state.carrito.append({
            "ID": str(len(st.session_state.carrito) + 1),
            "Descripción": d,
            "Cantidad": c,
            "Precio Unit.": p,
            "Subtotal": c * p
        })

def vaciar_carrito():
    st.session_state.carrito = []

# --- INTERFAZ DE USUARIO ---
st.title("🔧 Mecánica Pro")

# Sección de Cliente (Estática)
with st.container(border=True):
    st.subheader("👤 Datos del Cliente")
    col1, col2, col3 = st.columns(3)
    cliente = col1.text_input("Nombre", key="cli_nom")
    vehiculo = col2.text_input("Vehículo", key="cli_veh")
    patente = col3.text_input("Patente", key="cli_pat")

# Sección de Carga (Usamos FORM para evitar el error de removeChild)
st.subheader("🛠️ Detalle del Presupuesto")
with st.form("formulario_carga", clear_on_submit=True):
    c1, c2, c3 = st.columns([3, 1, 1])
    desc_f = c1.text_input("Descripción (Repuesto o Servicio)")
    cant_f = c2.number_input("Cantidad", min_value=1, value=1)
    prec_f = c3.number_input("Precio Unitario", min_value=0.0, step=100.0)
    
    submit = st.form_submit_button("➕ Agregar a la lista")
    if submit:
        agregar_item(desc_f, cant_f, prec_f)
        st.rerun()

# Sección de Visualización (Separada físicamente)
if st.session_state.carrito:
    st.write("---")
    df_carrito = pd.DataFrame(st.session_state.carrito)
    
    # Mostramos los datos de forma simple
    st.dataframe(
        df_carrito, 
        use_container_width=True, 
        hide_index=True,
        key="tabla_presupuesto"
    )
    
    total = df_carrito["Subtotal"].sum()
    st.metric("TOTAL PRESUPUESTO", f"$ {total:,.2f}")

    c_save, c_empty = st.columns([1, 4])
    if c_save.button("💾 Guardar en Excel"):
        st.info("Conectando con Google Sheets...")
        # Aquí irá la lógica de guardado una vez verifiquemos estabilidad
        
    if c_empty.button("🗑️ Vaciar Todo"):
        vaciar_carrito()
        st.rerun()
