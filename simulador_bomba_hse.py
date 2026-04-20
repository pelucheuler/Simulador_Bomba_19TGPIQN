import streamlit as st
import pandas as pd
from datetime import datetime
import random
from sqlalchemy import create_engine, text
import streamlit.components.v1 as components

# ==========================================
# 1. CONFIGURACIÓN DE BASE DE DATOS (NEON)
# ==========================================
DB_URL = "postgresql+psycopg2://neondb_owner:npg_lJYiw7A9WKVB@ep-shy-waterfall-annvqmxl-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

@st.cache_resource
def init_db():
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        # Tabla de Sesiones (Aprendices)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS aprendices (
                nombre VARCHAR(50) PRIMARY KEY,
                falla_inyectada VARCHAR(50),
                intentos_fallidos INTEGER,
                ots_exitosas INTEGER,
                costo_acumulado REAL,
                oee REAL,
                last_seen TIMESTAMP
            )
        """))
        # Tabla de Historial (Reporte CSV)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS historial_ots (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(50),
                minuto INTEGER,
                diagnostico VARCHAR(100),
                resultado VARCHAR(20),
                timestamp TIMESTAMP
            )
        """))
        conn.commit()
    return engine

engine = init_db()

# ==========================================
# 2. MOTOR FÍSICO: LAS 15 FALLAS
# ==========================================
FALLAS_FISICA = {
    "Ninguna": {"vib": 1.0, "amp": 1.0, "p_out": 1.0, "p_in": 1.0, "t_mot": 1.0, "trip": False, "err_pt1": False, "fuga": False},
    "1. Cavitación": {"vib": 3.0, "amp": 0.8, "p_out": 0.6, "p_in": 0.2, "t_mot": 1.0, "trip": False, "err_pt1": False, "fuga": False},
    "2. Falla Rodamiento Bomba": {"vib": 4.0, "amp": 1.2, "p_out": 0.95, "p_in": 1.0, "t_mot": 1.1, "trip": False, "err_pt1": False, "fuga": False},
    "3. Rodamiento Motor": {"vib": 3.5, "amp": 1.3, "p_out": 1.0, "p_in": 1.0, "t_mot": 1.8, "trip": False, "err_pt1": False, "fuga": False},
    "4. Desalineación Eje": {"vib": 5.0, "amp": 1.4, "p_out": 0.9, "p_in": 1.0, "t_mot": 1.3, "trip": False, "err_pt1": False, "fuga": False},
    "5. Eje Partido": {"vib": 0.5, "amp": 0.5, "p_out": 0.0, "p_in": 1.0, "t_mot": 1.0, "trip": False, "err_pt1": False, "fuga": False},
    "6. Fuga Sello Mecánico": {"vib": 1.2, "amp": 0.9, "p_out": 0.5, "p_in": 1.0, "t_mot": 1.0, "trip": False, "err_pt1": False, "fuga": True},
    "7. Impulsor Desgastado": {"vib": 1.1, "amp": 0.7, "p_out": 0.4, "p_in": 1.0, "t_mot": 1.0, "trip": False, "err_pt1": False, "fuga": False},
    "8. Obstrucción Descarga": {"vib": 2.0, "amp": 1.6, "p_out": 2.5, "p_in": 1.0, "t_mot": 1.2, "trip": True, "err_pt1": False, "fuga": False},
    "9. Filtro Succión Tapado": {"vib": 2.5, "amp": 0.8, "p_out": 0.3, "p_in": 0.1, "t_mot": 1.0, "trip": False, "err_pt1": False, "fuga": False},
    "10. Falla Sensor PT-1": {"vib": 1.0, "amp": 1.0, "p_out": 1.0, "p_in": 0.0, "t_mot": 1.0, "trip": False, "err_pt1": True, "fuga": False},
    "11. Cortocircuito Motor": {"vib": 0.0, "amp": 10.0, "p_out": 0.0, "p_in": 1.0, "t_mot": 2.0, "trip": True, "err_pt1": False, "fuga": False},
    "12. Caída de Fase": {"vib": 3.0, "amp": 2.5, "p_out": 0.6, "p_in": 1.0, "t_mot": 2.5, "trip": True, "err_pt1": False, "fuga": False},
    "13. Resonancia (Base)": {"vib": 6.0, "amp": 1.1, "p_out": 1.0, "p_in": 1.0, "t_mot": 1.0, "trip": False, "err_pt1": False, "fuga": False},
    "14. Sobrecarga Térmica": {"vib": 1.0, "amp": 1.8, "p_out": 1.0, "p_in": 1.0, "t_mot": 3.0, "trip": True, "err_pt1": False, "fuga": False},
    "15. Válvula Atascada": {"vib": 1.5, "amp": 0.9, "p_out": 0.6, "p_in": 1.2, "t_mot": 1.0, "trip": False, "err_pt1": False, "fuga": False}
}

