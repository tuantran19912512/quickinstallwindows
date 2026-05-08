import os
import sys
import time
import ctypes
import string
import shutil
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import re
import csv
import threading
import subprocess
import traceback
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import base64
from tkinter import filedialog

# ==========================================
# 1. CẤU HÌNH ĐƯỜNG DẪN DỮ LIỆU
# ==========================================
CSV_URL = "https://raw.githubusercontent.com/tuantran19912512/Windows-tool-box/refs/heads/main/iso_list.csv"

API_KEYS_B64 = [
    "QUl6YVN5Q3VKUkJaTDZnUU8tdVZOMWVvdHhmMlppTXNtYy1sandR",
    "QUl6YVN5QlRhVmRQdmlLaUJyR0JUVk0tUlRiVW51QUdFUzRWck1v",
    "QUl6YVN5QkI0NENOamtHRkdQSjhBaVZaMURxZFJnc3M5MDc4QThv",
    "QUl6YVN5Q2IzaE1LUVNOamt2bFNKbUlhTGtYcVNybFpWaFNSTThR",
    "QUl6YVN5Q2V0SVlWVzRsQmlULTd3TzdNQUJoWlNVQ0dKR1puQTM0"
]

# ==========================================
# 2. KIỂM TRA QUYỀN HỆ THỐNG
# ==========================================
def la_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if not la_admin():
    if getattr(sys, 'frozen', False):
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1)
    sys.exit()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ==========================================
# 3. TIỆN ÍCH HỆ THỐNG & BITLOCKER
# ==========================================
def kiem_tra_toc_do_mang(cb_log):
    """Đo lường độ ổn định và tốc độ mạng thực tế (MB/s) bằng Cloudflare CDN"""
    cb_log("Đang kiểm tra đo lường băng thông mạng (Mất khoảng 1-2 giây)...")
    try:
        # Dùng endpoint test speed chính thức của Cloudflare 
        # Tham số bytes=1048576 yêu cầu server trả về chính xác 1MB dữ liệu
        test_url = "https://speed.cloudflare.com/__down?bytes=1048576"
        req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
        
        start_time = time.time()
        # Đặt timeout 5 giây. Nếu quá 5 giây không tải nổi 1MB thì đích thị là mạng quá yếu
        with urllib.request.urlopen(req, timeout=5) as res:
            data = res.read() 
            
        thoi_gian = time.time() - start_time
        
        # Đề phòng mạng tải quá nhanh, thời gian ~ 0 dẫn đến lỗi chia cho 0
        if thoi_gian <= 0.001: 
            thoi_gian = 0.001 
            
        # Tính toán tốc độ thực tế
        dung_luong_mb = len(data) / (1024 * 1024)
        toc_do_mb_s = dung_luong_mb / thoi_gian
        
        cb_log(f"Kiểm tra hoàn tất: Tốc độ mạng hiện tại ~ {toc_do_mb_s:.1f} MB/s")
        return toc_do_mb_s
        
    except urllib.error.URLError as e:
        cb_log(f"LỖI MẠNG: Không thể kết nối tới máy chủ kiểm tra ({str(e)})")
        return 0.0
    except Exception as e:
        # Nếu lỗi phát sinh không rõ nguyên nhân (tường lửa gắt gao), 
        # ta có thể trả về một mức an toàn (ví dụ 10.0) để nó không chặn app, 
        # nhưng ở đây trả về 0.0 để nó vẫn hiện bảng thông báo cho chắc ăn.
        cb_log(f"Lỗi hệ thống khi đo mạng: {str(e)}")
        return 0.0
        
