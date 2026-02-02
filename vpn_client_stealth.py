"""
VPN клиент со встроенным DPI bypass функционалом
Маскирует трафик и применяет техники избежания обнаружения
"""
import socket
import struct
import threading
import time
import logging
from crypto_engine import CryptoEngine, HandshakeProtocol
from obfuscation import TrafficObfuscator, DPIBypass

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Stealth_VPNClient:
    """VPN клиент со встроенной маскировкой и DPI bypass"""
    
    PACKET_TYPE_DATA = 0x10
    PACKET_TYPE_KEEPALIVE = 0x11
    PACKET_TYPE_DISCONNECT = 0x12
    
    BUFFER_SIZE = 4096
    TIMEOUT = 30
    KEEPALIVE_INTERVAL = 5
    
    def __init__(self, server_host, server_port, password='secure_password',
                 obfuscation_mode='https', enable_dpi_bypass=True):
        self.server_host = server_host
        self.server_port = server_port
        self.password = password
        self.socket = None
        self.running = False
        self.crypto = CryptoEngine()
        self.connected = False
        
        # Параметры скрытности
        self.obfuscation_mode = obfuscation_mode
        self.enable_dpi_bypass = enable_dpi_bypass
        self.obfuscator = TrafficObfuscator(mode=obfuscation_mode)
        self.dpi_bypass = DPIBypass() if enable_dpi_bypass else None
        
        # Статистика
        self.stats = {
            'packets_sent': 0,
            'packets_recv': 0,
            'bytes_sent': 0,
            'bytes_recv': 0,
            'connect_time': None
        }
    
    def connect(self):
        """Подключается к VPN серверу с маскировкой"""
        try:
            # Создать сокет
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.TIMEOUT)
            
            logger.info(f"Подключение к серверу {self.server_host}:{self.server_port}...")
            
            if self.enable_dpi_bypass:
                logger.info(f"Режим скрытности: {self.obfuscation_mode}")
                logger.info("DPI bypass активирован")
            
            self.socket.connect((self.server_host, self.server_port))
            self.stats['connect_time'] = time.time()
            
            # Выполнить рукопожатие со скрытностью
            if self._stealth_handshake():
                self.connected = True
                self.running = True
                logger.info("Успешно подключено к VPN серверу (скрытный режим)")
                
                # Запустить потоки
                recv_thread = threading.Thread(target=self._receive_data, daemon=True)
                keepalive_thread = threading.Thread(target=self._send_keepalive, daemon=True)
                
                recv_thread.start()
                keepalive_thread.start()
                
                return True
            else:
                logger.error("Ошибка при рукопожатии")
                self.socket.close()
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при подключении: {e}")
            if self.socket:
                self.socket.close()
            return False
    
    def _stealth_handshake(self):
        """Выполняет рукопожатие со скрытностью"""
        try:
            # Шаг 1: Отправить HELLO
            hello = struct.pack('!B', HandshakeProtocol.HANDSHAKE_VERSION)
            hello += struct.pack('!B', HandshakeProtocol.HANDSHAKE_HELLO)
            hello += b'\x00' * 8
            
            # Обфускировать если нужно
            if self.enable_dpi_bypass:
                hello_obfuscated = self.obfuscator.obfuscate_packet(hello)
                self.socket.sendall(struct.pack('!H', len(hello_obfuscated)) + hello_obfuscated)
            else:
                self.socket.sendall(hello)
            
            # Шаг 2: Получить ключ сервера
            if self.enable_dpi_bypass:
                # Читаем размер обфускированного пакета
                size_header = self.socket.recv(2)
                if len(size_header) < 2:
                    logger.error("Неверный ответ от сервера")
                    return False
                key_len = struct.unpack('!H', size_header)[0]
                
                # Читаем обфускированный пакет
                server_key_obfuscated = b''
                while len(server_key_obfuscated) < key_len:
                    chunk = self.socket.recv(min(self.BUFFER_SIZE, key_len - len(server_key_obfuscated)))
                    if not chunk:
                        return False
                    server_key_obfuscated += chunk
                server_key_packet = self.obfuscator.deobfuscate_packet(server_key_obfuscated)
            else:
                server_key_packet = self.socket.recv(self.BUFFER_SIZE)
            
            if len(server_key_packet) < 3:
                logger.error("Неверный ответ от сервера")
                return False
            
            server_key_len = struct.unpack('!H', server_key_packet[1:3])[0]
            server_public_key = server_key_packet[3:3+server_key_len]
            
            logger.debug(f"Получен ключ сервера ({len(server_public_key)} байт)")
            
            # Шаг 3: Отправить свой ключ
            client_public_key = self.crypto.generate_keypair()
            key_packet = struct.pack('!B', HandshakeProtocol.HANDSHAKE_KEY_EXCHANGE)
            key_packet += struct.pack('!H', len(client_public_key))
            key_packet += client_public_key
            
            if self.enable_dpi_bypass:
                key_obfuscated = self.obfuscator.obfuscate_packet(key_packet)
                self.socket.sendall(struct.pack('!H', len(key_obfuscated)) + key_obfuscated)
            else:
                self.socket.sendall(key_packet)
            
            # Шаг 4: Установить общий секрет
            self.crypto.establish_shared_secret(server_public_key, is_server=False)
            logger.debug("Общий секрет установлен")
            
            # Шаг 5: Получить аутентификацию
            if self.enable_dpi_bypass:
                # Читаем размер обфускированного пакета
                size_header = self.socket.recv(2)
                if len(size_header) < 2:
                    logger.error("Неверный пакет аутентификации")
                    return False
                auth_len = struct.unpack('!H', size_header)[0]
                logger.debug(f"Получен размер аутентификации: {auth_len} байт")
                
                # Читаем обфускированный пакет
                auth_obfuscated = b''
                while len(auth_obfuscated) < auth_len:
                    chunk = self.socket.recv(min(self.BUFFER_SIZE, auth_len - len(auth_obfuscated)))
                    if not chunk:
                        return False
                    auth_obfuscated += chunk
                auth_packet = self.obfuscator.deobfuscate_packet(auth_obfuscated)
                logger.debug(f"После деобфускации: {len(auth_packet)} байт")
            else:
                auth_packet = self.socket.recv(self.BUFFER_SIZE)
                logger.debug(f"Получен пакет аутентификации: {len(auth_packet)} байт")
            
            if len(auth_packet) < 2:
                logger.error("Неверный пакет аутентификации")
                return False
            
            # Проверить пароль
            salt = auth_packet[1:17]
            server_hash = auth_packet[17:33]
            
            logger.debug(f"Полученный пакет аутентификации: {len(auth_packet)} байт")
            logger.debug(f"Соль: {salt.hex()}")
            logger.debug(f"Хеш сервера: {server_hash.hex()}")
            
            client_hash, _ = self.crypto.hash_password(self.password, salt)
            logger.debug(f"Хеш клиента (полный): {client_hash.hex()}")
            logger.debug(f"Хеш клиента (первые 16): {client_hash[:16].hex()}")
            
            if client_hash[:16] != server_hash:
                logger.error(f"Неверный пароль (не совпадают хеши)")
                return False
            
            logger.debug("Аутентификация пройдена")
            
            # Шаг 6: Отправить подтверждение
            confirm = struct.pack('!B', HandshakeProtocol.HANDSHAKE_SUCCESS)
            
            if self.enable_dpi_bypass:
                confirm_obfuscated = self.obfuscator.obfuscate_packet(confirm)
                # Отправить размер + обфускированный пакет
                self.socket.sendall(struct.pack('!H', len(confirm_obfuscated)) + confirm_obfuscated)
            else:
                self.socket.sendall(confirm)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при рукопожатии: {e}")
            return False
    
    def send_data(self, data):
        """Отправляет данные через маскированный VPN туннель"""
        if not self.connected:
            logger.warning("Не подключено к VPN")
            return False
        
        try:
            counter, encrypted = self.crypto.encrypt(data)
            
            logger.debug(f"Шифрование: data_len={len(data)}, counter={counter}, encrypted_len={len(encrypted)}")
            
            packet = struct.pack('!B', self.PACKET_TYPE_DATA)
            packet += struct.pack('!I', counter)
            packet += struct.pack('!H', len(encrypted))
            packet += encrypted
            
            logger.debug(f"Пакет до обфускации: total_len={len(packet)}")
            
            # Обфускировать если нужно
            if self.enable_dpi_bypass:
                obfuscated = self.obfuscator.obfuscate_packet(packet)
                # Добавить размер обфускированного пакета перед ним
                final_packet = struct.pack('!H', len(obfuscated)) + obfuscated
                logger.debug(f"После обфускации: obfuscated_len={len(obfuscated)}, final_len={len(final_packet)}")
            else:
                final_packet = packet
            
            self.socket.sendall(final_packet)
            
            self.stats['packets_sent'] += 1
            self.stats['bytes_sent'] += len(packet)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке данных: {e}")
            self.connected = False
            return False
    
    def _send_keepalive(self):
        """Отправляет keep-alive пакеты со скрытностью"""
        while self.running:
            try:
                time.sleep(self.KEEPALIVE_INTERVAL)
                
                if not self.connected:
                    continue
                
                counter, encrypted = self.crypto.encrypt(b'ping')
                logger.debug(f"Keep-alive: counter={counter}, encrypted_len={len(encrypted)}")
                
                packet = struct.pack('!B', self.PACKET_TYPE_KEEPALIVE)
                packet += struct.pack('!I', counter)
                packet += struct.pack('!H', len(encrypted))
                packet += encrypted
                logger.debug(f"Keep-alive пакет: total_len={len(packet)}")
                
                if self.enable_dpi_bypass:
                    obfuscated = self.obfuscator.obfuscate_packet(packet)
                    final_packet = struct.pack('!H', len(obfuscated)) + obfuscated
                    logger.debug(f"После обфускации: obfuscated_len={len(obfuscated)}, final_len={len(final_packet)}")
                else:
                    final_packet = packet
                
                self.socket.sendall(final_packet)
                
                logger.debug("Keep-alive отправлен")
                self.stats['packets_sent'] += 1
                
            except Exception as e:
                logger.error(f"Ошибка при отправке keep-alive: {e}")
                self.connected = False
                break
    
    def _receive_data(self):
        """Получает данные со скрытностью"""
        while self.running:
            try:
                # Получить размер пакета если обфускация включена
                if self.enable_dpi_bypass:
                    size_header = self.socket.recv(2)
                    if len(size_header) < 2:
                        logger.info("Соединение закрыто сервером")
                        self.connected = False
                        break
                    
                    packet_len = struct.unpack('!H', size_header)[0]
                    
                    # Получить обфускированный пакет
                    obfuscated_packet = b''
                    while len(obfuscated_packet) < packet_len:
                        chunk = self.socket.recv(min(self.BUFFER_SIZE, packet_len - len(obfuscated_packet)))
                        if not chunk:
                            logger.info("Соединение закрыто сервером")
                            self.connected = False
                            break
                        obfuscated_packet += chunk
                    
                    # Деобфускировать
                    packet = self.obfuscator.deobfuscate_packet(obfuscated_packet)
                else:
                    # Получить заголовок без обфускации
                    header = self.socket.recv(7)
                    if len(header) < 7:
                        logger.info("Соединение закрыто сервером")
                        self.connected = False
                        break
                    packet = header
                
                if len(packet) < 7:
                    logger.info("Соединение закрыто сервером")
                    self.connected = False
                    break
                
                packet_type = packet[0]
                counter = struct.unpack('!I', packet[1:5])[0]
                data_len = struct.unpack('!H', packet[5:7])[0]
                
                if data_len > self.BUFFER_SIZE * 2:
                    logger.error("Пакет слишком большой")
                    break
                
                # Получить данные если есть ещё
                encrypted_data = packet[7:] if len(packet) > 7 else b''
                while len(encrypted_data) < data_len:
                    chunk = self.socket.recv(
                        min(self.BUFFER_SIZE, data_len - len(encrypted_data))
                    )
                    if not chunk:
                        break
                    encrypted_data += chunk
                
                # Расшифровать
                decrypted = self.crypto.decrypt(counter, encrypted_data)
                
                self.stats['packets_recv'] += 1
                self.stats['bytes_recv'] += len(encrypted_data)
                
                if packet_type == self.PACKET_TYPE_DATA:
                    logger.debug(f"Получены данные: {len(decrypted)} байт")
                    logger.info(f"Данные: {decrypted}")
                    
                elif packet_type == self.PACKET_TYPE_KEEPALIVE:
                    logger.debug(f"Keep-alive ответ: {decrypted.decode('utf-8', errors='ignore')}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Ошибка при получении данных: {e}")
                self.connected = False
                break
    
    def disconnect(self):
        """Отключается от сервера"""
        try:
            if self.connected and self.socket:
                disconnect_packet = struct.pack('!B', self.PACKET_TYPE_DISCONNECT)
                counter, encrypted = self.crypto.encrypt(b'disconnect')
                disconnect_packet += struct.pack('!I', counter)
                disconnect_packet += struct.pack('!H', len(encrypted))
                disconnect_packet += encrypted
                
                if self.enable_dpi_bypass:
                    disconnect_packet = self.obfuscator.obfuscate_packet(disconnect_packet)
                
                self.socket.sendall(disconnect_packet)
            
            self.running = False
            self.connected = False
            
            if self.socket:
                self.socket.close()
            
            logger.info("Отключено от VPN сервера")
            
        except Exception as e:
            logger.error(f"Ошибка при отключении: {e}")
    
    def send_message(self, message):
        """Отправляет текстовое сообщение"""
        return self.send_data(message.encode('utf-8'))
    
    def get_statistics(self):
        """Возвращает статистику соединения"""
        connection_time = 0
        if self.stats['connect_time']:
            connection_time = time.time() - self.stats['connect_time']
        
        return {
            'connected': self.connected,
            'obfuscation_mode': self.obfuscation_mode,
            'dpi_bypass_enabled': self.enable_dpi_bypass,
            'connection_time': connection_time,
            'packets_sent': self.stats['packets_sent'],
            'packets_recv': self.stats['packets_recv'],
            'bytes_sent': self.stats['bytes_sent'],
            'bytes_recv': self.stats['bytes_recv']
        }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        server_host = sys.argv[1]
        server_port = int(sys.argv[2]) if len(sys.argv) > 2 else 443
        password = sys.argv[3] if len(sys.argv) > 3 else 'secure_password'
        obfuscation = sys.argv[4] if len(sys.argv) > 4 else 'https'
    else:
        server_host = 'localhost'
        server_port = 443
        password = 'secure_password'
        obfuscation = 'https'
    
    client = Stealth_VPNClient(
        server_host,
        server_port,
        password=password,
        obfuscation_mode=obfuscation,
        enable_dpi_bypass=True
    )
    
    if client.connect():
        try:
            print("Подключено к VPN. Вводите сообщения (quit для выхода, stats для статистики):")
            while True:
                message = input("> ")
                if message.lower() == 'quit':
                    break
                elif message.lower() == 'stats':
                    stats = client.get_statistics()
                    print("\n=== Статистика соединения ===")
                    for key, value in stats.items():
                        print(f"{key}: {value}")
                    print()
                else:
                    client.send_message(message)
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nОтключение...")
        finally:
            client.disconnect()
    else:
        logger.error("Не удалось подключиться к VPN")
