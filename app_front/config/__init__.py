"""Configuration du projet Flask"""

from os import getenv

API_URL = getenv("API_URL", "http://app-back:8000/api/v1")
NO_USERS_URL = f"{API_URL}/users/no-user"
LOGIN_URL = f"{API_URL}/users/login"
CREATE_USER_URL = f"{API_URL}/users/create"
CHANGE_PASSWORD_URL = f"{API_URL}/users/change-password"
SEARCH_USER_URL = f"{API_URL}/users/search"
MODIFY_USER_URL = f"{API_URL}/users/modify"
