import typer
import time
import requests as req
import os


def make_request_with_retries( url: str, data: dict, max_retries: int = 6) :
    attempt = 0
    while attempt < max_retries:
        try:
            response = req.post(url=url, data=data, timeout=60)
            return response
        except req.RequestException as e:
            attempt += 1
            if attempt < max_retries:
                time.sleep(1.5) 

def read_file( path: str):
    if os.path.exists(path):
        with open(path, "r") as file:
            return list(set(line.strip() for line in file))
    else:
        raise Exception(f"Not Found {path}")
        

def save_cracked( data, path_cracked):  
    os.makedirs("result", exist_ok=True)
    with open(os.path.join("result", path_cracked), "a+", encoding="utf-8") as file:
        file.writelines(data)

def is_ip_up( ip: str) -> bool:
    try:
        response = req.get(url=ip, timeout=30)
        return response.ok,ip
    except (req.RequestException, ValueError):
        return False,ip