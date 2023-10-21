# from minio import Minio
# from minio.error import NoSuchKey, ResponseError

# client = Minio(endpoint="localhost:9000",   # адрес сервера
#                access_key='minio',          # логин админа
#                secret_key='minio124',       # пароль админа
#                secure=False)      


# def upload_image_to_minio(image_name):
#     client.fput_object(bucket_name='events',  # имя бакета Minio
#                    object_name=image_name,   # имя для нового файла в хранилище Minio
#                    file_path=f'bmstu_lab3/minio/images/{image_name}')  # путь к исходному файлу на вашем сервере

