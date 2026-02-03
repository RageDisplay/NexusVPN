"""
Модуль обфускации и маскировки трафика для избежания обнаружения DPI
Имитирует обычный HTTPS/HTTP трафик, добавляет padding и рандомизщацию размеров пакетов
для обхода анализа паттернов трафика.
"""
import os
import struct
import random
import hashlib
import time
from typing import Tuple, List
import string


class TrafficObfuscator:
    """Основной класс для обфускации трафика VPN"""
    
    # Режимы обфускации
    MODE_HTTPS = 'https'
    MODE_HTTP2 = 'http2'
    MODE_WEBSOCKET = 'websocket'
    MODE_RANDOM = 'random'
    
    # Размеры пакетов для маскировки
    COMMON_PACKET_SIZES = [
        64, 128, 256, 512, 1024, 1448, 1500, 2048, 4096, 8192
    ]
    
    # Пользовательский агент для имитации браузеров
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)',
        'Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36',
    ]
    
    def __init__(self, mode=MODE_HTTPS):
        self.mode = mode
        self.packet_counter = 0
        self.session_id = os.urandom(32)
        self.last_packet_time = time.time()
        self.traffic_pattern = []
    
    def obfuscate_packet(self, data: bytes, additional_data: bytes = b'') -> bytes:
        """
        Обфускирует пакет VPN, маскируя его под обычный трафик
        
        Args:
            data: Данные VPN пакета
            additional_data: Дополнительные данные (например, заголовки)
        
        Returns:
            Обфускированный пакет, который выглядит как обычный трафик
        """
        self.packet_counter += 1
        
        if self.mode == self.MODE_HTTPS:
            return self._obfuscate_https(data)
        elif self.mode == self.MODE_HTTP2:
            return self._obfuscate_http2(data)
        elif self.mode == self.MODE_WEBSOCKET:
            return self._obfuscate_websocket(data)
        else:
            return self._obfuscate_random(data)
    
    def deobfuscate_packet(self, packet: bytes) -> bytes:
        """
        Деобфускирует пакет, восстанавливая оригинальные VPN данные
        
        Args:
            packet: Обфускированный пакет
        
        Returns:
            Оригинальные VPN данные
        """
        if self.mode == self.MODE_HTTPS:
            return self._deobfuscate_https(packet)
        elif self.mode == self.MODE_HTTP2:
            return self._deobfuscate_http2(packet)
        elif self.mode == self.MODE_WEBSOCKET:
            return self._deobfuscate_websocket(packet)
        else:
            return self._deobfuscate_random(packet)
    
    def _obfuscate_https(self, data: bytes) -> bytes:
        """Маскирует данные под HTTPS трафик (TLS Record)"""
        # TLS Record Layer формат
        content_type = b'\x17'  # Данные приложения
        tls_version = b'\x03\x03'  # TLS 1.2
        
        # Сохраним оригинальный размер в первые 2 байта
        original_size = struct.pack('>H', len(data))
        
        # Добавить случайное заполнение для скрытия размера данных
        padding_size = random.randint(0, 128)
        padding = os.urandom(padding_size)
        
        payload = original_size + data + padding
        
        # TLS заголовок фрейма
        frame_header = content_type + tls_version + struct.pack('>H', len(payload))
        
        return frame_header + payload
    
    def _deobfuscate_https(self, packet: bytes) -> bytes:
        """Восстанавливает данные из HTTPS маскировки"""
        if len(packet) < 7:  # 5 байт заголовок + 2 байта размер
            return b''
        
        # TLS заголовок фрейма
        tls_length = struct.unpack('>H', packet[3:5])[0]
        
        # Извлечь полезную нагрузку
        if len(packet) < 5 + tls_length:
            return b''
        
        payload = packet[5:5+tls_length]
        
        # Извлечь оригинальный размер из первых 2 байт полезной нагрузки
        if len(payload) < 2:
            return b''
        
        original_size = struct.unpack('>H', payload[0:2])[0]
        
        # Извлечь оригинальные данные (без заполнения)
        if len(payload) < 2 + original_size:
            return b''
        
        return payload[2:2+original_size]
    
    def _obfuscate_http2(self, data: bytes) -> bytes:
        """Маскирует данные под HTTP/2 фрейм"""
        # Формат HTTP/2 фрейма
        # 3 байта длины + 1 байт тип + 1 байт флаги + 4 байта ID потока
        
        # Сохраним оригинальный размер в первые 2 байта
        original_size = struct.pack('>H', len(data))
        
        # Добавить заполнение для маскировки размера
        padding_size = random.randint(0, 256)
        padding = b'\x00' * padding_size
        payload = original_size + data + padding
        
        # Ограничить размер фрейма (HTTP/2 максимум 16KB)
        chunk_size = min(len(payload), 16384)
        payload = payload[:chunk_size]
        
        # Заголовок HTTP/2 фрейма
        # 3 байта для длины в big-endian формате
        length = len(payload).to_bytes(3, 'big')
        frame_type = b'\x00'  # фрейм ДАННЫХ
        flags = b'\x00'
        stream_id = struct.pack('>I', random.randint(1, 0x7FFFFFFF))
        
        frame_header = length + frame_type + flags + stream_id
        
        return frame_header + payload
    
    def _deobfuscate_http2(self, packet: bytes) -> bytes:
        """Восстанавливает данные из HTTP/2 маскировки"""
        if len(packet) < 11:  # 9 заголовок + 2 размер
            return b''
        
        # Извлечь длину из заголовка (3 байта)
        length = int.from_bytes(packet[0:3], 'big')
        
        # Извлечь payload
        if len(packet) < 9 + length:
            return b''
        
        payload = packet[9:9+length]
        
        # Извлечь оригинальный размер из первых 2 байт полезной нагрузки
        if len(payload) < 2:
            return b''
        
        original_size = struct.unpack('>H', payload[0:2])[0]
        
        # Извлечь оригинальные данные (без padding)
        if len(payload) < 2 + original_size:
            return b''
        
        return payload[2:2+original_size]
    
    def _obfuscate_websocket(self, data: bytes) -> bytes:
        """Маскирует данные под WebSocket фрейм"""
        # Формат WebSocket фрейма
        # FIN + RSV + опкод (1 байт) + МАСКА + длина полезной нагрузки + ключ маски + полезная нагрузка
        
        # Сохраним оригинальный размер в первые 2 байта
        original_size = struct.pack('>H', len(data))
        
        # Случайная маска для XOR
        mask_key = os.urandom(4)
        
        # Подготовить данные с размером
        data_with_size = original_size + data
        
        # Замаскировать данные
        masked_data = bytearray()
        for i, byte in enumerate(data_with_size):
            masked_data.append(byte ^ mask_key[i % 4])
        
        # Добавить padding
        padding = os.urandom(random.randint(0, 64))
        masked_data.extend(padding)
        
        # Заголовок WebSocket фрейма
        fin_opcode = b'\x81'  # FIN + текстовый фрейм
        
        payload_len = len(masked_data)
        if payload_len < 126:
            length_byte = struct.pack('!B', 0x80 | payload_len)  # МАСКА=1
        elif payload_len < 65536:
            length_byte = b'\xfe' + struct.pack('!H', payload_len)
        else:
            length_byte = b'\xff' + struct.pack('!Q', payload_len)
        
        frame = fin_opcode + length_byte + mask_key + bytes(masked_data)
        
        return frame
    
    def _deobfuscate_websocket(self, packet: bytes) -> bytes:
        """Восстанавливает данные из WebSocket маскировки"""
        if len(packet) < 2:
            return b''
        
        # Извлечь длину полезной нагрузки
        payload_len_byte = packet[1]
        has_mask = (payload_len_byte & 0x80) != 0
        payload_len = payload_len_byte & 0x7f
        
        if payload_len == 126:
            if len(packet) < 4:
                return b''
            payload_len = struct.unpack('!H', packet[2:4])[0]
            offset = 4
        elif payload_len == 127:
            if len(packet) < 10:
                return b''
            payload_len = struct.unpack('!Q', packet[2:10])[0]
            offset = 10
        else:
            offset = 2
        
        # Извлечь маску и данные
        if has_mask:
            if len(packet) < offset + 4 + payload_len:
                return b''
            mask_key = packet[offset:offset+4]
            masked_data = packet[offset+4:offset+4+payload_len]
            
            # Разма́скировать
            data = bytearray()
            for i, byte in enumerate(masked_data):
                data.append(byte ^ mask_key[i % 4])
            
            # Извлечь оригинальный размер и данные
            if len(data) < 2:
                return b''
            
            original_size = struct.unpack('>H', bytes(data[0:2]))[0]
            if len(data) < 2 + original_size:
                return b''
            
            return bytes(data[2:2+original_size])
        
        return packet[offset:offset+payload_len]
    
    def _obfuscate_random(self, data: bytes) -> bytes:
        """Применяет случайную обфускацию"""
        # Сохраним оригинальный размер в первые 2 байта
        original_size = struct.pack('>H', len(data))
        
        # Добавить случайное количество padding
        padding_size = random.randint(16, 512)
        padding = os.urandom(padding_size)
        
        # Случайно расположить данные и padding
        result = original_size + data + padding
        return result
    
    def _deobfuscate_random(self, packet: bytes) -> bytes:
        """Восстанавливает данные из случайной маскировки"""
        if len(packet) < 2:
            return b''
        
        # Извлечь оригинальный размер из первых 2 байт
        original_size = struct.unpack('>H', packet[0:2])[0]
        
        if len(packet) < 2 + original_size:
            return b''
        
        return packet[2:2+original_size]
    
    def _generate_tls_noise(self) -> bytes:
        """Генерирует фиктивный TLS трафик"""
        # Имитация различных TLS record типов
        noise = b''
        num_records = random.randint(1, 3)
        
        for _ in range(num_records):
            record_type = random.choice([b'\x16', b'\x18', b'\x19'])  # Рукопожатие, Пульс, Произвольный
            tls_version = b'\x03\x03'
            length = struct.pack('>H', random.randint(100, 500))
            record_data = os.urandom(random.randint(50, 400))
            noise += record_type + tls_version + length + record_data
        
        return noise
    
    def _generate_fake_http2_frames(self) -> bytes:
        """Генерирует фиктивные HTTP/2 фреймы"""
        frames = b''
        num_frames = random.randint(0, 2)
        
        for _ in range(num_frames):
            length = struct.pack('>I', random.randint(10, 100))[:3]
            frame_type = random.choice([b'\x00', b'\x01', b'\x04', b'\x08'])  # ДАННЫЕ, ЗАГОЛОВКИ, СБРОС, ОКНО
            flags = b'\x00'
            stream_id = struct.pack('>I', random.randint(1, 0x7FFFFFFF))
            payload = os.urandom(random.randint(10, 100))
            frames += length + frame_type + flags + stream_id + payload
        
        return frames
    
    def _generate_fake_websocket_frames(self) -> bytes:
        """Генерирует фиктивные WebSocket фреймы"""
        frames = b''
        num_frames = random.randint(0, 2)
        
        for _ in range(num_frames):
            # Случайный фрейм
            fin_opcode = random.choice([b'\x81', b'\x82', b'\x89', b'\x8a'])  # текст, бинарные, пинг, понг
            payload = os.urandom(random.randint(10, 64))
            payload_len = len(payload)
            
            if payload_len < 126:
                length_byte = struct.pack('!B', 0x00 | payload_len)  # нет маски для фреймов сервера
            else:
                length_byte = b'\x7e' + struct.pack('!H', payload_len)
            
            frames += fin_opcode + length_byte + payload
        
        return frames


