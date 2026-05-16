import os
import sys
import time
import ctypes
import string
import shutil
import urllib.request
import urllib.parse
import urllib.error
import re
import csv
import threading
import subprocess
import random
import webbrowser
import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import base64

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & BẢO MẬT
# ==========================================
DUONG_DAN_KHO_DU_LIEU = "https://raw.githubusercontent.com/tuantran19912512/quickinstallwindows/refs/heads/main/list_win.csv"
CLOUD_WINRE_URL = "https://huggingface.co/datasets/tuantran1991/windows/resolve/main/Winre.wim"

DANH_SACH_KHOA_API = [
    "QUl6YVN5Q3VKUkJaTDZnUU8tdVZOMWVvdHhmMlppTXNtYy1sandR",
    "QUl6YVN5QlRhVmRQdmlLaUJyR0JUVk0tUlRiVW51QUdFUzRWck1v",
    "QUl6YVN5QkI0NENOamtHRkdQSjhBaVZaMURxZFJnc3M5MDc4QThv",
    "QUl6YVN5Q2IzaE1LUVNOamt2bFNKbUlhTGtYcVNybFpWaFNSTThR",
    "QUl6YVN5Q2V0SVlWVzRsQmlULTd3TzdNQUJoWlNVQ0dKR1puQTM0"
]

# ==========================================
# 2. LÕI KIỂM SOÁT QUYỀN HỆ THỐNG
# ==========================================
def kiem_tra_quyen_quan_tri():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if not kiem_tra_quyen_quan_tri():
    if getattr(sys, 'frozen', False):
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1)
    sys.exit()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ==========================================
