import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# 1. Configuración de página
st.set_page_config(page_title="Mecánica Pro", layout="centered", page_icon="🔧")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Inicializar el carrito en la sesión
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- FUNCIONES DE LÓGICA ---
def agregar_item():
    desc = st.session_state.temp_desc
    cant = st.session_state.temp_cant
    prec = st.session_state.temp_prec
    
    if desc and prec > 0:
        st.session_state.carrito.append({
            "Descripción": desc,
            "Cantidad": cant,
            "Precio Unit.": prec,
            "Subtotal": cant * prec
        })

def limpiar_todo():
    st.session_state.carrito = []
    st.session_state.cli_nombre = ""
    st.session_state.cli_vehiculo = ""

# --- INTERFAZ DE USUARIO ---
st.title("🔧 Mecánica Pro")
st.write("Sistema de Gestión de Presupuestos")

# Sección 1: Datos del Cliente
with st.container(border=True):
    st.subheader("👤 Datos del Cliente")
    st.text_input("Nombre completo", key="cli_nombre")
    st.text_input("Vehículo y Patente", key="cli_vehiculo")

# Sección 2: Carga de Trabajos
st.write("### 🛠️ Detalles del Trabajo")
with st.form(key="formulario_carga", clear_on_submit=True):
    st.text_input("Descripción del repuesto o servicio", key="temp_desc")
    c1, c2 = st.columns(2)
    c1.number_input("Cantidad", min_value=1, value=1, key="temp_cant")
    c2.number_input("Precio Unitario ($)", min_value=0.0, step=100.0, key="temp_prec")
    
    if st.form_submit_button("➕ Añadir a la lista"):
        agregar_item()

# Sección 3: Resumen y Guardado
if st.session_state.carrito:
    st.divider()
    st.subheader("📋 Resumen del Presupuesto")
    
    df_carrito = pd.DataFrame(st.session_state.carrito)
    st.table(df_carrito)
    
    total = df_carrito["Subtotal"].sum()
    st.markdown(f"## TOTAL: ${total:,.2f}")

    col_save, col_clear = st.columns(2)
    
    if col_save.button("💾 GUARDAR EN SISTEMA", use_container_width=True):
        if not st.session_state.cli_nombre or not st.session_state.cli_vehiculo:
            st.error("❌ Por favor completa los datos del cliente y vehículo.")
        else:
            try:
                # Generar ID y Fecha
                id_p = str(uuid.uuid4())[:8].upper()
                fecha_h = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                # Preparar datos para 'Resumen'
                nuevo_resumen = pd.DataFrame([{
                    "id_presupuesto": id_p,
                    "cliente": st.session_state.cli_nombre,
                    "vehiculo": st.session_state.cli_vehiculo,
                    "fecha": fecha_h,
                    "total": total
                }])
                
                # Preparar datos para 'Detalles'
                detalles_list = []
                for item in st.session_state.carrito:
                    detalles_list.append({
                        "id_presupuesto": id_p,
                        "descripcion": item["Descripción"],
                        "cantidad": item["Cantidad"],
                        "precio": item["Precio Unit."],
                        "subtotal": item["Subtotal"]
                    })
                df_detalles = pd.DataFrame(detalles_list)

                # --- PROCESO DE GUARDADO REFORZADO ---
                # Guardar en pestaña 'Resumen'
                try:
                    res_existente = conn.read(worksheet="Resumen")
                    res_final = pd.concat([res_existente, nuevo_resumen], ignore_index=True)
                    conn.update(worksheet="Resumen", data=res_final)
                except:
                    conn.create(worksheet="Resumen", data=nuevo_resumen)

                # Guardar en pestaña 'Detalles'
                try:
                    det_existente = conn.read(worksheet="Detalles")
                    det_final = pd.concat([det_existente, df_detalles], ignore_index=True)
                    conn.update(worksheet="Detalles", data=det_final)
                except:
                    conn.create(worksheet="Detalles", data=df_detalles)
                
                st.success(f"✅ ¡Presupuesto #{id_p} guardado con éxito!")
                st.balloons()
                st.session_state.carrito = [] # Limpiar carrito tras éxito
                
            except Exception as e:
                st.error(f"Hubo un problema de conexión: {e}")
                st.info("💡 Consejo: Asegúrate de que el correo del Service Account sea EDITOR en tu Google Sheets.")

    if col_clear.button("🗑️ VACIAR TODO", use_container_width=True):
        limpiar_todo()
        st.rerun()