# ==========================================
# 3. MOTOR GRÁFICO SVG
# ==========================================
def render_scada_pump(v, efecto, f_activa):
    rpm = v['rpm_actual']
    
    # Colores y Animaciones
    c_on = "#2ED573"
    c_danger = "#FF4757"
    
    anim_impeller = f"spin {max(0.05, 300/max(1, rpm))}s linear infinite" if rpm > 0 else "none"
    if "Eje Partido" in f_activa: anim_impeller = "wobble 0.2s infinite"
    
    anim_vib = "shake 0.1s infinite" if efecto['vib'] > 2.0 and rpm > 0 else "none"
    c_bubbles = "rgba(255, 255, 255, 0.8)" if "Cavitación" in f_activa else "none"
    c_leak = "#8D6E63" if efecto['fuga'] else "none"
    c_bearing = c_danger if "Rodamiento" in f_activa else "#CED6E0"
    
    pt1_display = "ERR" if efecto['err_pt1'] else f"{v['presion_in']:.1f}"
    breaker_status = 'TRIPPED' if efecto['trip'] or v['amperaje'] > 60 else ('ON' if v['pwr'] else 'OFF')
    c_breaker = c_danger if breaker_status == 'TRIPPED' else (c_on if v['pwr'] else "#A4B0BE")

    svg = f"""
    <style>
        @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}
        @keyframes shake {{ 0% {{ transform: translate(3px, 3px); }} 50% {{ transform: translate(-3px, -3px); }} 100% {{ transform: translate(3px, 3px); }} }}
        @keyframes wobble {{ 0% {{ transform: rotate(0deg); }} 25% {{ transform: rotate(5deg); }} 75% {{ transform: rotate(-5deg); }} 100% {{ transform: rotate(0deg); }} }}
        @keyframes bubble {{ 0% {{ transform: translateY(0); opacity: 1; }} 100% {{ transform: translateY(-30px); opacity: 0; }} }}
        .txt-title {{ font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; fill: #FFF; }}
        .txt-val-dark {{ font-family: 'Courier New', monospace; font-size: 16px; font-weight: bold; fill: #1E272E; }}
        .cavitating-bubble {{ animation: bubble 0.4s infinite; fill: {c_bubbles}; }}
    </style>
    <svg viewBox="0 0 1000 500" width="100%" height="100%" style="background-color: #F1F2F6; border: 4px solid #2F3542; border-radius: 8px;">
        <rect x="0" y="0" width="1000" height="40" fill="#1E272E"/>
        <text x="20" y="25" class="txt-title">HMI PRINCIPAL - VISTA DE CORTE P-101</text>

        <rect x="750" y="50" width="230" height="430" fill="#DFE4EA" stroke="#2F3542" stroke-width="4" rx="10"/>
        <rect x="750" y="50" width="230" height="30" fill="#2F3542" rx="5"/>
        <text x="765" y="70" class="txt-title">TABLERO ELÉCTRICO</text>
        
        <rect x="800" y="100" width="130" height="60" fill="{c_breaker}" rx="5" stroke="#2F3542"/>
        <text x="815" y="125" class="txt-title">MAIN BREAKER</text>
        <text x="830" y="145" class="txt-title">{breaker_status}</text>

        <circle cx="865" cy="240" r="45" fill="#FFFFFF" stroke="#2F3542" stroke-width="4"/>
        <text x="840" y="215" style="font-family: Arial; font-size: 11px; fill: #2F3542;">AMPERIOS</text>
        <text x="835" y="250" class="txt-val-dark" fill="{c_danger if v['amperaje'] > 45 else '#1E272E'}">{v['amperaje']:.1f} A</text>
        
        <g style="display: {'block' if v['loto'] else 'none'};">
            <rect x="780" y="320" width="170" height="100" fill="#FF4757" stroke="#FFFFFF" stroke-width="3"/>
            <text x="825" y="350" class="txt-title">PELIGRO</text>
            <text x="790" y="375" class="txt-title">EQUIPO BLOQUEADO</text>
            <text x="825" y="400" class="txt-title">(LOTO)</text>
        </g>
        
        <path d="M 50,250 L 350,250" stroke="#3742FA" stroke-width="50" fill="none" opacity="0.6"/>
        <circle cx="250" cy="150" r="25" fill="#FFFFFF" stroke="#2F3542" stroke-width="3"/>
        <text x="235" y="140" style="font-family: Arial; font-size: 11px; font-weight: bold; fill: #2F3542;">PT-1</text>
        <text x="225" y="165" class="txt-val-dark" fill="{c_danger if efecto['err_pt1'] else '#1E272E'}">{pt1_display}</text>
        <line x1="250" y1="175" x2="250" y2="225" stroke="#2F3542" stroke-width="3"/>

        <path d="M 450,150 L 450,80 L 700,80" stroke="#3742FA" stroke-width="40" fill="none" opacity="0.6"/>
        <circle cx="500" cy="180" r="25" fill="#FFFFFF" stroke="#2F3542" stroke-width="3"/>
        <text x="485" y="170" style="font-family: Arial; font-size: 11px; font-weight: bold; fill: #2F3542;">PT-2</text>
        <text x="475" y="195" class="txt-val-dark">{v['presion_out']:.1f}</text>
        <line x1="480" y1="160" x2="450" y2="120" stroke="#2F3542" stroke-width="2"/>

        <g style="animation: {anim_vib};">
            <circle cx="450" cy="250" r="90" fill="#A4B0BE" stroke="#2F3542" stroke-width="6"/>
            
            <ellipse cx="540" cy="250" rx="10" ry="40" fill="#2F3542"/>
            <path d="M 540,280 Q 550,330 560,350 Q 530,360 520,340 Z" fill="{c_leak}"/>
            <text x="490" y="380" style="font-family: Arial; font-size: 11px; font-weight: bold; fill: {c_danger if efecto['fuga'] else 'none'};">⚠️ FUGA DE EMPAQUE</text>
            
            <rect x="550" y="230" width="40" height="40" fill="{c_bearing}" stroke="#2F3542" stroke-width="3"/>
            <rect x="590" y="240" width="50" height="20" fill="#747D8C" stroke="#2F3542" stroke-width="2"/>

            <g style="transform-box: fill-box; transform-origin: center; animation: {anim_impeller};">
                <circle cx="450" cy="250" r="15" fill="#2F3542"/>
                <path d="M 450,250 L 450,180 Q 480,200 465,250 Z" fill="#747D8C"/>
                <path d="M 450,250 L 450,320 Q 420,300 435,250 Z" fill="#747D8C"/>
                <path d="M 450,250 L 520,250 Q 500,220 450,235 Z" fill="#747D8C"/>
                <path d="M 450,250 L 380,250 Q 400,280 450,265 Z" fill="#747D8C"/>
            </g>
            
            <circle cx="410" cy="220" r="6" class="cavitating-bubble" />
            <circle cx="430" cy="280" r="9" class="cavitating-bubble" style="animation-delay: 0.1s;" />
            <circle cx="390" cy="250" r="5" class="cavitating-bubble" style="animation-delay: 0.3s;" />
        </g>

        <rect x="640" y="200" width="100" height="100" fill="#2F3542" rx="8"/>
        <text x="660" y="255" class="txt-title">M-101</text>

        <rect x="20" y="420" width="700" height="60" fill="#1E272E" rx="5"/>
        <text x="40" y="440" class="txt-title">MONITOREO DE CONDICIÓN (VIBRACIÓN Y TEMP)</text>
        <text x="40" y="465" class="txt-title" fill="#A4B0BE">Vib (VT-1):</text>
        <text x="130" y="465" style="font-family: Courier; font-size: 16px; font-weight: bold; fill: {c_danger if v['vibracion'] > 6.0 else c_on};">{v['vibracion']:.2f} mm/s</text>
        <text x="280" y="465" class="txt-title" fill="#A4B0BE">Temp Motor (TT-1):</text>
        <text x="450" y="465" style="font-family: Courier; font-size: 16px; font-weight: bold; fill: {c_danger if v['temp_motor'] > 75 else c_on};">{v['temp_motor']:.1f} °C</text>
    </svg>
    """
    return svg

