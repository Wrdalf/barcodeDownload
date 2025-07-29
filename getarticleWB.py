import requests
import json
import time
import os
from pathlib import Path
import signal
from concurrent.futures import ThreadPoolExecutor

class WBVendorCodeExporter:
    def __init__(self):
        self.api_key = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwNDE3djEiLCJ0eXAiOiJKV1QifQ.eyJlbnQiOjEsImV4cCI6MTc2MjIwMjA1OSwiaWQiOiIwMTk2OWY5NC1lY2M3LTc0NTgtYjI2ZC1kNmY1YzlkNGI0YjMiLCJpaWQiOjE4NDY4ODE5LCJvaWQiOjEyNzAzMzIsInMiOjc5MzQsInNpZCI6ImNjYjAyMjE5LWUxM3QtNDQ0Ni05OWQ0LWZiOWVlZWI1YmFkYSIsInQiOmZhbHNlLCJ1aWQiOjE4NDY4ODE5fQ.ccnEqrSvI76sVMzRcO4VsJq2WXZIcuPi3Nc4V2TJWhUtuw8-g-eVQtDpeREI78SRpAjlyBaIDCr7bn9gzQL8Vg"
        self.base_url = "https://content-api.wildberries.ru/content/v2/get/cards/list"
        self.headers = {"Authorization": self.api_key}  # Точный формат из исходного кода
        self.vendor_codes = set()
        self.backup_file = "wb_temp_backup.json"
        self.output_file = "wb_vendor_codes.txt"
        self.checkpoint_interval = 1000
        self.last_saved_count = 0
        self.shutdown_requested = False
        self.total_requests = 0
        self.start_time = time.time()
        self.max_limit = 100
        self.timeout = 20
        self.retry_attempts = 5
        self.max_workers = 3  # Уменьшено для стабильности
        self.requests_per_minute = 100
        self.missed_cursors = []

    def setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        print("\nСохранение данных перед выходом...")
        self.shutdown_requested = True
        self.save_progress()
        self.save_final_results()
        print("Выход завершен.")
        exit(0)

    def save_progress(self):
        try:
            data = {
                "vendor_codes": list(self.vendor_codes),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.backup_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\nСохранено {len(self.vendor_codes)} артикулов во временный файл")
        except Exception as e:
            print(f"\nОшибка сохранения: {e}")

    def save_final_results(self):
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.vendor_codes)))
            print(f"\nФинальный результат сохранен в {self.output_file}")
            if os.path.exists(self.backup_file):
                os.remove(self.backup_file)
                print(f"Временный файл {self.backup_file} удален")
        except Exception as e:
            print(f"\nОшибка сохранения финального результата: {e}")

    def get_cards_batch(self, cursor=None):
        session = requests.Session()  # Новая сессия для каждого потока
        payload = {
            "settings": {
                "cursor": cursor or {"limit": self.max_limit},
                "filter": {"withPhoto": -1}
            }
        }
        for attempt in range(self.retry_attempts):
            try:
                print(f"Отправка запроса: cursor={cursor}, попытка {attempt + 1}")
                response = session.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )
                self.total_requests += 1
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"Лимит запросов! Ждем {retry_after} сек...")
                    time.sleep(retry_after)
                    continue
                if response.status_code == 401:
                    print("Ошибка: Токен недействителен (401 Unauthorized). Проверьте токен.")
                    return None
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"Ошибка запроса: {e}. Повтор через 5 сек...")
                if attempt < self.retry_attempts - 1:
                    time.sleep(5)
        print(f"Пропущен запрос для cursor={cursor} после {self.retry_attempts} попыток")
        return None

    def process_batch(self, cursor):
        data = self.get_cards_batch(cursor)
        if not data:
            self.missed_cursors.append(cursor)
            return None
        cards = data.get("cards", [])
        if not cards:
            return None
        new_codes = {card.get("vendorCode") for card in cards if card.get("vendorCode")}
        self.vendor_codes.update(new_codes)
        if len(cards) == self.max_limit:
            next_cursor = {
                "updatedAt": cards[-1]["updatedAt"],
                "nmID": cards[-1]["nmID"],
                "limit": self.max_limit
            }
        else:
            next_cursor = None
        elapsed = time.time() - self.start_time
        print(f"Выгружено: {len(self.vendor_codes)} | Скорость: {len(self.vendor_codes)/elapsed:.1f} арт/сек", end='\r')
        if len(self.vendor_codes) - self.last_saved_count >= self.checkpoint_interval:
            self.save_progress()
            self.last_saved_count = len(self.vendor_codes)
        return next_cursor

    def export_vendor_codes(self):
        print("=== Выгрузка vendorCode ===")
        print(f"API ключ: {'*'*10}{self.api_key[-5:]}\n")

        cursors = [None]
        processed_cursors = set()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while cursors and not self.shutdown_requested:
                print(f"Обработка {len(cursors)} курсоров...")
                future_to_cursor = {executor.submit(self.process_batch, cursor): cursor for cursor in cursors}
                cursors = []
                for future in future_to_cursor:
                    if self.shutdown_requested:
                        break
                    cursor = future_to_cursor[future]
                    try:
                        next_cursor = future.result()
                        if next_cursor:
                            cursor_key = json.dumps(next_cursor, sort_keys=True)
                            if cursor_key not in processed_cursors:
                                cursors.append(next_cursor)
                                processed_cursors.add(cursor_key)
                    except Exception as e:
                        print(f"\nОшибка обработки cursor={cursor}: {e}")
                        self.missed_cursors.append(cursor)
                    time.sleep(60 / self.requests_per_minute / self.max_workers)

        for attempt in range(2):
            if not self.missed_cursors or self.shutdown_requested:
                break
            print(f"\nПовторная обработка {len(self.missed_cursors)} пропущенных курсоров, попытка {attempt + 1}...")
            current_missed = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_cursor = {executor.submit(self.process_batch, cursor): cursor for cursor in self.missed_cursors}
                for future in future_to_cursor:
                    if self.shutdown_requested:
                        break
                    cursor = future_to_cursor[future]
                    try:
                        next_cursor = future.result()
                        if next_cursor:
                            cursor_key = json.dumps(next_cursor, sort_keys=True)
                            if cursor_key not in processed_cursors:
                                current_missed.append(next_cursor)
                                processed_cursors.add(cursor_key)
                    except Exception as e:
                        print(f"\nОшибка обработки cursor={cursor}: {e}")
                        current_missed.append(cursor)
                    time.sleep(60 / self.requests_per_minute / self.max_workers)
            self.missed_cursors = current_missed

        if self.missed_cursors:
            print(f"\nОсталось {len(self.missed_cursors)} пропущенных курсоров после всех попыток")

    def run(self):
        self.setup_signal_handlers()
        self.export_vendor_codes()
        if not self.shutdown_requested:
            self.save_final_results()
        print(f"\nВсего запросов: {self.total_requests}")
        elapsed = time.time() - self.start_time
        print(f"Всего выгружено: {len(self.vendor_codes)} vendor codes")
        print(f"Скорость: {len(self.vendor_codes)/elapsed:.1f} арт/сек")

if __name__ == "__main__":
    start_time = time.time()
    exporter = WBVendorCodeExporter()
    exporter.run()
    end_time = time.time()
    print(f"Время выполнения: {end_time - start_time:.2f} секунд")