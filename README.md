# Первый запуск

### Вариант A: Быстрый запуск на Linux (Docker)

#### 1. Подготовка сервера (2 минуты)

```bash
# Обновить систему
sudo apt-get update && sudo apt-get upgrade -y

# Установить Docker

# Установить Docker Compose

# Проверить установку
docker-compose --version
```

#### 2. Клонировать проект

```bash
cd /opt
git clone https://github.com/RageDisplay/NexusVPN
```

#### 3. Конфигурация

```bash
# Отредактировать пароль
sudo nano docker-compose.yml

# Найти строку:
# - VPN_PASSWORD=pass
# 
# Заменить на:
# - VPN_PASSWORD=****
```

#### 4. Запуск

```bash
# Запустить контейнер
sudo docker-compose up -d

# Проверить статус
sudo docker-compose ps
sudo docker-compose logs -f vpn-server
```

#### 5. Окончание

```
VPN Server запущен на 0.0.0.0:443
Рукопожатие успешно для 127.0.0.1
Аутентификация успешна
```
### Вариант B: Запуск на Windows (клиент)

#### 1. Установить Python

1. Скачать с https://python.org (версия 3.11+)
2. Запустить установщик
3. **ВАЖНО:** Отметить "Add Python to PATH"
4. Нажать "Install Now"

#### 2. Клонировать проект 

```bash
# Открыть PowerShell / Command Prompt
git clone https://github.com/RageDisplay/NexusVPN
cd NexusVPN
```

#### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

#### 4. Запустить клиент

```bash
python frontend/main.py
```
---

## Подключение

### На клиенте (Windows)

1. **Адрес сервера:** `123.45.67.89` (IP вашего сервера)
2. **Порт:** `443`
3. **Пароль:** `****` (из docker-compose.yml)
4. **Режим:** `HTTPS`
5. **DPI Bypass:** включен

Затем нажать **"Подключиться"**

---

## Проверка работы

### На Windows клиенте

```
1. Открыть браузер
2. Перейти на: https://ifconfig.me
3. Вы должны увидеть IP сервера (не ваш реальный IP)
```


## Диагностика

```bash
# Проверить логи
sudo docker-compose logs vpn-server

# Проверить портов
sudo netstat -tlnp | grep 443

# Проверить контейнер
sudo docker ps
```

### Клиент не подключается

```bash
# Проверить логи клиента
cat vpn_client.log

# Проверить доступность сервера
ping 123.45.67.89
telnet 123.45.67.89 443
```

---

## Логирование

### Логи сервера (Docker)

```bash
# Просмотр логов
sudo docker-compose logs -f vpn-server

# Только ошибки
sudo docker-compose logs vpn-server | grep ERROR

# Последние 100 строк
sudo docker-compose logs --tail=100 vpn-server
```

### Логи клиента

```bash
# На Windows
cat vpn_client.log

# Или открыть текстовым редактором
notepad vpn_client.log
```

## Следующие шаги

### 1. Оптимизация

```bash
# В docker-compose.yml отрегулировать:
- VPN_PORT (если 443 занят, использовать 8443)
- VPN_OBFUSCATION (попробовать http2, websocket)
```

### 2. Безопасность

```bash
# Установить файрвол на сервере
sudo ufw allow 443/tcp
sudo ufw allow 80/tcp
sudo ufw enable
```

### 3. Мониторинг

```bash
# Включить Prometheus мониторинг
sudo docker-compose up -d prometheus
# Перейти на http://server_ip:9090
```

### 4. Резервная копия

```bash
# Сохранить конфигурацию
cp docker-compose.yml docker-compose.yml.backup
```