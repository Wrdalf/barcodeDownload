import requests
import time

# Настройки
API_BASE_URL = "https://www.sima-land.ru/api/v5"
API_KEY = "4c0859bef4a9209b57aa315bedee9b9d722607a65c432f2c448b458d74cff4a41494381ae77672df136bd3b6545ba5779a3257aa8ac683fb8e7f2ae0f87f6331"
INPUT_FILE = "clients/ОЗОН/output2404/input.txt"
OUTPUT_FILE = "clients/ОЗОН/output2404/output.txt"
MAX_REQUESTS_PER_SECOND = 75  # 750 за 10 секунд
MAX_ERRORS_PER_10_SECONDS = 50  # 50 ошибок за 10 секунд
SAVE_INTERVAL = 100  # Сохранение каждые 100 артикулов

headers = {"X-Api-Key": API_KEY, "Content-Type": "application/json"}

# Переменные для отслеживания
request_count = 0
error_count = 0
start_time = time.time()
error_start_time = time.time()

def read_articles(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]

def get_item_data(sid):
    global request_count, error_count, start_time, error_start_time
    url = f"{API_BASE_URL}/item/{sid}?by_sid=true"
    current_time = time.time()

    # Контроль частоты: 75 запросов в секунду
    if request_count >= MAX_REQUESTS_PER_SECOND:
        elapsed = current_time - start_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        request_count = 0
        start_time = time.time()

    # Контроль ошибок: ждём, если близко к 50 за 10 секунд
    if error_count >= MAX_ERRORS_PER_10_SECONDS - 5:
        if current_time - error_start_time < 10.0:
            sleep_time = 10.0 - (current_time - error_start_time)
            print(f"Приближаемся к лимиту ошибок, ждём {sleep_time:.2f} секунд...")
            time.sleep(sleep_time)
        error_count = 0
        error_start_time = time.time()

    try:
        response = requests.get(url, headers=headers, timeout=3)
        request_count += 1
        if response.status_code == 200:
            return response.json()
        else:
            error_count += 1
            if error_count == 1:
                error_start_time = time.time()
            print(f"Ошибка для SID {sid}: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        error_count += 1
        if error_count == 1:
            error_start_time = time.time()
        print(f"Ошибка запроса для SID {sid}: {e}")
        return None

def process_articles(articles):
    processed_count = 0
    buffer = []
    print("=== Обработка артикулов ===")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        for sid in articles:
            item_data = get_item_data(sid)
            if item_data:
                minimum_order_quantity = item_data.get("minimum_order_quantity", "1")  # Берем minimum_order_quantity из API, по умолчанию 1
                name = item_data.get("name", "Не указано")
                barcodes = item_data.get("barcodes", [])
                processed_count += 1
                line = f"{minimum_order_quantity}|{sid}|{name}|{'|'.join(barcodes) if barcodes else 'Нет штрихкодов'}\n"
                buffer.append(line)

                print(f"Min Qty: {minimum_order_quantity}")
                print(f"SID: {sid}")
                print(f"Name: {name}")
                print(f"Barcodes: {'|'.join(barcodes) if barcodes else 'Нет штрихкодов'}")
                print(f"Обработано: {processed_count}")
                print("---")

                # Сохранение каждые SAVE_INTERVAL артикулов
                if processed_count % SAVE_INTERVAL == 0:
                    file.writelines(buffer)
                    buffer.clear()

        # Записываем остаток буфера
        if buffer:
            file.writelines(buffer)

def main():
    articles = read_articles(INPUT_FILE)
    if not articles:
        print("Файл пуст или не найден.")
        return
    try:
        process_articles(articles)
    except KeyboardInterrupt:
        print("\nОстановлено пользователем. Данные сохранены в текстовый файл.")
        with open(OUTPUT_FILE, "a", encoding="utf-8") as file:
            file.writelines(buffer)  # Сохраняем буфер при остановке
    except Exception as e:
        print(f"\nПроизошла ошибка: {e}. Данные сохранены в текстовый файл.")
        with open(OUTPUT_FILE, "a", encoding="utf-8") as file:
            file.writelines(buffer)

if __name__ == "__main__":
    main()