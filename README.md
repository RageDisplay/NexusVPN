# VPN с DPI Bypass

Полнофункциональный VPN с поддержкой обфусцировки.

### Установка зависимостей
```bash
pip install -r requirements.txt
```
### Запуск сервера (Пример)
```bash
python vpn_server_stealth.py 443 password https
```
### Запуск клиента (другой терминал)
```bash
python vpn_client_stealth.py localhost 443 password https
```


## ДОСТУПНЫЕ РЕЖИМЫ

| **https** | HTTPS TLS Record маскировка
| **http2** | HTTP/2 frame маскировка 
| **websocket** | WebSocket маскировка 
| **random** | Random padding маскировка 

### Пример с другими режимами:
```bash
# HTTP/2
python vpn_server_stealth.py 443 password http2
python vpn_client_stealth.py localhost 443 password http2

# WebSocket
python vpn_server_stealth.py 443 password websocket
python vpn_client_stealth.py localhost 443 password websocket

# Random
python vpn_server_stealth.py 443 password random
python vpn_client_stealth.py localhost 443 password random
```


## КРИПТОГРАФИЯ

- **Key Exchange:** Curve25519 ECDH
- **Encryption:** ChaCha20-Poly1305 AEAD
- **KDF:** PBKDF2-HMAC-SHA256 (100k iterations)
- **Nonce:** 96-bit random для каждого пакета
- **Authentication:** Poly1305 HMAC-TAG

---

## ОСОБЕННОСТИ

**DPI Evasion:** 4 встроенных режима маскировки
**Keep-Alive:** Автоматические пакеты каждые 5 сек
**Асинхронный сервер:** Поддержка нескольких клиентов
**Зашифрованные сообщения:** Конец-в-конец
**Производственный уровень:** Обработка ошибок и логирование

---

## ПАРАМЕТРЫ ЗАПУСКА

### Сервер
```bash
python vpn_server_stealth.py <PORT> <PASSWORD> <MODE>
```
- `PORT` - Порт для слушания (по умолчанию 443)
- `PASSWORD` - Пароль для аутентификации клиентов
- `MODE` - Режим обфусцировки (https, http2, websocket, random)

### Клиент
```bash
python vpn_client_stealth.py <HOST> <PORT> <PASSWORD> <MODE>
```
- `HOST` - Хост сервера (localhost, 192.168.1.1, и т.д.)
- `PORT` - Порт сервера
- `PASSWORD` - Пароль (должен совпадать с сервером)
- `MODE` - Режим обфусцировки (должен совпадать с сервером)

---