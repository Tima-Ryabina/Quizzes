# Импорт необходимых модулей Flask для работы с веб-приложением
from flask import Flask, redirect, request, session, url_for, render_template
# Функции для работы с базой данных викторин
from db_scripts import get_question_after, get_all_quizzes, check_answer
# Перемешивание вариантов ответов
from random import shuffle
import os  # для получения текущей рабочей директории

# Определяем текущую папку (где лежит этот скрипт)
folder = os.getcwd()

# Создаём Flask-приложение, указывая папки для шаблонов и статических файлов
web_application = Flask(__name__, template_folder=folder, static_folder=folder)
# Секретный ключ для работы с сессиями (необходим для сохранения состояния между запросами)
web_application.config['SECRET_KEY'] = 'VeryStrongKey'


def save_answers():
    """Сохраняет ответ пользователя на текущий вопрос в сессию."""
    # Получаем из отправленной формы текст ответа и ID вопроса
    answer = request.form.get('answer_text')
    question_id = request.form.get('question_id')
    # Запоминаем, на каком вопросе остановились (ID последнего показанного вопроса)
    session['last_question'] = question_id
    # Увеличиваем счётчик всех отвеченных вопросов
    session['total'] += 1
    # Проверяем правильность ответа через функцию из db_scripts
    if check_answer(question_id, answer):
        session['answers'] += 1  # если правильно – увеличиваем счётчик правильных


def question_form(question):
    """
    Формирует HTML-страницу с вопросом и вариантами ответов.
    question – кортеж из БД: (id_вопроса, текст_вопроса, правильный_ответ, wrong1, wrong2, wrong3)
    """
    # Собираем все варианты (правильный + три неправильных) в список
    answers_list = [question[2], question[3], question[4], question[5]]
    # Перемешиваем порядок вариантов, чтобы правильный не всегда был первым
    shuffle(answers_list)
    # Отображаем шаблон test.html, передавая ему:
    #   question – текст вопроса,
    #   question_id – ID вопроса (для сохранения в скрытом поле),
    #   answers_list – перемешанные варианты ответов
    return render_template('test.html',
                           question=question[1],
                           question_id=question[0],
                           answers_list=answers_list)


def quiz_form():
    """Генерирует HTML-форму для выбора викторины из выпадающего списка."""
    # Получаем список всех доступных викторин (список словарей с ключами id, title)
    quizzes = get_all_quizzes()
    # Начинаем собирать HTML-код страницы
    html = '''
    <!DOCTYPE HTML>
    <html>
    <head>
        <title>Выбор викторины</title>
    </head>
    <body>
        <form method="POST" action="/">
            <select name="quiz" id="quiz_list">
    '''
    # Для каждой викторины создаём элемент <option> с её id и названием
    for quiz in quizzes:
        html += '<option value="' + str(quiz["id"]) + '">' + quiz["title"] + '</option>\n'
    # Закрываем теги select, добавляем кнопку отправки и завершаем HTML
    html += '''
            </select>
            <input type="submit" value="Выбрать">
        </form>
    </body>
    </html>
    '''
    return html


def index():
    """
    Главная страница.
    При GET-запросе показывает форму выбора викторины.
    При POST-запросе (выбор сделан) сохраняет данные о викторине в сессию
    и перенаправляет на страницу первого вопроса.
    """
    if request.method == 'GET':
        # Просто показать форму
        return quiz_form()
    elif request.method == 'POST':
        # Получаем id выбранной викторины из формы
        quiz_id = request.form.get('quiz')
        if quiz_id:
            # Сохраняем в сессию id викторины
            session['quiz'] = int(quiz_id)
            # Начинаем с нулевого вопроса (ещё ни одного не задано)
            session['last_question'] = 0
            # Обнуляем счётчики правильных и всех ответов для новой викторины
            session['total'] = 0
            session['answers'] = 0
        # Переходим к обработчику вопросов
        return redirect(url_for('test'))


def test():
    """
    Обработчик вопросов викторины.
    При GET-запросе показывает первый/следующий вопрос.
    При POST-запросе сначала сохраняет ответ пользователя, затем показывает следующий вопрос.
    Если вопросы закончились – перенаправляет на страницу результата.
    """
    # Проверяем, выбрана ли викторина (есть ли ключ 'quiz' в сессии и он неотрицательный)
    if not ('quiz' in session) or int(session['quiz']) < 0:
        # Если нет – возвращаем на главную для выбора викторины
        return redirect(url_for('index'))
    else:
        # Если это отправка ответа (POST) – сохраняем его
        if request.method == 'POST':
            save_answers()
        # Получаем следующий вопрос после того, на котором остановились
        next_question = get_question_after(session['last_question'], session['quiz'])
        # Если вопросов больше нет (None или пустой кортеж) – показываем итоги
        if next_question is None or len(next_question) == 0:
            return redirect(url_for('result'))
        else:
            # Иначе отображаем форму с вопросом
            return question_form(next_question)


def result():
    """Страница с итоговым результатом викторины."""
    # Из сессии берём количество правильных ответов (по умолчанию 0) и общее число отвеченных вопросов
    return "Викторина окончена! Правильных ответов: " + str(session.get('answers', 0)) + " из " + str(session.get('total', 0))


# Регистрация URL-путей и связывание их с функциями-обработчиками
# Для главной страницы разрешены методы GET (показать форму) и POST (отправить выбранную викторину)
web_application.add_url_rule('/', 'index', index, methods=['POST', 'GET'])
# Для страницы /test разрешены GET (показать вопрос) и POST (отправить ответ)
web_application.add_url_rule('/test', 'test', test, methods=['POST', 'GET'])
# Для страницы /result только метод GET (просто показать результат)
web_application.add_url_rule('/result', 'result', result)

# Запуск веб-сервера только если файл выполняется как основная программа
if __name__ == "__main__":
    web_application.run()  # можно добавить debug=True для отладки