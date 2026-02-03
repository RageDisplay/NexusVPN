"""
VPN Клиент - основной VPN логика
"""
import socket
import threading
import logging
import json
import os
import sys
import time
from typing import Callable, Optional

# Добавить путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.protocols import VPNProtocol, PacketType, ObfuscationMode
from shared.utils import hash_password
from backend.crypto_engine import CryptoEngine
from backend.obfuscation import TrafficObfuscator, DPIBypass
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)


class VPNClient:
    """VPN клиент"""
    
    BUFFER_SIZE = 4096
    TIMEOUT = 30
    KEEPALIVE_INTERVAL = 20
    
    def __init__(self, server_host: str, server_port: int, password: str,
                 obfuscation_mode: str = 'https',
                 on_connect_callback: Callable = None,
                 on_disconnect_callback: Callable = None):
        self.server_host = server_host
        self.server_port = server_port
        self.password = password
        self.obfuscation_mode = obfuscation_mode
        
        self.socket = None
        self.running = False
        self.connected = False
        self.authenticated = False
        
        self.crypto = CryptoEngine()
        self.obfuscator = TrafficObfuscator(mode=obfuscation_mode)
        self.dpi_bypass = DPIBypass()
        
        self.on_connect_callback = on_connect_callback
        self.on_disconnect_callback = on_disconnect_callback
        
        self.stats = {
            'bytes_sent': 0,
            'bytes_received': 0,
            'packets_sent': 0,
            'packets_received': 0,
            'connection_time': None,
            'latency': 0
        }
        
        logger.info(f"VPN Client инициализирован для {server_host}:{server_port}")
    
    def connect(self) -> bool:
        """Подключиться к VPN серверу"""
        try:
            logger.info(f"Подключение к {self.server_host}:{self.server_port}...")
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.TIMEOUT)
            
            # Подключиться
            self.socket.connect((self.server_host, self.server_port))
            self.stats['connection_time'] = time.time()
            
            logger.info("Сокет подключен")
            
            # Рукопожатие
            if not self._handshake():
                logger.error("Ошибка при рукопожатии")
                self.socket.close()
                return False
            
            logger.info("Рукопожатие успешно")
            
            # Аутентификация
            if not self._authenticate():
                logger.error("Ошибка при аутентификации")
                self.socket.close()
                return False
            
            logger.info("Аутентификация успешна")
            self.authenticated = True
            self.connected = True
            self.running = True
            
            # Запустить потоки
            recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
            keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
            
            recv_thread.start()
            keepalive_thread.start()
            
            if self.on_connect_callback:
                self.on_connect_callback()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при подключении: {e}")
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
            return False
    
    def disconnect(self):
        """Отключиться от VPN"""
        if not self.connected:
            return
        
        try:
            self.running = False
            
            # Отправить пакет отключения
            if self.socket:
                disconnect_packet = VPNProtocol.create_disconnect()
                self.socket.sendall(disconnect_packet)
            
            time.sleep(0.5)
            
            if self.socket:
                self.socket.close()
        except Exception as e:
            logger.error(f"Ошибка при отключении: {e}")
        finally:
            self.connected = False
            self.authenticated = False
            
            if self.on_disconnect_callback:
                self.on_disconnect_callback()
            
            logger.info("Отключено от VPN")
    
    def _handshake(self) -> bool:
        """Выполнить рукопожатие"""
        try:
            # Сначала генерируем свою пару ключей
            self.crypto.generate_keypair()
            
            # Отправить запрос рукопожатия
            handshake_request = VPNProtocol.create_handshake_request(
                client_id='windows_client_v1',
                obfuscation_mode=ObfuscationMode.HTTPS
            )
            logger.debug(f"_handshake: Отправка ({len(handshake_request)} байт): {handshake_request[:50].hex()}")
            self.socket.sendall(handshake_request)
            
            # Получить ответ
            data = self.socket.recv(1024)
            if not data:
                logger.debug("_handshake: Получены пустые данные от сервера")
                return False
            
            logger.debug(f"_handshake: Получены данные ({len(data)} байт): {data[:50].hex()}")
            header, payload = VPNProtocol.parse_packet(data)
            if header is None or header.packet_type != PacketType.HANDSHAKE_RESPONSE:
                return False
            
            # Парсить ответ
            response = json.loads(payload.decode())
            logger.debug(f"Handshake response: {response}")
            
            # Вывести сеансовый ключ
            server_public_key = bytes.fromhex(response['server_public_key'])
            self.crypto.derive_session_key(
                server_public_key,
                self.password
            )
            
            # Отправить свой публичный ключ серверу
            client_public_key_raw = self.crypto.public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            client_key_response = json.dumps({
                'client_public_key': client_public_key_raw.hex()
            }).encode()
            client_key_packet = VPNProtocol.create_packet(
                PacketType.HANDSHAKE_RESPONSE,
                client_key_response
            )
            self.socket.sendall(client_key_packet)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при рукопожатии: {e}")
            return False
    
    def _authenticate(self) -> bool:
        """Аутентифицироваться"""
        try:
            # Получить вызов аутентификации
            data = self.socket.recv(1024)
            if not data:
                logger.debug("_authenticate: Получены пустые данные")
                return False
            
            logger.debug(f"_authenticate: Получены данные ({len(data)} байт): {data[:50].hex()}")
            header, challenge = VPNProtocol.parse_packet(data)
            if header is None:
                logger.debug("_authenticate: parse_packet вернул None")
                return False
            
            logger.debug(f"_authenticate: packet_type={header.packet_type}, ожидается {PacketType.AUTH_CHALLENGE}")
            if header.packet_type != PacketType.AUTH_CHALLENGE:
                return False
            
            logger.debug(f"Received auth challenge: {len(challenge)} bytes")
            
            # Создать ответ с хешем пароля
            pwd_hash, salt = hash_password(self.password)
            logger.debug(f"_authenticate: pwd_hash_len={len(pwd_hash)}, pwd_hash={pwd_hash.hex()}")
            
            # Отправить ответ
            auth_response = VPNProtocol.create_auth_response(pwd_hash)
            logger.debug(f"_authenticate: Отправка ({len(auth_response)} байт): {auth_response[:50].hex()}")
            self.socket.sendall(auth_response)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при аутентификации: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _receive_loop(self):
        """Основной цикл получения данных"""
        while self.running:
            try:
                data = self.socket.recv(self.BUFFER_SIZE)
                
                if not data:
                    logger.warning("Соединение закрыто сервером")
                    self.running = False
                    break
                
                header, payload = VPNProtocol.parse_packet(data)
                
                if header is None:
                    continue
                
                if header.packet_type == PacketType.DATA:
                    self.stats['packets_received'] += 1
                    self.stats['bytes_received'] += len(payload)
                
                elif header.packet_type == PacketType.KEEPALIVE:
                    # Ответить на keepalive
                    keepalive_response = VPNProtocol.create_keepalive()
                    self.socket.sendall(keepalive_response)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Ошибка при получении данных: {e}")
                break
    
    def _keepalive_loop(self):
        """Периодическая отправка keepalive"""
        while self.running:
            try:
                time.sleep(self.KEEPALIVE_INTERVAL)
                
                if self.running and self.socket:
                    keepalive = VPNProtocol.create_keepalive()
                    self.socket.sendall(keepalive)
                    
            except Exception as e:
                logger.error(f"Ошибка при отправке keepalive: {e}")
    
    def send_data(self, data: bytes) -> bool:
        """Отправить данные через VPN"""
        if not self.connected or not self.socket:
            return False
        
        try:
            packet = VPNProtocol.create_packet(PacketType.DATA, data)
            self.socket.sendall(packet)
            
            self.stats['packets_sent'] += 1
            self.stats['bytes_sent'] += len(data)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке данных: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Получить статистику подключения"""
        return self.stats.copy()
    
    def is_connected(self) -> bool:
        """Проверить, подключены ли"""
        return self.connected and self.authenticated
