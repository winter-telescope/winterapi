"""
Module for credentials
"""

import base64
import json
import logging
import secrets
from pathlib import Path
from typing import Optional

import keyring
from cryptography.fernet import Fernet
from keyring.errors import PasswordDeleteError
from pydantic import BaseModel, Field
from wintertoo.models import Program

logger = logging.getLogger(__name__)


KEYRING_SERVICE = "winterapi"
KEYRING_USER = "apisaltkey"
ENCODING = "ascii"
TIMEOUT = 300.0


class WinterAPICredentials(BaseModel):
    """
    Credentials for the Winter API
    """

    user: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    programs: dict[str, Program] = {}


secret_path = Path.home().joinpath(".winterapi.txt")
secrets_lock_path = secret_path.with_suffix(secret_path.suffix + ".lock")


def encrypt(
    text_str: str,
    keyring_service: str = KEYRING_SERVICE,
    keyring_user: str = KEYRING_USER,
) -> (bytes, bytes):
    """
    Function to encrypt a plaintext message.

    :param text_str: Text message to encrypt.
    :param keyring_service: Keyring service to use.
    :param keyring_user: Keyring user to use.
    :return:
    """
    fernet = Fernet(
        get_encryption_password(
            keyring_service=keyring_service, keyring_user=keyring_user
        )
    )
    ciphertext = fernet.encrypt(text_str.encode("utf-8"))

    return ciphertext


def write_secrets(
    secrets_dict: dict,
    keyring_service: str = KEYRING_SERVICE,
    keyring_user: str = KEYRING_USER,
):
    """
    Function to write secrets to a file.

    :param secrets_dict: Secrets dictionary to write.
    :param keyring_service: Keyring service to use.
    :param keyring_user: Keyring user to use.
    :return: None
    """
    with open(secret_path, "wb") as out_f:
        out_f.write(
            encrypt(
                str(json.dumps(secrets_dict, default=str)),
                keyring_service=keyring_service,
                keyring_user=keyring_user,
            )
        )


def decrypt(
    ciphertext: bytes,
    keyring_service: str = KEYRING_SERVICE,
    keyring_user: str = KEYRING_USER,
) -> str:
    """
    Function to decrypt a ciphertext message.

    :param ciphertext: Ciphertext message to decrypt.
    :param keyring_service: Keyring service to use.
    :param keyring_user: Keyring user to use.
    :return: Decrypted message.
    """
    # Decrypt the message
    fernet = Fernet(
        get_encryption_password(
            keyring_service=keyring_service, keyring_user=keyring_user
        )
    )
    plaintext = fernet.decrypt(ciphertext)

    return plaintext.decode("utf-8")


def get_secrets(
    keyring_service: str = KEYRING_SERVICE, keyring_user: str = KEYRING_USER
) -> dict:
    """
    Get secrets from the secrets file.

    :param keyring_service: Keyring service to use.
    :param keyring_user: Keyring user to use.
    :return: Secrets dictionary.
    """
    if secret_path.exists():
        with open(secret_path, "rb") as in_f:
            encrypted = in_f.read()
            decrypted = json.loads(
                decrypt(
                    encrypted,
                    keyring_service=keyring_service,
                    keyring_user=keyring_user,
                )
            )
    else:
        decrypted = {}
    return decrypted


def get_encryption_password(
    keyring_service: str = KEYRING_SERVICE, keyring_user: str = KEYRING_USER
) -> bytes:
    """
    Get the encryption password from the keyring.

    :param keyring_service: Keyring service to use.
    :param keyring_user: Keyring user to use.
    :return: Password
    """
    str_password = keyring.get_password(keyring_service, keyring_user)
    if str_password is None:
        password = base64.urlsafe_b64encode(secrets.token_bytes(32))
        keyring.set_password(
            keyring_service, keyring_user, password.decode(encoding=ENCODING)
        )
    else:
        password = str_password.encode(encoding=ENCODING)
    return password


def clear_credentials_cache():
    """
    Function to clear the credentials cache.

    :return: None
    """
    secret_path.unlink(missing_ok=True)
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
    except PasswordDeleteError:
        pass
