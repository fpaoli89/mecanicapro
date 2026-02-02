import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import uuid
from fpdf import FPDF
import urllib.parse
import pytz

# 1. Configuración de página
st.set_page_config(page_title="Gestión Integral Taller", layout="centered", page_icon="🔧")

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
            return datos
        return None
    except Exception as e:
        st.error(f"Error en Usuarios: {e}")
        return None

# --- FUNCIÓN DE PDF (NEGRO Y ROJO) ---
def crear_pdf(cliente_info, vehiculo, items, total, id_p, info_taller, fecha_str):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_fill_color(0, 0, 0) 
    pdf.rect(0, 0, 210, 65, 'F')
    pdf.set_text_color(255, 255, 255)
    
    pdf.set_font("Arial", "B", 22)
    pdf.set_y(10)
    pdf.set_text_color(220, 20, 60) # Rojo intenso
    pdf.cell(190, 10, str(info_taller.get('nombre_taller', 'Taller')).upper(), ln=True, align="L")
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 6, str(info_taller.get('rubro', 'Servicios')), ln=True, align="L")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 5, f"Email: {info_taller.get('email', '')}", ln=True, align="L")
    pdf.cell(190, 5, f"Dirección: {info_taller.get('direccion', '')} | Tel: {info_taller.get('telefono', '')}", ln=True, align="L")
    pdf.cell(190, 5, f"Presupuesto N°: {id_p} | Fecha: {fecha_str}", ln=True, align="L")
    
    pdf.set_y(75); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, "DATOS DEL CLIENTE Y TRABAJO", ln=True)
    pdf.set_draw_color(220, 20, 60); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 6, f"Cliente: {cliente_info['nombre']}", 0)
    pdf.cell(95, 6, f"Vehículo: {vehiculo}", ln=True)
    pdf.cell(95, 6, f"Domicilio: {cliente_info['domicilio']}", 0)
    pdf.cell(95, 6, f"Localidad: {cliente_info['localidad']}", ln=True); pdf.ln(5)
    
    pdf.set_fill_color(220, 20, 60); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", "B", 9)
    pdf.cell(100, 8, " Descripción", 1, 0, "L", True)
    pdf.cell(20, 8, "Cant.", 1, 0, "C", True)
    pdf.cell(35, 8, "Precio U.", 1, 0, "C", True)
    pdf.cell(35, 8, "Subtotal", 1, 1, "C", True)
    
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 9)
    for i in items:
        desc = i['Descripción'] if 'Descripción' in i else i['descripcion']
        cant = i['Cantidad'] if 'Cantidad' in i else i['cantidad']
        prec = i['Precio Unit.'] if 'Precio Unit.' in i else i['precio']
        subt = i['Subtotal'] if 'Subtotal' in i else i['subtotal']
        pdf.cell(100, 8, f" {desc}", 1)
        pdf.cell(20, 8, str(cant), 1, 0, "C")
        pdf.cell(35, 8, f"${float(prec):,.2f}", 1, 0, "R")
        pdf.cell(35, 8, f"${float(subt):,.2f}", 1, 1, "R")

    pdf.ln(3)
    pdf.set_font("Arial", "B", 12); pdf.set_fill_color(0, 0, 0); pdf.set_text_color(255, 255, 255)
    pdf.cell(155, 10, "TOTAL FINAL ", 0, 0, "R", True)
    pdf.cell(35, 10, f"${float(total):,.2f} ", 0, 1, "R", True)
    
    pdf.set_y(265); pdf.set_text_color(100, 100, 100); pdf.set_font("Arial", "B", 10)
    pdf.cell(190, 10, str(info_taller.get('leyenda', '')), 0, 0, "C")
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
            else: st.error("Acceso denegado")
