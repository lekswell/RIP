from minio import Minio
from io import BytesIO
# from minio.error import NoSuchKey, ResponseError

client = Minio(endpoint="localhost:9000",   # адрес сервера
               access_key='minio',          # логин админа
               secret_key='minio124',       # пароль админа
               secure=False)      


def get_minio_presigned_url(image_name):
    """
    Генерирует предварительно подписанный URL для изображения в MinIO.
    """
    if image_name == 'not_found.jpg':
        url = client.presigned_get_object(
            "events",
            "not_found.jpg",
        )
    else:
        url = client.presigned_get_object(
            "events",
            f"{image_name}.jpg",
        )

    return url

def upload_image_to_minio(image_file, minio_path):
    """
    Загружает изображение в MinIO и обновляет поле Image события
    """
    # Загружаем файл в MinIO
    client.put_object(
        "events",  # Замените на свой бакет
        minio_path,
        BytesIO(image_file.read()),  # Используем BytesIO для передачи данных
        image_file.size,
        content_type='image/jpeg',  # Укажите правильный тип содержимого для вашего файла
    )
