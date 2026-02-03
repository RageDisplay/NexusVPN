"""
Обфусцировка и DPI bypass
"""
import os
import random
import logging

logger = logging.getLogger(__name__)


class TrafficObfuscator:
    """Обфусцировка трафика под разные протоколы"""
    
    def __init__(self, mode: str = 'https'):
        self.mode = mode.lower()
    
    def obfuscate(self, data: bytes) -> bytes:
        """Добавить обфусцировку"""
        if self.mode == 'https':
            return self._obfuscate_https(data)
        elif self.mode == 'http2':
            return self._obfuscate_http2(data)
        elif self.mode == 'websocket':
            return self._obfuscate_websocket(data)
        elif self.mode == 'random':
            return self._obfuscate_random(data)
        else:
            return data
    
    def deobfuscate(self, data: bytes) -> bytes:
        """Убрать обфусцировку"""
        if self.mode == 'https':
            return self._deobfuscate_https(data)
        elif self.mode == 'http2':
            return self._deobfuscate_http2(data)
        elif self.mode == 'websocket':
            return self._deobfuscate_websocket(data)
        elif self.mode == 'random':
            return self._deobfuscate_random(data)
        else:
            return data
    
    def _obfuscate_https(self, data: bytes) -> bytes:
        """Маскировать как HTTPS трафик"""
        # Добавить HTTPS TLS-подобный заголовок
        tls_header = bytes([
            0x16,  # TLS Handshake
            0x03, 0x03,  # TLS Version 1.2
        ])
        length = len(data) & 0xFFFF
        tls_header += bytes([(length >> 8) & 0xFF, length & 0xFF])
        return tls_header + data
    
    def _deobfuscate_https(self, data: bytes) -> bytes:
        """Убрать HTTPS маскировку"""
        if len(data) > 5 and data[0] == 0x16:
            return data[5:]
        return data
    
    def _obfuscate_http2(self, data: bytes) -> bytes:
        """Маскировать как HTTP/2 трафик"""
        # HTTP/2 frame header
        frame_header = bytes([
            0x00, 0x00, len(data) & 0xFF,  # Длина
            0x00,  # Тип frame (DATA)
            0x00,  # Флаги
        ])
        frame_header += bytes([0x00, 0x00, 0x00, 0x00])  # Stream ID
        return frame_header + data
    
    def _deobfuscate_http2(self, data: bytes) -> bytes:
        """Убрать HTTP/2 маскировку"""
        if len(data) > 9:
            return data[9:]
        return data
    
    def _obfuscate_websocket(self, data: bytes) -> bytes:
        """Маскировать как WebSocket трафик"""
        # WebSocket frame header
        # FIN + opcode (binary frame = 0x82)
        ws_header = bytes([0x82])
        
        length = len(data)
        if length < 126:
            ws_header += bytes([0x80 | length])  # MASK + length
        elif length < 65536:
            ws_header += bytes([0x80 | 126])
            ws_header += bytes([(length >> 8) & 0xFF, length & 0xFF])
        else:
            ws_header += bytes([0x80 | 127])
            ws_header += bytes([(length >> 56) & 0xFF, (length >> 48) & 0xFF,
                               (length >> 40) & 0xFF, (length >> 32) & 0xFF,
                               (length >> 24) & 0xFF, (length >> 16) & 0xFF,
                               (length >> 8) & 0xFF, length & 0xFF])
        
        # Добавить маску
        mask = os.urandom(4)
        ws_header += mask
        
        # XOR данные с маской
        masked_data = bytes([
            data[i] ^ mask[i % 4] for i in range(len(data))
        ])
        
        return ws_header + masked_data
    
    def _deobfuscate_websocket(self, data: bytes) -> bytes:
        """Убрать WebSocket маскировку"""
        if len(data) < 6:
            return data
        
        # Пропустить WebSocket заголовок
        idx = 2
        
        # Читать длину
        length = data[idx] & 0x7F
        idx += 1
        
        if length == 126:
            if len(data) < idx + 2:
                return data
            idx += 2
        elif length == 127:
            if len(data) < idx + 8:
                return data
            idx += 8
        
        # Пропустить маску (4 байта)
        if len(data) < idx + 4:
            return data
        
        mask = data[idx:idx+4]
        idx += 4
        
        # Демаскировать данные
        masked_data = data[idx:]
        unmasked = bytes([
            masked_data[i] ^ mask[i % 4] for i in range(len(masked_data))
        ])
        
        return unmasked
    
    def _obfuscate_random(self, data: bytes) -> bytes:
        """Случайная обфусцировка (padding)"""
        # Добавить случайный padding
        padding_size = random.randint(1, 256)
        padding = os.urandom(padding_size)
        
        # Добавить размер padding в конце
        return data + padding + bytes([padding_size & 0xFF])
    
    def _deobfuscate_random(self, data: bytes) -> bytes:
        """Убрать случайное padding"""
        if len(data) < 1:
            return data
        
        padding_size = data[-1]
        if padding_size > 0 and len(data) > padding_size + 1:
            return data[:-padding_size-1]
        return data


class DPIBypass:
    """DPI (Deep Packet Inspection) bypass техники"""
    
    def __init__(self):
        self.techniques = [
            self._fragment_packets,
            self._insert_junk,
            self._randomize_mtu,
        ]
    
    def apply(self, data: bytes) -> bytes:
        """Применить DPI bypass"""
        # Выбрать случайную технику
        technique = random.choice(self.techniques)
        return technique(data)
    
    def _fragment_packets(self, data: bytes) -> bytes:
        """Фрагментировать пакеты"""
        if len(data) < 100:
            return data
        
        # Случайно разбить пакет
        split_point = random.randint(10, len(data) - 10)
        fragment1 = data[:split_point]
        fragment2 = data[split_point:]
        
        # Добавить маркер фрагментации
        return bytes([0xFB, 0x01]) + fragment1 + bytes([0xFB, 0x02]) + fragment2
    
    def _insert_junk(self, data: bytes) -> bytes:
        """Добавить мусорные данные"""
        junk_size = random.randint(10, 100)
        junk = os.urandom(junk_size)
        
        # Вставить мусор в случайное место
        insert_pos = random.randint(0, len(data))
        
        return (data[:insert_pos] + 
                bytes([0xFC, junk_size & 0xFF]) + 
                junk + 
                data[insert_pos:])
    
    def _randomize_mtu(self, data: bytes) -> bytes:
        """Случайно изменить MTU"""
        mtu = random.choice([512, 576, 1024, 1280, 1500])
        
        if len(data) <= mtu:
            return data
        
        # Добавить маркер MTU
        return bytes([0xFD, (mtu >> 8) & 0xFF, mtu & 0xFF]) + data


class PacketSizeHider:
    """Скрывать размеры пакетов"""
    
    @staticmethod
    def hide_size(data: bytes, target_size: int = 1500) -> bytes:
        """Привести пакет к целевому размеру"""
        if len(data) >= target_size:
            return data
        
        # Добавить padding
        padding_size = target_size - len(data)
        padding = os.urandom(padding_size)
        
        return data + padding
    
    @staticmethod
    def unhide_size(data: bytes) -> bytes:
        """Убрать padding (требует дополнительной информации о размере)"""
        # В реальной реализации это требует метаданные о размере
        return data
