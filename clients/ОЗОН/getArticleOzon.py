import requests
import json

def get_ozon_offer_ids():
    url = "https://api-seller.ozon.ru/v3/product/list"
    headers = {
        "Api-Key": "cb2147f6-1bed-4577-959d-5b3b68a645e5",  # Ваш API-ключ
        "Client-Id": "18895",                              # Ваш Client-Id
        "Content-Type": "application/json"
    }
    
    payload = {
        "filter": {
            "visibility": "ALL"  # Получаем все товары
        },
        "last_id": "",
        "limit": 1000  # Максимальный лимит за запрос
    }
    
    all_offer_ids = []  # Список для хранения артикулов
    
    while True:
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                print(f"Ошибка: {response.status_code} - {response.text}")
                break
            
            data = response.json()
            products = data.get('result', {}).get('items', [])
            
            # Извлекаем offer_id из каждого товара
            offer_ids = [product.get('offer_id') for product in products if product.get('offer_id')]
            all_offer_ids.extend(offer_ids)
            
            last_id = data.get('result', {}).get('last_id', '')
            print(f"Получено артикулов: {len(all_offer_ids)}")
            
            # Если больше нет страниц или данных меньше лимита, выходим
            if not last_id or len(products) < payload["limit"]:
                break
                
            payload["last_id"] = last_id
            
        except Exception as e:
            print(f"Произошла ошибка: {str(e)}")
            break
    
    # Сохраняем результат в файл
    with open('ozon_offer_ids.json', 'w', encoding='utf-8') as f:
        json.dump(all_offer_ids, f, ensure_ascii=False, indent=2)
    
    return all_offer_ids

if __name__ == "__main__":
    offer_ids = get_ozon_offer_ids()
    print(f"Всего выгружено артикулов: {len(offer_ids)}")