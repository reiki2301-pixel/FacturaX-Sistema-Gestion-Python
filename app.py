# Importamos todas las librerias que vamos a necesitar.
# `reportlab`: Para crear los PDFs de las facturas.
# `bcrypt`: Para encriptar las contraseñas y que nadie las pueda ver, ¡muy importante!
# `sqlite3`: Para manejar la base de datos, donde guardamos todos los datos (usuarios, clientes, etc.).
# `os`: Para interactuar con el sistema operativo, como crear carpetas si no existen.
# `tkinter` y `ttk`: Para crear la interfaz gráfica, es decir, las ventanas y botones que ve el usuario.
# `datetime`: Para trabajar con fechas, como la fecha de la factura.
# `json`: Para manejar la información de la empresa en un archivo de configuración.
# `ttkbootstrap`: Versión mejorada de `tkinter` que hace que la interfaz se vea más bonita.
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import bcrypt
import sqlite3
import os
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import json

# Importamos la librería ttkbootstrap
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from pathlib import Path

class DatabaseManager:
    """Gestiona la conexión y la estructura de la base de datos."""

    def __init__(self, db_path=None):
        base_dir = Path(__file__).resolve().parent   # carpeta donde está este .py
        self.db_path = str((base_dir / "database" / "facturacion.db") if db_path is None else Path(db_path))
        self.crear_directorio_db()
        print(f"[DB] Usando base de datos en: {self.db_path}")  # ← deja este print para verificar


    def get_db_connection(self):
        """Retorna una conexión a la base de datos."""
        return sqlite3.connect(self.db_path)

    def crear_directorio_db(self):
        """Crea la carpeta de la base de datos si no existe."""
        # Se obtiene el nombre del directorio de la ruta completa de la base de datos.
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def crear_tablas(self):
        """Crea las tablas si no están creadas."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    usuario TEXT NOT NULL UNIQUE,
                    contraseña TEXT NOT NULL,
                    rol TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    apellido TEXT,
                    cif TEXT UNIQUE,
                    direccion TEXT,
                    ciudad TEXT,
                    cp TEXT,
                    email TEXT UNIQUE,
                    telefono TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    descripcion TEXT,
                    precio REAL NOT NULL,
                    tipo TEXT NOT NULL,
                    iva_rate REAL NOT NULL DEFAULT 0.21,
                    irpf_rate REAL NOT NULL DEFAULT 0.0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facturas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER,
                    total REAL NOT NULL DEFAULT 0.0,
                    estado TEXT NOT NULL DEFAULT 'Pendiente',
                    fecha DATE NOT NULL,
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detalles_factura (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    factura_id INTEGER,
                    producto_id INTEGER,
                    cantidad INTEGER NOT NULL,
                    precio_unitario REAL NOT NULL,
                    iva_rate_aplicado REAL NOT NULL,
                    irpf_rate_aplicado REAL NOT NULL,
                    FOREIGN KEY (factura_id) REFERENCES facturas(id),
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)
            conn.commit()

    def crear_usuario_inicial(self):
        """Crea un usuario administrador por defecto si no existe."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            if cursor.fetchone()[0] == 0:
                nombre = "Admin"
                usuario = "admin"
                contrasena_hash = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt())
                rol = "administrador"
                cursor.execute("INSERT INTO usuarios (nombre, usuario, contraseña, rol) VALUES (?, ?, ?, ?)",
                               (nombre, usuario, contrasena_hash, rol))
                conn.commit()
                print("Usuario administrador por defecto creado: 'admin' / 'admin'")

    def actualizar_credenciales_usuario(self, usuario_actual, nuevo_usuario, nueva_contrasena):
        try:
            # Encriptar la nueva contraseña
            hashed_password = bcrypt.hashpw(nueva_contrasena.encode('utf-8'), bcrypt.gensalt())

            # Abrir conexión y cursor solo en este método
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE usuarios SET usuario = ?, contraseña = ? WHERE usuario = ?",
                    (nuevo_usuario, hashed_password.decode('utf-8'), usuario_actual)
                )
                conn.commit()
                return cursor.rowcount > 0  # True si se actualizó al menos 1 usuario
        except sqlite3.Error as e:
            messagebox.showerror("Error de Base de Datos", f"Ha ocurrido un error al actualizar el usuario: {e}")
            return False


class CompanyConfig:
    """Gestiona la configuración de la empresa en un archivo JSON."""

    def __init__(self, config_path="config.json"):
        self.config_path = config_path

    def cargar_configuracion(self):
        """Carga los datos de la empresa desde config.json o crea uno por defecto."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            config_default = {
                "nombre_empresa": "Mi Empresa S.L.",
                "direccion_empresa": "Calle Falsa 123, 1ºA",
                "ciudad_empresa": "Madrid",
                "cp_empresa": "28001",
                "cif_empresa": "B12345678",
                "email_empresa": "empresa@ejemplo.com",
                "telefono_empresa": "123 45 67 89"
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_default, f, indent=4)
            return config_default

    def guardar_configuracion(self, config):
        """Guarda los datos de la empresa en config.json."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)


# Instanciamos los objetos de gestión
db_manager = DatabaseManager()
company_config = CompanyConfig()
configuracion_empresa = company_config.cargar_configuracion()


