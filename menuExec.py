from src.Menu import Menu
from src.ProcessAuto import ProcessAutoImpl




def main():
	menu = Menu(ProcessAutoImpl())
	menu.tabMenu()

main()