def tat_bitlocker_he_thong(cb_log):
    """Kiểm tra và tắt BitLocker trên ổ hệ điều hành"""
    cb_log("Đang kiểm tra trạng thái BitLocker...")
    try:
        # Lấy ký tự ổ cài Win (thường là C:)
        sys_drive = os.environ.get('SystemDrive', 'C:')
        cmd = f'manage-bde -status {sys_drive}'
        res = subprocess.check_output(cmd, shell=True).decode('utf-8', errors='ignore')
        
        if "Mã hóa hoàn toàn" in res or "Đang mã hóa" in res or "Encryption in Progress" in res:
            cb_log(f"Phát hiện BitLocker đang bật trên {sys_drive}. Tiến hành giải mã...")
            subprocess.run(f'manage-bde -off {sys_drive}', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            cb_log("Đã gửi lệnh tắt BitLocker. Quy trình sẽ tiếp tục chạy ngầm.")
        else:
            cb_log("BitLocker đã tắt hoặc không tồn tại. An toàn.")
    except:
        cb_log("Không thể kiểm tra BitLocker. Sẽ tiếp tục xử lý cưỡng chế trong WinRE.")

def tim_o_dia_an_toan():
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    drives = [char for i, char in enumerate(string.ascii_uppercase) if bitmask & (1 << i)]
    os_drive = os.environ.get('SystemDrive', 'C:')[0]
    best_drive = None; max_free = 0
    for d in drives:
        if d == os_drive: continue
        path = f"{d}:\\"
        if ctypes.windll.kernel32.GetDriveTypeW(path) != 3: continue
        try:
            _, _, free = shutil.disk_usage(path)
            if free > 10 * 1024**3 and free > max_free:
                max_free = free; best_drive = d
        except: pass
    if not best_drive: raise Exception("Không tìm thấy phân vùng D/E nào trống trên 10GB!")
    return best_drive

def thuc_hien_backup(base_dir, driver_mode, wifi_mode, cb_log):
    if wifi_mode:
        cb_log("Đang sao lưu thông tin WiFi và mật khẩu...")
        wifi_dir = os.path.join(base_dir, "WiFi")
        os.makedirs(wifi_dir, exist_ok=True)
        try:
            res = subprocess.check_output('netsh wlan show interfaces', shell=True).decode('utf-8', errors='ignore')
            ssid = ""
            for line in res.split('\n'):
                if "SSID" in line and "BSSID" not in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        ssid = parts[1].strip(); break
            if ssid:
                with open(os.path.join(wifi_dir, "current_ssid.txt"), "w", encoding="utf-8") as f: f.write(ssid)
            subprocess.run(f'netsh wlan export profile key=clear folder="{wifi_dir}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            sc_path = os.path.join(base_dir, "SetupComplete.cmd")
            with open(sc_path, "w", encoding="utf-8") as f:
                f.write('@echo off\nsc config wlansvc start= auto\nnet start wlansvc\ntimeout /t 3 /nobreak >nul\nfor %%f in ("%~dp0WiFi\\*.xml") do netsh wlan add profile filename="%%f" user=all\nif exist "%~dp0WiFi\\current_ssid.txt" (\nset /p WLAN_SSID=<"%~dp0WiFi\\current_ssid.txt"\nnetsh wlan connect name="%WLAN_SSID%"\n)\n')
        except: pass

    if driver_mode != "Không Backup Driver":
        cb_log(f"Đang tiến hành nhổ Driver ({driver_mode})...")
        drv_dir = os.path.join(base_dir, "Drivers")
        os.makedirs(drv_dir, exist_ok=True)
        if driver_mode == "Backup Toàn Bộ Driver":
            ps_cmd = f'Export-WindowsDriver -Online -Destination "{drv_dir}"'
            subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            tmp_dir = os.path.join(base_dir, "DrvTemp")
            ps_cmd = f"""$ErrorActionPreference = 'SilentlyContinue'; New-Item -ItemType Directory -Force -Path "{tmp_dir}" | Out-Null; $drvs = Export-WindowsDriver -Online -Destination "{tmp_dir}"; foreach ($d in $drvs) {{ if ($d.ClassName -match 'Net|NetTrans|WLAN|Bluetooth') {{ $infPath = Split-Path $d.OriginalFileName; Copy-Item -Path $infPath -Destination "{drv_dir}" -Recurse -Force }} }}; Remove-Item -Path "{tmp_dir}" -Recurse -Force"""
            subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], creationflags=subprocess.CREATE_NO_WINDOW)