class PacketSizeHider:
    """Скрывает размеры пакетов для обхода анализа паттернов трафика"""
    
    def __init__(self, min_padding=16, max_padding=512):
        self.min_padding = min_padding
        self.max_padding = max_padding
        self.packet_history = []
    
    def add_padding(self, packet: bytes) -> Tuple[bytes, int]:
        """
        Добавляет случайный padding к пакету
        
        Returns:
            (padded_packet, padding_size)
        """
        padding_size = random.randint(self.min_padding, self.max_padding)
        padding = os.urandom(padding_size)
        
        padded = packet + padding
        self.packet_history.append({
            'size': len(packet),
            'padded_size': len(padded),
            'time': time.time()
        })
        
        return padded, padding_size
    
    def remove_padding(self, padded_packet: bytes, padding_size: int) -> bytes:
        """
        Удаляет padding из пакета (требует знания размера padding)
        """
        if len(padded_packet) >= padding_size:
            return padded_packet[:-padding_size]
        return padded_packet
    
    def randomize_packet_timing(self, base_delay: float = 0.01) -> float:
        """
        Генерирует случайную задержку между пакетами
        для маскировки паттернов передачи
        """
        jitter = random.uniform(0, base_delay * 2)
        return base_delay + jitter
    
    def get_traffic_pattern(self) -> dict:
        """Анализирует паттерны трафика"""
        if not self.packet_history:
            return {}
        
        sizes = [p['size'] for p in self.packet_history]
        padded_sizes = [p['padded_size'] for p in self.packet_history]
        
        return {
            'avg_packet_size': sum(sizes) / len(sizes),
            'avg_padded_size': sum(padded_sizes) / len(padded_sizes),
            'min_size': min(sizes),
            'max_size': max(sizes),
            'total_packets': len(self.packet_history),
            'overhead': sum(padded_sizes) - sum(sizes)
        }


