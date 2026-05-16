import os
import sys
import ssl
import time
import ctypes
import string
import shutil
import urllib.request
import re
import csv
import threading
import subprocess
import random
import webbrowser
import datetime
import base64
from tkinter import messagebox, filedialog
import customtkinter as ctk

# ============================================================
# 1. CAU HINH HE THONG
# ============================================================
DUONG_DAN_KHO = "https://raw.githubusercontent.com/tuantran19912512/quickinstallwindows/refs/heads/main/list_win.csv"
CLOUD_WINRE   = "https://huggingface.co/datasets/tuantran1991/windows/resolve/main/Winre.wim"
ARIA2C_URL    = "https://raw.githubusercontent.com/tuantran19912512/quickinstallwindows/refs/heads/main/aria2c.exe"

KHOA_API_B64 = [
    "QUl6YVN5Q3VKUkJaTDZnUU8tdVZOMWVvdHhmMlppTXNtYy1sandR",
    "QUl6YVN5QlRhVmRQdmlLaUJyR0JUVk0tUlRiVW51QUdFUzRWck1v",
    "QUl6YVN5QkI0NENOamtHRkdQSjhBaVZaMURxZFJnc3M5MDc4QThv",
    "QUl6YVN5Q2IzaE1LUVNOamt2bFNKbUlhTGtYcVNybFpWaFNSTThR",
    "QUl6YVN5Q2V0SVlWVzRsQmlULTd3TzdNQUJoWlNVQ0dKR1puQTM0",
]

# ============================================================
# 2. QUYEN QUAN TRI
# ============================================================
def _la_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not _la_admin():
    exe = sys.executable
    args = f'"{os.path.abspath(__file__)}"' if not getattr(sys, "frozen", False) else " ".join(sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, args, None, 1)
    sys.exit()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ============================================================
