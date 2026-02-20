"""Configuration du projet Flask"""

from os import getenv

API_URL = getenv('API_URL', 'http://app-back:8000/api/v1')
