"""
Module contenant les décorateurs et classes utilitaires pour les opérations SFTP
avec le serveur de Dilicom.
Ce module inclut:
- Le décorateur `retry_sftp` pour réessayer les opérations SFTP en cas d'erreur de connexion.
"""

import paramiko

def retry_sftp(func):
    """
    Décorateur pour réessayer une opération SFTP en cas d'erreur de connexion.
    
    args:
        func (callable): La fonction SFTP à décorer.
    returns:
        callable: La fonction décorée avec la logique de réessai.
    """
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (paramiko.SSHException, EOFError):
            self.connect()
            return func(self, *args, **kwargs)
    return wrapper
