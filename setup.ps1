$ErrorActionPreference = 'Stop'
if (-not (Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
$Py = '.venv\Scripts\python.exe'
& $Py -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cu128
& $Py -m pip install --no-build-isolation -e '.[docling,neural]'
& $Py -c "import torch; print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA GPU unavailable')"
Write-Host 'Setup complete. Ingest with: .\.venv\Scripts\python.exe -m finpaper ingest'
