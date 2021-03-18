import redis
import logging
import os
from dotenv import load_dotenv
from quiz_data import get_quiz_data

logger_redis = logging.getLogger("logger_redis_db")

class RedisDB:
    def __init__(self):
        self.redis_connection = redis.Redis(host=os.environ['REDIS_DB'], port=os.environ['REDIS_DB_PORT'], db=0,
                                            password=os.environ['REDIS_DB_PASSWORD'])
        logger_redis.setLevel(logging.INFO)

    def save_data(self, name, value):
        if self.redis_connection.set(name, value):
            logger_redis.info(f'Сохранены данные: id - {name} и вопрос - {value}')
        else:
            logger_redis.warning(f'Данные не сохранены: id - {name} и вопрос - {value}')

    def get_data(self, param):
        return self.redis_connection.get(param).decode('utf-8')

if __name__ == '__main__':
    load_dotenv(dotenv_path='.env')
    q = get_quiz_data()
    r = RedisDB()
    # r.save_data('foo', 'bar')
    print(list(q[0].keys())[0])
