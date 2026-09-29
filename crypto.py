import nacl.pwhash
import nacl.secret
import nacl.utils
import nacl.exceptions

from config import PASSPHRASE_HASH, KDF_SALT

KEY_SIZE = nacl.secret.SecretBox.KEY_SIZE  # 32
OPSLIMIT = nacl.pwhash.argon2id.OPSLIMIT_INTERACTIVE
MEMLIMIT = nacl.pwhash.argon2id.MEMLIMIT_INTERACTIVE


def verify_passphrase(passphrase):
    """Returns True if passphrase matches the hash stored in config.py."""
    try:
        nacl.pwhash.argon2id.verify(PASSPHRASE_HASH, passphrase.encode())
        return True
    except nacl.exceptions.InvalidkeyError:
        return False


def derive_key(passphrase):
    """Same passphrase + fixed salt = same key, on every device."""
    return nacl.pwhash.argon2id.kdf(
        KEY_SIZE, passphrase.encode(), KDF_SALT,
        opslimit=OPSLIMIT, memlimit=MEMLIMIT,
    )


def encrypt_message(key, plaintext):
    """Returns (nonce_hex, ciphertext_hex) ready to store in Supabase."""
    box = nacl.secret.SecretBox(key)
    nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
    encrypted = box.encrypt(plaintext.encode(), nonce)
    return nonce.hex(), encrypted.ciphertext.hex()


def decrypt_message(key, nonce_hex, ciphertext_hex):
    box = nacl.secret.SecretBox(key)
    nonce = bytes.fromhex(nonce_hex)
    ciphertext = bytes.fromhex(ciphertext_hex)
    return box.decrypt(ciphertext, nonce).decode()