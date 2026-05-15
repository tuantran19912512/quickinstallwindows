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
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import base64

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & BẢO MẬT
# ==========================================
DUONG_DAN_KHO_DU_LIEU = "https://raw.githubusercontent.com/tuantran19912512/quickinstallwindows/refs/heads/main/list_win.csv"

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
    ham_ghi_log("Đang đo lường băng thông mạng qua máy chủ Cloudflare...")
    try:
        url_kiem_tra = "https://speed.cloudflare.com/__down?bytes=1048576"
        yeu_cau = urllib.request.Request(url_kiem_tra, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        thoi_gian_bat_dau = time.time()
        with urllib.request.urlopen(yeu_cau, timeout=5) as phan_hoi:
            du_lieu_tai_ve = phan_hoi.read()
        thoi_gian_hoan_thanh = time.time() - thoi_gian_bat_dau
        toc_do_thuc_te = (len(du_lieu_tai_ve) / (1024 * 1024)) / max(thoi_gian_hoan_thanh, 0.001)
        ham_ghi_log(f"Đã đo xong. Tốc độ mạng hiện tại: ~ {toc_do_thuc_te:.1f} MB/s")
        return toc_do_thuc_te
    except Exception as loi:
        ham_ghi_log(f"Lỗi đo tốc độ ({str(loi)}). Áp dụng tốc độ giả lập mặc định.")
        return 5.0

def go_bo_bitlocker(ham_ghi_log):
    ham_ghi_log("Đang dò quét trạng thái mã hóa BitLocker trên phân vùng hệ điều hành...")
    try:
        o_dia_he_thong = os.environ.get('SystemDrive', 'C:')
        ket_qua_kiem_tra = subprocess.check_output(f'manage-bde -status {o_dia_he_thong}', shell=True).decode('utf-8', errors='ignore')
        if any(tu_khoa in ket_qua_kiem_tra for tu_khoa in ["Mã hóa", "Encryption", "完全な暗号化"]):
            ham_ghi_log(f"Phát hiện BitLocker đang khóa! Đang giải mã ép buộc trên {o_dia_he_thong}...")
            subprocess.run(f'manage-bde -off {o_dia_he_thong}', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            ham_ghi_log("Không phát hiện BitLocker. Phân vùng sạch.")
    except Exception as e:
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
            
    if not o_dia_toi_uu: raise Exception("Nghiêm trọng: Không tìm thấy phân vùng lưu trữ nào trống trên 10GB!")
    return o_dia_toi_uu

def sao_luu_du_lieu_he_thong(thu_muc_dich, lua_chon_driver, lua_chon_wifi, ham_ghi_log):
    kich_ban_setup_complete = '@echo off\n'

    if lua_chon_wifi:
        ham_ghi_log("Khởi động tiến trình bóc tách và sao lưu hồ sơ WiFi...")
        thu_muc_chua_wifi = os.path.join(thu_muc_dich, "WiFi")
        os.makedirs(thu_muc_chua_wifi, exist_ok=True)
        try:
            thong_tin_mang = subprocess.check_output('netsh wlan show interfaces', shell=True).decode('utf-8', errors='ignore')
            ten_wifi_dang_dung = re.search(r'SSID\s*:\s*(.*)', thong_tin_mang)
            if ten_wifi_dang_dung:
                with open(os.path.join(thu_muc_chua_wifi, "current_ssid.txt"), "w", encoding="utf-8") as tep_luu_ten: 
                    tep_luu_ten.write(ten_wifi_dang_dung.group(1).strip())
            subprocess.run(f'netsh wlan export profile key=clear folder="{thu_muc_chua_wifi}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            kich_ban_setup_complete += (
                'sc config wlansvc start= auto\nnet start wlansvc\ntimeout /t 3 /nobreak >nul\n'
                'for %%f in ("%~dp0WiFi\\*.xml") do netsh wlan add profile filename="%%f" user=all\n'
                'if exist "%~dp0WiFi\\current_ssid.txt" (set /p WLAN_SSID=<"%~dp0WiFi\\current_ssid.txt"\nnetsh wlan connect name="%WLAN_SSID%")\n'
                'rd /s /q "%~dp0WiFi" >nul 2>&1\n\n'
            )
        except Exception as e: ham_ghi_log(f"Cảnh báo: Không thể trích xuất WiFi ({e})")

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

    with open(os.path.join(thu_muc_dich, "SetupComplete.cmd"), "w", encoding="utf-8") as tep_lenh: tep_lenh.write(kich_ban_setup_complete)

    if lua_chon_driver != "Không Backup Driver":
        ham_ghi_log(f"Đang bóc tách trình điều khiển ({lua_chon_driver})...")
        thu_muc_chua_driver = os.path.join(thu_muc_dich, "Drivers")
        os.makedirs(thu_muc_chua_driver, exist_ok=True)
        if lua_chon_driver == "Backup Toàn Bộ Driver":
            subprocess.run(["powershell", "-Command", f'Export-WindowsDriver -Online -Destination "{thu_muc_chua_driver}"'], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            thu_muc_tam_thoi = os.path.join(thu_muc_dich, "DrvTemp")
            lenh_sao_luu_chon_loc = f"$drvs = Export-WindowsDriver -Online -Destination '{thu_muc_tam_thoi}'; foreach ($d in $drvs) {{ if ($d.ClassName -match 'Net|WLAN|Bluetooth') {{ Copy-Item (Split-Path $d.OriginalFileName) -Destination '{thu_muc_chua_driver}' -Recurse -Force }} }}; Remove-Item '{thu_muc_tam_thoi}' -Recurse -Force"
            subprocess.run(["powershell", "-Command", lenh_sao_luu_chon_loc], creationflags=subprocess.CREATE_NO_WINDOW)

# ==========================================
# 4. LÕI TIÊM WINRE (OFFLINE REGISTRY & BYPASS TPM)
# ==========================================
def tiem_kich_ban_winre(o_dia_luu_wim, ham_ghi_log):
    chuoi_ngau_nhien = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    ten_may_chong_trung = f"PC-{chuoi_ngau_nhien}"
    ham_ghi_log(f"Đã cấp phát tên máy: {ten_may_chong_trung}")

    noi_dung_unattend = f"""<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
    <settings pass="oobeSystem">
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
            <OOBE><HideEULAPage>true</HideEULAPage><SkipMachineOOBE>true</SkipMachineOOBE><SkipUserOOBE>true</SkipUserOOBE></OOBE>
            <UserAccounts><LocalAccounts><LocalAccount wcm:action="add" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State"><Name>Admin</Name><Group>Administrators</Group></LocalAccount></LocalAccounts></UserAccounts>
            <AutoLogon><Enabled>true</Enabled><Username>Admin</Username></AutoLogon>
        </component>
    </settings>
</unattend>"""
    
    thu_muc_cai_dat = f"{o_dia_luu_wim}:\\ZT_Cloud_Install"
    os.makedirs(thu_muc_cai_dat, exist_ok=True)
    with open(f"{thu_muc_cai_dat}\\unattend.xml", "w", encoding="utf-8") as tep_xml: tep_xml.write(noi_dung_unattend)
    
    ma_nguon_ps = f"""
$ErrorActionPreference = 'SilentlyContinue'
$KiTuHeThong = [System.IO.Path]::GetPathRoot($env:windir).Substring(0,1)
$ThongTinPhanVung = Get-Partition -DriveLetter $KiTuHeThong
$ThuTuODia = $ThongTinPhanVung.DiskNumber
$ThuTuPhanVung = $ThongTinPhanVung.PartitionNumber

$DuongDanWinRE = "C:\\Windows\\System32\\Recovery\\winre.wim"
$ThuMucGiaoTiep = "C:\\MountRE"
$WinRECopy = "C:\\winre_xu_ly.wim"

reagentc.exe /enable; Start-Sleep -Seconds 2; reagentc.exe /disable; Start-Sleep -Seconds 2

if (Test-Path $ThuMucGiaoTiep) {{ dism.exe /Unmount-Image /MountDir:$ThuMucGiaoTiep /Discard; Remove-Item $ThuMucGiaoTiep -Recurse -Force }}
New-Item -ItemType Directory -Force -Path $ThuMucGiaoTiep

Copy-Item $DuongDanWinRE $WinRECopy -Force
Set-ItemProperty $WinRECopy IsReadOnly $false
dism.exe /Mount-Image /ImageFile:$WinRECopy /Index:1 /MountDir:$ThuMucGiaoTiep

$KichBanXoaVaCai = @"
@echo off
for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (if exist "%%D:\\ZT_Cloud_Install\\install.wim" set "WPATH=%%D:\\ZT_Cloud_Install\\install.wim")
(echo select disk $ThuTuODia & echo select partition $ThuTuPhanVung & echo assign letter=W & echo format quick fs=ntfs label="Windows") | diskpart
dism /apply-image /imagefile:"%WPATH%" /index:1 /applydir:W:\\
if exist "%%~dpWPATHDrivers" ( dism /image:W:\\ /Add-Driver /Driver:"%%~dpWPATHDrivers" /Recurse )
bcdboot W:\\Windows

reg load HKLM\\ZT W:\\Windows\\System32\\config\\SYSTEM
reg add "HKLM\\ZT\\Setup\\LabConfig" /v BypassTPMCheck /t REG_DWORD /d 1 /f
reg add "HKLM\\ZT\\Setup\\LabConfig" /v BypassSecureBootCheck /t REG_DWORD /d 1 /f
reg unload HKLM\\ZT

reg load HKLM\\ZTSYSTEM W:\\Windows\\System32\\config\\SYSTEM
reg add "HKLM\\ZTSYSTEM\\ControlSet001\\Control\\ComputerName\\ComputerName" /v ComputerName /t REG_SZ /d {ten_may_chong_trung} /f
reg add "HKLM\\ZTSYSTEM\\ControlSet001\\Control\\ComputerName\\ActiveComputerName" /v ComputerName /t REG_SZ /d {ten_may_chong_trung} /f
reg add "HKLM\\ZTSYSTEM\\ControlSet001\\Services\\Tcpip\\Parameters" /v Hostname /t REG_SZ /d {ten_may_chong_trung} /f
reg add "HKLM\\ZTSYSTEM\\ControlSet001\\Services\\Tcpip\\Parameters" /v "NV Hostname" /t REG_SZ /d {ten_may_chong_trung} /f
reg unload HKLM\\ZTSYSTEM

mkdir W:\\Windows\\Panther
copy /Y "%%~dpWPATHunattend.xml" W:\\Windows\\Panther\\unattend.xml
if exist "%%~dpWPATHSetupComplete.cmd" ( mkdir W:\\Windows\\Setup\\Scripts & copy /Y "%%~dpWPATHSetupComplete.cmd" W:\\Windows\\Setup\\Scripts\\ )
if exist "%%~dpWPATHWiFi" ( mkdir W:\\Windows\\Setup\\Scripts\\WiFi & xcopy /E /Y /I "%%~dpWPATHWiFi" W:\\Windows\\Setup\\Scripts\\WiFi\\ )

wpeutil reboot
"@

    $KichBanXoaVaCai | Out-File "$ThuMucGiaoTiep\\Windows\\System32\\LenhRE.cmd" -Encoding oem
    '[LaunchApps]' + [char]13 + [char]10 + 'X:\\Windows\\System32\\LenhRE.cmd' | Out-File "$ThuMucGiaoTiep\\Windows\\System32\\winpeshl.ini" -Encoding ascii
    
    dism.exe /Unmount-Image /MountDir:$ThuMucGiaoTiep /Commit
    cmd.exe /c "attrib -h -s -r `"$DuongDanWinRE`""
    Copy-Item $WinRECopy $DuongDanWinRE -Force
    Remove-Item $WinRECopy -Force
    reagentc.exe /setreimage /path C:\\Windows\\System32\\Recovery
    reagentc.exe /enable; Start-Sleep -Seconds 2; reagentc.exe /boottore
"""
    
    with open(f"{thu_muc_cai_dat}\\config.ps1", "w", encoding="utf-8") as tep_ps1: tep_ps1.write(ma_nguon_ps)
    ket_qua = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", f"{thu_muc_cai_dat}\\config.ps1"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if ket_qua.returncode != 0: ham_ghi_log(f"Cảnh báo WinRE: {ket_qua.stderr.strip()}")

# ==========================================
# 5. ĐỘNG CƠ TẢI DỮ LIỆU ĐÁM MÂY (CÓ CHUYỂN HƯỚNG TRÌNH DUYỆT)
# ==========================================
def truat_xuat_du_lieu_dam_may(ma_file_tai, duong_dan_luu_tru, ham_cap_nhat_giao_dien, ham_ghi_log, su_kien_huy):
    if not ma_file_tai:
        ham_ghi_log("LỖI: Mã ID trống! Hãy kiểm tra lại cấu trúc file CSV.")
        return False

    for thu_tu, khoa_bao_mat_b64 in enumerate(DANH_SACH_KHOA_API):
        if su_kien_huy.is_set(): return False
        try: khoa_api_giai_ma = base64.b64decode(khoa_bao_mat_b64).decode('utf-8')
        except: continue
            
        duong_dan_truy_xuat = f"https://www.googleapis.com/drive/v3/files/{ma_file_tai}?alt=media&key={khoa_api_giai_ma}&acknowledgeAbuse=true"
        yeu_cau_ket_noi = urllib.request.Request(duong_dan_truy_xuat, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        
        try:
            with urllib.request.urlopen(yeu_cau_ket_noi, timeout=15) as cau_tra_loi:
                tong_kich_thuoc_file = int(cau_tra_loi.getheader('Content-Length', 0))
                with open(duong_dan_luu_tru, 'wb') as tep_tin_nhan:
                    dung_luong_da_tai = 0; thoi_gian_khoi_tao = time.time()
                    while True:
                        if su_kien_huy.is_set(): return False
                        khoi_du_lieu = cau_tra_loi.read(1024 * 1024)
                        if not khoi_du_lieu: break
                        tep_tin_nhan.write(khoi_du_lieu); dung_luong_da_tai += len(khoi_du_lieu)
                        if tong_kich_thuoc_file > 0: 
                            thoi_gian_xu_ly = max(time.time() - thoi_gian_khoi_tao, 0.001)
                            phan_tram = (dung_luong_da_tai / tong_kich_thuoc_file) * 100
                            toc_do_giay = dung_luong_da_tai / thoi_gian_xu_ly
                            ham_cap_nhat_giao_dien(phan_tram, dung_luong_da_tai, tong_kich_thuoc_file, toc_do_giay)
            ham_ghi_log(f"Đang truyền tải tốc độ cao qua Khóa API số {thu_tu + 1}.")
            return "SUCCESS"
            
        except urllib.error.HTTPError as loi_http:
            if loi_http.code == 403: ham_ghi_log(f"Khóa {thu_tu + 1} (403): Bị chặn/Quá tải giới hạn.")
            elif loi_http.code == 404: ham_ghi_log(f"Khóa {thu_tu + 1} (404): Không tìm thấy ID '{ma_file_tai}'.")
            else: ham_ghi_log(f"Khóa {thu_tu + 1} lỗi kết nối HTTP.")
            continue
        except Exception as e: 
            ham_ghi_log(f"Khóa {thu_tu + 1} lỗi mạng: {str(e)}")
            continue

    # KẾ HOẠCH B: ĐÁ LINK RA TRÌNH DUYỆT WEB
    ham_ghi_log("Tất cả API đã kiệt sức. Tiến hành đẩy link ra trình duyệt web...")
    link_tai_web = f"https://drive.google.com/uc?export=download&id={ma_file_tai}"
    
    try:
        webbrowser.open(link_tai_web)
        ham_ghi_log("Đã mở link trên trình duyệt. Vui lòng tải thủ công.")
        return "WEB_REDIRECT"
    except Exception as e:
        ham_ghi_log(f"Không thể mở trình duyệt: {str(e)}")
        return False

# ==========================================
# 6. GIAO DIỆN BẢNG ĐIỀU KHIỂN CHÍNH
# ==========================================
class BangDieuKhienTrungTam(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Trạm Triển Khai Kỹ Thuật - Tự Động Định Danh & Dọn Rác")
        self.geometry("850x720"); self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(2, weight=1)
        self.su_kien_huy_lenh = threading.Event(); self.co_the_hoat_dong = False

        self.khung_phan_dau = ctk.CTkFrame(self, fg_color="transparent"); self.khung_phan_dau.grid(row=0, column=0, pady=15, sticky="ew")
        ctk.CTkLabel(self.khung_phan_dau, text="HỆ THỐNG TRIỂN KHAI MÁY KHÁCH TỪ XA", font=("Arial", 22, "bold")).pack()
        self.nhan_trang_thai_kho = ctk.CTkLabel(self.khung_phan_dau, text="Đang đồng bộ dữ liệu với kho lưu trữ...", text_color="gray"); self.nhan_trang_thai_kho.pack()

        self.khung_thiet_lap = ctk.CTkFrame(self); self.khung_thiet_lap.grid(row=1, column=0, padx=20, pady=5, sticky="ew"); self.khung_thiet_lap.grid_columnconfigure((0, 1, 2), weight=1)
        self.bien_chon_driver = ctk.StringVar(value="Backup LAN & WIFI")
        ctk.CTkOptionMenu(self.khung_thiet_lap, values=["Không Backup Driver", "Backup LAN & WIFI", "Backup Toàn Bộ Driver"], variable=self.bien_chon_driver).grid(row=0, column=0, padx=10, pady=15)
        self.bien_chon_wifi = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(self.khung_thiet_lap, text="Trích xuất WiFi", variable=self.bien_chon_wifi).grid(row=0, column=1, padx=10, pady=15)
        self.bien_an_toan_test = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(self.khung_thiet_lap, text="CHẾ ĐỘ KIỂM THỬ", variable=self.bien_an_toan_test, progress_color="#D97706").grid(row=0, column=2, padx=10, pady=15)

        self.khung_danh_sach_os = ctk.CTkScrollableFrame(self, label_text=" DANH MỤC BẢN CÀI ĐẶT CÓ SẴN "); self.khung_danh_sach_os.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        
        self.hop_chua_nhat_ky = ctk.CTkTextbox(self, height=100, font=("Consolas", 12), fg_color="#0F172A", text_color="#38BDF8"); self.hop_chua_nhat_ky.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        self.hop_chua_nhat_ky.insert("0.0", "Hệ thống lõi đã khởi tạo thành công.\n"); self.hop_chua_nhat_ky.configure(state="disabled")

        self.khung_phan_cuoi = ctk.CTkFrame(self, fg_color="transparent"); self.khung_phan_cuoi.grid(row=4, column=0, padx=20, pady=15, sticky="ew"); self.khung_phan_cuoi.grid_columnconfigure(0, weight=1)
        self.thanh_bar_tien_do = ctk.CTkProgressBar(self.khung_phan_cuoi, height=12); self.thanh_bar_tien_do.grid(row=0, column=0, padx=(0, 20), sticky="ew"); self.thanh_bar_tien_do.set(0)
        self.nhan_chi_so_tai = ctk.CTkLabel(self.khung_phan_cuoi, text="0% | Tốc độ: 0 MB/s", font=("Arial", 12, "bold")); self.nhan_chi_so_tai.grid(row=1, column=0, sticky="w")
        self.nut_huy_bo = ctk.CTkButton(self.khung_phan_cuoi, text="🛑 HỦY TIẾN TRÌNH", fg_color="#BE123C", hover_color="#9F1239", state="disabled", command=self.kich_hoat_lenh_huy); self.nut_huy_bo.grid(row=0, column=1, rowspan=2)

        self.tien_hanh_quet_kho_du_lieu()

    def in_nhat_ky_he_thong(self, dong_thong_diep):
        self.hop_chua_nhat_ky.configure(state="normal"); self.hop_chua_nhat_ky.insert("end", f"[*] {dong_thong_diep}\n"); self.hop_chua_nhat_ky.see("end"); self.hop_chua_nhat_ky.configure(state="disabled"); self.update()

    def tien_hanh_quet_kho_du_lieu(self):
        def luong_xu_ly_mang():
            try:
                yeu_cau_csv = urllib.request.Request(DUONG_DAN_KHO_DU_LIEU, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                phan_hoi_csv = urllib.request.urlopen(yeu_cau_csv)
                du_lieu_chuoi = phan_hoi_csv.read().decode('utf-8-sig').splitlines()
                
                trinh_doc_csv = csv.DictReader(du_lieu_chuoi)
                cac_cot_tieu_de = [c.strip() for c in trinh_doc_csv.fieldnames if c]
                
                khoa_ten_file = next((cot for cot in cac_cot_tieu_de if 'name' in cot.lower() or 'tên' in cot.lower()), None)
                khoa_ma_file = next((cot for cot in cac_cot_tieu_de if 'id' in cot.lower() or 'link' in cot.lower()), None)
                
                if not khoa_ten_file or not khoa_ma_file:
                    self.in_nhat_ky_he_thong(f"Lỗi CSV. Các cột tìm thấy: {cac_cot_tieu_de}")
                    return

                so_luong_file = 0
                for hang_du_lieu in trinh_doc_csv:
                    ten_hien_thi = str(hang_du_lieu.get(khoa_ten_file, '')).strip()
                    chuoi_link_goc = str(hang_du_lieu.get(khoa_ma_file, '')).strip()
                    
                    tim_id = re.search(r'[-\w]{25,}', chuoi_link_goc)
                    ma_dinh_danh = tim_id.group(0) if tim_id else ''
                    
                    if ten_hien_thi and ".wim" in ten_hien_thi.lower() and ma_dinh_danh:
                        self.sinh_nut_cai_dat(ten_hien_thi, ma_dinh_danh)
                        so_luong_file += 1
                        
                self.nhan_trang_thai_kho.configure(text=f"✅ Đã giải mã cấu trúc thành công {so_luong_file} bản cài", text_color="#10B981")
            except Exception as e_loi: 
                self.in_nhat_ky_he_thong(f"Lỗi truy xuất CSV: {str(e_loi)}")
                self.nhan_trang_thai_kho.configure(text="❌ Lỗi phân tích cấu trúc", text_color="#EF4444")
                
        threading.Thread(target=luong_xu_ly_mang, daemon=True).start()

    def sinh_nut_cai_dat(self, nhan_ten_ban_cai, gia_tri_ma_file):
        ctk.CTkButton(self.khung_danh_sach_os, text=f"📥 TẢI VÀ ÁP DỤNG: {nhan_ten_ban_cai}", font=("Arial", 13, "bold"), fg_color="#1E293B", anchor="w", command=lambda: self.khoi_tao_tien_trinh(nhan_ten_ban_cai, gia_tri_ma_file)).pack(fill="x", pady=2, padx=5)

    def kich_hoat_lenh_huy(self): 
        self.su_kien_huy_lenh.set(); self.nut_huy_bo.configure(state="disabled")

    def khoi_tao_tien_trinh(self, nhan_ten_ban_cai, gia_tri_ma_file):
        if self.co_the_hoat_dong: return
        if not self.bien_an_toan_test.get():
            if not messagebox.askyesno("Xác Nhận Nguy Hiểm", "Hành động này sẽ XÓA SẠCH ổ C của máy tính. Chắc chắn tiếp tục?"): return
        self.co_the_hoat_dong = True; self.su_kien_huy_lenh.clear(); self.nut_huy_bo.configure(state="normal")
        threading.Thread(target=self.luong_dieu_phoi_chinh, args=(nhan_ten_ban_cai, gia_tri_ma_file), daemon=True).start()

    def luong_dieu_phoi_chinh(self, nhan_ten_ban_cai, gia_tri_ma_file):
        try:
            toc_do_mang_hien_tai = do_bang_thong_mang(self.in_nhat_ky_he_thong)
            duong_dan_usb_noi_bo = None
            if toc_do_mang_hien_tai < 1.5:
                if messagebox.askyesno("Báo Cáo Đường Truyền", f"Tốc độ mạng chậm (~{toc_do_mang_hien_tai:.1f}MB/s). Chọn wim từ ổ cứng/USB?"):
                    duong_dan_usb_noi_bo = filedialog.askopenfilename(filetypes=[("Tập tin Windows Image", "*.wim")])

            go_bo_bitlocker(self.in_nhat_ky_he_thong)
            o_dia_an_toan = tim_o_dia_luu_tru_an_toan(); thu_muc_chua_anh_wim = f"{o_dia_an_toan}:\\ZT_Cloud_Install"; os.makedirs(thu_muc_chua_anh_wim, exist_ok=True); vi_tri_luu_file_wim = os.path.join(thu_muc_chua_anh_wim, "install.wim")
            sao_luu_du_lieu_he_thong(thu_muc_chua_anh_wim, self.bien_chon_driver.get(), self.bien_chon_wifi.get(), self.in_nhat_ky_he_thong)

            if duong_dan_usb_noi_bo:
                self.in_nhat_ky_he_thong("Đang sao chép tập tin WIM cục bộ..."); shutil.copy2(duong_dan_usb_noi_bo, vi_tri_luu_file_wim)
            else:
                self.in_nhat_ky_he_thong(f"Mở luồng tải dữ liệu đám mây: {nhan_ten_ban_cai}...")
                ket_qua_tai = truat_xuat_du_lieu_dam_may(gia_tri_ma_file, vi_tri_luu_file_wim, self.lam_moi_giao_dien_tai, self.in_nhat_ky_he_thong, self.su_kien_huy_lenh)
                
                # NẾU TRẢ VỀ LÀ WEB_REDIRECT THÌ THÔNG BÁO VÀ DỪNG LẠI
                if ket_qua_tai == "WEB_REDIRECT":
                    # Xóa file rác 0KB do Python vừa tạo ra
                    try: os.remove(vi_tri_luu_file_wim)
                    except: pass
                    messagebox.showinfo("Chuyển Hướng Trình Duyệt", "Các máy chủ API hiện đang quá tải.\n\nHệ thống đã mở link tải trực tiếp trên trình duyệt Web của bạn.\n\nSAU KHI TẢI XONG FILE, hãy mở lại Tool và chọn tính năng [Tải file wim từ ổ cứng/USB] để tiếp tục.")
                    return self.khoi_phuc_trang_thai_goc("Đang chờ người dùng tải file thủ công...")
                elif not ket_qua_tai: 
                    return self.khoi_phuc_trang_thai_goc("Tiến trình tải dữ liệu bị hủy do lỗi mạng hoặc file lỗi.")

            if self.bien_an_toan_test.get():
                messagebox.showinfo("Báo Cáo", f"Đã lưu file an toàn tại: {vi_tri_luu_file_wim}\nChế độ Test: Máy không bị Format."); return self.khoi_phuc_trang_thai_goc("Kiểm thử xong.")

            self.in_nhat_ky_he_thong("Đang chèn kịch bản can thiệp vào nhân WinRE...")
            tiem_kich_ban_winre(o_dia_an_toan, self.in_nhat_ky_he_thong)
            messagebox.showinfo("Hoàn Tất Chuẩn Bị", "Kịch bản Zero-Touch đã nạp. Máy sẽ khởi động lại ngay lập tức."); os.system("shutdown /r /t 0")
        except Exception as loi_nghiem_trong:
            messagebox.showerror("Ngoại Lệ Trầm Trọng", str(loi_nghiem_trong)); self.khoi_phuc_trang_thai_goc(f"Thất bại: {loi_nghiem_trong}")

    def khoi_phuc_trang_thai_goc(self, thong_diep_cuoi="Chu kỳ thao tác đã đóng."):
        self.co_the_hoat_dong = False; self.nut_huy_bo.configure(state="disabled"); self.in_nhat_ky_he_thong(thong_diep_cuoi)

    def lam_moi_giao_dien_tai(self, gia_tri_phan_tram, dung_luong_da_tai, tong_dung_luong_file, toc_do_tren_giay):
        self.thanh_bar_tien_do.set(gia_tri_phan_tram / 100); self.nhan_chi_so_tai.configure(text=f"{int(gia_tri_phan_tram)}% | {(toc_do_tren_giay / (1024 * 1024)):.1f} MB/s | {(dung_luong_da_tai / 1024**3):.1f} GB"); self.update()

if __name__ == "__main__":
    ung_dung_ky_thuat = BangDieuKhienTrungTam(); ung_dung_ky_thuat.mainloop()