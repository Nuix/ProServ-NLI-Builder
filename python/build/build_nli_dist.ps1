$build_path = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Write-Output $build_path
$env_dest = "$build_path\dist"
$env_src = "$build_path\build"
$env_code = "$build_path\main"
$env_rsrc = "$build_path\resources"

if(Test-Path "$env_dest") {
    Remove-Item $env_dest -Recurse -Force
}

New-Item -Path $env_dest -ItemType Directory
Copy-Item "$env_src\python"  -Destination "$env_dest\python" -Recurse
Copy-Item "$env_code\nuix_nli_lib" -Destination "$env_dest\python\vendor" -Recurse
Copy-Item "$env_rsrc\init_nuix_nli_env.py" -Destination "$env_dest\python\"
Copy-Item "$env_rsrc\nli_builder.bat" -Destination "$env_dest\"

$dist_settings = @{
  Path = "$env_dest\python", "$env_dest\nli_builder.bat"
  DestinationPath = "$env_dest\nli_builder.zip"
  CompressionLevel = "Optimal"
}

Compress-Archive @dist_settings

$lib_settings = @{
  Path = "$env_dest\python\vendor\nuix_nli_lib"
  DestinationPath = "$env_dest\nuix_nli_lib.zip"
  CompressionLevel = "Optimal"
}

Compress-Archive @lib_settings

Write-Output "Done"