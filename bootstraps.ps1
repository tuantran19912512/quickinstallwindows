# ==============================================================================
# VIETTOOLBOX CLOUD BOOTSTRAPPER - FIX LIÊN KẾT GITHUB & CHỐNG FILE ẢO
# ==============================================================================

# 1. Chạy quyền Admin
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs; exit
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$ErrorActionPreference = "SilentlyContinue"

# --- [LIÊN KẾT MỚI CỦA SẾP] ---
$LinkPythonScript = "https://raw.githubusercontent.com/tuantran19912512/quickinstallwindows/main/quickinstall.py?t=$((Get-Date).Ticks)"
$PythonLibs = @("customtkinter")

# --- Giao diện Đồ họa ---
$Form = New-Object System.Windows.Forms.Form
$Form.Text = "VietToolbox Cloud Deploy"
$Form.Size = New-Object System.Drawing.Size(460, 180)
$Form.StartPosition = "CenterScreen"
$Form.FormBorderStyle = "FixedDialog"
$Form.BackColor = [System.Drawing.Color]::FromArgb(15, 23, 42)

$Label = New-Object System.Windows.Forms.Label
$Label.Text = "VIETTOOLBOX - ĐANG CHUẨN BỊ THƯ VIỆN"
$Label.Font = New-Object System.Drawing.Font("Arial", 11, [System.Drawing.FontStyle]::Bold)
$Label.ForeColor = [System.Drawing.Color]::White
$Label.AutoSize = $true; $Label.Location = New-Object System.Drawing.Point(20, 20); $Form.Controls.Add($Label)

$Status = New-Object System.Windows.Forms.Label
$Status.Text = "Đang kiểm tra Python..."; $Status.ForeColor = [System.Drawing.Color]::LightGray
$Status.AutoSize = $true; $Status.Location = New-Object System.Drawing.Point(20, 50); $Form.Controls.Add($Status)

$Bar = New-Object System.Windows.Forms.ProgressBar
$Bar.Size = New-Object System.Drawing.Size(400, 20); $Bar.Location = New-Object System.Drawing.Point(20, 85); $Form.Controls.Add($Bar)

$Form.Show(); $Form.Refresh()

function Update-UI ($msg, $val) {
    $Status.Text = $msg; $Bar.Value = $val; $Form.Refresh()
}

# --- BƯỚC 1: XỬ LÝ PYTHON (BỎ QUA FILE ẢO WINDOWS STORE) ---
Update-UI "Đang kiểm tra môi trường Python..." 20
$pyCmd = Get-Command "python" -ErrorAction SilentlyContinue
if (-not ($pyCmd -and ($pyCmd.Source -notmatch "WindowsApps"))) {
    Update-UI "Đang tải Python 3.12 chuẩn từ server..." 40
    $UrlPy = "https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe"
    $PathPy = Join-Path $env:TEMP "py_install.exe"
    Invoke-WebRequest -Uri $UrlPy -OutFile $PathPy -UseBasicParsing
    
    Update-UI "Đang cài đặt Python (Silent)..." 60
    $p = Start-Process -FilePath $PathPy -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_tcltk=1" -Wait -PassThru
    Remove-Item $PathPy
    # Cập nhật PATH ngay lập tức cho phiên làm việc này
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# --- BƯỚC 2: CÀI THƯ VIỆN GIAO DIỆN ---
Update-UI "Đang nạp thư viện CustomTkinter..." 80
python -m pip install $PythonLibs --quiet

# --- BƯỚC 3: TẢI SCRIPT TỪ GITHUB VÀ KHỞI CHẠY ---
Update-UI "Đang kết nối tới kho GitHub của Tuấn..." 90
$TempPyFile = Join-Path $env:TEMP "VietToolbox_QuickInstall.py"
try {
    Invoke-WebRequest -Uri $LinkPythonScript -OutFile $TempPyFile -UseBasicParsing
    if (Test-Path $TempPyFile) {
        Update-UI "Khởi động Dashboard thành công!" 100
        Start-Sleep -Seconds 1
        $Form.Close()
        
        # Chạy script Python đã tải về
        python $TempPyFile
    }
} catch {
    [System.Windows.Forms.MessageBox]::Show("Lỗi: Không thể tải được link: `n$LinkPythonScript", "Lỗi Liên Kết GitHub")
    $Form.Close()
} finally {
    # Tự động dọn rác sau khi khách đóng app
    if (Test-Path $TempPyFile) { Remove-Item $TempPyFile -Force }
}