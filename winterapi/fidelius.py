"""
Fidelius is the keeper of secrets. It is the class that handles the secrets.
"""

import logging

import numpy as np
from filelock import FileLock
from wintertoo.models import Program

from winterapi.credentials import (
    TIMEOUT,
    WinterAPICredentials,
    clear_credentials_cache,
    get_secrets,
    secrets_lock_path,
    write_secrets,
)

logger = logging.getLogger(__name__)


class Fidelius:
    """
    Class to handle the secrets.
    """

    def __init__(self):
        self.credentials = self.load_secrets()

    @staticmethod
    def load_secrets() -> WinterAPICredentials:
        """
        Load the secrets from the keyring.

        :return:
        """
        secret_dict = get_secrets()
        return WinterAPICredentials(**secret_dict)

    def reload_secrets(self):
        """
        Reload the secrets from the keyring.

        :return: None
        """
        self.credentials = self.load_secrets()

    def export_secrets(self):
        """
        Export the secrets to the keyring.

        :return: None
        """
        write_secrets(secrets_dict=self.credentials.dict())

    def set_user(self, user: str, password: str, overwrite=False):
        """
        Function to set the user and password.

        :param user: User name.
        :param password: Password.
        :param overwrite: bool, whether to overwrite existing user/password.
        :return: None
        """
        self.reload_secrets()
        with FileLock(secrets_lock_path, timeout=TIMEOUT):
            if np.logical_and(self.credentials.user is None, not overwrite):
                err = f"User/password already set, and overwrite is set to {overwrite}."
                logger.error(err)
                raise ValueError(err)

            self.credentials.user = user
            self.credentials.password = password
            self.export_secrets()

    def get_user(self) -> str:
        """
        Get the user name.

        :return: user name
        """
        if self.credentials.user is None:
            err = "No user has been set"
            logger.error(err)
            raise KeyError(err)

        return self.credentials.user

    def get_password(self) -> str:
        """
        Get the password.

        :return: Password
        """
        if self.credentials.password is None:
            err = "No password has been set"
            logger.error(err)
            raise KeyError(err)
        return self.credentials.password

    def add_program(self, program_details: dict, overwrite=False):
        """
        Function to add a program to the credentials.

        :param program_details: Program details.
        :param overwrite: Bool, whether to overwrite existing program.
        :return: None
        """
        self.reload_secrets()

        program_details.pop("puid")

        program_details = Program(**program_details)

        with FileLock(secrets_lock_path, timeout=TIMEOUT):
            if np.logical_and(
                program_details.progname in self.credentials.programs, not overwrite
            ):
                err = (
                    f"Program {program_details.progname} already set, "
                    f"and overwrite is set to {overwrite}."
                )
                logger.error(err)
                raise ValueError(err)

            self.credentials.programs[program_details.progname] = program_details
            self.export_secrets()

    def get_programs(self) -> list[Program]:
        """
        Function to get the list of programs.

        :return: List of programs.
        """
        return sorted(list(self.credentials.programs))

    def get_all_program_details(self) -> dict[str, Program]:
        """
        Return all the program details.

        :return: Program details.
        """
        return self.credentials.programs

    def get_program_details(self, program_name: str) -> Program:
        """
        Get the details of a program.

        :param program_name: Name of the program.
        :return: Program details.
        """
        if program_name not in self.credentials.programs:
            err = (
                f"Program {program_name} not found in"
                f" {list(self.credentials.programs)}"
            )
            logger.error(err)
            raise KeyError(err)
        return self.credentials.programs[program_name]

    def delete_program(self, program_name: str):
        """
        Function to delete a program.

        :param program_name: Name of the program.
        :return: None
        """
        self.reload_secrets()
        with FileLock(secrets_lock_path, timeout=TIMEOUT):
            assert self.get_program_details(program_name) is not None
            del self.credentials.programs[program_name]
            self.export_secrets()

    @staticmethod
    def clear_cache():
        """
        Clear the cache.

        :return: None
        """
        clear_credentials_cache()
