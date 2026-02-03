"""
Общий протокол взаимодействия между клиентом и сервером
"""
import struct
import json
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional


class PacketType(IntEnum):
    """Типы пакетов в протоколе"""
    HANDSHAKE_REQUEST = 0x01
    HANDSHAKE_RESPONSE = 0x02
    AUTH_CHALLENGE = 0x03
    AUTH_RESPONSE = 0x04
    DATA = 0x10
    KEEPALIVE = 0x11
    DISCONNECT = 0x12
    ERROR = 0xFF


class ObfuscationMode(IntEnum):
    """Режимы обфусцировки"""
    HTTPS = 0x01
    HTTP2 = 0x02
    WEBSOCKET = 0x03
    RANDOM = 0x04
    NONE = 0x00


@dataclass
class PacketHeader:
    """Заголовок пакета"""
    packet_type: int
    length: int
    sequence: int
    flags: int = 0
    
    def serialize(self) -> bytes:
        """Сериализовать заголовок"""
        return struct.pack('!BBHI', self.packet_type, self.flags, self.length, self.sequence)
    
    @staticmethod
    def deserialize(data: bytes) -> 'PacketHeader':
        """Десериализовать заголовок"""
        packet_type, flags, length, sequence = struct.unpack('!BBHI', data[:8])
        return PacketHeader(packet_type, length, sequence, flags)


class VPNProtocol:
    """Общий класс для работы с протоколом VPN"""
    
    HEADER_SIZE = 8  # 1 (packet_type) + 1 (flags) + 2 (length) + 4 (sequence)
    MAX_PAYLOAD_SIZE = 65535
    MAGIC_NUMBER = b'NVPN'
    
    @staticmethod
    def create_packet(packet_type: int, payload: bytes, sequence: int = 0, flags: int = 0) -> bytes:
        """Создать пакет с заголовком"""
        header = PacketHeader(packet_type, len(payload), sequence, flags)
        return header.serialize() + payload
    
    @staticmethod
    def parse_packet(data: bytes) -> tuple[Optional[PacketHeader], Optional[bytes]]:
        """Распарсить пакет"""
        if len(data) < VPNProtocol.HEADER_SIZE:
            return None, None
        
        try:
            header = PacketHeader.deserialize(data[:VPNProtocol.HEADER_SIZE])
            payload = data[VPNProtocol.HEADER_SIZE:VPNProtocol.HEADER_SIZE + header.length]
            
            if len(payload) != header.length:
                return None, None
            
            return header, payload
        except Exception:
            return None, None
    
    @staticmethod
    def create_handshake_request(client_id: str, obfuscation_mode: int) -> bytes:
        """Создать запрос на рукопожатие"""
        data = json.dumps({
            'client_id': client_id,
            'obfuscation_mode': obfuscation_mode,
            'version': '1.0'
        }).encode()
        return VPNProtocol.create_packet(PacketType.HANDSHAKE_REQUEST, data)
    
    @staticmethod
    def create_auth_response(password_hash: bytes) -> bytes:
        """Создать ответ на аутентификацию"""
        return VPNProtocol.create_packet(PacketType.AUTH_RESPONSE, password_hash)
    
    @staticmethod
    def create_keepalive() -> bytes:
        """Создать пакет keepalive"""
        return VPNProtocol.create_packet(PacketType.KEEPALIVE, b'\x00')
    
    @staticmethod
    def create_disconnect() -> bytes:
        """Создать пакет отключения"""
        return VPNProtocol.create_packet(PacketType.DISCONNECT, b'\x00')
