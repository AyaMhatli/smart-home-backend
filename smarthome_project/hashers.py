from django.contrib.auth.hashers import PBKDF2PasswordHasher


class FastPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    """Meme algorithme, moins de tours de calcul (adapte a la Raspberry Pi)."""
    iterations = 100000
