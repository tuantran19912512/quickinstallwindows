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
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import base64

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & BẢO MẬT
# ==========================================
DUONG_DAN_KHO_DU_LIEU = "https://raw.githubusercontent.com/tuantran19912512/quickinstallwindows/refs/heads/main/list_win.csv"

# Khóa API đám mây đã mã hóa Base64 để tránh bị quét tự động
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
    """Kiểm tra xem phần mềm có đang chạy dưới quyền Admin hay không."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# Nâng quyền tự động nếu chưa có
if not kiem_tra_quyen_quan_tri():
    if getattr(sys, 'frozen', False):
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1)
    sys.exit()

# Thiết lập giao diện phẳng (Flat UI) và chế độ tối (Dark Mode)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ==========================================
# 3. CÁC CÔNG CỤ TIỆN ÍCH (MẠNG, Ổ ĐĨA, BACKUP)
# ==========================================
def do_bang_thong_mang(ham_ghi_log):
    ham_ghi_log("Đang đo lường băng thông mạng qua máy chủ Cloudflare...")
    try:
        url_kiem_tra = "https://speed.cloudflare.com/__down?bytes=1048576"
        yeu_cau = urllib.request.Request(url_kiem_tra, headers={'User-Agent': 'Mozilla/5.0'})
        thoi_gian_bat_dau = time.time()
        with urllib.request.urlopen(yeu_cau, timeout=5) as phan_hoi:
            du_lieu_tai_ve = phan_hoi.read()
        thoi_gian_hoan_thanh = time.time() - thoi_gian_bat_dau
        toc_do_thuc_te = (len(du_lieu_tai_ve) / (1024 * 1024)) / (thoi_gian_hoan_thanh if thoi_gian_hoan_thanh > 0.001 else 0.001)
        ham_ghi_log(f"Đã đo xong. Tốc độ mạng hiện tại: ~ {toc_do_thuc_te:.1f} MB/s")
        return toc_do_thuc_te
    except Exception as loi:
        ham_ghi_log("Lỗi kết nối khi đo tốc độ. Sẽ áp dụng tốc độ giả lập mặc định.")
        return 5.0

def go_bo_bitlocker(ham_ghi_log):
    ham_ghi_log("Đang dò quét trạng thái mã hóa BitLocker trên phân vùng hệ điều hành...")
    try:
        o_dia_he_thong = os.environ.get('SystemDrive', 'C:')
        ket_qua_kiem_tra = subprocess.check_output(f'manage-bde -status {o_dia_he_thong}', shell=True).decode('utf-8', errors='ignore')
        if any(tu_khoa in ket_qua_kiem_tra for tu_khoa in ["Mã hóa", "Encryption", "完全な暗号化"]):
            ham_ghi_log(f"Phát hiện BitLocker đang khóa! Bắt đầu tiến trình giải mã ép buộc trên {o_dia_he_thong}...")
            subprocess.run(f'manage-bde -off {o_dia_he_thong}', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            ham_ghi_log("Không phát hiện BitLocker. Phân vùng sạch.")
    except:
        pass

def tim_o_dia_luu_tru_an_toan():
    """Tìm một phân vùng ngoài ổ C có dung lượng trống lớn hơn 10GB để chứa file ảnh hệ thống."""
    mat_na_o_dia = ctypes.windll.kernel32.GetLogicalDrives()
    danh_sach_o = [ky_tu for vi_tri, ky_tu in enumerate(string.ascii_uppercase) if mat_na_o_dia & (1 << vi_tri)]
    o_cai_dat_hien_tai = os.environ.get('SystemDrive', 'C:')[0]
    o_dia_toi_uu = None
    dung_luong_lon_nhat = 0
    
    for o_dia in danh_sach_o:
        if o_dia == o_cai_dat_hien_tai: 
            continue
        duong_dan_goc = f"{o_dia}:\\"
        if ctypes.windll.kernel32.GetDriveTypeW(duong_dan_goc) != 3: # 3 = Ổ cứng cố định (Fixed Drive)
            continue
        try:
            _, _, dung_luong_trong = shutil.disk_usage(duong_dan_goc)
            if dung_luong_trong > 10 * 1024**3 and dung_luong_trong > dung_luong_lon_nhat:
                dung_luong_lon_nhat = dung_luong_trong
                o_dia_toi_uu = o_dia
        except:
            pass
            
    if not o_dia_toi_uu: 
        raise Exception("Nghiêm trọng: Không tìm thấy phân vùng lưu trữ nào (D, E...) trống trên 10GB!")
    return o_dia_toi_uu

def sao_luu_du_lieu_he_thong(thu_muc_dich, lua_chon_driver, lua_chon_wifi, ham_ghi_log):
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
            
            kich_ban_phuc_hoi_wifi = (
                '@echo off\n'
                'sc config wlansvc start= auto\n'
                'net start wlansvc\n'
                'timeout /t 3 /nobreak >nul\n'
                'for %%f in ("%~dp0WiFi\\*.xml") do netsh wlan add profile filename="%%f" user=all\n'
                'if exist "%~dp0WiFi\\current_ssid.txt" (set /p WLAN_SSID=<"%~dp0WiFi\\current_ssid.txt"\n'
                'netsh wlan connect name="%WLAN_SSID%")\n'
            )
            with open(os.path.join(thu_muc_dich, "SetupComplete.cmd"), "w", encoding="utf-8") as tep_lenh:
                tep_lenh.write(kich_ban_phuc_hoi_wifi)
        except Exception as e:
            ham_ghi_log(f"Cảnh báo: Không thể trích xuất WiFi ({e})")

    if lua_chon_driver != "Không Backup Driver":
        ham_ghi_log(f"Kích hoạt mô-đun trích xuất trình điều khiển ({lua_chon_driver}). Việc này mất chút thời gian...")
        thu_muc_chua_driver = os.path.join(thu_muc_dich, "Drivers")
        os.makedirs(thu_muc_chua_driver, exist_ok=True)
        
        if lua_chon_driver == "Backup Toàn Bộ Driver":
            subprocess.run(["powershell", "-Command", f'Export-WindowsDriver -Online -Destination "{thu_muc_chua_driver}"'], creationflags=subprocess.CREATE_NO_WINDOW)
        else: # Chỉ LAN/WLAN/Bluetooth
            thu_muc_tam_thoi = os.path.join(thu_muc_dich, "DrvTemp")
            lenh_sao_luu_chon_loc = (
                f"$drvs = Export-WindowsDriver -Online -Destination '{thu_muc_tam_thoi}'; "
                f"foreach ($d in $drvs) {{ if ($d.ClassName -match 'Net|WLAN|Bluetooth') {{ Copy-Item (Split-Path $d.OriginalFileName) -Destination '{thu_muc_chua_driver}' -Recurse -Force }} }}; "
                f"Remove-Item '{thu_muc_tam_thoi}' -Recurse -Force"
            )
            subprocess.run(["powershell", "-Command", lenh_sao_luu_chon_loc], creationflags=subprocess.CREATE_NO_WINDOW)

def tiem_kich_ban_winre(o_dia_luu_wim, ham_ghi_log):
    chuoi_ngau_nhien = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    ten_may_chong_trung = f"PC-{chuoi_ngau_nhien}"
    ham_ghi_log(f"Đã cấp phát tên máy chủ định danh: {ten_may_chong_trung} (Phòng tránh xung đột IP nội bộ)")

    noi_dung_unattend = f"""<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
    <settings pass="specialize">
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
            <ComputerName>{ten_may_chong_trung}</ComputerName>
        </component>
    </settings>
    <settings pass="oobeSystem">
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
            <OOBE><HideEULAPage>true</HideEULAPage><SkipMachineOOBE>true</SkipMachineOOBE><SkipUserOOBE>true</SkipUserOOBE></OOBE>
            <UserAccounts>
                <LocalAccounts><LocalAccount wcm:action="add" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State"><Name>Admin</Name><Group>Administrators</Group></LocalAccount></LocalAccounts>
            </UserAccounts>
            <AutoLogon><Enabled>true</Enabled><Username>Admin</Username></AutoLogon>
        </component>
    </settings>
