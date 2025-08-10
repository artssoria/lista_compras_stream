import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "shopping_list.db"

# ==========================
# BASE DE DATOS
# ==========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla de productos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS shopping_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        offer TEXT
    )
    ''')
    
    # Tabla de historial de compras con comercio
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS shopping_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        store TEXT NOT NULL,
        total REAL NOT NULL
    )
    ''')

    # Tabla para detalle de productos de compras pasadas
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
    conn.close()

# ==========================
# CRUD productos
# ==========================
def agregar_producto(nombre, cantidad, precio, oferta):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO shopping_list (name, quantity, price, offer) VALUES (?, ?, ?, ?)',
        (nombre, cantidad, precio, oferta)
    )
    conn.commit()
    conn.close()

def modificar_producto(id_producto, nombre, cantidad, precio, oferta):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE shopping_list SET name=?, quantity=?, price=?, offer=? WHERE id=?',
        (nombre, cantidad, precio, oferta, id_producto)
    )
    conn.commit()
    conn.close()

def eliminar_producto(id_producto):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM shopping_list WHERE id=?', (id_producto,))
    conn.commit()
    conn.close()

def obtener_lista():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM shopping_list')
    productos = cursor.fetchall()
    conn.close()
    return productos

def borrar_lista():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM shopping_list')
    conn.commit()
    conn.close()

# ==========================
# Historial
# ==========================
def guardar_historial(total, comercio):
    fecha = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO shopping_history (date, store, total) VALUES (?, ?, ?)',
        (fecha, comercio, total)
    )
    purchase_id = cursor.lastrowid

    # Guardar detalle de la compra
    productos = obtener_lista()
    for _, nombre, cantidad, precio, oferta in productos:
        cursor.execute(
            'INSERT INTO purchase_details (purchase_id, name, quantity, price, offer) VALUES (?, ?, ?, ?, ?)',
            (purchase_id, nombre, cantidad, precio, oferta)
        )

    conn.commit()
    conn.close()

def obtener_historial():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM shopping_history ORDER BY date DESC')
    historial = cursor.fetchall()
    conn.close()
    return historial

