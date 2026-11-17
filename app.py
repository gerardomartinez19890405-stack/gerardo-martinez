import streamlit as st
from datetime import datetime
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
import pandas as pd
import json
import os

# Configuración de la página
st.set_page_config(page_title="Bitácora Vehicular GPS", page_icon="🚗", layout="centered")

# Archivos locales para que los datos NO se borren al cerrar la app
ARCHIVO_FLOTA = "flota_vehiculos.json"
ARCHIVO_BITACORAS = "historial_bitacoras.csv"

def cargar_flota():
    if os.path.exists(ARCHIVO_FLOTA):
        with open(ARCHIVO_FLOTA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {} # Inicia totalmente vacío para que tú registres tu vehículo primero

def guardar_flota(flota):
    with open(ARCHIVO_FLOTA, "w", encoding="utf-8") as f:
        json.dump(flota, f, indent=4, ensure_ascii=False)

def guardar_bitacora_csv(registro):
    df_nuevo = pd.DataFrame([registro])
    if os.path.exists(ARCHIVO_BITACORAS):
        df_nuevo.to_csv(ARCHIVO_BITACORAS, mode="a", header=False, index=False, encoding="utf-8")
    else:
        df_nuevo.to_csv(ARCHIVO_BITACORAS, mode="w", header=True, index=False, encoding="utf-8")

# Inicializar estados
if "flota" not in st.session_state:
    st.session_state.flota = cargar_flota()

if "viaje_activo" not in st.session_state:
    st.session_state.viaje_activo = False

if "puntos_gps" not in st.session_state:
    st.session_state.puntos_gps = []

st.title("🚗 Sistema de Control Vehicular y Bitácora GPS")

# Pestañas superiores (más cómodas en el celular que el menú lateral)
tab_viaje, tab_flota, tab_historial = st.tabs(["🚀 Bitácora en Ruta", "➕ Registrar Vehículo", "📊 Historial Guardado"])

# ==========================================
# PESTAÑA 2: REGISTRAR VEHÍCULO (INICIA VACÍA)
# ==========================================
with tab_flota:
    st.subheader("📝 Alta de Vehículo y Motorista")
    st.caption("Agrega aquí tu vehículo para comenzar, o registra toda la flota institucional.")
    
    with st.form("form_alta_vehiculo", clear_on_submit=True):
        placa = st.text_input("Número de Placa (Ej. P-123456)").upper().strip()
        modelo = st.text_input("Marca y Modelo (Ej. Jeep Liberty 2005)")
        motorista = st.text_input("Nombre Completo del Motorista Asignado")
        dui = st.text_input("Número de DUI (Ej. 00000000-0)")
        
        if st.form_submit_button("💾 Guardar Vehículo en Sistema", type="primary"):
            if placa and modelo and motorista and dui:
                st.session_state.flota[placa] = {
                    "modelo": modelo,
                    "motorista": motorista,
                    "dui": dui
                }
                guardar_flota(st.session_state.flota)
                st.success(f"✅ Vehículo **{placa} ({modelo})** registrado correctamente.")
            else:
                st.error("⚠️ Por favor completa todos los campos.")

    if st.session_state.flota:
        st.markdown("### Vehículos Registrados Actualmente")
        for p, datos in st.session_state.flota.items():
            st.write(f"- **{p}** | {datos['modelo']} — Motorista: {datos['motorista']} (DUI: {datos['dui']})")

# ==========================================
# PESTAÑA 1: REGISTRO DE VIAJE Y GPS REAL
# ==========================================
with tab_viaje:
    # Capturar ubicación GPS real del dispositivo
    ubicacion = get_geolocation()
    lat_actual, lon_actual = None, None
    
    if ubicacion and "coords" in ubicacion:
        lat_actual = ubicacion["coords"]["latitude"]
        lon_actual = ubicacion["coords"]["longitude"]

    # --- ESTADO A: LISTO PARA SALIR ---
    if not st.session_state.viaje_activo:
        if not st.session_state.flota:
            st.warning("👋 Aún no hay vehículos registrados. Ve a la pestaña **'➕ Registrar Vehículo'** de arriba para agregar tu auto.")
        else:
            st.subheader("📋 Registro de Salida (Origen)")
            
            if lat_actual and lon_actual:
                st.success(f"📡 Señal GPS Activa: `{lat_actual:.5f}, {lon_actual:.5f}`")
            else:
                st.info("📡 Esperando permiso de ubicación GPS en tu navegador (acepta el permiso si te lo pide)...")

            placa_sel = st.selectbox("Seleccione la Placa", list(st.session_state.flota.keys()))
            info_v = st.session_state.flota[placa_sel]
            st.info(f"**Vehículo:** {info_v['modelo']} | **Motorista:** {info_v['motorista']} (DUI: {info_v['dui']})")

            emergencia = st.checkbox("⚠️ Salida de Emergencia / Conductor Suplente")
            if emergencia:
                conductor_final = st.text_input("Nombre del Conductor Suplente")
                dui_final = st.text_input("DUI del Suplente")
                licencia_final = st.text_input("N° de Licencia")
            else:
                conductor_final = info_v["motorista"]
                dui_final = info_v["dui"]
                licencia_final = "Titular registrado"

            origen = st.text_input("Lugar de Salida (Origen)", value="Base / Residencia Usulután")
            destino = st.text_input("Destino Previsto (Ej. San Miguel)")
            km_inicial = st.number_input("Kilometraje Inicial (Odómetro del tablero)", min_value=0.0, step=1.0)

            if st.button("🚀 Iniciar Recorrido", type="primary"):
                if km_inicial > 0 and destino and conductor_final:
                    # Si el navegador aún no da GPS, usamos coordenada base de Usulután como respaldo
                    lat_ini = lat_actual if lat_actual else 13.3444
                    lon_ini = lon_actual if lon_actual else -88.4444
                    
                    st.session_state.viaje_activo = True
                    st.session_state.puntos_gps = [[lat_ini, lon_ini]]
                    st.session_state.datos_viaje = {
                        "placa": placa_sel,
                        "modelo": info_v["modelo"],
                        "conductor": conductor_final,
                        "dui": dui_final,
                        "licencia": licencia_final,
                        "origen": origen,
                        "destino": destino,
                        "km_inicial": km_inicial,
                        "hora_salida": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "hora_llegada_destino": "Pendiente"
                    }
                    st.rerun()
                else:
                    st.error("Completa el kilometraje inicial y el destino para arrancar.")

    # --- ESTADO B: VIAJE EN CURSO ---
    else:
        viaje = st.session_state.datos_viaje
        st.warning("🔴 **RECORRIDO EN CURSO**")
        st.write(f"**Vehículo:** {viaje['placa']} ({viaje['modelo']}) | **Conductor:** {viaje['conductor']}")
        st.write(f"**Salida:** {viaje['origen']} ({viaje['hora_salida']}) | **Odómetro Inicial:** {viaje['km_inicial']} km")

        # Si hay nueva lectura GPS distinta, la agregamos a la ruta
        if lat_actual and lon_actual:
            ultimo_punto = st.session_state.puntos_gps[-1]
            if [lat_actual, lon_actual] != ultimo_punto:
                st.session_state.puntos_gps.append([lat_actual, lon_actual])

        # Botón para registrar llegada al punto de destino (Ej. Al llegar a San Miguel antes de regresar)
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📍 Marcar Llegada a Destino"):
                st.session_state.datos_viaje["hora_llegada_destino"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if lat_actual and lon_actual:
                    st.session_state.puntos_gps.append([lat_actual, lon_actual])
                st.rerun()
        with col2:
            if st.button("🔄 Actualizar Punto GPS"):
                st.rerun()

        if viaje["hora_llegada_destino"] != "Pendiente":
            st.success(f"✅ Llegada a destino ({viaje['destino']}) marcada a las: **{viaje['hora_llegada_destino']}**")

        # Mostrar mapa en vivo con los puntos capturados
        mapa_vivo = folium.Map(location=st.session_state.puntos_gps[-1], zoom_start=12)
        folium.Marker(st.session_state.puntos_gps[0], popup="Origen", icon=folium.Icon(color="green")).add_to(mapa_vivo)
        if len(st.session_state.puntos_gps) > 1:
            folium.Marker(st.session_state.puntos_gps[-1], popup="Ubicación Actual", icon=folium.Icon(color="blue")).add_to(mapa_vivo)
            folium.PolyLine(st.session_state.puntos_gps, color="blue", weight=4).add_to(mapa_vivo)
        st_folium(mapa_vivo, height=280, width=700)

        st.markdown("---")
        st.subheader("🏁 Cierre de Bitácora (Retorno a Origen)")
        km_final = st.number_input("Kilometraje Final (Odómetro de retorno)", min_value=viaje["km_inicial"], step=1.0)
        factura = st.text_input("N° Factura / Vale de Combustible (Opcional)")
        galones = st.number_input("Galones cargados (Opcional)", min_value=0.0, step=0.1)

        if st.button("✅ Finalizar Recorrido y Guardar Bitácora", type="primary"):
            if km_final >= viaje["km_inicial"]:
                if lat_actual and lon_actual:
                    st.session_state.puntos_gps.append([lat_actual, lon_actual])
                
                hora_cierre = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                km_totales = km_final - viaje["km_inicial"]

                # Guardar en archivo CSV permanente
                registro_final = {
                    "Fecha_Salida": viaje["hora_salida"],
                    "Hora_Llegada_Destino": viaje["hora_llegada_destino"],
                    "Hora_Retorno_Final": hora_cierre,
                    "Placa": viaje["placa"],
                    "Vehiculo": viaje["modelo"],
                    "Conductor": viaje["conductor"],
                    "DUI": viaje["dui"],
                    "Origen": viaje["origen"],
                    "Destino": viaje["destino"],
                    "Km_Inicial": viaje["km_inicial"],
                    "Km_Final": km_final,
                    "Km_Recorridos": km_totales,
                    "Factura_Combustible": factura if factura else "N/A",
                    "Galones": galones,
                    "Coordenadas_Ruta": str(st.session_state.puntos_gps)
                }
                guardar_bitacora_csv(registro_final)

                st.session_state.viaje_activo = False
                st.success("🎉 ¡Bitácora guardada permanentemente en el historial!")
                st.balloons()
                st.rerun()
            else:
                st.error("El kilometraje final no puede ser menor al inicial.")

# ==========================================
# PESTAÑA 3: HISTORIAL GUARDADO Y EVIDENCIA MAPA
# ==========================================
with tab_historial:
    st.subheader("📊 Registro Histórico de Bitácoras")
    if os.path.exists(ARCHIVO_BITACORAS):
        df = pd.read_csv(ARCHIVO_BITACORAS)
        st.dataframe(df.drop(columns=["Coordenadas_Ruta"]), use_container_width=True)
        
        # Botón para descargar en Excel/CSV para el Jefe de Transporte
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar Reporte Completo (CSV / Excel)", data=csv_data, file_name="bitacoras_flota.csv", mime="text/csv")

        st.markdown("---")
        st.markdown("### 🗺️ Ver Evidencia de Ruta GPS de un Viaje")
        indice = st.selectbox("Seleccione el número de viaje a visualizar:", df.index, format_func=lambda x: f"Viaje #{x+1} - {df.loc[x, 'Placa']} ({df.loc[x, 'Fecha_Salida']} -> {df.loc[x, 'Destino']})")
        
        coords_str = df.loc[indice, "Coordenadas_Ruta"]
        puntos = eval(coords_str)
        
        mapa_evidencia = folium.Map(location=puntos[0], zoom_start=11)
        folium.Marker(puntos[0], popup="Salida (Origen)", icon=folium.Icon(color="green")).add_to(mapa_evidencia)
        if len(puntos) > 1:
            folium.Marker(puntos[-1], popup="Punto Final / Retorno", icon=folium.Icon(color="red")).add_to(mapa_evidencia)
            folium.PolyLine(puntos, color="blue", weight=4).add_to(mapa_evidencia)
        st_folium(mapa_evidencia, height=350, width=700)
    else:
        st.info("Aún no hay bitácoras finalizadas. Cuando completes tu primer recorrido aparecerá aquí.")