class TLSFingerprint:
    """Имитирует TLS fingerprint реальных браузеров для обхода DPI"""
    
    # Реальные TLS параметры браузеров
    BROWSER_PROFILES = {
        'chrome': {
            'supported_versions': [0x0304, 0x0303, 0x0302],  # TLS 1.3, 1.2, 1.1
            'cipher_suites': [
                0x1301, 0x1302, 0x1303,  # Шифры TLS 1.3
                0x002f, 0x0035, 0x003c, 0x002b  # Шифры TLS 1.2
            ],
            'extensions': [
                0x0000,  # server_name
                0x000d,  # signature_algorithms
                0x0005,  # status_request
                0x0010,  # supported_groups
                0x000b,  # ec_point_formats
                0x0021,  # padding
                0x0023,  # session_ticket
                0x000a,  # supported_versions
                0x0033,  # key_share
            ],
            'supported_groups': [0x001d, 0x0017, 0x0018],  # x25519, secp256r1, secp384r1
        },
        'firefox': {
            'supported_versions': [0x0304, 0x0303, 0x0302],
            'cipher_suites': [
                0x1301, 0x1302, 0x1303,
                0x002f, 0x0035, 0x003d, 0x003c
            ],
            'extensions': [
                0x0000, 0x000b, 0x000a, 0x0016, 0x0017, 0x001d,
                0x0018, 0x0023, 0x0028, 0x0029, 0x002b
            ],
            'supported_groups': [0x001d, 0x0017, 0x0018, 0x0019],
        },
        'safari': {
            'supported_versions': [0x0304, 0x0303],
            'cipher_suites': [0x1301, 0x1302, 0x1303, 0x002f, 0x0035],
            'extensions': [0x0000, 0x000b, 0x000a, 0x0016, 0x0010, 0x0023],
            'supported_groups': [0x001d, 0x0017, 0x0018],
        }
    }
    
    def __init__(self, profile='chrome'):
        self.profile = profile if profile in self.BROWSER_PROFILES else 'chrome'
        self.fingerprint = self.BROWSER_PROFILES[self.profile]
    
    def generate_client_hello(self) -> bytes:
        """Генерирует Client Hello пакет с реальным TLS fingerprint"""
        # Упрощённая версия - в реальности нужна полная TLS реализация
        hello = b''
        
        # Заголовок TLS Record
        hello += b'\x16'  # Тип содержания: Рукопожатие
        hello += b'\x03\x01'  # Версия: TLS 1.0 (для совместимости)
        
        # Заголовок рукопожатия
        hello += b'\x01'  # Тип рукопожатия: Привет клиента
        
        # Версия клиента
        hello += b'\x03\x03'  # TLS 1.2
        
        # Random
        hello += os.urandom(32)
        
        # Session ID
        session_id = os.urandom(32)
        hello += bytes([len(session_id)]) + session_id
        
        # Наборы шифров
        ciphers = self.fingerprint['cipher_suites']
        cipher_data = b''
        for cipher in ciphers:
            cipher_data += struct.pack('>H', cipher)
        hello += struct.pack('>H', len(cipher_data)) + cipher_data
        
        # Методы сжатия
        hello += b'\x01\x00'  # 1 метод: не сжимать
        
        # Extensions
        extensions = self._generate_extensions()
        hello += extensions
        
        return hello
    
    def _generate_extensions(self) -> bytes:
        """Генерирует TLS extensions"""
        extensions_data = b''
        
        for ext_id in self.fingerprint['extensions']:
            # Расширение имени сервера
            if ext_id == 0x0000:
                extensions_data += struct.pack('>H', ext_id)
                # Добавить реальное имя хоста
                hostname = b'www.example.com'
                ext_value = struct.pack('>H', len(hostname) + 5)
                ext_value += struct.pack('>H', len(hostname) + 1)
                ext_value += bytes([0x00]) + hostname
                extensions_data += struct.pack('>H', len(ext_value))
                extensions_data += ext_value
        
        return extensions_data


