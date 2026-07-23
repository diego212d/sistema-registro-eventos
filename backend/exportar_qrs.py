import os
# Importamos la app, la base de datos y la clase Alumno desde app.py
from app import app, db, Alumno 


def exportar_todos_los_qrs():
    # Crea una carpeta llamada 'qrs_para_imprimir' si no existe
    carpeta_destino = 'qrs_para_imprimir'
    os.makedirs(carpeta_destino, exist_ok=True)

    with app.app_context():
        # Buscamos a los alumnos que ya tienen el QR guardado en la BD
        alumnos_con_qr = Alumno.query.filter(Alumno.qr_code.isnot(None)).all()

        if not alumnos_con_qr:
            print("⚠️ No hay alumnos con QR confirmado en la Base de Datos.")
            return

        for alumno in alumnos_con_qr:
            # Limpiamos el nombre para evitar problemas con espacios en el archivo
            nombre_limpio = alumno.Nombre.replace(' ', '_')
            nombre_archivo = f"QR_{alumno.idAlumno}_{nombre_limpio}.png"
            ruta_completa = os.path.join(carpeta_destino, nombre_archivo)

            # Escribimos los datos binarios directamente en un archivo .png
            with open(ruta_completa, 'wb') as f:
                f.write(alumno.qr_code)
            
            print(f"✅ Guardado: {ruta_completa}")

        print(f"\n🎉 ¡Listo! Se guardaron todos los QR en la carpeta: '{os.path.abspath(carpeta_destino)}'")

if __name__ == '__main__':
    exportar_todos_los_qrs()