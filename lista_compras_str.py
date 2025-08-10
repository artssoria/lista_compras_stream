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
    
    # Tabla de historial de compras
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS shopping_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        total REAL NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()

# CRUD productos
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

# Historial
def guardar_historial(total):
    fecha = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO shopping_history (date, total) VALUES (?, ?)',
        (fecha, total)
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

def borrar_lista():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM shopping_list')
    conn.commit()
    conn.close()

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
        if productos:
            data, total = calcular_totales(productos)
            df = pd.DataFrame(data, columns=["ID", "Nombre", "Cantidad", "Precio", "Subtotal"])
            st.table(df.style.format({"Precio": "{:.2f}", "Subtotal": "{:.2f}"}))
            st.success(f"💰 Total: ${total:.2f}")

            # Botones de acción
            cols = st.columns(3)
            with cols[0]:
                if st.button("🗑️ Borrar Producto"):
                    id_borrar = st.number_input("ID a borrar", min_value=1, step=1)
                    if st.button("Confirmar Borrado"):
                        eliminar_producto(id_borrar)
                        st.success("Producto eliminado.")
                        st.rerun()
            with cols[1]:
                if st.button("🆕 Iniciar nueva compra"):
                    guardar_historial(total)
                    borrar_lista()
                    st.success("Compra guardada en historial y lista vaciada.")
                    st.rerun()
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
            df_hist = pd.DataFrame(historial, columns=["ID", "Fecha", "Total"])
            st.table(df_hist.style.format({"Total": "{:.2f}"}))
        else:
            st.info("No hay compras registradas.")

if __name__ == "__main__":
    main()