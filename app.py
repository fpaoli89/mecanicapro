import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
from fpdf import FPDF
import urllib.parse
import pytz

# 1. Configuración de página
st.set_page_config(page_title="Sistema Multi-Taller", layout="centered", page_icon="🔧")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN: VALIDAR USUARIO ---
def validar_usuario(user, pw):
    try:
        df_usuarios = conn.read(worksheet="Usuarios")
        # Buscamos si existe la combinación usuario/password
        usuario_valido = df_usuarios[(df_usuarios['usuario'] == user) & (df_usuarios['password'].astype(str) == str(pw))]
        if not usuario_valido.empty:
            return usuario_valido.iloc[0].to_dict()
        return None
    except Exception as e:
        st.error(f"Error al conectar con la tabla de usuarios: {e}")
        return None

# --- FUNCIÓN DE PDF (Mantenemos tu lógica pero ahora recibe 'info') ---
def crear_pdf(cliente, vehiculo, items, total, id_p, info, fecha_str=None):
    if fecha_str is None:
        tz = pytz.timezone('America/Argentina/Buenos_Aires')
        fecha_str = datetime.now(tz).strftime('%d/%m/%Y %H:%M')
    
    pdf = FPDF()
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
    
    # ... (Resto de la lógica del PDF igual que antes) ...
    pdf.set_y(60)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, "DETALLES DEL CLIENTE Y VEHÍCULO", ln=True)
    pdf.ln(5)
    
    # Tabla de items
    pdf.set_font("Arial", "B", 9)
    pdf.cell(100, 8, " Descripción", 1)
    pdf.cell(20, 8, "Cant.", 1)
    pdf.cell(35, 8, "Precio U.", 1)
    pdf.cell(35, 8, "Subtotal", 1, 1)
    
    pdf.set_font("Arial", "", 9)
    for i in items:
        pdf.cell(100, 8, f" {i['Descripción'] if 'Descripción' in i else i['descripcion']}", 1)
        pdf.cell(20, 8, str(i['Cantidad'] if 'Cantidad' in i else i['cantidad']), 1, 0, "C")
        pdf.cell(35, 8, f"${float(i['Precio Unit.'] if 'Precio Unit.' in i else i['precio']):,.2f}", 1, 0, "R")
        pdf.cell(35, 8, f"${float(i['Subtotal'] if 'Subtotal' in i else i['subtotal']):,.2f}", 1, 1, "R")

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(155, 10, "TOTAL ", 0, 0, "R")
    pdf.cell(35, 10, f"${total:,.2f}", 1, 1, "R")
    
    # Pie de página dinámico
    pdf.set_y(265)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(190, 10, str(info['leyenda']), 0, 0, "C")
    
    return pdf.output(dest="S").encode("latin-1")

# --- LÓGICA DE LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = None

if st.session_state.auth is None:
    st.title("🔐 Acceso al Sistema")
    with st.form("login"):
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            datos_taller = validar_usuario(user_input, pass_input)
            if datos_taller:
                st.session_state.auth = datos_taller
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
else:
    # --- SI ESTÁ LOGUEADO, MOSTRAR LA APP ---
    taller = st.session_state.auth
    
    st.sidebar.title(f"Bienvenido")
    st.sidebar.write(f"🔧 **{taller['nombre_taller']}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = None
        st.rerun()

    # Inicializar carrito
    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    tab1, tab2 = st.tabs(["📝 Crear Presupuesto", "📜 Historial"])

    with tab1:
        st.title(f"Presupuestos - {taller['nombre_taller']}")
        # (Aquí va toda tu lógica de carga de presupuesto que ya tenías)
        with st.container(border=True):
            cliente_nombre = st.text_input("Nombre del Cliente")
            vehiculo_info = st.text_input("Vehículo")
            tel_cliente = st.text_input("WhatsApp (Ej: 549...)")

        # Formulario de carga de items...
        with st.form("items"):
            d = st.text_input("Descripción")
            c = st.number_input("Cantidad", min_value=1)
            p = st.number_input("Precio", min_value=0.0)
            if st.form_submit_button("Agregar"):
                st.session_state.carrito.append({"Descripción": d, "Cantidad": c, "Precio Unit.": p, "Subtotal": c*p})

        if st.session_state.carrito:
            st.table(pd.DataFrame(st.session_state.carrito))
            total_val = sum(i['Subtotal'] for i in st.session_state.carrito)
            
            if st.button("GUARDAR PRESUPUESTO"):
                id_p = str(uuid.uuid4())[:8].upper()
                fecha_h = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).strftime("%Y-%m-%d %H:%M")
                
                # IMPORTANTE: Guardamos el 'usuario' en la base de datos para saber de quién es cada registro
                nuevo_res = pd.DataFrame([{"usuario": taller['usuario'], "id_presupuesto": id_p, "cliente": cliente_nombre, "vehiculo": vehiculo_info, "fecha": fecha_h, "total": total_val}])
                
                # Guardar en GSheets (Resumen y Detalles)
                r_exist = conn.read(worksheet="Resumen")
                conn.update(worksheet="Resumen", data=pd.concat([r_exist, nuevo_res], ignore_index=True))
                
                # (Lógica similar para Detalles...)
                st.success("Presupuesto Guardado")
                pdf_bytes = crear_pdf(cliente_nombre, vehiculo_info, st.session_state.carrito, total_val, id_p, taller, fecha_h)
                st.download_button("Descargar PDF", pdf_bytes, f"{cliente_nombre}.pdf")
                st.session_state.carrito = []

    with tab2:
        st.title("Historial del Taller")
        df_resumen = conn.read(worksheet="Resumen")
        # FILTRO CRÍTICO: Solo mostrar lo que pertenece al usuario logueado
        mis_presupuestos = df_resumen[df_resumen['usuario'] == taller['usuario']]
        st.dataframe(mis_presupuestos)