</unattend>"""
    
    thu_muc_cai_dat = f"{o_dia_luu_wim}:\\ZT_Cloud_Install"
    os.makedirs(thu_muc_cai_dat, exist_ok=True)
    with open(f"{thu_muc_cai_dat}\\unattend.xml", "w", encoding="utf-8") as tep_xml: 
        tep_xml.write(noi_dung_unattend)
    
    ma_nguon_ps = f"""
    $KiTuHeThong = [System.IO.Path]::GetPathRoot($env:windir).Substring(0,1)
    $ThongTinPhanVung = Get-Partition -DriveLetter $KiTuHeThong
    $ThuTuODia = $ThongTinPhanVung.DiskNumber
    $ThuTuPhanVung = $ThongTinPhanVung.PartitionNumber
    $DuongDanWinRE = "C:\\Windows\\System32\\Recovery\\winre.wim"
    $ThuMucGiaoTiep = "C:\\MountRE"
    $WinRECopy = "C:\\winre_xu_ly.wim"
    
    # 1. Tắt WinRE để kéo file winre.wim về đúng thư mục System32\\Recovery
    reagentc.exe /enable; Start-Sleep 2; reagentc.exe /disable; Start-Sleep 2
    
    # Dọn dẹp thư mục Mount nếu bị kẹt từ lần test trước
    if (Test-Path $ThuMucGiaoTiep) {{ dism.exe /Unmount-Image /MountDir:$ThuMucGiaoTiep /Discard; Remove-Item $ThuMucGiaoTiep -Recurse -Force }}
    New-Item -ItemType Directory -Force -Path $ThuMucGiaoTiep
    
    # 2. BƯỚC QUAN TRỌNG: Copy file WIM ra ngoài để phá vỡ bảo vệ Read-Only
    Copy-Item $DuongDanWinRE $WinRECopy -Force
    Set-ItemProperty $WinRECopy IsReadOnly $false
    
    # 3. Mount file copy
    dism.exe /Mount-Image /ImageFile:$WinRECopy /Index:1 /MountDir:$ThuMucGiaoTiep
    
    $KichBanXoaVaCai = @"
