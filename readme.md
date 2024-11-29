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

See [example settings file](./mdk.sublime-settings) for more in-depth usage.


## v2

install .net 8 SDK
https://dotnet.microsoft.com/en-us/download/dotnet/8.0
and the .net 4.8 dev pack (not 4.8.1)
https://www.microsoft.com/net/targeting

MDK folder contains files from https://github.com/malforge/mdk2/tree/main/Source/Mdk.CommandLine.Tests/TestData/LegacyScriptProject/MDK as well as other support files.


### WSL (doesnt work)


on WSL, install dotnet8
```bash
wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb
sudo apt-get update
sudo apt-get install -y dotnet-host
sudo apt-get install -y dotnet-sdk-8.0
```

clone the repo
```bash
git clone https://github.com/malforge/mdk2 
```

```bash
cd mdk2/Source/Mdk.CommandLine
dotnet publish "Mdk.CommandLine.csproj" -c Release --self-contained false -r linux-x64 /p:PublishSingleFile=true /p:IncludeNativeLibrariesForSelfExtract=true -o "binaries"
chmod +x binaries/mdk
./binaries/mdk help

alias mdk="$PWD/binaries/mdk "

mdk pack project.csproj -output ./here/ -gamebin="/mnt/c/Program Files (x86)/Steam/steamapps/common/SpaceEngineers/Bin64"
```


### Rider

install .net 8 SDK
https://dotnet.microsoft.com/en-us/download/dotnet/8.0
and the .net 4.8 dev pack (not 4.8.1)
https://www.microsoft.com/net/targeting

if you see this error:
```
0>Microsoft.PackageDependencyResolution.targets(266,5): Error NETSDK1004 : Assets file 'C:\Users\you\RiderProjects\Mdk.PbScript1\Mdk.PbScript1\obj\project.assets.json' not found. Run a NuGet package restore to generate this file.
0>------- Finished building project: Mdk.PbScript1. Succeeded: False. Errors: 1. Warnings: 0
```
update your mdk packages: https://github.com/malforge/mdk2/wiki/Updating-the-MDK2-Nuget-packages-using-Jetbrains-Rider

try `hamburger -> build -> clean project` then `hamburger -> build -> rebuild project`. If that doesn't work, restart rider.