def nap_winre_tu_dong(o_dia_luu):
    unattend_xml = """<?xml version="1.0" encoding="utf-8"?><unattend xmlns="urn:schemas-microsoft-com:unattend" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State"><settings pass="specialize"><component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"><ComputerName>PC-Admin</ComputerName><TimeZone>SE Asia Standard Time</TimeZone></component></settings><settings pass="oobeSystem"><component name="Microsoft-Windows-International-Core" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"><InputLocale>en-US</InputLocale><SystemLocale>en-US</SystemLocale><UILanguage>en-US</UILanguage><UserLocale>vi-VN</UserLocale></component><component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"><OOBE><HideEULAPage>true</HideEULAPage><HideLocalAccountScreen>true</HideLocalAccountScreen><HideOnlineAccountScreens>true</HideOnlineAccountScreens><HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE><SkipMachineOOBE>true</SkipMachineOOBE><SkipUserOOBE>true</SkipUserOOBE><ProtectYourPC>3</ProtectYourPC></OOBE><UserAccounts><LocalAccounts><LocalAccount wcm:action="add"><Password><Value></Value><PlainText>true</PlainText></Password><Description>Admin</Description><DisplayName>Admin</DisplayName><Group>Administrators</Group><Name>Admin</Name></LocalAccount></LocalAccounts></UserAccounts><AutoLogon><Password><Value></Value><PlainText>true</PlainText></Password><Enabled>true</Enabled><LogonCount>9999</LogonCount><Username>Admin</Username></AutoLogon></component></settings></unattend>"""
    with open(f"{o_dia_luu}:\\ZT_Cloud_Install\\unattend.xml", "w", encoding="utf-8") as f: f.write(unattend_xml)
    
    ps_code = f"""
    $ChuCaiOS = [System.IO.Path]::GetPathRoot($env:windir).Substring(0,1); $PhanVungOS = Get-Partition -DriveLetter $ChuCaiOS; $OsDisk = $PhanVungOS.DiskNumber; $OsPart = $PhanVungOS.PartitionNumber; $WinREGoc = "C:\\Windows\\System32\\Recovery\\winre.wim"; $ThuMucMnt = "C:\\MountRE"
    reagentc.exe /enable; Start-Sleep 2; reagentc.exe /disable; Start-Sleep 2
    if (Test-Path $ThuMucMnt) {{ dism.exe /Unmount-Image /MountDir:$ThuMucMnt /Discard; Remove-Item $ThuMucMnt -Recurse -Force }}
    New-Item -ItemType Directory -Path $ThuMucMnt; $WinRECopy = "C:\\winre_xu-ly.wim"; Copy-Item $WinREGoc $WinRECopy -Force; Set-ItemProperty $WinRECopy IsReadOnly $false; dism.exe /Mount-Image /ImageFile:$WinRECopy /Index:1 /MountDir:$ThuMucMnt
    $Lenh = @"
@echo off
set "WPATH="
for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (if exist "%%D:\\ZT_Cloud_Install\\install.wim" set "WPATH=%%D:\\ZT_Cloud_Install\\install.wim")
manage-bde -unlock W: -pw "" >nul 2>&1
manage-bde -off W: >nul 2>&1
(echo select disk $OsDisk & echo select partition $OsPart & echo assign letter=W & echo format quick fs=ntfs label="Windows") | diskpart
dism /apply-image /imagefile:"%WPATH%" /index:1 /applydir:W:\\
if exist "%%~dpWPATHDrivers" ( dism /image:W:\\ /Add-Driver /Driver:"%%~dpWPATHDrivers" /Recurse )
bcdboot W:\\Windows
reg load HKLM\\ZT W:\\Windows\\System32\\config\\SYSTEM
reg add "HKLM\\ZT\\Setup\\LabConfig" /v BypassTPMCheck /t REG_DWORD /d 1 /f
reg add "HKLM\\ZT\\Setup\\LabConfig" /v BypassSecureBootCheck /t REG_DWORD /d 1 /f
reg unload HKLM\\ZT
mkdir W:\\Windows\\Panther
copy /Y "%%~dpWPATHunattend.xml" W:\\Windows\\Panther\\unattend.xml
mkdir W:\\Windows\\Setup\\Scripts
if exist "%%~dpWPATHSetupComplete.cmd" ( copy /Y "%%~dpWPATHSetupComplete.cmd" W:\\Windows\\Setup\\Scripts\\ )
if exist "%%~dpWPATHWiFi" ( mkdir W:\\Windows\\Setup\\Scripts\\WiFi & copy /Y "%%~dpWPATHWiFi\\*.*" W:\\Windows\\Setup\\Scripts\\WiFi\\ )
rd /s /q "%%~dpWPATH"
wpeutil reboot
"@
    $Lenh | Out-File "$ThuMucMnt\\Windows\\System32\\LenhRE.cmd" -Encoding oem; '[LaunchApps]' + [char]13 + [char]10 + 'X:\\Windows\\System32\\LenhRE.cmd' | Out-File "$ThuMucMnt\\Windows\\System32\\winpeshl.ini" -Encoding ascii; dism.exe /Unmount-Image /MountDir:$ThuMucMnt /Commit; cmd.exe /c 'attrib -h -s -r' + ' ' + $WinREGoc; Copy-Item $WinRECopy $WinREGoc -Force; Remove-Item $WinRECopy -Force; reagentc.exe /setreimage /path C:\\Windows\\System32\\Recovery; reagentc.exe /enable; reagentc.exe /boottore
    """
    ps_file = f"{o_dia_luu}:\\ZT_Cloud_Install\\config.ps1"
    with open(ps_file, "w", encoding="utf-8") as f: f.write(ps_code)
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_file], creationflags=subprocess.CREATE_NO_WINDOW)
    os.remove(ps_file)

