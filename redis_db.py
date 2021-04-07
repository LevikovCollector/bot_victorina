import redis
import logging
import os

logger_redis = logging.getLogger("logger_redis_db")

class RedisDB:
    def __init__(self):
        self.redis_connection = redis.Redis(host=os.environ['REDIS_DB'], port=os.environ['REDIS_DB_PORT'], db=0,
                                            password=os.environ['REDIS_DB_PASSWORD'])
        logger_redis.setLevel(logging.INFO)


    def save_data(self, name, value):
        if self.redis_connection.set(name, value):
            logger_redis.info(f'Сохранены данные: id - {name} и значение - {value}')
        else:
            logger_redis.warning(f'Данные не сохранены: id - {name} и значение - {value}')

    def get_data(self, param):
        try:
            return self.redis_connection.get(param).decode('utf-8')
        except AttributeError:
            return 0
