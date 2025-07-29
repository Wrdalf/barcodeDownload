import pandas as pd
from collections import Counter
from tqdm import tqdm
import csv

# Сообщение о начале работы
print("Запуск программы...")

# Чтение первого Excel-файла (с артикулами и штрихкодами)
print("Чтение файла всеШкПМДК.xlsx...")
try:
    df1 = pd.read_excel('всеШкПМДК.xlsx', dtype=str, engine='openpyxl')
    print(f"Файл всеШкПМДК.xlsx успешно прочитан. Количество строк: {len(df1)}")
    print("Имена столбцов в df1:", df1.columns.tolist())
except Exception as e:
    print(f"Ошибка при чтении файла всеШкПМДК.xlsx: {e}")
    exit()

# Удаляем пустой столбец, если он есть
df1 = df1.loc[:, ~df1.columns.str.contains('^Unnamed')]

# Чтение второго файла (предположим, он тоже в формате Excel, например, шкОстатков.xlsx)
print("Чтение второго файла (шкОстатков.xlsx)...")
try:
    df2 = pd.read_excel('шкОстатков.xlsx', dtype=str, header=None, engine='openpyxl')
    df2.columns = ['Штрихкод']
    print(f"Файл шкОстатков.xlsx успешно прочитан. Количество строк: {len(df2)}")
except Exception as e:
    print(f"Ошибка при чтении файла шкОстатков.xlsx: {e}")
    exit()

# Подсчитываем количество повторений каждого штрихкода во втором файле
print("Подсчет повторений штрихкодов во втором файле...")
barcode_counts = Counter(df2['Штрихкод'])
print(f"Подсчет завершен. Уникальных штрихкодов: {len(barcode_counts)}")

# Создаем словарь для сопоставления штрихкода с артикулом
barcode_to_article = {}
print("Создание словаря штрихкод-артикул...")

# Используем tqdm для отображения прогресса
for index, row in tqdm(df1.iterrows(), total=len(df1), desc="Обработка строк первого файла"):
    article = row['Артикул']
    for i in range(1, 6):
        barcode = row[f'Штрихкод {i}']
        if pd.notna(barcode):
            barcode_to_article[barcode] = article

print(f"Словарь штрихкод-артикул создан. Количество записей: {len(barcode_to_article)}")

# Создаем список для записи результатов
results = []
print("Сопоставление штрихкодов из второго файла...")

# Используем tqdm для отображения прогресса
for barcode in tqdm(barcode_counts.keys(), desc="Обработка штрихкодов второго файла"):
    if barcode in barcode_to_article:
        article = barcode_to_article[barcode]
        count = barcode_counts[barcode]
        results.append(f"Штрихкод: {barcode}, Артикул: {article}, Количество: {count}")
    else:
        results.append(f"Штрихкод: {barcode}, Артикул: Не найден, Количество: {barcode_counts[barcode]}")

print(f"Сопоставление завершено. Количество результатов: {len(results)}")

# Записываем результаты в текстовый файл
print("Запись результатов в файл output.txt...")
with open('output.txt', 'w', encoding='utf-8') as f:
    for line in tqdm(results, desc="Запись в файл"):
        f.write(line + '\n')

print("Результаты успешно записаны в файл output.txt")
print("Программа завершена.")