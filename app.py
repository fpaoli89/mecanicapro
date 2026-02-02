import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
from fpdf import FPDF
import urllib.parse
import pytz

# 1. Configuración de página
st.set_page_config(page_title="Sistema Integral de Taller", layout="centered", page_icon="🔧")

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
            tel = str(datos.get('telefono', ''))
            datos['telefono'] = tel[:-2] if tel.endswith('.0') else tel
            datos.setdefault('rubro', 'Servicios Especializados')
            datos.setdefault('email', 'taller@contacto.com')
            return datos
        return None
    except Exception as e:
        st.error(f"Error en Usuarios: {e}")
        return None

# --- FUNCIÓN DE PDF (4 LÍNEAS DE ENCABEZADO) ---
def crear_pdf(cliente, vehiculo, items, total, id_p, info, fecha_str):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_fill_color(30, 60, 120) 
    pdf.rect(0, 0, 210, 65, 'F')
    pdf.set_text_color(255, 255, 255)
    
    # Línea 1: Taller
    pdf.set_font("Arial", "B", 22)
    pdf.set_y(10)
    pdf.cell(190, 10, str(info.get('nombre_taller', 'Taller')).upper(), ln=True, align="L")
    
    # Línea 2: Rubro
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 6, str(info.get('rubro', '')), ln=True, align="L")
    
    # Línea 3: Email
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 5, f"Email: {info.get('email', '')}", ln=True, align="L")
    
    # Línea 4: Dirección y Teléfono
    pdf.cell(190, 5, f"Dirección: {info.get('direccion', '')} | Tel: {info.get('telefono', '')}", ln=True, align="L")
    
    pdf.cell(190, 5, f"Presupuesto N°: {id_p} | Fecha: {fecha_str}", ln=True, align="L")
    
    pdf.set_y(75); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, "DETALLES DEL TRABAJO", ln=True)
    pdf.set_draw_color(30, 60, 120); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 7, f"Cliente: {cliente}", 0)
    pdf.cell(95, 7, f"Vehículo: {vehiculo}", ln=True); pdf.ln(5)
    
    # Tabla de items
    pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", "B", 9)
    pdf.cell(100, 8, " Descripción", 1, 0, "L", True)
    pdf.cell(20, 8, "Cant.", 1, 0, "C", True)
    pdf.cell(35, 8, "Precio U.", 1, 0, "C", True)
    pdf.cell(35, 8, "Subtotal", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 9)
    for i in items:
        pdf.cell(100, 8, f" {i['Descripción']}", 1)
        pdf.cell(20, 8, str(i['Cantidad']), 1, 0, "C")
        pdf.cell(35, 8, f"${i['Precio Unit.']:,.2f}", 1, 0, "R")
        pdf.cell(35, 8, f"${i['Subtotal']:,.2f}", 1, 1, "R")

    pdf.ln(3)
    pdf.set_font("Arial", "B", 12); pdf.set_fill_color(30, 60, 120); pdf.set_text_color(255, 255, 255)
    pdf.cell(155, 10, "TOTAL FINAL ", 0, 0, "R", True)
    pdf.cell(35, 10, f"${float(total):,.2f} ", 0, 1, "R", True)
    
    pdf.set_y(265); pdf.set_text_color(100, 100, 100); pdf.set_font("Arial", "B", 10)
    pdf.cell(190, 10, str(info.get('leyenda', '')), 0, 0, "C")
    return pdf.output(dest="S").encode("latin-1")

# --- LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = None

if st.session_state.auth is None:
    st.title("🔐 Acceso Sistema Taller")
    with st.form("login"):
        u, p = st.text_input("Usuario"), st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            datos = validar_usuario(u, p)
            if datos: st.session_state.auth = datos; st.rerun()
            else: st.error("Usuario o contraseña incorrectos")
