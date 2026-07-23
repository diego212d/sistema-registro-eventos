import os
import io
import re
import threading
import subprocess
import qrcode 

from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__, template_folder='../frontend', static_folder='../css')

# Configuración de Clave Secreta y Base de Datos
app.config['SECRET_KEY'] = 'rpxf ddbn cdbl otez'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:diego@127.0.0.1:5432/bd_pruebas'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración de Flask-Mail para Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'rjdjs2715@gmail.com'
app.config['MAIL_PASSWORD'] = 'rpxf ddbn cdbl otez'
app.config['MAIL_DEFAULT_SENDER'] = 'rjdjs2715@gmail.com'

mail = Mail(app)
db = SQLAlchemy(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])


# ==========================================
# MODELOS DE BASE DE DATOS
# ==========================================

class Alumno(db.Model):
    __tablename__ = 'Registro_Alumnos'
    __table_args__ = {'schema': 'public'}

    idAlumno = db.Column('idAlumno', db.Integer, primary_key=True)
    Nombre = db.Column('Nombre', db.String(50), nullable=False)
    Correo = db.Column('Correo', ARRAY(db.String(50)), nullable=False)
    confirmado = db.Column('confirmado', db.Boolean, default=False)
    qr_code = db.Column('qr_code', db.LargeBinary, nullable=True)
    asistencias = db.Column(db.Integer, default=0)      


class Empresario(db.Model):
    __tablename__ = 'Registro_Empresarios'
    __table_args__ = {'schema': 'public'}

    idEmpresario = db.Column('idEmpresario', db.Integer, primary_key=True)
    Nombre = db.Column('Nombre', db.String(100), nullable=False)
    ApellidoPaterno = db.Column('ApellidoPaterno', db.String(100), nullable=False)
    ApellidoMaterno = db.Column('ApellidoMaterno', db.String(100), nullable=True)
    Cargo = db.Column('Cargo', db.String(100), nullable=True)
    Empresa = db.Column('Empresa', db.String(150), nullable=False)
    LadaPais = db.Column('LadaPais', db.String(10), nullable=True)
    Telefono = db.Column('Telefono', db.String(20), nullable=False)
    Pais = db.Column('Pais', db.String(50), nullable=False)
    CodigoPostal = db.Column('CodigoPostal', db.String(20), nullable=False)
    Ciudad = db.Column('Ciudad', db.String(100), nullable=False)
    CalleNumero = db.Column('CalleNumero', db.String(150), nullable=True)
    Correo = db.Column('Correo', db.String(150), nullable=False, unique=True)
    
    # Datos del perfil empresarial / encuesta
    PosicionEmpresa = db.Column('PosicionEmpresa', db.String(150), nullable=True)
    AreaResponsabilidad = db.Column('AreaResponsabilidad', db.String(150), nullable=True)
    SectorIndustria = db.Column('SectorIndustria', ARRAY(db.String(100)), nullable=True)
    NumEmpleados = db.Column('NumEmpleados', db.String(50), nullable=True)
    DecisionesCompra = db.Column('DecisionesCompra', db.String(100), nullable=True)
    Presupuesto = db.Column('Presupuesto', db.String(100), nullable=True)
    TiempoInversion = db.Column('TiempoInversion', db.String(100), nullable=True)
    ProductosInteres = db.Column('ProductosInteres', ARRAY(db.String(100)), nullable=True)

    confirmado = db.Column('confirmado', db.Boolean, default=False)
    qr_code = db.Column('qr_code', db.LargeBinary, nullable=True)
    asistencias = db.Column(db.Integer, default=0)


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def es_correo_valido(correo):
    """ Valida si la cadena tiene un formato de correo electrónico correcto """
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, correo) is not None


