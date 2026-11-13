Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\sahin\AI-Agent-Desktop-Apps"
WshShell.Run """C:\Users\sahin\AppData\Local\Programs\Python\Python311\pythonw.exe"" ""C:\Users\sahin\AI-Agent-Desktop-Apps\agent_studio.py""", 0, False
