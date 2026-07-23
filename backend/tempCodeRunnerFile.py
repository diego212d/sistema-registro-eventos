from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__, template_folder='../frontend', static_folder='../css')

# Configuración de PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgresql:diego@127.0.0.1:5432/bd_pruebas'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Alumno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)



user_db=[]

@app.route('/alumnos')
def alumnos():
    alumnos = Alumno.query.all()
    return render_template('alumnos.html', user_db=alumnos)

@app.route('/registro_alumno', methods=['POST'])
def registro():
        nombre = request.form['nombre']
        email = request.form['email']
        nuevo = Alumno(nombre=nombre, email=email)
        db.session.add(nuevo)
        db.session.commit()
        return redirect(url_for('alumnos'))

@app.route('/empresarios')
def empresarios():
    return render_template('empresarios.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