# ==========================================
# 4. ĐỘNG CƠ TẢI PYTHON (ĐÃ FIX BASE64)
# ==========================================
def tai_file_thong_minh(file_id, luu_tai, cb_tien_do, cb_log, tin_hieu_huy):
    for idx, b64_key in enumerate(API_KEYS_B64):
        if tin_hieu_huy.is_set(): return False
        try: key = base64.b64decode(b64_key).decode('utf-8')
        except: continue
        cb_log(f"Đang kết nối tải WIM bằng API Key {idx + 1}...")
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={key}&acknowledgeAbuse=true"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                total = int(res.getheader('Content-Length', 0))
                with open(luu_tai, 'wb') as f:
                    done = 0; start = time.time()
                    while True:
                        if tin_hieu_huy.is_set(): return False
                        chunk = res.read(2 * 1024 * 1024)
                        if not chunk: break
                        f.write(chunk); done += len(chunk)
                        if total > 0: cb_tien_do((done/total)*100, done, total, done/(time.time()-start) if (time.time()-start)>0 else 0)
            return True
        except: continue
    if tin_hieu_huy.is_set(): return False
    cb_log("Cào Web Bypass Token...")
    cj = http.cookiejar.CookieJar(); opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    res = opener.open(f"https://drive.google.com/uc?export=download&id={file_id}")
    html = res.read().decode('utf-8', errors='ignore')
    token = re.search(r'confirm=([a-zA-Z0-9_-]+)', html)
    if token: res = opener.open(f"https://drive.google.com/uc?export=download&id={file_id}&confirm={token.group(1)}")
    total = int(res.getheader('Content-Length', 0))
    with open(luu_tai, 'wb') as f:
        done = 0; start = time.time()
        while True:
            if tin_hieu_huy.is_set(): res.close(); return False
            chunk = res.read(2 * 1024 * 1024)
            if not chunk: break
            f.write(chunk); done += len(chunk)
            cb_tien_do((done/total)*100, done, total, done/(time.time()-start) if (time.time()-start)>0 else 0)
    return True

