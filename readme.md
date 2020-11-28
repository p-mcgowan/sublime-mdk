# Sublime SE MDK (title pending)

Steal the MDK compiler for Visual Studio, use in sublime build to get errors and whatnot.
May need to install msbuild deps (see https://github.com/malware-dev/MDK-SE/wiki/Getting-Started)

- Copy folder into sublime/packages/
- Unzip msbuild.zip (pre-packaged dll's - prolly won't work on everyone's machine)  
  **NOTE** make sure it extracts into the same folder (.../Packages/se-mdk/)  
  If you messed this up, just move se-mdk/msbuild/msbuild to se-mdk/msbuild  
- Open APPDATA/Roaming/SpaceEngineers/IngameScripts/local/script-folder
- (optionally) add mdk.sublime-settings to the folder
- Select Tools -> Build System -> se-mdk
- Profit

If you have SE installed somewhere other than c...steamapps..common whatever, then change it in the mdk.sublime-settings file

Thanks to [malware](https://github.com/malware-dev)  
Based off [mdk-se](https://github.com/malware-dev/MDK-SE)  