# 3. TIEN ICH CHUNG
# ============================================================
def _chay(lenh, shell=True):
    return subprocess.run(
        lenh, shell=shell,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

def do_bang_thong(log):
    log("Dang do luong bang thong mang...")
    try:
        req = urllib.request.Request(
            "https://speed.cloudflare.com/__down?bytes=1048576",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read()
        spd = (len(data) / 1024 / 1024) / max(time.time() - t0, 0.001)
        log(f"Toc do mang: ~ {spd:.1f} MB/s")
        return spd
    except:
        return 5.0

def go_bo_bitlocker(log):
    log("Dang quet BitLocker...")
    try:
        drv = os.environ.get("SystemDrive", "C:")
        out = _chay(f"manage-bde -status {drv}").stdout.decode("utf-8", errors="ignore")
        if any(k in out for k in ["Fully Encrypted", "Protection On", "Encryption", "Ma hoa"]):
            log(f"Phat hien BitLocker! Dang Tam dung (Suspend) bao ve {drv}...")
            # Sử dụng -protectors -disable để mở khóa tức thì cho lần boot tới
            _chay(f"manage-bde -protectors -disable {drv}")
    except:
        pass

def tim_o_dia_luu():
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    sys_drv = os.environ.get("SystemDrive", "C:")[0]
    best, best_sz = None, 0
    for i, c in enumerate(string.ascii_uppercase):
        if not (mask & (1 << i)):
            continue
        if c == sys_drv:
            continue
        root = f"{c}:\\"
        if ctypes.windll.kernel32.GetDriveTypeW(root) != 3:
            continue
        try:
            _, _, free = shutil.disk_usage(root)
            if free > 10 * 1024**3 and free > best_sz:
                best, best_sz = c, free
        except:
            pass
    if not best:
        raise Exception("Khong tim thay phan vung du trong tren 10GB!")
    return best

def lay_disk_partition():
    ky_tu = os.environ.get("SystemDrive", "C:")[0]
    r = subprocess.run(
        ["powershell", "-Command",
         f"$p=Get-Partition -DriveLetter '{ky_tu}'; Write-Output \"$($p.DiskNumber) $($p.PartitionNumber)\""],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    parts = r.stdout.decode("utf-8", errors="ignore").strip().split()
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return 0, 1

# ============================================================
# 4. SAO LUU WIFI / DRIVER
# ============================================================
def sao_luu_he_thong(thu_muc, chon_driver, chon_wifi, log):
    cmd_setup = "@echo off\n"

    if chon_wifi:
        log("Dang trich xuat WiFi...")
        wdir = os.path.join(thu_muc, "WiFi")
        os.makedirs(wdir, exist_ok=True)
        try:
            out = _chay("netsh wlan show interfaces").stdout.decode("utf-8", errors="ignore")
            m = re.search(r"SSID\s*:\s*(.*)", out)
            if m:
                with open(os.path.join(wdir, "current_ssid.txt"), "w", encoding="utf-8") as f:
                    f.write(m.group(1).strip())
            _chay(f'netsh wlan export profile key=clear folder="{wdir}"')
        except:
            pass
        cmd_setup += (
            "sc config wlansvc start= auto\nnet start wlansvc\ntimeout /t 3 /nobreak >nul\n"
            'for %%f in ("%~dp0WiFi\\*.xml") do netsh wlan add profile filename="%%f" user=all\n'
            'if exist "%~dp0WiFi\\current_ssid.txt" ('
            'set /p WLAN_SSID=<"%~dp0WiFi\\current_ssid.txt"\n'
            'netsh wlan connect name="%WLAN_SSID%")\n'
            'rd /s /q "%~dp0WiFi" >nul 2>&1\n\n'
        )

    cmd_setup += (
        'del /q /f /s "%WINDIR%\\Temp\\*.*" >nul 2>&1\n'
        'del /q /f /s "%WINDIR%\\Prefetch\\*.*" >nul 2>&1\n'
        "net stop wuauserv >nul 2>&1\n"
        'del /q /f /s "%WINDIR%\\SoftwareDistribution\\Download\\*.*" >nul 2>&1\n'
        "net start wuauserv >nul 2>&1\n"
        'del /q /f /s "%TEMP%\\*.*" >nul 2>&1\n'
        'rd /s /q "%SystemDrive%\\$Recycle.Bin" >nul 2>&1\n'
        "for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do "
        '(if exist "%%D:\\ZT_Cloud_Install" rd /s /q "%%D:\\ZT_Cloud_Install" >nul 2>&1)\n'
        'del /f /q "%~f0" >nul 2>&1\n'
    )
    with open(os.path.join(thu_muc, "SetupComplete.cmd"), "w", encoding="utf-8") as f:
        f.write(cmd_setup)

    if chon_driver != "Khong Backup Driver":
        log(f"Dang backup driver ({chon_driver})...")
        ddir = os.path.join(thu_muc, "Drivers")
        os.makedirs(ddir, exist_ok=True)
        if chon_driver == "Backup Toan Bo Driver":
            subprocess.run(
                ["powershell", "-Command", f'Export-WindowsDriver -Online -Destination "{ddir}"'],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            tmp = os.path.join(thu_muc, "DrvTmp")
            ps = (
                f"$d=Export-WindowsDriver -Online -Destination '{tmp}';"
                f" foreach($x in $d){{ if($x.ClassName -match 'Net|WLAN|Bluetooth'){{"
                f" Copy-Item (Split-Path $x.OriginalFileName) -Destination '{ddir}' -Recurse -Force }}}};"
                f" Remove-Item '{tmp}' -Recurse -Force"
            )
            subprocess.run(["powershell", "-Command", ps], creationflags=subprocess.CREATE_NO_WINDOW)

# ============================================================
# 5. TAO UNATTEND.XML
# ============================================================
def tao_unattend(thu_muc, ten_may):
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
  <settings pass="oobeSystem">
    <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64"
               publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <OOBE>
        <HideEULAPage>true</HideEULAPage>
        <SkipMachineOOBE>true</SkipMachineOOBE>
        <SkipUserOOBE>true</SkipUserOOBE>
      </OOBE>
      <UserAccounts>
        <LocalAccounts>
          <LocalAccount wcm:action="add"
              xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
            <Name>Admin</Name>
            <Group>Administrators</Group>
          </LocalAccount>
        </LocalAccounts>
      </UserAccounts>
      <AutoLogon>
        <Enabled>true</Enabled>
        <Username>Admin</Username>
      </AutoLogon>
    </component>
  </settings>
</unattend>"""
    with open(os.path.join(thu_muc, "unattend.xml"), "w", encoding="utf-8") as f:
        f.write(xml)

# ============================================================
# 6. BUOC 1: TIM / TAI WINRE.WIM
# ============================================================
def tim_hoac_tai_winre(thu_muc, log, huy):
    log("=== [BUOC 1] XU LY WINRE.WIM ===")
    log("Dang tim winre.wim noi bo...")

    found = ""
    for path in [
        "C:\\Windows\\System32\\Recovery\\winre.wim",
        "C:\\Recovery\\WindowsRE\\winre.wim",
    ]:
        _chay(f'attrib -h -s -r "{path}"')
        if os.path.exists(path) and os.path.getsize(path) > 1024 * 1024:
            found = path
            log(f"Tim thay WinRE noi bo: {found}")
            break

    if not found:
        log("Khong thay o vi tri chuan. Quet WinSxS...")
        r = _chay("where /r C:\\Windows\\WinSxS winre.wim")
        lines = r.stdout.decode("utf-8", errors="ignore").strip().splitlines()
        if lines and os.path.exists(lines[0].strip()):
            found = lines[0].strip()
            log(f"Tim thay trong WinSxS: {found}")

    if not found:
        log("Khong tim thay WinRE noi bo. Dang tai tu HuggingFace Cloud...")
        save_dir = "C:\\Recovery\\WindowsRE"
        os.makedirs(save_dir, exist_ok=True)
        dest = os.path.join(save_dir, "winre.wim")
        try:
            ctx = ssl._create_unverified_context()
            req = urllib.request.Request(CLOUD_WINRE, headers={"User-Agent": "Mozilla/5.0"})
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
            with opener.open(req, timeout=600) as resp:
                total = int(resp.getheader("Content-Length", 0))
                done = 0
                t0 = time.time()
                with open(dest, "wb") as f:
                    while True:
                        if huy.is_set():
                            raise Exception("Nguoi dung huy tai WinRE.")
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if total > 0:
                            spd = done / max(time.time() - t0, 0.001) / 1024 / 1024
                            log(f"  WinRE: {done/total*100:.1f}% | {spd:.1f} MB/s")
            if os.path.exists(dest) and os.path.getsize(dest) > 1024 * 1024:
                found = dest
                log("Tai WinRE tu Cloud thanh cong!")
            else:
                raise Exception("File WinRE tai ve bi loi hoac rong!")
        except Exception as e:
            raise Exception(f"Khong the tai WinRE tu Cloud: {e}")

    return found

# ============================================================
# 7. BUOC 2: TIEM KICH BAN VAO WINRE (DA TOI UU BCDEDIT MỚI)
# ============================================================
def tiem_winre(winre_path, thu_muc, ten_may, disk_no, part_no, log):
    log("=== [BUOC 2] TIEM KICH BAN VAO WINRE ===")
    
    # Tách ổ đĩa và đường dẫn tương đối (Ví dụ: D: và \ZT_Cloud_Install)
    drive_letter = thu_muc[:2]
    thu_muc_rel = thu_muc[2:]

    ps = f"""
$ErrorActionPreference = 'Continue'
$FoundWIM      = "{winre_path}"
$MountDir      = "C:\\MountRE"
$WinRECopy     = "C:\\winre_work.wim"
$SafePath      = "{thu_muc}"

if (Test-Path $MountDir) {{
    dism.exe /Unmount-Image /MountDir:$MountDir /Discard | Out-Null
    Remove-Item $MountDir -Recurse -Force -ErrorAction SilentlyContinue
}}
New-Item -ItemType Directory -Force -Path $MountDir | Out-Null

Write-Output "[RE] Tat Fast Startup & xoa RE cu..."
powercfg /h off | Out-Null
reagentc.exe /disable | Out-Null
Start-Sleep -Seconds 1

Copy-Item $FoundWIM $WinRECopy -Force
cmd.exe /c "attrib -h -s -r `"$WinRECopy`" >nul 2>&1"

Write-Output "[RE] Mount WinRE..."
$r = dism.exe /Mount-Image /ImageFile:$WinRECopy /Index:1 /MountDir:$MountDir
if ($LASTEXITCODE -ne 0) {{ Write-Output "[RE] LOI MOUNT: $r"; exit 1 }}

$LenhRE = @"
@echo off
for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist "%%D:\\ZT_Cloud_Install\\install.wim" set "WPATH=%%D:\\ZT_Cloud_Install"
)
(echo select disk {disk_no} & echo select partition {part_no} & echo assign letter=W & echo format quick fs=ntfs label="Windows") | diskpart
dism /apply-image /imagefile:"%WPATH%\\install.wim" /index:1 /applydir:W:\\
if exist "%WPATH%\\Drivers" ( dism /image:W:\\ /Add-Driver /Driver:"%WPATH%\\Drivers" /Recurse )
bcdboot W:\\Windows
reg load HKLM\\ZT W:\\Windows\\System32\\config\\SYSTEM
reg add "HKLM\\ZT\\Setup\\LabConfig" /v BypassTPMCheck /t REG_DWORD /d 1 /f
reg add "HKLM\\ZT\\Setup\\LabConfig" /v BypassSecureBootCheck /t REG_DWORD /d 1 /f
reg unload HKLM\\ZT
reg load HKLM\\ZTSW W:\\Windows\\System32\\config\\SOFTWARE
reg add "HKLM\\ZTSW\\Microsoft\\Windows\\CurrentVersion\\OOBE" /v BypassNRO /t REG_DWORD /d 1 /f
reg unload HKLM\\ZTSW
reg load HKLM\\ZTSYS W:\\Windows\\System32\\config\\SYSTEM
reg add "HKLM\\ZTSYS\\ControlSet001\\Control\\ComputerName\\ComputerName" /v ComputerName /t REG_SZ /d {ten_may} /f
reg add "HKLM\\ZTSYS\\ControlSet001\\Control\\ComputerName\\ActiveComputerName" /v ComputerName /t REG_SZ /d {ten_may} /f
reg add "HKLM\\ZTSYS\\ControlSet001\\Services\\Tcpip\\Parameters" /v Hostname /t REG_SZ /d {ten_may} /f
reg add "HKLM\\ZTSYS\\ControlSet001\\Services\\Tcpip\\Parameters" /v "NV Hostname" /t REG_SZ /d {ten_may} /f
reg unload HKLM\\ZTSYS
mkdir W:\\Windows\\Panther
copy /Y "%WPATH%\\unattend.xml" W:\\Windows\\Panther\\unattend.xml
if exist "%WPATH%\\SetupComplete.cmd" ( mkdir W:\\Windows\\Setup\\Scripts & copy /Y "%WPATH%\\SetupComplete.cmd" W:\\Windows\\Setup\\Scripts\\ )
if exist "%WPATH%\\WiFi" ( mkdir W:\\Windows\\Setup\\Scripts\\WiFi & xcopy /E /Y /I "%WPATH%\\WiFi" W:\\Windows\\Setup\\Scripts\\WiFi\\ )
wpeutil reboot
"@

Write-Output "[RE] Tiem LenhRE.cmd va winpeshl.ini..."
$LenhRE | Out-File "$MountDir\\Windows\\System32\\LenhRE.cmd" -Encoding oem
'[LaunchApps]' + [char]13 + [char]10 + 'X:\\Windows\\System32\\LenhRE.cmd' | Out-File "$MountDir\\Windows\\System32\\winpeshl.ini" -Encoding ascii

Write-Output "[RE] Trich xuat boot.sdi de ho tro RAMDISK..."
$SdiPath = "$MountDir\\Windows\\Boot\\DVD\\PCAT\\boot.sdi"
if (Test-Path $SdiPath) {{
    Copy-Item $SdiPath "$SafePath\\boot.sdi" -Force
}} else {{
    Copy-Item "$MountDir\\Windows\\Boot\\PXE\\boot.sdi" "$SafePath\\boot.sdi" -Force -ErrorAction SilentlyContinue
}}

Write-Output "[RE] Commit WinRE..."
$r2 = dism.exe /Unmount-Image /MountDir:$MountDir /Commit
if ($LASTEXITCODE -ne 0) {{
    Write-Output "[RE] LOI COMMIT: $r2"
    dism.exe /Unmount-Image /MountDir:$MountDir /Discard | Out-Null
    exit 1
}}

Write-Output "[RE] Sao chep winre.wim vao vung an toan ($SafePath)..."
Copy-Item $WinRECopy "$SafePath\\winre.wim" -Force
cmd.exe /c "attrib +h +s +r `"$SafePath\\winre.wim`" >nul 2>&1"
Remove-Item $WinRECopy -Force -ErrorAction SilentlyContinue

Write-Output "[RE] Cau hinh BCD cuong che boot vao WinRE..."
$ramdisk = bcdedit /create /d "ZT Ramdisk" /device
$ramdiskGuid = if ($ramdisk -match '(\\{{[a-fA-F0-9-]+\\}})') {{ $matches[1] }} else {{ "" }}
if (-not $ramdiskGuid) {{ Write-Output "[RE] Loi: Khong lay duoc GUID Ramdisk"; exit 1 }}

bcdedit /set $ramdiskGuid ramdisksdioptions locating | Out-Null
bcdedit /set $ramdiskGuid ramdisksdipath "{thu_muc_rel}\\boot.sdi" | Out-Null

$os = bcdedit /create /d "ZT Deploy Environment" /application osloader
$osGuid = if ($os -match '(\\{{[a-fA-F0-9-]+\\}})') {{ $matches[1] }} else {{ "" }}
if (-not $osGuid) {{ Write-Output "[RE] Loi: Khong lay duoc GUID OSLoader"; exit 1 }}

# Kiem tra xem may dang boot chuan nao (UEFI efi hay BIOS exe)
$currentPath = (bcdedit /enum '{{current}}' | Select-String "path").Line
if ($currentPath -match "\\.efi") {{
    $winload = "\\Windows\\System32\\winload.efi"
}} else {{
    $winload = "\\Windows\\System32\\winload.exe"
}}

bcdedit /set $osGuid device "ramdisk=[{drive_letter}]{thu_muc_rel}\\winre.wim,$ramdiskGuid" | Out-Null
bcdedit /set $osGuid osdevice "ramdisk=[{drive_letter}]{thu_muc_rel}\\winre.wim,$ramdiskGuid" | Out-Null
bcdedit /set $osGuid path $winload | Out-Null
bcdedit /set $osGuid systemroot "\\Windows" | Out-Null
bcdedit /set $osGuid winpe "Yes" | Out-Null
bcdedit /set $osGuid detecthal "Yes" | Out-Null

Write-Output "[RE] Dat lenh Boot 1 lan vao WinRE..."
bcdedit /bootsequence $osGuid | Out-Null

Write-Output "[RE] HOAN TAT CAU HINH BCD NATIVE BOOT!"
"""

    ps1_path = os.path.join(thu_muc, "prep_winre.ps1")
    try:
        with open(ps1_path, "w", encoding="utf-8") as f:
            f.write(ps)
        log("--- Bat dau xu ly WinRE (BCD Method) ---")
        proc = subprocess.Popen(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps1_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
            text=True, encoding="utf-8", errors="ignore"
        )
        for line in proc.stdout:
            s = line.strip()
            if s:
                log(s)
        proc.wait()
        log("--- Ket thuc xu ly WinRE ---")
        if proc.returncode != 0:
            raise Exception("Tiem kich ban WinRE that bai! Xem log phia tren.")
    finally:
        if os.path.exists(ps1_path):
            try:
                os.remove(ps1_path)
            except:
                pass


# ============================================================
# 8. BUOC 4: BOOT VAO WINRE (DA SUA)
# ============================================================
def boot_vao_winre(log):
    log("=== [BUOC 4] HOAN THIEN KHOI DONG ===")
    log("Thiet lap BCD Bootsequence truc tiep OK.")
    log("May se khoi dong vao RAMDISK WinRE de bung Windows...")
    
# ============================================================
# 9. DONG CO TAI FILE (Google Drive -> HuggingFace -> Web)
# ============================================================
def tai_file(ma_gdrive, link_hf, duong_dan_luu, cap_nhat_ui, log, huy):
    """
    Chien luoc: voi moi server [Google Drive, HuggingFace]:
        1. Thu Aria2c 16 luong
        2. Thu Python urllib (du phong)
    Neu tat ca that bai -> mo web Google Drive.
    """
    thu_muc = os.path.dirname(duong_dan_luu)
    ten_file = os.path.basename(duong_dan_luu)
    aria     = os.path.join(thu_muc, "aria2c.exe")

    # --- Tai aria2c neu chua co ---
    if not os.path.exists(aria):
        log("Dang tai Aria2c engine...")
        try:
            urllib.request.urlretrieve(ARIA2C_URL, aria)
            if os.path.getsize(aria) < 500000:
                os.remove(aria)
                raise Exception("aria2c khong hop le")
        except Exception as e:
            log(f"Aria2c khoi tao that bai: {e}")
            aria = ""

    # --- Xay danh sach server theo thu tu uu tien ---
    servers = []

    if ma_gdrive and not ma_gdrive.startswith("http"):
        for b64 in KHOA_API_B64:
            try:
                key = base64.b64decode(b64).decode("utf-8")
                url = (
                    f"https://www.googleapis.com/drive/v3/files/{ma_gdrive}"
                    f"?alt=media&key={key}&acknowledgeAbuse=true"
                )
                servers.append(("Google Drive", url))
                break
            except:
                continue

    if link_hf and link_hf.startswith("http"):
        servers.append(("HuggingFace", link_hf))

    if not servers:
        log("Khong co URL hop le de tai!")
        return False

    # --- Helper: tai bang Aria2c ---
    def _aria(url, ten):
        if not aria or not os.path.exists(aria):
            return False
        log(f"[Aria2c] Ket noi {ten} - 16 luong...")
        cmd = [aria, "-x16", "-s16", "-k5M", "-c", "--file-allocation=none",
               "-d", thu_muc, "-o", ten_file, url]
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
            universal_newlines=True, encoding="utf-8", errors="ignore"
        )
        for line in p.stdout:
            if huy.is_set():
                p.kill()
                return False
            m = re.search(r"\((\d+)%\)", line)
            if m:
                cap_nhat_ui(int(m.group(1)), 0, 100, 0)
        p.wait()
        if os.path.exists(duong_dan_luu) and os.path.getsize(duong_dan_luu) > 1024 * 1024:
            sz = os.path.getsize(duong_dan_luu)
            cap_nhat_ui(100, sz, sz, 0)
            return True
        try:
            if os.path.exists(duong_dan_luu):
                os.remove(duong_dan_luu)
        except:
            pass
        return False

    # --- Helper: tai bang Python urllib ---
    # --- Helper: tai bang Python urllib ---
    def _python(url, ten):
        log(f"[Python] Ket noi {ten}...")
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "*/*"}
            ctx = ssl._create_unverified_context()
            req = urllib.request.Request(url, headers=headers)
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
            with opener.open(req, timeout=60) as resp:
                total = int(resp.getheader("Content-Length", 0))
                done = 0
                t0 = time.time()
                with open(duong_dan_luu, "wb") as f:
                    while True:
                        if huy.is_set():
                            return False
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if total > 0:
                            spd = done / max(time.time() - t0, 0.001)
                            cap_nhat_ui(done / total * 100, done, total, spd)
            if os.path.exists(duong_dan_luu) and os.path.getsize(duong_dan_luu) > 1024 * 1024:
                return True
        except Exception as e:
            log(f"[Python] Loi tu {ten}: {e}")
        try:
            if os.path.exists(duong_dan_luu):
                os.remove(duong_dan_luu)
        except:
            pass
        return False

    # --- Chay tung server ---
    for ten_sv, url_sv in servers:
        if huy.is_set():
            return False
        log(f">>> Ket noi server: {ten_sv}")

        if _aria(url_sv, ten_sv):
            return "SUCCESS"
        if huy.is_set():
            return False

        if _python(url_sv, ten_sv):
            return "SUCCESS"
        if huy.is_set():
            return False

        log(f"  Server {ten_sv} that bai. Chuyen server tiep theo...")

    # --- Tat ca that bai -> mo Web ---
    if ma_gdrive and not ma_gdrive.startswith("http"):
        log("Tat ca server tu dong deu bi chan. Mo link Google Drive tren Web...")
        try:
            webbrowser.open(f"https://drive.google.com/file/d/{ma_gdrive}/view")
            return "WEB_REDIRECT"
        except:
            pass

    return False

# ============================================================
# 10. GIAO DIEN CHINH
# ============================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Tram Trien Khai Ky Thuat - Tu Dong Dinh Danh & Don Rac")
        self.geometry("850x720")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._huy   = threading.Event()
        self._busy  = False
        self._nuts  = []

        # Header
        frm_top = ctk.CTkFrame(self, fg_color="transparent")
        frm_top.grid(row=0, column=0, pady=15, sticky="ew")
        ctk.CTkLabel(frm_top, text="HE THONG TRIEN KHAI MAY KHACH TU XA",
                     font=("Arial", 22, "bold")).pack()
        self.lbl_kho = ctk.CTkLabel(frm_top, text="Dang dong bo kho du lieu...", text_color="gray")
        self.lbl_kho.pack()

        # Settings
        frm_cfg = ctk.CTkFrame(self)
        frm_cfg.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        frm_cfg.grid_columnconfigure((0, 1, 2), weight=1)

        self.var_drv = ctk.StringVar(value="Backup LAN & WIFI")
        ctk.CTkOptionMenu(
            frm_cfg,
            values=["Khong Backup Driver", "Backup LAN & WIFI", "Backup Toan Bo Driver"],
            variable=self.var_drv
        ).grid(row=0, column=0, padx=10, pady=15)

        self.var_wifi = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(frm_cfg, text="Trich xuat WiFi", variable=self.var_wifi).grid(
            row=0, column=1, padx=10, pady=15)

        self.var_test = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(frm_cfg, text="CHE DO KIEM THU", variable=self.var_test,
                      progress_color="#D97706").grid(row=0, column=2, padx=10, pady=15)

        # List OS
        self.frm_list = ctk.CTkScrollableFrame(self, label_text=" DANH MUC BAN CAI DAT CO SAN ")
        self.frm_list.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        btn_local = ctk.CTkButton(
            self.frm_list, text="CHON FILE WIM TU O CUNG / USB",
            font=("Arial", 14, "bold"), fg_color="#047857", hover_color="#065F46",
            command=self._chon_local
        )
        btn_local.pack(fill="x", pady=(5, 15), padx=5)
        self._nuts.append(btn_local)

        # Log
        self.log_box = ctk.CTkTextbox(self, height=180, font=("Consolas", 12),
                                       fg_color="#0F172A", text_color="#38BDF8")
        self.log_box.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        self.log_box.insert("0.0", "He thong loi v32.1 da khoi tao.\n")
        self.log_box.configure(state="disabled")

        # Progress
        frm_bot = ctk.CTkFrame(self, fg_color="transparent")
        frm_bot.grid(row=4, column=0, padx=20, pady=15, sticky="ew")
        frm_bot.grid_columnconfigure(0, weight=1)

        self.bar = ctk.CTkProgressBar(frm_bot, height=12)
        self.bar.grid(row=0, column=0, padx=(0, 20), sticky="ew")
        self.bar.set(0)

        self.lbl_speed = ctk.CTkLabel(frm_bot, text="0% | Toc do: 0 MB/s",
                                       font=("Arial", 12, "bold"))
        self.lbl_speed.grid(row=1, column=0, sticky="w")

        self.btn_huy = ctk.CTkButton(frm_bot, text="HUY TIEN TRINH",
                                      fg_color="#BE123C", hover_color="#9F1239",
                                      state="disabled", command=self._huy_bo)
        self.btn_huy.grid(row=0, column=1, rowspan=2)

        self._quet_kho()

    # ---- Log ----
    def _log(self, msg):
        self.after(0, self.__log, msg)

    def __log(self, msg):
        t = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{t}] {msg}\n")
        n = int(self.log_box.index("end-1c").split(".")[0])
        if n > 200:
            self.log_box.delete("1.0", f"{n-200}.0")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ---- Progress ----
    def _ui(self, pct, done, total, spd):
        self.after(0, self.__ui, pct, done, total, spd)

    def __ui(self, pct, done, total, spd):
        self.bar.set(pct / 100)
        if total == 0:
            self.lbl_speed.configure(text=f"{int(pct)}% | Aria2c 16 luong...")
        else:
            self.lbl_speed.configure(
                text=f"{int(pct)}% | {spd/1024/1024:.1f} MB/s | {done/1024**3:.2f} GB"
            )

    # ---- Quet kho CSV ----
    def _quet_kho(self):
        def _run():
            try:
                req = urllib.request.Request(DUONG_DAN_KHO,
                                              headers={"User-Agent": "Mozilla/5.0"})
                raw = urllib.request.urlopen(req).read().decode("utf-8-sig").splitlines()
                reader = csv.DictReader(raw)
                cols = [c.strip() for c in reader.fieldnames if c]

                k_ten = next((c for c in cols if "name" in c.lower() or "ten" in c.lower()), None)
                k_id  = next((c for c in cols if "id" in c.lower()
                               and "link" not in c.lower().replace(" ", "")), None)
                k_raw = next((c for c in cols if "linkraw" in c.lower().replace(" ", "")), None)

                if not k_ten:
                    return
                count = 0
                for row in reader:
                    ten  = str(row.get(k_ten, "")).strip()
                    link = str(row.get(k_id, "")).strip() if k_id else ""
                    raw2 = str(row.get(k_raw, "")).strip() if k_raw else ""
                    gid  = ""
                    m    = re.search(r"[-\w]{25,}", link)
                    if m:
                        gid = m.group(0)
                    if ten and ".wim" in ten.lower() and (gid or raw2):
                        self._them_nut(ten, gid, raw2)
                        count += 1
                self.after(0, lambda: self.lbl_kho.configure(
                    text=f"Da giai ma {count} ban cai", text_color="#10B981"))
            except:
                self.after(0, lambda: self.lbl_kho.configure(
                    text="Loi phan tich kho du lieu", text_color="#EF4444"))

        threading.Thread(target=_run, daemon=True).start()

    def _them_nut(self, ten, gid, raw):
        btn = ctk.CTkButton(
            self.frm_list,
            text=f"TAI VA AP DUNG: {ten}",
            font=("Arial", 13, "bold"), fg_color="#1E293B", anchor="w",
            command=lambda n=ten, g=gid, r=raw: self._bat_dau(n, g, r)
        )
        btn.pack(fill="x", pady=2, padx=5)
        self._nuts.append(btn)

    def _khoa(self):
        for b in self._nuts:
            b.configure(state="disabled")

    def _mo_khoa(self):
        for b in self._nuts:
            b.configure(state="normal")

    def _huy_bo(self):
        self._huy.set()
        self.btn_huy.configure(state="disabled")

    def _reset(self, msg="Hoan thanh."):
        self._busy = False
        self.after(0, lambda: self.btn_huy.configure(state="disabled"))
        self.after(0, self._mo_khoa)
        self._log(msg)

    # ---- Chon WIM local ----
    def _chon_local(self):
        if self._busy:
            messagebox.showwarning("Canh Bao", "He thong dang ban!")
            return
        path = filedialog.askopenfilename(filetypes=[("Windows Image", "*.wim")])
        if not path:
            return
        if not self.var_test.get() and not messagebox.askyesno(
            "Canh Bao", "Hanh dong nay se XOA SACH o C. Tiep tuc?"
        ):
            return
        self._busy = True
        self._huy.clear()
        self.btn_huy.configure(state="normal")
        self._khoa()
        threading.Thread(target=self._main, args=("Local WIM", "", "", path), daemon=True).start()

    # ---- Chon WIM cloud ----
    def _bat_dau(self, ten, gid, raw):
        if self._busy:
            messagebox.showwarning("Canh Bao", "He thong dang ban!")
            return
        if not self.var_test.get() and not messagebox.askyesno(
            "Canh Bao", "Hanh dong nay se XOA SACH o C. Tiep tuc?"
        ):
            return
        self._busy = True
        self._huy.clear()
        self.btn_huy.configure(state="normal")
        self._khoa()
        threading.Thread(target=self._main, args=(ten, gid, raw, None), daemon=True).start()

    # ============================================================
    # LUONG CHINH: WINRE -> TIEM -> TAI WIM -> BOOT
    # ============================================================
    def _main(self, ten, gid, raw, local=None):
        thu_muc = ""
        try:
            # Chuan bi thu muc lam viec
            go_bo_bitlocker(self._log)
            o = tim_o_dia_luu()
            thu_muc = f"{o}:\\ZT_Cloud_Install"
            os.makedirs(thu_muc, exist_ok=True)

            sao_luu_he_thong(thu_muc, self.var_drv.get(), self.var_wifi.get(), self._log)

            disk_no, part_no = lay_disk_partition()
            ten_may = "PC-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
            self._log(f"Ten may cap phat: {ten_may}")

            tao_unattend(thu_muc, ten_may)

            # ---- BUOC 1: Tim / Tai WinRE ----
            winre_path = tim_hoac_tai_winre(thu_muc, self._log, self._huy)
            if self._huy.is_set():
                return self._reset("Huy o buoc WinRE.")

            # ---- BUOC 2: Tiem kich ban ----
            tiem_winre(winre_path, thu_muc, ten_may, disk_no, part_no, self._log)
            if self._huy.is_set():
                return self._reset("Huy sau buoc tiem WinRE.")

            self._log("WinRE da san sang. Bat dau tai install.wim...")

            # ---- BUOC 3: Tai / Copy install.wim ----
            wim_path = os.path.join(thu_muc, "install.wim")

            if local:
                if os.path.abspath(local).lower() == os.path.abspath(wim_path).lower():
                    self._log("File WIM da nam san trong khoang. Bo qua copy...")
                else:
                    self._log("=== [BUOC 3] COPY install.wim NOI BO ===")
                    total = os.path.getsize(local)
                    done  = 0
                    t0    = time.time()
                    with open(local, "rb") as src, open(wim_path, "wb") as dst:
                        while True:
                            chunk = src.read(4 * 1024 * 1024)
                            if not chunk:
                                break
                            if self._huy.is_set():
                                raise Exception("Nguoi dung huy copy WIM.")
                            dst.write(chunk)
                            done += len(chunk)
                            spd = done / max(time.time() - t0, 0.001)
                            self._ui(done / total * 100, done, total, spd)
                    self._log("Copy hoan tat.")
            else:
                self._log("=== [BUOC 3] TAI install.wim TU CLOUD ===")
                do_bang_thong(self._log)
                self._log(f"Ket noi: {ten}...")
                kq = tai_file(gid, raw, wim_path, self._ui, self._log, self._huy)
                if kq == "WEB_REDIRECT":
                    try:
                        os.remove(wim_path)
                    except:
                        pass
                    messagebox.showinfo("Tai Thu Cong", "May chu ban. Da mo link tai tren Web.")
                    return self._reset("Cho tai thu cong...")
                elif not kq:
                    return self._reset("Tien trinh bi huy.")

            # Kiem tra WIM
            self._log("Kiem tra tinh toan ven file WIM...")
            r = _chay(f'dism /Get-WimInfo /WimFile:"{wim_path}"')
            if r.returncode != 0:
                try:
                    os.remove(wim_path)
                except:
                    pass
                raise Exception("File WIM bi loi! He thong chan dinh dang o C.")
            self._log("File WIM hop le 100%.")

            if self.var_test.get():
                messagebox.showinfo(
                    "Kiem Thu",
                    f"WinRE da tiem OK\nWIM tai ve: {wim_path}\nChe do Test: Hoan thanh."
                )
                return self._reset("Kiem thu thanh cong.")

            # ---- BUOC 4: Boot vao WinRE ----
            boot_vao_winre(self._log)
            messagebox.showinfo(
                "Thanh Cong",
                "Moi thu da san sang!\n"
                "WinRE da duoc cau hinh.\n"
                "install.wim da tai ve.\n"
                "Bam OK -> may tu khoi dong va bung Windows."
            )
            os.system("shutdown /r /f /t 2")

        except Exception as e:
            messagebox.showerror("Loi Ky Thuat", str(e))
            self._reset("Tien trinh that bai.")
        finally:
            for f in [os.path.join(thu_muc, "prep_winre.ps1"),
                      os.path.join(thu_muc, "aria2c.exe")]:
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass


if __name__ == "__main__":
    app = App()
    app.mainloop()