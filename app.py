import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
from fpdf import FPDF
import urllib.parse
import pytz

# 1. Configuración de página
st.set_page_config(page_title="Sistema de Presupuestos PRO", layout="centered", page_icon="🔧")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN: VALIDAR USUARIO ---
def validar_usuario(user, pw):
    try:
        df_usuarios = conn.read(worksheet="Usuarios")
        if df_usuarios.empty:
            return None
        usuario_valido = df_usuarios[(df_usuarios['usuario'] == user) & (df_usuarios['password'].astype(str) == str(pw))]
        if not usuario_valido.empty:
            return usuario_valido.iloc[0].to_dict()
        return None
    except Exception as e:
        st.error(f"Error en pestaña Usuarios: {e}")
        return None

# --- FUNCIÓN DE PDF ---
def crear_pdf(cliente, vehiculo, items, total, id_p, info, fecha_str):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Encabezado con datos del taller logueado
    pdf.set_fill_color(30, 60, 120) 
    pdf.rect(0, 0, 210, 50, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 22)
    pdf.set_y(10)
    pdf.cell(190, 10, str(info['nombre_taller']).upper(), ln=True, align="L")
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 5, f"Dirección: {info['direccion']}", ln=True, align="L")
    pdf.cell(190, 5, f"WhatsApp: {info['telefono']}", ln=True, align="L")
    pdf.cell(190, 5, f"Presupuesto N°: {id_p} | Fecha: {fecha_str}", ln=True, align="L")
    
    pdf.set_y(60)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, "DETALLES DEL CLIENTE Y VEHÍCULO", ln=True)
    pdf.set_draw_color(30, 60, 120)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 7, f"Cliente: {cliente}", 0)
    pdf.cell(95, 7, f"Vehículo: {vehiculo}", ln=True)
    pdf.ln(5)
    
    # Tabla
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(100, 8, " Descripción", 1, 0, "L", True)
    pdf.cell(20, 8, "Cant.", 1, 0, "C", True)
    pdf.cell(35, 8, "Precio U.", 1, 0, "C", True)
    pdf.cell(35, 8, "Subtotal", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 9)
    for i in items:
        # Maneja tanto nombres de columnas de sesión como de historial
        d = i.get('Descripción') or i.get('descripcion')
        c = i.get('Cantidad') or i.get('cantidad')
        p = i.get('Precio Unit.') or i.get('precio')
        s = i.get('Subtotal') or i.get('subtotal')
        pdf.cell(100, 8, f" {d}", 1)
        pdf.cell(20, 8, str(c), 1, 0, "C")
        pdf.cell(35, 8, f"${float(p):,.2f}", 1, 0, "R")
        pdf.cell(35, 8, f"${float(s):,.2f}", 1, 1, "R")

    pdf.ln(3)
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(30, 60, 120)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(155, 10, "TOTAL FINAL ", 0, 0, "R", True)
    pdf.cell(35, 10, f"${float(total):,.2f} ", 0, 1, "R", True)

    pdf.set_y(265)
    pdf.set_text_color(100, 100, 100)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(190, 10, str(info['leyenda']), 0, 0, "C")
    
    return pdf.output(dest="S").encode("latin-1")

# --- LÓGICA DE ACCESO ---
if 'auth' not in st.session_state:
    st.session_state.auth = None

