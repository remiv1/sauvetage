"""
Module de gestion des hashages de mots de passe. Il y a une classe principale :
    - PwdHasher : Service de hashage/validation des mots de passe.
Ce module utilise la bibliothèque bcrypt pour le hashage sécurisé des mots de passe.
"""

import bcrypt

class PwdHasher:
    """
    Service de hashage/validation des mots de passe.
    Contient les méthodes :
        - __init__ : pour initialiser le service avec un nombre de rounds pour bcrypt.
        - hash : pour hasher un mot de passe en utilisant bcrypt.
        - verify : pour vérifier si un mot de passe correspond à un hash donné.
    """

    def __init__(self, rounds: int = 12) -> None:
        """Initialise le service de hashage.
        Args:
            rounds (int): Le nombre de rounds pour le hashage bcrypt.
                          Plus c'est élevé, plus c'est sécurisé mais plus c'est lent.
        """
        self.rounds = rounds

    def hash(self, password: str) -> str:
        """Hash un mot de passe en utilisant bcrypt.
        Args:
            password (str): Le mot de passe à hasher.
        Returns:
            str: Le mot de passe hashé.
        """
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password=password.encode('utf-8'), salt=salt)
        return hashed.decode('utf-8')

    def verify(self, password: str, hashed: str) -> bool:
        """Vérifie si un mot de passe correspond à un hash donné.
        Args:
            password (str): Le mot de passe à vérifier.
            hashed (str): Le hash à comparer.
        Returns:
            bool: True si le mot de passe correspond au hash, False sinon.
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
