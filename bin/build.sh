#!/bin/bash

# /mnt/c/Users/mcgow/Desktop/games/se/mdk/bin/build.sh

shopt -s globstar
# set -x

win_temp=/mnt/c/Users/mcgow/AppData/Local/Temp
mdk_root=$(cd $(dirname $0)/.. && pwd)
mdk_root_win=$(wslpath -w $mdk_root)
compileFiles=()
build_dir=./build
output=Script.cs
main=main.cs
files=*
thumb=true
here=$PWD

while true; do
  if [ -f manifest.build ]; then
    sed -e 's/\r$//' manifest.build >/tmp/manifest.build
    source /tmp/manifest.build
    break
  fi
  this_dir=$PWD
  cd ..
  if [ "$PWD" == "$this_dir" ]; then
    echo "Could not find manifest"
    exit 1
  fi
done

# wsl workarounds - creating files with wsl and editing on windows, things go wrong...
# all file CRUD must go through powershell (slow)
psmkdir() {
  # echo powershell.exe -Command mkdir -Force $@ 1>/dev/null
  powershell.exe -Command mkdir -Force $@ 1>/dev/null
}

psrm() {
  # echo powershell.exe -Command Remove-Item $@ -Force -Recurse -Confirm:\$false
  powershell.exe -Command Remove-Item $@ -Force -Recurse -Confirm:\$false
}

pscopy() {
  # echo powershell.exe -Command cp "$1" "$2"
  powershell.exe -Command cp "$1" "$2"
}

psappend() {
  # echo powershell.exe -Command cat "$2" \>\> "$1"
  powershell.exe -Command cat "$2" \>\> "$1"
}

pstouch() {
  # echo powershell.exe -Command echo \$null \>\> "$1"
  powershell.exe -Command echo \$null \>\> "$1"
}

psmv() {
  # echo powershell.exe -Command mv -Force "$1" "$2"
  powershell.exe -Command mv -Force "$1" "$2"
}

toWinPath() {
  wslpath -w $(realpath "$1")
}

arrayJoin() {
  local d=$1
  shift
  local f=$1
  shift
  printf %s "$f" "${@/#/$d}"
}

copyToBuildPath() {
  local filename="$1"
  local target="$2"
  echo "wrapping $filename -> $target"
  tr -d '\r\n' < $mdk_root/lib/head.cs > $win_temp/script.cs
  cat "$filename" "$mdk_root/lib/tail.cs" >> $win_temp/script.cs
  # cat $win_temp/script.cs
  psmv "$(toWinPath $win_temp/script.cs)" "$target"
}

onSuccess() {
  outputs=("$main")
  for file in $files; do
    if [ "$file" == "$main" ]; then continue; fi
    outputs+=("$file")
  done
  cat $outputs > $win_temp/script.cs
  psmv "$(toWinPath $win_temp/script.cs)" "$output"

  if [ "$thumb" == "true" ]; then
    pscopy ${mdk_root_win}\\MDK\\thumb.png thumb.png
  elif [ -n "$thumb" ]; then
    pscopy "$thumb" thumb.png
  fi
}

# optimize so slow af ps calls
preBuild() {
  psrm $build_dir
  psmkdir $build_dir
  declare -A folders=()
  for file in $files; do
    no_relative_path=$(dirname $file | sed 's/^[\.\/]\+//g')
    folders["$build_dir/$no_relative_path"]=true
  done
  local cs_folders=$(arrayJoin ' , ' "${!folders[@]}")
  psmkdir $cs_folders
}

build() {
  preBuild

  copyToBuildPath "$main" "$build_dir/Program.cs"
  for file in $files; do
    echo "$main" "$file"
    if [ "$file" == "$main" ]; then continue; fi
    no_relative_path=$(echo $file | sed 's/^[\.\/]\+//g')
    copyToBuildPath "$file" "$build_dir/$no_relative_path"
    compileFiles+=("$(toWinPath $build_dir/$no_relative_path)")
  done
  compileFiles+=("$(toWinPath $build_dir/Program.cs)")
}

collectBuildFiles() {
  build_path=$(realpath $build_dir)
  out_path=$(realpath $output)
  echo "build_path: $build_path"
  echo "out_path: $out_path"
  for file in $files; do
    file_path=$(realpath $file)
    if [ "$file_path" == "$build_path" ] || \
      [ "$file_path" == "$out_path" ]; then
      continue
    fi

    if [ -d "$file" ]; then
      contents=$(find $file -name '*.cs')
      echo "file_path: $file_path"
      echo $contents
      targets+=($contents)
    elif [[ "$file" == *.cs ]]; then
      echo "file_path: $file_path"
      echo $file
      targets+=($file)
    else
      echo "skipping non .cs $file"
    fi
  done
  if [ ${#targets[@]} == 0 ]; then
    echo "no files found to build"
    exit 1
  fi

  files=${targets[@]}
}


arg="$@" # options, files / folders TODO
targets=()

collectBuildFiles
echo "found files: $files"

build

echo "compileFiles:"
echo "${compileFiles[@]}"

exit 1
tr -d '\r\n' < $mdk_root/lib/compile.bat > $build_dir/compile.bat
# cat $build_dir/compile.bat
# echo -e '\n\n'
echo "\
 /additionalfile:$mdk_root_win\MDK\MDK.options.props \
/additionalfile:$mdk_root_win\MDK\MDK.paths.props \
/additionalfile:$mdk_root_win\Instructions.readme \
/additionalfile:$mdk_root_win\thumb.png \
/additionalfile:$mdk_root_win\MDK\whitelist.cache \
$mdk_root_win\MDK\Bootstrapper.cs \
${compileFiles[@]} \
\"$mdk_root_win\MDK\.NETFramework,Version=v4.6.1.AssemblyAttributes.cs\"
" >> $build_dir/compile.bat

echo "compiling"
cmd.exe /c $(toWinPath $build_dir/compile.bat)
res=$?

if [ $res == 0 ]; then
  psrm "$(toWinPath ./Bootstrapper.exe),$(toWinPath ./Bootstrapper.pdb)"
  onSuccess
  echo "all done"
  exit 0
else
  echo "something went wrong"
  exit 1
fi
