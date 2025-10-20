#!/usr/bin/env python3
"""
Скрипт для генерации VAPID ключей для браузерных push-уведомлений.
Запустите этот скрипт один раз для генерации ключей и добавьте их в .env файл.
"""

try:
    from pywebpush import webpush
    import base64
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
except ImportError as e:
    print("Ошибка импорта. Установите необходимые зависимости:")
    print("pip install pywebpush cryptography")
    exit(1)


def generate_vapid_keys():
    """Генерирует пару VAPID ключей"""
    
    # Генерируем приватный ключ
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    
    # Получаем публичный ключ
    public_key = private_key.public_key()
    
    # Сериализуем приватный ключ
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Сериализуем публичный ключ в несжатом формате
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    
    # Кодируем в base64 URL-safe формат
    private_key_b64 = base64.urlsafe_b64encode(private_key_bytes).decode('utf-8').rstrip('=')
    public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')
    
    return private_key_b64, public_key_b64


def main():
    print("🔐 Генерация VAPID ключей для PlaylistChecker...")
    print()
    
    try:
        private_key, public_key = generate_vapid_keys()
        
        print("✅ VAPID ключи успешно сгенерированы!")
        print()
        print("📋 Добавьте следующие строки в ваш .env файл:")
        print("=" * 60)
        print(f"VAPID_PUBLIC_KEY={public_key}")
        print(f"VAPID_PRIVATE_KEY={private_key}")
        print("VAPID_EMAIL=mailto:your_email@example.com")
        print("=" * 60)
        print()
        print("⚠️  ВАЖНО:")
        print("1. Замените 'your_email@example.com' на ваш реальный email")
        print("2. Сохраните эти ключи в безопасном месте")
        print("3. Не публикуйте приватный ключ в открытых репозиториях")
        print("4. Публичный ключ будет использоваться в браузере")
        print("5. Приватный ключ используется только на сервере")
        
    except Exception as e:
        print(f"❌ Ошибка генерации ключей: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
