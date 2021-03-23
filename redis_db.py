import redis
import logging
import os
from dotenv import load_dotenv

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

    def get_question_number(self, key):
        return int(self.get_data(f'{key}-question_number'))

    def get_right_answers(self, key):
        return int(self.get_data(f'{key}-right_answers'))

    def get_user_not_answer_question_state(self, key):
        return int(self.get_data(f'{key}-user_not_answer_question_state'))

    def get_missed_questions(self, key):
        return int(self.get_data(f'{key}-missed_questions'))

    def get_vk_user_state_ready(self, key):
        return int(self.get_data(f'{key}-user_state_ready'))

    def save_question_number(self, key, q_num):
        self.save_data(name=f'{key}-question_number', value=q_num)

    def save_right_answers(self, key, value):
        self.save_data(name=f'{key}-right_answers', value=value)

    def save_missed_questions(self, key, value):
        self.save_data(name=f'{key}-missed_questions', value=value)

    def save_user_not_answer_question_state(self, key, value):
        self.save_data(name=f'{key}-user_not_answer_question_state', value=value)

    def save_vk_user_state_ready(self, key, value):
        self.save_data(name=f'{key}-user_state_ready', value=value)

if __name__ == '__main__':
    load_dotenv(dotenv_path='.env')
    user_key = 'vk-7224598'
    redis_db = RedisDB()
    redis_db.save_right_answers(user_key, 0)
    redis_db.save_missed_questions(user_key, 0)
    redis_db.save_question_number(user_key, -1)
    redis_db.save_user_not_answer_question_state(user_key, 1)
    redis_db.save_vk_user_state_ready(user_key, 1)