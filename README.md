&lt;h1 align="center">LoL Smart Tracker&lt;/h1>
&lt;p align="center">
&lt;img src="app/static/img/logoLolTracker.png" alt="LoL Smart Tracker Logo" width="150"/>
&lt;/p>
&lt;p align="center">
&lt;strong>Analiza tus partidas de League of Legends y recibe recomendaciones de IA para mejorar tu juego.&lt;/strong>
&lt;br />
&lt;a href="#%EF%B8%8F-acerca-del-proyecto">Acerca del Proyecto&lt;/a> •
&lt;a href="#-características">Características&lt;/a> •
&lt;a href="#-tecnologías-utilizadas">Tecnologías&lt;/a> •
&lt;a href="#-cómo-empezar">Cómo Empezar&lt;/a> •
&lt;a href="#-futuras-mejoras">Futuras Mejoras&lt;/a> •
&lt;a href="#-contacto">Contacto&lt;/a>
&lt;/p>

&lt;div align="center">

Hola 👋, Soy Erik Santana Montelongo, Backend Developer y creador de este proyecto.

&lt;/div>

🔭 Acerca del Proyecto
LoL Smart Tracker es una aplicación web diseñada para ayudar a los jugadores de League of Legends a visualizar su rendimiento reciente y, lo más importante, recibir recomendaciones personalizadas y análisis inteligentes generados por IA para mejorar su desempeño en el juego. 

A diferencia de otros trackers que se centran en mostrar estadísticas simples, LoL Smart Tracker busca:

Interpretar tus estadísticas con lógica e inteligencia. 
Detectar patrones en tu juego, como campeones con bajo rendimiento, fallos comunes, o baja participación en objetivos. 
Sugerir cambios adaptativos para mejorar tu estrategia general. 
El sistema obtiene automáticamente las últimas partidas del usuario a través de la API oficial de Riot Games y aplica diferentes técnicas de IA, desde análisis estadísticos avanzados hasta modelos de Machine Learning, para generar sugerencias y perspectivas únicas. 

Este proyecto es una evolución en las herramientas de análisis de LoL, buscando ser una herramienta proactiva que realmente ayude a los jugadores a mejorar, ofreciendo información útil más allá de simples números. 

(Este proyecto fue originalmente mi Trabajo Final de Grado, y ha sido expandido y mejorado continuamente.)

✨ Características
Visualización de Historial de Partidas: Muestra un resumen de tus últimas partidas (hasta 20), incluyendo KDA, CS, oro, daño, objetos, hechizos, y más.
Análisis del Invocador: Presenta información de tu perfil, incluyendo nivel y rango en Solo/Duo.
Recomendaciones Inteligentes (IA - Nivel 1):
Análisis de winrate general y rachas de derrotas.
Evaluación del rendimiento con campeones específicos (KDA y winrate).
Análisis de CS/minuto según el rol.
Evaluación de la participación en asesinatos (KP%).
Análisis de la puntuación de visión por minuto.
Identificación de métricas clave que se correlacionan con tus victorias/derrotas para campeones específicos.
Perspectivas Clave por Campeón (IA - Árbol de Decisión):
Un modelo de Machine Learning simple analiza tus partidas con tus campeones más jugados para identificar qué estadística personal (ej. CS/min, KDA Ratio) parece ser el factor más influyente para tus victorias.
Análisis de Estilos de Juego (IA - Clustering K-Means):
Un modelo de clustering agrupa tus partidas recientes en diferentes estilos de juego, ayudándote a entender tus tendencias.
Predicción de Composición de Equipo (IA - RandomForest):
Un modelo entrenado con datos de composiciones de equipo ofrece una estimación de la probabilidad de victoria para el equipo azul en cada partida de tu historial, basado únicamente en los campeones seleccionados.
Muestra los campeones que el modelo global considera más influyentes.
Búsqueda Integrada: Busca cualquier invocador por su Riot ID#TAG directamente desde la página de resultados.
Almacenamiento de Datos: Guarda los datos de las partidas procesadas en una base de datos SQLite local para permitir análisis más profundos y el reentrenamiento de modelos de ML a medida que se recopilan más datos.
Optimización con Caché: Utiliza Flask-Caching para reducir las llamadas a la API de Riot y mejorar los tiempos de carga en búsquedas repetidas.
🛠️ Tecnologías Utilizadas
Este proyecto se ha construido utilizando las siguientes tecnologías principales:

