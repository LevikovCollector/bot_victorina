import os
import pathlib
import re


def get_quiz_data():
    files = os.listdir('quiz-questions')
    data_quiz = []
    template = 'Вопрос \d+:'
    for file in files:
        try:
            if file not in ['COPYRIGHT', 'fill.log', 'index', 'preface']:
                file_path = pathlib.Path.joinpath(pathlib.Path.cwd(), 'quiz-questions', file)
                with open(file_path, 'r', encoding='KOI8-R') as q_file:
                    file_contents = q_file.read()
                    split_contents = file_contents.split('\n\n')
                    for index,  content in enumerate(split_contents):
                        if re.search(template,content):
                            question = content
                            answer = split_contents[index + 1]\
                                .split('Ответ:\n')[-1]\
                                .replace('.', '')\
                                .lower()\
                                .replace('[', '')\
                                .replace(']', '')\
                                .replace('"', '')
                            data_quiz.append({question: answer})
        except IndexError:
            print(file)
    return data_quiz
