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
    headers = get_common_headers()
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(
                f"https://api.bfl.ml/v1/get_result?id={request_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'Ready':
                    return data.get('result', {}).get('sample')
            
            attempt += 1
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error checking status: {str(e)}")
            time.sleep(0.5)
    
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

        response = requests.post(FLUX_API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            return jsonify({'error': f'Erreur API: {response.text}'}), response.status_code

        request_id = response.json().get('request_id')
        if not request_id:
            return jsonify({'error': 'ID de requête manquant'}), 400

        image_url = check_generation_status(request_id)
        if not image_url:
            return jsonify({'error': 'Échec de la génération'}), 500

        response_data = {
            'image': image_url,
            'seed': seed
        }
        logger.info(f"Sending response with seed: {seed}")
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
