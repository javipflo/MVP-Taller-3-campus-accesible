import streamlit as st
import pandas as pd
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from datetime import datetime
from gtts import gTTS
import io
import os
import json

# ===================================================
# Conf general
# ===================================================
st.set_page_config(
    page_title="Campus Accesible UTEM",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.block-container { padding-top: 1.5rem; padding-bottom: 0rem; }
.stAlert { border-radius: 12px; }
div.stButton > button { border-radius: 8px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

RUTAS_FILE = "rutas_guardadas.json"


# ===================================================
# Funciones auxiliares
# ===================================================
def cargar_csv_seguro(nombre_archivo, columnas_minimas):
    """Carga un CSV y crea columnas faltantes para evitar errores."""
    try:
        df = pd.read_csv(nombre_archivo)
    except FileNotFoundError:
        df = pd.DataFrame(columns=columnas_minimas)
        df.to_csv(nombre_archivo, index=False)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=columnas_minimas)

    for col in columnas_minimas:
        if col not in df.columns:
            df[col] = ""

    return df


def cargar_rutas_guardadas():
    if os.path.exists(RUTAS_FILE):
        try:
            with open(RUTAS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def guardar_rutas_guardadas(rutas):
    with open(RUTAS_FILE, "w", encoding="utf-8") as f:
        json.dump(rutas, f, ensure_ascii=False, indent=4)


def clave_ruta(origen, destino):
    return f"{origen}__{destino}"


def obtener_ruta(origen, destino):
    """Primero busca rutas dibujadas; si no existen, usa rutas base."""
    clave_directa = clave_ruta(origen, destino)
    clave_inversa = clave_ruta(destino, origen)

    if clave_directa in st.session_state.rutas_guardadas:
        return st.session_state.rutas_guardadas[clave_directa], "guardada"

    if clave_inversa in st.session_state.rutas_guardadas:
        return st.session_state.rutas_guardadas[clave_inversa][::-1], "guardada"

    if (origen, destino) in diccionario_rutas:
        return diccionario_rutas[(origen, destino)], "predefinida"

    if (destino, origen) in diccionario_rutas:
        return diccionario_rutas[(destino, origen)][::-1], "predefinida"

    return None, "sin_ruta"


# ===================================================
# carga de datos
# ===================================================
if "df_edificios" not in st.session_state:
    st.session_state.df_edificios = cargar_csv_seguro(
        "edificios.csv",
        ["nombre", "descripcion", "lat", "lon", "tiene_ascensor"]
    )

if "df_puntos" not in st.session_state:
    st.session_state.df_puntos = cargar_csv_seguro(
        "puntos_accesibles.csv",
        ["nombre", "tipo", "edificio", "descripcion", "lat", "lon", "estado"]
    )

if "df_destinos" not in st.session_state:
    st.session_state.df_destinos = cargar_csv_seguro(
        "destinos.csv",
        ["destino"]
    )

if "alertas_bloqueos" not in st.session_state:
    st.session_state.alertas_bloqueos = []

if "rutas_guardadas" not in st.session_state:
    st.session_state.rutas_guardadas = cargar_rutas_guardadas()

df_edificios = st.session_state.df_edificios
df_puntos = st.session_state.df_puntos

# Asegurar tipos numéricos para mapas
for df in [df_edificios, df_puntos]:
    if "lat" in df.columns:
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    if "lon" in df.columns:
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")


# ===================================================
# íconos y rutas base
# ===================================================
iconos_edificios = {
    "M1": "graduation-cap",
    "M2": "utensils",
    "M3": "graduation-cap",
    "M5": "flask",
    "M6": "bolt",
    "M7": "industry",
    "M8": "microscope",
    "Biblioteca": "book",
    "Gimnasio": "dumbbell",
    "Cancha Multideportiva": "basketball-ball",
    "Entrada Alessandri": "door-open",
    "SESAES": "notes-medical"
}

diccionario_rutas = {
    ("M1", "M2"): [[-33.466173, -70.598008], [-33.466180, -70.597722]],
    ("M1", "M3"): [[-33.466173, -70.598008], [-33.466180, -70.597722], [-33.466180, -70.597424]],
    ("M1", "M6"): [[-33.466173, -70.598008], [-33.466173, -70.596607], [-33.466123, -70.596607]],
    ("M1", "M7"): [[-33.466173, -70.598008], [-33.466173, -70.597215], [-33.465948, -70.597215]],
    ("M1", "M8"): [[-33.466173, -70.598008], [-33.466173, -70.596889], [-33.466450, -70.596889]],
    ("M1", "Biblioteca"): [[-33.466173, -70.598008], [-33.466173, -70.597850], [-33.465833, -70.597850]],
    ("M1", "Gimnasio"): [[-33.466173, -70.598008], [-33.466173, -70.597900], [-33.466620, -70.597900]],
    ("M1", "SESAES"): [[-33.466173, -70.598008], [-33.466350, -70.598000], [-33.466350, -70.597950]],
    ("M1", "Cancha Multideportiva"): [[-33.466173, -70.598008], [-33.466173, -70.597000], [-33.465714, -70.597000], [-33.465714, -70.596769]],
    ("M2", "M3"): [[-33.466180, -70.597722], [-33.466180, -70.597424]],
    ("M3", "M6"): [[-33.466180, -70.597424], [-33.466180, -70.596607], [-33.466123, -70.596607]],
    ("M3", "M7"): [[-33.466180, -70.597424], [-33.465948, -70.597424], [-33.465948, -70.597215]],
}


# ===================================================
# Salas y espacios por edificio
# ===================================================
salas_por_edificio = {
    "M1": {
        1: [
            "Entrada Alessandri",
            "Servicios de Bienestar Estudiantil oficina 1",
            "Servicios de Bienestar Estudiantil oficina 2",
            "Secretaría de Estudios",
            "Dirección de Desarrollo Estudiantil",
            "Laboratorio de Plan Común Facultad de Ingeniería",
            "Facultad de Ciencias Naturales, Matemática y Medio Ambiente",
            "Departamento de Física"
        ],
        2: [
            "Laboratorio A", "Laboratorio B", "Laboratorio C", "Laboratorio D", "Laboratorio E",
            "Oficina Dirección Departamento de Física", "Pañol", "Baño de mujeres", "Baño de hombres"
        ],
        3: [
            "M1-301", "M1-302", "M1-303", "M1-304", "M1-305", "M1-306", "M1-307",
            "Laboratorio de Suelos y Medio Ambiente", "Baño de mujeres", "Baño de hombres"
        ],
        4: [
            "Laboratorio n°1 de Informática", "Laboratorio n°2 de Informática",
            "Laboratorio n°3 de Informática", "Laboratorio n°4 de Informática",
            "Oficina Encargado de Laboratorios", "Baños de hombres y mujeres"
        ]
    },
    "M2": {
        1: ["Casino"],
        2: ["M2-201", "M2-202", "M2-203", "M2-204", "Baño de hombres", "Baño mixto"],
        3: ["M2-301", "M2-302", "M2-303", "M2-304", "Baño de hombres", "Baño de mujeres"]
    },
    "M3": {
        1: ["M3-101", "M3-102", "M3-103", "M3-104", "Sala de carrera de Geomensura", "Baño de mujeres accesible", "Baño de hombres accesible"],
        2: ["M3-201", "M3-202", "M3-203", "M3-204", "Baño de hombres", "Baño mixto"],
        3: ["M3-301", "M3-303", "M3-304", "Sala de carrera de Ciencias de Datos", "Baño de mujeres", "Baño de hombres"],
        4: ["Laboratorios"]
    },
    "M5": {
        1: ["Lobby", "Laboratorio de Biología, Microbiología y Biotecnología", "Baños auxiliares", "Baños hombres/mujeres", "Facultad de Ciencias Naturales, Matemática y Medio Ambiente"],
        2: ["M5-206", "M5-207", "M5-208", "M5-209", "M5-210", "M5-211", "M5-212", "M5-213", "Escuela de Geomensura", "M5-215", "M5-216", "Baño varones/mujeres"],
        3: ["Facultad Escuela de Matemáticas", "Baño hombre/mujer funcionarios", "Departamento de Química y Biotecnología", "Secretaría Departamento de Biotecnología", "Sala de reuniones", "Departamento de Matemáticas"],
        4: ["Lab de docencia n°3 Química Analítica", "Lab de Nanotecnología y Materiales Avanzados", "Lab Química Organometálica", "Lab de docencia n°4 Química Orgánica", "Sala destilación", "Lab de docencia n°2 Química Inorgánica", "Bodega de solventes químicos inflamables y residuos químicos", "Bodega de residuos químicos", "Lab de investigación materiales inorgánicos", "LabinBio"]
    },
    "M6": {
        1: ["M6-114", "M6-111", "Ascensor próximamente", "M6-122", "M6-110", "M6-108", "M6-103", "M6-107", "Baño mixto", "M6-101", "M6-106"],
        2: ["Baño mujeres", "M6-209", "M6-203", "M6-204", "M6-208", "M6-206", "M6-210", "M6-207", "M6-205", "M6-212", "M6-214", "Baño hombres"],
        3: ["Baño mujeres", "M6-325", "M6-326", "M6-304", "M6-327", "Departamento de Mecánica", "M6-330", "M6-331", "M6-322", "Baño hombres"],
        4: ["M6-400"]
    },
    "M7": {
        1: ["Escuela Electrónica", "Escuela Industria", "Escuela Informática", "Escuela Mecánica y Dibujante Proyectista", "Escuela Geomensura", "Escuela Bachillerato y Plan Común Ingeniería"],
        2: ["Departamento de Electricidad", "Consejo Facultad de Ingeniería"],
        3: ["Departamento Informática", "Laboratorio Informática N°7", "Dirección Departamento de Industria"]
    },
    "M8": {
        1: [
            "Sala carrera de Mecánica", "Sala Escuela de Química", "Sala de Química 1", "Sala de Química 2",
            "Sala Multimedia de Química", "Laboratorio de Ingeniería de Bioprocesos",
            "Laboratorio de Biotransformaciones Departamento de Biotecnología", "Laboratorio",
            "Club de Desarrollo Experimental EXDEV", "Sala carrera Ingeniería en Informática",
            "Club de Tecnología y Telecomunicación CTT", "Sala carrera Civil en Computación"
        ]
    },
    "Biblioteca": {
        -1: ["Espacio lúdico", "Oficinas de secretaría", "Salas de estudio"],
        1: ["Salas de estudio"],
        2: ["Salas de estudio", "PC disponibles para préstamo"],
        3: ["Salas de estudio", "Salas de estudio postgrado", "Documentos de postgrado"],
        4: ["Acceso solo funcionarios"]
    },
    "Gimnasio": {
        1: ["Gimnasio subterráneo. Se accede bajando por escaleras."]
    },
    "SESAES": {
        1: ["Enfermería"]
    }
}


def pisos_disponibles_para(destino):
    if destino in salas_por_edificio:
        return sorted(salas_por_edificio[destino].keys())
    return [1]


# ===================================================
# sidebear
# ===================================================
st.sidebar.image("https://utem.cl/wp-content/uploads/2017/06/logo-utem.png", width=150)
st.sidebar.title("♿ Menú Principal")
modo = st.sidebar.radio(
    "Navegar a:",
    ["🗺️ Mapa Principal", "⚠️ Reportar Obstáculo", "⚙️ Panel Administrador"]
)

# ===================================================
# MÓDULO 1: mapa principal
# ===================================================
if modo == "🗺️ Mapa Principal":
    st.title("📍 Campus Accesible Ñuñoa")

    st.sidebar.markdown("---")
    st.sidebar.subheader("⭐ Rutas Guardadas")
    destinos_frecuentes = st.session_state.df_destinos["destino"].dropna().tolist()
    usar_frecuente = st.sidebar.checkbox("Cargar rutas frecuentes")

    st.sidebar.markdown("---")
    st.sidebar.subheader("👁️ Filtros de Infraestructura")
    mostrar_banos = st.sidebar.checkbox("🚻 Baños")
    mostrar_zonas = st.sidebar.checkbox("🌳 Zonas Tranquilas")
    mostrar_rampas = st.sidebar.checkbox("♿ Rampas de Acceso")
    mostrar_ascensores = st.sidebar.checkbox("🛗 Ascensores")

    nodos = df_edificios["nombre"].dropna().tolist()

    if not nodos:
        st.error("No hay edificios registrados en edificios.csv.")
        st.stop()

    col_geo, col_salas, col_fav = st.columns([2, 2, 1])

    with col_geo:
        if usar_frecuente and destinos_frecuentes:
            destino = st.selectbox("🎯 Destino Seleccionado:", destinos_frecuentes)
            origen = st.selectbox("📍 Origen:", [n for n in nodos if n != destino])
        else:
            origen = st.selectbox("📍 Origen:", nodos, index=nodos.index("M1") if "M1" in nodos else 0)
            destino = st.selectbox("🎯 Destino:", [n for n in nodos if n != origen])

    with col_salas:
        pisos_destino = pisos_disponibles_para(destino)

        piso = st.radio(
            "🏢 Nivel/Piso:",
            pisos_destino,
            horizontal=True,
            format_func=lambda x: "Piso -1" if x == -1 else f"Piso {x}"
        )

        salas_disponibles = salas_por_edificio.get(destino, {}).get(piso, [])

        if salas_disponibles:
            sala_seleccionada = st.selectbox(
                "🚪 Espacios disponibles en este nivel:",
                salas_disponibles
            )
        else:
            sala_seleccionada = None
            st.caption(f"No se registran espacios en el piso {piso}.")

        if sala_seleccionada:
            st.caption(f"Espacio seleccionado: {sala_seleccionada}")

    with col_fav:
        st.write("")
        st.write("")
        if st.button("⭐ Guardar Destino", use_container_width=True):
            if destino not in destinos_frecuentes:
                nueva_fila = pd.DataFrame({"destino": [destino]})
                st.session_state.df_destinos = pd.concat(
                    [st.session_state.df_destinos, nueva_fila],
                    ignore_index=True
                )
                st.session_state.df_destinos.to_csv("destinos.csv", index=False)
                st.toast(f"¡{destino} añadido a favoritos!", icon="⭐")

    datos_dest = df_edificios[df_edificios["nombre"] == destino].iloc[0]
    tiene_ascensor = str(datos_dest.get("tiene_ascensor", "No"))
    es_accesible = not (piso > 1 and tiene_ascensor == "No")
    color_ruta = "green" if es_accesible else "red"

    col_alert, col_audio = st.columns([4, 1])

    with col_alert:
        if es_accesible:
            st.success(f"♿ **Infraestructura Accesible:** Desplazamiento hacia {destino}, piso {piso}.")
            msg_voz = f"Ruta accesible hacia {destino}, piso {piso}."
        else:
            st.error(f"⚠️ **Barrera Arquitectónica:** El bloque {destino} no cuenta con ascensor. Requiere uso de escaleras.")
            msg_voz = f"Advertencia. El edificio {destino} no posee ascensor. El trayecto requiere escaleras."

    with col_audio:
        if st.button("🔊 Guía de Voz", use_container_width=True):
            tts = gTTS(text=msg_voz, lang="es")
            audio_file = io.BytesIO()
            tts.write_to_fp(audio_file)
            audio_file.seek(0)
            st.audio(audio_file, format="audio/mp3", autoplay=True)

    if st.session_state.alertas_bloqueos:
        for a in st.session_state.alertas_bloqueos:
            st.warning(f"🚧 **Alerta Vial:** {a['edificio']} - {a['descripcion']}")

    mapa_objeto = folium.Map(location=[-33.466142, -70.597048], zoom_start=18)

    # Edificios
    for _, row in df_edificios.dropna(subset=["lat", "lon"]).iterrows():
        n_edif = row["nombre"]
        marcador_color = "red" if n_edif == destino else "green" if n_edif == origen else "blue"

        folium.Marker(
            [row["lat"], row["lon"]],
            popup=f"<b>{n_edif}</b><br>{row.get('descripcion', '')}<br>Ascensor: {row.get('tiene_ascensor', 'No informado')}",
            tooltip=n_edif,
            icon=folium.Icon(
                color=marcador_color,
                icon=iconos_edificios.get(n_edif, "info-sign"),
                prefix="fa"
            )
        ).add_to(mapa_objeto)

    # Filtros de puntos accesibles
    if mostrar_banos:
        tipos_bano = ["Baño", "Baño accesible", "Baño hombres", "Baño mujeres", "Baño mixto"]
        for _, b in df_puntos[df_puntos["tipo"].isin(tipos_bano)].dropna(subset=["lat", "lon"]).iterrows():
            folium.Marker(
                [b["lat"], b["lon"]],
                popup=b.get("descripcion", ""),
                tooltip=b.get("nombre", "Baño"),
                icon=folium.Icon(color="lightblue", icon="restroom", prefix="fa")
            ).add_to(mapa_objeto)

    if mostrar_zonas:
        for _, z in df_puntos[df_puntos["tipo"].isin(["Zona Tranquila", "Zona común"])].dropna(subset=["lat", "lon"]).iterrows():
            folium.Marker(
                [z["lat"], z["lon"]],
                popup=z.get("descripcion", ""),
                tooltip=z.get("nombre", "Zona"),
                icon=folium.Icon(color="purple", icon="tree", prefix="fa")
            ).add_to(mapa_objeto)

    if mostrar_rampas:
        for _, r in df_puntos[df_puntos["tipo"] == "Rampa"].dropna(subset=["lat", "lon"]).iterrows():
            folium.Marker(
                [r["lat"], r["lon"]],
                popup=r.get("descripcion", ""),
                tooltip=r.get("nombre", "Rampa"),
                icon=folium.Icon(color="orange", icon="wheelchair", prefix="fa")
            ).add_to(mapa_objeto)

    if mostrar_ascensores:
        for _, a in df_puntos[df_puntos["tipo"] == "Ascensor"].dropna(subset=["lat", "lon"]).iterrows():
            folium.Marker(
                [a["lat"], a["lon"]],
                popup=a.get("descripcion", ""),
                tooltip=a.get("nombre", "Ascensor"),
                icon=folium.Icon(color="darkpurple", icon="sort", prefix="fa")
            ).add_to(mapa_objeto)

    trayecto_coords, tipo_ruta = obtener_ruta(origen, destino)

    if trayecto_coords:
        folium.PolyLine(
            trayecto_coords,
            color=color_ruta,
            weight=7,
            opacity=0.85,
            tooltip=f"Ruta {tipo_ruta}: {origen} → {destino}"
        ).add_to(mapa_objeto)
    else:
        c_o = [
            df_edificios[df_edificios["nombre"] == origen].iloc[0]["lat"],
            df_edificios[df_edificios["nombre"] == origen].iloc[0]["lon"]
        ]
        c_d = [
            df_edificios[df_edificios["nombre"] == destino].iloc[0]["lat"],
            df_edificios[df_edificios["nombre"] == destino].iloc[0]["lon"]
        ]
        folium.PolyLine(
            [c_o, c_d],
            color="gray",
            dash_array="10",
            weight=4
        ).add_to(mapa_objeto)

    st_folium(mapa_objeto, height=580, use_container_width=True, returned_objects=[])


# ===================================================
# MÓDULO 2: formulario de alertas
# ===================================================
elif modo == "⚠️ Reportar Obstáculo":
    st.title("Reporte de Incidencias en Ruta")
    st.write("Genera advertencias inmediatas visibles para toda la comunidad universitaria.")

    with st.form("obstaculo_form"):
        edif_afectado = st.selectbox("Estructura afectada:", df_edificios["nombre"])
        desc_bloqueo = st.text_area("Detalle de la barrera física detectada:")

        if st.form_submit_button("Publicar Alerta"):
            st.session_state.alertas_bloqueos.append({
                "edificio": edif_afectado,
                "descripcion": desc_bloqueo,
                "fecha": datetime.now()
            })
            st.success("¡Reporte guardado! El aviso se reflejará sobre el mapa interactivo de inmediato.")


# ===================================================
# MÓDULO 3: administrador
# ===================================================
elif modo == "⚙️ Panel Administrador":
    st.title("Administración del Sistema")

    tab_admin1, tab_admin2, tab_admin3 = st.tabs([
        "Infraestructura",
        "Editor de rutas",
        "Puntos accesibles"
    ])

    # -------------------------------
    # TAB 1: infraestructura
    # -------------------------------
    with tab_admin1:
        edif_mod = st.selectbox("Seleccione el bloque a gestionar:", df_edificios["nombre"])

        estado_actual = df_edificios.loc[
            df_edificios["nombre"] == edif_mod,
            "tiene_ascensor"
        ].values[0]

        st.info(f"Estado de ascensor actual en {edif_mod}: `{estado_actual}`")

        nuevo_estado = st.radio(
            "Modificar disponibilidad:",
            ["Sí", "No"],
            index=0 if estado_actual == "Sí" else 1,
            horizontal=True
        )

        if st.button("Guardar configuración"):
            st.session_state.df_edificios.loc[
                st.session_state.df_edificios["nombre"] == edif_mod,
                "tiene_ascensor"
            ] = nuevo_estado

            st.session_state.df_edificios.to_csv("edificios.csv", index=False)
            st.success("Cambios guardados correctamente.")

    # -------------------------------
    # TAB 2: El editor de rutas
    # -------------------------------
    with tab_admin2:
        st.subheader("Editor visual de rutas")

        st.info("""
        Dibuja la ruta directamente sobre el mapa usando la herramienta de línea.
        Luego selecciona origen y destino, y guarda la ruta.
        """)

        col_r1, col_r2 = st.columns(2)

        with col_r1:
            origen_ruta = st.selectbox(
                "Origen de la ruta:",
                df_edificios["nombre"],
                key="origen_editor"
            )

        with col_r2:
            destino_ruta = st.selectbox(
                "Destino de la ruta:",
                [n for n in df_edificios["nombre"] if n != origen_ruta],
                key="destino_editor"
            )

        mapa_editor = folium.Map(location=[-33.466142, -70.597048], zoom_start=18)

        for _, row in df_edificios.dropna(subset=["lat", "lon"]).iterrows():
            folium.Marker(
                [row["lat"], row["lon"]],
                tooltip=row["nombre"],
                popup=row.get("descripcion", ""),
                icon=folium.Icon(
                    color="blue",
                    icon=iconos_edificios.get(row["nombre"], "info-sign"),
                    prefix="fa"
                )
            ).add_to(mapa_editor)

        Draw(
            export=False,
            draw_options={
                "polyline": True,
                "polygon": False,
                "rectangle": False,
                "circle": False,
                "marker": False,
                "circlemarker": False
            },
            edit_options={"edit": True, "remove": True}
        ).add_to(mapa_editor)

        dibujo = st_folium(
            mapa_editor,
            height=560,
            use_container_width=True,
            returned_objects=["all_drawings"],
            key="mapa_editor_rutas"
        )

        coords_extraidas = []

        if dibujo and dibujo.get("all_drawings"):
            ultimo_dibujo = dibujo["all_drawings"][-1]

            if ultimo_dibujo.get("geometry", {}).get("type") == "LineString":
                coords_lonlat = ultimo_dibujo["geometry"]["coordinates"]
                coords_extraidas = [[lat, lon] for lon, lat in coords_lonlat]

                st.success(f"Ruta detectada con {len(coords_extraidas)} puntos.")
                st.code(coords_extraidas)

        if st.button("Guardar ruta dibujada"):
            if not coords_extraidas:
                st.error("Primero debes dibujar una línea en el mapa.")
            else:
                clave = clave_ruta(origen_ruta, destino_ruta)
                st.session_state.rutas_guardadas[clave] = coords_extraidas
                guardar_rutas_guardadas(st.session_state.rutas_guardadas)
                st.success(f"Ruta guardada: {origen_ruta} → {destino_ruta}")

        st.markdown("### Rutas guardadas actualmente")

        if st.session_state.rutas_guardadas:
            rutas_tabla = pd.DataFrame([
                {"Ruta": k.replace("__", " → "), "Puntos": len(v)}
                for k, v in st.session_state.rutas_guardadas.items()
            ])
            st.dataframe(rutas_tabla, use_container_width=True)
        else:
            st.caption("Aún no hay rutas dibujadas guardadas.")

    # -------------------------------
    # TAB 3: puntos accesibles
    # -------------------------------
    with tab_admin3:
        st.subheader("Agregar puntos libres de accesibilidad al mapa")

        st.info("""
        Haz clic en cualquier lugar del mapa para registrar puntos libres, como rampas,
        baños accesibles, ascensores, entradas, pasamanos o barreras. Estos puntos no
        necesitan estar asociados a una sala específica.
        """)

        tipo_punto = st.selectbox(
            "Tipo de punto:",
            [
                "Baño accesible",
                "Baño hombres",
                "Baño mujeres",
                "Baño mixto",
                "Rampa",
                "Ascensor",
                "Entrada accesible",
                "Pasamanos",
                "Escalera",
                "Barrera",
                "Zona común",
                "Otro servicio"
            ]
        )

        nombre_punto = st.text_input(
            "Nombre del punto:",
            placeholder="Ej: Rampa entre M3 y patio central"
        )

        opciones_sector = ["Campus / Punto libre"] + df_edificios["nombre"].tolist()

        edificio_punto = st.selectbox(
            "Edificio o sector asociado:",
            opciones_sector,
            key="edificio_punto"
        )

        descripcion_punto = st.text_area(
            "Descripción:",
            placeholder="Ej: Rampa ubicada en el pasillo hacia la zona común."
        )

        estado_punto = st.selectbox(
            "Estado:",
            [
                "Disponible",
                "Operativo",
                "Fuera de servicio",
                "Acceso limitado",
                "No accesible",
                "Pendiente de validar"
            ]
        )

        mapa_puntos = folium.Map(location=[-33.466142, -70.597048], zoom_start=18)

        # Edificios como referencia
        for _, row in df_edificios.dropna(subset=["lat", "lon"]).iterrows():
            folium.Marker(
                [row["lat"], row["lon"]],
                tooltip=row["nombre"],
                popup=row.get("descripcion", ""),
                icon=folium.Icon(color="blue", icon="building", prefix="fa")
            ).add_to(mapa_puntos)

        # Puntos ya guardados
        if not st.session_state.df_puntos.empty:
            for _, p in st.session_state.df_puntos.dropna(subset=["lat", "lon"]).iterrows():
                folium.Marker(
                    [p["lat"], p["lon"]],
                    tooltip=p.get("nombre", ""),
                    popup=f"{p.get('tipo', '')} - {p.get('descripcion', '')}",
                    icon=folium.Icon(color="green", icon="info-sign")
                ).add_to(mapa_puntos)

        click_mapa = st_folium(
            mapa_puntos,
            height=560,
            use_container_width=True,
            returned_objects=["last_clicked"],
            key="mapa_agregar_puntos"
        )

        lat_click = None
        lon_click = None

        if click_mapa and click_mapa.get("last_clicked"):
            lat_click = click_mapa["last_clicked"]["lat"]
            lon_click = click_mapa["last_clicked"]["lng"]

            st.success("Ubicación seleccionada en el mapa.")
            st.write(f"Latitud: `{lat_click}`")
            st.write(f"Longitud: `{lon_click}`")

        if st.button("Guardar punto accesible"):
            if not nombre_punto.strip():
                st.error("Debes escribir un nombre para el punto.")
            elif lat_click is None or lon_click is None:
                st.error("Debes hacer clic en el mapa para seleccionar la ubicación.")
            else:
                nuevo_punto = pd.DataFrame([{
                    "nombre": nombre_punto,
                    "tipo": tipo_punto,
                    "edificio": edificio_punto,
                    "descripcion": descripcion_punto,
                    "lat": lat_click,
                    "lon": lon_click,
                    "estado": estado_punto
                }])

                st.session_state.df_puntos = pd.concat(
                    [st.session_state.df_puntos, nuevo_punto],
                    ignore_index=True
                )

                st.session_state.df_puntos.to_csv("puntos_accesibles.csv", index=False)

                st.success(f"Punto guardado correctamente: {nombre_punto}")
                st.rerun()

        st.markdown("### Puntos accesibles registrados")

        if st.session_state.df_puntos.empty:
            st.caption("Aún no hay puntos registrados.")
        else:
            st.dataframe(st.session_state.df_puntos, use_container_width=True)

            st.markdown("### Eliminar punto accesible")

            punto_a_eliminar = st.selectbox(
                "Selecciona el punto que quieres eliminar:",
                st.session_state.df_puntos["nombre"].tolist(),
                key="punto_a_eliminar"
            )

            if st.button("Eliminar punto accesible"):
                st.session_state.df_puntos = st.session_state.df_puntos[
                    st.session_state.df_puntos["nombre"] != punto_a_eliminar
                ]

                st.session_state.df_puntos.to_csv("puntos_accesibles.csv", index=False)

                st.success(f"Punto eliminado correctamente: {punto_a_eliminar}")
                st.rerun()
