dotnet.exe exec "CSC_DIR\csc.dll"
/noconfig
/nowarn:1701,1702,2008
/fullpaths
/nostdlib+
/platform:x86
/errorreport:prompt
/errorendlocation
/preferreduilang:en-US
/highentropyva+
/lib:"MDK_ROOT\MDK\bin"
/lib:"SE_GAME_DIR\Bin64"
/lib:"DOTNET_48_DIR"
/lib:"DOTNET_48_DIR\Facades"
/reference:netstandard.dll,
Microsoft.CodeAnalysis.CSharp.dll,
Microsoft.CodeAnalysis.dll,
Microsoft.CSharp.dll,
System.Collections.Immutable.dll,
System.dll,
System.Memory.dll,
System.Numerics.Vectors.dll,
mscorlib.dll,
System.Core.dll,
System.Runtime.CompilerServices.Unsafe.dll
/filealign:512
/out:"MDK_ROOT\MDK\bin\mdkmin.exe"
/subsystemversion:6.00
/target:exe
/utf8output
/langversion:7.3
"MDK_ROOT\MDK\minifier.cs"
"MDK_ROOT\MDK\.NETFramework,Version=v4.8.AssemblyAttributes.cs"
