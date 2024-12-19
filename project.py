import csv
import os
import re
from fuzzywuzzy import fuzz, process
from logger_config import setup_log


class PriceMachine:

    def __init__(self):
        self.data = []
        self.logger = setup_log()  # Настройка логирования
        # self.result = ''
        # self.name_length = 0

    def load_prices(self, Prices='.'):
        """
            Сканирует указанный каталог. Ищет файлы со словом price в названии.
            В файле ищет столбцы с названием товара, ценой и весом.
            Допустимые названия для столбца с товаром:
                товар
                название
                наименование
                продукт

            Допустимые названия для столбца с ценой:
                розница
                цена

            Допустимые названия для столбца с весом (в кг.)
                вес
                масса
                фасовка
        """
        self.logger.info('Загрузка файлов из каталога: %s', Prices)

        for filename in os.listdir('Prices'):

            self.logger.debug(f"Проверка файла: %s", filename)
            if 'price' in filename and filename.endswith('.csv'):
                filepath = os.path.join(Prices, filename)
                self.replace_with_semicolon(filepath)
                with open(filepath, encoding='utf-8') as file:
                    reader = csv.reader(file, delimiter=';')
                    headers = next(reader)

                    product_idx, price_idx, weight_idx = self._search_product_price_weight(headers)

                    for r in reader:
                        if product_idx is not None and price_idx is not None and weight_idx is not None:
                            product_name = r[product_idx]
                            price = float(r[price_idx])
                            weight = float(r[weight_idx])
                            if weight <= 0:
                                self.logger.warning('Пропуск товара %s с некорректным весом: %s', product_name, weight)
                                continue

                            price_kg = price / weight
                            self.data.append({
                                'name': product_name,
                                'price': price,
                                'file_path': filename,
                                'weight': weight,
                                'price_kg': price_kg,
                            })
        self.logger.info('Загрузка цен завершена. Загружено позиций: %d', len(self.data))
        return len(self.data)

    def replace_with_semicolon(self, Prices):
        """Заменяет все запятые на точку с запятой в CSV-файле"""
        self.logger.info('Обработка файла: %s', Prices)
        with open(Prices, 'r', encoding='utf-8') as file:
            content = file.read()


        content = re.sub(r'(?<!")\,(?!")', ';', content)

        with open(Prices, 'w', encoding='utf-8') as file:
            file.write(content)

        self.logger.debug('Файл %s успешно обработан.', Prices)

    def _search_product_price_weight(self, head):

        product_head = ["название", "продукт", "товар", "наименование"]
        price_head = ["цена", "розница"]
        weight_head = ["фасовка", "масса", "вес"]

        product_idx = next((i for i, h in enumerate(head) if h in product_head), None)
        price_idx = next((i for i, h in enumerate(head) if h in price_head), None)
        weight_idx = next((i for i, h in enumerate(head) if h in weight_head), None)

        return product_idx, price_idx, weight_idx

    def export_to_html(self, fname='output.html'):
        """Экспортируем данные в HTML-файл."""

        result = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Позиции продуктов</title>
        </head>
        <body>
            <table>
                <tr>
                    <th>Номер</th>
                    <th>Название</th>
                    <th>Цена</th>
                    <th>Фасовка</th>
                    <th>Файл</th>
                    <th>Цена за кг.</th>
                </tr>
        '''
        for index, item in enumerate(self.data, start=1):

            result += f'''
                    <tr><td>{index}</td><td>{item['name']}</td><td>{item['price']:.2f}</td><td>{item['weight']}</td><td>{item['file_path']}</td><td>{item['price_kg']:.2f}</td></tr>'''

        result += '''
                    </table>
                </body>
                </html>
                '''

        with open(fname, 'w', encoding='utf-8') as file:
            file.write(result)
        self.logger.info('Данные успешно экспортированы в %s.', fname)
        return f'Данные успешно импортированы в {fname}.'


    def _normalize_text(self,text):
        """Приводит текст к нижнему регистру и удаляет лишние пробелы."""
        return text.lower().strip()


    def _find_similar_names(self,text, product_names, similarity_threshold=60):
        """Находит схожие названия продуктов на основе нечеткого сравнения."""
        matched_items = process.extract(text, product_names, limit=None, scorer=fuzz.ratio)
        return {match for match, score in matched_items if score > similarity_threshold}


    def find_text(self, text):
        """Ищет и возвращает продукты с названиями, похожими на введённый текст."""
        text = self._normalize_text(text)
        product_names = [self._normalize_text(item['name']) for item in self.data]

        matched_names = self._find_similar_names(text, product_names)

        results = [
            item for item in self.data
            if re.search(r'\b' + re.escape(text) + r'\b', self._normalize_text(item['name'])) or self._normalize_text(
                item['name']) in matched_names
        ]

        return sorted(results, key=lambda x: x['price_kg'])


#     Логика работы программы
if __name__ == '__main__':

    pm = PriceMachine()
    print(pm.load_prices('Prices'))
    print(pm.export_to_html())

    while True:
        search_text = input('Введите текст для поиска или "exit" для выхода: ')
        if search_text == 'exit':
            pm.logger.info('Завершаем работу')
            print('Завершаем работу')
            break

        found_items = pm.find_text(search_text)

        if found_items:
            pm.logger.info('Найдено %d позиций по запросу "%s"', len(found_items), search_text)
            print(f'Найдено {len(found_items)} позиций:')
            print('№\tНаименование\t\t\t\t\t\t\tЦена\t Вес\tФайл\t\t\tЦена за кг.')

            for index, item in enumerate(found_items, start=1):

                print(f'{index:<3}\t'
                      f'{item["name"]:<35}\t'
                      f'{item["price"]:>10.2f}\t'  
                      f'{item["weight"]:>5}\t'  
                      f'{item["file_path"]:<15}\t'
                      f'{item["price_kg"]:>8.2f}')

        else:
            pm.logger.info('Ничего не найдено для запроса "%s"', search_text)
            print('Ничего не найдено')