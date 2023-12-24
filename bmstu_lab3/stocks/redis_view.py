import redis

def get_instance_redis():
    red =  redis.Redis(
        host='0.0.0.0',
        port=6379,
    )
    return red


def set_key(key, value):
    red = get_instance_redis()
    red.set(key, value, ex=86400)


def get_value(key):
    red = get_instance_redis()
    return red.get(key)


def delete_value(key):
    red = get_instance_redis()
    red.delete(key)