# ==========================================
# 4. RUTEO Y LOGIN
# ==========================================
st.set_page_config(page_title="Red HMI & CMMS", layout="wide")

if 'role' not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    st.markdown("<h1 style='text-align: center; color: #1E272E;'>🏭 Simulador HMI Red Industrial (Neon)</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### 👨‍🏫 Ingreso Instructor")
        pwd = st.text_input("Contraseña Maestra:", type="password")
        if st.button("Entrar como Instructor", type="primary"):
            if pwd == "admin123":
                st.session_state.role = "Instructor"
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
                
    with c2:
        st.markdown("### 👷‍♂️ Ingreso Aprendiz")
        nombre = st.text_input("Nombre Completo:")
        if st.button("Iniciar Turno", type="primary") and nombre:
            st.session_state.role = "Aprendiz"
            st.session_state.nombre = nombre
            
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO aprendices (nombre, falla_inyectada, intentos_fallidos, ots_exitosas, costo_acumulado, oee, last_seen) 
                    VALUES (:n, 'Ninguna', 0, 0, 0, 100.0, :t)
                    ON CONFLICT(nombre) DO UPDATE SET last_seen = :t
                """), {"n": nombre, "t": datetime.now()})
                conn.commit()
            st.rerun()

# ==========================================
# 5. DASHBOARD DEL INSTRUCTOR
# ==========================================
elif st.session_state.role == "Instructor":
    st.title("👨‍🏫 Tablero de Control de Planta (Instructor)")
    if st.button("Cerrar Sesión"):
        st.session_state.role = None
        st.rerun()
        
    with engine.connect() as conn:
        df_alumnos = pd.read_sql("SELECT * FROM aprendices", conn)
        
    st.subheader(f"📡 Operarios en Línea: {len(df_alumnos)}")
    st.dataframe(df_alumnos.style.highlight_max(subset=['intentos_fallidos', 'costo_acumulado'], color='lightcoral'), use_container_width=True)

    st.markdown("### ⚡ Inyector Remoto de Fallas")
    col1, col2, col3 = st.columns(3)
    alumno_sel = col1.selectbox("Seleccionar Aprendiz:", df_alumnos['nombre'].tolist() if not df_alumnos.empty else ["N/A"])
    falla_sel = col2.selectbox("Seleccionar Falla:", list(FALLAS_FISICA.keys()))
    
    if col3.button("🔥 EJECUTAR FALLA", type="primary") and alumno_sel != "N/A":
        with engine.connect() as conn:
            conn.execute(text("UPDATE aprendices SET falla_inyectada = :f WHERE nombre = :n"), {"f": falla_sel, "n": alumno_sel})
            conn.commit()
        st.success(f"Falla inyectada a la estación de {alumno_sel}.")
        st.rerun()

    st.divider()
    st.markdown("### 📥 Descarga Analítica")
    with engine.connect() as conn:
        df_historial = pd.read_sql("SELECT * FROM historial_ots", conn)
    st.download_button("Descargar Reporte CMMS (CSV para Power BI)", data=df_historial.to_csv(index=False), file_name="Data_Mantenimiento_Clase.csv", mime="text/csv")

# ==========================================
# 6. ESTACIÓN DEL APRENDIZ (SCADA Y OT)
# ==========================================
elif st.session_state.role == "Aprendiz":
    nombre = st.session_state.nombre
    if 'rpm_sp' not in st.session_state: st.session_state.rpm_sp = 1800
    if 'minutos' not in st.session_state: st.session_state.minutos = 0
    if 'pwr' not in st.session_state: st.session_state.pwr = True
    
    # 6.1 Leer BD (Ping al servidor)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT falla_inyectada, intentos_fallidos, costo_acumulado FROM aprendices WHERE nombre = :n"), {"n": nombre}).fetchone()
        falla_actual = res[0]
        intentos = res[1]
        costos = res[2]

    # Sidebar: Panel Operativo
    st.sidebar.markdown(f"### 👷‍♂️ Estación: {nombre}")
    st.sidebar.error(f"Errores: **{intentos}** | Costo: **${costos:,.0f} USD**")
    
    st.sidebar.markdown("### 🎛️ CONTROLES HMI")
    st.session_state.pwr = st.sidebar.toggle("Main Breaker", value=st.session_state.pwr)
    rpm_in = st.sidebar.slider("RPM Setpoint", 0, 3600, st.session_state.rpm_sp, 100)
    loto = st.sidebar.checkbox("🔒 Aplicar LOTO (Corte Energía)")
    
    if st.sidebar.button("⏱️ AVANZAR 10 MINUTOS", use_container_width=True, type="primary"):
        st.session_state.rpm_sp = rpm_in
        st.session_state.minutos += 10
        with engine.connect() as conn:
            conn.execute(text("UPDATE aprendices SET last_seen = :t WHERE nombre = :n"), {"t": datetime.now(), "n": nombre})
            conn.commit()

    # 6.2 Procesamiento Físico
    efecto = FALLAS_FISICA[falla_actual]
    trip_activo = efecto["trip"] or (st.session_state.rpm_sp > 3000 and efecto["amp"] > 1.0)
    
    v = {
        'pwr': st.session_state.pwr,
        'loto': loto,
        'rpm_actual': st.session_state.rpm_sp if (st.session_state.pwr and not loto and not trip_activo) else 0
    }
    
    rpm = v['rpm_actual']
    v['presion_in'] = (14.7 * efecto["p_in"]) if rpm > 0 else (14.7 if efecto["p_in"]>0 else 0)
    v['presion_out'] = ((rpm * 0.04) * efecto["p_out"]) if rpm > 0 else 0
    v['amperaje'] = (((rpm / 100.0) + (v['presion_out']*0.2)) * efecto["amp"]) if rpm > 0 else 0
    
    if trip_activo and st.session_state.pwr and not loto: 
        v['amperaje'] = random.uniform(80, 150) # Cortocircuito / Sobrecorriente visual
        
    v['vibracion'] = (1.2 + (rpm / 3600.0)) * efecto["vib"] if rpm > 0 else 0
    v['temp_motor'] = 40.0 + ((rpm / 200.0) * efecto["t_mot"])

    # Castigo financiero en tiempo real si hay falla y no se repara
    if falla_actual != "Ninguna" and st.session_state.minutos > 0:
        costos += 1500 # $1500 por cada avance de tiempo averiado
        with engine.connect() as conn:
            conn.execute(text("UPDATE aprendices SET costo_acumulado = :c WHERE nombre = :n"), {"c": costos, "n": nombre})
            conn.commit()

    # Render SCADA
    st.markdown(f"**Tiempo de Operación de la Planta:** Minuto {st.session_state.minutos}")
    components.html(render_scada_pump(v, efecto, falla_actual), height=520)

    # 6.3 Sistema OT Interactiva
    st.divider()
    st.markdown("### 📋 CMMS: ORDEN DE TRABAJO (OT)")
    
    if falla_actual == "Ninguna":
        st.success("🟢 Sistema operando con normalidad. Avanza el tiempo para monitorear.")
    else:
        st.warning("⚠️ Anomalía Detectada. Diagnostica y ejecuta la reparación para detener las pérdidas.")
        with st.form("ot_form"):
            col1, col2 = st.columns(2)
            diag = col1.selectbox("Diagnóstico Raíz (Selecciona la falla exacta):", ["Seleccionar..."] + list(FALLAS_FISICA.keys())[1:])
            accion = col2.selectbox("Acción Correctiva:", ["Seleccionar...", "Cambio de Rodamiento", "Alineación Láser", "Rebobinado Motor", "Limpieza de Filtro/Succión", "Cambio de Sellos", "Reemplazo de Instrumentación"])
            
            if st.form_submit_button("🛠️ APROBAR Y EJECUTAR OT", type="primary"):
                if not loto:
                    st.error("❌ ¡VIOLACIÓN HSE! No aislaste las energías. Accidente reportado.")
                    with engine.connect() as conn:
                        conn.execute(text("UPDATE aprendices SET costo_acumulado = costo_acumulado + 5000, intentos_fallidos = intentos_fallidos + 1 WHERE nombre = :n"), {"n": nombre})
                        conn.commit()
                elif diag == "Seleccionar..." or accion == "Seleccionar...":
                    st.error("Diligencia la OT completa.")
                elif diag == falla_actual:
                    st.success("✅ Diagnóstico Preciso. Reparación Exitosa.")
                    with engine.connect() as conn:
                        conn.execute(text("INSERT INTO historial_ots (nombre, minuto, diagnostico, resultado, timestamp) VALUES (:n, :m, :d, 'EXITO', :t)"), {"n": nombre, "m": st.session_state.minutos, "d": diag, "t": datetime.now()})
                        conn.execute(text("UPDATE aprendices SET falla_inyectada = 'Ninguna', ots_exitosas = ots_exitosas + 1 WHERE nombre = :n"), {"n": nombre})
                        conn.commit()
                    st.rerun()
                else:
                    st.error("❌ Diagnóstico Erróneo. Los síntomas no coinciden. El equipo sigue averiado.")
                    with engine.connect() as conn:
                        conn.execute(text("INSERT INTO historial_ots (nombre, minuto, diagnostico, resultado, timestamp) VALUES (:n, :m, :d, 'FALLA', :t)"), {"n": nombre, "m": st.session_state.minutos, "d": diag, "t": datetime.now()})
                        conn.execute(text("UPDATE aprendices SET intentos_fallidos = intentos_fallidos + 1, costo_acumulado = costo_acumulado + 1000 WHERE nombre = :n"), {"n": nombre})
                        conn.commit()
                    st.rerun()