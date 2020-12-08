# Sublime SE MDK (title pending)

Steal the MDK compiler for Visual Studio, use in sublime build to get errors and whatnot.
~May need to install msbuild deps (see https://github.com/malware-dev/MDK-SE/wiki/Getting-Started)~

- Copy / clone into sublime packages folder
  (likely `C:\Users\username\AppData\Roaming\Sublime Text 3\Packages\se-mdk`)
- Unzip lib.zip (pre-packaged dll's - prolly won't work on everyone's machine)
  Make sure it extracts into the same folder (`\Packages\se-mdk`)
  If it's in `\Packages\se-mdk\lib\lib`, just move `se-mdk\lib`
  You should end up with `\Packages\se-mdk\lib\lots-of.dll`
- Open or create a new script (`C:\Users\username\AppData\Roaming\SpaceEngineers\IngameScripts\local\script-folder\`
- Add mdk.sublime-settings to the folder. Any setting in the local project file will override the [defaults](mdk.sublime-settings).
- Select Tools -> Build System -> se-mdk
- Profit

If you have SE installed somewhere other than c...steamapps..common whatever, then change it in the mdk.sublime-settings file

Thanks to [malware](https://github.com/malware-dev)
Inspired by [mdk-se](https://github.com/malware-dev/MDK-SE)
