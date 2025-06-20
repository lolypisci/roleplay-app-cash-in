# Roleplay Archive: Cash In

**Qué hace:**  
Permite a estudiantes grabar roleplays “buyer/seller” en un supermercado, registrar productos y enviarlos a un backend; el profesor luego revisa y escucha.

**Cómo usar:**  
1. Student App: instala Python y dependencias (`pip install sounddevice numpy requests`), en `student_app.py` pone `BACKEND_URL="https://TU_URL_RAILWAY"`, y ejecuta `python student_app.py`.  
2. Backend: despliega en Railway conectando este repo, con start command `uvicorn main:app --host 0.0.0.0 --port $PORT`. Obtén la URL fija y ponla en Student App.  
3. Teacher’s View: abre `https://TU_URL_RAILWAY/` en el navegador, pulsa “Load Sessions” para ver audios.

**Política:**  
Uso no comercial sólo personal/educativo. No redistribuir ni obtener beneficio. Ver LICENSE.

**Contacto:**  
Loli – lolypisci@gmail.com