# ==========================================
# 5. GIAO DIỆN CUSTOM-TKINTER (DASHBOARD)
# ==========================================
class VietToolboxApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VietToolbox ISO Client - Dashboard V25")
        self.geometry("850x700")
        self.minsize(800, 650)
        self.tin_hieu_huy = threading.Event(); self.dang_chay = False
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(2, weight=1)
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.lbl_title = ctk.CTkLabel(self.frame_header, text="HỆ THỐNG TRIỂN KHAI WINDOWS ZERO-TOUCH", font=ctk.CTkFont(family="Arial", size=20, weight="bold"))
        self.lbl_title.pack()
        self.lbl_subtitle = ctk.CTkLabel(self.frame_header, text="Đang đồng bộ dữ liệu từ kho GitHub...", font=ctk.CTkFont(family="Arial", size=13), text_color="gray")
        self.lbl_subtitle.pack()
        self.frame_options = ctk.CTkFrame(self)
        self.frame_options.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.frame_options.grid_columnconfigure((0, 1, 2), weight=1)
        self.driver_var = ctk.StringVar(value="Backup LAN & WIFI")
        self.opt_driver = ctk.CTkOptionMenu(self.frame_options, values=["Không Backup Driver", "Backup LAN & WIFI", "Backup Toàn Bộ Driver"], variable=self.driver_var, width=200)
        self.opt_driver.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        self.wifi_var = ctk.BooleanVar(value=True)
        self.sw_wifi = ctk.CTkSwitch(self.frame_options, text="Lưu WiFi & Tự Động Kết Nối", variable=self.wifi_var, onvalue=True, offvalue=False, font=ctk.CTkFont(weight="bold"))
        self.sw_wifi.grid(row=0, column=1, padx=20, pady=15)
        self.test_var = ctk.BooleanVar(value=False)
        self.sw_test = ctk.CTkSwitch(self.frame_options, text="CHẾ ĐỘ TEST", variable=self.test_var, onvalue=True, offvalue=False, progress_color="#D97706", font=ctk.CTkFont(weight="bold"))
        self.sw_test.grid(row=0, column=2, padx=20, pady=15, sticky="e")
        self.scroll_list = ctk.CTkScrollableFrame(self, label_text=" DANH SÁCH BẢN CÀI ĐẶT ", label_font=ctk.CTkFont(weight="bold"))
        self.scroll_list.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.log_box = ctk.CTkTextbox(self, height=120, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#0F172A", text_color="#38BDF8", border_width=1, border_color="#334155")
        self.log_box.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.log_box.insert("0.0", "[HỆ THỐNG] Đã khởi tạo môi trường Zero-Touch thành công.\n")
        self.log_box.configure(state="disabled")
        self.frame_bottom = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_bottom.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.frame_bottom.grid_columnconfigure(0, weight=1)
        self.progress_bar = ctk.CTkProgressBar(self.frame_bottom, height=15)
        self.progress_bar.grid(row=0, column=0, padx=(0, 20), pady=5, sticky="ew")
        self.progress_bar.set(0)
        self.lbl_info = ctk.CTkLabel(self.frame_bottom, text="0% | 0 MB/s", font=ctk.CTkFont(weight="bold", size=13))
        self.lbl_info.grid(row=1, column=0, sticky="w", pady=0)
        self.btn_stop = ctk.CTkButton(self.frame_bottom, text="🛑 HỦY TẢI", width=120, height=40, fg_color="#BE123C", hover_color="#9F1239", font=ctk.CTkFont(weight="bold", size=14), state="disabled", command=self.gui_lenh_huy)
        self.btn_stop.grid(row=0, column=1, rowspan=2, sticky="e")
        self.nap_du_lieu_github()

    def ghi_log(self, text):
        self.log_box.configure(state="normal"); self.log_box.insert("end", f"[*] {text}\n"); self.log_box.see("end"); self.log_box.configure(state="disabled"); self.update_idletasks()

    def nap_du_lieu_github(self):
        def task():
            try:
                res = urllib.request.urlopen(CSV_URL); lines = res.read().decode('utf-8').splitlines(); reader = csv.DictReader(lines); count = 0
                for row in reader:
                    if ".wim" in row['Name'].lower(): self.tao_nut_bam(row['Name'], row['FileID']); count += 1
                self.lbl_subtitle.configure(text=f"✅ Đã tải thành công {count} cấu hình Windows từ GitHub", text_color="#10B981")
            except Exception as e:
                self.lbl_subtitle.configure(text="❌ Lỗi kết nối kho dữ liệu GitHub!", text_color="#EF4444"); self.ghi_log(f"LỖI MẠNG: {str(e)}")
        threading.Thread(target=task, daemon=True).start()

    def tao_nut_bam(self, ten, fid):
        btn = ctk.CTkButton(self.scroll_list, text=f"📥 CÀI ĐẶT: {ten}", font=ctk.CTkFont(size=14, weight="bold"), fg_color="#1E293B", hover_color="#0284C7", anchor="w", height=45, command=lambda: self.xac_nhan_cai_dat(ten, fid))
        btn.pack(fill="x", pady=5, padx=10)

    def xac_nhan_cai_dat(self, ten, fid):
        if self.dang_chay: return messagebox.showwarning("Cảnh báo", "Hệ thống đang bận. Vui lòng HỦY tiến trình hiện tại trước.")
        if not self.test_var.get():
            kq = messagebox.askyesno("XÁC NHẬN FORMAT Ổ C", f"CẢNH BÁO: Toàn bộ dữ liệu ổ C:\\ sẽ bị xóa sạch để cài bản:\n[{ten}]\n\nBạn có chắc chắn muốn thực hiện quy trình Zero-Touch không?")
            if not kq: return
        self.dang_chay = True; self.tin_hieu_huy.clear(); self.btn_stop.configure(state="normal"); self.progress_bar.set(0); self.log_box.configure(state="normal"); self.log_box.delete("0.0", "end"); self.log_box.configure(state="disabled")
        self.ghi_log(f"KHỞI ĐỘNG CHIẾN DỊCH: {ten}")
        threading.Thread(target=self.worker, args=(ten, fid, self.driver_var.get(), self.wifi_var.get()), daemon=True).start()

    def gui_lenh_huy(self):
        if self.dang_chay: self.ghi_log("Phát lệnh HỦY TẢI. Đang dọn dẹp hệ thống..."); self.btn_stop.configure(state="disabled"); self.tin_hieu_huy.set()

    def worker(self, ten, fid, drv_mode, wifi_mode):
        wim_file = ""
        file_local_chon = None  # Biến lưu đường dẫn wim local nếu mạng yếu
        
        try:
            # --- [TÍNH NĂNG MỚI] KIỂM TRA MẠNG VÀ PHƯƠNG ÁN DỰ PHÒNG ---
            toc_do = kiem_tra_toc_do_mang(self.ghi_log)
            if toc_do < 2.0: # Ngưỡng tốc độ (tùy chỉnh: 2.0 MB/s)
                self.ghi_log("Phát hiện mạng yếu hoặc không ổn định!")
                chon_local = messagebox.askyesno(
                    "Cảnh báo Mạng Yếu", 
                    f"Tốc độ mạng hiện tại khá chậm (~{toc_do:.1f} MB/s).\nViệc tải bản cài đặt có thể mất rất nhiều thời gian.\n\nBạn có muốn chuyển sang phương án DỰ PHÒNG: Chọn một file cài đặt (.wim) có sẵn trong USB/Ổ cứng không?"
                )
                if chon_local:
                    file_local_chon = filedialog.askopenfilename(
                        title="Chọn file install.wim dự phòng", 
                        filetypes=[("Windows Image", "*.wim")]
                    )
                    if not file_local_chon:
                        self.ghi_log("Đã hủy chọn file dự phòng. Hủy chiến dịch.")
                        return self.reset_ui()
                    self.ghi_log(f"Đã chuyển sang phương án dự phòng. Dùng file: {file_local_chon}")
                else:
                    tiep_tuc = messagebox.askyesno("Tiếp tục?", "Bạn vẫn muốn CỐ GẮNG tải qua mạng chậm này?")
                    if not tiep_tuc:
                        self.ghi_log("Đã hủy tiến trình theo yêu cầu người dùng.")
                        return self.reset_ui()
            # -----------------------------------------------------------

            # 1. TẮT BITLOCKER TRƯỚC
            tat_bitlocker_he_thong(self.ghi_log)
            
            self.ghi_log("Phân tích ổ đĩa an toàn (Không chạm ổ C)...")
            safe_d = tim_o_dia_an_toan()
            base_dir = f"{safe_d}:\\ZT_Cloud_Install"
            os.makedirs(base_dir, exist_ok=True)
            wim_file = os.path.join(base_dir, "install.wim")
            
            thuc_hien_backup(base_dir, drv_mode, wifi_mode, self.ghi_log)
            if self.tin_hieu_huy.is_set(): return self.xu_ly_huy(base_dir)
            
            # --- XỬ LÝ NGUỒN FILE WIM TÙY THEO PHƯƠNG ÁN ---
            if file_local_chon:
                self.ghi_log("Đang copy file WIM dự phòng vào vùng an toàn. Vui lòng đợi...")
                shutil.copy2(file_local_chon, wim_file)
                self.ghi_log("Đã copy xong file WIM.")
            else:
                self.ghi_log("Bắt đầu kết nối Đám mây lấy File WIM...")
                thanh_cong = tai_file_thong_minh(fid, wim_file, self.up_progress, self.ghi_log, self.tin_hieu_huy)
                if not thanh_cong: return self.xu_ly_huy(base_dir)
            # -----------------------------------------------

            if self.test_var.get():
                self.ghi_log(f"CHẾ ĐỘ TEST HOÀN TẤT. WIM lưu tại: {base_dir}")
                messagebox.showinfo("Thành Công (Test Mode)", f"File WIM và Backup đã lưu an toàn ở:\n{base_dir}")
                self.reset_ui()
                return
                
            self.ghi_log("Đang nạp mã độc quyền Format & Xả WIM vào môi trường WinRE...")
            nap_winre_tu_dong(safe_d)
            self.ghi_log("TẤT CẢ ĐÃ SẴN SÀNG! Tiến hành Restart máy sau 3 giây.")
            messagebox.showinfo("Hoàn tất quy trình", "Quy trình Zero-Touch đã nạp xong!\nMáy tính sẽ khởi động lại và tự động Format ổ C, cài Win, bơm Driver & kết nối WiFi.")
            os.system("shutdown /r /t 0 /c \"Tien hanh Zero-Touch Install\"")
            
        except Exception as e: 
            self.ghi_log(f"LỖI PHÁT SINH: {str(e)}")
            messagebox.showerror("Lỗi", str(e))
            if 'base_dir' in locals(): self.xu_ly_huy(base_dir)
            else: self.reset_ui()

    def xu_ly_huy(self, base_dir):
        if os.path.exists(base_dir): shutil.rmtree(base_dir, ignore_errors=True)
        self.ghi_log("Đã dọn dẹp phân vùng thành công. Trả lại không gian ổ cứng."); self.reset_ui(); self.progress_bar.set(0); self.lbl_info.configure(text="0% | 0 MB/s")

    def reset_ui(self): self.dang_chay = False; self.btn_stop.configure(state="disabled"); self.ghi_log("Hệ thống về trạng thái Chờ lệnh.")

    def up_progress(self, p, d, t, s):
        self.progress_bar.set(p / 100.0); self.lbl_info.configure(text=f"{int(p)}% | {s/(1024*1024):.1f} MB/s | {d/1024**3:.1f}/{t/1024**3:.1f} GB"); self.update_idletasks()

if __name__ == "__main__":
    try:
        app = VietToolboxApp(); app.mainloop()
    except Exception as e:
        desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop'); log_file = os.path.join(desktop_path, "Loi_ZeroTouch_Log.txt")
        with open(log_file, "w", encoding="utf-8") as f: f.write(traceback.format_exc())