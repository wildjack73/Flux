import os
import time
import random
import logging
import requests
from flask import Flask, request, jsonify, render_template, send_file
from dotenv import load_dotenv
from io import BytesIO

load_dotenv()

# Configuration
FLUX_API_KEY = os.getenv('FLUX_API_KEY')
FLUX_API_URL = "https://api.bfl.ml/v1/flux-pro-1.1"
FLUX_RESULT_URL = "https://api.bfl.ml/v1/result"

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_common_headers():
    return {
        'x-key': FLUX_API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
    }

def check_generation_status(request_id, max_attempts=20):
    """Vérifie le statut de la génération d'image."""
    logger.info(f"Checking status for request_id: {request_id}")
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"Status check attempt {attempt + 1}/{max_attempts}")
            response = requests.get(
                f"{FLUX_RESULT_URL}/{request_id}",
                headers=get_common_headers()
            )
            
            logger.info(f"Status response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('status', '').lower()
                
                logger.info(f"Status: {status}")
                
                if status == 'ready':
                    image_url = result.get('image')
                    if image_url:
                        logger.info(f"Image URL found: {image_url}")
                        return image_url
                    logger.warning("Status ready but no image URL found")
                    
            elif response.status_code != 404:
                logger.error(f"Unexpected status code: {response.status_code}")
                break
                
            time.sleep(1.5)
            
        except Exception as e:
            logger.error(f"Error checking status: {str(e)}")
            time.sleep(1.5)
            
    logger.error("Max attempts reached without success")
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_image():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        seed = data.get('seed', random.randint(1000, 9999))

        logger.info(f"Starting generation with prompt: {prompt}, seed: {seed}")

        if not prompt:
            return jsonify({'error': 'Prompt manquant'}), 400

        headers = get_common_headers()
        payload = {
            'prompt': prompt,
            'width': 1024,
            'height': 768,
            'prompt_upsampling': False,
            'safety_tolerance': 2,
            'seed': seed
        }

        logger.info(f"Sending request to API with payload: {payload}")
        response = requests.post(FLUX_API_URL, headers=headers, json=payload)
        
        logger.info(f"API Response status: {response.status_code}")
        logger.info(f"API Response content: {response.text}")
        
        if response.status_code != 200:
            return jsonify({'error': f'Erreur API: {response.text}'}), response.status_code

        request_id = response.json().get('request_id')
        if not request_id:
            return jsonify({'error': 'ID de requête manquant'}), 400

        logger.info(f"Got request_id: {request_id}, checking status...")
        image_url = check_generation_status(request_id)
        
        if not image_url:
            return jsonify({'error': 'Échec de la génération'}), 500

        response_data = {
            'image': image_url,
            'seed': seed
        }
        logger.info(f"Success! Sending response: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Erreur lors de la génération: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download-image')
def download_image():
    try:
        image_url = request.args.get('url')
        prompt = request.args.get('prompt', '')
        
        if not image_url:
            return jsonify({'error': 'URL manquante'}), 400

        # Créer un nom de fichier à partir des deux premiers mots du prompt
        words = prompt.strip().split()[:2]  # Prendre les deux premiers mots
        filename = '_'.join(words) if words else 'generated'  # Joindre les mots avec un underscore
        filename = ''.join(c if c.isalnum() or c == '_' else '_' for c in filename)  # Nettoyer le nom
        filename = f"{filename}.jpg"  # Ajouter l'extension

        response = requests.get(image_url)
        if response.status_code != 200:
            return jsonify({'error': 'Erreur lors du téléchargement'}), response.status_code

        return send_file(
            BytesIO(response.content),
            mimetype='image/jpeg',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