else:
    taller = st.session_state.auth
    st.sidebar.title(f"🔧 {taller['nombre_taller']}")
    if st.sidebar.button("Cerrar Sesión"): st.session_state.auth = None; st.rerun()
    st.sidebar.markdown("---")
    st.sidebar.caption("FAPSOFTWARE - versión 1.0")
    st.sidebar.caption("by Fernando Paoli")

    if 'carrito' not in st.session_state: st.session_state.carrito = []

    tabs = st.tabs(["📝 Presupuesto", "👥 Clientes", "📦 Stock", "📜 Historial"])

    # --- TAB 1: PRESUPUESTADOR ---
    with tabs[0]:
        st.title("Nuevo Presupuesto")
        try:
            df_cli_raw = conn.read(worksheet="Clientes")
            lista_cli = sorted(df_cli_raw['nombre'].astype(str).tolist())
        except: lista_cli = []

        c1, c2 = st.columns(2)
        sel_c = c1.selectbox("Seleccionar Cliente:", ["-- Buscar --"] + lista_cli)
        cli_data = {"nombre": "", "telefono": "", "domicilio": "", "localidad": ""}
        
        if sel_c != "-- Buscar --":
            row_c = df_cli_raw[df_cli_raw['nombre'] == sel_c].iloc[0]
            cli_data = {"nombre": sel_c, "telefono": str(row_c['telefono']), "domicilio": str(row_c.get('domicilio', '')), "localidad": str(row_c.get('localidad', ''))}
            if cli_data['telefono'].endswith('.0'): cli_data['telefono'] = cli_data['telefono'][:-2]
        else:
            cli_data['nombre'] = c1.text_input("Nombre Manual")

        vehi = c2.text_input("Vehículo / Patente")
        tel_w = st.text_input("WhatsApp Cliente", value=cli_data['telefono'])

        st.write("---")
        try:
            df_pre_raw = conn.read(worksheet="Precios")
            lista_pre = sorted(df_pre_raw['item'].astype(str).tolist())
        except: lista_pre = []

        col_b, col_c, col_p = st.columns([3, 1, 1])
        op_p = col_b.selectbox("Repuesto/Servicio:", ["-- Manual --"] + lista_pre)
        p_sug, desc_f = 0.0, ""
        if op_p != "-- Manual --":
            desc_f = op_p
            p_sug = float(df_pre_raw[df_pre_raw['item'] == op_p]['precio'].iloc[0])
        else: desc_f = col_b.text_input("Descripción")

        cant = col_c.number_input("Cant.", min_value=1, value=1)
        prec = col_p.number_input("Precio $", min_value=0.0, value=p_sug)

        if st.button("➕ Añadir"):
            if desc_f and prec > 0:
                st.session_state.carrito.append({"id": str(uuid.uuid4())[:5], "Descripción": desc_f, "Cantidad": int(cant), "Precio Unit.": float(prec), "Subtotal": float(cant * prec)})
                st.rerun()

        if st.session_state.carrito:
            st.write("### Detalle")
            for idx, item in enumerate(st.session_state.carrito):
                cx1, cx2, cx3, cx4, cx5 = st.columns([3,1,1,1,0.5])
                cx1.write(item['Descripción']); cx2.write(f"x{item['Cantidad']}"); cx3.write(f"${item['Precio Unit.']:,.0f}"); cx4.write(f"**${item['Subtotal']:,.0f}**")
                if cx5.button("🗑️", key=f"del_{item['id']}"): st.session_state.carrito.pop(idx); st.rerun()

            total_f = sum(i['Subtotal'] for i in st.session_state.carrito)
            st.write("---")
            st.subheader(f"Total Carrito: ${total_f:,.2f}")

            # Botones alineados a la derecha
            b1, b2, b3, b4 = st.columns([2, 1, 1, 1])
            if b2.button("💾 GUARDAR", use_container_width=True):
                id_p = str(uuid.uuid4())[:8].upper()
                f_h = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).strftime("%Y-%m-%d %H:%M")
                res_df = pd.DataFrame([{"usuario": taller['usuario'], "id_presupuesto": id_p, "cliente": cli_data['nombre'], "vehiculo": vehi, "fecha": f_h, "total": total_f}])
                det_df = pd.DataFrame([{"usuario": taller['usuario'], "id_presupuesto": id_p, "descripcion": i["Descripción"], "cantidad": i["Cantidad"], "precio": i["Precio Unit."], "subtotal": i["Subtotal"]} for i in st.session_state.carrito])
                conn.update(worksheet="Resumen", data=pd.concat([conn.read(worksheet="Resumen"), res_df], ignore_index=True))
                conn.update(worksheet="Detalles", data=pd.concat([conn.read(worksheet="Detalles"), det_df], ignore_index=True))
                st.success(f"Guardado como {id_p}")
                st.session_state['ultimo_pdf'] = {"cli": cli_data, "vehi": vehi, "car": list(st.session_state.carrito), "tot": total_f, "id": id_p, "fec": f_h}
                st.session_state.carrito = []; st.cache_data.clear()
            
            if 'ultimo_pdf' in st.session_state:
                u = st.session_state['ultimo_pdf']
                pdf_b = crear_pdf(u['cli'], u['vehi'], u['car'], u['tot'], u['id'], taller, u['fec'])
                b3.download_button("📥 PDF", pdf_b, f"Presu_{u['cli']['nombre']}.pdf", use_container_width=True)
                
                msg = urllib.parse.quote(f"Hola {u['cli']['nombre']}, adjunto el presupuesto para {u['vehi']} por un total de ${u['tot']:,.2f}.")
                url_w = f"https://wa.me/{tel_w}?text={msg}"
                b4.link_button("📲 WHATSAPP", url_w, use_container_width=True)

    # --- TAB 2: CLIENTES ---
    with tabs[1]:
        st.subheader("Gestión de Clientes")
        with st.expander("➕ Nuevo Cliente"):
            with st.form("f_new_cli", clear_on_submit=True):
                n_c, t_c = st.text_input("Nombre"), st.text_input("Teléfono")
                d_c, l_c = st.text_input("Domicilio"), st.text_input("Localidad")
                if st.form_submit_button("Guardar"):
                    df_c_act = conn.read(worksheet="Clientes")
                    new_c = pd.DataFrame([{"nombre": str(n_c), "telefono": str(t_c), "domicilio": str(d_c), "localidad": str(l_c)}])
                    conn.update(worksheet="Clientes", data=pd.concat([df_c_act.astype(str), new_c], ignore_index=True).sort_values("nombre"))
                    st.success("Guardado"); st.cache_data.clear(); st.rerun()
        try:
            df_c_edit = conn.read(worksheet="Clientes").astype(str).sort_values("nombre")
            bus_cli = st.text_input("🔎 Filtrar cliente...")
            df_fil = df_c_edit[df_c_edit['nombre'].str.contains(bus_cli, case=False, na=False)] if bus_cli else df_c_edit
            ed_cli = st.data_editor(df_fil, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Actualizar Clientes"):
                df_final_c = pd.concat([df_c_edit[~df_c_edit['nombre'].str.contains(bus_cli, case=False, na=False)], ed_cli]).sort_values("nombre") if bus_cli else ed_cli
                conn.update(worksheet="Clientes", data=df_final_c)
                st.success("Base actualizada"); st.cache_data.clear()
        except: st.info("Sin datos.")

    # --- TAB 3: STOCK ---
    with tabs[2]:
        st.subheader("Lista de Precios")
        try:
            df_p_edit = conn.read(worksheet="Precios").sort_values("item")
            ed_pre = st.data_editor(df_p_edit, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Actualizar Precios"):
                conn.update(worksheet="Precios", data=ed_pre)
                st.success("Precios actualizados"); st.cache_data.clear()
        except: st.info("Carga items.")

    # --- TAB 4: HISTORIAL ---
    with tabs[3]:
        st.subheader("Consulta e Impresión")
        try:
            df_r, df_d = conn.read(worksheet="Resumen"), conn.read(worksheet="Detalles")
            df_c_info = conn.read(worksheet="Clientes").astype(str)
            df_r['fecha_dt'] = pd.to_datetime(df_r['fecha']).dt.date
            f1, f2 = st.columns(2)
            filtro_h = f1.text_input("🔎 Buscar en Historial")
            rango_h = f2.date_input("📅 Rango", value=(date.today(), date.today()))
            
            mask = (df_r['usuario'] == taller['usuario'])
            if filtro_h: mask &= df_r['cliente'].str.contains(filtro_h, case=False, na=False)
            if len(rango_h) == 2: mask &= (df_r['fecha_dt'] >= rango_h[0]) & (df_r['fecha_dt'] <= rango_h[1])
            
            df_hist_filtro = df_r[mask].sort_values('fecha', ascending=False)
            for _, row in df_hist_filtro.iterrows():
                with st.expander(f"📄 {row['fecha']} | {row['cliente']} | ${row['total']:,.0f}"):
                    items_presu = df_d[df_d['id_presupuesto'] == row['id_presupuesto']]
                    st.write(f"**Vehículo:** {row['vehiculo']}")
                    st.table(items_presu[['descripcion', 'cantidad', 'precio', 'subtotal']])
                    
                    info_c_re = df_c_info[df_c_info['nombre'] == row['cliente']]
                    c_re_data = {"nombre": row['cliente'], "domicilio": info_c_re['domicilio'].iloc[0] if not info_c_re.empty else "", "localidad": info_c_re['localidad'].iloc[0] if not info_c_re.empty else ""}
                    pdf_re = crear_pdf(c_re_data, row['vehiculo'], items_presu.to_dict('records'), row['total'], row['id_presupuesto'], taller, row['fecha'])
                    st.download_button("📥 Descargar PDF", pdf_re, f"Re_{row['id_presupuesto']}.pdf", key=f"re_{row['id_presupuesto']}")
        except: st.info("Sin registros.")

    st.write("---")
    st.caption("FAPSOFTWARE - versión 1.0 - by Fernando Paoli")
