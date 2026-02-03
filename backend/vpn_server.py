"""
VPN Сервер - основной компонент
Перенаправляет весь трафик клиентов в интернет через сервер
"""
import socket
import threading
import logging
import struct
import json
import time
import hmac
from typing import Dict, Tuple, Optional
import sys
import os

# Добавить путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.protocols import VPNProtocol, PacketType, ObfuscationMode
from shared.utils import hash_password, verify_password, RateLimiter
from backend.crypto_engine import CryptoEngine
from backend.traffic_router import TrafficRouter

logger = logging.getLogger(__name__)


class VPNServer:
    """Основной класс VPN сервера"""
    
    BUFFER_SIZE = 4096
    TIMEOUT = 30
    KEEPALIVE_INTERVAL = 20
    MAX_CLIENTS = 100
    
    def __init__(self, host: str = '0.0.0.0', port: int = 443, password: str = 'pass'):
        self.host = host
        self.port = port
        self.password = password
        self.password_hash, self.password_salt = hash_password(password)
        
        self.server_socket = None
        self.running = False
        self.clients: Dict[str, ClientHandler] = {}
        self.lock = threading.Lock()
        
        # Маршрутизатор трафика
        self.traffic_router = TrafficRouter()
        
        # Ограничитель частоты
        self.rate_limiter = RateLimiter(max_requests=100, time_window=60)
        
        logger.info(f"VPN Server инициализирован на {host}:{port}")
    
    def start(self):
        """Запустить VPN сервер"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            logger.info(f"🚀 VPN Server запущен на {self.host}:{self.port}")
            
            # Запустить поток для принятия подключений
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            
            # Запустить поток для мониторинга клиентов
            monitor_thread = threading.Thread(target=self._monitor_clients, daemon=True)
            monitor_thread.start()
            
            # Блокирующий вызов - сервер работает
            accept_thread.join()
            
        except Exception as e:
            logger.error(f"Ошибка при запуске сервера: {e}")
            self.stop()
    
    def stop(self):
        """Остановить VPN сервер"""
        self.running = False
        
        # Отключить всех клиентов
        with self.lock:
            for client_id in list(self.clients.keys()):
                try:
                    self.clients[client_id].disconnect()
                except:
                    pass
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        logger.info("VPN Server остановлен")
    
    def _accept_connections(self):
        """Принимать входящие подключения"""
        while self.running:
            try:
                client_socket, client_addr = self.server_socket.accept()
                
                # Проверить лимит клиентов
                with self.lock:
                    if len(self.clients) >= self.MAX_CLIENTS:
                        logger.warning(f"Максимум клиентов достигнут. Отклоняю {client_addr}")
                        client_socket.close()
                        continue
                
                # Проверить rate limiting
                client_ip = client_addr[0]
                if not self.rate_limiter.is_allowed(client_ip):
                    logger.warning(f"Rate limit превышен для {client_ip}")
                    client_socket.close()
                    continue
                
                logger.info(f"✓ Новое подключение от {client_addr}")
                
                # Создать обработчик клиента
                client_handler = ClientHandler(
                    client_socket,
                    client_addr,
                    self.password,
                    self.password_hash,
                    self.password_salt,
                    self.traffic_router,
                    self._on_client_disconnect
                )
                
                # Добавить клиента в список
                with self.lock:
                    self.clients[client_addr[0]] = client_handler
                
                # Запустить обработчик в отдельном потоке
                client_thread = threading.Thread(
                    target=client_handler.handle,
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"Ошибка при принятии подключения: {e}")
    
    def _monitor_clients(self):
        """Мониторить здоровье клиентов"""
        while self.running:
            try:
                time.sleep(self.KEEPALIVE_INTERVAL)
                
                with self.lock:
                    dead_clients = []
                    for client_id, handler in self.clients.items():
                        if not handler.is_alive():
                            dead_clients.append(client_id)
                    
                    for client_id in dead_clients:
                        logger.info(f"✗ Удаляю мертвого клиента {client_id}")
                        del self.clients[client_id]
                
            except Exception as e:
                logger.error(f"Ошибка при мониторинге: {e}")
    
    def _on_client_disconnect(self, client_addr: str):
        """Callback когда клиент отключается"""
        with self.lock:
            if client_addr in self.clients:
                del self.clients[client_addr]
                logger.info(f"Клиент {client_addr} отключен")


class ClientHandler:
    """Обработчик клиента"""
    
    def __init__(self, client_socket: socket.socket, client_addr: Tuple[str, int],
                 password: str, password_hash: bytes, password_salt: bytes,
                 traffic_router: 'TrafficRouter', on_disconnect_callback):
        self.client_socket = client_socket
        self.client_addr = client_addr
        self.client_ip = client_addr[0]
        self.client_id = f"{client_addr[0]}:{client_addr[1]}"
        
        self.password = password
        self.password_hash = password_hash
        self.password_salt = password_salt
        self.traffic_router = traffic_router
        self.on_disconnect_callback = on_disconnect_callback
        
        self.crypto = CryptoEngine()
        self.authenticated = False
        self.running = False
        
        # TUN интерфейс для этого клиента
        self.tun_interface = None
        
        logger.info(f"ClientHandler создан для {self.client_id}")
    
    def handle(self):
        """Основной цикл обработки клиента"""
        try:
            self.client_socket.settimeout(30)
            self.running = True
            
            # Этап 1: Рукопожатие
            if not self._handshake():
                logger.warning(f"Рукопожатие с {self.client_id} не удалось")
                return
            
            logger.info(f"✓ Рукопожатие успешно для {self.client_id}")
            
            # Этап 2: Аутентификация
            if not self._authenticate():
                logger.warning(f"Аутентификация {self.client_id} не удалась")
                return
            
            logger.info(f"✓ Аутентификация успешна для {self.client_id}")
            self.authenticated = True
            
            # Этап 3: Основной цикл трафика
            self._handle_traffic()
            
        except Exception as e:
            logger.error(f"Ошибка в ClientHandler: {e}")
        finally:
            self.disconnect()
    
    def _handshake(self) -> bool:
        """Рукопожатие с клиентом"""
        try:
            # Получить запрос рукопожатия
            data = self.client_socket.recv(1024)
            if not data:
                logger.debug("_handshake: Получены пустые данные")
                return False
            
            logger.debug(f"_handshake: Получены данные ({len(data)} байт): {data[:50].hex()}")
            
            header, payload = VPNProtocol.parse_packet(data)
            if header is None:
                logger.debug(f"_handshake: parse_packet вернул None")
                return False
            
            logger.debug(f"_handshake: packet_type={header.packet_type}, ожидается {PacketType.HANDSHAKE_REQUEST}")
            
            if header.packet_type != PacketType.HANDSHAKE_REQUEST:
                return False
            
            # Парсить запрос
            request_data = json.loads(payload.decode())
            logger.debug(f"Handshake request: {request_data}")
            
            # Генерировать пару ключей и выполнить ECDH
            server_public_key_raw = self.crypto.generate_keypair()
            
            # Отправить ответ
            response_data = json.dumps({
                'status': 'ok',
                'server_public_key': server_public_key_raw.hex(),
                'server_id': 'nexus_vpn_server_v1'
            }).encode()
            
            response_packet = VPNProtocol.create_packet(
                PacketType.HANDSHAKE_RESPONSE,
                response_data
            )
            self.client_socket.sendall(response_packet)
            
            # Получить ключ клиента
            client_key_data = self.client_socket.recv(1024)
            if not client_key_data:
                logger.debug("_handshake: Клиент не отправил ключ")
                return False
            
            header_client, payload_client = VPNProtocol.parse_packet(client_key_data)
            if header_client is None:
                logger.debug("_handshake: Ошибка парсинга ключа клиента")
                return False
            
            # Парсить ключ клиента
            client_key_response = json.loads(payload_client.decode())
            client_public_key = bytes.fromhex(client_key_response.get('client_public_key', ''))
            
            if not client_public_key:
                logger.debug("_handshake: Ключ клиента пуст")
                return False
            
            # Установить сессионный ключ на сервере
            self.crypto.derive_session_key(client_public_key, self.password.encode())
            
            logger.info(f"✓ Рукопожатие успешно для {self.client_addr[0]}:{self.client_addr[1]}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при рукопожатии: {e}")
            return False
    
    def _authenticate(self) -> bool:
        """Аутентификация клиента"""
        try:
            # Отправить вызов аутентификации
            challenge = os.urandom(32)
            challenge_packet = VPNProtocol.create_packet(
                PacketType.AUTH_CHALLENGE,
                challenge
            )
            logger.debug(f"_authenticate: Отправка challenge ({len(challenge_packet)} байт)")
            self.client_socket.sendall(challenge_packet)
            
            # Получить ответ
            data = self.client_socket.recv(1024)
            if not data:
                logger.debug("_authenticate: Получены пустые данные")
                return False
            
            logger.debug(f"_authenticate: Получены данные ({len(data)} байт): {data[:50].hex()}")
            header, payload = VPNProtocol.parse_packet(data)
            if header is None:
                logger.debug("_authenticate: parse_packet вернул None")
                return False
            
            logger.debug(f"_authenticate: packet_type={header.packet_type}, ожидается {PacketType.AUTH_RESPONSE}")
            if header.packet_type != PacketType.AUTH_RESPONSE:
                return False
            
            # Проверить пароль - payload содержит хеш пароля от клиента
            # payload это bytes, нужно сравнить с нашим хешем
            logger.debug(f"_authenticate: payload_len={len(payload)}, password_hash_len={len(self.password_hash)}")
            logger.debug(f"_authenticate: payload={payload.hex()}")
            logger.debug(f"_authenticate: password_hash={self.password_hash.hex()}")
            
            if not hmac.compare_digest(self.password_hash, payload):
                logger.debug("_authenticate: Хеш пароля не совпадает")
                return False
            
            logger.info(f"✓ Аутентификация успешна для {self.client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при аутентификации: {e}")
            return False
    
    def _handle_traffic(self):
        """Основной цикл обработки трафика"""
        logger.info(f"Начало обработки трафика для {self.client_id}")
        
        # Здесь должна быть маршрутизация трафика через TUN/TAP
        # Пока реализуем базовую версию с простой пересылкой
        
        while self.running:
            try:
                data = self.client_socket.recv(self.traffic_router.BUFFER_SIZE)
                
                if not data:
                    break
                
                # Парсить пакет
                header, payload = VPNProtocol.parse_packet(data)
                
                if header is None:
                    continue
                
                if header.packet_type == PacketType.DATA:
                    # Маршрутизировать данные
                    self.traffic_router.route_traffic(self.client_id, payload)
                
                elif header.packet_type == PacketType.KEEPALIVE:
                    # Ответить на keepalive
                    keepalive_response = VPNProtocol.create_keepalive()
                    self.client_socket.sendall(keepalive_response)
                
                elif header.packet_type == PacketType.DISCONNECT:
                    logger.info(f"Клиент {self.client_id} запросил отключение")
                    break
                
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Ошибка при обработке трафика: {e}")
                break
    
    def disconnect(self):
        """Отключить клиента"""
        self.running = False
        try:
            self.client_socket.close()
        except:
            pass
        
        self.on_disconnect_callback(self.client_ip)
    
    def is_alive(self) -> bool:
        """Проверить, жив ли клиент"""
        return self.running and self.authenticated


def main():
    """Точка входа для сервера"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NexusVPN Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host для слушания')
    parser.add_argument('--port', type=int, default=443, help='Port для слушания')
    parser.add_argument('--password', default='pass', help='Пароль')
    
    args = parser.parse_args()
    
    # Настроить логирование
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = VPNServer(host=args.host, port=args.port, password=args.password)
    
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Получено SIGINT, остановка сервера...")
        server.stop()


if __name__ == '__main__':
    main()
