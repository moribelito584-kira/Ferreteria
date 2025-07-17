# inventario_ferreteria/app.py

import os
from dotenv import load_dotenv
import sys
import webbrowser
import threading
import time
from waitress import serve
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import firebase_admin
from firebase_admin import credentials, firestore
from werkzeug.utils import secure_filename
import uuid
import datetime # ¡Importación necesaria para obtener el año actual!

# --- Cargar variables de entorno al inicio ---
load_dotenv()

# --- Configuración de la aplicación Flask ---
app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

if not app.config['SECRET_KEY']:
    print("ERROR: La variable de entorno 'FLASK_SECRET_KEY' no está configurada.")
    print("Por favor, crea un archivo .env en la raíz de tu proyecto con FLASK_SECRET_KEY='tu_clave_secreta_generada'.")
    exit(1)

# --- Inicialización de Firebase Admin SDK ---
SERVICE_ACCOUNT_KEY_FILENAME = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')

if not SERVICE_ACCOUNT_KEY_FILENAME:
    print("ERROR: La variable de entorno 'FIREBASE_SERVICE_ACCOUNT_PATH' no está configurada.")
    print("Por favor, crea un archivo .env en la raíz de tu proyecto con FIREBASE_SERVICE_ACCOUNT_PATH='nombre_de_tu_clave.json'.")
    exit(1)

# Determina la ruta base del entorno de ejecución (especialmente para PyInstaller)
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    APP_ROOT_DIR = os.path.dirname(sys.executable)
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    APP_ROOT_DIR = bundle_dir

SERVICE_ACCOUNT_KEY_FULL_PATH = os.path.join(bundle_dir, SERVICE_ACCOUNT_KEY_FILENAME)

load_dotenv(os.path.join(bundle_dir, '.env'), override=True)

if not os.path.exists(SERVICE_ACCOUNT_KEY_FULL_PATH):
    print(f"ERROR: No se encontró el archivo de clave de servicio de Firebase en '{SERVICE_ACCOUNT_KEY_FULL_PATH}'.")
    print("Asegúrate de que el nombre del archivo en .env sea correcto y esté en la misma carpeta que app.py.")
    exit(1)

try:
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_FULL_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    
    
    
    print("Firebase Admin SDK inicializado correctamente.")
except Exception as e:
    print(f"ERROR: No se pudo inicializar Firebase Admin SDK: {e}")
    print("Revisa tu archivo de clave de servicio JSON y tus permisos de proyecto en la Consola de Firebase.")
    exit(1)

# --- Procesador de contexto para variables globales en las plantillas ---
@app.context_processor
def inject_global_variables():
    """Inyecta variables que estarán disponibles en todas las plantillas."""
    return dict(current_year=datetime.datetime.now().year)

# --- Configuration for Local Image Storage ---
UPLOAD_FOLDER_NAME = 'product_images' # This is the subfolder name
UPLOAD_PATH = os.path.join(APP_ROOT_DIR, UPLOAD_FOLDER_NAME) # This is the full path to the images folder

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(UPLOAD_PATH):
    os.makedirs(UPLOAD_PATH)
    print(f"Directorio de subida creado: {UPLOAD_PATH}")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image_locally(file, product_id):
    if not file or not allowed_file(file.filename):
        return None

    original_filename = secure_filename(file.filename)
    unique_filename = f"{product_id}_{uuid.uuid4().hex[:8]}_{original_filename}"
    file_path = os.path.join(UPLOAD_PATH, unique_filename)

    try:
        file.save(file_path)
        return unique_filename
    except Exception as e:
        print(f"Error al guardar la imagen localmente: {e}")
        return None

# --- Ruta para servir imágenes locales subidas ---
@app.route(f'/{UPLOAD_FOLDER_NAME}/<path:filename>')
def serve_uploaded_image(filename):
    return send_from_directory(UPLOAD_PATH, filename)

# --- Rutas (Endpoints) de la Aplicación ---
@app.route('/')
def index():
    productos = []
    try:
        docs = db.collection('productos').stream()
        for doc in docs:
            producto_data = doc.to_dict()
            producto_data['id'] = doc.id
            productos.append(producto_data)
        productos.sort(key=lambda p: p.get('nombre', '').lower())
    except Exception as e:
        flash(f'Error al cargar productos: {e}', 'error')
    return render_template('index.html', productos=productos)

@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        nombre = request.form['nombre']
        stock_str = request.form['stock']
        precio_compra_str = request.form['precio_compra']
        precio_venta_str = request.form['precio_venta']
        categoria = request.form['categoria']

        try:
            stock = float(stock_str)
            precio_compra = float(precio_compra_str) if precio_compra_str else None
            precio_venta = float(precio_venta_str) if precio_venta_str else None
        except ValueError:
            flash('Error: El stock, precio de compra o precio de venta deben ser números válidos.', 'error')
            return render_template('add_product.html', product=request.form)

        codigo = str(uuid.uuid4())[:8]

        try:
            nuevo_producto_data = {
                'nombre': nombre,
                'codigo': codigo,
                'stock': stock,
                'unidad': '',
                'precio_compra': precio_compra,
                'precio_venta': precio_venta,
                'categoria': categoria,
                'imagen_filename': ''
            }

            doc_ref = db.collection('productos').add(nuevo_producto_data)
            product_id = doc_ref[1].id

            file = request.files.get('imagen')
            if file:
                image_filename = save_image_locally(file, product_id)
                if image_filename:
                    db.collection('productos').document(product_id).update({'imagen_filename': image_filename})
                    flash('Producto añadido y imagen subida correctamente!', 'success')
                else:
                    flash('Producto añadido, pero hubo un error al subir la imagen.', 'warning')
            else:
                flash('Producto añadido correctamente!', 'success')

            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error al añadir producto: {e}', 'error')
            return render_template('add_product.html', product=request.form)

    return render_template('add_product.html')

