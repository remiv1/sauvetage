"""Module de tests pour les routes d'administration du front-end."""

import pytest   # pylint: disable=unused-import

REDIRECTION = "<!doctype html>\n<html lang=en>\n<title>Redirecting...</"
HOME_PAGE = "<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n"
FORBIDEN = "<!doctype html>\n<html lang=en>\n<title>403 Forbidden"


def test_index(client_all):
    """Test de la route d'index de l'administration."""
    response = client_all.get("/admin/")

    assert response.status_code == 200
    assert response.text.startswith(HOME_PAGE)


def test_create_first_user(client, fastapi_test_client, make_user):  # pylint: disable=unused-argument
    """Test de la route de création du premier utilisateur."""
    # Test sans utilisateur en base - devrait afficher le formulaire (200)
    response_get = client.get("/admin/first-user")
    assert response_get.status_code == 200
    assert response_get.text.startswith(HOME_PAGE)

    # On suppose que le premier utilisateur a déjà été créé dans les tests précédents
    make_user(username="admin", email="admin@example.com")
    # Après création d'un utilisateur, devrait rediriger (302)
    response_get_2 = client.get("/admin/first-user")
    assert response_get_2.status_code == 302
    assert response_get_2.text.startswith(REDIRECTION)
