# Боты викторины в VK и Телегерам
## Описание
Созданы боты которые проводят викторину

## Как установить
Python3 должен быть уже установлен. Затем используйте pip (или pip3, есть конфликт с Python2) для установки зависимостей
```
pip install -r requirements.txt
```
Должен быть архив с вопросами с названием "quiz-questions"

## Пример запуска скрипта
Для запуска скрипта требуется сделать следующее:

1. Созадать бота и получить его токен(Telegram)
2. Создать группу в ВК и добавить к ней ключ (дать доступы к отправке сообщений)
3. Получить свой id (использовать бота @userinfobot) - чат id для телеграмм бота
4. В папке со скаченным скриптом создать файл .env
5. На сайте [redislabs](https://redislabs.com) создать базу данных и получить токен
5. Открыть файл в текстом редакторе и добавить строки
```
VK_GROUP_TOKEN=<указать токен группы VK>
TELEGRAM_BOT_TOKEN=<токен от телеграмма>
TELEGRAM_CHAT_ID=<ваш id полученный от @userinfobot>
TELEGRAMM_LOGGER_BOT=<токен от телеграмма> - бот который сообщает об ошибках в приложении
REDIS_DB=<адрес на базу данных>
REDIS_DB_PORT=<порт на котором работает БД>
REDIS_DB_PASSWORD=<пароль от БД>
```
8. В папке со скаченной программой разархивировать вопросы для квиза в папку "quiz-questions"
9. Выполнить команду (в папке со скаченным скриптом)
```
python telegram_bot.py - запускает телеграм бота 
python vk_bot.py - запускает вк бота 
```

## Пример работы
![](https://github.com/LevikovCollector/bot_messages/blob/master/gif_for_github/chat_bot.gif)