def generar_bytes_qr(contenido):
    """ Genera solo el QR binario para la base de datos """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(str(contenido))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def crear_diseno_gafete(bytes_qr, id_usuario, nombre_usuario):
    """ Crea un ticket adaptado para rollo térmico de 62mm con texto auto-ajustable """
    
    ANCHO, ALTO = 600, 900
    gafete = Image.new('RGB', (ANCHO, ALTO), 'white')
    draw = ImageDraw.Draw(gafete)

    # 1. Cargar Logo
    ruta_logo = "backend/logo-nexara-lockup.png"
    if os.path.exists(ruta_logo):
        try:
            logo = Image.open(ruta_logo)
            logo_ancho, logo_alto = 300, 300
            logo = logo.resize((logo_ancho, logo_alto))
            pos_logo_x = (ANCHO - logo_ancho) // 2
            pos_logo_y = 30

            if logo.mode == 'RGBA':
                gafete.paste(logo, (pos_logo_x, pos_logo_y), logo)
            else:
                gafete.paste(logo.convert('RGB'), (pos_logo_x, pos_logo_y))
        except Exception as err_img:
            print(f"⚠️ Error cargando logo: {err_img}")

    # 2. Cargar Fuentes
    try:
        fnt_titulo = ImageFont.truetype("arial.ttf", 32)
        fnt_texto = ImageFont.truetype("arial.ttf", 26)
    except:
        fnt_titulo = ImageFont.load_default()
        fnt_texto = ImageFont.load_default()

    # 3. Dibujar Encabezado y Folio
    draw.text((30, 350), "BALLETE ELISA CARRILLO ", fill="black", font=fnt_titulo)
    draw.text((30, 400), f"Folio: {id_usuario}", fill="black", font=fnt_texto)

    # 4. Manejo Inteligente del Nombre Completo (Salto de línea si es largo)
    if len(nombre_usuario) > 22:
        partes = nombre_usuario.split(' ')
        mitad = len(partes) // 2
        linea1 = " ".join(partes[:mitad])
        linea2 = " ".join(partes[mitad:])
        
        draw.text((30, 440), f"Nombre: {linea1}", fill="black", font=fnt_texto)
        draw.text((30, 475), f"        {linea2}", fill="black", font=fnt_texto)
    else:
        draw.text((30, 440), f"Nombre: {nombre_usuario}", fill="black", font=fnt_texto)

    # 5. Código QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(str(id_usuario))
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    qr_ancho, qr_alto = qr_img.size
    pos_qr_x = (ANCHO - qr_ancho) // 2
    pos_qr_y = 530
    
    gafete.paste(qr_img, (pos_qr_x, pos_qr_y))
    draw.text((pos_qr_x + 10, pos_qr_y + qr_alto + 15), "", fill="black", font=fnt_texto)

    buffer_gafete = io.BytesIO()
    gafete.save(buffer_gafete, format="PNG")
    return buffer_gafete.getvalue()


def _imprimir_proceso(bytes_qr, id_usuario, nombre_usuario):
    """ Impresión silenciosa mediante PowerShell """
    try:
        bytes_diseno_final = crear_diseno_gafete(bytes_qr, id_usuario, nombre_usuario)

        carpeta_temp = os.path.abspath("temp_print")
        os.makedirs(carpeta_temp, exist_ok=True)
        nombre_limpio = nombre_usuario.replace(" ", "_")
        ruta_archivo = os.path.join(carpeta_temp, f"Ticket_{id_usuario}_{nombre_limpio}.png")

        with open(ruta_archivo, 'wb') as f:
            f.write(bytes_diseno_final)

        ps_script = f"""
        [System.Reflection.Assembly]::LoadWithPartialName("System.Drawing") | Out-Null
        [System.Reflection.Assembly]::LoadWithPartialName("System.Printing") | Out-Null

        $ImagePath = "{ruta_archivo.replace('\\', '/')}"
        $printDoc = New-Object System.Drawing.Printing.PrintDocument
        
        $printDoc.OriginAtMargins = $true
        $printDoc.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(0, 0, 0, 0)

        $printDoc.add_PrintPage({{
            param($sender, $e)
            $img = [System.Drawing.Image]::FromFile($ImagePath)
            $printableWidth = $e.PageBounds.Width
            $scale = $printableWidth / $img.Width
            $printableHeight = [int]($img.Height * $scale)

            $e.Graphics.DrawImage($img, 0, 0, $printableWidth, $printableHeight)
        }})

        $printDoc.Print()
        """

        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=True
        )

        print(f"✅ Ticket impreso con éxito para {nombre_usuario}")

    except Exception as e:
        print(f"❌ Error al intentar imprimir: {e}")


