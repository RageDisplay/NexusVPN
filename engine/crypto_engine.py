"""
Криптографический движок для VPN протокола
Использует ChaCha20-Poly1305 для шифрования и Curve25519 для обмена ключами
"""
import os
import struct
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.backends import default_backend
import hashlib


class CryptoEngine:
    """Основной криптографический модуль"""
    
    NONCE_SIZE = 12  # 96 бит для ChaCha20
    TAG_SIZE = 16    # 128 бит для Poly1305
    KEY_SIZE = 32    # 256 бит
    
    def __init__(self):
        self.backend = default_backend()
        self.private_key = None
        self.public_key = None
        self.shared_secret = None
        self.encryption_key = None
        self.decryption_key = None
        self.send_counter = 0
        self.recv_counter = 0
    
    def generate_keypair(self):
        """Генерирует пару ключей на основе Curve25519"""
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def get_public_key(self):
        """Возвращает открытый ключ"""
        if self.public_key is None:
            self.generate_keypair()
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def establish_shared_secret(self, peer_public_key_bytes, is_server=False):
        """Устанавливает общий секрет используя открытый ключ соседа"""
        peer_public_key = x25519.X25519PublicKey.from_public_bytes(peer_public_key_bytes)
        self.shared_secret = self.private_key.exchange(peer_public_key)
        
        # Производим два ключа из общего секрета (один для отправки, один для приёма)
        hkdf_salt = b'vpn_protocol_v1'
        
        # На сервере ключи меняются местами
        if is_server:
            # Сервер слушает (приём) на ключе, который клиент использовал для отправки
            hash_obj = hashlib.sha256()
            hash_obj.update(self.shared_secret + hkdf_salt + b'client_encryption')
            self.decryption_key = hash_obj.digest()[:self.KEY_SIZE]
            
            hash_obj = hashlib.sha256()
            hash_obj.update(self.shared_secret + hkdf_salt + b'server_encryption')
            self.encryption_key = hash_obj.digest()[:self.KEY_SIZE]
        else:
            # Клиент отправляет на ключе client_encryption и слушает на server_encryption
            hash_obj = hashlib.sha256()
            hash_obj.update(self.shared_secret + hkdf_salt + b'client_encryption')
            self.encryption_key = hash_obj.digest()[:self.KEY_SIZE]
            
            hash_obj = hashlib.sha256()
            hash_obj.update(self.shared_secret + hkdf_salt + b'server_encryption')
            self.decryption_key = hash_obj.digest()[:self.KEY_SIZE]
    
    def _create_nonce(self, counter):
        """Создаёт nonce из счётчика"""
        return struct.pack('<Q', counter) + b'\x00\x00\x00\x00'
    
    def encrypt(self, plaintext, aad=b''):
        """
        Шифрует данные используя ChaCha20-Poly1305
        
        Args:
            plaintext: Данные для шифрования
            aad: Additional Authenticated Data
        
        Returns:
            (counter, ciphertext, tag) - счётчик, шифротекст и тег аутентификации
        """
        if self.encryption_key is None:
            raise ValueError("Shared secret не установлен")
        
        nonce = self._create_nonce(self.send_counter)
        cipher = ChaCha20Poly1305(self.encryption_key)
        
        ciphertext = cipher.encrypt(nonce, plaintext, aad)
        counter = self.send_counter
        self.send_counter += 1
        
        return counter, ciphertext
    
    def decrypt(self, counter, ciphertext, aad=b''):
        """
        Расшифровывает данные используя ChaCha20-Poly1305
        
        Args:
            counter: Счётчик для создания nonce
            ciphertext: Зашифрованные данные с тегом
            aad: Additional Authenticated Data
        
        Returns:
            plaintext - расшифрованные данные
        """
        if self.decryption_key is None:
            raise ValueError("Shared secret не установлен")
        
        nonce = self._create_nonce(counter)
        cipher = ChaCha20Poly1305(self.decryption_key)
        
        plaintext = cipher.decrypt(nonce, ciphertext, aad)
        return plaintext
    
    def hash_password(self, password: str, salt: bytes = None) -> tuple:
        """Хеширует пароль используя SHA-256"""
        if salt is None:
            salt = os.urandom(16)
        
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return hash_obj, salt


class HandshakeProtocol:
    """Протокол рукопожатия для установления безопасного соединения"""
    
    HANDSHAKE_VERSION = 1
    HANDSHAKE_HELLO = 0x01
    HANDSHAKE_KEY_EXCHANGE = 0x02
    HANDSHAKE_AUTH = 0x03
    HANDSHAKE_SUCCESS = 0x04
    HANDSHAKE_ERROR = 0x05
    
    def __init__(self):
        self.crypto = CryptoEngine()
    
    def create_hello_packet(self):
        """Создаёт HELLO пакет для инициализации рукопожатия"""
        packet = struct.pack('!B', self.HANDSHAKE_VERSION)
        packet += struct.pack('!B', self.HANDSHAKE_HELLO)
        packet += os.urandom(8)  # Случайный ID сеанса
        return packet
    
    def create_key_exchange_packet(self):
        """Создаёт пакет обмена ключами"""
        public_key = self.crypto.generate_keypair()
        packet = struct.pack('!B', self.HANDSHAKE_KEY_EXCHANGE)
        packet += struct.pack('!H', len(public_key))
        packet += public_key
        return packet, self.crypto
    
    def parse_key_exchange_packet(self, data):
        """Парсит пакет обмена ключами"""
        if data[0] != self.HANDSHAKE_KEY_EXCHANGE:
            raise ValueError("Неверный тип пакета")
        
        key_len = struct.unpack('!H', data[1:3])[0]
        public_key = data[3:3+key_len]
        return public_key
