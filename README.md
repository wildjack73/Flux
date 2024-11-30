# Générateur d'Images IA avec Flux 1.1 Pro

## Prérequis
- Python 3.8+
- Compte Flux API avec clé d'accès

## Installation

1. Clonez le dépôt
2. Créez un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. Installez les dépendances
```bash
pip install -r requirements.txt
```

4. Configurez votre clé API
- Ouvrez le fichier `.env`
- Remplacez `votre_clé_api_flux_ici` par votre clé API réelle

## Lancement de l'application
```bash
python app.py
```

Ouvrez votre navigateur à l'adresse `http://localhost:5000`

## Utilisation
1. Entrez une description détaillée de l'image
2. Cliquez sur "Générer l'Image"
3. L'image générée s'affichera automatiquement

## Fonctionnalités
- Génération d'images par IA
- Interface simple et intuitive
- Supporte les prompts en français et en anglais

## Limitations
- Nécessite une connexion internet
- Dépend des limitations de l'API Flux
