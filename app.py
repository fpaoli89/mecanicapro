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
        if df_usuarios.empty: return None
        df_usuarios.columns = df_usuarios.columns.str.strip().str.lower()
        df_usuarios['password'] = df_usuarios['password'].astype(str)
        usuario_valido = df_usuarios[(df_usuarios['usuario'] == user) & (df_usuarios['password'] == str(pw))]
        
        if not usuario_valido.empty:
            datos = usuario_valido.iloc[0].to_dict()
            # Limpiar teléfono del taller
            tel = str(datos.get('telefono', ''))
            datos['telefono'] = tel[:-2] if tel.endswith('.0') else tel
            # Asegurar que existan campos de rubro y email
            datos.setdefault('rubro', 'Servicios Mecánicos')
            datos.setdefault('email', 'contacto@taller.com')
            return datos
        return None
    except Exception as e:
        st.error(f"Error en Usuarios: {e}")
        return None

# --- FUNCIÓN DE PDF MODIFICADA (ENCABEZADO AMPLIADO) ---
def crear_pdf(cliente, vehiculo, items, total, id_p, info, fecha_str):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Encabezado con más líneas
    pdf.set_fill_color(30, 60, 120) 
    pdf.rect(0, 0, 210, 65, 'F') # Aumentamos la altura del rectángulo azul
    pdf.set_text_color(255, 255, 255)
    
    # Línea 1: Taller
    pdf.set_font("Arial", "B", 22)
    pdf.set_y(10)
    pdf.cell(190, 10, str(info.get('nombre_taller', 'Taller')).upper(), ln=True, align="L")
    
    # Línea 2: Rubro
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 6, str(info.get('rubro', '')), ln=True, align="L")
    
    # Líneas de contacto
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 5, f"Email: {info.get('email', '')}", ln=True, align="L")
    pdf.cell(190, 5, f"Dirección: {info.get('direccion', '')}", ln=True, align="L")
    pdf.cell(190, 5, f"WhatsApp Taller: {info.get('telefono', '')}", ln=True, align="L")
    pdf.cell(190, 5, f"Presupuesto N°: {id_p} | Fecha: {fecha_str}", ln=True, align="L")
    
    pdf.set_y(75); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, "DETALLES DEL CLIENTE Y VEHÍCULO", ln=True)
    pdf.set_draw_color(30, 60, 120); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 7, f"Cliente: {cliente}", 0)
    pdf.cell(95, 7, f"Vehículo: {vehiculo}", ln=True); pdf.ln(5)
    
    # Tabla
    pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", "B", 9)
    pdf.cell(100, 8, " Descripción", 1, 0, "L", True)
    pdf.cell(20, 8, "Cant.", 1, 0, "C", True)
    pdf.cell(35, 8, "Precio U.", 1, 0, "C", True)
    pdf.cell(35, 8, "Subtotal", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 9)
    for i in items:
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

    tab1, tab2, tab3 = st.tabs(["📝 Presupuestador", "👥 Clientes", "📜 Historial"])

    # --- PESTAÑA 2: GESTIÓN DE CLIENTES ---
    with tab2:
        st.subheader("Registrar Nuevo Cliente")
        with st.form("nuevo_cliente_form", clear_on_submit=True):
            n_cli = st.text_input("Nombre y Apellido")
            t_cli = st.text_input("WhatsApp (Ej: 549...)")
            if st.form_submit_button("💾 Guardar Cliente"):
                if n_cli and t_cli:
                    try:
                        df_c = conn.read(worksheet="Clientes")
                        # Limpiar .0 si viene de un copy-paste
                        t_cli_clean = t_cli[:-2] if t_cli.endswith('.0') else t_cli
                        nuevo_c = pd.DataFrame([{"nombre": n_cli, "telefono": t_cli_clean}])
                        conn.update(worksheet="Clientes", data=pd.concat([df_c, nuevo_c], ignore_index=True))
                        st.success(f"Cliente {n_cli} guardado!")
                        st.cache_data.clear()
                    except Exception as e: st.error(f"Error: {e}")
                else: st.warning("Completa ambos campos")

    # --- PESTAÑA 1: PRESUPUESTADOR ---
    with tab1:
        st.title("Nuevo Trabajo")
        try:
            df_clientes = conn.read(worksheet="Clientes")
            lista_clientes = df_clientes['nombre'].tolist()
        except: lista_clientes = []

        c1, c2 = st.columns(2)
        sel_cliente = c1.selectbox("Seleccionar Cliente:", ["-- Buscar --"] + lista_clientes)
        
        tel_sugerido = ""
        cliente_final = ""
        if sel_cliente != "-- Buscar --":
            cliente_final = sel_cliente
            row_c = df_clientes[df_clientes['nombre'] == sel_cliente].iloc[0]
            t_r = str(row_c['telefono'])
            tel_sugerido = t_r[:-2] if t_r.endswith('.0') else t_r
        else:
            cliente_final = c1.text_input("O escribe nombre manualmente")

        vehiculo = c2.text_input("Vehículo / Patente")
        tel_envio = st.text_input("WhatsApp Cliente", value=tel_sugerido)

        st.write("---")
        try:
            df_precios = conn.read(worksheet="Precios")
            lista_p = df_precios['item'].tolist()
        except: lista_p = []

        col_b, col_c, col_p = st.columns([3, 1, 1])
        op_p = col_b.selectbox("Repuesto/Trabajo:", ["-- Manual --"] + lista_p)
        precio_s = 0.0
        desc_f = ""
        
        if op_p != "-- Manual --":
            desc_f = op_p
            precio_s = float(df_precios[df_precios['item'] == op_p]['precio'].iloc[0])
        else: desc_f = col_b.text_input("Descripción libre")

        cant = col_c.number_input("Cant.", min_value=1, value=1)
        prec = col_p.number_input("Precio $", min_value=0.0, value=precio_s, step=500.0)

        if st.button("➕ Añadir"):
            if desc_f and prec > 0:
                st.session_state.carrito.append({"id": str(uuid.uuid4())[:5], "Descripción": desc_f, "Cantidad": cant, "Precio Unit.": prec, "Subtotal": cant * prec})
                st.rerun()

        if st.session_state.carrito:
            st.write("---")
            for idx, item in enumerate(st.session_state.carrito):
                cl1, cl2, cl3, cl4, cl5 = st.columns([3,1,1,1,0.5])
                cl1.write(item['Descripción'])
                cl2.write(f"x{item['Cantidad']}")
                cl3.write(f"${item['Precio Unit.']:,.0f}")
                cl4.write(f"**${item['Subtotal']:,.0f}**")
                if cl5.button("🗑️", key=f"del_{item['id']}"):
                    st.session_state.carrito.pop(idx); st.rerun()

            total_f = sum(i['Subtotal'] for i in st.session_state.carrito)
            st.subheader(f"Total: ${total_f:,.2f}")

            if st.button("💾 GUARDAR Y GENERAR PDF", use_container_width=True):
                id_p = str(uuid.uuid4())[:8].upper()
                tz = pytz.timezone('America/Argentina/Buenos_Aires')
                fecha_h = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
                
                # Guardar
                res_df = pd.DataFrame([{"usuario": taller['usuario'], "id_presupuesto": id_p, "cliente": cliente_final, "vehiculo": vehiculo, "fecha": fecha_h, "total": total_f}])
                det_df = pd.DataFrame([{"usuario": taller['usuario'], "id_presupuesto": id_p, "descripcion": i["Descripción"], "cantidad": i["Cantidad"], "precio": i["Precio Unit."], "subtotal": i["Subtotal"]} for i in st.session_state.carrito])
                
                conn.update(worksheet="Resumen", data=pd.concat([conn.read(worksheet="Resumen"), res_df], ignore_index=True))
                conn.update(worksheet="Detalles", data=pd.concat([conn.read(worksheet="Detalles"), det_df], ignore_index=True))

                pdf_b = crear_pdf(cliente_final, vehiculo, st.session_state.carrito, total_f, id_p, taller, fecha_h)
                st.download_button("📥 Descargar PDF", pdf_b, f"Presu_{cliente_final}.pdf", "application/pdf")
                
                if tel_envio:
                    msg = f"Hola {cliente_final}, presupuesto de *{taller.get('nombre_taller')}* por ${total_f:,.2f}"
                    st.link_button("📲 Enviar WhatsApp", f"https://wa.me/{tel_envio}?text={urllib.parse.quote(msg)}")
                
                st.session_state.carrito = []; st.cache_data.clear()

    with tab3:
        st.title("Historial")
        try:
            df_r = conn.read(worksheet="Resumen")
            df_d = conn.read(worksheet="Detalles")
            hist = df_r[df_r['usuario'] == taller['usuario']].copy()
            hist['fecha_dt'] = pd.to_datetime(hist['fecha'])
            
            f1, f2, f3 = st.columns([2,1,1])
            busq = f1.text_input("🔍 Buscar Cliente/Patente")
            if busq: hist = hist[hist['cliente'].str.contains(busq, case=False) | hist['vehiculo'].str.contains(busq, case=False)]
            
            for _, row in hist.sort_values('fecha_dt', ascending=False).iterrows():
                with st.expander(f"🚗 {row['vehiculo']} | {row['cliente']} | {row['fecha']}"):
                    st.table(df_d[df_d['id_presupuesto'] == row['id_presupuesto']][['descripcion', 'cantidad', 'precio', 'subtotal']])
                    pdf_re = crear_pdf(row['cliente'], row['vehiculo'], df_d[df_d['id_presupuesto'] == row['id_presupuesto']].to_dict('records'), row['total'], row['id_presupuesto'], taller, row['fecha'])
                    st.download_button("🖨️ PDF", pdf_re, f"RE_{row['id_presupuesto']}.pdf", key=f"re_{row['id_presupuesto']}")
        except: st.info("Sin datos.")
