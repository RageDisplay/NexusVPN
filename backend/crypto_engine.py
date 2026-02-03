"""
Криптографический движок для VPN
Использует ChaCha20-Poly1305 AEAD и Curve25519 для ECDH
"""
import os
import struct
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class CryptoEngine:
    """Криптографический движок"""
    
    NONCE_SIZE = 12
    TAG_SIZE = 16
    KEY_SIZE = 32
    PBKDF2_ITERATIONS = 100000
    
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.session_key = None
        self.backend = default_backend()
        self.nonce_counter = 0
    
    def generate_keypair(self):
        """Генерировать пару ключей Curve25519"""
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def derive_session_key(self, server_public_key_bytes: bytes, password: bytes):
        """Вывести сессионный ключ из общего секрета и пароля"""
        # Десериализовать публичный ключ сервера
        server_public_key = x25519.X25519PublicKey.from_public_bytes(server_public_key_bytes)
        
        # Выполняем ECDH
        shared_secret = self.private_key.exchange(server_public_key)
        
        # Комбинируем с паролем для дополнительной безопасности
        if isinstance(password, str):
            password = password.encode()
        combined = shared_secret + password
        
        # Применяем KDF
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=b'NexusVPN_Salt',
            iterations=self.PBKDF2_ITERATIONS,
            backend=self.backend
        )
        self.session_key = kdf.derive(combined)
    
    def generate_nonce(self) -> bytes:
        """Генерировать уникальный nonce"""
        # Используем счетчик + случайные байты для уникальности
        nonce = struct.pack('>Q', self.nonce_counter) + os.urandom(4)
        self.nonce_counter += 1
        return nonce[:self.NONCE_SIZE]
    
    def encrypt(self, plaintext: bytes, aad: bytes = None) -> tuple[bytes, bytes]:
        """
        Зашифровать данные с ChaCha20-Poly1305
        Возвращает (ciphertext, nonce)
        """
        if self.session_key is None:
            raise ValueError("Session key not set")
        
        nonce = self.generate_nonce()
        cipher = ChaCha20Poly1305(self.session_key)
        
        ciphertext = cipher.encrypt(nonce, plaintext, aad)
        return ciphertext, nonce
    
    def decrypt(self, ciphertext: bytes, nonce: bytes, aad: bytes = None) -> bytes:
        """
        Расшифровать данные с ChaCha20-Poly1305
        """
        if self.session_key is None:
            raise ValueError("Session key not set")
        
        cipher = ChaCha20Poly1305(self.session_key)
        return cipher.decrypt(nonce, ciphertext, aad)


class HandshakeProtocol:
    """Протокол рукопожатия с поддержкой обфусцировки"""
    
    def __init__(self):
        self.crypto = CryptoEngine()
    
    def initiate_handshake(self, password: bytes) -> tuple[bytes, bytes]:
        """
        Инициировать рукопожатие
        Возвращает (public_key, encrypted_public_key)
        """
        public_key_raw = self.crypto.generate_keypair()
        
        # Зашифровать публичный ключ паролем для дополнительной безопасности
        cipher = ChaCha20Poly1305(self._derive_password_key(password))
        nonce = os.urandom(self.crypto.NONCE_SIZE)
        encrypted = cipher.encrypt(nonce, public_key_raw, b'HANDSHAKE')
        
        return public_key_raw, nonce + encrypted
    
    def respond_handshake(self, client_public_key: bytes, password: bytes) -> bytes:
        """
        Ответить на рукопожатие
        Возвращает зашифрованный публичный ключ сервера
        """
        self.crypto.generate_keypair()
        
        # Вывести сеансовый ключ
        self.crypto.derive_session_key(client_public_key, password)
        
        return self.crypto.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'NexusVPN_PWD',
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(password)
