from cryptography.fernet import Fernet, InvalidToken


def generate_encryption_key() -> str:
    return Fernet.generate_key().decode()


def encrypt_key(plaintext: str, encryption_key: str) -> str:
    fernet = Fernet(encryption_key.encode())
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str, encryption_key: str) -> str:
    fernet = Fernet(encryption_key.encode())
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return ""


def mask_key(plaintext: str) -> str:
    if not plaintext:
        return ""
    if len(plaintext) <= 8:
        return "****"
    return f"{plaintext[:4]}...{plaintext[-4:]}"
