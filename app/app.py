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
    flask_app_instance = Flask(__name__, instance_relative_config=True)

    # --- Configuración de la Aplicación ---
    # Configuración de SQLAlchemy
    # Construir la ruta a la carpeta 'instance' en la raíz del proyecto

    project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    instance_folder_path = os.path.join(project_root, 'instance')

    default_db_path = 'sqlite:///' + os.path.join(instance_folder_path, 'lol_smart_tracker.db')
    flask_app_instance.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or default_db_path
    flask_app_instance.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- Creación de Directorios Necesarios (como 'instance' para SQLite y 'flask_cache' para FileSystemCache) ---
    try:
        # Crear la carpeta 'instance' en la raíz del proyecto si no existe
        if not os.path.exists(instance_folder_path):
            os.makedirs(instance_folder_path)
        
        cache_dir_from_config = cache.config.get("CACHE_DIR") 
        if cache_dir_from_config:

            if cache_dir_from_config.startswith('instance') and not os.path.isabs(cache_dir_from_config):
                abs_cache_dir = os.path.join(project_root, cache_dir_from_config)
                if not os.path.exists(abs_cache_dir):
                    os.makedirs(abs_cache_dir)
    except OSError as e:
        pass 

    # --- Inicialización de Extensiones ---
    db.init_app(flask_app_instance)
    cache.init_app(flask_app_instance)

    # --- Registrar Blueprints ---
    flask_app_instance.register_blueprint(routes)

    # --- Crear Tablas de la Base de Datos (si no existen) ---
    with flask_app_instance.app_context():
        db.create_all()
    return flask_app_instance

application = create_app()

# Este bloque es para ejecutar la aplicación directamente con 'python -m app.app' para desarrollo local.
if __name__ == "__main__":
    application.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG", "1") == "1")