from typing import Annotated
import typer
from Cracker import Crack
app = typer.Typer()

@app.command()
def main(ips: Annotated[str, typer.Option("--ips")],usernames: Annotated[str, typer.Option("--usernames")],passwords: Annotated[str, typer.Option("--passwords")] ,output: Annotated[str, typer.Option("--output")] = "Cracked.txt",thread: Annotated[int, typer.Option("--thread")]=10):
    typer.clear()
    crack = Crack()
    crack.crack(ips,usernames,passwords,output,int(thread))

app()