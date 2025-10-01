## FacturaX: Sistema de Gestión y Facturación en Python



### 💡 Descripción del Proyecto

**FacturaX** es una aplicación de escritorio completa y robusta desarrollada en **Python** diseñada para la gestión integral de clientes, productos y la **generación automatizada de facturas en PDF**.

Este proyecto fue desarrollado como mi Trabajo Final de Curso, demostrando la capacidad de construir una solución de negocio con autenticación segura y gestión de bases de datos relacionales, siendo ideal para autónomos y pequeñas empresas.

### ⚙️ Tecnologías Clave

| Componente | Tecnología | Propósito Clave |
| :--- | :--- | :--- |
| **Lenguaje** | Python | Lógica de negocio y backend de la aplicación. |
| **Interfaz Gráfica (GUI)** | **Tkinter** / `ttkbootstrap` | Interfaz de escritorio visual y moderna. |
| **Base de Datos** | **SQLite3** | Almacenamiento de datos local, ligero y portátil. |
| **Seguridad** | **Bcrypt** | Encriptado seguro de contraseñas de usuarios. |
| **Automatización** | **ReportLab** | Creación de facturas profesionales en formato PDF. |
| **Gestión de Archivos** | **Pathlib** | Gestión eficiente de rutas y archivos del sistema. |

### ✨ Funcionalidades Destacadas

| Categoría | Funcionalidades |
| :--- | :--- |
| **Seguridad** | **Sistema de Login** con autenticación de usuarios y gestión de **roles (Administrador/Empleado)**. Encriptado de contraseñas mediante `bcrypt`. |
| **Datos** | Gestión completa **(CRUD)** de Clientes, Productos, Facturas y Usuarios. Uso de un **Modelo de Datos Relacional** en SQLite para la integridad. |
| **Automatización** | Generación de facturas profesionales en formato **PDF** con cálculos automáticos de **IVA** e **IRPF** utilizando `ReportLab`. |
| **Control** | Funciones de filtrado de facturas por estado (`Pagada`/`Pendiente`), importe, cliente y fecha. |
| **Diseño** | Interfaz de usuario **visual e intuitiva** con componentes mejorados de `ttkbootstrap`. |

### 🛠️ Instalación y Uso (Instrucciones)

Para clonar y ejecutar este proyecto en tu entorno local, sigue los siguientes pasos:

**1. Requisitos:**

* **Python 3.x** instalado.

**2. Clonar el Repositorio:**

```bash
git clone [https://github.com/tu-usuario/FacturaX-Sistema-Gestion-Python.git](https://github.com/tu-usuario/FacturaX-Sistema-Gestion-Python.git)
cd FacturaX-Sistema-Gestion-Python