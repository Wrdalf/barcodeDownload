import requests

def check_wb_api_key(api_key, api_type='content'):
    """
    Проверяет работоспособность API ключа Wildberries
    
    :param api_key: Ваш API ключ Wildberries
    :param api_type: Тип API ('content' или 'marketplace')
    :return: True если ключ работает, False если нет
    """
    headers = {
        'Authorization': api_key
    }
    
    if api_type.lower() == 'content':
        # Тестовый запрос к Content API
        url = 'https://suppliers-api.wildberries.ru/api/v2/stocks'
    elif api_type.lower() == 'marketplace':
        # Тестовый запрос к Marketplace API
        url = 'https://statistics-api.wildberries.ru/api/v1/supplier/incomes'
    else:
        raise ValueError("Неверный тип API. Допустимые значения: 'content' или 'marketplace'")
    
    try:
        response = requests.get(url, headers=headers)
        
        # Код 200 означает успешный запрос (ключ работает)
        if response.status_code == 200:
            return True
        # Код 401 означает неавторизованный доступ (неверный ключ)
        elif response.status_code == 401:
            return False
        # Другие коды могут означать разные ошибки
        else:
            print(f"Неожиданный код ответа: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Произошла ошибка при проверке API ключа: {e}")
        return False


# Пример использования
if __name__ == "__main__":
    your_api_key = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjQxMDE2djEiLCJ0eXAiOiJKV1QifQ.eyJlbnQiOjEsImV4cCI6MTc0NjMyMjE4NCwiaWQiOiIwMTkyZWQxMS00MmQ5LTdlZTMtOTkzOC1jZjRmMTU2ODRhZDMiLCJpaWQiOjE4NDY4ODE5LCJvaWQiOjEyNzAzMzIsInMiOjc5MzQsInNpZCI6ImNjYjAyMjE5LWUxM2QtNDQ0Ni05OWQ0LWZiOWVlZWI1YmFkYSIsInQiOmZhbHNlLCJ1aWQiOjE4NDY4ODE5fQ.I8Zn_wIdKGII2ynoZkI7yfUWNOO2Ud8v8Rq6uDpD1lMGBEHE_WhP4KPUNy1wnXN2cFCLW9ROVXAJGd0U2QTa8Q"  # Замените на ваш реальный API ключ
    api_type = "marketplace"  # Или "marketplace" для Marketplace API
    
    is_valid = check_wb_api_key(your_api_key, api_type)
    
    if is_valid:
        print("API ключ работает корректно!")
    else:
        print("API ключ не работает или неверен.")