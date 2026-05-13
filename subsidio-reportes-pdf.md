# subsidio-reportes-pdf

**Guía rápida para usuarios**

Este programa te permite generar PDFs a partir de archivos de Excel/CSV de subsidios, de forma automática y sencilla.

---

## ¿Qué necesito?

1. Tener los archivos CSV del formulario principal y de los subformularios (por ejemplo, SubForm4).
2. Colocar los archivos del formulario principal en la carpeta `input/main/` y los de subformularios en `input/sub/`.
3. Tener instalado Python (pide ayuda si no sabes instalarlo).

---

## ¿Cómo uso el programa?

1. Abre una terminal o consola en la carpeta del proyecto.
2. Ejecuta este comando:
   ```bash
   python generate_pdfs.py --main input/main --sub input/sub --out output/pdfs
   ```
3. Espera a que termine. Los PDFs aparecerán en la carpeta `output/pdfs/`.

+---
+
+## Opciones útiles
+
+- Para generar solo los primeros 100 registros (más rápido):
+  ```bash
+  python generate_pdfs.py --main input/main --sub input/sub --out output/pdfs --limit 100
+  ```
+- Para generar PDFs solo para ciertos DUIs:
+  ```bash
+  python generate_pdfs.py --main input/main --sub input/sub --out output/pdfs --only "06784334-6,03934980-5"
+  ```
+- Para incluir todos los campos aunque estén vacíos:
+  ```bash
+  python generate_pdfs.py --main input/main --sub input/sub --out output/pdfs --include-empty
+  ```
+- Para obtener todos los PDFs juntos en un archivo ZIP:
+  ```bash
+  python generate_pdfs.py --main input/main --sub input/sub --out output/pdfs --zip
+  ```

---

+## ¿Dónde veo los resultados?
+
+Tus PDFs estarán en la carpeta que pusiste en `--out`, por ejemplo:
+
+```
+output/pdfs/
+  06784334-6.pdf
+  03934980-5.pdf
+  ...
+```
+
+Si usaste la opción `--zip`, también tendrás un archivo ZIP con todos los PDFs en la carpeta `output/`:
+
+```
+output/subsidios_pdfs.zip
+```

---

## ¿Problemas o dudas?

Pide ayuda a soporte o al área técnica. Solo necesitas copiar tus archivos en las carpetas correctas y ejecutar el comando.
