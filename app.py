import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
from fpdf import FPDF
import urllib.parse

# 1. Configuración de página
st.set_page_config(page_title="Taller Mecánico El Fer", layout="centered", page_icon="🔧")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Inicializar el carrito en la sesión
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- FUNCIÓN DE PDF MEJORADA ---
def crear_pdf(cliente, vehiculo, items, total, id_p, fecha=None):
    if fecha is None:
        fecha = datetime.now().strftime('%d/%m/%Y')
    
    pdf = FPDF()
    pdf.add_page()
    
    # --- ENCABEZADO PROFESIONAL ---
    # Rectángulo azul de fondo para el encabezado
    pdf.set_fill_color(30, 60, 120) 
    pdf.rect(0, 0, 210, 45, 'F')
    
    pdf.set_font("Arial", "B", 24)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, "TALLER MECÁNICO EL FER", ln=True, align="L")
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 5, "Servicio Integral Automotriz", ln=True, align="L")
    pdf.cell(190, 5, f"Presupuesto N°: {id_p} | Fecha: {fecha}", ln=True, align="L")
    
    pdf.ln(20) # Espacio para salir del encabezado azul
    
    # --- DATOS DEL CLIENTE ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "INFORMACIÓN DEL CLIENTE Y VEHÍCULO", ln=True)
    pdf.set_draw_color(30, 60, 120)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(95, 8, f"Cliente: {cliente}", 0)
    pdf.cell(95, 8, f"Vehículo / Patente: {vehiculo}", ln=True)
    pdf.ln(8)
    
    # --- TABLA DE ITEMS ---
    # Cabecera de tabla
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(100, 10, " Descripción del Trabajo / Repuesto", 1, 0, "L", True)
    pdf.cell(20, 10, "Cant.", 1, 0, "C", True)
    pdf.cell(35, 10, "Precio U.", 1, 0, "C", True)
    pdf.cell(35, 10, "Subtotal", 1, 1, "C", True)
    
    # Cuerpo de tabla
    pdf.set_font("Arial", "", 10)
    for i in items:
        desc = i.get("Descripción") or i.get("descripcion")
        cant = i.get("Cantidad") or i.get("cantidad")
        prec = i.get("Precio Unit.") or i.get("precio")
        subt = i.get("Subtotal") or i.get("subtotal")
        
        pdf.cell(100, 10, f" {desc}", 1)
        pdf.cell(20, 10, str(cant), 1, 0, "C")
        pdf.cell(35, 10, f"${float(prec):,.2f}", 1, 0, "R")
        pdf.cell(35, 10, f"${float(subt):,.2f}", 1, 1, "R")
    
    # --- TOTAL ---
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(30, 60, 120)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(155, 12, "TOTAL FINAL ", 0, 0, "R", True)
    pdf.cell(35, 12, f"${float(total):,.2f} ", 0, 1, "R", True)
    
    # --- PIE DE PÁGINA (Tus datos) ---
    pdf.set_y(-35)
    pdf.set_text_color(80, 80, 80)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(190, 5, "Este presupuesto tiene una validez de 7 días.", ln=True, align="C")
    pdf.set_font("Arial", "B", 9)
    pdf.cell(190, 5, "Dirección: 18 n° 960, Gral. Pico, La Pampa", ln=True, align="C")
    pdf.cell(190, 5, "WhatsApp: 5492302645333", ln=True, align="C")
    
    return pdf.output(dest="S").encode("latin-1")

# --- INTERFAZ CON PESTAÑAS ---
tab1, tab2 = st.tabs(["📝 Crear Presupuesto", "📜 Historial"])

with tab1:
    st.title("🔧 Taller Mecánico El Fer")

    with st.container(border=True):
        st.subheader("👤 Datos del Cliente")
        cliente_nombre = st.text_input("Nombre completo", key="cli_nombre")
        vehiculo_info = st.text_input("Vehículo y Patente", key="cli_vehiculo")
        tel_whatsapp = "5492302645333" # Tu WhatsApp por defecto o puedes hacerlo dinámico

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
        total_val = df["Subtotal"].sum()
        st.markdown(f"## TOTAL: ${total_val:,.2f}")

        if st.button("💾 GUARDAR Y GENERAR PDF", use_container_width=True):
            if not cliente_nombre or not vehiculo_info:
                st.warning("⚠️ Completa los datos del cliente.")
            else:
                try:
                    id_p = str(uuid.uuid4())[:8].upper()
                    fecha_h = datetime.now().strftime("%Y-%m-%d %H:%M")

                    nuevo_res = pd.DataFrame([{"id_presupuesto":id_p,"cliente":cliente_nombre,"vehiculo":vehiculo_info,"fecha":fecha_h,"total":total_val}])
                    detalles_list = []
                    for item in st.session_state.carrito:
                        detalles_list.append({"id_presupuesto":id_p,"descripcion":item["Descripción"],"cantidad":item["Cantidad"],"precio":item["Precio Unit."],"subtotal":item["Subtotal"]})
                    df_det = pd.DataFrame(detalles_list)

                    # Guardado en GSheets
                    r_exist = conn.read(worksheet="Resumen")
                    conn.update(worksheet="Resumen", data=pd.concat([r_exist, nuevo_res], ignore_index=True))
                    d_exist = conn.read(worksheet="Detalles")
                    conn.update(worksheet="Detalles", data=pd.concat([d_exist, df_det], ignore_index=True))
                    
                    pdf_bytes = crear_pdf(cliente_nombre, vehiculo_info, st.session_state.carrito, total_val, id_p)
                    st.success("✅ Guardado correctamente")
                    st.download_button("📥 Descargar PDF Profesional", data=pdf_bytes, file_name=f"Presupuesto_{cliente_nombre}.pdf", mime="application/pdf")
                    
                    # WhatsApp para el cliente (Aviso)
                    msg = f"Hola {cliente_nombre}, te envío el presupuesto de *Taller Mecánico El Fer*.\nTotal: ${total_val:,.2f}"
                    ws_link = f"https://wa.me/{tel_whatsapp}?text={urllib.parse.quote(msg)}"
                    st.link_button("📲 Notificar por WhatsApp", ws_link)
                    
                    st.session_state.carrito = []
                    st.cache_data.clear()
                    
                except Exception as e:
                    st.error(f"Error: {e}")

with tab2:
    st.title("📜 Historial de Trabajos")
    try:
        df_resumen = conn.read(worksheet="Resumen")
        df_detalles_all = conn.read(worksheet="Detalles")
        
        busqueda = st.text_input("🔍 Buscar cliente o vehículo")
        
        df_filtrado = df_resumen.copy()
        if busqueda:
            df_filtrado = df_filtrado[df_filtrado['cliente'].str.contains(busqueda, case=False) | df_filtrado['vehiculo'].str.contains(busqueda, case=False)]
        
        for _, row in df_filtrado.iloc[::-1].iterrows():
            with st.expander(f"📅 {row['fecha']} | {row['cliente']} | ${row['total']:,.2f}"):
                det = df_detalles_all[df_detalles_all['id_presupuesto'] == row['id_presupuesto']]
                st.table(det[['descripcion', 'cantidad', 'precio', 'subtotal']])
                
                pdf_re = crear_pdf(row['cliente'], row['vehiculo'], det.to_dict('records'), row['total'], row['id_presupuesto'], row['fecha'])
                st.download_button("🖨️ Reimprimir PDF", data=pdf_re, file_name=f"Reimpresion_{row['id_presupuesto']}.pdf", mime="application/pdf", key=f"re_{row['id_presupuesto']}")
    except:
        st.info("Cargando historial...")
