# check_missed_articles.py

INPUT_FILE = "clients/ОЗОН/allBarcodes.txt"
OUTPUT_FILE = "clients/ОЗОН/output_fast.txt"
MISSED_FILE = "clients/ОЗОН/miss.txt" 


def read_articles(file_path):
    """Читает артикулы из input.txt и возвращает множество."""
    articles = set()
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    articles.add(line)
    except FileNotFoundError:
        print(f"Файл {file_path} не найден.")
    return articles

def read_processed_articles(file_path):
    """Читает обработанные артикулы из output.txt и возвращает множество SID."""
    processed_articles = set()
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    # Формат строки в output.txt: min_qty|sid|name|barcode1|barcodeN
                    parts = line.split("|")
                    if len(parts) >= 2:  # Убедимся, что есть хотя бы min_qty и sid
                        sid = parts[1]  # SID — второй столбец
                        processed_articles.add(sid)
    except FileNotFoundError:
        print(f"Файл {file_path} не найден.")
    return processed_articles

def find_missed_articles(input_articles, processed_articles):
    """Находит пропущенные артикулы (те, что есть в input.txt, но нет в output.txt)."""
    return input_articles - processed_articles

def save_missed_articles(missed_articles):
    """Сохраняет пропущенные артикулы в новый файл missed_articles.txt."""
    if not missed_articles:
        print("Пропущенных артикулов нет.")
        return
    with open(MISSED_FILE, "w", encoding="utf-8") as file:
        for article in sorted(missed_articles):  # Сортируем для удобства
            file.write(f"{article}\n")
    print(f"Пропущенные артикулы сохранены в {MISSED_FILE}. Всего пропущено: {len(missed_articles)}")

def main():
    # Читаем исходные артикулы из input.txt
    input_articles = read_articles(INPUT_FILE)
    if not input_articles:
        print("Исходный файл input.txt пуст или не найден. Завершение.")
        return

    # Читаем обработанные артикулы из output.txt
    processed_articles = read_processed_articles(OUTPUT_FILE)

    # Находим пропущенные артикулы
    missed_articles = find_missed_articles(input_articles, processed_articles)

    # Сохраняем пропущенные артикулы в новый файл
    save_missed_articles(missed_articles)

if __name__ == "__main__":
    main()