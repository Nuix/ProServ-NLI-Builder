$volatility_dir = "volatility"
$symbol_dir = "$volatility_dir\symbols"

if (Test-Path $volatility_dir) {
  Remove-Item -Recurse -Force $volatility_dir
}

New-Item $symbol_dir -ItemType Directory
