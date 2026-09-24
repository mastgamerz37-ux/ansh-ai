Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\\ansh"
WshShell.Run "venv\Scripts\pythonw.exe main.py", 0, False