if st.session_state.auth is None:
    st.title("🔐 Acceso Talleres")
    with st.form("login_form"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            datos = validar_usuario(u, p)
            if datos:
                st.session_state.auth = datos
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
else:
    taller = st.session_state.auth
    st.sidebar.title("🔧 Menú")
    st.sidebar.info(f"Taller: {taller['nombre_taller']}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = None
        st.rerun()

    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    tab1, tab2 = st.tabs(["📝 Nuevo Presupuesto", "📜 Historial"])

    with tab1:
        st.title("Crear Presupuesto")
        
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Nombre del Cliente")
        vehiculo = c2.text_input("Vehículo / Patente")
        tel = st.text_input("WhatsApp para envío (Ej: 549...)")

        with st.form("item_carga", clear_on_submit=True):
            col1, col2, col3 = st.columns([3,1,1])
            desc = col1.text_input("Descripción del trabajo/repuesto")
            cant = col2.number_input("Cant.", min_value=1, value=1)
            prec = col3.number_input("Precio $", min_value=0.0, step=100.0)
            if st.form_submit_button("➕ Añadir"):
                if desc and prec > 0:
                    st.session_state.carrito.append({
                        "Descripción": desc, 
                        "Cantidad": cant, 
                        "Precio Unit.": prec, 
                        "Subtotal": cant * prec
                    })

        if st.session_state.carrito:
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car)
            total_final = df_car["Subtotal"].sum()
            st.subheader(f"Total: ${total_final:,.2f}")

            if st.button("💾 GUARDAR Y GENERAR PDF", use_container_width=True):
                if not cliente or not vehiculo:
                    st.warning("Completa los datos del cliente")
                else:
                    try:
                        id_p = str(uuid.uuid4())[:8].upper()
                        tz = pytz.timezone('America/Argentina/Buenos_Aires')
                        fecha_h = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

                        # 1. Guardar Resumen (con usuario)
                        nuevo_res = pd.DataFrame([{
                            "usuario": taller['usuario'],
                            "id_presupuesto": id_p,
                            "cliente": cliente,
                            "vehiculo": vehiculo,
                            "fecha": fecha_h,
                            "total": total_final
                        }])
                        
                        # 2. Guardar Detalles (con usuario)
                        detalles_list = []
                        for item in st.session_state.carrito:
                            detalles_list.append({
                                "usuario": taller['usuario'],
                                "id_presupuesto": id_p,
                                "descripcion": item["Descripción"],
                                "cantidad": item["Cantidad"],
                                "precio": item["Precio Unit."],
                                "subtotal": item["Subtotal"]
                            })
                        df_det_nuevo = pd.DataFrame(detalles_list)

                        # Actualizar Sheets
                        res_old = conn.read(worksheet="Resumen")
                        det_old = conn.read(worksheet="Detalles")
                        
                        conn.update(worksheet="Resumen", data=pd.concat([res_old, nuevo_res], ignore_index=True))
                        conn.update(worksheet="Detalles", data=pd.concat([det_old, df_det_nuevo], ignore_index=True))

                        # PDF
                        pdf_b = crear_pdf(cliente, vehiculo, st.session_state.carrito, total_final, id_p, taller, fecha_h)
                        st.success("¡Presupuesto guardado!")
                        st.download_button("📥 Descargar PDF", pdf_b, f"Presupuesto_{cliente}.pdf", "application/pdf")
                        
                        if tel:
                            msg = f"Hola {cliente}, te envío el presupuesto de *{taller['nombre_taller']}* por un total de ${total_final:,.2f}"
                            st.link_button("📲 Enviar WhatsApp", f"https://wa.me/{tel}?text={urllib.parse.quote(msg)}")
                        
                        st.session_state.carrito = []
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

    with tab2:
        st.title("Historial")
        try:
            df_r = conn.read(worksheet="Resumen")
            df_d = conn.read(worksheet="Detalles")
            
            # FILTRO POR USUARIO (Esto evita el KeyError si la columna existe)
            if 'usuario' in df_r.columns:
                historial_taller = df_r[df_r['usuario'] == taller['usuario']]
                
                if historial_taller.empty:
                    st.info("No hay presupuestos cargados aún.")
                else:
                    busqueda = st.text_input("🔍 Buscar por cliente o vehículo")
                    if busqueda:
                        historial_taller = historial_taller[
                            historial_taller['cliente'].str.contains(busqueda, case=False) | 
                            historial_taller['vehiculo'].str.contains(busqueda, case=False)
                        ]
                    
                    for _, row in historial_taller.iloc[::-1].iterrows():
                        with st.expander(f"📅 {row['fecha']} | {row['cliente']} | ${row['total']:,.2f}"):
                            items_p = df_d[df_d['id_presupuesto'] == row['id_presupuesto']]
                            st.table(items_p[['descripcion', 'cantidad', 'precio', 'subtotal']])
                            
                            # Reimpresión
                            pdf_re = crear_pdf(row['cliente'], row['vehiculo'], items_p.to_dict('records'), row['total'], row['id_presupuesto'], taller, row['fecha'])
                            st.download_button("🖨️ Reimprimir PDF", pdf_re, f"Presupuesto_{row['id_presupuesto']}.pdf", key=f"re_{row['id_presupuesto']}")
            else:
                st.error("Falta la columna 'usuario' en la pestaña Resumen.")
        except:
            st.write("Cargando datos...")
