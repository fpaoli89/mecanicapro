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
def crear_pdf(cliente, vehiculo, items, total, id_p, fecha=None):
    if fecha is None:
        fecha = datetime.now().strftime('%d/%m/%Y')
    
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("Arial", "B", 20)
    pdf.cell(200, 10, "PRESUPUESTO - MECÁNICA PRO", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(200, 10, f"ID: #{id_p} | Fecha: {fecha}", ln=True, align="C")
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
        # Manejo de nombres de columnas por si vienen de diferentes fuentes
        desc = i.get("Descripción") or i.get("descripcion")
        cant = i.get("Cantidad") or i.get("cantidad")
        prec = i.get("Precio Unit.") or i.get("precio")
        subt = i.get("Subtotal") or i.get("subtotal")
        
        pdf.cell(100, 10, str(desc), 1)
        pdf.cell(30, 10, str(cant), 1, 0, "C")
        pdf.cell(30, 10, f"${float(prec):,.2f}", 1, 0, "C")
        pdf.cell(30, 10, f"${float(subt):,.2f}", 1, 1, "C")
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, f"TOTAL: ${float(total):,.2f}", 0, 1, "R")
    
    return pdf.output(dest="S").encode("latin-1")

# --- INTERFAZ CON PESTAÑAS ---
tab1, tab2 = st.tabs(["📝 Crear Presupuesto", "📜 Historial"])

with tab1:
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
                fecha_h = datetime.now().strftime("%Y-%m-%d %H:%M")

                # Lógica de guardado
                nuevo_res = pd.DataFrame([{"id_presupuesto":id_p,"cliente":cliente,"vehiculo":vehiculo,"fecha":fecha_h,"total":total}])
                detalles_list = []
                for item in st.session_state.carrito:
                    detalles_list.append({"id_presupuesto":id_p,"descripcion":item["Descripción"],"cantidad":item["Cantidad"],"precio":item["Precio Unit."],"subtotal":item["Subtotal"]})
                df_det = pd.DataFrame(detalles_list)

                try:
                    r_exist = conn.read(worksheet="Resumen")
                    conn.update(worksheet="Resumen", data=pd.concat([r_exist, nuevo_res], ignore_index=True))
                except:
                    conn.create(worksheet="Resumen", data=nuevo_res)

                try:
                    d_exist = conn.read(worksheet="Detalles")
                    conn.update(worksheet="Detalles", data=pd.concat([d_exist, df_det], ignore_index=True))
                except:
                    conn.create(worksheet="Detalles", data=df_det)
                
                pdf_bytes = crear_pdf(cliente, vehiculo, st.session_state.carrito, total, id_p)
                st.success("✅ Guardado en Excel")
                st.download_button("📥 Descargar Presupuesto PDF", data=pdf_bytes, file_name=f"Presupuesto_{id_p}.pdf", mime="application/pdf")
                
                if telefono:
                    texto = f"Hola {cliente}, te adjunto el presupuesto para tu {vehiculo}.\nTotal: ${total:,.2f}\nSaludos de Mecánica Pro."
                    texto_url = urllib.parse.quote(texto)
                    ws_link = f"https://wa.me/{telefono}?text={texto_url}"
                    st.link_button("📲 Enviar Aviso por WhatsApp", ws_link)
                
                st.session_state.carrito = []
                st.cache_data.clear() # Limpiar cache para que el historial se actualice
                
            except Exception as e:
                st.error(f"Error: {e}")

with tab2:
    st.title("📜 Historial de Presupuestos")
    
    try:
        df_resumen = conn.read(worksheet="Resumen")
        df_detalles_all = conn.read(worksheet="Detalles")
        
        # Filtros
        col1, col2 = st.columns(2)
        busqueda = col1.text_input("🔍 Buscar por Cliente o Vehículo")
        # Convertir fecha a string para filtrar
        df_resumen['fecha'] = df_resumen['fecha'].astype(str)
        
        # Aplicar filtros
        df_filtrado = df_resumen.copy()
        if busqueda:
            df_filtrado = df_filtrado[
                df_filtrado['cliente'].str.contains(busqueda, case=False) | 
                df_filtrado['vehiculo'].str.contains(busqueda, case=False)
            ]
        
        st.write(f"Mostrando {len(df_filtrado)} presupuestos")
        
        for index, row in df_filtrado.sort_index(ascending=False).iterrows():
            with st.expander(f"📅 {row['fecha']} - 👤 {row['cliente']} - 💰 ${row['total']:,.2f}"):
                st.write(f"**ID:** {row['id_presupuesto']}")
                st.write(f"**Vehículo:** {row['vehiculo']}")
                
                # Obtener detalles de este presupuesto específico
                detalles_p = df_detalles_all[df_detalles_all['id_presupuesto'] == row['id_presupuesto']]
                st.table(detalles_p[['descripcion', 'cantidad', 'precio', 'subtotal']])
                
                # Botón de Reimpresión
                pdf_reprint = crear_pdf(
                    row['cliente'], 
                    row['vehiculo'], 
                    detalles_p.to_dict('records'), 
                    row['total'], 
                    row['id_presupuesto'],
                    row['fecha']
                )
                
                st.download_button(
                    label="🖨️ Reimprimir PDF",
                    data=pdf_reprint,
                    file_name=f"Reimpresion_{row['id_presupuesto']}.pdf",
                    mime="application/pdf",
                    key=f"btn_{row['id_presupuesto']}"
                )
                
    except Exception as e:
        st.info("Aún no hay presupuestos guardados o el historial está cargando...")