Backend:
Python
Flask (Framework web)
Flask-SQLAlchemy (ORM para la base de datos)
Flask-Caching (Sistema de caché)
Frontend:
HTML5
CSS3 (con Tailwind CSS para estilos rápidos y Bootstrap para algunos componentes)
JavaScript (mínimo, principalmente para funcionalidades de Bootstrap si se usan)
Machine Learning:
Pandas (Manipulación de datos)
NumPy (Cálculo numérico)
Scikit-learn (Modelos de ML: Árbol de Decisión, K-Means, RandomForest)
Base de Datos:
SQLite
API:
Riot Games API (para obtener datos de League of Legends)
Otros:
Requests (para hacer llamadas HTTP)
python-dotenv (para manejar variables de entorno)
Joblib (para guardar y cargar modelos de ML)
🚀 Cómo Empezar
Sigue estos pasos para poner en marcha el proyecto en tu entorno local.

Prerrequisitos
Python 3.8 o superior
pip (manejador de paquetes de Python)
Una clave de API de Riot Games válida (obtenida desde Riot Developer Portal)
Instalación
Clona el repositorio (o descarga el código):

Bash

git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
cd TU_REPOSITORIO
Crea y Activa un Entorno Virtual (Recomendado):

Bash

python -m venv venv
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate
Instala las Dependencias:

Bash

pip install -r requirements.txt
Configura tus Variables de Entorno:

Crea un archivo llamado .env en la raíz del proyecto.
Añade tu clave de API de Riot y otras configuraciones si es necesario:
Fragmento de código

RIOT_API_KEY="RGAPI-TU_CLAVE_AQUI"
# Opcional: puedes configurar las regiones por defecto si no son euw1/europe
# RIOT_ACCOUNT_REGION="europe"
# RIOT_PLATFORM_REGION="euw1"
# Opcional: para configurar el número de partidas para la IA desde el .env
# MATCH_COUNT_FOR_AI=30 
# MIN_GAMES_FOR_CHAMP_ML=10
# MIN_GAMES_FOR_CLUSTERING_ML=15
# NUM_CLUSTERS_PLAYSTYLE=3
Inicializa la Base de Datos y Entrena el Modelo (Primera Vez):

Ejecuta la aplicación Flask una vez para crear la base de datos y las tablas:
Bash

python -m app.app 
# O python run.py si tienes un script de lanzamiento
(Puedes detenerla con Ctrl+C después de que se inicie y cree la BD).
Para poblar la base de datos, usa la aplicación web para buscar algunos jugadores.
Una vez que tengas datos en la BD (después de buscar varios jugadores), ejecuta el script de entrenamiento:
Bash

python train_composition_model.py
Esto creará los archivos team_composition_predictor.joblib y team_composition_features.joblib.
Ejecuta la Aplicación Flask:

Bash

python -m app.app 
# O python run.py
Abre tu navegador y ve a http://127.0.0.1:5000/ (o la URL que muestre tu consola).

🔮 Futuras Mejoras
Este proyecto tiene mucho potencial para crecer. Algunas ideas basadas en la propuesta original y lo que hemos construido: ()

Mejorar Precisión de Modelos de ML: A medida que se recopilen más datos, reentrenar los modelos y experimentar con arquitecturas más complejas o ingeniería de características avanzada.
Profundizar en "IA Explicando Errores": Extraer reglas más específicas de los Árboles de Decisión o usar técnicas como SHAP/LIME para modelos más complejos.
Alertas y Evolución en el Tiempo: Si se guardan datos a largo plazo por usuario, se podría mostrar su progreso y generar alertas sobre cambios en su rendimiento o estilo. ()
Comparación entre Jugadores: Permitir comparar estadísticas y recomendaciones entre dos jugadores.
Análisis de Fase de Juego: Extraer datos de la timeline de las partidas para dar consejos específicos sobre el juego temprano, medio o tardío. ()
Sugerencias de Builds más Detalladas: Analizar composiciones enemigas para sugerir ítems situacionales.

Enlace al Proyecto: https://github.com/Erikzonnn/LoL-Smart-Tracker
