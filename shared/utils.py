"""
Вспомогательные функции
"""
import hashlib
import hmac
import os
from typing import Tuple

# Фиксированная соль для всех операций хеширования паролей
FIXED_SALT = b'NexusVPN_DefaultSalt_v1.0'

def generate_random_bytes(length: int) -> bytes:
    """Генерировать случайные байты"""
    return os.urandom(length)


def hash_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
    """Хешировать пароль с солью"""
    if salt is None:
        salt = FIXED_SALT
    
    # PBKDF2 с 100k итерациями
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt,
        100000
    )
    return pwd_hash, salt


def verify_password(password: str, stored_hash: bytes, salt: bytes) -> bool:
    """Проверить пароль"""
    pwd_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(pwd_hash, stored_hash)


def get_local_ip() -> str:
    """Получить локальный IP адрес"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class RateLimiter:
    """Ограничитель частоты запросов"""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
    
    def is_allowed(self, key: str) -> bool:
        """Проверить, разрешен ли запрос"""
        import time
        now = time.time()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Удалить старые запросы
        self.requests[key] = [
            t for t in self.requests[key] 
            if now - t < self.time_window
        ]
        
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True
        
        return False
