#!/bin/bash

# Скрипт запуска VPN сервера в Docker контейнере

echo "Запуск NexusVPN сервера..."

# Параметры по умолчанию
HOST="${VPN_HOST:-0.0.0.0}"
PORT="${VPN_PORT:-443}"
PASSWORD="${VPN_PASSWORD:-your_secure_password}"
OBFUSCATION="${VPN_OBFUSCATION:-https}"

echo "Параметры сервера:"
echo "  Хост: $HOST"
echo "  Порт: $PORT"
echo "  Обфусцировка: $OBFUSCATION"

# Настроить iptables для маршрутизации трафика
echo "📡 Настройка маршрутизации трафика..."

# Включить forwarding
sysctl -w net.ipv4.ip_forward=1 > /dev/null 2>&1

# Настроить NAT
if ! iptables -t nat -L POSTROUTING -n 2>/dev/null | grep -q "MASQUERADE"; then
    iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE || true
    iptables -A FORWARD -i eth1 -o eth0 -j ACCEPT || true
    iptables -A FORWARD -i eth0 -o eth1 -m state --state RELATED,ESTABLISHED -j ACCEPT || true
    echo "✓ NAT правила установлены"
fi

# Запустить VPN сервер
echo "Запуск VPN сервера на $HOST:$PORT..."
cd /app
python -m backend.vpn_server \
    --host "$HOST" \
    --port "$PORT" \
    --password "$PASSWORD"

# Очистить iptables при выходе
trap 'echo "Очистка правил iptables..." && iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE 2>/dev/null; exit' SIGTERM SIGINT
