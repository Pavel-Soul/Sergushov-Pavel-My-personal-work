from datetime import datetime, timedelta
import re
import regex

# Класс для работы с прочими сервисами
class OthServices:
    def __init__(self):
        # Дни недели
        self.days_of_week_short = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
        self.time_of_day = [ '7:00',  '7:30',  '8:00',  '8:30',  '9:00',  '9:30', '10:00', '10:30',
                            '11:00', '11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30',
                            '15:00', '15:30', '16:00', '16:30', '17:00', '17:30', '18:00', '18:30',
                            '19:00', '19:30', '20:00', '20:30', '21:00', '21:30', '22:00', '22:30']
        self.months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    # следующий месяц
    def get_next_month(self, dt):
        if dt.month == 12:
            next_month = datetime(dt.year + 1, 1, 1)
        else:
            # Иначе просто следующий месяц
            next_month = datetime(dt.year, dt.month + 1, 1)
        return next_month
    # предыдущий месяц
    def get_prev_month(self, dt):
        if dt.month == 1:
            prev_month = datetime(dt.year - 1, 12, 1)
        else:
            # Иначе просто следующий месяц
            prev_month = datetime(dt.year, dt.month - 1, 1)
        return prev_month
    # следующий месяц
    def get_next_month2(self, dt):
        if dt.month == 12:
            next_month = datetime(dt.year + 1, 1, 1, dt.hour, dt.minute)
        else:
            # Иначе просто следующий месяц
            next_month = datetime(dt.year, dt.month + 1, 1, dt.hour, dt.minute)
        return next_month
    # предыдущий месяц
    def get_prev_month2(self, dt):
        if dt.month == 1:
            prev_month = datetime(dt.year - 1, 12, 1, dt.hour, dt.minute)
        else:
            # Иначе просто следующий месяц
            prev_month = datetime(dt.year, dt.month - 1, 1, dt.hour, dt.minute)
        return prev_month
    # дни текущей недели
    def get_week_dates(self, date, days_cnt):
        # date = datetime.strptime(date_str, '%d.%m.%Y')
        start_of_week = date - timedelta(days=date.weekday())
        week = [start_of_week + timedelta(days=i) for i in range(days_cnt)]
        week_str = []
        for d in week:
            day_of_week = d.weekday()
            week_str.append([d.strftime('%d.%m.%Y'), self.days_of_week_short[day_of_week]])
        return week_str
    # матрица дней текущего месяца
    def get_month_dates(self, dt):
        # date = datetime.strptime(date_str, '%d.%m.%Y')
        # первый день месяца
        first_day_of_month = datetime(dt.year, dt.month, 1)
        # первый день недели первого дня месяца
        start_of_matrix = first_day_of_month - timedelta(days=first_day_of_month.weekday())
        # последний день месяца
        next_month = self.get_next_month(dt)
        last_day_of_month = next_month - timedelta(days=1)
        # Количество дней в матрице
        cnt_of_days = last_day_of_month.day + (6 - last_day_of_month.weekday()) + first_day_of_month.weekday()
        # матрица дат
        month = []
        for i in range(cnt_of_days):
            month.append(start_of_matrix + timedelta(days=i))
        return month
    def get_month_dates2(self, dt):
        # первый день месяца
        first_day_of_month = datetime(dt.year, dt.month, 1)
        # первый день недели первого дня месяца
        start_of_matrix = first_day_of_month - timedelta(days=first_day_of_month.weekday())
        # последний день месяца
        next_month = self.get_next_month(dt)
        last_day_of_month = next_month - timedelta(days=1)
        # Количество дней в матрице
        cnt_of_days = last_day_of_month.day + (6 - last_day_of_month.weekday()) + first_day_of_month.weekday()
        # матрица дат
        month = []
        for i in range(cnt_of_days):
            day = start_of_matrix + timedelta(days=i)
            # Сохраняем время из dt
            day_with_time = day.replace(hour=dt.hour, minute=dt.minute, second=dt.second)
            month.append(day_with_time)
        return month
    # будущие дни
    def get_fut_week_dates(self, date, days_cnt):
        week = [date + timedelta(days=i) for i in range(days_cnt)]
        week_str = []
        for d in week:
            day_of_week = d.weekday()
            if day_of_week != 6:
                week_str.append([d.strftime('%d.%m.%Y'), self.days_of_week_short[day_of_week]])
        return week_str
    # все даты между двумя заданными
    def get_all_dates_between(self, start_date_str, end_date_str):
        # Преобразование строк в объекты datetime
        start_date = datetime.strptime(start_date_str, "%d.%m.%Y")
        end_date = datetime.strptime(end_date_str, "%d.%m.%Y")
        # Генерация всех дат между start_date и end_date
        current_date = start_date
        dates = []
        while current_date <= end_date:
            dates.append(current_date.strftime("%d.%m.%Y"))
            current_date += timedelta(days=1)
        return dates
    # следующий день
    def get_next_date(self, date_str):
        return (datetime.strptime(date_str, '%d.%m.%Y') + timedelta(days=1)).strftime('%d.%m.%Y')
    # получение конца периода
    def get_end_time(self, date_str, time_str, duration_str):
        return (datetime.strptime(date_str + ' ' + time_str, '%d.%m.%Y %H:%M') + timedelta(minutes=int(duration_str.split(' ')[0]))).strftime('%H:%M')
    # Вывод дней недели, за которые можно записаться
    def get_future_dates_markup(self, date, button0, days_cnt):
        # Вывод будущих дней недели
        week_dates = self.get_fut_week_dates(datetime.now(), days_cnt)
        markup = []
        for i in range(len(week_dates)):
            style = 'primary'
            if week_dates[i][0] == date:
                style = 'base'
            elif datetime.strptime(week_dates[i][0], '%d.%m.%Y') < datetime.now()-timedelta(1):
                style = 'attention'
            markup.append({'text': week_dates[i][1], 'callbackData': button0 + ';' + week_dates[i][0], 'style': style})
        return [markup]
    # Вывод дней недели, за текущую неделю
    def get_week_dates_markup(self, date, start_week_date, button0, days_cnt):
        # Вывод дней недели
        week_dates = self.get_week_dates(datetime.strptime(start_week_date, '%d.%m.%Y'), days_cnt)
        markup = []
        for i in range(len(week_dates)):
            style = 'primary'
            if week_dates[i][0] == date:
                style = 'base'
            elif datetime.strptime(week_dates[i][0], '%d.%m.%Y') < datetime.now()-timedelta(1):
                style = 'attention'
            markup.append({'text': week_dates[i][1], 'callbackData': button0 + ';' + week_dates[i][0], 'style': style})
        markup = [markup]
        markup.append([{'text': '<<', 'callbackData': 'Новые даты;Назад;' + date + ';' + week_dates[0][0] + ';' + button0 , "style": 'primary'},
                       {'text': '>>', 'callbackData': 'Новые даты;Вперед;' + date + ';' + week_dates[0][0] + ';' + button0 , "style": 'primary'}])
        return markup
    # Выбор дней недели с прокруткой
    def get_week_dates_shift_markup_pattern(self, dt_str, week_dt_str, prefix, days_cnt):
        # Вывод дней текущей недели
        week_dates = self.get_week_dates(datetime.strptime(week_dt_str, '%d.%m.%Y'), days_cnt)
        # Заполнение markup датами
        markup = []
        for i in range(len(week_dates)):
            style = 'primary'
            if week_dates[i][0] == dt_str:
                style = 'base'
            elif datetime.strptime(week_dates[i][0], '%d.%m.%Y') < datetime.now() - timedelta(1):
                style = 'attention'
            markup.append({'text': week_dates[i][1], 'callbackData': prefix + week_dates[i][0], 'style': style})
        markup = [markup]
        # Добавление кнопок движения дат по неделям
        markup.append([{'text': '<<',
                        'callbackData': prefix + 'Даты;Назад;' + week_dates[0][0],
                        "style": 'primary'},
                       {'text': '>>',
                        'callbackData': prefix + 'Даты;Вперед;' + week_dates[0][0],
                        "style": 'primary'}])
        return markup, week_dates[0][0], week_dates[days_cnt-1][0]
    # Выбор дней в месяце с прокруткой месяца
    def get_month_dates_shift_markup_pattern(self, dt_str, month_dt_str, prefix):
        # Вывод дней текущей недели
        month_dates = self.get_month_dates(datetime.strptime(month_dt_str, '%d.%m.%Y'))
        # Заполнение markup датами
        markup = []
        for i in range(len(month_dates)//7):
            week = []
            for j in range(7):
                curr_dt = month_dates[i*7+j]
                curr_dt_str = curr_dt.strftime('%d.%m.%Y')
                style = 'primary'
                if curr_dt_str == dt_str:
                    style = 'attention'
                elif curr_dt < (datetime.now() - timedelta(1)) or month_dates[7].month != curr_dt.month:
                    style = 'base'
                week.append({'text': str(curr_dt.day), 'callbackData': prefix + curr_dt_str, 'style': style})
            markup.append(week)
        # Добавление кнопок движения дат по неделям
        markup.append([{'text': '<<',
                        'callbackData': prefix + 'Даты;Назад;' + month_dates[7].strftime('%d.%m.%Y'),
                        "style": 'primary'},
                       {'text': '>>',
                        'callbackData': prefix + 'Даты;Вперед;' + month_dates[7].strftime('%d.%m.%Y'),
                        "style": 'primary'}])
        return markup, self.months[month_dates[7].month-1] + ' ' + str(month_dates[7].year)
        # Выбор дней в месяце с прокруткой месяца
    def get_month_dates_shift_markup_pattern2(self, dt: datetime, month_dt: datetime, prefix: str):
        # Вывод дней текущей недели
        month_dates = self.get_month_dates2(month_dt)
        # Заполнение markup датами
        markup = []
        for i in range(len(month_dates) // 7):
            week = []
            for j in range(7):
                curr_dt = month_dates[i * 7 + j]
                curr_dt_str = curr_dt.strftime('%d.%m.%Y %H:%M')
                style = 'primary'
                #print(curr_dt, dt)
                if curr_dt == dt:
                    style = 'attention'
                elif curr_dt < (datetime.now() - timedelta(days=1)) or month_dates[7].month != curr_dt.month:
                    style = 'base'
                week.append({'text': str(curr_dt.day), 'callbackData': prefix + curr_dt_str, 'style': style})
            markup.append(week)
        # print(markup)
        # Добавление кнопок движения дат по неделям
        markup.append([{'text': '<<',
                        'callbackData': prefix + 'Даты;Назад;' + month_dates[7].strftime('%d.%m.%Y %H:%M'),
                        "style": 'primary'},
                       {'text': '>>',
                        'callbackData': prefix + 'Даты;Вперед;' + month_dates[7].strftime('%d.%m.%Y %H:%M'),
                        "style": 'primary'}])
        # print(markup)
        return markup, self.months[month_dates[7].month - 1] + ' ' + str(month_dates[7].year)
    # Найти дату со сдвигом
    def get_shift_date(self, dt_str, direct, shift):
        dt = datetime.strptime(dt_str, '%d.%m.%Y')
        if direct == 'Вперед':
            dt = (dt + timedelta(days=shift))
        elif dt < datetime.now():
            pass
        else:
            dt = (dt - timedelta(days=shift))
        return dt.strftime('%d.%m.%Y')
    # Найти месяц со сдвигом
    def get_shift_month(self, dt_str, direct):
        dt = datetime.strptime(dt_str, '%d.%m.%Y')
        if direct == 'Вперед':
            dt = self.get_next_month(dt)
        elif dt < datetime.now():
            pass
        else:
            dt = self.get_prev_month(dt)
        return dt.strftime('%d.%m.%Y')
    # Найти месяц со сдвигом
    def get_shift_month2(self, dt_str, direct):
        dt = datetime.strptime(dt_str, '%d.%m.%Y %H:%M')
        if direct == 'Вперед':
            dt = self.get_next_month2(dt)
        elif dt < datetime.now():
            pass
        else:
            dt = self.get_prev_month2(dt)
        return dt
    # Выбор времени c прокруткой
    def get_times_shift_markup_pattern(self, time_str, curr_time_str, prefix, times_cnt):
        # Вывод дней текущей недели
        times = self.time_of_day
        lt = len(times)
        # Заполнение markup датами
        markup = []
        # Поиск нужного диапозона данных
        for i in range(lt // times_cnt):
            j = min((i+1)*times_cnt-1, lt-1)
            if datetime.strptime('10.10.2000 ' + times[j], '%d.%m.%Y %H:%M') >= datetime.strptime('10.10.2000 ' + curr_time_str, '%d.%m.%Y %H:%M'):
                for k in range(i*times_cnt, j+1, 1):
                    style = 'attention' if times[k] == time_str else 'primary'
                    markup.append({'text': times[k], 'callbackData': prefix + times[k], 'style': style})
                break
        markup = [markup]
        # Добавление кнопок движения дат по неделям
        markup.append([{'text': '<<',
                        'callbackData': prefix + 'Время;Назад;' + times[i*times_cnt],
                        "style": 'primary'},
                       {'text': '>>',
                        'callbackData': prefix + 'Время;Вперед;' + times[i*times_cnt],
                        "style": 'primary'}])
        return markup
    # Найти время со сдвигом
    def get_shift_time(self, time_str, direct, shift):
        lt = len(self.time_of_day)
        for i in range(lt):
            if time_str == self.time_of_day[i]:
                break
        if direct == 'Вперед' and i + shift < lt:
            return self.time_of_day[i+shift]
        elif direct == 'Назад' and i - shift >= 0:
            return self.time_of_day[i-shift]
        return time_str
    # Выбор времени без прокрутки
    def get_times_markup_pattern(self, time_str, prefix, cols, rows):
        # Вывод дней текущей недели
        times = self.time_of_day
        # Заполнение markup датами
        markup = []
        for i in range(rows):
            markup1 = []
            for j in range(cols):
                style = 'primary'
                k = i*cols + j + 2
                if times[k] == time_str:
                    style = 'attention'
                #elif datetime.strptime(week_dates[i][0], '%d.%m.%Y') < datetime.now() - timedelta(1):
                    #style = 'attention'
                markup1.append({'text': times[k], 'callbackData': prefix + times[k], 'style': style})
            markup.append(markup1)
        return markup
    # Выбор длительности
    def get_duration_markup_pattern(self, date_str, time_str, dur, prefix):
        # Вывод дней текущей недели
        durs = ['45', '60', '90', '120','480']
        # Заполнение markup датами
        markup = []
        for i in range(len(durs)):
            style = 'primary'
            if durs[i] == dur:
                style = 'base'
            #elif datetime.strptime(week_dates[i][0], '%d.%m.%Y') < datetime.now() - timedelta(1):
                #style = 'attention'
            markup.append({'text': durs[i], 'callbackData': prefix + durs[i], 'style': style})
        markup = [markup]
        return markup
    # Вывод времени за текущий день
    def get_day_times_markup(self, date, start_week_date, button0, times_cnt):
        # Вывод дней недели
        times = self.time_of_day[:4]
        markup = [times]
        '''
        for i in range(len(week_dates)):
            style = 'primary'
            if week_dates[i][0] == date:
                style = 'base'
            elif datetime.strptime(week_dates[i][0], '%d.%m.%Y') < datetime.now()-timedelta(1):
                style = 'attention'
            markup.append({'text': week_dates[i][1], 'callbackData': button0 + ';' + week_dates[i][0], 'style': style})
        '''
        markup = [markup]
        markup.append([{'text': '<<', 'callbackData': 'Новые даты;Назад;' + date + ';' + 'week_dates[0][0]' + ';' + button0 , "style": 'primary'},
                       {'text': '>>', 'callbackData': 'Новые даты;Вперед;' + date + ';' + 'week_dates[0][0]' + ';' + button0 , "style": 'primary'}])
        return markup
    # Преобразование массива в текст
    def list_to_txt(self, lst, length):
        curr_len = 0
        txt = ''
        for elem in lst:
            if curr_len + len(elem) > length:
                txt += '\n' + elem + ' '
                curr_len = len(elem) + 1
            else:
                curr_len = curr_len + len(elem) + 1
                txt += elem + ' '
        return txt
    # Проверка, что текст содержит только буквы, цифры и знаки препинания
    def is_text_valid(self, txt):
        # Регулярное выражение для буквенно-цифровых символов, знаков препинания и пробелов
        pattern = regex.compile(r'[\p{L}\p{N}\p{P}\s]+', regex.UNICODE)
        
        # Удаляем все разрешенные символы из текста
        cleaned_text = pattern.sub('', txt)
        
        # Если текст пуст после удаления, значит он содержал только разрешенные символы
        return cleaned_text == ''
    # Ближайшие дата и время
    def find_nearest_day_and_time(self, day_of_week: int, target_time: str):
        # Преобразуем target_time в объект времени
        target_hour, target_minute = map(int, target_time.split(':'))
        # Получаем текущую дату и время
        now = datetime.now()
        # Вычисляем разницу в днях до целевого дня недели
        days_until_target = (day_of_week - now.isoweekday()) % 7
        nearest_day = now + timedelta(days=days_until_target)
        # Устанавливаем целевое время
        nearest_day_with_time = nearest_day.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        # Если текущее время уже прошло, берем следующий неделю
        if now > nearest_day_with_time:
            nearest_day_with_time += timedelta(weeks=1)
        return nearest_day_with_time