# 3. CÁC CÔNG CỤ TIỆN ÍCH
# ==========================================
def do_bang_thong_mang(ham_ghi_log):
    ham_ghi_log("Đang đo lường băng thông mạng...")
    try:
        url_kiem_tra = "https://speed.cloudflare.com/__down?bytes=1048576"
        yeu_cau = urllib.request.Request(url_kiem_tra, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        thoi_gian_bat_dau = time.time()
        with urllib.request.urlopen(yeu_cau, timeout=5) as phan_hoi:
            du_lieu_tai_ve = phan_hoi.read()
        thoi_gian_hoan_thanh = time.time() - thoi_gian_bat_dau
        toc_do_thuc_te = (len(du_lieu_tai_ve) / (1024 * 1024)) / max(thoi_gian_hoan_thanh, 0.001)
        ham_ghi_log(f"Đã đo xong. Tốc độ mạng: ~ {toc_do_thuc_te:.1f} MB/s")
        return toc_do_thuc_te
    except Exception:
        return 5.0

def go_bo_bitlocker(ham_ghi_log):
    ham_ghi_log("Đang dò quét trạng thái mã hóa BitLocker...")
    try:
        o_dia_he_thong = os.environ.get('SystemDrive', 'C:')
        tien_trinh = subprocess.run(
            f'manage-bde -status {o_dia_he_thong}', shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        ket_qua_kiem_tra = tien_trinh.stdout.decode('utf-8', errors='ignore') if tien_trinh.stdout else ""
        danh_sach_tu_khoa = ["Mã hóa", "Encryption", "完全な暗号化", "Fully Encrypted", "Protection On"]
        if any(tu_khoa in ket_qua_kiem_tra for tu_khoa in danh_sach_tu_khoa):
            ham_ghi_log(f"Phát hiện BitLocker! Đang giải mã ép buộc trên {o_dia_he_thong}...")
            subprocess.run(f'manage-bde -off {o_dia_he_thong}', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass

def tim_o_dia_luu_tru_an_toan():
    mat_na_o_dia = ctypes.windll.kernel32.GetLogicalDrives()
    danh_sach_o = [ky_tu for vi_tri, ky_tu in enumerate(string.ascii_uppercase) if mat_na_o_dia & (1 << vi_tri)]
    o_cai_dat_hien_tai = os.environ.get('SystemDrive', 'C:')[0]

    o_dia_toi_uu = None
    dung_luong_lon_nhat = 0

    for o_dia in danh_sach_o:
        if o_dia == o_cai_dat_hien_tai: continue
        duong_dan_goc = f"{o_dia}:\\"
        if ctypes.windll.kernel32.GetDriveTypeW(duong_dan_goc) != 3: continue
        try:
            _, _, dung_luong_trong = shutil.disk_usage(duong_dan_goc)
            if dung_luong_trong > 10 * 1024**3 and dung_luong_trong > dung_luong_lon_nhat:
                dung_luong_lon_nhat = dung_luong_trong
                o_dia_toi_uu = o_dia
        except: pass

    if not o_dia_toi_uu: raise Exception("Không tìm thấy phân vùng lưu trữ nào trống trên 10GB!")
    return o_dia_toi_uu

def sao_luu_du_lieu_he_thong(thu_muc_dich, lua_chon_driver, lua_chon_wifi, ham_ghi_log):
    kich_ban_setup_complete = '@echo off\n'

    if lua_chon_wifi:
        ham_ghi_log("Đang bóc tách và sao lưu WiFi...")
        thu_muc_chua_wifi = os.path.join(thu_muc_dich, "WiFi")
        os.makedirs(thu_muc_chua_wifi, exist_ok=True)
        try:
            tien_trinh_wifi = subprocess.run(
                'netsh wlan show interfaces', shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            thong_tin_mang = tien_trinh_wifi.stdout.decode('utf-8', errors='ignore') if tien_trinh_wifi.stdout else ""
            ten_wifi_dang_dung = re.search(r'SSID\s*:\s*(.*)', thong_tin_mang)
            if ten_wifi_dang_dung:
                with open(os.path.join(thu_muc_chua_wifi, "current_ssid.txt"), "w", encoding="utf-8") as tep_luu_ten:
                    tep_luu_ten.write(ten_wifi_dang_dung.group(1).strip())
            subprocess.run(
                f'netsh wlan export profile key=clear folder="{thu_muc_chua_wifi}"',
                shell=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            kich_ban_setup_complete += (
                'sc config wlansvc start= auto\nnet start wlansvc\ntimeout /t 3 /nobreak >nul\n'
                'for %%f in ("%~dp0WiFi\\*.xml") do netsh wlan add profile filename="%%f" user=all\n'
                'if exist "%~dp0WiFi\\current_ssid.txt" (set /p WLAN_SSID=<"%~dp0WiFi\\current_ssid.txt"\nnetsh wlan connect name="%WLAN_SSID%")\n'
                'rd /s /q "%~dp0WiFi" >nul 2>&1\n\n'
            )
        except Exception: pass

    kich_ban_setup_complete += (
        'del /q /f /s "%WINDIR%\\Temp\\*.*" >nul 2>&1\n'
        'del /q /f /s "%WINDIR%\\Prefetch\\*.*" >nul 2>&1\n'
        'net stop wuauserv >nul 2>&1\n'
        'del /q /f /s "%WINDIR%\\SoftwareDistribution\\Download\\*.*" >nul 2>&1\n'
        'net start wuauserv >nul 2>&1\n'
        'del /q /f /s "%TEMP%\\*.*" >nul 2>&1\n'
        'rd /s /q "%SystemDrive%\\$Recycle.Bin" >nul 2>&1\n'
        'for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (if exist "%%D:\\ZT_Cloud_Install" rd /s /q "%%D:\\ZT_Cloud_Install" >nul 2>&1)\n'
        'del /f /q "%~f0" >nul 2>&1\n'
    )

    with open(os.path.join(thu_muc_dich, "SetupComplete.cmd"), "w", encoding="utf-8") as tep_lenh:
        tep_lenh.write(kich_ban_setup_complete)

    if lua_chon_driver != "Không Backup Driver":
        ham_ghi_log(f"Đang bóc tách trình điều khiển ({lua_chon_driver})...")
        thu_muc_chua_driver = os.path.join(thu_muc_dich, "Drivers")
        os.makedirs(thu_muc_chua_driver, exist_ok=True)
        if lua_chon_driver == "Backup Toàn Bộ Driver":
            subprocess.run(
                ["powershell", "-Command", f'Export-WindowsDriver -Online -Destination "{thu_muc_chua_driver}"'],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            thu_muc_tam_thoi = os.path.join(thu_muc_dich, "DrvTemp")
            lenh_sao_luu_chon_loc = (
                f"$drvs = Export-WindowsDriver -Online -Destination '{thu_muc_tam_thoi}';"
                f" foreach ($d in $drvs) {{ if ($d.ClassName -match 'Net|WLAN|Bluetooth') {{"
                f" Copy-Item (Split-Path $d.OriginalFileName) -Destination '{thu_muc_chua_driver}' -Recurse -Force }} }};"
                f" Remove-Item '{thu_muc_tam_thoi}' -Recurse -Force"
            )
            subprocess.run(
                ["powershell", "-Command", lenh_sao_luu_chon_loc],
                creationflags=subprocess.CREATE_NO_WINDOW
            )

# ==========================================
# 4. GIAI ĐOẠN 1: TÌM / TẢI WINRE.WIM
# ==========================================
def tim_hoac_tai_winre(thu_muc_cai_dat, ham_ghi_log, su_kien_huy):
    """
    Tìm winre.wim nội bộ (nhiều vị trí). Nếu không thấy thì tải thẳng từ HuggingFace.
    Trả về đường dẫn đầy đủ tới winre.wim đã sẵn sàng, hoặc raise Exception.
    """
    ham_ghi_log("=== [BƯỚC 1] XỬ LÝ WINRE.WIM TRƯỚC ===")
    ham_ghi_log("Đang tìm kiếm winre.wim nội bộ trên máy...")

    duong_dan_tim_thay = ""

    # --- Danh sách vị trí ưu tiên ---
    danh_sach_vi_tri = [
        "C:\\Windows\\System32\\Recovery\\winre.wim",
        "C:\\Recovery\\WindowsRE\\winre.wim",
    ]

    for duong_dan in danh_sach_vi_tri:
        try:
            subprocess.run(
                f'attrib -h -s -r "{duong_dan}"', shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if os.path.exists(duong_dan) and os.path.getsize(duong_dan) > 1024 * 1024:
                duong_dan_tim_thay = duong_dan
                ham_ghi_log(f"Tìm thấy WinRE nội bộ: {duong_dan_tim_thay}")
                break
        except Exception:
            pass

    # --- Thử trong WinSxS nếu chưa tìm thấy ---
    if not duong_dan_tim_thay:
        ham_ghi_log("Không thấy ở vị trí chuẩn. Đang quét thư mục WinSxS...")
        try:
            ket_qua_tim = subprocess.run(
                'where /r C:\\Windows\\WinSxS winre.wim', shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            dong_dau_tien = ket_qua_tim.stdout.decode('utf-8', errors='ignore').strip().splitlines()
            if dong_dau_tien:
                duong_dan_tim_thay = dong_dau_tien[0].strip()
                ham_ghi_log(f"Tìm thấy trong WinSxS: {duong_dan_tim_thay}")
        except Exception:
            pass

    # --- Fallback: tải từ HuggingFace ---
    if not duong_dan_tim_thay:
        ham_ghi_log("Không tìm thấy WinRE nội bộ. Bắt đầu tải từ HuggingFace Cloud...")
        thu_muc_winre = "C:\\Recovery\\WindowsRE"
        os.makedirs(thu_muc_winre, exist_ok=True)
        duong_dan_cloud = os.path.join(thu_muc_winre, "winre.wim")

        try:
            [Net_ServicePointManager_SecurityProtocol] = [None]  # placeholder
            yeu_cau = urllib.request.Request(
                CLOUD_WINRE_URL,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(yeu_cau, timeout=600) as phan_hoi:
                tong_kich_thuoc = int(phan_hoi.getheader('Content-Length', 0))
                da_tai = 0
                bat_dau = time.time()
                with open(duong_dan_cloud, 'wb') as tep:
                    while True:
                        if su_kien_huy.is_set():
                            raise Exception("Người dùng hủy tải WinRE.")
                        khoi = phan_hoi.read(1024 * 1024)
                        if not khoi:
                            break
                        tep.write(khoi)
                        da_tai += len(khoi)
                        if tong_kich_thuoc > 0:
                            phan_tram = da_tai / tong_kich_thuoc * 100
                            toc_do = da_tai / max(time.time() - bat_dau, 0.001) / (1024 * 1024)
                            ham_ghi_log(f"Tải WinRE: {phan_tram:.1f}% | {toc_do:.1f} MB/s")

            if os.path.exists(duong_dan_cloud) and os.path.getsize(duong_dan_cloud) > 1024 * 1024:
                duong_dan_tim_thay = duong_dan_cloud
                ham_ghi_log("Tải WinRE từ Cloud thành công!")
            else:
                raise Exception("File WinRE tải về bị lỗi hoặc rỗng!")

        except Exception as e:
            raise Exception(f"Không thể tải WinRE từ Cloud: {str(e)}")

    return duong_dan_tim_thay

# ==========================================
# 5. GIAI ĐOẠN 2: TIÊM KỊCH BẢN VÀO WINRE
# ==========================================
def tiem_kich_ban_vao_winre(duong_dan_winre_goc, thu_muc_cai_dat, ten_may, so_dia, so_phan_vung, ham_ghi_log):
    """
    Mount winre.wim → tiêm LenhRE.cmd + winpeshl.ini → Commit.
    Sau đó đăng ký và bật WinRE. KHÔNG boot ở bước này.
    """
    ham_ghi_log("=== [BƯỚC 2] TIÊM KỊCH BẢN VÀO WINRE ===")

    ma_nguon_ps = f"""
$ErrorActionPreference = 'Continue'

$FoundWIM = "{duong_dan_winre_goc}"
$ThuMucGiaoTiep = "C:\\MountRE"
$WinRECopy     = "C:\\winre_xu_ly.wim"

# Dọn mount point cũ nếu còn sót
if (Test-Path $ThuMucGiaoTiep) {{
    dism.exe /Unmount-Image /MountDir:$ThuMucGiaoTiep /Discard | Out-Null
    Remove-Item $ThuMucGiaoTiep -Recurse -Force -ErrorAction SilentlyContinue
}}
New-Item -ItemType Directory -Force -Path $ThuMucGiaoTiep | Out-Null

# Tắt Fast Startup để tránh xung đột
Write-Output "[RE-LOG] Tắt Fast Startup..."
powercfg /h off | Out-Null

# Hủy đăng ký WinRE cũ
Write-Output "[RE-LOG] Hủy đăng ký WinRE cũ..."
reagentc.exe /disable | Out-Null
Start-Sleep -Seconds 2

# Sao chép file để xử lý an toàn
Copy-Item $FoundWIM $WinRECopy -Force
cmd.exe /c "attrib -h -s -r `"$WinRECopy`" >nul 2>&1"

# Mount
Write-Output "[RE-LOG] Mount WinRE vào RAM..."
$MountLog = dism.exe /Mount-Image /ImageFile:$WinRECopy /Index:1 /MountDir:$ThuMucGiaoTiep
if ($LASTEXITCODE -ne 0) {{
    Write-Output "[RE-LOG] LOI MOUNT: $MountLog"
    exit 1
}}

# Kịch bản thực thi trong RE
$LenhRE = @"
@echo off
for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist "%%D:\\ZT_Cloud_Install\\install.wim" set "WPATH=%%D:\\ZT_Cloud_Install"
)
(echo select disk {so_dia} & echo select partition {so_phan_vung} & echo assign letter=W & echo format quick fs=ntfs label="Windows") | diskpart
dism /apply-image /imagefile:"%WPATH%\\install.wim" /index:1 /applydir:W:\\
if exist "%WPATH%\\Drivers" ( dism /image:W:\\ /Add-Driver /Driver:"%WPATH%\\Drivers" /Recurse )
bcdboot W:\\Windows

reg load HKLM\\ZT W:\\Windows\\System32\\config\\SYSTEM
reg add "HKLM\\ZT\\Setup\\LabConfig" /v BypassTPMCheck /t REG_DWORD /d 1 /f
reg add "HKLM\\ZT\\Setup\\LabConfig" /v BypassSecureBootCheck /t REG_DWORD /d 1 /f
reg unload HKLM\\ZT

reg load HKLM\\ZTSOFTWARE W:\\Windows\\System32\\config\\SOFTWARE
reg add "HKLM\\ZTSOFTWARE\\Microsoft\\Windows\\CurrentVersion\\OOBE" /v BypassNRO /t REG_DWORD /d 1 /f
reg unload HKLM\\ZTSOFTWARE

reg load HKLM\\ZTSYSTEM W:\\Windows\\System32\\config\\SYSTEM
reg add "HKLM\\ZTSYSTEM\\ControlSet001\\Control\\ComputerName\\ComputerName" /v ComputerName /t REG_SZ /d {ten_may} /f
reg add "HKLM\\ZTSYSTEM\\ControlSet001\\Control\\ComputerName\\ActiveComputerName" /v ComputerName /t REG_SZ /d {ten_may} /f
reg add "HKLM\\ZTSYSTEM\\ControlSet001\\Services\\Tcpip\\Parameters" /v Hostname /t REG_SZ /d {ten_may} /f
reg add "HKLM\\ZTSYSTEM\\ControlSet001\\Services\\Tcpip\\Parameters" /v "NV Hostname" /t REG_SZ /d {ten_may} /f
reg unload HKLM\\ZTSYSTEM

mkdir W:\\Windows\\Panther
copy /Y "%WPATH%\\unattend.xml" W:\\Windows\\Panther\\unattend.xml
if exist "%WPATH%\\SetupComplete.cmd" ( mkdir W:\\Windows\\Setup\\Scripts & copy /Y "%WPATH%\\SetupComplete.cmd" W:\\Windows\\Setup\\Scripts\\ )
if exist "%WPATH%\\WiFi" ( mkdir W:\\Windows\\Setup\\Scripts\\WiFi & xcopy /E /Y /I "%WPATH%\\WiFi" W:\\Windows\\Setup\\Scripts\\WiFi\\ )

wpeutil reboot
"@

Write-Output "[RE-LOG] Tiêm LenhRE.cmd và winpeshl.ini..."
$LenhRE | Out-File "$ThuMucGiaoTiep\\Windows\\System32\\LenhRE.cmd" -Encoding oem
'[LaunchApps]' + [char]13 + [char]10 + 'X:\\Windows\\System32\\LenhRE.cmd' |
    Out-File "$ThuMucGiaoTiep\\Windows\\System32\\winpeshl.ini" -Encoding ascii

# Commit
Write-Output "[RE-LOG] Đóng gói lại WinRE (Commit)..."
$CommitLog = dism.exe /Unmount-Image /MountDir:$ThuMucGiaoTiep /Commit
if ($LASTEXITCODE -ne 0) {{
    Write-Output "[RE-LOG] LOI COMMIT: $CommitLog"
    dism.exe /Unmount-Image /MountDir:$ThuMucGiaoTiep /Discard | Out-Null
    exit 1
}}

# Chép vào vị trí chuẩn
$SafeRePath = "C:\\Recovery\\WindowsRE"
if (-not (Test-Path $SafeRePath)) {{ New-Item -ItemType Directory -Force -Path $SafeRePath | Out-Null }}
Copy-Item $WinRECopy "$SafeRePath\\winre.wim" -Force
cmd.exe /c "attrib -h -s -r `"$SafeRePath\\winre.wim`" >nul 2>&1"
Remove-Item $WinRECopy -Force -ErrorAction SilentlyContinue

# Đăng ký và bật WinRE
Write-Output "[RE-LOG] Đăng ký đường dẫn WinRE mới..."
$kq_set = reagentc.exe /setreimage /path $SafeRePath
Write-Output $kq_set

Write-Output "[RE-LOG] Kích hoạt WinRE..."
$kq_en = reagentc.exe /enable
if ($LASTEXITCODE -ne 0) {{
    Write-Output "[RE-LOG] CANH BAO enable: $kq_en"
    exit 1
}}

Write-Output "[RE-LOG] HOÀN TẤT TIÊM KỊCH BẢN WINRE!"
"""

    duong_dan_ps1 = os.path.join(thu_muc_cai_dat, "prep_winre.ps1")
    try:
        with open(duong_dan_ps1, "w", encoding="utf-8") as f:
            f.write(ma_nguon_ps)

        ham_ghi_log("--- Bắt đầu xử lý WinRE ---")
        tien_trinh = subprocess.Popen(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", duong_dan_ps1],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
            text=True, encoding='utf-8', errors='ignore'
        )
        for dong in tien_trinh.stdout:
            dong_sach = dong.strip()
            if dong_sach:
                ham_ghi_log(dong_sach)
        tien_trinh.wait()
        ham_ghi_log("--- Kết thúc xử lý WinRE ---")

        if tien_trinh.returncode != 0:
            raise Exception("Tiêm kịch bản WinRE thất bại! Xem log phía trên để kiểm tra.")
    finally:
        if os.path.exists(duong_dan_ps1):
            try: os.remove(duong_dan_ps1)
            except: pass

# ==========================================
# 6. GIAI ĐOẠN 3: BOOT VÀO WINRE
# ==========================================
def khoi_dong_vao_winre(ham_ghi_log):
    """Đặt cờ BootToRE và khởi động lại máy."""
    ham_ghi_log("=== [BƯỚC 4] ĐẶT CỜ BOOT VÀO WINRE & KHỞI ĐỘNG LẠI ===")
    tien_trinh = subprocess.run(
        "reagentc.exe /boottore", shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    ket_qua = tien_trinh.stdout.decode('utf-8', errors='ignore').strip()
    ham_ghi_log(f"reagentc /boottore: {ket_qua}")
    if tien_trinh.returncode != 0:
        raise Exception(f"Lệnh BootToRE bị từ chối! Chi tiết: {ket_qua}")
    ham_ghi_log("Hệ thống sẽ khởi động lại và bung Windows tự động...")

# ==========================================
# 7. ĐỘNG CƠ TẢI DỮ LIỆU ĐÁM MÂY
# ==========================================
def truat_xuat_du_lieu_dam_may(ma_file_tai, link_raw_du_phong, duong_dan_luu_tru,
                                ham_cap_nhat_giao_dien, ham_ghi_log, su_kien_huy):
    thu_muc_luu = os.path.dirname(duong_dan_luu_tru)
    ten_file    = os.path.basename(duong_dan_luu_tru)
    tool_aria   = "C:\\ZT_Cloud_Install\\aria2c.exe"

    if not os.path.exists(tool_aria):
        ham_ghi_log("Đang đồng bộ động cơ tải đa luồng Aria2c...")
        try:
            urllib.request.urlretrieve(
                "https://raw.githubusercontent.com/tuantran19912512/quickinstallwindows/refs/heads/main/aria2c.exe",
                tool_aria
            )
            if os.path.getsize(tool_aria) < 500000:
                os.remove(tool_aria)
                raise Exception("File aria2c tải về không hợp lệ!")
        except Exception as e:
            ham_ghi_log(f"Lỗi khởi tạo Aria2c: {str(e)}")

    url_chinh_xac = ""
    if ma_file_tai and not ma_file_tai.startswith("http"):
        for khoa_bao_mat_b64 in DANH_SACH_KHOA_API:
            try:
                khoa_api_giai_ma = base64.b64decode(khoa_bao_mat_b64).decode('utf-8')
                url_chinh_xac = (
                    f"https://www.googleapis.com/drive/v3/files/{ma_file_tai}"
                    f"?alt=media&key={khoa_api_giai_ma}&acknowledgeAbuse=true"
                )
                break
            except: continue
    elif link_raw_du_phong:
        url_chinh_xac = link_raw_du_phong

    if url_chinh_xac and os.path.exists(tool_aria):
        ham_ghi_log("Đã kích hoạt Aria2c Engine: Xé file tải 16 luồng siêu tốc!")
        cmd = [tool_aria, "-x", "16", "-s", "16", "-k", "5M", "-c",
               "-d", thu_muc_luu, "-o", ten_file, url_chinh_xac]
        tien_trinh_aria = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
            universal_newlines=True, encoding='utf-8', errors='ignore'
        )
        for dong in tien_trinh_aria.stdout:
            if su_kien_huy.is_set():
                tien_trinh_aria.kill()
                return False
            tim_phan_tram = re.search(r'\((\d+)%\)', dong)
            if tim_phan_tram:
                phan_tram = int(tim_phan_tram.group(1))
                ham_cap_nhat_giao_dien(phan_tram, 0, 100, 0)
        tien_trinh_aria.wait()
        if os.path.exists(duong_dan_luu_tru) and os.path.getsize(duong_dan_luu_tru) > 1024 * 1024:
            sz = os.path.getsize(duong_dan_luu_tru)
            ham_cap_nhat_giao_dien(100, sz, sz, 0)
            return "SUCCESS"

    ham_ghi_log("Chuyển về luồng tải dự phòng (Python Native Single-Thread)...")
    try:
        if not url_chinh_xac: raise Exception("Không có URL hợp lệ.")
        yeu_cau_ket_noi = urllib.request.Request(
            url_chinh_xac,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(yeu_cau_ket_noi, timeout=15) as cau_tra_loi:
            tong_kich_thuoc = int(cau_tra_loi.getheader('Content-Length', 0))
            with open(duong_dan_luu_tru, 'wb') as tep:
                da_tai = 0; bat_dau = time.time()
                while True:
                    if su_kien_huy.is_set(): return False
                    khoi = cau_tra_loi.read(1024 * 1024)
                    if not khoi: break
                    tep.write(khoi); da_tai += len(khoi)
                    if tong_kich_thuoc > 0:
                        ham_cap_nhat_giao_dien(
                            (da_tai / tong_kich_thuoc) * 100, da_tai,
                            tong_kich_thuoc,
                            da_tai / max(time.time() - bat_dau, 0.001)
                        )
        return "SUCCESS"
    except Exception:
        if ma_file_tai and not ma_file_tai.startswith("http"):
            ham_ghi_log("Các luồng tải ngầm bị chặn. Chuyển hướng ra Web...")
            try:
                webbrowser.open(f"https://drive.google.com/file/d/{ma_file_tai}/view")
                return "WEB_REDIRECT"
            except: pass
    return False

# ==========================================
# 8. TẠO FILE UNATTEND.XML
# ==========================================
def tao_unattend_xml(thu_muc_cai_dat, ten_may):
    noi_dung = f"""<?xml version="1.0" encoding="utf-8"?>
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
    with open(os.path.join(thu_muc_cai_dat, "unattend.xml"), "w", encoding="utf-8") as f:
        f.write(noi_dung)

# ==========================================
# 9. LẤY THÔNG TIN ĐĨA / PHÂN VÙNG HỆ THỐNG
# ==========================================
def lay_thong_tin_phan_vung_he_thong():
    """Trả về (disk_number, partition_number) của phân vùng chứa C:\\"""
    ky_tu = os.environ.get('SystemDrive', 'C:')[0]
    ket_qua = subprocess.run(
        ["powershell", "-Command",
         f"$p = Get-Partition -DriveLetter '{ky_tu}'; Write-Output \"$($p.DiskNumber) $($p.PartitionNumber)\""],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    dong = ket_qua.stdout.decode('utf-8', errors='ignore').strip()
    phan_tu = dong.split()
    if len(phan_tu) == 2:
        return int(phan_tu[0]), int(phan_tu[1])
    return 0, 1  # fallback

# ==========================================
# 10. GIAO DIỆN ĐIỀU KHIỂN CHÍNH
# ==========================================
class BangDieuKhienTrungTam(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Trạm Triển Khai Kỹ Thuật - Tự Động Định Danh & Dọn Rác")
        self.geometry("850x720")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.su_kien_huy_lenh = threading.Event()
        self.co_the_hoat_dong  = False
        self.mang_luu_nut_bam  = []

        # --- Header ---
        self.khung_phan_dau = ctk.CTkFrame(self, fg_color="transparent")
        self.khung_phan_dau.grid(row=0, column=0, pady=15, sticky="ew")
        ctk.CTkLabel(
            self.khung_phan_dau,
            text="HỆ THỐNG TRIỂN KHAI MÁY KHÁCH TỪ XA",
            font=("Arial", 22, "bold")
        ).pack()
        self.nhan_trang_thai_kho = ctk.CTkLabel(
            self.khung_phan_dau,
            text="Đang đồng bộ dữ liệu với kho lưu trữ...",
            text_color="gray"
        )
        self.nhan_trang_thai_kho.pack()

        # --- Thiết lập ---
        self.khung_thiet_lap = ctk.CTkFrame(self)
        self.khung_thiet_lap.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.khung_thiet_lap.grid_columnconfigure((0, 1, 2), weight=1)

        self.bien_chon_driver = ctk.StringVar(value="Backup LAN & WIFI")
        ctk.CTkOptionMenu(
            self.khung_thiet_lap,
            values=["Không Backup Driver", "Backup LAN & WIFI", "Backup Toàn Bộ Driver"],
            variable=self.bien_chon_driver
        ).grid(row=0, column=0, padx=10, pady=15)

        self.bien_chon_wifi = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(self.khung_thiet_lap, text="Trích xuất WiFi",
                      variable=self.bien_chon_wifi).grid(row=0, column=1, padx=10, pady=15)

        self.bien_an_toan_test = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            self.khung_thiet_lap, text="CHẾ ĐỘ KIỂM THỬ",
            variable=self.bien_an_toan_test, progress_color="#D97706"
        ).grid(row=0, column=2, padx=10, pady=15)

        # --- Danh sách bản cài ---
        self.khung_danh_sach_os = ctk.CTkScrollableFrame(
            self, label_text=" DANH MỤC BẢN CÀI ĐẶT CÓ SẴN "
        )
        self.khung_danh_sach_os.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        self.nut_cai_local = ctk.CTkButton(
            self.khung_danh_sach_os,
            text="📁 CHỌN FILE WIM TỪ Ổ CỨNG / USB",
            font=("Arial", 14, "bold"),
            fg_color="#047857", hover_color="#065F46",
            command=self.kich_hoat_cai_dat_local
        )
        self.nut_cai_local.pack(fill="x", pady=(5, 15), padx=5)
        self.mang_luu_nut_bam.append(self.nut_cai_local)

        # --- Log ---
        self.hop_chua_nhat_ky = ctk.CTkTextbox(
            self, height=180, font=("Consolas", 12),
            fg_color="#0F172A", text_color="#38BDF8"
        )
        self.hop_chua_nhat_ky.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        self.hop_chua_nhat_ky.insert("0.0", "Hệ thống lõi 31.0 đã khởi tạo thành công.\n")
        self.hop_chua_nhat_ky.configure(state="disabled")

        # --- Thanh tiến độ ---
        self.khung_phan_cuoi = ctk.CTkFrame(self, fg_color="transparent")
        self.khung_phan_cuoi.grid(row=4, column=0, padx=20, pady=15, sticky="ew")
        self.khung_phan_cuoi.grid_columnconfigure(0, weight=1)

        self.thanh_bar_tien_do = ctk.CTkProgressBar(self.khung_phan_cuoi, height=12)
        self.thanh_bar_tien_do.grid(row=0, column=0, padx=(0, 20), sticky="ew")
        self.thanh_bar_tien_do.set(0)

        self.nhan_chi_so_tai = ctk.CTkLabel(
            self.khung_phan_cuoi, text="0% | Tốc độ: 0 MB/s",
            font=("Arial", 12, "bold")
        )
        self.nhan_chi_so_tai.grid(row=1, column=0, sticky="w")

        self.nut_huy_bo = ctk.CTkButton(
            self.khung_phan_cuoi, text="🛑 HỦY TIẾN TRÌNH",
            fg_color="#BE123C", hover_color="#9F1239",
            state="disabled", command=self.kich_hoat_lenh_huy
        )
        self.nut_huy_bo.grid(row=0, column=1, rowspan=2)

        self.tien_hanh_quet_kho_du_lieu()

    # --- Ghi log ---
    def in_nhat_ky_he_thong(self, dong_thong_diep):
        self.after(0, self._tien_hanh_ghi_log, dong_thong_diep)

    def _tien_hanh_ghi_log(self, dong_thong_diep):
        dau_thoi_gian = datetime.datetime.now().strftime("%H:%M:%S")
        self.hop_chua_nhat_ky.configure(state="normal")
        self.hop_chua_nhat_ky.insert("end", f"[{dau_thoi_gian}] {dong_thong_diep}\n")
        so_dong = int(self.hop_chua_nhat_ky.index('end-1c').split('.')[0])
        if so_dong > 200:
            self.hop_chua_nhat_ky.delete("1.0", f"{so_dong - 200}.0")
        self.hop_chua_nhat_ky.see("end")
        self.hop_chua_nhat_ky.configure(state="disabled")

    # --- Quét kho CSV ---
    def tien_hanh_quet_kho_du_lieu(self):
        def luong_xu_ly_mang():
            try:
                yeu_cau_csv = urllib.request.Request(
                    DUONG_DAN_KHO_DU_LIEU,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                phan_hoi_csv  = urllib.request.urlopen(yeu_cau_csv)
                du_lieu_chuoi = phan_hoi_csv.read().decode('utf-8-sig').splitlines()
                trinh_doc_csv = csv.DictReader(du_lieu_chuoi)
                cac_cot = [c.strip() for c in trinh_doc_csv.fieldnames if c]

                khoa_ten  = next((c for c in cac_cot if 'name' in c.lower() or 'tên' in c.lower()), None)
                khoa_id   = next((c for c in cac_cot if 'id' in c.lower() or ('link' in c.lower() and 'raw' not in c.lower())), None)
                khoa_raw  = next((c for c in cac_cot if 'linkraw' in c.lower().replace(" ", "")), None)

                if not khoa_ten: return
                so_luong = 0
                for hang in trinh_doc_csv:
                    ten   = str(hang.get(khoa_ten, '')).strip()
                    link  = str(hang.get(khoa_id, '')).strip() if khoa_id else ""
                    raw   = str(hang.get(khoa_raw, '')).strip() if khoa_raw else ""
                    id_gg = ""
                    tim   = re.search(r'[-\w]{25,}', link)
                    if tim: id_gg = tim.group(0)
                    if ten and ".wim" in ten.lower() and (id_gg or raw):
                        self.sinh_nut_cai_dat(ten, id_gg, raw)
                        so_luong += 1

                self.after(0, lambda: self.nhan_trang_thai_kho.configure(
                    text=f"✅ Đã giải mã {so_luong} bản cài", text_color="#10B981"
                ))
            except Exception:
                self.after(0, lambda: self.nhan_trang_thai_kho.configure(
                    text="❌ Lỗi phân tích cấu trúc", text_color="#EF4444"
                ))

        threading.Thread(target=luong_xu_ly_mang, daemon=True).start()

    def sinh_nut_cai_dat(self, nhan, ma, raw):
        nut = ctk.CTkButton(
            self.khung_danh_sach_os,
            text=f"📥 TẢI VÀ ÁP DỤNG: {nhan}",
            font=("Arial", 13, "bold"), fg_color="#1E293B", anchor="w",
            command=lambda n=nhan, m=ma, r=raw: self.khoi_tao_tien_trinh(n, m, r)
        )
        nut.pack(fill="x", pady=2, padx=5)
        self.mang_luu_nut_bam.append(nut)

    def kich_hoat_lenh_huy(self):
        self.su_kien_huy_lenh.set()
        self.nut_huy_bo.configure(state="disabled")

    def khoa_giao_dien_cai_dat(self):
        for nut in self.mang_luu_nut_bam: nut.configure(state="disabled")

    def mo_khoa_giao_dien_cai_dat(self):
        for nut in self.mang_luu_nut_bam: nut.configure(state="normal")

    def kich_hoat_cai_dat_local(self):
        if self.co_the_hoat_dong:
            messagebox.showwarning("Cảnh Báo", "Hệ thống đang bận chạy một tiến trình khác!")
            return
        duong_dan_file = filedialog.askopenfilename(filetypes=[("Tập tin Windows Image", "*.wim")])
        if not duong_dan_file: return
        if not self.bien_an_toan_test.get() and not messagebox.askyesno(
            "Cảnh Báo", "Hành động này sẽ XÓA SẠCH ổ C. Tiếp tục?"
        ): return

        self.co_the_hoat_dong = True
        self.su_kien_huy_lenh.clear()
        self.nut_huy_bo.configure(state="normal")
        self.khoa_giao_dien_cai_dat()
        threading.Thread(
            target=self.luong_dieu_phoi_chinh,
            args=("Cài đặt từ Local", None, None, duong_dan_file),
            daemon=True
        ).start()

    def khoi_tao_tien_trinh(self, nhan, ma, raw):
        if self.co_the_hoat_dong:
            messagebox.showwarning("Cảnh Báo", "Hệ thống đang bận chạy một tiến trình khác!")
            return
        if not self.bien_an_toan_test.get() and not messagebox.askyesno(
            "Cảnh Báo", "Hành động này sẽ XÓA SẠCH ổ C. Tiếp tục?"
        ): return

        self.co_the_hoat_dong = True
        self.su_kien_huy_lenh.clear()
        self.nut_huy_bo.configure(state="normal")
        self.khoa_giao_dien_cai_dat()
        threading.Thread(
            target=self.luong_dieu_phoi_chinh,
            args=(nhan, ma, raw, None),
            daemon=True
        ).start()

    # ==========================================
    # LUỒNG CHÍNH: THỨ TỰ MỚI
    # ==========================================
    def luong_dieu_phoi_chinh(self, nhan_ten, ma_file, link_raw, duong_dan_local=None):
        thu_muc_cai_dat = ""
        try:
            # --- Chuẩn bị hạ tầng ---
            go_bo_bitlocker(self.in_nhat_ky_he_thong)
            o_dia_an_toan   = tim_o_dia_luu_tru_an_toan()
            thu_muc_cai_dat = f"{o_dia_an_toan}:\\ZT_Cloud_Install"
            os.makedirs(thu_muc_cai_dat, exist_ok=True)

            # Backup WiFi / Driver
            sao_luu_du_lieu_he_thong(
                thu_muc_cai_dat,
                self.bien_chon_driver.get(),
                self.bien_chon_wifi.get(),
                self.in_nhat_ky_he_thong
            )

            # Lấy thông tin phân vùng để nhúng vào kịch bản RE
            so_dia, so_phan_vung = lay_thong_tin_phan_vung_he_thong()

            # Tên máy ngẫu nhiên
            ten_may = "PC-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            self.in_nhat_ky_he_thong(f"Tên máy được cấp phát: {ten_may}")

            # Tạo unattend.xml
            tao_unattend_xml(thu_muc_cai_dat, ten_may)

            # ==================================================
            # BƯỚC 1: TÌM / TẢI WINRE.WIM
            # ==================================================
            duong_dan_winre = tim_hoac_tai_winre(
                thu_muc_cai_dat,
                self.in_nhat_ky_he_thong,
                self.su_kien_huy_lenh
            )
            if self.su_kien_huy_lenh.is_set():
                return self.khoi_phuc_trang_thai_goc("Tiến trình bị hủy ở bước WinRE.")

            # ==================================================
            # BƯỚC 2: TIÊM KỊCH BẢN VÀO WINRE
            # ==================================================
            tiem_kich_ban_vao_winre(
                duong_dan_winre,
                thu_muc_cai_dat,
                ten_may, so_dia, so_phan_vung,
                self.in_nhat_ky_he_thong
            )
            if self.su_kien_huy_lenh.is_set():
                return self.khoi_phuc_trang_thai_goc("Tiến trình bị hủy sau bước tiêm WinRE.")

            self.in_nhat_ky_he_thong("✅ WinRE đã sẵn sàng. Bắt đầu tải install.wim...")

            # ==================================================
            # BƯỚC 3: TẢI / COPY install.wim
            # ==================================================
            vi_tri_luu_wim = os.path.join(thu_muc_cai_dat, "install.wim")

            if duong_dan_local:
                if os.path.abspath(duong_dan_local).lower() == os.path.abspath(vi_tri_luu_wim).lower():
                    self.in_nhat_ky_he_thong("File WIM đã nằm sẵn trong khoang. Bỏ qua bước copy...")
                else:
                    self.in_nhat_ky_he_thong("=== [BƯỚC 3] COPY install.wim NỘI BỘ ===")
                    tong_dung_luong = os.path.getsize(duong_dan_local)
                    da_chep = 0
                    bat_dau = time.time()
                    with open(duong_dan_local, 'rb') as src, open(vi_tri_luu_wim, 'wb') as dst:
                        while phan_doan := src.read(4 * 1024 * 1024):
                            if self.su_kien_huy_lenh.is_set():
                                raise Exception("Người dùng hủy copy WIM.")
                            dst.write(phan_doan)
                            da_chep += len(phan_doan)
                            toc_do = da_chep / max(time.time() - bat_dau, 0.001)
                            self.lam_moi_giao_dien_tai(
                                (da_chep / tong_dung_luong) * 100,
                                da_chep, tong_dung_luong, toc_do
                            )
                    self.in_nhat_ky_he_thong("Sao chép file hoàn tất.")
            else:
                self.in_nhat_ky_he_thong("=== [BƯỚC 3] TẢI install.wim TỪ CLOUD ===")
                do_bang_thong_mang(self.in_nhat_ky_he_thong)
                self.in_nhat_ky_he_thong(f"Mở cổng kết nối: {nhan_ten}...")
                ket_qua_tai = truat_xuat_du_lieu_dam_may(
                    ma_file, link_raw, vi_tri_luu_wim,
                    self.lam_moi_giao_dien_tai,
                    self.in_nhat_ky_he_thong,
                    self.su_kien_huy_lenh
                )
                if ket_qua_tai == "WEB_REDIRECT":
                    try: os.remove(vi_tri_luu_wim)
                    except: pass
                    messagebox.showinfo("Tải Thủ Công", "Máy chủ bận. Đã mở link tải trực tiếp trên Web.")
                    return self.khoi_phuc_trang_thai_goc("Đang chờ tải thủ công...")
                elif not ket_qua_tai:
                    return self.khoi_phuc_trang_thai_goc("Tiến trình bị hủy.")

            # Kiểm tra tính toàn vẹn WIM
            self.in_nhat_ky_he_thong("Kiểm tra tính toàn vẹn file WIM...")
            kt_wim = subprocess.run(
                f'dism /Get-WimInfo /WimFile:"{vi_tri_luu_wim}"',
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if kt_wim.returncode != 0:
                try: os.remove(vi_tri_luu_wim)
                except: pass
                raise Exception("File WIM tải về bị lỗi! Hệ thống chặn định dạng ổ C.")
            self.in_nhat_ky_he_thong("✅ File WIM an toàn 100%.")

            # Chế độ kiểm thử — dừng tại đây
            if self.bien_an_toan_test.get():
                messagebox.showinfo(
                    "Kiểm Thử",
                    f"WinRE đã tiêm ✅\nWIM đã sẵn sàng tại: {vi_tri_luu_wim}\nChế độ Test: Hoàn thành an toàn."
                )
                return self.khoi_phuc_trang_thai_goc("Kiểm thử thành công.")

            # ==================================================
            # BƯỚC 4: BOOT VÀO WINRE → XỬ LÝ TỰ ĐỘNG
            # ==================================================
            khoi_dong_vao_winre(self.in_nhat_ky_he_thong)
            messagebox.showinfo(
                "Thành Công",
                "Mọi thứ đã sẵn sàng!\n"
                "WinRE đã được cấu hình.\n"
                "install.wim đã tải về.\n"
                "Bấm OK → máy tự khởi động và bung Windows."
            )
            os.system("shutdown /r /f /t 2")

        except Exception as loi:
            messagebox.showerror("Lỗi Kỹ Thuật", str(loi))
            self.khoi_phuc_trang_thai_goc("Tiến trình thất bại.")
        finally:
            if thu_muc_cai_dat:
                for tep in [
                    os.path.join(thu_muc_cai_dat, "prep_winre.ps1"),
                    "C:\\ZT_Cloud_Install\\aria2c.exe"
                ]:
                    if os.path.exists(tep):
                        try: os.remove(tep)
                        except: pass

    def khoi_phuc_trang_thai_goc(self, thong_diep="Hoạt động tạm dừng."):
        self.co_the_hoat_dong = False
        self.after(0, lambda: self.nut_huy_bo.configure(state="disabled"))
        self.after(0, self.mo_khoa_giao_dien_cai_dat)
        self.in_nhat_ky_he_thong(thong_diep)

    def lam_moi_giao_dien_tai(self, phan_tram, da_tai, tong, toc_do):
        self.after(0, self._tien_hanh_cap_nhat_ui, phan_tram, da_tai, tong, toc_do)

    def _tien_hanh_cap_nhat_ui(self, phan_tram, da_tai, tong, toc_do):
        self.thanh_bar_tien_do.set(phan_tram / 100)
        if tong == 0:
            self.nhan_chi_so_tai.configure(text=f"{int(phan_tram)}% | Aria2c Đang kéo 16 luồng...")
        else:
            self.nhan_chi_so_tai.configure(
                text=f"{int(phan_tram)}% | {toc_do / (1024*1024):.1f} MB/s | {da_tai / 1024**3:.1f} GB"
            )


if __name__ == "__main__":
    ung_dung = BangDieuKhienTrungTam()
    ung_dung.mainloop()