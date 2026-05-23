
import requests
import re

def check_sql_injection(url, parameter, payload="' OR '1'='1"):
    try:
        target_url = f"{url}?{parameter}={payload}"
        response = requests.get(target_url, timeout=10)
        # Простая эвристика: если ответ изменился или содержит SQL-ошибки
        if any(err in response.text.lower() for err in ["sql syntax", "mysql_fetch", "ora-01756", "sqlite3.error"]):
            return True, f"Возможная SQL-инъекция обнаружена на {url}. Ответ содержит SQL-ошибку."
        return False, "SQL-ошибок не обнаружено."
    except Exception as e:
        return False, f"Ошибка при проверке SQL-инъекции: {e}"

def check_xss(url, parameter, payload="<script>alert('XSS')</script>"):
    try:
        target_url = f"{url}?{parameter}={payload}"
        response = requests.get(target_url, timeout=10)
        if payload in response.text:
            return True, f"Возможная XSS обнаружена на {url}. Пейлоад отражен в ответе."
        return False, "XSS не обнаружена."
    except Exception as e:
        return False, f"Ошибка при проверке XSS: {e}"