def imprimir_qr_en_segundo_plano(bytes_qr, id_usuario, nombre_usuario):
    """ Lanza el proceso de impresión en un hilo secundario """
    hilo = threading.Thread(
        target=_imprimir_proceso,
        args=(bytes_qr, id_usuario, nombre_usuario)
    )
    hilo.start()


# ==========================================
# RUTAS DE FLASK
# ==========================================

@app.route('/')
def alumnos():
    alumnos = Alumno.query.all()
    return render_template('alumnos.html', user_db=alumnos)


@app.route('/empresarios')
def empresarios():
    return render_template('empresarios.html')


@app.route('/registro_alumno', methods=['POST'])
def registro():
    try:
        Nombre = request.form['nombre']
        Correo = request.form['email']

        # Verificar si el correo ya está registrado en alumnos
        alumno_existente = Alumno.query.filter(Alumno.Correo.any(Correo)).first()
        if alumno_existente:
            return """
            <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 60px auto; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; background-color: #ffffff;">
                <div style="font-size: 48px; margin-bottom: 15px;">⚠️</div>
                <h2 style="color: #e74c3c; margin-bottom: 15px; font-size: 22px;">Correo ya registrado</h2>
                <p style="color: #666; font-size: 15px; margin-bottom: 25px;">Este correo electrónico ya se encuentra registrado. Revisa tu bandeja de entrada para confirmar tu registro.</p>
                <a href="/" style="display: inline-block; padding: 12px 24px; background-color: #3498db; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold;">Volver al inicio</a>
            </div>
            """, 400

        nuevo = Alumno(Nombre=Nombre, Correo=[Correo], confirmado=False)
        db.session.add(nuevo)
        db.session.commit()
        print("✅ Alumno guardado en la Base de Datos con éxito")

        token_url = serializer.dumps(Correo, salt='email-confirm-salt')
        url_confirmacion = url_for('confirmar_email', token=token_url, _external=True)

        msg = Message(
            subject="Confirma tu registro de alumno",
            recipients=[Correo]
        )
        msg.html = f"""
            <h3>¡Hola {Nombre}!</h3>
            <p>Gracias por registrarte. Haz clic en el enlace para activar tu cuenta:</p>
            <p>
                <a href="{url_confirmacion}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Aceptar y Confirmar Registro
                </a>
            </p>
        """
        
        mail.send(msg)
        print("✅ Correo enviado con éxito desde Gmail")

        return """
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 60px auto; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; background-color: #ffffff;">
            <div style="font-size: 48px; margin-bottom: 15px;">✉️</div>
            <h2 style="color: #2c3e50; margin-bottom: 15px; font-size: 22px;">Te hemos enviado un correo de confirmación.</h2>
            <p style="color: #666; font-size: 15px; margin-bottom: 25px;">Por favor revisa tu bandeja de entrada (y la carpeta de spam por si acaso).</p>
            <a href="/" style="display: inline-block; padding: 12px 24px; background-color: #3498db; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold;">Volver al inicio</a>
        </div>
        """

    except Exception as e:
        print(f"❌ ERROR CRÍTICO EN REGISTRO: {e}")
        db.session.rollback()
        return f"<h1>Ocurrió un error: {e}</h1>", 500


@app.route('/confirmar/<token>')
def confirmar_email(token):
    try:
        correo_validado = serializer.loads(token, salt='email-confirm-salt', max_age=3600)
    except SignatureExpired:
        return '<h1>El enlace ha expirado. Realiza el registro de nuevo.</h1>'
    except BadTimeSignature:
        return '<h1>El enlace de confirmación no es válido.</h1>'

    alumno = Alumno.query.filter(Alumno.Correo.any(correo_validado)).first()

    if alumno:
        if alumno.confirmado:
            return """
            <div style="display: flex; justify-content: center; align-items: center; min-height: 100vh; background-color: #f4f6f9; margin: 0; padding: 20px; box-sizing: border-box; font-family: Arial, sans-serif;">
                <div style="width: 100%; max-width: 450px; padding: 40px 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: center; background-color: #ffffff;">
                    <div style="font-size: 52px; margin-bottom: 20px;">ℹ️</div>
                    <h2 style="color: #2c3e50; margin: 0 0 25px 0; font-size: 22px; line-height: 1.4;">Tu cuenta ya había sido confirmada previamente.</h2>
                </div>
            </div>
            """
        
        alumno.confirmado = True
        qr_bytes = generar_bytes_qr(alumno.idAlumno)
        alumno.qr_code = qr_bytes

        imprimir_qr_en_segundo_plano(qr_bytes, alumno.idAlumno, alumno.Nombre)

        db.session.commit()
        return redirect(url_for('alumnos'))

    return "<h1>Alumno no encontrado.</h1>"