def obtener_detalle_compra(purchase_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT name, quantity, price, offer FROM purchase_details WHERE purchase_id=?', (purchase_id,))
    detalle = cursor.fetchall()
    conn.close()
    return detalle

# ==========================
# CÁLCULOS
# ==========================
def calcular_totales(productos):
    total = 0
    data = []
    for id, nombre, cantidad, precio, oferta in productos:
        subtotal = cantidad * precio
        if oferta == "2x1":
            subtotal = (cantidad // 2 * precio) + (cantidad % 2 * precio)
        elif oferta:
            try:
                subtotal *= (1 - float(oferta))
            except:
                pass
        total += subtotal
        data.append([id, nombre, cantidad, precio, subtotal])
    return data, total

def calcular_subtotal_vivo(cantidad, precio, oferta):
    subtotal = cantidad * precio
    if oferta == "2x1":
        subtotal = (cantidad // 2 * precio) + (cantidad % 2 * precio)
    elif oferta:
        try:
            subtotal *= (1 - float(oferta))
        except:
            pass
    return subtotal

# ==========================
# INTERFAZ
# ==========================
def main():
    st.set_page_config(page_title="Lista de Compras", layout="centered")
    st.title("🛒 Lista de Compras con Historial")
    init_db()

    menu = ["Lista y Gestión", "Historial de Compras"]
    choice = st.sidebar.selectbox("Menú", menu)

    if choice == "Lista y Gestión":
        st.subheader("📋 Lista de Compras")
        
        productos = obtener_lista()
        comercio_input = st.text_input("🏪 Nombre del comercio para la compra actual")

        if productos:
            data, total = calcular_totales(productos)
            df = pd.DataFrame(data, columns=["ID", "Nombre", "Cantidad", "Precio", "Subtotal"])
            st.table(df.style.format({"Precio": "{:.2f}", "Subtotal": "{:.2f}"}))
            st.success(f"💰 Total: ${total:.2f}")

            cols = st.columns(3)
            with cols[0]:
                id_borrar = st.number_input("ID a borrar", min_value=1, step=1)
                if st.button("🗑️ Borrar Producto"):
                    eliminar_producto(id_borrar)
                    st.success("Producto eliminado.")
                    st.rerun()

            with cols[1]:
                if st.button("🆕 Iniciar nueva compra"):
                    if comercio_input.strip():
                        guardar_historial(total, comercio_input)
                        borrar_lista()
                        st.success(f"Compra guardada en historial ({comercio_input}) y lista vaciada.")
                        st.rerun()
                    else:
                        st.error("Debes ingresar el nombre del comercio antes de guardar.")

            with cols[2]:
                if st.button("❌ Vaciar lista"):
                    borrar_lista()
                    st.success("Lista vaciada.")
                    st.rerun()

        else:
            st.warning("La lista está vacía.")

        st.markdown("---")
        st.subheader("➕ Agregar / ✏️ Modificar Producto")

        opciones = {f"Nuevo producto": None}
        opciones.update({f"{p[0]} - {p[1]}": p[0] for p in productos})

        seleccion = st.selectbox("Selecciona un producto para modificar o 'Nuevo producto'", list(opciones.keys()))
        id_producto = opciones[seleccion]

        if id_producto:
            producto = next(p for p in productos if p[0] == id_producto)
            nombre = st.text_input("Nombre", producto[1])
            cantidad = st.number_input("Cantidad", min_value=1, value=producto[2])
            precio = st.number_input("Precio", min_value=0.0, format="%.2f", value=producto[3])
            oferta = st.text_input("Oferta", producto[4] if producto[4] else "")
        else:
            nombre = st.text_input("Nombre")
            cantidad = st.number_input("Cantidad", min_value=1, value=1)
            precio = st.number_input("Precio", min_value=0.0, format="%.2f")
            oferta = st.text_input("Oferta (ej: '2x1' o '0.10')")

        subtotal_vivo = calcular_subtotal_vivo(cantidad, precio, oferta)
        st.info(f"💵 Subtotal estimado: ${subtotal_vivo:.2f}")

        if st.button("Guardar"):
            if nombre and precio > 0:
                if id_producto:
                    modificar_producto(id_producto, nombre, cantidad, precio, oferta)
                    st.success("Producto modificado correctamente.")
                else:
                    agregar_producto(nombre, cantidad, precio, oferta)
                    st.success("Producto agregado correctamente.")
                st.rerun()
            else:
                st.error("Por favor ingresa un nombre y precio válido.")

    elif choice == "Historial de Compras":
        st.subheader("📜 Historial de Compras")
        historial = obtener_historial()
        if historial:
            df_hist = pd.DataFrame(historial, columns=["ID", "Fecha", "Comercio", "Total"])
            st.table(df_hist.style.format({"Total": "{:.2f}"}))

            compra_id = st.number_input("ID de compra para ver detalle", min_value=1, step=1)
            if st.button("Mostrar detalle"):
                detalle = obtener_detalle_compra(compra_id)
                if detalle:
                    data = []
                    total_detalle = 0
                    for nombre, cantidad, precio, oferta in detalle:
                        subtotal = calcular_subtotal_vivo(cantidad, precio, oferta)
                        total_detalle += subtotal
                        data.append([nombre, cantidad, precio, subtotal])
                    df_detalle = pd.DataFrame(data, columns=["Nombre", "Cantidad", "Precio", "Subtotal"])
                    st.table(df_detalle.style.format({"Precio": "{:.2f}", "Subtotal": "{:.2f}"}))
                    st.success(f"💰 Total de la compra: ${total_detalle:.2f}")
                else:
                    st.info("No se encontraron productos para esta compra.")
        else:
            st.info("No hay compras registradas.")

if __name__ == "__main__":
    main()