Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\sahin\AI-Agent-Desktop-Apps"
WshShell.Run """C:\Users\sahin\AppData\Local\Programs\Python\Python311\pythonw.exe"" ""C:\Users\sahin\AI-Agent-Desktop-Apps\ufo_app.py""", 0, False