def cambiar_credenciales_admin():
    """Crea una ventana para cambiar las credenciales de un administrador."""
    top = tb.Toplevel(ventana)
    top.title("Cambiar Credenciales de Administrador")
    centrar_ventana(top, 350, 300)  # subo un poco la altura para que quepan los campos

    # ⭐ Configurar la columna 1 para que se expanda horizontalmente
    top.columnconfigure(1, weight=1)

    # Variables para los campos
    usuario_actual_var = tk.StringVar()
    nuevo_usuario_var = tk.StringVar()
    nueva_contrasena_var = tk.StringVar()
    confirmar_contrasena_var = tk.StringVar()

    # Widgets usando el sistema de grid
    tb.Label(top, text="Usuario Actual:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
    tb.Entry(top, textvariable=usuario_actual_var).grid(row=0, column=1, padx=10, pady=5, sticky="ew")

    tb.Label(top, text="Nuevo Usuario:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
    tb.Entry(top, textvariable=nuevo_usuario_var).grid(row=1, column=1, padx=10, pady=5, sticky="ew")

    tb.Label(top, text="Nueva Contraseña:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
    tb.Entry(top, textvariable=nueva_contrasena_var, show="*").grid(row=2, column=1, padx=10, pady=5, sticky="ew")

    tb.Label(top, text="Confirmar Contraseña:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
    tb.Entry(top, textvariable=confirmar_contrasena_var, show="*").grid(row=3, column=1, padx=10, pady=5, sticky="ew")

    def guardar_cambios():
        usuario_actual = usuario_actual_var.get()
        nuevo_usuario = nuevo_usuario_var.get()
        nueva_contrasena = nueva_contrasena_var.get()
        confirmar_contrasena = confirmar_contrasena_var.get()

        # Validaciones
        if not usuario_actual or not nuevo_usuario or not nueva_contrasena or not confirmar_contrasena:
            messagebox.showerror("Error", "Todos los campos son obligatorios.")
            return

        if nueva_contrasena != confirmar_contrasena:
            messagebox.showerror("Error", "Las contraseñas no coinciden.")
            return

        # Llamar a la función de la base de datos usando el usuario actual proporcionado
        if db_manager.actualizar_credenciales_usuario(usuario_actual, nuevo_usuario, nueva_contrasena):
            messagebox.showinfo("Éxito", "Credenciales actualizadas correctamente.")
            top.destroy()
        else:
            messagebox.showerror("Error", f"No se encontró el usuario '{usuario_actual}' o no se pudo actualizar.")

    # ⭐ Frame para los botones
    frame_botones = tb.Frame(top)
    frame_botones.grid(row=4, column=0, columnspan=2, pady=10)

    tb.Button(frame_botones, text="Guardar Cambios", command=guardar_cambios, bootstyle="success").pack(side="left", padx=5)
    tb.Button(frame_botones, text="Cancelar", command=top.destroy, bootstyle="danger").pack(side="left", padx=5)



# --- FUNCIONES Y LÓGICA EXISTENTE (ADAPTADA) ---

def centrar_ventana(window, width, height):
    """
    Centra las ventanas en la pantalla.
    Recibe la ventana, el ancho y el alto deseado.
    """
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)
    window.geometry('%dx%d+%d+%d' % (width, height, x, y))


# Aquí comprobamos si el usuario y contraseña son correctos.
def verificar_login(usuario, contrasena, ventana_login):
    if not usuario or not contrasena:
        messagebox.showwarning("Campos vacíos", "Por favor ingresa usuario y contraseña.")
        return

    try:
        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT contraseña, rol FROM usuarios WHERE usuario = ?", (usuario,))
        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            hash_contrasena_guardado = resultado[0]
            rol = resultado[1]
            # Se compara la contraseña escrita con la que está encriptada en la base de datos.
            hash_bytes = hash_contrasena_guardado.encode('utf-8') if isinstance(hash_contrasena_guardado,str) else hash_contrasena_guardado
            if bcrypt.checkpw(contrasena.encode('utf-8'), hash_bytes):
                messagebox.showinfo("Éxito", f"Te damos la bienvenida a la aplicaciòn: {usuario}")
                abrir_menu(usuario, rol, ventana_login)
            else:
                messagebox.showerror("Error", "Usuario o contraseña no coinciden")
        else:
            messagebox.showerror("Error", "Usuario no existe")

    except sqlite3.Error as e:
        messagebox.showerror("Error de base de datos", f"Ocurrió un error: {e}")

# Si el login es correcto, abrimos el menú principal de la aplicación.
def abrir_menu(usuario, rol, login_window):
    login_window.withdraw() # Esconde la ventana de login.
    menu_window = tb.Toplevel()
    menu_window.title("Menú Principal")
    centrar_ventana(menu_window, 400, 450)
    tb.Label(menu_window, text=f"Hola, {usuario} ({rol})", font=("Arial", 14)).pack(pady=20)

    # Botones del menú principal.
    tb.Button(menu_window, text="Clientes", width=25, command=lambda: ventana_clientes(rol)).pack(pady=5)
    tb.Button(menu_window, text="Productos / Servicios", width=25, command=lambda: ventana_productos(rol)).pack(pady=5)
    tb.Button(menu_window, text="Facturas", width=25, command=lambda: ventana_editar_factura(rol)).pack(pady=5)

    # Creamos un condicional para que solo los administradores vean estos botones
    if rol.lower() == "administrador":
        tb.Button(menu_window, text="Gestionar Usuarios", width=25, command=ventana_usuarios).pack(pady=5)
        tb.Button(menu_window, text="Configurar Empresa", width=25, command=ventana_configuracion).pack(pady=5)
        tb.Button(menu_window, text="Cambiar Credenciales", width=25, command=cambiar_credenciales_admin).pack(pady=5)

    # Botón para cerrar sesión y volver al login
    def cerrar_sesion():
        menu_window.destroy()
        login_window.deiconify()

    tb.Button(menu_window, text="Cerrar Sesión", width=25, command=cerrar_sesion, bootstyle="danger").pack(pady=20)


# Esta función abre una ventana para configurar los datos de la empresa.
# Sirve para cambiar nombre, dirección, cif, email, etc. y guardarlos en el archivo JSON.
def ventana_configuracion():
    global configuracion_empresa

    def guardar_configuracion():
        nueva_config = {
            "nombre_empresa": entry_nombre.get(),
            "direccion_empresa": entry_direccion.get(),
            "ciudad_empresa": entry_ciudad.get(),
            "cp_empresa": entry_cp.get(),
            "cif_empresa": entry_cif.get(),
            "email_empresa": entry_email.get(),
            "telefono_empresa": entry_telefono.get()
        }
        company_config.guardar_configuracion(nueva_config)
        global configuracion_empresa
        configuracion_empresa = nueva_config
        messagebox.showinfo("Éxito", "Configuración de la empresa guardada correctamente.")
        top.destroy()

    top = tb.Toplevel()
    top.title("Configurar Datos de la Empresa")
    # ⭐ Ajustamos la altura para más espacio
    centrar_ventana(top, 400, 420)

    # ⭐ Permite que la columna y la fila se expandan sin deformar
    top.columnconfigure(1, weight=1)
    top.rowconfigure(7, weight=1)

    # ⭐ Los labels se alinean a la izquierda y los entrys se estiran
    tb.Label(top, text="Nombre de la Empresa:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    entry_nombre = tb.Entry(top)
    entry_nombre.insert(0, configuracion_empresa.get("nombre_empresa", ""))
    entry_nombre.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    tb.Label(top, text="Dirección:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    entry_direccion = tb.Entry(top)
    entry_direccion.insert(0, configuracion_empresa.get("direccion_empresa", ""))
    entry_direccion.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    tb.Label(top, text="Ciudad:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
    entry_ciudad = tb.Entry(top)
    entry_ciudad.insert(0, configuracion_empresa.get("ciudad_empresa", ""))
    entry_ciudad.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

    tb.Label(top, text="Código Postal:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
    entry_cp = tb.Entry(top)
    entry_cp.insert(0, configuracion_empresa.get("cp_empresa", ""))
    entry_cp.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

    tb.Label(top, text="CIF:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
    entry_cif = tb.Entry(top)
    entry_cif.insert(0, configuracion_empresa.get("cif_empresa", ""))
    entry_cif.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

    tb.Label(top, text="Email:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
    entry_email = tb.Entry(top)
    entry_email.insert(0, configuracion_empresa.get("email_empresa", ""))
    entry_email.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

    tb.Label(top, text="Teléfono:").grid(row=6, column=0, padx=5, pady=5, sticky="w")
    entry_telefono = tb.Entry(top)
    entry_telefono.insert(0, configuracion_empresa.get("telefono_empresa", ""))
    entry_telefono.grid(row=6, column=1, padx=5, pady=5, sticky="ew")

    # ⭐ Botón centrado y con tamaño normal (sin sticky="ew")
    tb.Button(top, text="Guardar Cambios", command=guardar_configuracion, bootstyle="success").grid(row=7, column=0,columnspan=2,pady=10)


# Esta función abre la ventana para gestionar los usuarios del sistema.
def ventana_usuarios():
    usuarios_win = tb.Toplevel()
    usuarios_win.title("Gestión de Usuarios")
    centrar_ventana(usuarios_win, 1000, 600)

    # Frame principal donde va la tabla de usuarios
    frame_tabla = tb.Frame(usuarios_win)
    frame_tabla.pack(fill="both", expand=True, padx=10, pady=10)

    # Tabla (Treeview) para mostrar los usuarios con sus columnas
    tabla = tb.Treeview(frame_tabla, columns=("ID", "Nombre", "Usuario", "Rol"),show="headings", bootstyle="primary")
    tabla.heading("ID", text="ID")
    tabla.heading("Nombre", text="Nombre")
    tabla.heading("Usuario", text="Usuario")
    tabla.heading("Rol", text="Rol")

    # Ajustamos ancho y alineación de cada columna
    tabla.column("ID", width=50, anchor="center")
    tabla.column("Nombre", width=200, anchor="center")
    tabla.column("Usuario", width=200, anchor="center")
    tabla.column("Rol", width=150, anchor="center")
    tabla.pack(side="left", fill="both", expand=True)

    # Barra de desplazamiento vertical para la tabla
    scrollbar = tb.Scrollbar(frame_tabla, orient="vertical", command=tabla.yview)
    scrollbar.pack(side="right", fill="y")
    tabla.configure(yscrollcommand=scrollbar.set)

    # ---------------- FUNCIONES INTERNAS ----------------

    # Cargar todos los usuarios desde la base de datos y mostrarlos en la tabla
    def cargar_usuarios():
        for fila in tabla.get_children():
            tabla.delete(fila)  # Limpiar la tabla primero
        with db_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, usuario, rol FROM usuarios")
            for usuario in cursor.fetchall():
                tabla.insert("", "end", values=usuario)

    # Añadir un nuevo usuario
    def añadir_usuario():
        def guardar_usuario():
            nombre = entry_nombre.get()
            usuario = entry_usuario.get()
            contraseña = entry_contraseña.get()
            rol = combo_rol.get()
            # Validamos que no falte nada
            if not nombre or not usuario or not contraseña or not rol:
                messagebox.showerror("Error", "Todos los campos son obligatorios")
                return
            # Encriptamos la contraseña antes de guardarla
            password_encriptada = bcrypt.hashpw(contraseña.encode('utf-8'), bcrypt.gensalt())
            try:
                with db_manager.get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO usuarios (nombre, usuario, contraseña, rol) VALUES (?, ?, ?, ?)",
                                   (nombre, usuario, password_encriptada, rol))
                    conn.commit()
                top.destroy()
                cargar_usuarios()  # Refrescar la tabla
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "El nombre de usuario ya existe")

        # Ventana emergente para introducir datos del nuevo usuario
        top = tb.Toplevel(usuarios_win)
        top.title("Añadir Usuario")
        # ⭐ Ajustamos el tamaño de la ventana
        centrar_ventana(top, 320, 280)
        # ⭐ Permite que la columna y la fila se expandan sin deformar los elementos
        top.columnconfigure(1, weight=1)
        top.rowconfigure(4, weight=1)

        # ⭐ Los labels se alinean a la izquierda con sticky="w"
        tb.Label(top, text="Nombre:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        entry_nombre = tb.Entry(top)
        # ⭐ Los campos de entrada se estiran con sticky="ew"
        entry_nombre.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Usuario:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        entry_usuario = tb.Entry(top)
        entry_usuario.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Contraseña:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        entry_contraseña = tb.Entry(top, show="*")
        entry_contraseña.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Rol:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        combo_rol = tb.Combobox(top, values=["administrador", "empleado"])
        combo_rol.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # ⭐ Botón centrado y con tamaño normal (sin sticky="ew")
        tb.Button(top, text="Guardar", command=guardar_usuario, bootstyle="success").grid(row=4, column=0, columnspan=2,pady=10)

    # Editar un usuario existente
    def editar_usuario():
        seleccionado = tabla.selection()
        if not seleccionado:
            messagebox.showerror("Error", "Selecciona un usuario para editar.")
            return
        usuario_id = tabla.item(seleccionado)["values"][0]
        with db_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nombre, usuario, rol FROM usuarios WHERE id = ?", (usuario_id,))
            datos_usuario = cursor.fetchone()
        if not datos_usuario:
            messagebox.showerror("Error", "No se encontraron los datos del usuario.")
            return

        def guardar_cambios():
            nombre = entry_nombre.get()
            usuario = entry_usuario.get()
            rol = combo_rol.get()
            nueva_contrasena = entry_contrasena.get()
            confirmar_contrasena = entry_confirmar.get()

            if not nombre or not usuario or not rol:
                messagebox.showerror("Error", "Todos los campos son obligatorios.")
                return

            # Lógica para actualizar solo si se ingresó una nueva contraseña
            if nueva_contrasena:
                if nueva_contrasena != confirmar_contrasena:
                    messagebox.showerror("Error", "Las contraseñas no coinciden.")
                    return

                # Encriptar la nueva contraseña con bcrypt
                contrasena_hash = bcrypt.hashpw(nueva_contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                try:
                    with db_manager.get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE usuarios SET nombre = ?, usuario = ?, rol = ?, contraseña = ? WHERE id = ?",
                            (nombre, usuario, rol, contrasena_hash, usuario_id))
                        conn.commit()
                    messagebox.showinfo("Éxito", "Usuario y contraseña actualizados correctamente.")
                    top.destroy()
                    cargar_usuarios()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Error", "El nombre de usuario ya existe.")
            else:
                # Si no se ingresó una nueva contraseña, solo actualizar el nombre y el rol
                try:
                    with db_manager.get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET nombre = ?, usuario = ?, rol = ? WHERE id = ?",
                                       (nombre, usuario, rol, usuario_id))
                        conn.commit()
                    messagebox.showinfo("Éxito", "Usuario actualizado correctamente.")
                    top.destroy()
                    cargar_usuarios()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Error", "El nombre de usuario ya existe.")

        # Ventana para modificar los datos del usuario
        top = tb.Toplevel(usuarios_win)
        top.title("Editar Usuario")
        # ⭐ Ajusta la medida de la ventana para los nuevos campos
        centrar_ventana(top, 320, 380)
        # ⭐ Permite que la columna y la fila se expandan sin deformar los elementos
        top.columnconfigure(1, weight=1)
        top.rowconfigure(5, weight=1)

        # ⭐ Alinea los labels a la izquierda con sticky="w"
        tb.Label(top, text="Nombre:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        entry_nombre = tb.Entry(top)
        entry_nombre.insert(0, datos_usuario[0])
        # ⭐ Los campos de entrada se estiran con sticky="ew"
        entry_nombre.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Usuario:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        entry_usuario = tb.Entry(top)
        entry_usuario.insert(0, datos_usuario[1])
        entry_usuario.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Rol:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        combo_rol = tb.Combobox(top, values=["administrador", "empleado"])
        combo_rol.set(datos_usuario[2])
        combo_rol.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # ⭐ Nuevos campos de contraseña con sticky="w"
        tb.Label(top, text="Nueva Contraseña:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        entry_contrasena = tb.Entry(top, show="*")
        entry_contrasena.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Confirmar Contraseña:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        entry_confirmar = tb.Entry(top, show="*")
        entry_confirmar.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # ⭐ Botón centrado y con tamaño normal (sin sticky="ew")
        tb.Button(top, text="Guardar Cambios", command=guardar_cambios, bootstyle="success").grid(row=5, column=0,columnspan=2, pady=10)

    # Eliminar un usuario
    def eliminar_usuario():
        seleccionado = tabla.selection()
        if not seleccionado:
            messagebox.showerror("Error", "Selecciona un usuario para eliminar")
            return
        usuario_id = tabla.item(seleccionado)["values"][0]
        if usuario_id == 1:  # Protección para no borrar al administrador principal
            messagebox.showerror("Error", "No puedes eliminar el usuario administrador principal.")
            return
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres eliminar este usuario?"):
            with db_manager.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
                conn.commit()
            cargar_usuarios()

    # ---------------- BOTONES ----------------
    frame_botones = tb.Frame(usuarios_win)
    frame_botones.pack(pady=10)
    tb.Button(frame_botones, text="Añadir Usuario", command=añadir_usuario, bootstyle="primary").pack(side="left", padx=5)
    tb.Button(frame_botones, text="Editar Usuario", command=editar_usuario, bootstyle="info").pack(side="left", padx=5)
    tb.Button(frame_botones, text="Eliminar Usuario", command=eliminar_usuario, bootstyle="danger").pack(side="left", padx=5)

    # Cargamos usuarios al iniciar
    cargar_usuarios()



# Esta función abre la ventana para gestionar los clientes.
# Permite buscarlos, verlos en una tabla, añadir nuevos, editarlos o eliminarlos.
def ventana_clientes(rol):
    clientes_win = tb.Toplevel()
    clientes_win.title("Gestión de Clientes")
    centrar_ventana(clientes_win, 1400, 800)

    # --- Barra de búsqueda de clientes ---
    frame_filtros = tb.Frame(clientes_win)
    frame_filtros.pack(fill="x", padx=10, pady=10)
    tb.Label(frame_filtros, text="Buscar por nombre o apellido:").pack(side="left", padx=(0, 5))
    entry_busqueda = tb.Entry(frame_filtros)
    entry_busqueda.pack(side="left", fill="x", expand=True, padx=(0, 10))

    # Botón para buscar por nombre o apellido
    tb.Button(frame_filtros, text="Buscar",command=lambda: cargar_clientes(entry_busqueda.get()),bootstyle="info").pack(side="left", padx=5)

    # Botón para volver a mostrar todos los clientes
    tb.Button(frame_filtros, text="Mostrar Todos",command=lambda: cargar_clientes(""),bootstyle="secondary").pack(side="left", padx=5)
    # --- Fin de búsqueda ---

    # --- Tabla para mostrar los clientes ---
    frame_tabla = tb.Frame(clientes_win)
    frame_tabla.pack(fill="both", expand=True, padx=10, pady=10)
    tabla = tb.Treeview(frame_tabla,columns=("ID", "Nombre", "Apellido", "Email", "Teléfono","Dirección", "Ciudad", "CP", "CIF"),show="headings", bootstyle="primary")

    # Definimos los encabezados de las columnas
    tabla.heading("ID", text="ID")
    tabla.heading("Nombre", text="Nombre")
    tabla.heading("Apellido", text="Apellido")
    tabla.heading("Email", text="Email")
    tabla.heading("Teléfono", text="Teléfono")
    tabla.heading("Dirección", text="Dirección")
    tabla.heading("Ciudad", text="Ciudad")
    tabla.heading("CP", text="C.P.")
    tabla.heading("CIF", text="CIF")

    # Ajustamos tamaños y alineación de columnas
    tabla.column("ID", width=50, anchor="center")
    tabla.column("Nombre", width=100, anchor="center")
    tabla.column("Apellido", width=100, anchor="center")
    tabla.column("Email", width=150, anchor="center")
    tabla.column("Teléfono", width=100, anchor="center")
    tabla.column("Dirección", width=200, anchor="center")
    tabla.column("Ciudad", width=100, anchor="center")
    tabla.column("CP", width=50, anchor="center")
    tabla.column("CIF", width=100, anchor="center")

    tabla.pack(side="left", fill="both", expand=True)

    # Scrollbar para movernos por la tabla si hay muchos clientes
    scrollbar = tb.Scrollbar(frame_tabla, orient="vertical", command=tabla.yview)
    scrollbar.pack(side="right", fill="y")
    tabla.configure(yscrollcommand=scrollbar.set)



    # FUNCIONES INTERNAS

    # Función para cargar clientes desde la base de datos
    def cargar_clientes(nombre_filtro=""):
        # Limpia primero la tabla
        for fila in tabla.get_children():
            tabla.delete(fila)
        with db_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT id, nombre, apellido, email, telefono, direccion, ciudad, cp, cif FROM clientes"
            params = []
            # Si el usuario escribió algo en el buscador, filtramos
            if nombre_filtro:
                query += " WHERE nombre LIKE ? OR apellido LIKE ?"
                params.append(f"%{nombre_filtro}%")
                params.append(f"%{nombre_filtro}%")
            cursor.execute(query, tuple(params))
            # Insertamos los clientes en la tabla
            for cliente in cursor.fetchall():
                tabla.insert("", "end", values=cliente)

    # Añadir un cliente nuevo
    def añadir_cliente():
        def guardar():
            # Recogemos datos de los campos
            nombre = entry_nombre.get()
            apellido = entry_apellido.get()
            email = entry_email.get()
            telefono = entry_telefono.get()
            direccion = entry_direccion.get()
            ciudad = entry_ciudad.get()
            cp = entry_cp.get()
            cif = entry_cif.get()
            # Validamos que no falten los campos obligatorios
            if not nombre or not apellido:
                messagebox.showerror("Error", "Nombre y Apellido son obligatorios")
                return
            with db_manager.get_db_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "INSERT INTO clientes (nombre, apellido, email, telefono, direccion, ciudad, cp, cif) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (nombre, apellido, email, telefono, direccion, ciudad, cp, cif))
                    conn.commit()
                    top.destroy()
                    cargar_clientes()
                except sqlite3.IntegrityError as e:
                    messagebox.showerror("Error", f"Error al guardar el cliente: {e}")

        # Ventana emergente para rellenar datos del cliente
        top = tb.Toplevel(clientes_win)
        top.title("Añadir Cliente")
        # ⭐ Ajustamos el tamaño de la ventana para que se vea mejor
        centrar_ventana(top, 320, 480)

        # ⭐ Permite que la columna y la fila se expandan sin deformar los elementos
        top.columnconfigure(1, weight=1)
        top.rowconfigure(8, weight=1)

        # ⭐ Los labels se alinean a la izquierda y los entrys se estiran
        tb.Label(top, text="Nombre").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        entry_nombre = tb.Entry(top)
        entry_nombre.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Apellido").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        entry_apellido = tb.Entry(top)
        entry_apellido.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Email").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        entry_email = tb.Entry(top)
        entry_email.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Teléfono").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        entry_telefono = tb.Entry(top)
        entry_telefono.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Dirección").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        entry_direccion = tb.Entry(top)
        entry_direccion.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Ciudad").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        entry_ciudad = tb.Entry(top)
        entry_ciudad.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="C.P.").grid(row=6, column=0, padx=5, pady=5, sticky="w")
        entry_cp = tb.Entry(top)
        entry_cp.grid(row=6, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="CIF").grid(row=7, column=0, padx=5, pady=5, sticky="w")
        entry_cif = tb.Entry(top)
        entry_cif.grid(row=7, column=1, padx=5, pady=5, sticky="ew")

        # ⭐ Botón centrado y con tamaño normal (sin sticky="ew")
        tb.Button(top, text="Guardar", command=guardar, bootstyle="success").grid(row=8, column=0, columnspan=2,pady=10)

    # Editar un cliente existente
    def editar_cliente():
        seleccionado = tabla.selection()
        if not seleccionado:
            messagebox.showerror("Error", "Selecciona un cliente para editar.")
            return
        cliente_id = tabla.item(seleccionado)["values"][0]
        with db_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nombre, apellido, email, telefono, direccion, ciudad, cp, cif FROM clientes WHERE id = ?",
                (cliente_id,))
            datos_cliente = cursor.fetchone()

        def guardar_cambios():
            # Recogemos los nuevos datos
            nombre = entry_nombre.get()
            apellido = entry_apellido.get()
            email = entry_email.get()
            telefono = entry_telefono.get()
            direccion = entry_direccion.get()
            ciudad = entry_ciudad.get()
            cp = entry_cp.get()
            cif = entry_cif.get()
            if not nombre or not apellido:
                messagebox.showerror("Error", "Nombre y Apellido son obligatorios")
                return
            with db_manager.get_db_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "UPDATE clientes SET nombre = ?, apellido = ?, email = ?, telefono = ?, direccion = ?, ciudad = ?, cp = ?, cif = ? WHERE id = ?",
                        (nombre, apellido, email, telefono, direccion, ciudad, cp, cif, cliente_id))
                    conn.commit()
                    top.destroy()
                    cargar_clientes()
                except sqlite3.IntegrityError as e:
                    messagebox.showerror("Error", f"Error al guardar los cambios: {e}")

        # Ventana con los datos precargados para editar
        top = tb.Toplevel(clientes_win)
        top.title("Editar Cliente")
        # ⭐ Ajustamos el tamaño de la ventana
        centrar_ventana(top, 320, 480)

        # ⭐ Permite que la columna y la fila se expandan sin deformar los elementos
        top.columnconfigure(1, weight=1)
        top.rowconfigure(8, weight=1)

        labels = ["Nombre", "Apellido", "Email", "Teléfono", "Dirección", "Ciudad", "C.P.", "CIF"]
        entries = []

        for i, label in enumerate(labels):
            # ⭐ Alinea los labels a la izquierda con sticky="w"
            tb.Label(top, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="w")
            e = tb.Entry(top)
            e.insert(0, datos_cliente[i])
            # ⭐ Los campos de entrada se estiran con sticky="ew"
            e.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
            entries.append(e)

        # Desempaquetamos los campos para usarlos después
        entry_nombre, entry_apellido, entry_email, entry_telefono, entry_direccion, entry_ciudad, entry_cp, entry_cif = entries

        # ⭐ Botón centrado y con tamaño normal (sin sticky="ew")
        tb.Button(top, text="Guardar Cambios", command=guardar_cambios, bootstyle="success").grid(row=len(labels),column=0,columnspan=2, pady=10)

    # Eliminar un cliente seleccionado
    def eliminar_cliente():
        seleccionado = tabla.selection()
        if not seleccionado:
            messagebox.showerror("Error", "Selecciona un cliente para eliminar")
            return
        cliente_id = tabla.item(seleccionado)["values"][0]
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres eliminar este cliente?"):
            with db_manager.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
                conn.commit()
            cargar_clientes()

    # ---------------- BOTONES ----------------
    cargar_clientes()  # Mostrar clientes al iniciar
    frame_botones = tb.Frame(clientes_win)
    frame_botones.pack(pady=10)
    tb.Button(frame_botones, text="Añadir Cliente", command=añadir_cliente, bootstyle="primary").pack(side="left", padx=5)
    tb.Button(frame_botones, text="Editar Cliente", command=editar_cliente, bootstyle="info").pack(side="left", padx=5)

    # Creamos el botón de eliminar solo si el usuario es adminitrador
    if rol.lower() == "administrador":
        tb.Button(frame_botones, text="Eliminar Cliente", command=eliminar_cliente, bootstyle="danger").pack(side="left", padx=5)



def ventana_productos(rol):
    productos_win = tb.Toplevel()
    productos_win.title("Gestión de Productos y Servicios")
    centrar_ventana(productos_win, 1400, 800)
    frame_filtros = tb.Frame(productos_win, padding=10)
    frame_filtros.pack(fill="x")
    tb.Label(frame_filtros, text="Buscar por nombre:").pack(side="left", padx=(0, 5))
    entry_busqueda = tb.Entry(frame_filtros)
    entry_busqueda.pack(side="left", padx=(0, 10))
    tb.Label(frame_filtros, text="Filtrar por tipo:").pack(side="left", padx=(10, 5))
    combo_tipo_filtro = tb.Combobox(frame_filtros, values=["Todos", "Producto", "Servicio"], state="readonly")
    combo_tipo_filtro.set("Todos")
    combo_tipo_filtro.pack(side="left", padx=(0, 10))

    def cargar_productos(nombre_filtro="", tipo_filtro="Todos"):
        for fila in tabla.get_children():
            tabla.delete(fila)
        query = "SELECT * FROM productos WHERE 1"
        params = []
        if nombre_filtro:
            query += " AND nombre LIKE ?"
            params.append(f"%{nombre_filtro}%")
        if tipo_filtro != "Todos":
            query += " AND tipo = ?"
            params.append(tipo_filtro)
        with db_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            # DEBUG (puedes quitar esto cuando funcione)
            print("[SQL]", query)
            print("[PARAMS]", params)
            try:
                cursor.execute("SELECT COUNT(*) FROM clientes")
                print("[DEBUG] nº clientes:", cursor.fetchone()[0])
                cursor.execute("SELECT COUNT(*) FROM facturas")
                print("[DEBUG] nº facturas:", cursor.fetchone()[0])
            except Exception as e:
                print("[DEBUG] Error contando filas:", e)

            cursor.execute(query, tuple(params))
            for producto in cursor.fetchall():
                tabla.insert("", "end", values=producto)

    tb.Button(frame_filtros, text="Buscar",command=lambda: cargar_productos(entry_busqueda.get(), combo_tipo_filtro.get()), bootstyle="info").pack(side="left", padx=5)
    frame_tabla = tb.Frame(productos_win)
    frame_tabla.pack(fill="both", expand=True, padx=10, pady=10)
    tabla = tb.Treeview(frame_tabla, columns=("ID", "Nombre", "Descripción", "Precio", "Tipo", "IVA", "IRPF"),show="headings", bootstyle="primary")
    tabla.heading("ID", text="ID")
    tabla.heading("Nombre", text="Nombre")
    tabla.heading("Descripción", text="Descripción")
    tabla.heading("Precio", text="Precio")
    tabla.heading("Tipo", text="Tipo")
    tabla.heading("IVA", text="IVA")
    tabla.heading("IRPF", text="IRPF")
    tabla.column("ID", width=30, anchor="center")
    tabla.column("Nombre", width=120, anchor="center")
    tabla.column("Descripción", width=200, anchor="center")
    tabla.column("Precio", width=80, anchor="center")
    tabla.column("Tipo", width=80, anchor="center")
    tabla.column("IVA", width=60, anchor="center")
    tabla.column("IRPF", width=60, anchor="center")
    tabla.pack(side="left", fill="both", expand=True)
    scrollbar = tb.Scrollbar(frame_tabla, orient="vertical", command=tabla.yview)
    scrollbar.pack(side="right", fill="y")
    tabla.configure(yscrollcommand=scrollbar.set)

    def añadir_producto():
        def guardar():
            nombre = entry_nombre.get()
            descripcion = entry_descripcion.get()
            precio = entry_precio.get()
            tipo = combo_tipo.get()
            if not nombre or not precio or not tipo:
                messagebox.showerror("Error", "Nombre, precio y tipo son obligatorios")
                return
            try:
                precio = float(precio)
            except ValueError:
                messagebox.showerror("Error", "El precio debe ser un número")
                return
            iva_rate = 0.21
            irpf_rate = 0.0
            if tipo == "Servicio":
                irpf_rate = 0.07
            with db_manager.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO productos (nombre, descripcion, precio, tipo, iva_rate, irpf_rate) VALUES (?, ?, ?, ?, ?, ?)",
                    (nombre, descripcion, precio, tipo, iva_rate, irpf_rate))
                conn.commit()
            top.destroy()
            cargar_productos()

        top = tb.Toplevel(productos_win)
        top.title("Añadir Producto/Servicio")
        # ⭐ Ajustamos el tamaño de la ventana
        centrar_ventana(top, 320, 280)
        # ⭐ Permite que la columna y la fila se expandan sin deformar los elementos
        top.columnconfigure(1, weight=1)
        top.rowconfigure(4, weight=1)

        # ⭐ Los labels se alinean a la izquierda y los entrys se estiran
        tb.Label(top, text="Nombre").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        entry_nombre = tb.Entry(top)
        entry_nombre.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Descripción").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        entry_descripcion = tb.Entry(top)
        entry_descripcion.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Precio").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        entry_precio = tb.Entry(top)
        entry_precio.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Tipo").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        combo_tipo = tb.Combobox(top, values=["Producto", "Servicio"])
        combo_tipo.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # ⭐ Botón centrado y con tamaño normal (sin sticky="ew")
        tb.Button(top, text="Guardar", command=guardar, bootstyle="success").grid(row=4, column=0, columnspan=2,pady=10)

    def editar_producto():
        seleccionado = tabla.selection()
        if not seleccionado:
            messagebox.showerror("Error", "Selecciona un producto para editar.")
            return
        producto_id = tabla.item(seleccionado)["values"][0]
        with db_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nombre, descripcion, precio, tipo, iva_rate, irpf_rate FROM productos WHERE id = ?",
                           (producto_id,))
            datos_producto = cursor.fetchone()

        def guardar_cambios():
            nombre = entry_nombre.get()
            descripcion = entry_descripcion.get()
            precio_str = entry_precio.get()
            tipo = combo_tipo.get()
            if not nombre or not precio_str or not tipo:
                messagebox.showerror("Error", "Nombre, precio y tipo son obligatorios.")
                return
            try:
                precio = float(precio_str)
            except ValueError:
                messagebox.showerror("Error", "El precio debe ser un número válido.")
                return
            iva_rate = 0.21
            irpf_rate = 0.0
            if tipo == "Servicio":
                irpf_rate = 0.07
            with db_manager.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE productos SET nombre = ?, descripcion = ?, precio = ?, tipo = ?, iva_rate = ?, irpf_rate = ? WHERE id = ?",
                    (nombre, descripcion, precio, tipo, iva_rate, irpf_rate, producto_id))
                conn.commit()
            top.destroy()
            cargar_productos()

        top = tb.Toplevel(productos_win)
        top.title("Editar Producto/Servicio")
        # ⭐ Ajustamos el tamaño de la ventana para que se vea mejor
        centrar_ventana(top, 320, 280)
        # ⭐ Permite que la columna y la fila se expandan sin deformar los elementos
        top.columnconfigure(1, weight=1)
        top.rowconfigure(4, weight=1)

        # ⭐ Los labels se alinean a la izquierda y los entrys se estiran
        tb.Label(top, text="Nombre:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        entry_nombre = tb.Entry(top)
        entry_nombre.insert(0, datos_producto[0])
        entry_nombre.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Descripción:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        entry_descripcion = tb.Entry(top)
        entry_descripcion.insert(0, datos_producto[1])
        entry_descripcion.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Precio:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        entry_precio = tb.Entry(top)
        entry_precio.insert(0, datos_producto[2])
        entry_precio.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        tb.Label(top, text="Tipo:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        combo_tipo = tb.Combobox(top, values=["Producto", "Servicio"])
        combo_tipo.set(datos_producto[3])
        combo_tipo.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # ⭐ Botón centrado y con tamaño normal (sin sticky="ew")
        tb.Button(top, text="Guardar Cambios", command=guardar_cambios, bootstyle="success").grid(row=4, column=0,
                                                                                                  columnspan=2, pady=10)

    def eliminar_producto():
        seleccionado = tabla.selection()
        if not seleccionado:
            messagebox.showerror("Error", "Selecciona un producto para eliminar")
            return
        producto_id = tabla.item(seleccionado)["values"][0]
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres eliminar este producto/servicio?"):
            with db_manager.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
                conn.commit()
            cargar_productos()

    cargar_productos()
    frame_botones = tb.Frame(productos_win)
    frame_botones.pack(pady=10)

    # Creamos un botón de "Añadir" y "Editar" que siempre esté visible
    tb.Button(frame_botones, text="Añadir Producto/Servicio", command=añadir_producto, bootstyle="primary").pack(side="left", padx=5)
    tb.Button(frame_botones, text="Editar Producto/Servicio", command=editar_producto, bootstyle="info").pack(side="left",padx=5)

    # Creamos el botón de eliminar solo si el usuario es administrador
    if rol.lower() == "administrador":
        tb.Button(frame_botones, text="Eliminar Producto/Servicio", command=eliminar_producto, bootstyle="danger").pack(side="left", padx=5)


def crear_pdf(factura_data,detalles_factura,datos_cliente,configuracion_empresa,factura_path):
    """
    Esta función crea un documento PDF con los datos de una factura.
    No se modifica ya que se debe quedar intacta.
    """
    if not os.path.exists("facturas"):
        os.makedirs("facturas")
    doc = SimpleDocTemplate(factura_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Centered', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT))

    # Título de la factura
    story.append(Paragraph("<b>FACTURA</b>", styles['Centered']))
    story.append(Spacer(1, 0.2 * inch))

    # Datos de la empresa (Emisor)
    story.append(Paragraph(f"<b>Emisor:</b>", styles['Left']))
    story.append(Paragraph(f"{configuracion_empresa['nombre_empresa']}", styles['Left']))
    story.append(Paragraph(f"CIF: {configuracion_empresa['cif_empresa']}", styles['Left']))
    story.append(Paragraph(f"Dirección: {configuracion_empresa['direccion_empresa']}, {configuracion_empresa['cp_empresa']}",styles['Left']))
    story.append(Paragraph(f"Ciudad: {configuracion_empresa['ciudad_empresa']}", styles['Left']))
    story.append(Paragraph(f"Email: {configuracion_empresa['email_empresa']}", styles['Left']))
    story.append(Paragraph(f"Teléfono: {configuracion_empresa['telefono_empresa']}", styles['Left']))
    story.append(Spacer(1, 0.2 * inch))

    # Datos del cliente (Receptor)
    story.append(Paragraph(f"<b>Cliente:</b>", styles['Left']))
    story.append(Paragraph(f"Nombre: {datos_cliente[1]} {datos_cliente[2]}", styles['Left']))
    story.append(Paragraph(f"CIF: {datos_cliente[3]}", styles['Left']))
    story.append(Paragraph(f"Dirección: {datos_cliente[4]}", styles['Left']))
    story.append(Paragraph(f"Ciudad: {datos_cliente[5]}", styles['Left']))
    story.append(Paragraph(f"CP: {datos_cliente[6]}", styles['Left']))
    story.append(Paragraph(f"Email: {datos_cliente[7]}", styles['Left']))
    story.append(Paragraph(f"Teléfono: {datos_cliente[8]}", styles['Left']))
    story.append(Spacer(1, 0.2 * inch))

    # Datos de la factura
    story.append(Paragraph(f"<b>Número de Factura:</b> {factura_data[0]}", styles['Left']))
    story.append(Paragraph(f"<b>Fecha:</b> {factura_data[1]}", styles['Left']))
    story.append(Spacer(1, 0.2 * inch))

    # Contenido de la tabla
    data = [["Descripción", "Cantidad", "Precio Unitario", "Subtotal", "IVA", "IRPF", "Total"]]
    subtotal_general = 0
    iva_total = 0
    irpf_total = 0
    total_general = 0

    for item in detalles_factura:
        producto_id, cantidad, precio_unitario, iva_rate, irpf_rate = item[2], item[3], item[4], item[5], item[6]
        subtotal = cantidad * precio_unitario
        iva = subtotal * iva_rate
        irpf = subtotal * irpf_rate
        total = subtotal + iva - irpf

        # Obtener nombre del producto
        with db_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nombre FROM productos WHERE id = ?", (producto_id,))
            nombre_producto = cursor.fetchone()[0]

        data.append([
            nombre_producto,
            str(cantidad),
            f"{precio_unitario:.2f} €",
            f"{subtotal:.2f} €",
            f"{iva:.2f} €",
            f"{irpf:.2f} €",
            f"{total:.2f} €"
        ])
        subtotal_general += subtotal
        iva_total += iva
        irpf_total += irpf
        total_general += total

    data.append(["", "", "", "", "", "", ""])
    data.append(["", "", "", "<b>Subtotal:</b>", f"{subtotal_general:.2f} €", "", ""])
    data.append(["", "", "", "<b>IVA:</b>", f"{iva_total:.2f} €", "", ""])
    data.append(["", "", "", "<b>IRPF:</b>", f"{irpf_total:.2f} €", "", ""])
    data.append(["", "", "", "<b>Total:</b>", f"{total_general:.2f} €", "", ""])

    table = Table(data, colWidths=[3 * inch, 0.7 * inch, 1 * inch, 1 * inch, 0.7 * inch, 0.7 * inch, 1 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(table)
    doc.build(story)
    messagebox.showinfo("Éxito", f"Factura {factura_data[0]} creada en {factura_path}")


# MANTÉN ESTA FUNCIÓN SEPARADA Y SIN MODIFICACIONES
def cargar_facturas(tabla_facturas, cliente="", estado="Todos", min_importe="", max_importe="", fecha=""):
    # Limpia la tabla primero
    for item in tabla_facturas.get_children():
        tabla_facturas.delete(item)

    try:
        with db_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT f.id, c.nombre || ' ' || c.apellido as cliente, f.total, f.estado, f.fecha
                FROM facturas f
                JOIN clientes c ON f.cliente_id = c.id
                WHERE 1=1
            """
            params = []

            if cliente:
                query += " AND (c.nombre || ' ' || c.apellido LIKE ? OR c.nombre LIKE ? OR c.apellido LIKE ?)"
                params.append(f"%{cliente}%")
                params.append(f"%{cliente}%")
                params.append(f"%{cliente}%")

            if estado and estado != "Todos":
                query += " AND f.estado = ?"
                params.append(estado)

            if min_importe:
                query += " AND f.total >= ?"
                params.append(float(min_importe))

            if max_importe:
                query += " AND f.total <= ?"
                params.append(float(max_importe))

            if fecha:
                try:
                    fecha_db = datetime.strptime(fecha, "%d/%m/%Y").strftime("%Y-%m-%d")
                except ValueError:
                    try:
                        fecha_db = datetime.strptime(fecha, "%Y/%m/%d").strftime("%Y-%m-%d")
                    except ValueError:
                        fecha_db = fecha

                query += " AND f.fecha = ?"
                params.append(fecha_db)

            # 🔎 DEBUG: mostrar la query y los parámetros
            print("[SQL]", query)
            print("[PARAMS]", params)

            cursor.execute(query, tuple(params))
            resultados = cursor.fetchall()

            # 🔎 DEBUG: cuántas facturas se encontraron
            print("[DEBUG] nº facturas encontradas:", len(resultados))
            for factura in resultados:
                print("[DEBUG] fila:", factura)
                tabla_facturas.insert("", "end", values=factura)

    except Exception as e:
        messagebox.showerror("Error de base de datos", f"Error al cargar facturas: {e}")



def limpiar_filtros(entry_cliente, combo_estado, entry_min_importe, entry_max_importe, entry_fecha, tabla_facturas):
    # Limpiamos todos los campos de búsqueda
    entry_cliente.delete(0, tk.END)
    combo_estado.current(0)  # vuelve a "Todos"
    entry_min_importe.delete(0, tk.END)
    entry_max_importe.delete(0, tk.END)
    entry_fecha.delete(0, tk.END)

    # Recargar todas las facturas sin filtros
    try:
        cargar_facturas(tabla_facturas)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron recargar las facturas: {e}")


def crear_pdf_factura(factura_id):
    """
    Crea un archivo PDF para una factura específica
    """
    # Esta función es el corazón del programa, donde se genera el PDF de la factura.
    # Es bastante larga porque hay que configurar muchas cosas para que el PDF
    # quede bonito y con todos los datos.

    # 1. Configuración de archivos y directorios
    directorio_facturas = ("facturas")
    # Comprueba si existe la carpeta 'facturas'. Si no, la crea.
    if not os.path.exists(directorio_facturas):
        os.makedirs(directorio_facturas)

    nombre_archivo = f"Factura_{factura_id}.pdf"
    ruta_completa = os.path.join(directorio_facturas, nombre_archivo)
    try:
        # 2. Obtener los datos de la factura y los detalles de los items
        with db_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            # Coge todos los datos del cliente y la factura de la base de datos.
            cursor.execute("""
                SELECT f.id, f.fecha, c.nombre, c.apellido, c.direccion, c.ciudad, c.cp, c.email, c.telefono, c.cif
                FROM facturas f
                JOIN clientes c ON f.cliente_id = c.id
                WHERE f.id = ?
            """, (factura_id,))
            factura_info = cursor.fetchone()

            # Si no encuentra la factura, avisa con un error.
            if not factura_info:
                print(f"Error: No se encontró la factura con ID {factura_id}")
                return

            # Asigna los datos a variables para usarlos más cómodamente.
            factura_id_db, fecha, nombre_cliente, apellido_cliente, direccion_cliente, ciudad_cliente, cp_cliente, email_cliente, telefono_cliente, cif_cliente = factura_info

            # Coge los productos de la factura.
            cursor.execute("""
                SELECT p.nombre, df.cantidad, df.precio_unitario, df.iva_rate_aplicado, df.irpf_rate_aplicado
                FROM detalles_factura df
                JOIN productos p ON df.producto_id = p.id
                WHERE df.factura_id = ? AND p.tipo = 'Producto'
            """, (factura_id,))
            productos = cursor.fetchall()

            # Coge los servicios de la factura.
            cursor.execute("""
                SELECT p.nombre, df.cantidad, df.precio_unitario, df.iva_rate_aplicado, df.irpf_rate_aplicado
                FROM detalles_factura df
                JOIN productos p ON df.producto_id = p.id
                WHERE df.factura_id = ? AND p.tipo = 'Servicio'
            """, (factura_id,))
            servicios = cursor.fetchall()

            if not productos and not servicios:
                print("Advertencia: La factura no tiene productos ni servicios.")
                return

        # 3. Configurar el PDF
        # Aquí se inicia la creación del documento PDF con un tamaño de página y márgenes.
        doc = SimpleDocTemplate(ruta_completa, pagesize=letter, leftMargin=0.5 * inch, rightMargin=0.5 * inch)
        story = []
        # Coge los estilos de texto predefinidos de la librería `reportlab`.
        styles = getSampleStyleSheet()

        # Aquí se crean todos los estilos de texto que se van a usar en el PDF.
        # Es como crear plantillas para los títulos, subtítulos, el texto normal,
        # y cómo se alinean los párrafos (a la izquierda, derecha o centro).
        styles.add(ParagraphStyle(name='FacturaHeading1', fontSize=12, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='FacturaNormal', fontSize=12, fontName='Helvetica'))
        styles.add(ParagraphStyle(name='RightAlign', alignment=TA_RIGHT, fontSize=12, fontName='Helvetica'))
        styles.add(ParagraphStyle(name='LeftAlign', alignment=TA_LEFT, fontSize=12, fontName='Helvetica'))
        styles.add(ParagraphStyle(name='NormalRight', alignment=TA_RIGHT, fontSize=12, fontName='Helvetica'))
        styles.add(ParagraphStyle(name='FacturaLeftAlign', alignment=TA_LEFT, fontSize=10, fontName='Helvetica'))
        styles.add(ParagraphStyle(name='FacturaRightAlign', alignment=TA_RIGHT, fontSize=12, fontName='Helvetica'))

        # Estilo para la palabra FACTURA
        styles.add(ParagraphStyle(name='FacturaTitle', alignment=TA_CENTER, fontSize=18, fontName='Helvetica-Bold'))

        # Estilo para datos de empresa
        styles.add(ParagraphStyle(name='EmpresaLeftAlign', alignment=TA_LEFT, fontSize=10, fontName='Helvetica', leftIndent=20))

        # Estilos de fuente para los datos del cliente
        styles.add(ParagraphStyle(name='FacturaClienteNormal', fontSize=10, fontName='Helvetica'))
        styles.add(ParagraphStyle(name='FacturaClienteLeftAlign', alignment=TA_LEFT, fontSize=10, fontName='Helvetica'))
        styles.add(ParagraphStyle(name='FacturaClienteRightAlign', alignment=TA_RIGHT, fontSize=10, fontName='Helvetica'))
        styles.add(ParagraphStyle(name='FacturaClienteCentre', alignment=TA_CENTER, fontSize=10, fontName='Helvetica', leftIndent=53))
        styles.add(ParagraphStyle(name='FacturaClienteLeftIndent', alignment=TA_LEFT, fontSize=10, fontName='Helvetica', leftIndent=110))

        # Estilos para Número de factura y fecha
        styles.add(ParagraphStyle(name='NumFechaLeftIndent', alignment=TA_LEFT, fontSize=10, fontName='Helvetica', leftIndent=370))

        # 4. Contenido del PDF
        # Aquí se empieza a "construir" el contenido.
        story.append(Paragraph("<b>FACTURA</b>", styles['FacturaTitle']))
        story.append(Spacer(1, 50))

        # Se crea la tabla de datos de la empresa con su estilo.
        data_empresa = [
            [Paragraph("<b>DATOS DE LA EMPRESA</b>", styles['EmpresaLeftAlign'])],
            [Paragraph("<b>Tecnologi S.L.</b>", styles['EmpresaLeftAlign'])],
            [Paragraph(f"<b>Dirección:</b> Calle Lirio 23, 1ªA", styles['EmpresaLeftAlign'])],
            [Paragraph(f"<b>C.P.:</b> 28938, Móstoles (Madrid)", styles['EmpresaLeftAlign'])],
            [Paragraph(f"<b>CIF:</b> B12345678", styles['EmpresaLeftAlign'])],
            [Paragraph(f"<b>Email:</b> tecnologi@gmail.com", styles['EmpresaLeftAlign'])],
            [Paragraph(f"<b>Teléfono:</b> +34 123 45 67 89", styles['EmpresaLeftAlign'])]
        ]

        # Se crea la tabla y se le aplica un estilo.
        table_empresa = Table(data_empresa, colWidths=[doc.width / 2.0])
        table_empresa.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2)
        ]))

        # Se crea la tabla de datos del cliente con su estilo.
        data_cliente = [
            # Puedes usar un estilo con sangría también para el título si quieres
            [Paragraph("<b>DATOS DEL CLIENTE</b>", styles['FacturaClienteCentre'])],
            [Paragraph(f"<b>Nombre:</b> {nombre_cliente} {apellido_cliente}", styles['FacturaClienteLeftIndent'])],
            [Paragraph(f"<b>Dirección:</b> {direccion_cliente}", styles['FacturaClienteLeftIndent'])],
            [Paragraph(f"<b>C.P.:</b> {cp_cliente}, {ciudad_cliente}", styles['FacturaClienteLeftIndent'])],
            [Paragraph(f"<b>CIF:</b> {cif_cliente}", styles['FacturaClienteLeftIndent'])],
            [Paragraph(f"<b>Email:</b> {email_cliente}", styles['FacturaClienteLeftIndent'])],
            [Paragraph(f"<b>Teléfono:</b> {telefono_cliente}", styles['FacturaClienteLeftIndent'])]
        ]

        table_cliente = Table(data_cliente, colWidths=[doc.width / 2.0])
        table_cliente.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2)
        ]))

        # Tabla principal con empresa a la izquierda y cliente a la derecha.
        # Se unen las dos tablas de arriba en una sola para que salgan una al lado de la otra.
        data_header_main = [
            [table_empresa, table_cliente]
        ]

        # Definimos la tabla principal del encabezado.
        table_header_main = Table(data_header_main, colWidths=[doc.width / 2.0, doc.width / 2.0])
        table_header_main.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0)
        ]))

        # Añadimos el header al story
        story.append(table_header_main)
        story.append(Spacer(1, 24))

        # Tabla del número de factura y fecha, alineada a la derecha
        # Se añaden la fecha y el número de factura.
        factura_info_data = [
            [Paragraph(f"<b>Número de Factura:</b> {factura_id}", styles['NumFechaLeftIndent'])],
            [Paragraph(f"<b>Fecha:</b> {fecha}", styles['NumFechaLeftIndent'])]
        ]
        factura_info_table = Table(factura_info_data, hAlign='RIGHT')
        story.append(factura_info_table)
        story.append(Spacer(1, 12))

        # Tabla de productos
        # Solo se creara si hay productos
        base_imponible_productos = 0.0
        # Comprueba si hay productos para crear la tabla, si no, se la salta.
        if productos:
            story.append(Paragraph("<b>Productos</b>", styles['FacturaHeading1']))
            story.append(Spacer(1, 20))

            # Encabezado de la tabla de productos.
            data_productos = [["Concepto", "Cantidad", "Precio Unitario", "Subtotal", "IVA", "Total Item"]]
            # Recorre la lista de productos y calcula los subtotales, IVAs, etc.
            for producto in productos:
                nombre, cantidad, precio, iva_rate, _ = producto
                subtotal = round(cantidad * precio, 2)
                iva_item = round(subtotal * iva_rate, 2)
                total_item = round(subtotal + iva_item, 2)
                base_imponible_productos += subtotal

                # Añade los datos de cada producto a la tabla.
                data_productos.append([
                    Paragraph(nombre, styles['LeftAlign']),
                    Paragraph(f"{cantidad}", styles['RightAlign']),
                    Paragraph(f"{precio:.2f}€", styles['RightAlign']),
                    Paragraph(f"{subtotal:.2f}€", styles['RightAlign']),
                    Paragraph(f"{iva_item:.2f}€", styles['RightAlign']),
                    Paragraph(f"{total_item:.2f}€", styles['RightAlign'])
                ])

            # Crea la tabla con los datos y le aplica un estilo (colores, bordes, etc.).
            tabla_productos = Table(data_productos, colWidths=[122, 83, 85, 83, 83, 83])
            tabla_productos.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00427c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (-1, 0), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#00427c')),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT')
            ]))
            story.append(tabla_productos)
            story.append(Spacer(1, 40))

        # Tabla de servicios
        # Solo se creara si tenemos algun servicios
        base_imponible_servicios = 0.0
        iva_total_servicios = 0.0
        irpf_total_servicios = 0.0

        # Mismo proceso para los servicios.
        if servicios:
            story.append(Paragraph("<b>Servicios</b>", styles['FacturaHeading1']))
            story.append(Spacer(1, 20))

            data_servicios = [["Concepto", "Cantidad", "Precio Unitario", "Subtotal", "IVA", "IRPF", "Total Item"]]
            for servicio in servicios:
                nombre, cantidad, precio, iva_rate, irpf_rate = servicio
                subtotal = round(cantidad * precio, 2)
                iva_item = round(subtotal * iva_rate, 2)
                irpf_item = round(subtotal * irpf_rate, 2)
                total_item = round(subtotal + iva_item - irpf_item, 2)
                base_imponible_servicios += subtotal
                iva_total_servicios += iva_item
                irpf_total_servicios += irpf_item

                data_servicios.append([
                    Paragraph(nombre, styles['LeftAlign']),
                    Paragraph(f"{cantidad}", styles['RightAlign']),
                    Paragraph(f"{precio:.2f}€", styles['RightAlign']),
                    Paragraph(f"{subtotal:.2f}€", styles['RightAlign']),
                    Paragraph(f"{iva_item:.2f}€", styles['RightAlign']),
                    Paragraph(f"-{irpf_item:.2f}€" if irpf_item > 0 else "0.00€", styles['RightAlign']),
                    Paragraph(f"{total_item:.2f}€", styles['RightAlign'])
                ])

            tabla_servicios = Table(data_servicios, colWidths=[117, 60, 85, 73, 68, 68, 68])
            tabla_servicios.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00427c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (-1, 0), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#00427c')),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT')
            ]))
            story.append(tabla_servicios)
            story.append(Spacer(1, 40))

        # Tabla de totales
        # Sumamos todos los totales para la factura final
        # Se suman la base imponible, el IVA y el IRPF de productos y servicios.
        base_imponible_total = base_imponible_productos + base_imponible_servicios

        iva_total_productos = 0.0
        for producto in productos:
            _, cantidad, precio, iva_rate, _ = producto
            subtotal = round(cantidad * precio, 2)
            iva_total_productos += round(subtotal * iva_rate, 2)

        iva_total = iva_total_productos + iva_total_servicios
        irpf_total = irpf_total_servicios
        total_factura = base_imponible_total + iva_total - irpf_total

        # Se crea la tabla final con los totales.
        data_totales = [
            [Paragraph("<b>Base Imponible</b>", styles['RightAlign']),
             Paragraph(f"<b>{base_imponible_total:.2f}€</b>", styles['RightAlign'])],
            [Paragraph("<b>Total IVA (21%)</b>", styles['RightAlign']),
             Paragraph(f"<b>{iva_total:.2f}€</b>", styles['RightAlign'])],
            [Paragraph("<b>Total IRPF (7%)</b>", styles['RightAlign']),
             Paragraph(f"<b>-{irpf_total:.2f}€</b>", styles['RightAlign'])],
            [Paragraph("<b>Total Factura</b>", styles['RightAlign']),
             Paragraph(f"<b>{total_factura:.2f}€</b>", styles['RightAlign'])]
        ]

        # Se le aplica un estilo.
        tabla_totales_interna = Table(data_totales, colWidths=[140, 80])
        tabla_totales_interna.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#00427c')),
        ]))

        tabla_totales_externa = Table([[tabla_totales_interna]], colWidths=[550])
        tabla_totales_externa.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))

        story.append(Spacer(1, 60))
        story.append(tabla_totales_externa)

        # 5. Construir y guardar el PDF
        doc.build(story)
        print(f"PDF de la factura {factura_id} generado correctamente en {ruta_completa}")

    except Exception as e:
        # Si algo falla en la creación del PDF, muestra un error.
        print(f"Ocurrió un error al generar el PDF: {e}")


# Añadir un producto o servicio a la factura.
def añadir_item_a_factura(factura_win, tabla_productos_factura, tipo):
    # Esta función se encarga de abrir una ventana para que puedas
    # elegir un producto o servicio y añadirlo a la tabla de la factura que
    # estamos creando. Le pasamos el tipo ('Producto' o 'Servicio') para saber que buscar.

    def guardar_item():
        # Esta función se activa cuando pulsamos el botón "Añadir".
        seleccionado = listbox_productos.curselection()
        # Primero, comprueba que has seleccionado algo de la lista.
        if not seleccionado:
            messagebox.showerror("Error", "Debes seleccionar un ítem.")
            return

        nombre_item = listbox_productos.get(seleccionado[0])
        cantidad_str = entry_cantidad.get()

        # Verifica que has metido una cantidad.
        if not cantidad_str:
            messagebox.showerror("Error", "Debes especificar una cantidad.")
            return

        try:
            # Intenta convertir la cantidad a un número entero y se asegura de
            # que sea positivo. Si no, muestra un error.
            cantidad = int(cantidad_str)
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número entero positivo.")
            return

        # Busca en la base de datos la información del producto o servicio seleccionado,
        # incluyendo los precios y las tasas de impuestos (IVA e IRPF).
        with db_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, precio, iva_rate, irpf_rate FROM productos WHERE nombre = ?", (nombre_item,))
            producto_id, precio_unitario, iva_rate, irpf_rate = cursor.fetchone()

        # Aquí se calculan todos los totales por cada ítem. Se redondean a 2 decimales.
        subtotal = round(precio_unitario * cantidad, 2)
        iva_item = round(subtotal * iva_rate, 2)
        irpf_item = round(subtotal * irpf_rate, 2)
        total_item = round(subtotal + iva_item - irpf_item, 2)

        # Inserta los datos calculados en la tabla temporal de la factura.
        # El ID del producto lo guardamos en una columna oculta para usarlo
        # más tarde al guardar la factura definitiva.
        tabla_productos_factura.insert("", "end", values=(nombre_item, cantidad, precio_unitario, subtotal, iva_item, irpf_item, total_item, producto_id))
        top.destroy()

    def filtrar_items(event=None):
        # Esta función filtra la lista de productos/servicios mientras escribes
        # en el campo de búsqueda.
        filtro = entry_busqueda.get().lower()
        items_filtrados = [item for item in items_disponibles if filtro in item.lower()]
        listbox_productos.delete(0, tk.END)
        for item in items_filtrados:
            listbox_productos.insert(tk.END, item)

    # Crea la ventana de selección.
    top = tb.Toplevel(factura_win)
    top.title(f"Añadir {tipo}")
    centrar_ventana(top, 450, 450)

    # Busca en la base de datos todos los productos o servicios del tipo que
    # le hemos pasado ('Producto' o 'Servicio').
    items_disponibles = []
    with db_manager.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM productos WHERE tipo = ?", (tipo,))
        for item in cursor.fetchall():
            items_disponibles.append(item[0])

    # Crea los widgets para la búsqueda.
    frame_busqueda = tb.Frame(top, padding=10)
    frame_busqueda.pack(fill="x")
    tb.Label(frame_busqueda, text="Buscar:").pack(side="left", padx=(0, 5))
    entry_busqueda = tb.Entry(frame_busqueda)
    entry_busqueda.pack(side="left", fill="x", expand=True, padx=5)
    entry_busqueda.bind("<KeyRelease>", filtrar_items)

    # Crea la Lista de productos/servicios.
    frame_lista = tb.Frame(top, padding=10)
    frame_lista.pack(fill="both", expand=True)

    listbox_productos = tk.Listbox(frame_lista, width=50, height=10, bd=0, activestyle="none", font=("Helvetica", 10))
    listbox_productos.pack(side="left", fill="both", expand=True)

    # Añade un scrollbar para poder moverte por la lista si es muy larga.
    scrollbar = tb.Scrollbar(frame_lista, orient="vertical", command=listbox_productos.yview)
    scrollbar.pack(side="right", fill="y")
    listbox_productos.configure(yscrollcommand=scrollbar.set)

    # Rellena la lista con todos los productos/servicios disponibles.
    for item in items_disponibles:
        listbox_productos.insert(tk.END, item)

    # Widgets para pedir la cantidad.
    frame_cantidad = tb.Frame(top, padding=10)
    frame_cantidad.pack(fill="x")
    tb.Label(frame_cantidad, text="Cantidad:").pack(side="left", padx=(0, 5))
    entry_cantidad = tb.Entry(frame_cantidad, width=10)
    entry_cantidad.pack(side="left")

    # Botón final para añadir el ítem.
    tb.Button(top, text=f"Añadir {tipo}", command=guardar_item, bootstyle="success").pack(pady=10)


# Creamos la factura con (IVA/IRPF)
def crear_factura(tabla_principal, entry_cliente, combo_estado, entry_min_importe, entry_max_importe, entry_fecha, factura_id=None):
    # Esta es la función principal para crear o editar una factura.
    # El parámetro `factura_id` se usa para saber si estamos creando una nueva
    # (es `None`) o editando una que ya existe.

    factura_win = tb.Toplevel()
    factura_win.title("Crear Nueva Factura" if factura_id is None else "Editar Factura")
    centrar_ventana(factura_win, 950, 500)

    # Frame para los datos del cliente, con su combobox.
    frame_cliente = tb.LabelFrame(factura_win, text="Datos del Cliente", padding=10)
    frame_cliente.pack(fill="x", padx=10, pady=5)

    tb.Label(frame_cliente, text="Cliente:").pack(side="left", padx=5)
    clientes_combobox = tb.Combobox(frame_cliente, state="readonly")
    clientes_combobox.pack(side="left", fill="x", expand=True, padx=5)

    # Coge todos los clientes de la base de datos y los mete en el combobox.
    clientes = {}
    with db_manager.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, apellido FROM clientes")
        for cliente_id, nombre, apellido in cursor.fetchall():
            clientes[f"{nombre} {apellido}"] = cliente_id

    clientes_combobox["values"] = list(clientes.keys())

    # Frame para la tabla de productos y servicios de la factura.
    frame_productos = tb.LabelFrame(factura_win, text="Productos y Servicios", padding=10)
    frame_productos.pack(fill="both", expand=True, padx=10, pady=5)

    # Se crea la tabla (Treeview) para mostrar los ítems de la factura.
    tabla_productos_factura = tb.Treeview(frame_productos, columns=("Nombre", "Cantidad", "Precio Unitario", "Subtotal", "IVA", "IRPF", "Total Item", "ID Producto"), show="headings", bootstyle="primary")
    tabla_productos_factura.heading("Nombre", text="Nombre")
    tabla_productos_factura.heading("Cantidad", text="Cantidad")
    tabla_productos_factura.heading("Precio Unitario", text="Precio Unitario")
    tabla_productos_factura.heading("Subtotal", text="Subtotal")
    tabla_productos_factura.heading("IVA", text="IVA")
    tabla_productos_factura.heading("IRPF", text="IRPF")
    tabla_productos_factura.heading("Total Item", text="Total Item")
    tabla_productos_factura.heading("ID Producto", text="ID Producto") # Columna oculta para el ID

    # Ajustamos el tamaño y la alineación de las columnas.
    tabla_productos_factura.column("Nombre", width=180, anchor="center")
    tabla_productos_factura.column("Cantidad", width=70, anchor="center")
    tabla_productos_factura.column("Precio Unitario", width=100, anchor="center")
    tabla_productos_factura.column("Subtotal", width=90, anchor="center")
    tabla_productos_factura.column("IVA", width=70, anchor="center")
    tabla_productos_factura.column("IRPF", width=70, anchor="center")
    tabla_productos_factura.column("Total Item", width=100, anchor= "center")
    tabla_productos_factura.column("ID Producto", width=0, stretch=False) # Hacemos la columna invisible


    # Scrollbar para la tabla
    scrollbar = tb.Scrollbar(frame_productos, orient="vertical", command=tabla_productos_factura.yview)
    scrollbar.pack(side="right", fill="y")
    tabla_productos_factura.configure(yscrollcommand=scrollbar.set)
    tabla_productos_factura.pack(fill="both", expand=True)

    def guardar_factura(tabla_principal, entry_cliente, combo_estado, entry_min_importe, entry_max_importe,entry_fecha):
        # Esta función guarda la factura en la base de datos.
        cliente_seleccionado = clientes_combobox.get()
        if not cliente_seleccionado:
            messagebox.showerror("Error", "Debes seleccionar un cliente.")
            return

        cliente_id = clientes.get(cliente_seleccionado)

        # Recorre la tabla de productos y servicios para coger toda la información.
        productos_factura = []
        total_factura_final = 0.0
        for item in tabla_productos_factura.get_children():
            nombre, cantidad, precio, subtotal, iva, irpf, total_item, producto_id = tabla_productos_factura.item(item,"values")

            cantidad_num = int(cantidad)
            precio_num = float(precio)

            productos_factura.append({"nombre": nombre,"cantidad": cantidad_num,"precio_unitario": precio_num,"iva": iva,"irpf": irpf,"producto_id": producto_id})
            total_factura_final += float(total_item)

        if not productos_factura:
            messagebox.showerror("Error", "La factura no puede estar vacía.")
            return

        try:
            with db_manager.get_db_connection() as conn:
                cursor = conn.cursor()

                if factura_id is None:  # 👉 usa el factura_id de la función principal
                    fecha_actual = datetime.now().strftime("%Y-%m-%d")
                    cursor.execute("""
                        INSERT INTO facturas (fecha, cliente_id, total)
                        VALUES (?, ?, ?)
                    """, (fecha_actual, cliente_id, total_factura_final))
                    factura_id_guardada = cursor.lastrowid
                else:
                    cursor.execute("""
                        UPDATE facturas SET cliente_id = ?, total = ?
                        WHERE id = ?
                    """, (cliente_id, total_factura_final, factura_id))
                    cursor.execute("DELETE FROM detalles_factura WHERE factura_id = ?", (factura_id,))
                    factura_id_guardada = factura_id

                # Guardar detalles
                for producto in productos_factura:
                    cursor.execute("SELECT iva_rate, irpf_rate FROM productos WHERE id = ?", (producto["producto_id"],))
                    iva_rate_aplicado, irpf_rate_aplicado = cursor.fetchone()

                    cursor.execute(
                        "INSERT INTO detalles_factura (factura_id, producto_id, cantidad, precio_unitario, iva_rate_aplicado, irpf_rate_aplicado) VALUES (?, ?, ?, ?, ?, ?)",
                        (factura_id_guardada, producto["producto_id"], producto["cantidad"],producto["precio_unitario"], iva_rate_aplicado, irpf_rate_aplicado))

                conn.commit()

            messagebox.showinfo("Éxito", f"Factura {'actualizada' if factura_id is not None else 'creada'} con éxito.")
            factura_win.destroy()

            cargar_facturas(tabla_principal,cliente=entry_cliente.get(),estado=combo_estado.get(), min_importe=entry_min_importe.get(), max_importe=entry_max_importe.get(), fecha=entry_fecha.get())

        except sqlite3.Error as e:
            messagebox.showerror("Error de base de datos", f"Ocurrió un error al guardar la factura: {e}")

    def eliminar_producto_de_tabla():
        # Función para quitar un ítem de la tabla temporal de la factura.
        seleccionado = tabla_productos_factura.selection()
        if not seleccionado:
            messagebox.showerror("Error", "Selecciona un producto de la tabla para eliminarlo.")
            return
        tabla_productos_factura.delete(seleccionado)

    # Si estamos editando una factura, rellenamos los campos y la tabla
    # con los datos que ya tiene.
    if factura_id is not None:
        with db_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cliente_id FROM facturas WHERE id = ?", (factura_id,))
            cliente_id_factura = cursor.fetchone()[0]

            # Buscar el nombre del cliente para seleccionarlo en el combobox
            cursor.execute("SELECT nombre, apellido FROM clientes WHERE id = ?", (cliente_id_factura,))
            nombre_cliente, apellido_cliente = cursor.fetchone()
            clientes_combobox.set(f"{nombre_cliente} {apellido_cliente}")

            # Cargar los productos de la factura en la tabla
            cursor.execute("""
                SELECT p.nombre, df.cantidad, df.precio_unitario, df.iva_rate_aplicado, df.irpf_rate_aplicado, p.id
                FROM detalles_factura df
                JOIN productos p ON df.producto_id = p.id
                WHERE df.factura_id = ?
            """, (factura_id,))
            for nombre, cantidad, precio, iva_rate, irpf_rate, producto_id in cursor.fetchall():
                subtotal = round(cantidad * precio, 2)
                iva_item = round(subtotal * iva_rate, 2)
                irpf_item = round(subtotal * irpf_rate, 2)
                total_item = round(subtotal + iva_item - irpf_item, 2)
                tabla_productos_factura.insert("", "end", values=(nombre, cantidad, precio, subtotal, iva_item, irpf_item, total_item, producto_id))

    # Frame para los botones de gestión de la factura.
    frame_botones_factura = tb.Frame(factura_win)
    frame_botones_factura.pack(pady=10)

    # Botones separados para productos y servicios
    tb.Button(frame_botones_factura, text="Añadir Producto", command=lambda: añadir_item_a_factura(factura_win, tabla_productos_factura, "Producto"), bootstyle="primary").pack(side="left", padx=5)
    tb.Button(frame_botones_factura, text="Añadir Servicio", command=lambda: añadir_item_a_factura(factura_win, tabla_productos_factura, "Servicio"), bootstyle="primary").pack(side="left", padx=5)
    tb.Button(frame_botones_factura, text="Eliminar Item", command=eliminar_producto_de_tabla, bootstyle="danger").pack(side="left", padx=5)
    tb.Button(frame_botones_factura, text="Guardar Factura", command=lambda: guardar_factura(tabla_principal, entry_cliente, combo_estado, entry_min_importe, entry_max_importe, entry_fecha), bootstyle="success").pack(side="left", padx=5)

def editar_factura(tabla_principal, entry_cliente, combo_estado, entry_min_importe, entry_max_importe, entry_fecha):
    seleccion = tabla_principal.selection()
    if not seleccion:
        messagebox.showerror("Error", "Debes seleccionar una factura para editarla.")
        return

    factura_id = tabla_principal.item(seleccion[0], "values")[0]  # coge el ID de la factura seleccionada
    crear_factura(tabla_principal, entry_cliente, combo_estado, entry_min_importe, entry_max_importe, entry_fecha, factura_id=factura_id)

# Ventana de gestión de facturas
def ventana_editar_factura(rol):
    facturas_win = tb.Toplevel()
    facturas_win.title("Gestión de Facturas")
    centrar_ventana(facturas_win, 1400, 800)

    # --- FILTROS (ARRIBA) ---
    frame_busqueda = tb.Frame(facturas_win, bootstyle="success-flat")
    frame_busqueda.pack(side="top", fill="x", padx=10, pady=8)

    tb.Label(frame_busqueda, text="Cliente:").pack(side="left", padx=5)
    entry_cliente = tb.Entry(frame_busqueda, bootstyle="success-flat")
    entry_cliente.pack(side="left", padx=5)

    tb.Label(frame_busqueda, text="Estado:").pack(side="left", padx=5)
    combo_estado = tb.Combobox(frame_busqueda, values=["Todos", "Pagada", "Pendiente"],
                               bootstyle="success-flat", width=12)
    combo_estado.current(0)
    combo_estado.pack(side="left", padx=5)

    tb.Label(frame_busqueda, text="Importe:").pack(side="left", padx=5)
    entry_min_importe = tb.Entry(frame_busqueda, width=8, bootstyle="success-flat")
    entry_min_importe.pack(side="left", padx=2)
    tb.Label(frame_busqueda, text="a").pack(side="left", padx=2)
    entry_max_importe = tb.Entry(frame_busqueda, width=8, bootstyle="success-flat")
    entry_max_importe.pack(side="left", padx=2)

    tb.Label(frame_busqueda, text="Fecha (DD/MM/AAAA):").pack(side="left", padx=5)
    entry_fecha = tb.Entry(frame_busqueda, bootstyle="success-flat")
    entry_fecha.pack(side="left", padx=5)

    def buscar_facturas():
        cargar_facturas(tabla_facturas,cliente=entry_cliente.get().strip(),estado=combo_estado.get().strip(),min_importe=entry_min_importe.get().strip(),max_importe=entry_max_importe.get().strip(),fecha=entry_fecha.get().strip())

    def limpiar():
        limpiar_filtros(entry_cliente, combo_estado, entry_min_importe,entry_max_importe, entry_fecha, tabla_facturas)

    tb.Button(frame_busqueda, text="Buscar", command=buscar_facturas,bootstyle="success").pack(side="left", padx=6)
    tb.Button(frame_busqueda, text="Limpiar", command=limpiar,bootstyle="success").pack(side="left", padx=6)

    # --- TABLA (CENTRO) ---
    frame_tabla = tb.Frame(facturas_win)
    frame_tabla.pack(side="top", fill="both", expand=True, padx=10, pady=10)

    tabla_facturas = ttk.Treeview(frame_tabla,columns=("id", "cliente", "total", "estado", "fecha"),show="headings",height=20)
    tabla_facturas.heading("id", text="ID")
    tabla_facturas.heading("cliente", text="Cliente")
    tabla_facturas.heading("total", text="Total")
    tabla_facturas.heading("estado", text="Estado")
    tabla_facturas.heading("fecha", text="Fecha")

    tabla_facturas.column("id", width=60, anchor="center")
    tabla_facturas.column("cliente", width=220, anchor="center")
    tabla_facturas.column("total", width=100, anchor="center")
    tabla_facturas.column("estado", width=120, anchor="center")
    tabla_facturas.column("fecha", width=120, anchor="center")

    tabla_facturas.pack(side="left", fill="both", expand=True)

    scrollbar = tb.Scrollbar(frame_tabla, orient="vertical", command=tabla_facturas.yview)
    scrollbar.pack(side="right", fill="y")
    tabla_facturas.configure(yscrollcommand=scrollbar.set)

    # --- ACCIONES (BOTONES ABAJO) ---
    def _seleccion_id():
        sel = tabla_facturas.selection()
        if not sel:
            messagebox.showerror("Error", "Selecciona una factura.")
            return None
        return tabla_facturas.item(sel[0])["values"][0]

    def crear():
        crear_factura(tabla_facturas)

    def editar():
        factura_id = _seleccion_id()
        if factura_id is None:
            return
        crear_factura(tabla_facturas, factura_id)

    def generar_pdf():
        factura_id = _seleccion_id()
        if factura_id is None:
            return
        crear_pdf_factura(factura_id)
        messagebox.showinfo("Éxito", "PDF generado correctamente.")

    def eliminar():
        factura_id = _seleccion_id()
        if factura_id is None:
            return
        if not messagebox.askyesno("Confirmar", f"¿Eliminar la factura {factura_id}?"):
            return
        with db_manager.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM detalles_factura WHERE factura_id=?", (factura_id,))
            cur.execute("DELETE FROM facturas WHERE id=?", (factura_id,))
            conn.commit()
        cargar_facturas(tabla_facturas)
        messagebox.showinfo("Éxito", "Factura eliminada.")

    def cambiar_estado(estado):
        factura_id = _seleccion_id()
        if factura_id is None:
            return
        with db_manager.get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE facturas SET estado=? WHERE id=?", (estado, factura_id))
            conn.commit()
        cargar_facturas(tabla_facturas)
        messagebox.showinfo("Éxito", f"Factura marcada como {estado}.")

    frame_botones = tb.Frame(facturas_win)
    frame_botones.pack(side="bottom", pady=8)

    tb.Button(frame_botones, text="Crear Factura", command=lambda: crear_factura(tabla_facturas,entry_cliente,combo_estado,entry_min_importe,entry_max_importe,entry_fecha),bootstyle="primary").pack(side="left", padx=5)
    tb.Button(frame_botones, text="Editar Factura", command=lambda: editar_factura(tabla_facturas,entry_cliente,combo_estado,entry_min_importe,entry_max_importe,entry_fecha),bootstyle="info").pack(side="left", padx=5)
    tb.Button(frame_botones, text="Generar PDF", command=generar_pdf, bootstyle="light").pack(side="left", padx=5)

    # ⭐ Condición para mostrar el botón de eliminar solo a los administradores
    if rol.lower() == "administrador":
        tb.Button(frame_botones, text="Eliminar Factura", command=eliminar, bootstyle="danger").pack(side="left",padx=5)

    tb.Button(frame_botones, text="Marcar como Pagada", command=lambda: cambiar_estado("Pagada"),bootstyle="success").pack(side="left", padx=5)
    tb.Button(frame_botones, text="Marcar como Pendiente", command=lambda: cambiar_estado("Pendiente"),bootstyle="warning").pack(side="left", padx=5)

    # Cargar al abrir
    cargar_facturas(tabla_facturas)




# Lógica de inicio (manteniendo las llamadas originales)
db_manager.crear_tablas()
db_manager.crear_usuario_inicial()

# Creación de la ventana de login
ventana = tb.Window(themename="superhero")
ventana.title("Login - Facturación")
centrar_ventana(ventana, 300, 200)

# Widgets de la ventana de login
tb.Label(ventana, text="Usuario:").pack(pady=5)
entry_usuario = tb.Entry(ventana)
entry_usuario.pack()
tb.Label(ventana, text="Contraseña:").pack(pady=5)
entry_contraseña = tb.Entry(ventana, show="*")
entry_contraseña.pack()

tb.Button(ventana, text="Login", command=lambda: verificar_login(entry_usuario.get(), entry_contraseña.get(), ventana),bootstyle="primary").pack(pady=10)

ventana.mainloop()