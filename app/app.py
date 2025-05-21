# app/app.py
import os
from flask import Flask
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env al inicio de la aplicación
load_dotenv() 

from .routes import routes
from .extensions import cache, db
from . import models

def create_app():
    """
    Factory function para crear y configurar la aplicación Flask.
    """
    app = Flask(__name__, instance_relative_config=True)
    
    # Configuración de SQLAlchemy
    project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    instance_folder_path = os.path.join(project_root, 'instance')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
                                           'sqlite:///' + os.path.join(instance_folder_path, 'lol_smart_tracker.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    print(f"DEBUG (Flask App): Usando BD en: {app.config['SQLALCHEMY_DATABASE_URI']}") # DEBUG

    # --- Creación de Directorios Necesarios ---
    try:
        # Crear la carpeta 'instance' en la raíz del proyecto si no existe
        if not os.path.exists(instance_folder_path):
            os.makedirs(instance_folder_path)
            app.logger.info(f"Directorio de instancia creado en: {instance_folder_path}")

        # Si usas FileSystemCache y CACHE_DIR está configurado a 'instance/flask_cache'
        # Flask-Caching usualmente crea el directorio si no existe, pero esto es una doble verificación.
        cache_dir_from_config = cache.config.get("CACHE_DIR") # Obtener de la instancia de Cache
        if cache_dir_from_config and cache_dir_from_config.startswith('instance') and not os.path.isabs(cache_dir_from_config):
            # Construir path absoluto para CACHE_DIR si es relativo a 'instance'
            abs_cache_dir = os.path.join(project_root, cache_dir_from_config)
            if not os.path.exists(abs_cache_dir):
                os.makedirs(abs_cache_dir)
                app.logger.info(f"Directorio de caché creado en: {abs_cache_dir}")

    except OSError as e:
        app.logger.warning(f"No se pudo crear el directorio de instancia o caché: {e}")
        pass 

    # --- Inicialización de Extensiones ---
    db.init_app(app)    # Inicializar SQLAlchemy con la aplicación
    cache.init_app(app) 

    # --- Registrar Blueprints ---
    app.register_blueprint(routes)

    # --- Crear Tablas de la Base de Datos (si no existen) ---
    with app.app_context():
        print("DEBUG (Flask App): Intentando crear tablas de la base de datos (db.create_all())...")
        db.create_all()
        print("DEBUG (Flask App): Tablas de la base de datos verificadas/creadas.")

    return app

if __name__ == "__main__":
    current_app = create_app()
    current_app.run(host='0.0.0.0', port=5000, debug=True)