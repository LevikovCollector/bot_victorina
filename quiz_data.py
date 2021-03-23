import os
import pathlib

def get_quiz_data():
    files = os.listdir('quiz-questions')
    data_quiz = []
    for file in files:
        try:
            if file not in ['COPYRIGHT', 'fill.log', 'index', 'preface']:
                with open(pathlib.Path.joinpath(pathlib.Path.cwd(), 'quiz-questions', file),'r', encoding='KOI8-R') as q_file:
                    file_contents = q_file.read()
                    split_contents = file_contents.split('\n\n')
                    question_index = 0
                    for content in split_contents:
                        if 'Вопрос' in content:
                            break
                        else:
                            question_index += 1
                    question = split_contents[question_index].split(':')[-1]
                    answer = split_contents[question_index+1].split('Ответ:\n')[-1].replace('.', '').lower().replace('[', '').replace(']', '').replace('"', '')
                    data_quiz.append(
                                    {
                                      question:answer
                                    }
                                     )
        except IndexError:
            print(file)
    return data_quiz


def get_answer(quiz_data, question_number, redis_db, redis_db_key):
    return quiz_data[question_number][redis_db.get_data(redis_db_key)]








