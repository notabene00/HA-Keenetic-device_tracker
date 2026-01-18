# Тестирование интеграции Keenetic

## Статус тестов

✅ **27 из 27 unit тестов проходят успешно**

## Структура тестов

### 1. `test_exceptions.py` - Тесты исключений (7 тестов)
- Базовое исключение `KeeneticError`
- `KeeneticConnectionError` - ошибки подключения
- `KeeneticAuthenticationError` - ошибки аутентификации
- `KeeneticTimeoutError` - таймауты
- `KeeneticResponseError` - ошибки ответа
- Иерархия исключений
- Перехват базовым классом

### 2. `test_keenetic.py` - Тесты API клиента (20 тестов)

#### ConnectedDevice (6 тестов):
- Парсинг беспроводного устройства
- Парсинг проводного устройства
- Обработка ключей с дефисами
- Приоритет отображаемого имени
- Дополнительные атрибуты Wi-Fi
- Дополнительные атрибуты Ethernet

#### KeeneticRouter (14 тестов):
- Инициализация HTTP
- Инициализация HTTPS
- Порт по умолчанию
- Успешное подключение
- Подключение с аутентификацией
- Ошибка аутентификации
- Таймаут подключения
- Ошибка соединения
- Получение списка устройств
- Обработка невалидного ответа
- Закрытие соединения
- Async context manager
- Exponential backoff retry (3 попытки)
- Повторная аутентификация при 401

## Запуск тестов

```bash
# Установка зависимостей
pip install pytest pytest-asyncio httpx

# Запуск всех тестов
pytest tests/ -v

# Запуск с coverage
pytest tests/ --cov=custom_components/keenetic --cov-report=html

# Запуск конкретного файла
pytest tests/test_keenetic.py -v
```

## Что протестировано

### ✅ Покрыто тестами:
1. **Async httpx клиент** - все операции асинхронные
2. **Exponential backoff** - 3 попытки с экспоненциальной задержкой
3. **Обработка ошибок** - все типы исключений
4. **Парсинг устройств** - wireless, wired, с/без имён
5. **Аутентификация** - Basic Auth, повторная при 401
6. **Context manager** - правильное открытие/закрытие
7. **SSL поддержка** - HTTP и HTTPS
8. **Type hints** - все методы имеют типы

### ⚠️ Требует реального роутера для тестирования:
1. **Реальное подключение к Keenetic** - API endpoints
2. **Config Flow UI** - интеграция с Home Assistant
3. **ScannerEntity** - device_tracker платформа
4. **Coordinator** - периодическое обновление данных
5. **Dispatcher signals** - события HA

## Тестирование с реальным роутером

Для полного тестирования интеграции с Home Assistant:

1. **Установите интеграцию** в Home Assistant:
   ```bash
   # Скопируйте в custom_components
   cp -r custom_components/keenetic /config/custom_components/
   ```

2. **Перезапустите Home Assistant**

3. **Добавьте интеграцию через UI**:
   - Settings → Devices & Services → Add Integration
   - Найдите "Keenetic"
   - Введите параметры роутера:
     - Host: IP адрес роутера (например, `192.168.1.1`)
     - Port: `80` (HTTP) или `443` (HTTPS)
     - Username: имя пользователя
     - Password: пароль
     - Use SSL: включите для HTTPS
     - Verify SSL: проверка SSL сертификата

4. **Проверьте работу**:
   - Откройте Developer Tools → States
   - Найдите entities `device_tracker.keenetic_*`
   - Проверьте атрибуты устройств

## Логирование для отладки

Добавьте в `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.keenetic: debug
```

Логи будут в `home-assistant.log`:
- Подключение к роутеру
- Получение списка устройств  
- Ошибки и retry попытки
- Обновление состояний устройств

## Известные ограничения

- Тесты не требуют установки Home Assistant
- Config Flow тесты удалены (требуют полную HA среду)
- Integration тесты требуют реальный роутер Keenetic

## Continuous Integration

Рекомендуется настроить GitHub Actions для автоматического запуска тестов:

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install pytest pytest-asyncio httpx
      - run: pytest tests/ -v
```
