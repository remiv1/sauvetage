"""
Module contenant les services pour les opérations SFTP avec le serveur de Dilicom.
Ce module inclut:
- La classe `DilicomService` qui encapsule les opérations SFTP avec le serveur de Dilicom.
"""

from db_models.repositories.dilicom import DilicomRepository

class DilicomService:
    """
    Service pour les opérations SFTP avec le serveur de Dilicom.
    Cette classe utilise `DilicomRepository` pour gérer les connexions et les opérations SFTP.
    """
    def __init__(self):
        self.repository = DilicomRepository()