else:
    taller = st.session_state.auth
    st.sidebar.title(f"🔧 {taller['nombre_taller']}")
    if st.sidebar.button("Cerrar Sesión"): st.session_state.auth = None; st.rerun()

    if 'carrito' not in st.session_state: st.session_state.carrito = []

    tabs = st.tabs(["📝 Presupuesto", "👥 Clientes", "📦 Stock/Precios", "📜 Historial"])

    # --- TAB 1: PRESUPUESTADOR ---
    with tabs[0]:
        st.title("Nuevo Presupuesto")
        try:
            df_cli = conn.read(worksheet="Clientes")
            # Ordenar alfabéticamente los clientes
            lista_cli = sorted(df_cli['nombre'].astype(str).tolist())
        except: lista_cli = []

        c1, c2 = st.columns(2)
        sel_c = c1.selectbox("Seleccionar Cliente:", ["-- Buscar --"] + lista_cli)
        tel_sug, cli_f = "", ""
        if sel_c != "-- Buscar --":
            cli_f = sel_c
            row_c = df_cli[df_cli['nombre'] == sel_c].iloc[0]
            t_r = str(row_c['telefono'])
            tel_sug = t_r[:-2] if t_r.endswith('.0') else t_r
        else: cli_f = c1.text_input("Nombre de Cliente")

        vehi = c2.text_input("Vehículo / Patente")
        tel_w = st.text_input("WhatsApp para enviar", value=tel_sug)

        st.write("---")
        try:
            df_pre = conn.read(worksheet="Precios")
            # Ordenar alfabéticamente los items de precios
            lista_pre = sorted(df_pre['item'].astype(str).tolist())
        except: lista_pre = []

        col_b, col_c, col_p = st.columns([3, 1, 1])
        op_p = col_b.selectbox("Elegir Item:", ["-- Manual --"] + lista_pre)
        p_sug, desc_f = 0.0, ""
        if op_p != "-- Manual --":
            desc_f = op_p
            p_sug = float(df_pre[df_pre['item'] == op_p]['precio'].iloc[0])
        else: desc_f = col_b.text_input("Descripción Manual")

        cant = col_c.number_input("Cant.", min_value=1, value=1)
        prec = col_p.number_input("Precio $", min_value=0.0, value=p_sug)

        if st.button("➕ Agregar al Listado"):
            if desc_f and prec > 0:
                st.session_state.carrito.append({"id": str(uuid.uuid4())[:5], "Descripción": desc_f, "Cantidad": cant, "Precio Unit.": prec, "Subtotal": cant * prec})
                st.rerun()

        if st.session_state.carrito:
            for idx, item in enumerate(st.session_state.carrito):
                cx1, cx2, cx3, cx4, cx5 = st.columns([3,1,1,1,0.5])
                cx1.write(item['Descripción'])
                cx2.write(f"x{item['Cantidad']}")
                cx3.write(f"${item['Precio Unit.']:,.0f}")
                cx4.write(f"**${item['Subtotal']:,.0f}**")
                if cx5.button("🗑️", key=f"del_{item['id']}"):
                    st.session_state.carrito.pop(idx); st.rerun()

            total_final = sum(i['Subtotal'] for i in st.session_state.carrito)
            st.subheader(f"Total: ${total_final:,.2f}")
            if st.button("💾 FINALIZAR Y GENERAR PDF", use_container_width=True):
                id_p = str(uuid.uuid4())[:8].upper()
                tz = pytz.timezone('America/Argentina/Buenos_Aires')
                f_h = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
                
                res_df = pd.DataFrame([{"usuario": taller['usuario'], "id_presupuesto": id_p, "cliente": cli_f, "vehiculo": vehi, "fecha": f_h, "total": total_final}])
                det_df = pd.DataFrame([{"usuario": taller['usuario'], "id_presupuesto": id_p, "descripcion": i["Descripción"], "cantidad": i["Cantidad"], "precio": i["Precio Unit."], "subtotal": i["Subtotal"]} for i in st.session_state.carrito])
                
                conn.update(worksheet="Resumen", data=pd.concat([conn.read(worksheet="Resumen"), res_df], ignore_index=True))
                conn.update(worksheet="Detalles", data=pd.concat([conn.read(worksheet="Detalles"), det_df], ignore_index=True))

                pdf_bytes = crear_pdf(cli_f, vehi, st.session_state.carrito, total_final, id_p, taller, f_h)
                st.download_button("📥 Descargar PDF", pdf_bytes, f"Presu_{cli_f}.pdf")
                if tel_w:
                    msg = f"Hola {cli_f}, te envío el presupuesto de *{taller['nombre_taller']}* por un total de ${total_final:,.2f}"
                    st.link_button("📲 Enviar por WhatsApp", f"https://wa.me/{tel_w}?text={urllib.parse.quote(msg)}")
                st.session_state.carrito = []; st.cache_data.clear()

    # --- TAB 2: GESTIÓN DE CLIENTES (ORDENADOS) ---
    with tabs[1]:
        st.subheader("Registrar Nuevo Cliente")
        with st.form("form_c", clear_on_submit=True):
            n_c = st.text_input("Nombre y Apellido")
            t_c = st.text_input("Número WhatsApp (Ej: 549...)")
            if st.form_submit_button("Guardar Cliente"):
                df_act = conn.read(worksheet="Clientes")
                nuevo_c = pd.DataFrame([{"nombre": n_c, "telefono": t_c}])
                df_total = pd.concat([df_act, nuevo_c], ignore_index=True).sort_values("nombre")
                conn.update(worksheet="Clientes", data=df_total)
                st.success("Cliente guardado y lista ordenada"); st.cache_data.clear()

    # --- TAB 3: STOCK Y PRECIOS (ORDENADOS) ---
    with tabs[2]:
        st.subheader("Carga de Productos / Servicios")
        with st.expander("➕ Agregar Nuevo Item a la Lista"):
            with st.form("form_p", clear_on_submit=True):
                it_n = st.text_input("Descripción del Producto/Servicio")
                pr_n = st.number_input("Precio base $", min_value=0.0, step=500.0)
                if st.form_submit_button("Guardar Item"):
                    df_pre_act = conn.read(worksheet="Precios")
                    nuevo_p = pd.DataFrame([{"item": it_n, "precio": pr_n}])
                    df_p_total = pd.concat([df_pre_act, nuevo_p], ignore_index=True).sort_values("item")
                    conn.update(worksheet="Precios", data=df_p_total)
                    st.success("Item guardado y lista actualizada"); st.cache_data.clear(); st.rerun()

        st.write("---")
        st.subheader("Editor de Precios")
        try:
            df_edit = conn.read(worksheet="Precios").sort_values("item")
            edited_df = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Guardar Cambios en Precios"):
                conn.update(worksheet="Precios", data=edited_df.sort_values("item"))
                st.success("Precios actualizados correctamente"); st.cache_data.clear()
        except: st.info("Carga tu primer item arriba.")

    # --- TAB 4: HISTORIAL ---
    with tabs[3]:
        st.subheader("Historial de Presupuestos")
        try:
            df_r = conn.read(worksheet="Resumen")
            df_d = conn.read(worksheet="Detalles")
            # Filtrar por usuario actual
            hist = df_r[df_r['usuario'] == taller['usuario']].copy()
            for _, row in hist.sort_values('fecha', ascending=False).iterrows():
                with st.expander(f"📅 {row['fecha']} - {row['cliente']} ({row['vehiculo']})"):
                    items_h = df_d[df_d['id_presupuesto'] == row['id_presupuesto']]
                    st.table(items_h[['descripcion', 'cantidad', 'precio', 'subtotal']])
                    st.write(f"**Total: ${row['total']:,.2f}**")
        except: st.info("Aún no tienes presupuestos guardados.")
