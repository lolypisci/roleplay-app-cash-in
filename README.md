# Rolefy 🎭📚

**Rolefy** es una herramienta educativa pensada para facilitar y registrar actividades de roleplay orales en el aula de idiomas. Está diseñada para entornos de enseñanza de inglés como lengua extranjera (ESL), especialmente en niveles escolares.

Permite grabar interacciones simuladas entre estudiantes (por ejemplo, comprador y vendedor en un supermercado), asociar cada grabación con nombres, productos y precios, y guardar automáticamente un registro con opción de feedback y nota por parte del profesor.

---

## 🎯 Características principales

- Grabación de roleplays directamente desde la app de escritorio.
- Asociación de datos: comprador, vendedor, productos, precios.
- Generación de recibo ficticio para cada roleplay.
- Guardado automático en base de datos.
- Vista del profesor con tabla de todos los registros.
- Campos editables: feedback y nota por roleplay.
- Botón de copia de seguridad manual desde interfaz.
- Botón para reiniciar Railway directamente desde interfaz.
- Acceso offline (modo local) o mediante servidor en Railway.
- Interfaz moderna, clara y funcional.

---

## 🖥️ Requisitos

- Python 3.10 o superior.
- Navegador web moderno (para la interfaz de profesor).
- Sistema operativo Windows (para app de escritorio, con `student_app.py`).
- Cuenta Railway gratuita (opcional, para despliegue online).
- Git (opcional, si usas backup + control de versiones).

---

## 🚀 Instalación local (modo offline)

1. Clona este repositorio o copia todos los archivos en una carpeta.
2. Asegúrate de tener Python instalado.
3. Crea un entorno virtual:

   ```bash
   python -m venv venv
Activa el entorno virtual:

Windows:

bash
Copiar código
venv\Scripts\activate
macOS/Linux:

bash
Copiar código
source venv/bin/activate
Instala dependencias:

bash
Copiar código
pip install -r requirements.txt
Ejecuta la app:

bash
Copiar código
uvicorn main:app --reload
Abre en tu navegador:

arduino
Copiar código
http://localhost:8000
☁️ Uso con Railway (modo online)
Crea un proyecto en Railway.

Sube este repositorio.

Añade variables de entorno:

ini
Copiar código
RAILWAY_TOKEN=tu_token
PROJECT_ID=tu_project_id
Desde la app Teacher View podrás reiniciar Railway automáticamente si algo se cuelga.

🧪 Interfaz de profesor
Accede a http://localhost:8000 para ver la tabla de registros.

Puedes filtrar y ordenar por nombre o fecha.

Puedes editar directamente los campos de feedback y nota.

Usa el botón de copia de seguridad para descargar un archivo .json con todos los roleplays.

🧑‍🎓 Interfaz de grabación (Rolefy Student App)
Ejecuta student_app.py como aplicación de escritorio.

Introduce nombres, graba el roleplay, añade los productos y sus precios.

Se enviará el audio y los datos al servidor local o Railway, según configuración.

Se genera un recibo visual al finalizar.

🗃️ Copias de seguridad
Desde la interfaz de profesor, puedes hacer clic en "Backup" y se guardará un archivo .json con todos los datos actuales en la carpeta /updates.

Esto permite guardar progreso, evitar pérdida de datos y mantener historial.

🛠️ Personalización y extensiones
Esta app puede adaptarse para otros tipos de simulaciones educativas (por ejemplo, entrevistas de trabajo, situaciones de emergencia, etc.). Si quieres ampliar o modificar Rolefy, puedes contactarme.

📁 Estructura de archivos
css
Copiar código
📦rolefy/
 ┣ 📂static/              → Archivos estáticos (HTML, CSS, JS)
 ┣ 📂uploads/             → Grabaciones de audio
 ┣ 📂updates/             → Copias de seguridad
 ┣ main.py                → Backend principal con FastAPI
 ┣ launcher.py            → Launcher para gestión rápida
 ┣ student_app.py         → Aplicación de escritorio para estudiantes
 ┣ models.py              → Modelo de datos SQLAlchemy
 ┣ database.py            → Conexión a base de datos SQLite
 ┣ .env                   → Variables secretas (Railway)
 ┣ requirements.txt       → Dependencias Python
 ┣ README.md              → Este archivo
 ┗ ...
📌 Política de privacidad
Rolefy no recopila ni envía datos a terceros. Toda la información (audios, nombres, evaluaciones) queda almacenada localmente o en el servidor Railway bajo tu control.

Tú decides si quieres almacenar los datos online o mantenerlos en local.

📬 Contacto
Para sugerencias, soporte o desarrollo personalizado:

Email: lolypisci@gmail.com

© 2025 Rolefy. Todos los derechos reservados.