@app.route('/registro_empresario', methods=['POST'])
def registro_empresario():
    try:
        email = request.form.get('email', '').strip()

        if not email or not es_correo_valido(email):
            return "<h1>Correo electrónico no válido.</h1>", 400

        # 🔍 VERIFICAR SI EL CORREO YA EXISTE EN LA BASE DE DATOS
        empresario_existente = Empresario.query.filter_by(Correo=email).first()
        if empresario_existente:
            return """
            <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 60px auto; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; background-color: #ffffff;">
                <div style="font-size: 48px; margin-bottom: 15px;">⚠️</div>
                <h2 style="color: #e74c3c; margin-bottom: 15px; font-size: 22px;">Este correo ya está registrado</h2>
                <p style="color: #666; font-size: 15px; margin-bottom: 25px;">El correo electrónico ingresado ya se encuentra registrado en nuestro sistema. Por favor revisa tu correo para confirmar tu registro o utiliza un correo diferente.</p>
                <a href="/empresarios" style="display: inline-block; padding: 12px 24px; background-color: #0b2c70; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold;">Volver al formulario</a>
            </div>
            """, 400

        nombre = request.form.get('nombre', '').strip()
        apellido_paterno = request.form.get('apellido_paterno', '').strip()
        apellido_materno = request.form.get('apellido_materno', '').strip()
        cargo = request.form.get('cargo', '').strip()
        empresa = request.form.get('empresa', '').strip()
        lada_pais = request.form.get('lada_pais', '').strip()
        telefono = request.form.get('telefono', '').strip()
        pais = request.form.get('pais', '').strip()
        codigo_postal = request.form.get('codigo_postal', '').strip()
        ciudad = request.form.get('ciudad', '').strip()
        calle_numero = request.form.get('calle_numero', '').strip()

        posicion_empresa = request.form.get('posicion_empresa')
        area_responsabilidad = request.form.get('area_responsabilidad')
        sector_industria = request.form.getlist('sector_industria') 
        num_empleados = request.form.get('num_empleados')
        decisiones_compra = request.form.get('decisiones_compra')
        presupuesto = request.form.get('presupuesto')
        tiempo_inversion = request.form.get('tiempo_inversion')
        productos_interes = request.form.getlist('productos_interes')

        nuevo_empresario = Empresario(
            Nombre=nombre,
            ApellidoPaterno=apellido_paterno,
            ApellidoMaterno=apellido_materno,
            Cargo=cargo,
            Empresa=empresa,
            LadaPais=lada_pais,
            Telefono=telefono,
            Pais=pais,
            CodigoPostal=codigo_postal,
            Ciudad=ciudad,
            CalleNumero=calle_numero,
            Correo=email,
            PosicionEmpresa=posicion_empresa,
            AreaResponsabilidad=area_responsabilidad,
            SectorIndustria=sector_industria,
            NumEmpleados=num_empleados,
            DecisionesCompra=decisiones_compra,
            Presupuesto=presupuesto,
            TiempoInversion=tiempo_inversion,
            ProductosInteres=productos_interes,
            confirmado=False
        )

        db.session.add(nuevo_empresario)
        db.session.commit()

        payload = {'email': email, 'tipo': 'empresario'}
        token_url = serializer.dumps(payload, salt='email-confirm-salt')
        url_confirmacion = url_for('confirmar_email_generico', token=token_url, _external=True)

        msg = Message(
            subject="Confirmación de Registro - FESPA Mexico 2026",
            recipients=[email]
        )
        msg.html = f"""
            <h3>¡Hola {nombre} {apellido_paterno}!</h3>
            <p>Gracias por registrarte para el evento <strong>FESPA Mexico 2026</strong>.</p>
            <p>Para confirmar tu asistencia e imprimir tu gafete de acceso, haz clic en el siguiente enlace:</p>
            <p>
                <a href="{url_confirmacion}" style="background-color: #0b2c70; color: white; padding: 12px 22px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Confirmar mi Registro y Generar Gafete
                </a>
            </p>
        """
        mail.send(msg)

        return """
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 60px auto; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; background-color: #ffffff;">
            <div style="font-size: 48px; margin-bottom: 15px;">✉️</div>
            <h2 style="color: #0b2c70; margin-bottom: 15px; font-size: 22px;">¡Registro recibido con éxito!</h2>
            <p style="color: #666; font-size: 15px; margin-bottom: 25px;">Te hemos enviado un correo de confirmación a tu email. Por favor revísalo para activar tu acceso.</p>
            <a href="/empresarios" style="display: inline-block; padding: 12px 24px; background-color: #0b2c70; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold;">Volver al registro</a>
        </div>
        """

    except Exception as e:
        print(f"❌ ERROR EN REGISTRO DE EMPRESARIO: {e}")
        db.session.rollback()
        return f"<h1>Ocurrió un error al procesar tu registro: {e}</h1>", 500


