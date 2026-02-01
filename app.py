import streamlit as st

# 1. Configuración de página - Estilo minimalista para evitar errores
st.set_page_config(page_title="Mecanica Pro", layout="centered")

# 2. Inicializar el acumulador de texto si no existe
if 'resumen_texto' not in st.session_state:
    st.session_state.resumen_texto = ""
if 'total_acumulado' not in st.session_state:
    st.session_state.total_acumulado = 0.0

# --- FUNCIONES ---
def procesar_item():
    d = st.session_state.temp_desc
    c = st.session_state.temp_cant
    p = st.session_state.temp_prec
    
    if d and p > 0:
        subtotal = c * p
        # Creamos una línea de texto simple
        nueva_linea = f"{c}x {d} ........ ${subtotal:,.2f}\n"
        st.session_state.resumen_texto += nueva_linea
        st.session_state.total_acumulado += subtotal

def limpiar_todo():
    st.session_state.resumen_texto = ""
    st.session_state.total_acumulado = 0.0

# --- INTERFAZ ---
st.title("🔧 Mecánica Pro")

with st.container(border=True):
    st.text_input("Cliente", key="c_nom")
    st.text_input("Vehículo", key="c_veh")

st.write("### 🛠️ Cargar Trabajo")

# Formulario ultra-estable
with st.form(key="carga_estatica", clear_on_submit=True):
    st.text_input("Descripción", key="temp_desc")
    st.number_input("Cantidad", min_value=1, value=1, key="temp_cant")
    st.number_input("Precio Unitario", min_value=0.0, key="temp_prec")
    
    # Al hacer clic, procesamos y refrescamos
    st.form_submit_button("Añadir", on_click=procesar_item)

# VISUALIZACIÓN EN BLOQUE FIJO (Esto no debería romper el DOM de Edge)
if st.session_state.resumen_texto:
    st.write("### 📋 Detalle")
    # Usamos un área de código/texto que es un solo bloque estático
    st.code(st.session_state.resumen_texto, language=None)
    
    st.markdown(f"## TOTAL: ${st.session_state.total_acumulado:,.2f}")

    if st.button("🗑️ Borrar y Reiniciar"):
        limpiar_todo()
        st.rerun()
