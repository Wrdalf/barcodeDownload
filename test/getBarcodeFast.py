import aiohttp
import asyncio
import time
import os
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import signal

class SimaLandBarcodeExporter:
    def __init__(self):
        self.api_base_url = "https://www.sima-land.ru/api/v5"
        self.api_key = "4c0859bef4a9209b57aa315bedee9b9d722607a65c432f2c448b458d74cff4a41494381ae77672df136bd3b6545ba5779a3257aa8ac683fb8e7f2ae0f87f6331"
        self.input_file = "clients/ОЗОН/output2404/input.txt"
        self.output_file = "clients/ОЗОН/output2404/output.txt"
        self.errors_file = "clients/ОЗОН/output2404/errors.txt"
        self.invalid_sids_file = "clients/ОЗОН/output2404/invalid_sids.txt"
        self.max_requests_per_10_seconds = 750  # 75/сек
        self.max_errors_per_10_seconds = 50
        self.save_interval = 100
        self.chunk_size = 1000
        self.max_concurrent = 10
        self.timeout = 3
        self.retry_attempts = 3
        self.headers = {"X-Api-Key": self.api_key, "Content-Type": "application/json"}
        self.processed_count = 0
        self.error_count = 0
        self.invalid_count = 0
        self.request_count = 0
        self.start_time = time.time()
        self.error_start_time = time.time()
        self.buffer = []
        self.error_buffer = []
        self.invalid_buffer = []
        self.shutdown_requested = False
        self.semaphore = asyncio.Semaphore(self.max_requests_per_10_seconds // 10)  # ~75/сек
        self.chunks = deque()
        self.lock = asyncio.Lock()

    def setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        print("\nСохранение данных перед выходом...")
        self.shutdown_requested = True
        self.save_buffers()
        print("Выход завершен.")
        exit(0)

    def read_articles(self):
        try:
            with open(self.input_file, "r", encoding="utf-8") as file:
                articles = [line.strip() for line in file if line.strip()]
            # Разделение на чанки по 1000
            self.chunks = deque([articles[i:i + self.chunk_size] for i in range(0, len(articles), self.chunk_size)])
            print(f"Загружено {len(articles)} артикулов, разделено на {len(self.chunks)} чанков")
            return articles
        except Exception as e:
            print(f"Ошибка чтения файла {self.input_file}: {e}")
            return []

    async def save_buffers(self):
        async with self.lock:
            try:
                with open(self.output_file, "a", encoding="utf-8") as f:
                    f.writelines(self.buffer)
                self.buffer.clear()
            except Exception as e:
                print(f"Ошибка сохранения в {self.output_file}: {e}")
            try:
                with open(self.errors_file, "a", encoding="utf-8") as f:
                    f.writelines(self.error_buffer)
                self.error_buffer.clear()
            except Exception as e:
                print(f"Ошибка сохранения в {self.errors_file}: {e}")
            try:
                with open(self.invalid_sids_file, "a", encoding="utf-8") as f:
                    f.writelines(self.invalid_buffer)
                self.invalid_buffer.clear()
            except Exception as e:
                print(f"Ошибка сохранения в {self.invalid_sids_file}: {e}")

    async def get_item_data(self, session, sid):
        url = f"{self.api_base_url}/item/{sid}?by_sid=true"
        async with self.semaphore:
            for attempt in range(self.retry_attempts):
                try:
                    async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                        self.request_count += 1
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 404:
                            async with self.lock:
                                self.invalid_count += 1
                                self.invalid_buffer.append(f"{sid}|Не найден на Сима-ленде\n")
                            return None
                        elif response.status == 429:
                            async with self.lock:
                                self.error_count += 1
                                if self.error_count == 1:
                                    self.error_start_time = time.time()
                            retry_after = int(response.headers.get('Retry-After', 10))
                            print(f"Лимит запросов (429) для SID {sid}, ждём {retry_after} сек...")
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            async with self.lock:
                                self.error_count += 1
                                if self.error_count == 1:
                                    self.error_start_time = time.time()
                                self.error_buffer.append(f"{sid}|Ошибка {response.status}: {await response.text()}\n")
                            return None
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    async with self.lock:
                        self.error_count += 1
                        if self.error_count == 1:
                            self.error_start_time = time.time()
                        self.error_buffer.append(f"{sid}|Ошибка запроса: {e}\n")
                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(1)
            return None

    async def process_chunk(self, session, chunk):
        for sid in chunk:
            if self.shutdown_requested:
                break
            # Контроль ошибок: пауза при 45 ошибках за 10 сек
            async with self.lock:
                if self.error_count >= self.max_errors_per_10_seconds - 5:
                    current_time = time.time()
                    if current_time - self.error_start_time < 10.0:
                        sleep_time = 10.0 - (current_time - self.error_start_time)
                        print(f"Приближаемся к лимиту ошибок ({self.error_count}), ждём {sleep_time:.2f} сек...")
                        await asyncio.sleep(sleep_time)
                    self.error_count = 0
                    self.error_start_time = time.time()

            item_data = await self.get_item_data(session, sid)
            if item_data:
                async with self.lock:
                    minimum_order_quantity = item_data.get("minimum_order_quantity", "1")
                    name = item_data.get("name", "Не указано")
                    barcodes = item_data.get("barcodes", [])
                    self.processed_count += 1
                    line = f"{minimum_order_quantity}|{sid}|{name}|{'|'.join(barcodes) if barcodes else 'Нет штрихкодов'}\n"
                    self.buffer.append(line)

                    print(f"Min Qty: {minimum_order_quantity}")
                    print(f"SID: {sid}")
                    print(f"Name: {name}")
                    print(f"Barcodes: {'|'.join(barcodes) if barcodes else 'Нет штрихкодов'}")
                    print(f"Обработано: {self.processed_count} | Пропущено ошибок: {self.error_count} | Неверных SID: {self.invalid_count}")
                    elapsed = time.time() - self.start_time
                    print(f"Скорость: {self.processed_count / elapsed:.2f} арт/сек")
                    print("---")

                    if self.processed_count % self.save_interval == 0:
                        await self.save_buffers()

    async def worker(self, session):
        while self.chunks and not self.shutdown_requested:
            async with self.lock:
                if not self.chunks:
                    break
                chunk = self.chunks.popleft()
            await self.process_chunk(session, chunk)

    async def export_barcodes(self):
        print("=== Обработка артикулов ===")
        async with aiohttp.ClientSession() as session:
            tasks = [self.worker(session) for _ in range(self.max_concurrent)]
            await asyncio.gather(*tasks)
        await self.save_buffers()

    def run(self):
        self.setup_signal_handlers()
        articles = self.read_articles()
        if not articles:
            print("Файл пуст или не найден.")
            return
        try:
            asyncio.run(self.export_barcodes())
        except KeyboardInterrupt:
            print("\nОстановлено пользователем.")
        except Exception as e:
            print(f"\nПроизошла ошибка: {e}.")
        finally:
            self.save_buffers()
        elapsed = time.time() - self.start_time
        print(f"\nВсего обработано: {self.processed_count} артикулов")
        print(f"Пропущено из-за ошибок: {self.error_count}")
        print(f"Неверных SID: {self.invalid_count}")
        print(f"Скорость: {self.processed_count / elapsed:.2f} арт/сек")
        print(f"Время выполнения: {elapsed:.2f} секунд")

if __name__ == "__main__":
    exporter = SimaLandBarcodeExporter()
    exporter.run