class DPIBypass:
    """Техники для обхода DPI (Deep Packet Inspection)"""
    
    def __init__(self):
        self.obfuscator = TrafficObfuscator()
        self.size_hider = PacketSizeHider()
        self.tls_profile = TLSFingerprint()
    
    def prepare_packet_for_transmission(self, vpn_packet: bytes) -> bytes:
        """
        Подготавливает VPN пакет для передачи, применяя все техники DPI bypass
        """
        # 1. Обфускация под обычный трафик
        obfuscated = self.obfuscator.obfuscate_packet(vpn_packet)
        
        # 2. Скрытие размера через padding
        padded, padding_size = self.size_hider.add_padding(obfuscated)
        
        # 3. Добавить random задержку
        self.size_hider.randomize_packet_timing()
        
        # Сохранить информацию о padding для восстановления
        header = struct.pack('>I', padding_size)
        
        return header + padded
    
    def recover_packet_from_transmission(self, transmitted_packet: bytes) -> bytes:
        """
        Восстанавливает оригинальный VPN пакет из переданного пакета
        """
        if len(transmitted_packet) < 4:
            return b''
        
        # Извлечь размер padding
        padding_size = struct.unpack('>I', transmitted_packet[:4])[0]
        padded_packet = transmitted_packet[4:]
        
        # Удалить padding
        unpadded = self.size_hider.remove_padding(padded_packet, padding_size)
        
        # Деобфускировать
        vpn_packet = self.obfuscator.deobfuscate_packet(unpadded)
        
        return vpn_packet
    
    def evade_pattern_detection(self, packets: List[bytes]) -> List[bytes]:
        """
        Применяет техники для избежания обнаружения по паттернам трафика
        """
        evasion_packets = []
        
        for packet in packets:
            # Изменить размер пакета
            modified = packet + os.urandom(random.randint(0, 256))
            
            # Добавить random интервалы
            time.sleep(random.uniform(0.001, 0.01))
            
            # Обфускировать
            obfuscated = self.obfuscator.obfuscate_packet(modified)
            evasion_packets.append(obfuscated)
        
        return evasion_packets
    
    def get_dpi_evasion_stats(self) -> dict:
        """Возвращает статистику по техникам обхода DPI"""
        return {
            'obfuscation_mode': self.obfuscator.mode,
            'traffic_pattern': self.size_hider.get_traffic_pattern(),
            'tls_profile': self.tls_profile.profile,
            'total_packets_hidden': self.size_hider.packet_history.__len__(),
        }
