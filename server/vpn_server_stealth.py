"""
VPN сервер со встроенным DPI bypass функционалом
Маскирует трафик под обычный HTTPS/HTTP и применяет другие техники избежания обнаружения
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import struct
import threading
import time
import logging
from engine.crypto_engine import CryptoEngine, HandshakeProtocol
from engine.obfuscation import TrafficObfuscator, DPIBypass, PacketSizeHider

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Stealth_VPNServer:
    """VPN сервер с поддержкой маскировки трафика и DPI bypass"""
    
    PACKET_TYPE_DATA = 0x10
    PACKET_TYPE_KEEPALIVE = 0x11
    PACKET_TYPE_DISCONNECT = 0x12
    
    BUFFER_SIZE = 4096
    TIMEOUT = 30
    
    def __init__(self, host='0.0.0.0', port=443, password='secure_password', 
                 obfuscation_mode='https', enable_dpi_bypass=True):
        self.host = host
        self.port = port
        self.password = password
        self.server_socket = None
        self.clients = {}
        self.running = False
        self.lock = threading.Lock()
        self.crypto = CryptoEngine()
        self.crypto.generate_keypair()
        
        # Параметры скрытности
        self.obfuscation_mode = obfuscation_mode
        self.enable_dpi_bypass = enable_dpi_bypass
        self.obfuscator = TrafficObfuscator(mode=obfuscation_mode)
        self.dpi_bypass = DPIBypass() if enable_dpi_bypass else None
    
    def start(self):
        """Запускает VPN сервер со скрытностью"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # На портах 443 (HTTPS) или 80 (HTTP) сервер выглядит как обычный веб-сервер
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        protocol_name = "HTTPS" if self.port == 443 else "HTTP"
        logger.info(f"VPN сервер (маскировка под {protocol_name}) запущен на {self.host}:{self.port}")
        
        if self.enable_dpi_bypass:
            logger.info(f"Режим скрытности: {self.obfuscation_mode}")
            logger.info("DPI bypass активирован")
        
        while self.running:
            try:
                client_socket, client_addr = self.server_socket.accept()
                logger.info(f"Новое подключение от {client_addr}")
                
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_addr),
                    daemon=True
                )
                client_thread.start()
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Ошибка при принятии подключения: {e}")
        
        self.stop()
    
    def handle_client(self, client_socket, client_addr):
        """Обрабатывает клиентское подключение с поддержкой скрытности"""
        try:
            client_socket.settimeout(self.TIMEOUT)
            
            # Шаг 1: Рукопожатие с маскировкой
            result = self._stealth_handshake(client_socket, client_addr)
            if not result or result is True:
                return
            
            # Распаковать результат
            _, server_crypto = result
            
            # Шаг 2: Установка криптографической сессии
            client_id = f"{client_addr[0]}:{client_addr[1]}"
            
            with self.lock:
                self.clients[client_id] = {
                    'socket': client_socket,
                    'crypto': server_crypto,
                    'obfuscator': TrafficObfuscator(mode=self.obfuscation_mode),
                    'created': time.time(),
                    'last_activity': time.time(),
                    'packets_sent': 0,
                    'packets_recv': 0,
                    'bytes_hidden': 0
                }
            
            logger.info(f"Клиент {client_id} аутентифицирован (скрытный режим: {self.enable_dpi_bypass})")
            
            # Шаг 3: Основной цикл обработки зашифрованных данных
            self._handle_stealth_data_exchange(client_socket, client_id)
            
        except socket.timeout:
            logger.debug(f"Тайм-аут соединения с {client_addr}")
        except Exception as e:
            logger.error(f"Ошибка при обработке клиента {client_addr}: {e}")
        finally:
            client_socket.close()
            if 'client_id' in locals():
                with self.lock:
                    if client_id in self.clients:
                        del self.clients[client_id]
                        logger.info(f"Клиент {client_id} отключен")
    
    def _stealth_handshake(self, client_socket, client_addr):
        """Выполняет рукопожатие с маскировкой под обычный HTTPS трафик"""
        try:
            # Получить пакет от клиента
            if self.enable_dpi_bypass:
                # Читаем размер обфускированного пакета
                size_header = client_socket.recv(2)
                if len(size_header) < 2:
                    logger.warning(f"Неверный начальный пакет от {client_addr}")
                    self._send_fake_https_response(client_socket)
                    return False
                
                hello_len = struct.unpack('!H', size_header)[0]
                
                # Читаем обфускированный пакет
                hello_obfuscated = b''
                while len(hello_obfuscated) < hello_len:
                    chunk = client_socket.recv(min(4096, hello_len - len(hello_obfuscated)))
                    if not chunk:
                        self._send_fake_https_response(client_socket)
                        return False
                    hello_obfuscated += chunk
                
                # Деобфускируем
                try:
                    initial_packet = self.obfuscator.deobfuscate_packet(hello_obfuscated)
                except:
                    self._send_fake_https_response(client_socket)
                    return False
            else:
                initial_packet = client_socket.recv(self.BUFFER_SIZE)
            
            if len(initial_packet) < 2:
                logger.warning(f"Неверный начальный пакет от {client_addr}")
                self._send_fake_https_response(client_socket)
                return False
            
            # Проверить, это VPN пакет или фиктивный трафик
            version = initial_packet[0]
            packet_type = initial_packet[1] if len(initial_packet) > 1 else 0
            
            if version != HandshakeProtocol.HANDSHAKE_VERSION:
                logger.warning(f"Неверная версия протокола от {client_addr}")
                self._send_fake_https_response(client_socket)
                return False
            
            if packet_type == HandshakeProtocol.HANDSHAKE_HELLO:
                # Это VPN рукопожатие
                logger.debug(f"VPN рукопожатие от {client_addr}")
                result = self._perform_vpn_handshake(client_socket, client_addr)
                return result
            else:
                # Это может быть обычный браузер - отправить фиктивный ответ
                self._send_fake_https_response(client_socket)
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при рукопожатии со скрытностью с {client_addr}: {e}")
            try:
                self._send_fake_https_response(client_socket)
            except:
                pass
            return False
    
    def _perform_vpn_handshake(self, client_socket, client_addr):
        """Выполняет обычное VPN рукопожатие"""
        try:
            # Отправить ключ сервера с маскировкой
            server_crypto = CryptoEngine()
            server_public_key = server_crypto.generate_keypair()
            
            # Обфускировать ключ в TLS фрейм
            key_packet = struct.pack('!B', HandshakeProtocol.HANDSHAKE_KEY_EXCHANGE)
            key_packet += struct.pack('!H', len(server_public_key))
            key_packet += server_public_key
            
            if self.enable_dpi_bypass:
                obfuscated_key = self.obfuscator.obfuscate_packet(key_packet)
                client_socket.sendall(struct.pack('!H', len(obfuscated_key)) + obfuscated_key)
            else:
                client_socket.sendall(key_packet)
            
            # Получить ключ клиента (тоже может быть обфускирован)
            if self.enable_dpi_bypass:
                # Читаем размер обфускированного пакета
                size_header = client_socket.recv(2)
                if len(size_header) < 2:
                    return False
                response_len = struct.unpack('!H', size_header)[0]
                
                # Читаем обфускированный пакет
                response_obfuscated = b''
                while len(response_obfuscated) < response_len:
                    chunk = client_socket.recv(min(4096, response_len - len(response_obfuscated)))
                    if not chunk:
                        return False
                    response_obfuscated += chunk
                response = self.obfuscator.deobfuscate_packet(response_obfuscated)
            else:
                response = client_socket.recv(self.BUFFER_SIZE)
            
            if len(response) < 3:
                return False
            
            client_public_key = response[3:3+32]
            server_crypto.establish_shared_secret(client_public_key, is_server=True)
            
            # Аутентификация
            password_hash, salt = server_crypto.hash_password(self.password)
            logger.debug(f"Пароль хеширован: соль={salt.hex()}, хеш={password_hash.hex()}")
            
            auth_packet = struct.pack('!B', HandshakeProtocol.HANDSHAKE_AUTH)
            auth_packet += salt
            auth_packet += password_hash[:16]
            logger.debug(f"Отправка аутентификации: {len(auth_packet)} байт")
            
            if self.enable_dpi_bypass:
                obfuscated_auth = self.obfuscator.obfuscate_packet(auth_packet)
                client_socket.sendall(struct.pack('!H', len(obfuscated_auth)) + obfuscated_auth)
            else:
                client_socket.sendall(auth_packet)
            
            # Подтверждение - читаем с размером если обфускация включена
            if self.enable_dpi_bypass:
                # Читаем размер обфускированного пакета
                size_header = client_socket.recv(2)
                if len(size_header) < 2:
                    return False
                confirm_len = struct.unpack('!H', size_header)[0]
                
                # Читаем обфускированное подтверждение
                confirm_obfuscated = b''
                while len(confirm_obfuscated) < confirm_len:
                    chunk = client_socket.recv(min(4096, confirm_len - len(confirm_obfuscated)))
                    if not chunk:
                        return False
                    confirm_obfuscated += chunk
                
                confirm = self.obfuscator.deobfuscate_packet(confirm_obfuscated)
            else:
                confirm = client_socket.recv(10)
            
            if len(confirm) < 1 or confirm[0] != HandshakeProtocol.HANDSHAKE_SUCCESS:
                return False
            
            # Сохранить криптографический объект
            client_id = f"{client_addr[0]}:{client_addr[1]}"
            with self.lock:
                if client_id not in self.clients:
                    self.clients[client_id] = {}
                self.clients[client_id]['crypto'] = server_crypto
            
            logger.info(f"Рукопожатие со скрытностью с {client_addr} успешно")
            return True, server_crypto
            
        except Exception as e:
            logger.error(f"Ошибка при VPN рукопожатии: {e}")
            return False
    
    def _send_fake_https_response(self, client_socket):
        """Отправляет фиктивный HTTPS ответ обычному браузеру"""
        try:
            # Простой TLS alert
            fake_response = b'\x15\x03\x03\x00\x02\x02\x00'  # TLS Оповещение: ошибка рукопожатия
            client_socket.sendall(fake_response)
        except:
            pass
    
    def _handle_stealth_data_exchange(self, client_socket, client_id):
        """Обрабатывает обмен данными с поддержкой маскировки"""
        while self.running:
            try:
                # Получить размер пакета
                if self.enable_dpi_bypass:
                    # Читаем размер обфускированного пакета
                    size_header = client_socket.recv(2)
                    if len(size_header) < 2:
                        break
                    obfuscated_len = struct.unpack('!H', size_header)[0]
                    
                    if obfuscated_len > self.BUFFER_SIZE * 4:
                        logger.warning(f"Пакет слишком большой от {client_id}")
                        break
                    
                    # Получить обфускированный пакет
                    obfuscated_data = b''
                    while len(obfuscated_data) < obfuscated_len:
                        chunk = client_socket.recv(min(self.BUFFER_SIZE, obfuscated_len - len(obfuscated_data)))
                        if not chunk:
                            break
                        obfuscated_data += chunk
                    
                    # Деобфускировать
                    with self.lock:
                        if client_id not in self.clients:
                            break
                        obfuscator = self.clients[client_id]['obfuscator']
                    
                    packet = obfuscator.deobfuscate_packet(obfuscated_data)
                else:
                    # Без обфускации читаем заголовок напрямую
                    header = client_socket.recv(7)
                    if len(header) < 7:
                        break
                    packet = header
                
                if len(packet) < 7:
                    logger.debug(f"Пакет слишком мал: {len(packet)} байт")
                    break
                
                packet_type = packet[0]
                counter = struct.unpack('!I', packet[1:5])[0]
                data_len = struct.unpack('!H', packet[5:7])[0]
                
                logger.debug(f"Распакован пакет: type={packet_type}, counter={counter}, data_len={data_len}, total_packet_len={len(packet)}")
                
                if data_len > self.BUFFER_SIZE * 2:
                    logger.warning(f"Пакет слишком большой от {client_id}")
                    break
                
                # Получить зашифрованные данные если нужно
                encrypted_data = packet[7:] if len(packet) > 7 else b''
                while len(encrypted_data) < data_len:
                    chunk = client_socket.recv(min(self.BUFFER_SIZE, data_len - len(encrypted_data)))
                    if not chunk:
                        break
                    encrypted_data += chunk
                
                with self.lock:
                    if client_id not in self.clients:
                        break
                    
                    client_info = self.clients[client_id]
                    client_info['last_activity'] = time.time()
                    client_info['packets_recv'] += 1
                    crypto = client_info['crypto']
                
                # Расшифровать
                try:
                    logger.debug(f"Расшифровка: counter={counter}, encrypted_len={len(encrypted_data)}, packet_type={packet_type}")
                    decrypted = crypto.decrypt(counter, encrypted_data)
                    logger.debug(f"Расшифровка успешна: {len(decrypted)} байт")
                except Exception as e:
                    logger.error(f"Ошибка расшифровки от {client_id}: {type(e).__name__}: {str(e)}")
                    logger.error(f"Данные: counter={counter}, encrypted_data_len={len(encrypted_data)}")
                    logger.error(f"Данные (hex): {encrypted_data[:50].hex()}")
                    break
                
                # Обработать пакет
                if packet_type == self.PACKET_TYPE_DATA:
                    logger.debug(f"Получены данные от {client_id}: {len(decrypted)} байт")
                    
                    with self.lock:
                        if client_id in self.clients:
                            self.clients[client_id]['bytes_hidden'] += len(decrypted)
                    
                elif packet_type == self.PACKET_TYPE_KEEPALIVE:
                    logger.debug(f"Keep-alive от {client_id}")
                    
                    # Отправить keep-alive ответ
                    response = struct.pack('!B', self.PACKET_TYPE_KEEPALIVE)
                    counter_resp, encrypted_resp = crypto.encrypt(b'pong')
                    response += struct.pack('!I', counter_resp)
                    response += struct.pack('!H', len(encrypted_resp))
                    response += encrypted_resp
                    
                    # Обфускировать если нужно
                    if self.enable_dpi_bypass:
                        obfuscated_resp = obfuscator.obfuscate_packet(response)
                        response = struct.pack('!H', len(obfuscated_resp)) + obfuscated_resp
                    
                    with self.lock:
                        if client_id in self.clients:
                            self.clients[client_id]['packets_sent'] += 1
                    
                    try:
                        client_socket.sendall(response)
                    except:
                        break
                    
                elif packet_type == self.PACKET_TYPE_DISCONNECT:
                    logger.info(f"Клиент {client_id} инициировал отключение")
                    break
                    
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Ошибка при обмене данными с {client_id}: {e}")
                break
    
    def stop(self):
        """Остановить сервер"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("VPN сервер остановлен")
    
    def get_stealth_stats(self):
        """Возвращает статистику скрытности"""
        with self.lock:
            return {
                'active_clients': len(self.clients),
                'obfuscation_mode': self.obfuscation_mode,
                'dpi_bypass_enabled': self.enable_dpi_bypass,
                'clients': {
                    client_id: {
                        'created': client['created'],
                        'packets_sent': client['packets_sent'],
                        'packets_recv': client['packets_recv'],
                        'bytes_hidden': client.get('bytes_hidden', 0)
                    }
                    for client_id, client in self.clients.items()
                }
            }


if __name__ == '__main__':
    import sys
    
    # Параметры по умолчанию
    port = 443  # HTTPS
    password = 'secure_password'
    obfuscation = 'https'
    
    # Парсить аргументы
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        password = sys.argv[2]
    if len(sys.argv) > 3:
        obfuscation = sys.argv[3]
    
    # Запустить сервер
    server = Stealth_VPNServer(
        host='0.0.0.0',
        port=port,
        password=password,
        obfuscation_mode=obfuscation,
        enable_dpi_bypass=True
    )
    
    # Поток для вывода статистики
    def print_stats():
        while server.running:
            time.sleep(30)
            stats = server.get_stealth_stats()
            logger.info(f"Активных клиентов: {stats['active_clients']} | "
                       f"Режим: {stats['obfuscation_mode']} | "
                       f"DPI bypass: {'Включён' if stats['dpi_bypass_enabled'] else 'Отключён'}")
    
    stats_thread = threading.Thread(target=print_stats, daemon=True)
    stats_thread.start()
    
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Остановка сервера...")
