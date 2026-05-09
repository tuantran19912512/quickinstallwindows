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
import random  # <-- BỔ SUNG THƯ VIỆN ĐỂ TẠO TÊN MÁY NGẪU NHIÊN
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import base64

# ==========================================
# 1. CẤU HÌNH DỮ LIỆU & BẢO MẬT
# ==========================================
CSV_URL = "https://raw.githubusercontent.com/tuantran19912512/Windows-tool-box/refs/heads/main/iso_list.csv"

# Khóa API đã mã hóa Base64
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
def kiem_tra_quyen_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if not kiem_tra_quyen_admin():
    if getattr(sys, 'frozen', False):
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1)
    sys.exit()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ==========================================
# 3. TIỆN ÍCH HỆ THỐNG (Mạng, BitLocker, Backup, WinRE)
# ==========================================
def do_toc_do_mang(ghi_chu_log):
    ghi_chu_log("Đang đo lường băng thông mạng (Máy chủ Cloudflare)...")
    try:
        du_ong_dan_kiem_tra = "https://speed.cloudflare.com/__down?bytes=1048576"
        yeu_cau = urllib.request.Request(du_ong_dan_kiem_tra, headers={'User-Agent': 'Mozilla/5.0'})
        bat_dau = time.time()
        with urllib.request.urlopen(yeu_cau, timeout=5) as phan_hoi:
            du_lieu = phan_hoi.read()
        thoi_gian_mat = time.time() - bat_dau
        toc_do_thuc = (len(du_lieu) / (1024 * 1024)) / (thoi_gian_mat if thoi_gian_mat > 0.001 else 0.001)
        ghi_chu_log(f"Kết quả đo tốc độ: ~ {toc_do_thuc:.1f} MB/s")
        return toc_do_thuc
    except:
        ghi_chu_log("Không thể kết nối máy chủ đo tốc độ. Áp dụng tốc độ ảo mặc định.")
        return 5.0