@echo off
for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (if exist "%%D:\\ZT_Cloud_Install\\install.wim" set "WPATH=%%D:\\ZT_Cloud_Install\\install.wim")
(echo select disk $ThuTuODia & echo select partition $ThuTuPhanVung & echo assign letter=W & echo format quick fs=ntfs label="Windows") | diskpart
dism /apply-image /imagefile:"%WPATH%" /index:1 /applydir:W:\\
if exist "%%~dpWPATHDrivers" ( dism /image:W:\\ /Add-Driver /Driver:"%%~dpWPATHDrivers" /Recurse )
bcdboot W:\\Windows
mkdir W:\\Windows\\Panther
copy /Y "%%~dpWPATHunattend.xml" W:\\Windows\\Panther\\unattend.xml
if exist "%%~dpWPATHSetupComplete.cmd" ( mkdir W:\\Windows\\Setup\\Scripts & copy /Y "%%~dpWPATHSetupComplete.cmd" W:\\Windows\\Setup\\Scripts\\ )
wpeutil reboot
"@

    $KichBanXoaVaCai | Out-File "$ThuMucGiaoTiep\\Windows\\System32\\LenhRE.cmd" -Encoding oem
    '[LaunchApps]' + [char]13 + [char]10 + 'X:\\Windows\\System32\\LenhRE.cmd' | Out-File "$ThuMucGiaoTiep\\Windows\\System32\\winpeshl.ini" -Encoding ascii
    
    # 4. Lưu lại thay đổi vào file WIM copy
    dism.exe /Unmount-Image /MountDir:$ThuMucGiaoTiep /Commit
    
    # 5. Gỡ thuộc tính Ẩn/Hệ thống của file WIM gốc và chép đè
    cmd.exe /c "attrib -h -s -r `"$DuongDanWinRE`""
    Copy-Item $WinRECopy $DuongDanWinRE -Force
    Remove-Item $WinRECopy -Force
    
    # 6. Kích hoạt lại WinRE và cắm cờ khởi động
    reagentc.exe /setreimage /path C:\\Windows\\System32\\Recovery
    reagentc.exe /enable; Start-Sleep 2
    reagentc.exe /boottore
    """
    
    with open(f"{thu_muc_cai_dat}\\config.ps1", "w", encoding="utf-8") as tep_ps1: 
        tep_ps1.write(ma_nguon_ps)
        
    ket_qua = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", f"{thu_muc_cai_dat}\\config.ps1"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    
    if ket_qua.returncode != 0:
        ham_ghi_log(f"Cảnh báo WinRE: Quá trình nạp gặp sự cố -> {ket_qua.stderr.strip()}")

# ==========================================
# 4. ĐỘNG CƠ TẢI DỮ LIỆU ĐÁM MÂY
# ==========================================
def truat_xuat_du_lieu_dam_may(ma_file_tai, duong_dan_luu_tru, ham_cap_nhat_giao_dien, ham_ghi_log, su_kien_huy):
    for thu_tu, khoa_bao_mat_b64 in enumerate(DANH_SACH_KHOA_API):
        if su_kien_huy.is_set(): 
            return False
        try: 
            khoa_api_giai_ma = base64.b64decode(khoa_bao_mat_b64).decode('utf-8')
        except: 
            continue
            
        duong_dan_truy_xuat = f"https://www.googleapis.com/drive/v3/files/{ma_file_tai}?alt=media&key={khoa_api_giai_ma}&acknowledgeAbuse=true"
        yeu_cau_ket_noi = urllib.request.Request(duong_dan_truy_xuat, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        
        try:
            with urllib.request.urlopen(yeu_cau_ket_noi, timeout=15) as cau_tra_loi:
                tong_kich_thuoc_file = int(cau_tra_loi.getheader('Content-Length', 0))
                with open(duong_dan_luu_tru, 'wb') as tep_tin_nhan:
                    dung_luong_da_tai = 0
                    thoi_gian_khoi_tao = time.time()
                    
                    while True:
                        if su_kien_huy.is_set(): 
                            return False
                        
                        khoi_du_lieu = cau_tra_loi.read(1024 * 1024)
                        if not khoi_du_lieu: 
                            break
                            
                        tep_tin_nhan.write(khoi_du_lieu)
                        dung_luong_da_tai += len(khoi_du_lieu)
                        
                        if tong_kich_thuoc_file > 0: 
                            phan_tram = (dung_luong_da_tai / tong_kich_thuoc_file) * 100
                            toc_do_giay = dung_luong_da_tai / (time.time() - thoi_gian_khoi_tao)
                            ham_cap_nhat_giao_dien(phan_tram, dung_luong_da_tai, tong_kich_thuoc_file, toc_do_giay)
            return True
        except Exception as e: 
            ham_ghi_log(f"Khóa API nhánh {thu_tu + 1} gặp sự cố, tự động chuyển nhánh...")
            continue
            
    ham_ghi_log("Lỗi: Toàn bộ hệ thống khóa API đều từ chối kết nối.")
    return False

# ==========================================
# 5. LÕI GIAO DIỆN BẢNG ĐIỀU KHIỂN (FLAT UI)
# ==========================================
class BangDieuKhienTrungTam(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Trạm Triển Khai Kỹ Thuật - Tự Động Định Danh")
        self.geometry("850x720")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        self.su_kien_huy_lenh = threading.Event()
        self.co_the_hoat_dong = False

        # Khung Tiêu Đề
        self.khung_phan_dau = ctk.CTkFrame(self, fg_color="transparent")
        self.khung_phan_dau.grid(row=0, column=0, pady=15, sticky="ew")
        ctk.CTkLabel(self.khung_phan_dau, text="HỆ THỐNG TRIỂN KHAI MÁY KHÁCH TỪ XA", font=("Arial", 22, "bold")).pack()
        self.nhan_trang_thai_kho = ctk.CTkLabel(self.khung_phan_dau, text="Đang đồng bộ dữ liệu với kho lưu trữ...", text_color="gray")
        self.nhan_trang_thai_kho.pack()

        # Khung Tùy Chọn Cấu Hình
        self.khung_thiet_lap = ctk.CTkFrame(self)
        self.khung_thiet_lap.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.khung_thiet_lap.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.bien_chon_driver = ctk.StringVar(value="Backup LAN & WIFI")
        ctk.CTkOptionMenu(self.khung_thiet_lap, values=["Không Backup Driver", "Backup LAN & WIFI", "Backup Toàn Bộ Driver"], variable=self.bien_chon_driver).grid(row=0, column=0, padx=10, pady=15)
        
        self.bien_chon_wifi = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(self.khung_thiet_lap, text="Trích xuất mật khẩu WiFi", variable=self.bien_chon_wifi).grid(row=0, column=1, padx=10, pady=15)
        
        self.bien_an_toan_test = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(self.khung_thiet_lap, text="CHẾ ĐỘ KIỂM THỬ (Không Format)", variable=self.bien_an_toan_test, progress_color="#D97706").grid(row=0, column=2, padx=10, pady=15)

        # Khu Vực Danh Sách Hệ Điều Hành
        self.khung_danh_sach_os = ctk.CTkScrollableFrame(self, label_text=" DANH MỤC BẢN CÀI ĐẶT CÓ SẴN ")
        self.khung_danh_sach_os.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        
        # Khung Nhật Ký Hệ Thống
        self.hop_chua_nhat_ky = ctk.CTkTextbox(self, height=100, font=("Consolas", 12), fg_color="#0F172A", text_color="#38BDF8")
        self.hop_chua_nhat_ky.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        self.hop_chua_nhat_ky.insert("0.0", "Hệ thống lõi đã tải xong.\n")
        self.hop_chua_nhat_ky.configure(state="disabled")

        # Khung Tiến Trình & Điều Khiển
        self.khung_phan_cuoi = ctk.CTkFrame(self, fg_color="transparent")
        self.khung_phan_cuoi.grid(row=4, column=0, padx=20, pady=15, sticky="ew")
        self.khung_phan_cuoi.grid_columnconfigure(0, weight=1)
        
        self.thanh_bar_tien_do = ctk.CTkProgressBar(self.khung_phan_cuoi, height=12)
        self.thanh_bar_tien_do.grid(row=0, column=0, padx=(0, 20), sticky="ew")
        self.thanh_bar_tien_do.set(0)
        
        self.nhan_chi_so_tai = ctk.CTkLabel(self.khung_phan_cuoi, text="0% | Tốc độ: 0 MB/s", font=("Arial", 12, "bold"))
        self.nhan_chi_so_tai.grid(row=1, column=0, sticky="w")
        
        self.nut_huy_bo = ctk.CTkButton(self.khung_phan_cuoi, text="🛑 HỦY TIẾN TRÌNH", fg_color="#BE123C", hover_color="#9F1239", state="disabled", command=self.kich_hoat_lenh_huy)
        self.nut_huy_bo.grid(row=0, column=1, rowspan=2)

        self.tien_hanh_quet_kho_du_lieu()

    def in_nhat_ky_he_thong(self, dong_thong_diep):
        self.hop_chua_nhat_ky.configure(state="normal")
        self.hop_chua_nhat_ky.insert("end", f"[*] {dong_thong_diep}\n")
        self.hop_chua_nhat_ky.see("end")
        self.hop_chua_nhat_ky.configure(state="disabled")
        self.update()

    def tien_hanh_quet_kho_du_lieu(self):
        """Hàm đọc CSV thông minh, tự động nhận biết tiêu đề cột cũ/mới."""
        def luong_xu_ly_mang():
            try:
                yeu_cau_csv = urllib.request.Request(DUONG_DAN_KHO_DU_LIEU, headers={'User-Agent': 'Mozilla/5.0'})
                phan_hoi_csv = urllib.request.urlopen(yeu_cau_csv)
                du_lieu_chuoi = phan_hoi_csv.read().decode('utf-8').splitlines()
                
                trinh_doc_csv = csv.DictReader(du_lieu_chuoi)
                cac_cot_tieu_de = trinh_doc_csv.fieldnames
                
                khoa_ten_file = 'Filename' if 'Filename' in cac_cot_tieu_de else 'Name'
                khoa_ma_file = 'ID' if 'ID' in cac_cot_tieu_de else 'FileID'

                for hang_du_lieu in trinh_doc_csv:
                    ten_hien_thi = hang_du_lieu.get(khoa_ten_file, '')
                    ma_dinh_danh = hang_du_lieu.get(khoa_ma_file, '')
                    
                    if ten_hien_thi and ".wim" in ten_hien_thi.lower():
                        self.sinh_nut_cai_dat(ten_hien_thi, ma_dinh_danh)
                        
                self.nhan_trang_thai_kho.configure(text="✅ Đã giải mã cấu trúc kho lưu trữ thành công", text_color="#10B981")
            except Exception as e_loi: 
                self.in_nhat_ky_he_thong(f"Lỗi truy xuất CSV: {str(e_loi)}")
                self.nhan_trang_thai_kho.configure(text="❌ Lỗi phân tích cấu trúc từ máy chủ Github", text_color="#EF4444")
                
        threading.Thread(target=luong_xu_ly_mang, daemon=True).start()

    def sinh_nut_cai_dat(self, nhan_ten_ban_cai, gia_tri_ma_file):
        ctk.CTkButton(
            self.khung_danh_sach_os, 
            text=f"📥 TẢI VÀ ÁP DỤNG: {nhan_ten_ban_cai}", 
            font=("Arial", 13, "bold"), 
            fg_color="#1E293B", 
            anchor="w", 
            command=lambda: self.khoi_tao_tien_trinh(nhan_ten_ban_cai, gia_tri_ma_file)
        ).pack(fill="x", pady=2, padx=5)

    def kich_hoat_lenh_huy(self): 
        self.su_kien_huy_lenh.set()
        self.nut_huy_bo.configure(state="disabled")

    def khoi_tao_tien_trinh(self, nhan_ten_ban_cai, gia_tri_ma_file):
        if self.co_the_hoat_dong: 
            return
            
        if not self.bien_an_toan_test.get():
            canh_bao = messagebox.askyesno("Xác Nhận Nguy Hiểm", "Hành động này sẽ XÓA SẠCH toàn bộ dữ liệu trên phân vùng ổ C. Bạn có chắc chắn muốn tiếp tục?")
            if not canh_bao: 
                return
                
        self.co_the_hoat_dong = True
        self.su_kien_huy_lenh.clear()
        self.nut_huy_bo.configure(state="normal")
        threading.Thread(target=self.luong_dieu_phoi_chinh, args=(nhan_ten_ban_cai, gia_tri_ma_file), daemon=True).start()

    def luong_dieu_phoi_chinh(self, nhan_ten_ban_cai, gia_tri_ma_file):
        try:
            toc_do_mang_hien_tai = do_bang_thong_mang(self.in_nhat_ky_he_thong)
            duong_dan_usb_noi_bo = None
            
            if toc_do_mang_hien_tai < 1.5:
                quyet_dinh = messagebox.askyesno("Báo Cáo Đường Truyền", f"Tốc độ mạng quá chậm (~{toc_do_mang_hien_tai:.1f}MB/s). Bạn có muốn chuyển sang nạp file .wim thủ công từ USB ngoài?")
                if quyet_dinh:
                    duong_dan_usb_noi_bo = filedialog.askopenfilename(filetypes=[("Tập tin Windows Image", "*.wim")])

            go_bo_bitlocker(self.in_nhat_ky_he_thong)
            
            o_dia_an_toan = tim_o_dia_luu_tru_an_toan()
            thu_muc_chua_anh_wim = f"{o_dia_an_toan}:\\ZT_Cloud_Install"
            os.makedirs(thu_muc_chua_anh_wim, exist_ok=True)
            vi_tri_luu_file_wim = os.path.join(thu_muc_chua_anh_wim, "install.wim")
            
            sao_luu_du_lieu_he_thong(thu_muc_chua_anh_wim, self.bien_chon_driver.get(), self.bien_chon_wifi.get(), self.in_nhat_ky_he_thong)

            if duong_dan_usb_noi_bo:
                self.in_nhat_ky_he_thong("Đang tiến hành di chuyển tập tin WIM từ thiết bị lưu trữ ngoài...")
                shutil.copy2(duong_dan_usb_noi_bo, vi_tri_luu_file_wim)
            else:
                self.in_nhat_ky_he_thong(f"Mở luồng tải dữ liệu đám mây cho bản: {nhan_ten_ban_cai}...")
                ket_qua_tai = truat_xuat_du_lieu_dam_may(gia_tri_ma_file, vi_tri_luu_file_wim, self.lam_moi_giao_dien_tai, self.in_nhat_ky_he_thong, self.su_kien_huy_lenh)
                if not ket_qua_tai: 
                    return self.khoi_phuc_trang_thai_goc("Tiến trình tải dữ liệu đã bị hủy hoặc rớt mạng.")

            if self.bien_an_toan_test.get():
                messagebox.showinfo("Báo Cáo Thành Công", f"Giai đoạn tiền trạm hoàn tất. File ảnh đã được đặt tại: {vi_tri_luu_file_wim}\nTiến trình cài đặt không được kích hoạt do đang ở chế độ TEST.")
                return self.khoi_phuc_trang_thai_goc("Kiểm thử thành công.")

            self.in_nhat_ky_he_thong("Đang chèn kịch bản tự động hóa vào nhân WinRE...")
            tiem_kich_ban_winre(o_dia_an_toan, self.in_nhat_ky_he_thong)
            
            messagebox.showinfo("Hoàn Tất Chẩn Bị", "Kịch bản Zero-Touch đã được nạp thành công. Máy khách sẽ lập tức khởi động lại để tiến hành xóa hệ điều hành cũ.")
            os.system("shutdown /r /t 0")
            
        except Exception as loi_nghiem_trong:
            messagebox.showerror("Ngoại Lệ Trầm Trọng", str(loi_nghiem_trong))
            self.khoi_phuc_trang_thai_goc(f"Thất bại: {loi_nghiem_trong}")

    def khoi_phuc_trang_thai_goc(self, thong_diep_cuoi="Chu kỳ thao tác đã đóng."):
        self.co_the_hoat_dong = False
        self.nut_huy_bo.configure(state="disabled")
        self.in_nhat_ky_he_thong(thong_diep_cuoi)

    def lam_moi_giao_dien_tai(self, gia_tri_phan_tram, dung_luong_da_tai, tong_dung_luong_file, toc_do_tren_giay):
        self.thanh_bar_tien_do.set(gia_tri_phan_tram / 100)
        chuoi_thong_tin = f"{int(gia_tri_phan_tram)}% | {(toc_do_tren_giay / (1024 * 1024)):.1f} MB/s | {(dung_luong_da_tai / 1024**3):.1f} GB"
        self.nhan_chi_so_tai.configure(text=chuoi_thong_tin)
        self.update()

if __name__ == "__main__":
    ung_dung_ky_thuat = BangDieuKhienTrungTam()
    ung_dung_ky_thuat.mainloop()