"""Exceptions for Keenetic integration."""


class KeeneticError(Exception):
    """Base exception for Keenetic integration."""


class KeeneticConnectionError(KeeneticError):
    """Exception raised when connection to router fails."""


class KeeneticAuthenticationError(KeeneticError):
    """Exception raised when authentication fails."""


class KeeneticTimeoutError(KeeneticError):
    """Exception raised when request times out."""


class KeeneticResponseError(KeeneticError):
    """Exception raised when router returns unexpected response."""