@app.route('/edit/<string:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    producto_ref = db.collection('productos').document(product_id)
    producto_doc = producto_ref.get()

    if not producto_doc.exists:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('index'))

    current_product_data = producto_doc.to_dict()

    if request.method == 'POST':
        nombre = request.form['nombre']
        codigo = request.form['codigo']
        stock_str = request.form['stock']
        unidad = request.form.get('unidad', '')
        precio_compra_str = request.form['precio_compra']
        precio_venta_str = request.form['precio_venta']
        categoria = request.form['categoria']

        try:
            stock = float(stock_str)
            precio_compra = float(precio_compra_str) if precio_compra_str else None
            precio_venta = float(precio_venta_str) if precio_venta_str else None
        except ValueError:
            flash('Error: El stock, precio de compra o precio de venta deben ser números válidos.', 'error')
            return render_template('edit_product.html', product=request.form, product_id=product_id)

        original_codigo = current_product_data.get('codigo')
        if codigo != original_codigo:
            producto_existente_con_nuevo_codigo = db.collection('productos').where('codigo', '==', codigo).limit(1).get()
            if len(producto_existente_con_nuevo_codigo) > 0:
                flash('Error: El código de producto ya existe en otro producto. Por favor, usa uno diferente.', 'error')
                return render_template('edit_product.html', product=request.form, product_id=product_id)

        file = request.files.get('imagen')
        image_filename = current_product_data.get('imagen_filename', '')

        if file:
            new_image_filename = save_image_locally(file, product_id)
            if new_image_filename:
                image_filename = new_image_filename
                flash('Nueva imagen subida correctamente.', 'info')
            else:
                flash('Hubo un error al subir la nueva imagen.', 'warning')

        try:
            updated_data = {
                'nombre': nombre,
                'codigo': codigo,
                'stock': stock,
                'unidad': unidad,
                'precio_compra': precio_compra,
                'precio_venta': precio_venta,
                'categoria': categoria,
                'imagen_filename': image_filename
            }
            producto_ref.update(updated_data)
            flash('Producto actualizado correctamente!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error al actualizar producto: {e}', 'error')
            return render_template('edit_product.html', product=request.form, product_id=product_id)

    return render_template('edit_product.html', product=current_product_data, product_id=product_id)

@app.route('/delete/<string:product_id>', methods=['POST'])
def delete_product(product_id):
    try:
        product_doc = db.collection('productos').document(product_id).get()
        if product_doc.exists:
            image_filename = product_doc.to_dict().get('imagen_filename')
            if image_filename:
                file_path_to_delete = os.path.join(UPLOAD_PATH, image_filename)
                if os.path.exists(file_path_to_delete):
                    os.remove(file_path_to_delete)
                    print(f"Imagen local eliminada: {file_path_to_delete}")

        db.collection('productos').document(product_id).delete()
        flash('Producto eliminado correctamente!', 'success')
    except Exception as e:
        flash(f'Error al eliminar producto: {e}', 'error')
    return redirect(url_for('index'))

@app.route('/increase_stock/<string:product_id>', methods=['POST'])
def increase_stock(product_id):
    producto_ref = db.collection('productos').document(product_id)
    producto_doc = producto_ref.get()

    if not producto_doc.exists:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('index'))

    try:
        cantidad = float(request.form['cantidad'])
        if cantidad <= 0:
            flash('La cantidad a aumentar debe ser un número positivo.', 'error')
            return redirect(url_for('index'))

        current_stock = producto_doc.to_dict().get('stock', 0.0)
        new_stock = current_stock + cantidad
        producto_ref.update({'stock': new_stock})
        flash(f'Stock de {producto_doc.to_dict()["nombre"]} aumentado en {cantidad}. Nuevo stock: {new_stock}', 'info')
    except ValueError:
        flash('La cantidad debe ser un número válido.', 'error')
    except Exception as e:
        flash(f'Error al aumentar stock: {e}', 'error')
    return redirect(url_for('index'))

@app.route('/decrease_stock/<string:product_id>', methods=['POST'])
def decrease_stock(product_id):
    producto_ref = db.collection('productos').document(product_id)
    producto_doc = producto_ref.get()

    if not producto_doc.exists:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('index'))

    try:
        cantidad = float(request.form['cantidad'])
        if cantidad <= 0:
            flash('La cantidad a disminuir debe ser un número positivo.', 'error')
            return redirect(url_for('index'))

        current_stock = producto_doc.to_dict().get('stock', 0.0)
        if current_stock >= cantidad:
            new_stock = current_stock - cantidad
            producto_ref.update({'stock': new_stock})
            flash(f'Stock de {producto_doc.to_dict()["nombre"]} disminuido en {cantidad}. Nuevo stock: {new_stock}', 'info')
        else:
            flash(f'No hay suficiente stock de {producto_doc.to_dict()["nombre"]}. Stock actual: {current_stock}', 'warning')
    except ValueError:
        flash('La cantidad debe ser un número válido.', 'error')
    except Exception as e:
        flash(f'Error al disminuir stock: {e}', 'error')
    return redirect(url_for('index'))

# --- Ejecución de la aplicación ---
if __name__ == '__main__':
    HOST = '127.0.0.1'
    PORT = 5000
    app_url = f"http://{HOST}:{PORT}/"

    def open_browser():
        time.sleep(1)
        webbrowser.open_new_tab(app_url)

    threading.Thread(target=serve, kwargs={'app': app, 'host': HOST, 'port': PORT}).start()
    open_browser()