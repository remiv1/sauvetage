"""Tests unitaires pour les objets de la base de données."""

from typing import Dict, Any
from sqlalchemy.orm import Session, joinedload
from db_models.objects.users import Users, UsersPasswords

def test_user_to_dict(db_session: Session): # pylint: disable=redefined-outer-name
    """Test de la méthode to_dict de la classe Users."""
    user = Users(
        id=1,
        username="testuser",
        email="test@user.fr",
        is_active=True,
        nb_failed_logins=0,
        is_locked=False,
        permissions="13"
    )
    db_session.add(user)
    db_session.commit()
    retrieved: Users = db_session.query(Users).where(Users.id==1).first()
    user_dict = retrieved.to_dict() # type: ignore

    assert user_dict["id"] == 1
    assert user_dict["username"] == "testuser"
    assert user_dict["email"] == "test@user.fr"
    assert user_dict["is_active"] is True
    assert user_dict["nb_failed_logins"] == 0
    assert user_dict["is_locked"] is False
    assert user_dict["permissions"] == "13"
    assert "created_at" not in user_dict
    assert "updated_at" not in user_dict

def test_user_from_dict():
    """Test de la méthode from_dict de la classe Users."""
    user_data: Dict[str, Any] = {
        "username": "testuser",
        "email": "test@user.fr",
        "is_active": True,
        "permissions": "13"
    }
    user = Users.from_dict(user_data)
    assert user.username == "testuser"
    assert user.email == "test@user.fr"
    assert user.is_active is True
    assert user.permissions == "13"

def test_complete_user(db_session: Session):    # pylint: disable=unused-argument, redefined-outer-name
    """Test de récupération d'un utilisateur complet"""
    user = Users(
        username="John Doe",
        email="john.doe@example.com",
        permissions="12345678"
    )
    db_session.add(user)
    db_session.flush()
    pswd = UsersPasswords(
        user_id=user.id,
        password_hash="hashed_password"
    )
    db_session.add(pswd)
    db_session.commit()
    retrieved_user = db_session.query(Users) \
                               .where(Users.id==user.id) \
                               .options(
                                   joinedload(Users.passwords)
                               ) \
                               .first()
    assert retrieved_user is not None
    assert retrieved_user.username == "John Doe"
    assert retrieved_user.email == "john.doe@example.com"
    assert retrieved_user.permissions == "12345678"
    assert len(retrieved_user.passwords) == 1
    assert retrieved_user.passwords[0].password_hash == "hashed_password"