@app.route('/confirmar_generico/<token>')
def confirmar_email_generico(token):
    try:
        data = serializer.loads(token, salt='email-confirm-salt', max_age=3600)
    except (SignatureExpired, BadTimeSignature):
        return '<h1>El enlace de confirmación ha expirado o no es válido.</h1>'

    if isinstance(data, dict):
        email = data.get('email')
        tipo = data.get('tipo')
    else:
        email = data
        tipo = 'alumno'

    if tipo == 'empresario':
        usuario = Empresario.query.filter_by(Correo=email).first()
        if usuario:
            ap_materno = f" {usuario.ApellidoMaterno}" if usuario.ApellidoMaterno else ""
            nombre_completo = f"{usuario.Nombre} {usuario.ApellidoPaterno}{ap_materno}".strip()
        else:
            nombre_completo = ""
    else:
        usuario = Alumno.query.filter(Alumno.Correo.any(email)).first()
        nombre_completo = usuario.Nombre if usuario else ""

    if usuario:
        if usuario.confirmado:
            return """
            <div style="display: flex; justify-content: center; align-items: center; min-height: 100vh; background-color: #f4f6f9; margin: 0; padding: 20px; box-sizing: border-box; font-family: Arial, sans-serif;">
                <div style="width: 100%; max-width: 450px; padding: 40px 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: center; background-color: #ffffff;">
                    <div style="font-size: 52px; margin-bottom: 20px;">ℹ️</div>
                    <h2 style="color: #2c3e50; margin: 0 0 25px 0; font-size: 22px; line-height: 1.4;">Tu cuenta ya había sido confirmada previamente.</h2>
                </div>
            </div>
            """
        
        usuario.confirmado = True
        
        id_registro = getattr(usuario, 'idEmpresario', getattr(usuario, 'idAlumno', 0))
        qr_bytes = generar_bytes_qr(id_registro)
        usuario.qr_code = qr_bytes

        imprimir_qr_en_segundo_plano(qr_bytes, id_registro, nombre_completo)

        db.session.commit()
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 60px auto; padding: 30px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            <h1 style="color: #27ae60;">¡Registro Confirmado!</h1>
            <p>Hola <strong>{nombre_completo}</strong>, tu gafete de acceso ha sido enviado a imprimir.</p>
        </div>
        """

    return "<h1>Usuario no encontrado.</h1>"

@app.route('/validar_qr', methods=['POST'])
def validar_qr():
    qr_data = request.form.get('qr_data', '').strip()
    
    # Supongamos que el QR contiene el id del Empresario o Alumno
    # Buscar si existe en Alumnos o Empresarios
    empresario = Empresario.query.get(qr_data) if qr_data.isdigit() else None
    
    if empresario:
        return f"<h1 style='color:green;'>ENTRADA PERMITIDA: {empresario.Nombre} {empresario.ApellidoPaterno}</h1><a href='/escanear'>Siguiente</a>"
    else:
        return "<h1 style='color:red;'>ACCESO DENEGADO / NO ENCONTRADO</h1><a href='/escanear'>Reintentar</a>"


@app.route('/escanear', methods=['GET', 'POST'])
def escanear():
    if request.method == 'POST':
        qr_data = request.form.get('qr_data', '').strip()
        modo = request.form.get('modo', 'entrada') # 'entrada' o 'salida'
        
        asistente = None
        tipo_usuario = ""
        
        if qr_data.isdigit():
            id_num = int(qr_data)
            asistente = Empresario.query.get(id_num)
            tipo_usuario = "Empresario"
            
            if not asistente:
                asistente = Alumno.query.get(id_num)
                tipo_usuario = "Alumno"

        # 1. Si NO existe el usuario
        if not asistente:
            return responder_escaneo(
                exito=False, 
                mensaje="❌ ACCESO DENEGADO", 
                detalles=f'El ID "{qr_data}" no se encuentra registrado.', 
                pitido="error"
            )

        nombre = f"{asistente.Nombre} {getattr(asistente, 'ApellidoPaterno', '')}".strip()
        asistencias_actuales = getattr(asistente, 'asistencias', 0) or 0

        # 2. Lógica para ENTRADA
        if modo == 'entrada':
            if asistencias_actuales >= 1:
                return responder_escaneo(
                    exito=False, 
                    mensaje="❌ LÍMITE ALCANZADO", 
                    detalles=f"{nombre} ya ingresó {asistencias_actuales}/1 veces.", 
                    pitido="error"
                )
            
            # Incrementar conteo
            asistente.asistencias = asistencias_actuales + 1
            db.session.commit()
            
            return responder_escaneo(
                exito=True, 
                mensaje="✅ ENTRADA REGISTRADA", 
                detalles=f"{nombre} ({tipo_usuario})<br><br><strong style='font-size:22px;'>Entradas: {asistente.asistencias}/1</strong>", 
                pitido="exito"
            )

        # 3. Lógica para SALIDA
        elif modo == 'salida':
            if asistencias_actuales <= 0:
                return responder_escaneo(
                    exito=False, 
                    mensaje="⚠️ SALIDA DENEGADA", 
                    detalles=f"{nombre} no registra entradas activas.", 
                    pitido="error"
                )
            
            # Decrementar conteo
            asistente.asistencias = asistencias_actuales - 1
            db.session.commit()
            
            return responder_escaneo(
                exito=True, 
                mensaje="🚪 SALIDA REGISTRADA", 
                detalles=f"{nombre} ({tipo_usuario})<br><br><strong style='font-size:22px;'>Entradas activas: {asistente.asistencias}/1</strong>", 
                pitido="exito"
            )

    # Vista GET (Formulario principal)
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Control de Acceso Zebra</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 15px; background: #f0f2f5; margin: 0; }
            .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); max-width: 400px; margin: auto; }
            .btn-modo { padding: 15px; font-size: 18px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; margin: 5px; width: 45%; }
            .modo-entrada { background-color: #28a745; color: white; }
            .modo-salida { background-color: #dc3545; color: white; }
            .inactivo { opacity: 0.3; }
            input[type="text"] { font-size: 22px; padding: 12px; width: 85%; border-radius: 8px; border: 2px solid #007bff; text-align: center; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="color:#0b2c70;">📷 Control de Acceso</h2>
            
            <div>
                <button id="btnEntrada" type="button" class="btn-modo modo-entrada" onclick="setModo('entrada')">🟢 ENTRADA</button>
                <button id="btnSalida" type="button" class="btn-modo modo-salida inactivo" onclick="setModo('salida')">🔴 SALIDA</button>
            </div>

            <form action="/escanear" method="POST" style="margin-top: 15px;">
                <input type="hidden" name="modo" id="input_modo" value="entrada">
                <input type="text" name="qr_data" id="qr_input" placeholder="Escanea con la TC21..." autofocus autocomplete="off">
            </form>
        </div>

        <script>
            function setModo(modo) {
                document.getElementById('input_modo').value = modo;
                if (modo === 'entrada') {
                    document.getElementById('btnEntrada').classList.remove('inactivo');
                    document.getElementById('btnSalida').classList.add('inactivo');
                } else {
                    document.getElementById('btnSalida').classList.remove('inactivo');
                    document.getElementById('btnEntrada').classList.add('inactivo');
                }
                document.getElementById('qr_input').focus();
            }

            const input = document.getElementById('qr_input');
            input.focus();
            document.addEventListener('click', () => input.focus());
        </script>
    </body>
    </html>
    """


