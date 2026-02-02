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

# --- FUNCIÓN: VALIDAR USUARIO Y LIMPIAR DATOS ---
def validar_usuario(user, pw):
    try:
        df_usuarios = conn.read(worksheet="Usuarios")
        if df_usuarios.empty: return None
        df_usuarios.columns = df_usuarios.columns.str.strip().str.lower()
        df_usuarios['password'] = df_usuarios['password'].astype(str)
        
        usuario_valido = df_usuarios[(df_usuarios['usuario'] == user) & (df_usuarios['password'] == str(pw))]
        
        if not usuario_valido.empty:
            datos = usuario_valido.iloc[0].to_dict()
            # Limpieza de teléfono .0
            tel = str(datos.get('telefono', ''))
            datos['telefono'] = tel[:-2] if tel.endswith('.0') else tel
            return datos
        return None
    except Exception as e:
        st.error(f"Error en Usuarios: {e}")
        return None

# --- FUNCIÓN DE PDF ---
def crear_pdf(cliente, vehiculo, items, total, id_p, info, fecha_str):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Encabezado azul
    pdf.set_fill_color(30, 60, 120) 
    pdf.rect(0, 0, 210, 50, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 22)
    pdf.set_y(10)
    pdf.cell(190, 10, str(info.get('nombre_taller', 'Taller')).upper(), ln=True, align="L")
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 5, f"Dirección: {info.get('direccion', '')}", ln=True, align="L")
    pdf.cell(190, 5, f"WhatsApp: {info.get('telefono', '')}", ln=True, align="L")
    pdf.cell(190, 5, f"Presupuesto N°: {id_p} | Fecha: {fecha_str}", ln=True, align="L")
    
    pdf.set_y(60); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, "DETALLES DEL CLIENTE Y VEHÍCULO", ln=True)
    pdf.set_draw_color(30, 60, 120); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 7, f"Cliente: {cliente}", 0)
    pdf.cell(95, 7, f"Vehículo: {vehiculo}", ln=True); pdf.ln(5)
    
    # Tabla de ítems
    pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", "B", 9)
    pdf.cell(100, 8, " Descripción", 1, 0, "L", True)
    pdf.cell(20, 8, "Cant.", 1, 0, "C", True)
    pdf.cell(35, 8, "Precio U.", 1, 0, "C", True)
    pdf.cell(35, 8, "Subtotal", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 9)
    for i in items:
        # Normalizamos nombres de columnas por si vienen de dict o de dataframe
        d = i.get('Descripción') or i.get('descripcion') or "Sin desc."
        c = i.get('Cantidad') or i.get('cantidad') or 1
        p = i.get('Precio Unit.') or i.get('precio') or 0
        s = i.get('Subtotal') or i.get('subtotal') or 0
        pdf.cell(100, 8, f" {d}", 1)
        pdf.cell(20, 8, str(c), 1, 0, "C")
        pdf.cell(35, 8, f"${float(p):,.2f}", 1, 0, "R")
        pdf.cell(35, 8, f"${float(s):,.2f}", 1, 1, "R")

    pdf.ln(3)
    pdf.set_font("Arial", "B", 12); pdf.set_fill_color(30, 60, 120); pdf.set_text_color(255, 255, 255)
    pdf.cell(155, 10, "TOTAL FINAL ", 0, 0, "R", True)
    pdf.cell(35, 10, f"${float(total):,.2f} ", 0, 1, "R", True)

    pdf.set_y(265); pdf.set_text_color(100, 100, 100); pdf.set_font("Arial", "B", 10)
    pdf.cell(190, 10, str(info.get('leyenda', '')), 0, 0, "C")
    
    return pdf.output(dest="S").encode("latin-1")

# --- LÓGICA DE LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = None

if st.session_state.auth is None:
    st.title("🔐 Acceso Talleres")
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            datos = validar_usuario(u, p)
            if datos: st.session_state.auth = datos; st.rerun()
            else: st.error("Error de acceso")
