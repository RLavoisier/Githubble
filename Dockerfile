# Utilise l'image officielle Python 3.13
FROM python:3.13-slim

# Définit le répertoire de travail
WORKDIR /app

# Installe Poetry
RUN pip install --no-cache-dir poetry

# Copie les fichiers nécessaires
COPY pyproject.toml poetry.lock ./

# Installe les dépendances sans installer dev dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Copie le code source
COPY app/ ./app/

# Expose le port de l'application
EXPOSE 8000

# Commande pour démarrer FastAPI avec Uvicorn
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