def responder_escaneo(exito, mensaje, detalles, pitido):
    color_bg = "#d4edda" if exito else "#f8d7da"
    color_texto = "#155724" if exito else "#721c24"
    color_borde = "#c3e6cb" if exito else "#f5c6cb"

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resultado Escaneo</title>
    </head>
    <body style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background: #f0f2f5;">
        <div style="background-color: {color_bg}; color: {color_texto}; padding: 30px 20px; border-radius: 12px; border: 3px solid {color_borde}; max-width: 400px; margin: auto;">
            <h1 style="margin: 0; font-size: 28px;">{mensaje}</h1>
            <p style="font-size: 18px; margin-top: 15px;">{detalles}</p>
        </div>
        <br>
        <a href="/escanear" id="btnSiguiente" style="display: inline-block; padding: 18px 35px; background-color: #007bff; color: white; text-decoration: none; font-size: 22px; border-radius: 10px; font-weight: bold;">Escanear Siguiente</a>

        <script>
            // Sintetizador de audio Web Audio API
            function reproducirPitido() {{
                try {{
                    const AudioContext = window.AudioContext || window.webkitAudioContext;
                    const ctx = new AudioContext();
                    
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);

                    if ("{pitido}" === "exito") {{
                        // Bip corto y agudo (Éxito)
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(880, ctx.currentTime); // Nota A5
                        gain.gain.setValueAtTime(0.5, ctx.currentTime);
                        osc.start();
                        osc.stop(ctx.currentTime + 0.15);
                    }} else {{
                        // Doble pitido grave (Error/Denegado)
                        osc.type = 'sawtooth';
                        osc.frequency.setValueAtTime(150, ctx.currentTime);
                        gain.gain.setValueAtTime(0.8, ctx.currentTime);
                        
                        osc.start(ctx.currentTime);
                        osc.stop(ctx.currentTime + 0.25);

                        // Segundo tono de error
                        setTimeout(() => {{
                            const ctx2 = new AudioContext();
                            const osc2 = ctx2.createOscillator();
                            const gain2 = ctx2.createGain();
                            osc2.connect(gain2);
                            gain2.connect(ctx2.destination);
                            osc2.type = 'sawtooth';
                            osc2.frequency.setValueAtTime(120, ctx2.currentTime);
                            gain2.gain.setValueAtTime(0.8, ctx2.currentTime);
                            osc2.start();
                            osc2.stop(ctx2.currentTime + 0.3);
                        }}, 300);
                    }}
                }} catch(e) {{
                    console.log("Audio no soportado o bloqueado:", e);
                }}
            }}

            // Reproducir inmediatamente
            window.onload = function() {{
                reproducirPitido();
            }};
        </script>
    </body>
    </html>
    """
    # Generador de sonidos vía sintetizador Web Audio API (No requiere archivos .mp3)
    script_audio = """
    <script>
        function emitirSonido(tipo) {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);

            if (tipo === 'exito') {
                osc.frequency.setValueAtTime(800, ctx.currentTime);
                osc.type = 'sine';
                gain.gain.setValueAtTime(0.3, ctx.currentTime);
                osc.start();
                osc.stop(ctx.currentTime + 0.15);
            } else {
                // Pitido de Error (Grave y más largo)
                osc.frequency.setValueAtTime(180, ctx.currentTime);
                osc.type = 'sawtooth';
                gain.gain.setValueAtTime(0.5, ctx.currentTime);
                osc.start();
                osc.stop(ctx.currentTime + 0.5);
            }
        }
        window.onload = function() {
            emitirSonido('""" + pitido + """');
        };
    </script>
    """

    color_bg = "#d4edda" if exito else "#f8d7da"
    color_texto = "#155724" if exito else "#721c24"
    color_borde = "#c3e6cb" if exito else "#f5c6cb"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resultado Escaneo</title>
        {script_audio}
    </head>
    <body style="font-family: Arial; text-align: center; padding: 20px; background: #f0f2f5;">
        <div style="background-color: {color_bg}; color: {color_texto}; padding: 30px 20px; border-radius: 12px; border: 2px solid {color_borde}; max-width: 400px; margin: auto;">
            <h1 style="margin: 0; font-size: 26px;">{mensaje}</h1>
            <p style="font-size: 18px; margin-top: 15px;">{detalles}</p>
        </div>
        <br>
        <a href="/escanear" style="display: inline-block; padding: 15px 30px; background-color: #007bff; color: white; text-decoration: none; font-size: 20px; border-radius: 8px; font-weight: bold;">Siguiente Escaneo</a>
    </body>
    </html>
    """
    # Si la Zebra (o el navegador) manda un código por POST:
    if request.method == 'POST':
        qr_data = request.form.get('qr_data', '').strip()
        
        # Buscar en Alumno o Empresario
        asistente = None
        tipo_usuario = ""
        
        if qr_data.isdigit():
            id_num = int(qr_data)
            asistente = Empresario.query.get(id_num)
            tipo_usuario = "Empresario"
            
            if not asistente:
                asistente = Alumno.query.get(id_num)
                tipo_usuario = "Alumno"

        if asistente:
            nombre = f"{asistente.Nombre} {getattr(asistente, 'ApellidoPaterno', '')}".strip()
            return f"""
            <div style="font-family: Arial; text-align: center; padding: 40px; max-width: 500px; margin: auto;">
                <div style="background-color: #d4edda; color: #155724; padding: 20px; border-radius: 10px; border: 2px solid #c3e6cb;">
                    <h1 style="margin: 0; font-size: 32px;">✅ ACCESO PERMITIDO</h1>
                    <h2 style="color: #333; margin-top: 15px;">{nombre}</h2>
                    <p style="font-size: 18px; color: #555;">Tipo: <strong>{tipo_usuario}</strong> | ID: <strong>{qr_data}</strong></p>
                </div>
                <br>
                <a href="/escanear" style="display: inline-block; padding: 15px 30px; background-color: #007bff; color: white; text-decoration: none; font-size: 20px; border-radius: 8px; font-weight: bold;">Escanear Siguiente</a>
            </div>
            """
        else:
            return f"""
            <div style="font-family: Arial; text-align: center; padding: 40px; max-width: 500px; margin: auto;">
                <div style="background-color: #f8d7da; color: #721c24; padding: 20px; border-radius: 10px; border: 2px solid #f5c6cb;">
                    <h1 style="margin: 0; font-size: 32px;">❌ ACCESO DENEGADO</h1>
                    <p style="font-size: 18px; color: #555;">El ID <strong>"{qr_data}"</strong> no se encuentra en la base de datos.</p>
                </div>
                <br>
                <a href="/escanear" style="display: inline-block; padding: 15px 30px; background-color: #dc3545; color: white; text-decoration: none; font-size: 20px; border-radius: 8px; font-weight: bold;">Reintentar</a>
            </div>
            """

    # Si entras a la URL desde el navegador (GET), muestra la pantalla del escáner:
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Control de Acceso Zebra</title>
    </head>
    <body style="font-family: Arial; text-align: center; padding: 20px; background-color: #f4f6f9;">
        <h2 style="color: #0b2c70;">📷 Control de Acceso Zebra</h2>
        <p style="color: #666;">Apunta con la TC21 y presiona el botón de escaneo</p>
        
        <form action="/escanear" method="POST" style="margin-top: 30px;">
            <input type="text" name="qr_data" id="qr_input" placeholder="Listo para escanear..." autofocus autocomplete="off" style="font-size: 20px; padding: 15px; width: 80%; border-radius: 8px; border: 2px solid #0b2c70; text-align: center;">
        </form>

        <script>
            // Asegura que el cuadro de texto nunca pierda el foco
            const input = document.getElementById('qr_input');
            input.focus();
            document.addEventListener('click', () => input.focus());
        </script>
    </body>
    </html>
    """
# ==========================================
# PUNTO DE ENTRADA
# ==========================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)