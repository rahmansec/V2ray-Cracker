import typer
from Cracker import Crack
app = typer.Typer()

@app.command()
def main(ip_list: str, userlist: str, passwordlist: str, output: str,thread=10):
    crack = Crack()
    crack.crack(ip_list,userlist,passwordlist,output,thread)