def huy_bitlocker(ghi_chu_log):
    ghi_chu_log("Tiến hành dò tìm mã hóa BitLocker trên ổ hệ điều hành...")
    try:
        o_cai_win = os.environ.get('SystemDrive', 'C:')
        lenh_kiem_tra = f'manage-bde -status {o_cai_win}'
        ket_qua_kiem_tra = subprocess.check_output(lenh_kiem_tra, shell=True).decode('utf-8', errors='ignore')
        if any(tu_khoa in ket_qua_kiem_tra for tu_khoa in ["Mã hóa", "Encryption", "完全な暗号化"]):
            ghi_chu_log(f"Phát hiện rào cản BitLocker. Ra lệnh giải mã tức thời phân vùng {o_cai_win}...")
            subprocess.run(f'manage-bde -off {o_cai_win}', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except: pass

def tim_phan_vung_an_toan():
    mat_na_bit = ctypes.windll.kernel32.GetLogicalDrives()
    danh_sach_o_dia = [ky_tu for vi_tri, ky_tu in enumerate(string.ascii_uppercase) if mat_na_bit & (1 << vi_tri)]
    o_he_thong = os.environ.get('SystemDrive', 'C:')[0]
    o_tot_nhat = None; dung_luong_max = 0
    for o_dia in danh_sach_o_dia:
        if o_dia == o_he_thong: continue
        duong_dan = f"{o_dia}:\\"
        if ctypes.windll.kernel32.GetDriveTypeW(duong_dan) != 3: continue
        try:
            _, _, dung_luong_trong = shutil.disk_usage(duong_dan)
            if dung_luong_trong > 10 * 1024**3 and dung_luong_trong > dung_luong_max:
                dung_luong_max = dung_luong_trong; o_tot_nhat = o_dia
        except: pass
    if not o_tot_nhat: raise Exception("Không tìm thấy ổ đĩa Data (D, E...) nào trống trên 10GB để chứa WIM!")
    return o_tot_nhat

def dong_goi_du_lieu_cu(thu_muc_goc, che_do_driver, che_do_wifi, ghi_chu_log):
    if che_do_wifi:
        ghi_chu_log("Bắt đầu trích xuất hồ sơ mạng WiFi...")
        thu_muc_wifi = os.path.join(thu_muc_goc, "WiFi"); os.makedirs(thu_muc_wifi, exist_ok=True)
        try:
            ket_qua_netsh = subprocess.check_output('netsh wlan show interfaces', shell=True).decode('utf-8', errors='ignore')
            ten_mang_hien_tai = re.search(r'SSID\s*:\s*(.*)', ket_qua_netsh)
            if ten_mang_hien_tai:
                with open(os.path.join(thu_muc_wifi, "current_ssid.txt"), "w", encoding="utf-8") as file_chu: 
                    file_chu.write(ten_mang_hien_tai.group(1).strip())
            subprocess.run(f'netsh wlan export profile key=clear folder="{thu_muc_wifi}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            with open(os.path.join(thu_muc_goc, "SetupComplete.cmd"), "w", encoding="utf-8") as lenh_cmd:
                lenh_cmd.write('@echo off\nsc config wlansvc start= auto\nnet start wlansvc\ntimeout /t 3 /nobreak >nul\nfor %%f in ("%~dp0WiFi\\*.xml") do netsh wlan add profile filename="%%f" user=all\nif exist "%~dp0WiFi\\current_ssid.txt" (set /p WLAN_SSID=<"%~dp0WiFi\\current_ssid.txt"\nnetsh wlan connect name="%WLAN_SSID%")\n')
        except: pass

    if che_do_driver != "Không Backup Driver":
        ghi_chu_log(f"Đang kích hoạt quy trình bóc tách ({che_do_driver})...")
        thu_muc_driver = os.path.join(thu_muc_goc, "Drivers"); os.makedirs(thu_muc_driver, exist_ok=True)
        if che_do_driver == "Backup Toàn Bộ Driver":
            subprocess.run(["powershell", "-Command", f'Export-WindowsDriver -Online -Destination "{thu_muc_driver}"'], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            thu_muc_tam = os.path.join(thu_muc_goc, "DrvTemp")
            lenh_ps = f"$drvs = Export-WindowsDriver -Online -Destination '{thu_muc_tam}'; foreach ($d in $drvs) {{ if ($d.ClassName -match 'Net|WLAN|Bluetooth') {{ Copy-Item (Split-Path $d.OriginalFileName) -Destination '{thu_muc_driver}' -Recurse -Force }} }}; Remove-Item '{thu_muc_tam}' -Recurse -Force"
            subprocess.run(["powershell", "-Command", lenh_ps], creationflags=subprocess.CREATE_NO_WINDOW)

def nap_tuy_tuyen_winre(o_dia_muc_tieu, ghi_chu_log):
    # CHỨC NĂNG MỚI: Tự động sinh tên máy chống đụng IP LAN
    chuoi_ky_tu_ngau_nhien = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    ten_may_tinh = f"PC-{chuoi_ky_tu_ngau_nhien}"
    ghi_chu_log(f"Đã cấp phát tự động tên máy: {ten_may_tinh} (Chống trùng lặp LAN)")

    cau_hinh_unattend = f"""<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
    <settings pass="specialize">
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
            <ComputerName>{ten_may_tinh}</ComputerName>
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
    
    thu_muc_lam_viec = f"{o_dia_muc_tieu}:\\ZT_Cloud_Install"; os.makedirs(thu_muc_lam_viec, exist_ok=True)
    with open(f"{thu_muc_lam_viec}\\unattend.xml", "w", encoding="utf-8") as file_xml: file_xml.write(cau_hinh_unattend)
    
    kich_ban_ps = f"""
    $ChuCaiOS = [System.IO.Path]::GetPathRoot($env:windir).Substring(0,1); $PhanVungOS = Get-Partition -DriveLetter $ChuCaiOS; $OsDisk = $PhanVungOS.DiskNumber; $OsPart = $PhanVungOS.PartitionNumber; $WinREGoc = "C:\\Windows\\System32\\Recovery\\winre.wim"; $ThuMucMnt = "C:\\MountRE"
    reagentc.exe /enable; reagentc.exe /disable; New-Item -ItemType Directory -Force -Path $ThuMucMnt
    dism.exe /Mount-Image /ImageFile:$WinREGoc /Index:1 /MountDir:$ThuMucMnt
    $Lenh = @"
@echo off
for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (if exist "%%D:\\ZT_Cloud_Install\\install.wim" set "WPATH=%%D:\\ZT_Cloud_Install\\install.wim")
(echo select disk $OsDisk & echo select partition $OsPart & echo assign letter=W & echo format quick fs=ntfs label="Windows") | diskpart
dism /apply-image /imagefile:"%WPATH%" /index:1 /applydir:W:\\
if exist "%%~dpWPATHDrivers" ( dism /image:W:\\ /Add-Driver /Driver:"%%~dpWPATHDrivers" /Recurse )
bcdboot W:\\Windows
mkdir W:\\Windows\\Panther
copy /Y "%%~dpWPATHunattend.xml" W:\\Windows\\Panther\\unattend.xml
if exist "%%~dpWPATHSetupComplete.cmd" ( mkdir W:\\Windows\\Setup\\Scripts & copy /Y "%%~dpWPATHSetupComplete.cmd" W:\\Windows\\Setup\\Scripts\\ )
wpeutil reboot
"@
    $Lenh | Out-File "$ThuMucMnt\\Windows\\System32\\LenhRE.cmd" -Encoding oem; '[LaunchApps]' + [char]13 + [char]10 + 'X:\\Windows\\System32\\LenhRE.cmd' | Out-File "$ThuMucMnt\\Windows\\System32\\winpeshl.ini" -Encoding ascii
    dism.exe /Unmount-Image /MountDir:$ThuMucMnt /Commit; reagentc.exe /enable; reagentc.exe /boottore
    """
    with open(f"{thu_muc_lam_viec}\\config.ps1", "w", encoding="utf-8") as file_ps: file_ps.write(kich_ban_ps)
    subprocess.run(["powershell", "-File", f"{thu_muc_lam_viec}\\config.ps1"], creationflags=subprocess.CREATE_NO_WINDOW)

# ==========================================
# 4. ĐỘNG CƠ TẢI DỮ LIỆU ĐÁM MÂY
# ==========================================
def tai_file_tu_dam_may(ma_file, duong_dan_luu, cap_nhat_tien_do, ghi_chu_log, tin_hieu_huy):
    for vi_tri, khoa_b64 in enumerate(API_KEYS_B64):
        if tin_hieu_huy.is_set(): return False
        try: khoa_giai_ma = base64.b64decode(khoa_b64).decode('utf-8')
        except: continue
        duong_dan_tai = f"https://www.googleapis.com/drive/v3/files/{ma_file}?alt=media&key={khoa_giai_ma}&acknowledgeAbuse=true"
        yeu_cau_tai = urllib.request.Request(duong_dan_tai, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(yeu_cau_tai, timeout=15) as phan_hoi:
                tong_dung_luong = int(phan_hoi.getheader('Content-Length', 0))
                with open(duong_dan_luu, 'wb') as file_tai:
                    da_tai = 0; thoi_gian_bat_dau = time.time()
                    while True:
                        if tin_hieu_huy.is_set(): return False
                        phan_doan = phan_hoi.read(1024 * 1024)
                        if not phan_doan: break
                        file_tai.write(phan_doan); da_tai += len(phan_doan)
                        if tong_dung_luong > 0: cap_nhat_tien_do((da_tai/tong_dung_luong)*100, da_tai, tong_dung_luong, da_tai/(time.time()-thoi_gian_bat_dau))
            return True
        except: continue
    return False

# ==========================================
# 5. LÕI GIAO DIỆN BẢNG ĐIỀU KHIỂN
# ==========================================
class GiaoDienVietToolbox(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VietToolbox ISO Client - Dashboard V25.7 (Auto-Rename)")
        self.geometry("850x720"); self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(2, weight=1)
        self.tin_hieu_huy = threading.Event(); self.trang_thai_chay = False

        self.khung_tieu_de = ctk.CTkFrame(self, fg_color="transparent"); self.khung_tieu_de.grid(row=0, column=0, pady=15, sticky="ew")
        ctk.CTkLabel(self.khung_tieu_de, text="HỆ THỐNG TRIỂN KHAI WINDOWS ZERO-TOUCH", font=("Arial", 22, "bold")).pack()
        self.nhan_phu = ctk.CTkLabel(self.khung_tieu_de, text="Đang đồng bộ dữ liệu đám mây...", text_color="gray"); self.nhan_phu.pack()

        self.khung_tuy_chon = ctk.CTkFrame(self); self.khung_tuy_chon.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.khung_tuy_chon.grid_columnconfigure((0, 1, 2), weight=1)
        self.bien_driver = ctk.StringVar(value="Backup LAN & WIFI")
        ctk.CTkOptionMenu(self.khung_tuy_chon, values=["Không Backup Driver", "Backup LAN & WIFI", "Backup Toàn Bộ Driver"], variable=self.bien_driver).grid(row=0, column=0, padx=10, pady=15)
        self.bien_wifi = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(self.khung_tuy_chon, text="Lưu WiFi & Connect", variable=self.bien_wifi).grid(row=0, column=1, padx=10, pady=15)
        self.bien_test = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(self.khung_tuy_chon, text="CHẾ ĐỘ TEST", variable=self.bien_test, progress_color="#D97706").grid(row=0, column=2, padx=10, pady=15)

        self.khung_cuon = ctk.CTkScrollableFrame(self, label_text=" DANH SÁCH BẢN CÀI ĐẶT "); self.khung_cuon.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        
        self.hop_nhat_ky = ctk.CTkTextbox(self, height=100, font=("Consolas", 12), fg_color="#0F172A", text_color="#38BDF8"); self.hop_nhat_ky.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        self.hop_nhat_ky.insert("0.0", "Hệ thống sẵn sàng.\n"); self.hop_nhat_ky.configure(state="disabled")

        self.khung_duoi = ctk.CTkFrame(self, fg_color="transparent"); self.khung_duoi.grid(row=4, column=0, padx=20, pady=15, sticky="ew")
        self.khung_duoi.grid_columnconfigure(0, weight=1)
        self.thanh_tien_do = ctk.CTkProgressBar(self.khung_duoi, height=12); self.thanh_tien_do.grid(row=0, column=0, padx=(0, 20), sticky="ew"); self.thanh_tien_do.set(0)
        self.nhan_thong_tin = ctk.CTkLabel(self.khung_duoi, text="0% | 0 MB/s", font=("Arial", 12, "bold")); self.nhan_thong_tin.grid(row=1, column=0, sticky="w")
        self.nut_huy = ctk.CTkButton(self.khung_duoi, text="🛑 HỦY LỆNH", fg_color="#BE123C", hover_color="#9F1239", state="disabled", command=self.huy_tien_trinh); self.nut_huy.grid(row=0, column=1, rowspan=2)

        self.tai_du_lieu_kho()

    def ghi_nhat_ky(self, noi_dung):
        self.hop_nhat_ky.configure(state="normal"); self.hop_nhat_ky.insert("end", f"[*] {noi_dung}\n"); self.hop_nhat_ky.see("end"); self.hop_nhat_ky.configure(state="disabled"); self.update()

    def tai_du_lieu_kho(self):
        def tac_vu():
            try:
                phan_hoi = urllib.request.urlopen(CSV_URL); cac_dong = phan_hoi.read().decode('utf-8').splitlines(); doc_csv = csv.DictReader(cac_dong)
                for dong in doc_csv:
                    if ".wim" in dong['Name'].lower(): self.tao_nut_bam(dong['Name'], dong['FileID'])
                self.nhan_phu.configure(text="✅ Đã kết nối kho lưu trữ", text_color="#10B981")
            except: self.nhan_phu.configure(text="❌ Lỗi mất kết nối mạng", text_color="#EF4444")
        threading.Thread(target=tac_vu, daemon=True).start()

    def tao_nut_bam(self, ten_ban_cai, ma_file):
        ctk.CTkButton(self.khung_cuon, text=f"📥 CÀI ĐẶT: {ten_ban_cai}", font=("Arial", 13, "bold"), fg_color="#1E293B", anchor="w", command=lambda: self.khoi_dong(ten_ban_cai, ma_file)).pack(fill="x", pady=2, padx=5)

    def huy_tien_trinh(self): self.tin_hieu_huy.set(); self.nut_huy.configure(state="disabled")

    def khoi_dong(self, ten_ban_cai, ma_file):
        if self.trang_thai_chay: return
        if not self.bien_test.get() and not messagebox.askyesno("Xác nhận Format", "Toàn bộ ổ C sẽ bị xóa. Tiếp tục?"): return
        self.trang_thai_chay = True; self.tin_hieu_huy.clear(); self.nut_huy.configure(state="normal")
        threading.Thread(target=self.luong_xu_ly_chinh, args=(ten_ban_cai, ma_file), daemon=True).start()

    def luong_xu_ly_chinh(self, ten_ban_cai, ma_file):
        try:
            toc_do_mang = do_toc_do_mang(self.ghi_nhat_ky)
            duong_dan_local = None
            if toc_do_mang < 1.5:
                if messagebox.askyesno("Phát hiện mạng yếu", f"Băng thông ~{toc_do_mang:.1f}MB/s. Chuyển sang chọn file .wim thủ công từ USB?"):
                    duong_dan_local = filedialog.askopenfilename(filetypes=[("Windows Image", "*.wim")])

            huy_bitlocker(self.ghi_nhat_ky)
            o_an_toan = tim_phan_vung_an_toan(); thu_muc_lam_viec = f"{o_an_toan}:\\ZT_Cloud_Install"; os.makedirs(thu_muc_lam_viec, exist_ok=True); file_wim_muc_tieu = os.path.join(thu_muc_lam_viec, "install.wim")
            dong_goi_du_lieu_cu(thu_muc_lam_viec, self.bien_driver.get(), self.bien_wifi.get(), self.ghi_nhat_ky)

            if duong_dan_local:
                self.ghi_nhat_ky("Đang chép dữ liệu từ USB..."); shutil.copy2(duong_dan_local, file_wim_muc_tieu)
            else:
                self.ghi_nhat_ky(f"Bắt đầu kéo dữ liệu {ten_ban_cai}..."); 
                if not tai_file_tu_dam_may(ma_file, file_wim_muc_tieu, self.cap_nhat_giao_dien_tai, self.ghi_nhat_ky, self.tin_hieu_huy): return self.khoi_phuc_mac_dinh("Đã hủy hoặc xảy ra lỗi mạng.")

            if self.bien_test.get():
                messagebox.showinfo("Thành Công", f"Đã lưu tại {file_wim_muc_tieu}"); return self.khoi_phuc_mac_dinh()

            self.ghi_nhat_ky("Đang nạp kịch bản vào WinRE..."); 
            nap_tuy_tuyen_winre(o_an_toan, self.ghi_nhat_ky) # Truyền biến ghi log vào hàm
            
            messagebox.showinfo("Hoàn Tất Xử Lý", "Hệ thống sẽ tự khởi động lại để tiến hành Zero-Touch."); os.system("shutdown /r /t 0")
        except Exception as loi_phat_sinh:
            messagebox.showerror("Báo Cáo Lỗi", str(loi_phat_sinh)); self.khoi_phuc_mac_dinh()

    def khoi_phuc_mac_dinh(self, loi_nhan="Tiến trình đã kết thúc."):
        self.trang_thai_chay = False; self.nut_huy.configure(state="disabled"); self.ghi_nhat_ky(loi_nhan)

    def cap_nhat_giao_dien_tai(self, phan_tram, da_tai, tong_cong, toc_do):
        self.thanh_tien_do.set(phan_tram/100); self.nhan_thong_tin.configure(text=f"{int(phan_tram)}% | {toc_do/(1024*1024):.1f} MB/s | {da_tai/1024**3:.1f}GB"); self.update()

if __name__ == "__main__":
    ung_dung = GiaoDienVietToolbox(); ung_dung.mainloop()