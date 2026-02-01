import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
from fpdf import FPDF
import urllib.parse

# 1. Configuración de página
st.set_page_config(page_title="Mecánica Pro", layout="centered", page_icon="🔧")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Inicializar el carrito en la sesión
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- FUNCIONES DE LÓGICA ---
def crear_pdf(cliente, vehiculo, items, total, id_p):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("Arial", "B", 20)
    pdf.cell(200, 10, "PRESUPUESTO - MECÁNICA PRO", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(200, 10, f"ID: #{id_p} | Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.ln(10)
    
    # Datos Cliente
    pdf.set_font("Arial", "B", 12)
    pdf.cell(100, 10, f"Cliente: {cliente}")
    pdf.cell(100, 10, f"Vehículo: {vehiculo}", ln=True)
    pdf.ln(5)
    
    # Tabla
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(100, 10, "Descripción", 1, 0, "C", True)
    pdf.cell(30, 10, "Cant.", 1, 0, "C", True)
    pdf.cell(30, 10, "Precio U.", 1, 0, "C", True)
    pdf.cell(30, 10, "Subtotal", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 10)
    for i in items:
        pdf.cell(100, 10, str(i["Descripción"]), 1)
        pdf.cell(30, 10, str(i["Cantidad"]), 1, 0, "C")
        pdf.cell(30, 10, f"${i['Precio Unit.']:,.2f}", 1, 0, "C")
        pdf.cell(30, 10, f"${i['Subtotal']:,.2f}", 1, 1, "C")
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, f"TOTAL: ${total:,.2f}", 0, 1, "R")
    
    return pdf.output(dest="S").encode("latin-1")

# --- INTERFAZ ---
st.title("🔧 Mecánica Pro")

with st.container(border=True):
    st.subheader("👤 Datos del Cliente")
    cliente = st.text_input("Nombre completo", key="cli_nombre")
    vehiculo = st.text_input("Vehículo y Patente", key="cli_vehiculo")
    telefono = st.text_input("WhatsApp Cliente (Ej: 54911...)")

st.write("### 🛠️ Detalles del Trabajo")
with st.form(key="formulario_carga", clear_on_submit=True):
    desc = st.text_input("Descripción", key="temp_desc")
    c1, c2 = st.columns(2)
    cant = c1.number_input("Cantidad", min_value=1, value=1, key="temp_cant")
    prec = c2.number_input("Precio Unitario ($)", min_value=0.0, step=100.0, key="temp_prec")
    if st.form_submit_button("➕ Añadir"):
        if desc and prec > 0:
            st.session_state.carrito.append({"Descripción": desc, "Cantidad": cant, "Precio Unit.": prec, "Subtotal": cant * prec})

if st.session_state.carrito:
    df = pd.DataFrame(st.session_state.carrito)
    st.table(df)
    total = df["Subtotal"].sum()
    st.markdown(f"## TOTAL: ${total:,.2f}")

    if st.button("💾 GUARDAR Y GENERAR PDF", use_container_width=True):
        try:
            id_p = str(uuid.uuid4())[:8].upper()
            # ... (Lógica de guardado en GSheets que ya tienes funcionando) ...
            
            # Generar PDF
            pdf_bytes = crear_pdf(cliente, vehiculo, st.session_state.carrito, total, id_p)
            
            st.success("✅ Guardado en Excel")
            st.download_button("📥 Descargar Presupuesto PDF", data=pdf_bytes, file_name=f"Presupuesto_{id_p}.pdf", mime="application/pdf")
            
            # Botón WhatsApp
            texto = f"Hola {cliente}, te adjunto el presupuesto para tu {vehiculo}.\nTotal: ${total:,.2f}\nSaludos de Mecánica Pro."
            texto_url = urllib.parse.quote(texto)
            ws_link = f"https://wa.me/{telefono}?text={texto_url}"
            st.link_button("📲 Enviar Aviso por WhatsApp", ws_link)
            
        except Exception as e:
            st.error(f"Error: {e}")
