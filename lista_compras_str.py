import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ==========================
# CONFIGURACIÓN
# ==========================
DB_NAME = "shopping_list.db"

st.set_page_config(page_title="🛒 Lista de Compras", layout="wide")

# ==========================
# BASE DE DATOS - Inicialización
# ==========================
def init_db():
    """Inicializa todas las tablas necesarias."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shopping_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            offer TEXT
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shopping_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            store TEXT NOT NULL,
            total REAL NOT NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            offer TEXT,
            FOREIGN KEY (purchase_id) REFERENCES shopping_history(id)
        )
        ''')
        conn.commit()

# ==========================
# FUNCIONES DE BASE DE DATOS
# ==========================
@st.cache_data(ttl=60)
def obtener_lista():
    """Obtiene la lista actual de compras."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql_query("SELECT id, name, quantity, price, offer FROM shopping_list", conn)
        return df
    except Exception as e:
        st.error(f"Error al cargar la lista: {e}")
        return pd.DataFrame(columns=["id", "name", "quantity", "price", "offer"])

@st.cache_data(ttl=60)
def obtener_historial():
    """Obtiene el historial de compras."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql_query("""
                SELECT id, date, store, total 
                FROM shopping_history 
                ORDER BY date DESC, id DESC
            """, conn)
        return df
    except Exception as e:
        st.error(f"Error al cargar el historial: {e}")
        return pd.DataFrame(columns=["id", "date", "store", "total"])

def obtener_detalle_compra(purchase_id):
    """Obtiene el detalle de una compra específica."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql_query("""
                SELECT name, quantity, price, offer 
                FROM purchase_details 
                WHERE purchase_id = ?
            """, conn, params=(purchase_id,))
        return df
    except Exception as e:
        st.error(f"Error al cargar el detalle: {e}")
        return pd.DataFrame()

def agregar_producto(nombre, cantidad, precio, oferta):
    """Agrega un producto a la lista."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO shopping_list (name, quantity, price, offer) VALUES (?, ?, ?, ?)',
                (nombre.strip(), cantidad, precio, oferta.strip() if oferta else None)
            )
            conn.commit()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al agregar producto: {e}")

def modificar_producto(id_producto, nombre, cantidad, precio, oferta):
    """Modifica un producto existente."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
                'UPDATE shopping_list SET name=?, quantity=?, price=?, offer=? WHERE id=?',
                (nombre.strip(), cantidad, precio, oferta.strip() if oferta else None, id_producto)
            )
            conn.commit()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al modificar producto: {e}")

def eliminar_producto(id_producto):
    """Elimina un producto por ID."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute('DELETE FROM shopping_list WHERE id=?', (id_producto,))
            conn.commit()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al eliminar producto: {e}")

