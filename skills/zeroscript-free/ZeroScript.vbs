' SPDX-License-Identifier: GPL-3.0-or-later
' ZeroScript.vbs - Launch the ZeroScript desktop app with zero console window.
Option Explicit

Dim fso, sh, appDir, appPy, pyw, envLocal, envProg, envProg86

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

appDir = fso.GetParentFolderName(WScript.ScriptFullName)
appPy = fso.BuildPath(appDir, "app.py")

If Not fso.FileExists(appPy) Then
  MsgBox "app.py was not found next to ZeroScript.vbs." & vbCrLf & vbCrLf & _
         "If you opened this from inside a ZIP file, extract the whole folder first.", _
         vbCritical, "ZeroScript"
  WScript.Quit 1
End If

Function FindPythonWInRoot(rootPath)
  FindPythonWInRoot = ""
  If rootPath = "" Or Not fso.FolderExists(rootPath) Then Exit Function
  Dim rootFolder, subFolder, candidate
  Set rootFolder = fso.GetFolder(rootPath)
  For Each subFolder In rootFolder.SubFolders
    If Left(LCase(subFolder.Name), 7) = "python3" Then
      candidate = fso.BuildPath(subFolder.Path, "pythonw.exe")
      If fso.FileExists(candidate) Then
        FindPythonWInRoot = candidate
        Exit Function
      End If
    End If
  Next
End Function

Function CanRun(cmd)
  On Error Resume Next
  Dim rc
  rc = sh.Run(cmd, 0, True)
  CanRun = (Err.Number = 0 And rc = 0)
  Err.Clear
  On Error GoTo 0
End Function

pyw = ""
envLocal = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python"
envProg = sh.ExpandEnvironmentStrings("%ProgramFiles%")
envProg86 = sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%")

pyw = FindPythonWInRoot(envLocal)
If pyw = "" Then pyw = FindPythonWInRoot(envProg)
If pyw = "" Then pyw = FindPythonWInRoot(envProg86)

If pyw <> "" Then
  Dim pyExe
  pyExe = fso.BuildPath(fso.GetParentFolderName(pyw), "python.exe")
  If fso.FileExists(pyExe) Then
    If CanRun("""" & pyExe & """ -c ""import websockets""") Then
      sh.CurrentDirectory = appDir
      sh.Run """" & pyw & """ """ & appPy & """", 0, False
      WScript.Quit 0
    End If
  End If
End If

If CanRun("py -3 -c ""import websockets""") Then
  sh.CurrentDirectory = appDir
  sh.Run "pyw -3 """ & appPy & """", 0, False
  WScript.Quit 0
End If

If CanRun("python -c ""import websockets""") Then
  sh.CurrentDirectory = appDir
  sh.Run "pythonw """ & appPy & """", 0, False
  WScript.Quit 0
End If

' Fallback to start_app.bat if pythonw/websockets setup is needed
sh.CurrentDirectory = appDir
sh.Run """" & fso.BuildPath(appDir, "start_app.bat") & """", 1, False
