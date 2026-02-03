"""
Маршрутизатор трафика VPN
Отвечает за перенаправление трафика через интернет
"""
import socket
import threading
import logging
from typing import Dict, Optional
import struct

logger = logging.getLogger(__name__)


class TrafficRouter:
    """Маршрутизатор трафика VPN"""
    
    BUFFER_SIZE = 4096
    SOCKET_TIMEOUT = 5
    
    def __init__(self):
        self.routes: Dict[str, 'ClientRoute'] = {}
        self.lock = threading.Lock()
        self.dns_cache = {}
    
    def route_traffic(self, client_id: str, payload: bytes) -> bool:
        """
        Маршрутизировать трафик от клиента
        payload содержит IP пакет
        """
        try:
            # Парсить IP пакет
            if len(payload) < 20:
                return False
            
            # Получить версию IP
            version = (payload[0] >> 4) & 0xF
            
            if version == 4:
                return self._route_ipv4(client_id, payload)
            elif version == 6:
                return self._route_ipv6(client_id, payload)
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при маршрутизации: {e}")
            return False
    
    def _route_ipv4(self, client_id: str, packet: bytes) -> bool:
        """Маршрутизировать IPv4 пакет"""
        try:
            # Парсить IPv4 заголовок
            # Формат: version(4) + ihl(4) + dscp(6) + ecn(2) + length(16) + ...\n            src_ip = '.'.join(str(b) for b in packet[12:16])
            dst_ip = '.'.join(str(b) for b in packet[16:20])
            
            protocol = packet[9]
            
            if protocol == 6:  # TCP
                return self._route_tcp(client_id, src_ip, dst_ip, packet)
            elif protocol == 17:  # UDP
                return self._route_udp(client_id, src_ip, dst_ip, packet)
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при маршрутизации IPv4: {e}")
            return False
    
    def _route_ipv6(self, client_id: str, packet: bytes) -> bool:
        """Маршрутизировать IPv6 пакет"""
        try:
            # Парсить IPv6 заголовок
            src_ip = ':'.join('%02x' % b for b in packet[8:24])
            dst_ip = ':'.join('%02x' % b for b in packet[24:40])
            
            next_header = packet[6]
            
            if next_header == 6:  # TCP
                return self._route_tcp(client_id, src_ip, dst_ip, packet)
            elif next_header == 17:  # UDP
                return self._route_udp(client_id, src_ip, dst_ip, packet)
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при маршрутизации IPv6: {e}")
            return False
    
    def _route_tcp(self, client_id: str, src_ip: str, dst_ip: str, packet: bytes) -> bool:
        """Маршрутизировать TCP трафик"""
        try:
            # Парсить TCP заголовок (после IP заголовка)
            ip_header_len = ((packet[0] & 0xF) * 4)
            src_port = struct.unpack('!H', packet[ip_header_len:ip_header_len+2])[0]
            dst_port = struct.unpack('!H', packet[ip_header_len+2:ip_header_len+4])[0]
            
            route_key = f"{client_id}:{src_ip}:{src_port}:{dst_ip}:{dst_port}"
            
            with self.lock:
                if route_key not in self.routes:
                    self.routes[route_key] = ClientRoute(
                        client_id, src_ip, src_port, dst_ip, dst_port, is_tcp=True
                    )
                
                route = self.routes[route_key]
            
            # Отправить пакет через интернет
            return route.send_packet(packet)
            
        except Exception as e:
            logger.debug(f"Ошибка при маршрутизации TCP: {e}")
            return False
    
    def _route_udp(self, client_id: str, src_ip: str, dst_ip: str, packet: bytes) -> bool:
        """Маршрутизировать UDP трафик"""
        try:
            # Парсить UDP заголовок
            ip_header_len = ((packet[0] & 0xF) * 4)
            src_port = struct.unpack('!H', packet[ip_header_len:ip_header_len+2])[0]
            dst_port = struct.unpack('!H', packet[ip_header_len+2:ip_header_len+4])[0]
            
            route_key = f"{client_id}:{src_ip}:{src_port}:{dst_ip}:{dst_port}"
            
            with self.lock:
                if route_key not in self.routes:
                    self.routes[route_key] = ClientRoute(
                        client_id, src_ip, src_port, dst_ip, dst_port, is_tcp=False
                    )
                
                route = self.routes[route_key]
            
            # Отправить пакет через интернет
            return route.send_packet(packet)
            
        except Exception as e:
            logger.debug(f"Ошибка при маршрутизации UDP: {e}")
            return False
    
    def cleanup_route(self, route_key: str):
        """Очистить маршрут"""
        with self.lock:
            if route_key in self.routes:
                del self.routes[route_key]


class ClientRoute:
    """Маршрут для отдельного клиента"""
    
    def __init__(self, client_id: str, src_ip: str, src_port: int,
                 dst_ip: str, dst_port: int, is_tcp: bool = True):
        self.client_id = client_id
        self.src_ip = src_ip
        self.src_port = src_port
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.is_tcp = is_tcp
        
        self.socket = None
        self.lock = threading.Lock()
        self._create_socket()
    
    def _create_socket(self):
        """Создать сокет для этого маршрута"""
        try:
            socket_type = socket.SOCK_STREAM if self.is_tcp else socket.SOCK_DGRAM
            self.socket = socket.socket(socket.AF_INET, socket_type)
            self.socket.settimeout(5)
            
            if self.is_tcp:
                # TCP: подключиться к целевому адресу
                try:
                    self.socket.connect((self.dst_ip, self.dst_port))
                except Exception as e:
                    logger.debug(f"Ошибка подключения TCP к {self.dst_ip}:{self.dst_port}: {e}")
                    self.socket = None
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Ошибка при создании сокета: {e}")
            self.socket = None
            return False
    
    def send_packet(self, packet: bytes) -> bool:
        """Отправить пакет через интернет"""
        if self.socket is None:
            return False
        
        try:
            with self.lock:
                if self.is_tcp:
                    # TCP: отправить данные напрямую
                    # Пропустить IP и TCP заголовки, отправить только payload
                    payload = packet[40:]  # Минимальный заголовок TCP
                    if payload:
                        self.socket.sendall(payload)
                else:
                    # UDP: отправить пакет
                    self.socket.sendto(packet, (self.dst_ip, self.dst_port))
                
                return True
                
        except Exception as e:
            logger.debug(f"Ошибка при отправке пакета: {e}")
            return False
    
    def close(self):
        """Закрыть маршрут"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
