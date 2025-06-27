import os
import json
import time
import logging
from PIL import Image
from google.api_core import exceptions
from flask import Flask, request, jsonify, render_template
import base64
from io import BytesIO
from api import model  # Remove vision_model from import

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Crear la app Flask primero
app = Flask(__name__)

# Ruta para servir la página principal (interfaz)
@app.route('/')
def index():
    return render_template('index.html')

# API para describir imagen (JSON con base64)
@app.route('/api/describe-image', methods=['POST'])
def describe_image():
    data = request.get_json()
    base64_str = data.get('base64')
    name = data.get('name')
    tipo = data.get('tipo')
    dimensiones = data.get('dimensiones')
    descripcion = ""
    logging.info(f"Solicitud recibida para describir imagen: name={name}, tipo={tipo}, dimensiones={dimensiones}")
    try:
        image_data = base64.b64decode(base64_str)
        img = Image.open(BytesIO(image_data))
        logging.info(f"Imagen decodificada correctamente: {name}")
        max_retries = 3
        retry_delay = 60  # segundos
        for attempt in range(max_retries):
            try:
                # Convertir PIL Image a base64 PNG
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                logging.info(f"Imagen convertida a base64 PNG para {name}")

                response = model.generate_content(
                    [
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": img_base64
                            }
                        },
                        "Describe brevemente en tres palabras la imagen y proporciona una breve descripción en español."
                    ],
                    generation_config={
                        "temperature": 0.7,
                        "top_p": 0.1,
                        "top_k": 16,
                        "max_output_tokens": 100
                    }
                )
                descripcion = response.text.strip()
                logging.info(f"Descripción generada para {name}: {descripcion}")
                break
            except exceptions.ResourceExhausted:
                logging.warning(f"Cuota excedida al describir {name}, intento {attempt+1}/{max_retries}")
                if attempt == max_retries - 1:
                    descripcion = "Error: No se pudo obtener la descripción debido a límites de cuota"
                else:
                    time.sleep(retry_delay)
            except Exception as e:
                logging.error(f"Error inesperado al describir {name}: {str(e)}")
                descripcion = f"Error: {str(e)}"
                break
    except Exception as e:
        logging.error(f"Error procesando la imagen {name}: {str(e)}")
        descripcion = f"Error: {str(e)}"
    return jsonify({
        "name": name,
        "tipo": tipo,
        "dimensiones": dimensiones,
        "descripcion": descripcion
    })

# API para describir imagen desde formulario (multipart/form-data)
@app.route('/api/describe-image-form', methods=['POST'])
def describe_image_form():
    if 'image' not in request.files:
        logging.warning("No image uploaded en describe-image-form")
        return jsonify({"error": "No image uploaded"}), 400
    file = request.files['image']
    if file.filename == '':
        logging.warning("No image selected en describe-image-form")
        return jsonify({"error": "No image selected"}), 400

    # Leer y convertir a base64
    img_bytes = file.read()
    base64_str = base64.b64encode(img_bytes).decode('utf-8')
    mime_type = file.mimetype

    prompt = "Describe esta imagen de forma detallada en una o dos frases:"

    logging.info(f"Solicitud recibida para describir imagen por formulario: filename={file.filename}, mime_type={mime_type}")

    try:
        response = model.generate_content(  # Use model instead of vision_model
            [
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": base64_str
                    }
                },
                prompt
            ],
            generation_config={
                "temperature": 0.7,
                "top_p": 0.1,
                "top_k": 16,
                "max_output_tokens": 150
            }
        )
        descripcion = response.text.strip()
        logging.info(f"Descripción generada para {file.filename}: {descripcion}")
    except Exception as e:
        logging.error(f"Error describiendo imagen por formulario {file.filename}: {str(e)}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"descripcion": descripcion})

if __name__ == "__main__":
    logging.info("Iniciando servidor Flask en modo debug")
    app.run(debug=True)