def borrar_lista():
    """Vacía toda la lista actual."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute('DELETE FROM shopping_list')
            conn.commit()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al vaciar lista: {e}")

def guardar_historial(total, comercio):
    """Guarda la compra actual en el historial."""
    fecha = datetime.now().strftime("%Y-%m-%d")
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO shopping_history (date, store, total) VALUES (?, ?, ?)',
                (fecha, comercio.strip(), total)
            )
            purchase_id = cursor.lastrowid

            productos = obtener_lista().values.tolist()
            for _, nombre, cantidad, precio, oferta in productos:
                cursor.execute(
                    'INSERT INTO purchase_details (purchase_id, name, quantity, price, offer) VALUES (?, ?, ?, ?, ?)',
                    (purchase_id, nombre, cantidad, precio, oferta)
                )
            conn.commit()
        st.cache_data.clear()
        st.success(f"✅ Compra guardada en '{comercio}' y lista vaciada.")
        st.session_state["comercio_actual"] = ""
    except Exception as e:
        st.error(f"Error al guardar historial: {e}")

# ==========================
# CÁLCULOS
# ==========================
def calcular_subtotal(cantidad, precio, oferta):
    """Calcula el subtotal considerando ofertas."""
    if not oferta:
        return cantidad * precio
    oferta = oferta.strip()
    if oferta == "2x1":
        return (cantidad // 2 + cantidad % 2) * precio
    try:
        descuento = float(oferta)
        return cantidad * precio * (1 - descuento)
    except ValueError:
        return cantidad * precio  # Ignorar oferta si no es válida

def calcular_totales(df):
    """Calcula totales y devuelve DataFrame con subtotal."""
    df_copy = df.copy()
    df_copy["Subtotal"] = df_copy.apply(
        lambda row: calcular_subtotal(row["quantity"], row["price"], row["offer"]), axis=1
    )
    total = df_copy["Subtotal"].sum()
    return df_copy, total

# ==========================
# INTERFAZ DE USUARIO
# ==========================
def main():
    init_db()
    st.title("🛒 Lista de Compras Inteligente")

    menu = st.sidebar.radio("📌 Menú", ["🛒 Lista de Compras", "📜 Historial"])
    st.sidebar.divider()

    if menu == "🛒 Lista de Compras":
        gestionar_lista()
    elif menu == "📜 Historial":
        ver_historial()

# --------------------------
# GESTIÓN DE LISTA
# --------------------------
def gestionar_lista():
    st.subheader("📋 Tu Lista de Compras")
    
    # Inicializar session_state
    if "comercio_actual" not in st.session_state:
        st.session_state.comercio_actual = ""

    comercio = st.text_input("🏪 Nombre del comercio", value=st.session_state.comercio_actual, key="comercio_actual")

    df = obtener_lista()

    if not df.empty:
        df_display, total = calcular_totales(df)

        # Mostrar ID claramente
        df_show = df_display[["id", "name", "quantity", "price", "offer", "Subtotal"]].copy()
        df_show.columns = ["ID", "Producto", "Cant.", "Precio ($)", "Oferta", "Subtotal ($)"]
        df_show["Precio ($)"] = df_show["Precio ($)"].map("${:.2f}".format)
        df_show["Subtotal ($)"] = df_show["Subtotal ($)"].map("${:.2f}".format)
        df_show["Oferta"] = df_show["Oferta"].fillna("—")

        st.dataframe(df_show, use_container_width=True, hide_index=True)

        st.markdown(f"### **Total: $ {total:,.2f}**")

        col1, col2, col3 = st.columns(3)
        with col1:
            id_borrar = st.number_input("ID a eliminar", min_value=1, step=1, key="del_id")
            if st.button("🗑️ Eliminar", use_container_width=True):
                if id_borrar in df["id"].values:
                    eliminar_producto(id_borrar)
                    st.success(f"Producto ID {id_borrar} eliminado.")
                    st.rerun()
                else:
                    st.error("❌ ID no encontrado en la lista.")

        with col2:
            if st.button("🆕 Guardar y vaciar lista", use_container_width=True):
                if not comercio.strip():
                    st.error("⚠️ Ingresa el nombre del comercio.")
                else:
                    guardar_historial(total, comercio)

        with col3:
            if st.button("❌ Vaciar todo", type="secondary", use_container_width=True):
                borrar_lista()
                st.success("Lista vaciada.")
                st.rerun()

    else:
        st.info("📭 Tu lista está vacía. Agrega productos abajo.")

    # --- Formulario de agregar/modificar ---
    st.divider()
    st.subheader("➕ Agregar o Modificar Producto")

    productos_previos = obtener_lista()
    nombres_previos = productos_previos["name"].tolist() if not productos_previos.empty else []

    with st.form("producto_form"):
        # Mostrar opciones con ID para evitar confusión
        opciones = ["➕ Nuevo producto"]
        if not productos_previos.empty:
            for _, row in productos_previos.iterrows():
                opciones.append(f"✏️ ID {row['id']}: {row['name']}")

        seleccion = st.selectbox("Selecciona un producto para editar o nuevo", opciones)

        id_editar = None
        datos_actuales = {}

        if seleccion != "➕ Nuevo producto":
            id_selec = int(seleccion.split(" ")[2])  # Extraer ID de "✏️ ID X: ..."
            fila = productos_previos[productos_previos["id"] == id_selec]
            if not fila.empty:
                datos_actuales = fila.iloc[0].to_dict()
                id_editar = id_selec

        nombre = st.text_input(
            "Nombre del producto",
            value=datos_actuales.get("name", ""),
            placeholder="Ej: Arroz"
        )

        col_a, col_b = st.columns(2)
        with col_a:
            cantidad = st.number_input(
                "Cantidad",
                min_value=1,
                value=int(datos_actuales.get("quantity", 1)),
                step=1
            )
        with col_b:
            precio_str = st.text_input(
                "Precio ($)",
                value="" if not datos_actuales else str(float(datos_actuales["price"])),
                placeholder="Ej: 150.99"
            )

        # Validar precio
        try:
            if not precio_str or precio_str.strip() == "":
                precio = None
            else:
                precio = float(precio_str.replace(",", "."))
                if precio < 0:
                    st.error("⚠️ El precio no puede ser negativo.")
                    precio = None
        except ValueError:
            st.error("⚠️ Precio inválido. Usa números (ej: 129.99 o 129,99)")
            precio = None

        # Campo único para oferta (simplificado)
        oferta = st.text_input(
            "Oferta (opcional)",
            value=datos_actuales.get("offer", "") if datos_actuales else "",
            placeholder="Ej: 2x1, 0.10 (10% off)"
        )

        # Subtotal en tiempo real
        if precio is not None:
            subtotal = calcular_subtotal(cantidad, precio, oferta)
            st.markdown(f"**💵 Subtotal estimado: $ {subtotal:,.2f}**")
        else:
            st.markdown("**💵 Subtotal estimado: —**")

        submitted = st.form_submit_button("💾 Guardar producto", type="primary")

        if submitted:
            if not nombre.strip():
                st.error("⚠️ El nombre del producto es obligatorio.")
            elif precio is None:
                st.error("⚠️ El precio debe ser un número válido.")
            else:
                if id_editar:
                    modificar_producto(id_editar, nombre, cantidad, precio, oferta)
                    st.success("✅ Producto actualizado.")
                else:
                    if nombre in nombres_previos:
                        st.warning("⚠️ Este producto ya existe. Edítalo desde la lista.")
                    else:
                        agregar_producto(nombre, cantidad, precio, oferta)
                        st.success("✅ Producto agregado.")
                st.rerun()


# --------------------------
# HISTORIAL
# --------------------------
def ver_historial():
    st.subheader("📜 Historial de Compras")
    df_hist = obtener_historial()

    if df_hist.empty:
        st.info("📭 Aún no has realizado compras.")
        return

    df_show = df_hist[["id", "date", "store", "total"]].copy()
    df_show.columns = ["ID", "Fecha", "Comercio", "Total ($)"]
    df_show["Total ($)"] = df_show["Total ($)"].map("${:.2f}".format)

    st.dataframe(df_show, use_container_width=True, hide_index=True)

    st.divider()
    compra_id = st.number_input("Ver detalle de compra (ID)", min_value=1, step=1, key="hist_id")
    if st.button("🔍 Mostrar detalle"):
        detalle = obtener_detalle_compra(compra_id)
        if not detalle.empty:
            detalle_calc, total_detalle = calcular_totales(detalle)

            df_detalle = detalle_calc[["name", "quantity", "price", "offer", "Subtotal"]].copy()
            df_detalle.columns = ["Producto", "Cant.", "Precio ($)", "Oferta", "Subtotal ($)"]
            df_detalle["Precio ($)"] = df_detalle["Precio ($)"].map("${:.2f}".format)
            df_detalle["Subtotal ($)"] = df_detalle["Subtotal ($)"].map("${:.2f}".format)
            df_detalle["Oferta"] = df_detalle["Oferta"].fillna("—")

            st.dataframe(df_detalle, use_container_width=True, hide_index=True)
            st.markdown(f"### **Total de la compra: $ {total_detalle:,.2f}**")
        else:
            st.info("❌ No se encontró detalle para ese ID.")


# ==========================
# EJECUCIÓN
# ==========================
if __name__ == "__main__":
    main()
