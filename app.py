import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
from fpdf import FPDF
import urllib.parse
import pytz 

# 1. Configuración de página
st.set_page_config(page_title="Sistema de Presupuestos", layout="centered", page_icon="🔧")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- NUEVA FUNCIÓN: LEER DATOS DEL TALLER ---
def obtener_datos_taller():
    try:
        df_conf = conn.read(worksheet="Configuracion")
        # Retorna la primera fila como un diccionario
        return df_conf.iloc[0].to_dict()
    except Exception:
        # Datos de respaldo por si la pestaña no existe aún
        return {
            "nombre_taller": "TALLER MECÁNICO",
            "direccion": "Dirección no configurada",
            "telefono": "0000000000",
            "leyenda_presupuesto": "Presupuesto válido por 7 días"
        }

# --- FUNCIÓN DE PDF DINÁMICA ---
def crear_pdf(cliente, vehiculo, items, total, id_p, info_taller, fecha_str=None):
    if fecha_str is None:
        tz = pytz.timezone('America/Argentina/Buenos_Aires')
        fecha_str = datetime.now(tz).strftime('%d/%m/%Y %H:%M')
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # --- ENCABEZADO ---
    pdf.set_fill_color(30, 60, 120) 
    pdf.rect(0, 0, 210, 50, 'F')
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 22)
    pdf.set_y(10)
    # NOMBRE DINÁMICO
    pdf.cell(190, 10, str(info_taller['nombre_taller']).upper(), ln=True, align="L")
    
    pdf.set_font("Arial", "", 10)
    # DIRECCIÓN Y TELÉFONO DINÁMICOS
    pdf.cell(190, 5, f"Dirección: {info_taller['direccion']}", ln=True, align="L")
    pdf.cell(190, 5, f"WhatsApp: {info_taller['telefono']}", ln=True, align="L")
    pdf.cell(190, 5, f"Presupuesto N°: {id_p} | Fecha: {fecha_str}", ln=True, align="L")
    
    pdf.set_y(60) 
    
    # --- DATOS DEL CLIENTE ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, "DETALLES DEL CLIENTE Y VEHÍCULO", ln=True)
    pdf.set_draw_color(30, 60, 120)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 7, f"Cliente: {cliente}", 0)
    pdf.cell(95, 7, f"Vehículo / Patente: {vehiculo}", ln=True)
    pdf.ln(5)
    
    # --- TABLA DE ITEMS ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(100, 8, " Descripción", 1, 0, "L", True)
    pdf.cell(20, 8, "Cant.", 1, 0, "C", True)
    pdf.cell(35, 8, "Precio U.", 1, 0, "C", True)
    pdf.cell(35, 8, "Subtotal", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 9)
    for i in items:
        desc = i.get("Descripción") or i.get("descripcion")
        cant = i.get("Cantidad") or i.get("cantidad")
        prec = i.get("Precio Unit.") or i.get("precio")
        subt = i.get("Subtotal") or i.get("subtotal")
        
        pdf.cell(100, 8, f" {desc}", 1)
        pdf.cell(20, 8, str(cant), 1, 0, "C")
        pdf.cell(35, 8, f"${float(prec):,.2f}", 1, 0, "R")
        pdf.cell(35, 8, f"${float(subt):,.2f}", 1, 1, "R")
    
    # --- TOTAL ---
    pdf.ln(3)
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(30, 60, 120)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(155, 10, "TOTAL FINAL ", 0, 0, "R", True)
    pdf.cell(35, 10, f"${float(total):,.2f} ", 0, 1, "R", True)

    # --- LEYENDA PIE DE PÁGINA DINÁMICA ---
    pdf.set_y(265) 
    pdf.set_text_color(100, 100, 100)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(190, 10, str(info_taller['leyenda_presupuesto']), 0, 0, "C")
    
    return pdf.output(dest="S").encode("latin-1")

# --- INICIO DE LA APLICACIÓN ---

# Cargar configuración del taller
info_taller = obtener_datos_taller()

# Inicializar carrito
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

tab1, tab2 = st.tabs(["📝 Crear Presupuesto", "📜 Historial"])

with tab1:
    # TÍTULO DINÁMICO EN LA WEB
    st.title(f"🔧 {info_taller['nombre_taller']}")
    
    with st.container(border=True):
        st.subheader("👤 Datos del Cliente")
        cliente_nombre = st.text_input("Nombre completo", key="cli_nombre")
        vehiculo_info = st.text_input("Vehículo y Patente", key="cli_vehiculo")
        tel_cliente = st.text_input("WhatsApp Cliente (Ej: 5492302...)", key="cli_tel")

    st.write("### 🛠️ Detalles del Trabajo")
    with st.form(key="formulario_carga", clear_on_submit=True):
        desc = st.text_input("Descripción")
        c1, c2 = st.columns(2)
        cant = c1.number_input("Cantidad", min_value=1, value=1)
        prec = c2.number_input("Precio Unitario ($)", min_value=0.0, step=100.0)
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
                    tz = pytz.timezone('America/Argentina/Buenos_Aires')
                    fecha_h = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

                    nuevo_res = pd.DataFrame([{"id_presupuesto":id_p,"cliente":cliente_nombre,"vehiculo":vehiculo_info,"fecha":fecha_h,"total":total_val}])
                    detalles_list = []
                    for item in st.session_state.carrito:
                        detalles_list.append({"id_presupuesto":id_p,"descripcion":item["Descripción"],"cantidad":item["Cantidad"],"precio":item["Precio Unit."],"subtotal":item["Subtotal"]})
                    df_det = pd.DataFrame(detalles_list)

                    r_exist = conn.read(worksheet="Resumen")
                    conn.update(worksheet="Resumen", data=pd.concat([r_exist, nuevo_res], ignore_index=True))
                    d_exist = conn.read(worksheet="Detalles")
                    conn.update(worksheet="Detalles", data=pd.concat([d_exist, df_det], ignore_index=True))
                    
                    # LLAMADA AL PDF PASANDO INFO_TALLER
                    pdf_bytes = crear_pdf(cliente_nombre, vehiculo_info, st.session_state.carrito, total_val, id_p, info_taller, fecha_h)
                    st.success("✅ Guardado correctamente")
                    st.download_button("📥 Descargar PDF", data=pdf_bytes, file_name=f"Presupuesto_{cliente_nombre}.pdf", mime="application/pdf")
                    
                    if tel_cliente:
                        msg = f"Hola {cliente_nombre}, te envío el presupuesto de *{info_taller['nombre_taller']}*.\nTotal: ${total_val:,.2f}"
                        ws_link = f"https://wa.me/{tel_cliente}?text={urllib.parse.quote(msg)}"
                        st.link_button("📲 Enviar a Cliente por WhatsApp", ws_link)
                    
                    st.session_state.carrito = []
                    st.cache_data.clear()
                    
                except Exception as e:
                    st.error(f"Error: {e}")

with tab2:
    st.title("📜 Historial")
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
                
                # REIMPRESIÓN PASANDO INFO_TALLER
                pdf_re = crear_pdf(row['cliente'], row['vehiculo'], det.to_dict('records'), row['total'], row['id_presupuesto'], info_taller, row['fecha'])
                st.download_button("🖨️ Reimprimir", data=pdf_re, file_name=f"Presupuesto_{row['id_presupuesto']}.pdf", mime="application/pdf", key=f"re_{row['id_presupuesto']}")
    except:
        st.info("Cargando historial...")
