# Cấu hình danh sách thư viện cần cài
$PythonLibraries = @("customtkinter")
$Title = "VIETTOOLBOX - ĐANG CHUẨN BỊ THƯ VIỆN LÀM VIỆC"

# Tạo giao diện WinForms
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$Form = New-Object System.Windows.Forms.Form
$Form.Text = "VietToolbox Bootstrapper"
$Form.Size = New-Object System.Drawing.Size(450, 180)
$Form.StartPosition = "CenterScreen"
$Form.FormBorderStyle = "FixedDialog"
$Form.MaximizeBox = $false
$Form.BackColor = [System.Drawing.Color]::FromArgb(30, 30, 30) # Dark Mode

$Label = New-Object System.Windows.Forms.Label
$Label.Text = $Title
$Label.Font = New-Object System.Drawing.Font("Arial", 11, [System.Drawing.FontStyle]::Bold)
$Label.ForeColor = [System.Drawing.Color]::White
$Label.AutoSize = $true
$Label.Location = New-Object System.Drawing.Point(20, 20)
$Form.Controls.Add($Label)

$StatusLabel = New-Object System.Windows.Forms.Label
$StatusLabel.Text = "Đang kiểm tra môi trường hệ thống..."
$StatusLabel.ForeColor = [System.Drawing.Color]::LightGray
$StatusLabel.AutoSize = $true
$StatusLabel.Location = New-Object System.Drawing.Point(20, 50)
$Form.Controls.Add($StatusLabel)

$ProgressBar = New-Object System.Windows.Forms.ProgressBar
$ProgressBar.Location = New-Object System.Drawing.Point(20, 80)
$ProgressBar.Size = New-Object System.Drawing.Size(400, 25)
$ProgressBar.Style = "Continuous"
$Form.Controls.Add($ProgressBar)

# Hiển thị Form và xử lý logic
$Form.Show()
$Form.Refresh()

function Update-UI ($msg, $val) {
    $StatusLabel.Text = $msg
    $ProgressBar.Value = $val
    $Form.Refresh()
    Start-Sleep -Milliseconds 500
}

# Bước 1: Kiểm tra Python
Update-UI "Đang kiểm tra cài đặt Python..." 20
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Update-UI "Python chưa có. Đang tải và cài đặt Python (v3.12)..." 40
    # Tự động tải Python từ web chính thức (silent install)
    $url = "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
    $out = "$env:TEMP\python_installer.exe"
    Invoke-WebRequest -Uri $url -OutFile $out
    Start-Process -FilePath $out -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
    Remove-Item $out
}

# Bước 2: Nâng cấp PIP
Update-UI "Đang tối ưu trình quản lý gói (PIP)..." 60
python -m pip install --upgrade pip --quiet

# Bước 3: Cài đặt thư viện theo yêu cầu
$step = 40 / $PythonLibraries.Count
$currentVal = 60
foreach ($lib in $PythonLibraries) {
    Update-UI "Đang nạp thư viện: $lib ..." $currentVal
    python -m pip install $lib --quiet
    $currentVal += $step
}

# Bước 4: Hoàn tất và khởi chạy script chính
Update-UI "Hoàn tất! Đang khởi động bảng điều khiển chính..." 100
Start-Sleep -Seconds 1
$Form.Close()

# Chạy file script Python của ông
if (Test-Path "quickinstall.py") {
    python "quickinstall.py"
} else {
    [System.Windows.Forms.MessageBox]::Show("Không tìm thấy file quickinstall.py trong thư mục hiện tại!", "Lỗi")
}