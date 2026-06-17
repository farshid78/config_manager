# Installer scripts

This repo includes per-platform installer scripts that automate:
- create `venv/`
- install `requirements.txt`
- create runtime folders: `data/logs`, `data/exports`, `data/clean_ips`
- create `.env` from `.env.example` if missing

## Linux
```bash
chmod +x installer_linux.sh
./installer_linux.sh
# Start
source venv/bin/activate
python main.py
```

## macOS
```bash
chmod +x installer_macos.sh
./installer_macos.sh
# Start
source venv/bin/activate
python main.py
```

## Windows (PowerShell)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.5installer_windows.ps1
# Start
& .\venv\Scripts\python.exe .\main.py
```

