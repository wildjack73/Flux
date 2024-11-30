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
        data = request.json
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Prompt requis'}), 400
            
        prompt = data['prompt']
        seed = data.get('seed')
        
        logger.info(f"Starting generation with prompt: {prompt}")
        
        try:
            # Configuration de l'API Flux
            headers = get_common_headers()
            
            # Préparation des données
            payload = {
                'prompt': prompt,
                'width': 1024,
                'height': 768,
                'prompt_upsampling': False,
                'safety_tolerance': 2,
                'seed': seed if seed is not None else random.randint(1000, 9999),
                'negative_prompt': 'blurry, bad quality, worst quality, low quality, deformed, distorted, disfigured'
            }
            
            # Envoi de la requête
            logger.info("Envoi de la requête à Flux...")
            logger.info(f"Payload: {payload}")
            
            response = requests.post(
                FLUX_API_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"API error response: {response.text}")
                return jsonify({'error': 'Erreur lors de la génération'}), response.status_code
                
            result = response.json()
            request_id = result.get('id')
            
            if not request_id:
                return jsonify({'error': 'ID de requête manquant dans la réponse'}), 500
                
            # Vérification du statut
            image_url = check_generation_status(request_id)
            
            if not image_url:
                return jsonify({'error': 'Timeout lors de la génération de l\'image'}), 500
                
            return jsonify({
                'status': 'completed',
                'image': image_url,
                'seed': payload.get('seed', 'aléatoire')
            })
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Erreur de communication avec Flux: {str(e)}"
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 500
            
        except Exception as e:
            error_msg = f"Erreur lors de la génération de l'image: {str(e)}"
            logger.error(error_msg)
            logger.exception("Stack trace complète:")
            return jsonify({'error': error_msg}), 500
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in generation: {error_msg}")
        logger.exception("Stack trace complète:")
        return jsonify({'error': error_msg}), 500

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