else:
    taller = st.session_state.auth
    st.sidebar.title("🔧 Menú")
    st.sidebar.info(f"Taller: {taller.get('nombre_taller')}")
    if st.sidebar.button("Cerrar Sesión"): st.session_state.auth = None; st.rerun()

    if 'carrito' not in st.session_state: st.session_state.carrito = []

    tab1, tab2 = st.tabs(["📝 Presupuestador", "📜 Historial y Búsqueda"])

    with tab1:
        st.title("Nuevo Trabajo")
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Cliente")
        vehiculo = c2.text_input("Vehículo / Patente")
        tel_envio = st.text_input("WhatsApp Cliente (Sin +)")

        st.subheader("Añadir Trabajos/Repuestos")
        
        # --- BUSCADOR DE PRECIOS SUGERIDOS ---
        try:
            df_precios = conn.read(worksheet="Precios")
            lista_sugeridos = df_precios['item'].tolist()
        except:
            lista_sugeridos = []

        # Interfaz de carga
        col_bus, col_cant, col_precio = st.columns([3, 1, 1])
        
        # Usamos un selectbox para sugeridos o texto libre
        opcion = col_bus.selectbox("Buscar en lista de precios:", ["-- Escribir nuevo --"] + lista_sugeridos)
        
        precio_sugerido = 0.0
        desc_final = ""
        
        if opcion != "-- Escribir nuevo --":
            desc_final = opcion
            precio_sugerido = float(df_precios[df_precios['item'] == opcion]['precio'].iloc[0])
        else:
            desc_final = col_bus.text_input("Descripción manual")

        cant = col_cant.number_input("Cant.", min_value=1, value=1)
        prec = col_precio.number_input("Precio $", min_value=0.0, value=precio_sugerido, step=500.0)

        if st.button("➕ Añadir al Presupuesto"):
            if desc_final and prec > 0:
                st.session_state.carrito.append({
                    "id": str(uuid.uuid4())[:5],
                    "Descripción": desc_final,
                    "Cantidad": cant,
                    "Precio Unit.": prec,
                    "Subtotal": cant * prec
                })
                st.rerun()

        # Mostrar Carrito y permitir Borrar/Editar
        if st.session_state.carrito:
            st.write("---")
            for idx, item in enumerate(st.session_state.carrito):
                cb1, cb2, cb3, cb4, cb5 = st.columns([3,1,1,1,0.5])
                cb1.write(item['Descripción'])
                cb2.write(f"x{item['Cantidad']}")
                cb3.write(f"${item['Precio Unit.']:,.0f}")
                cb4.write(f"**${item['Subtotal']:,.0f}**")
                if cb5.button("🗑️", key=f"del_{item['id']}"):
                    st.session_state.carrito.pop(idx)
                    st.rerun()

            total_final = sum(i['Subtotal'] for i in st.session_state.carrito)
            st.subheader(f"Total: ${total_final:,.2f}")

            if st.button("💾 FINALIZAR Y GUARDAR", use_container_width=True):
                if not cliente or not vehiculo:
                    st.warning("Faltan datos del cliente")
                else:
                    id_p = str(uuid.uuid4())[:8].upper()
                    tz = pytz.timezone('America/Argentina/Buenos_Aires')
                    fecha_h = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
                    
                    # Guardar en Sheets
                    res_df = pd.DataFrame([{"usuario": taller['usuario'], "id_presupuesto": id_p, "cliente": cliente, "vehiculo": vehiculo, "fecha": fecha_h, "total": total_final}])
                    det_df = pd.DataFrame([{"usuario": taller['usuario'], "id_presupuesto": id_p, "descripcion": i["Descripción"], "cantidad": i["Cantidad"], "precio": i["Precio Unit."], "subtotal": i["Subtotal"]} for i in st.session_state.carrito])
                    
                    conn.update(worksheet="Resumen", data=pd.concat([conn.read(worksheet="Resumen"), res_df], ignore_index=True))
                    conn.update(worksheet="Detalles", data=pd.concat([conn.read(worksheet="Detalles"), det_df], ignore_index=True))

                    pdf_b = crear_pdf(cliente, vehiculo, st.session_state.carrito, total_final, id_p, taller, fecha_h)
                    st.success("Presupuesto Guardado Correctamente")
                    st.download_button("📥 Descargar PDF", pdf_b, f"Presupuesto_{cliente}.pdf", "application/pdf")
                    
                    if tel_envio:
                        msg = f"Hola {cliente}, te envío el presupuesto de *{taller.get('nombre_taller')}* por un total de ${total_final:,.2f}"
                        st.link_button("📲 Enviar por WhatsApp", f"https://wa.me/{tel_envio}?text={urllib.parse.quote(msg)}")
                    
                    st.session_state.carrito = []; st.cache_data.clear()

    with tab2:
        st.title("Historial de Trabajos")
        try:
            df_r = conn.read(worksheet="Resumen")
            df_d = conn.read(worksheet="Detalles")
            historial = df_r[df_r['usuario'] == taller['usuario']].copy()
            historial['fecha_dt'] = pd.to_datetime(historial['fecha'])
            
            f1, f2, f3 = st.columns([2,1,1])
            busqueda = f1.text_input("🔍 Buscar Cliente o Patente")
            d_desde = f2.date_input("Desde", value=datetime(2025,1,1))
            d_hasta = f3.date_input("Hasta")

            if busqueda:
                historial = historial[historial['cliente'].str.contains(busqueda, case=False) | historial['vehiculo'].str.contains(busqueda, case=False)]
            historial = historial[(historial['fecha_dt'].dt.date >= d_desde) & (historial['fecha_dt'].dt.date <= d_hasta)]

            for _, row in historial.sort_values('fecha_dt', ascending=False).iterrows():
                with st.expander(f"🚗 {row['vehiculo']} | {row['cliente']} | {row['fecha']}"):
                    items_p = df_d[df_d['id_presupuesto'] == row['id_presupuesto']]
                    st.table(items_p[['descripcion', 'cantidad', 'precio', 'subtotal']])
                    pdf_re = crear_pdf(row['cliente'], row['vehiculo'], items_p.to_dict('records'), row['total'], row['id_presupuesto'], taller, row['fecha'])
                    st.download_button("🖨️ Reimprimir PDF", pdf_re, f"RE_{row['id_presupuesto']}.pdf", key=f"re_{row['id_presupuesto']}")
        except: st.info("No hay datos cargados aún.")
