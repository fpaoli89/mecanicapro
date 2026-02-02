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

# --- FUNCIÓN DE PDF ---
def crear_pdf(cliente_info, vehiculo, items, total, id_p, info_taller, fecha_str):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_fill_color(30, 60, 120) 
    pdf.rect(0, 0, 210, 65, 'F')
    pdf.set_text_color(255, 255, 255)
    
    pdf.set_font("Arial", "B", 22)
    pdf.set_y(10)
    pdf.cell(190, 10, str(info_taller.get('nombre_taller', 'Taller')).upper(), ln=True, align="L")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 6, str(info_taller.get('rubro', 'Servicios')), ln=True, align="L")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 5, f"Email: {info_taller.get('email', '')}", ln=True, align="L")
    pdf.cell(190, 5, f"Dirección: {info_taller.get('direccion', '')} | Tel: {info_taller.get('telefono', '')}", ln=True, align="L")
    pdf.cell(190, 5, f"Presupuesto N°: {id_p} | Fecha: {fecha_str}", ln=True, align="L")
    
    pdf.set_y(75); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, "DATOS DEL CLIENTE Y TRABAJO", ln=True)
    pdf.set_draw_color(30, 60, 120); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 6, f"Cliente: {cliente_info['nombre']}", 0)
    pdf.cell(95, 6, f"Vehículo: {vehiculo}", ln=True)
    pdf.cell(95, 6, f"Domicilio: {cliente_info['domicilio']}", 0)
    pdf.cell(95, 6, f"Localidad: {cliente_info['localidad']}", ln=True); pdf.ln(5)
    
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
                st.session_state.carrito.append({"id": str(uuid.uuid4())[:5], "Descripción": desc_f, "Cantidad": cant, "Precio Unit.": prec, "Subtotal": cant * prec})
                st.rerun()

        if st.session_state.carrito:
            for idx, item in enumerate(st.session_state.carrito):
                cx1, cx2, cx3, cx4, cx5 = st.columns([3,1,1,1,0.5])
                cx1.write(item['Descripción']); cx2.write(f"x{item['Cantidad']}"); cx3.write(f"${item['Precio Unit.']:,.0f}"); cx4.write(f"**${item['Subtotal']:,.0f}**")
                if cx5.button("🗑️", key=f"del_{item['id']}"): st.session_state.carrito.pop(idx); st.rerun()

            total_f = sum(i['Subtotal'] for i in st.session_state.carrito)
            if st.button("💾 GUARDAR Y GENERAR PDF"):
                id_p = str(uuid.uuid4())[:8].upper()
                f_h = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).strftime("%Y-%m-%d %H:%M")
                
                res_df = pd.DataFrame([{"usuario": taller['usuario'], "id_presupuesto": id_p, "cliente": cli_data['nombre'], "vehiculo": vehi, "fecha": f_h, "total": total_f}])
                det_df = pd.DataFrame([{"usuario": taller['usuario'], "id_presupuesto": id_p, "descripcion": i["Descripción"], "cantidad": i["Cantidad"], "precio": i["Precio Unit."], "subtotal": i["Subtotal"]} for i in st.session_state.carrito])
                
                conn.update(worksheet="Resumen", data=pd.concat([conn.read(worksheet="Resumen"), res_df], ignore_index=True))
                conn.update(worksheet="Detalles", data=pd.concat([conn.read(worksheet="Detalles"), det_df], ignore_index=True))
                
                pdf_b = crear_pdf(cli_data, vehi, st.session_state.carrito, total_f, id_p, taller, f_h)
                st.download_button("📥 Descargar Presupuesto", pdf_b, f"Presu_{cli_data['nombre']}.pdf")
                st.session_state.carrito = []; st.cache_data.clear()

    # --- TAB 2: CLIENTES ---
    with tabs[1]:
        st.subheader("Fichas de Clientes")
        with st.expander("➕ Registrar Nuevo Cliente"):
            with st.form("f_new_cli", clear_on_submit=True):
                n_c = st.text_input("Nombre y Apellido")
                t_c = st.text_input("Teléfono")
                d_c = st.text_input("Domicilio")
                l_c = st.text_input("Localidad")
                if st.form_submit_button("Guardar"):
                    df_c_act = conn.read(worksheet="Clientes")
                    new_c = pd.DataFrame([{"nombre": str(n_c), "telefono": str(t_c), "domicilio": str(d_c), "localidad": str(l_c)}])
                    conn.update(worksheet="Clientes", data=pd.concat([df_c_act.astype(str), new_c], ignore_index=True).sort_values("nombre"))
                    st.success("Guardado"); st.cache_data.clear(); st.rerun()

        st.write("---")
        try:
            df_c_edit = conn.read(worksheet="Clientes").astype(str).sort_values("nombre")
            bus_cli = st.text_input("🔎 Filtrar por nombre...")
            df_fil = df_c_edit[df_c_edit['nombre'].str.contains(bus_cli, case=False, na=False)] if bus_cli else df_c_edit
            ed_cli = st.data_editor(df_fil, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Guardar cambios Clientes"):
                df_final_c = pd.concat([df_c_edit[~df_c_edit['nombre'].str.contains(bus_cli, case=False, na=False)], ed_cli]).sort_values("nombre") if bus_cli else ed_cli
                conn.update(worksheet="Clientes", data=df_final_c)
                st.success("Base de datos actualizada"); st.cache_data.clear()
        except: st.info("Carga clientes para ver la lista.")

    # --- TAB 3: STOCK ---
    with tabs[2]:
        st.subheader("Lista de Precios")
        try:
            df_p_edit = conn.read(worksheet="Precios").sort_values("item")
            ed_pre = st.data_editor(df_p_edit, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Guardar cambios Precios"):
                conn.update(worksheet="Precios", data=ed_pre)
                st.success("Precios actualizados"); st.cache_data.clear()
        except: st.info("No hay items cargados.")

    # --- TAB 4: HISTORIAL (FILTRADO AVANZADO) ---
    with tabs[3]:
        st.subheader("Consulta de Presupuestos")
        try:
            df_r = conn.read(worksheet="Resumen")
            df_d = conn.read(worksheet="Detalles")
            
            # Conversión de fecha para filtrado
            df_r['fecha_dt'] = pd.to_datetime(df_r['fecha']).dt.date
            
            # Filtros en columnas
            f1, f2 = st.columns([2, 2])
            filtro_nombre = f1.text_input("🔎 Buscar Cliente", placeholder="Nombre del cliente...")
            rango_fecha = f2.date_input("📅 Rango de Fecha", value=(date.today(), date.today()), key="rango_h")
            
            # Aplicar filtros
            mask = (df_r['usuario'] == taller['usuario'])
            if filtro_nombre:
                mask &= df_r['cliente'].str.contains(filtro_nombre, case=False, na=False)
            
            if len(rango_fecha) == 2:
                mask &= (df_r['fecha_dt'] >= rango_fecha[0]) & (df_r['fecha_dt'] <= rango_fecha[1])
            
            df_hist_filtro = df_r[mask].sort_values('fecha', ascending=False)
            
            st.write(f"Se encontraron **{len(df_hist_filtro)}** presupuestos.")
            
            for _, row in df_hist_filtro.iterrows():
                with st.expander(f"📄 {row['fecha']} | {row['cliente']} | ${row['total']:,.0f}"):
                    st.write(f"**Vehículo:** {row['vehiculo']}")
                    st.write("**Detalles:**")
                    items_presu = df_d[df_d['id_presupuesto'] == row['id_presupuesto']]
                    st.table(items_presu[['descripcion', 'cantidad', 'precio', 'subtotal']])
                    st.write(f"**ID:** {row['id_presupuesto']}")
        except Exception as e:
            st.info("No se encontraron registros o error en la carga.")
