; === Shooting App Installer Script - Tối ưu hóa ===

#define MyAppName "Tập Luyện K54"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "LTSoftware"
#define MyAppExeName "TrainingK54.exe"
#define MyAppIconName "assets\app_icon.ico" 
#define MyOutputFolder "dist\TrainingK54"

[Setup]
AppId={{C194D481-22C5-42E1-975E-538F36C58925}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
PrivilegesRequired=admin
OutputDir=installers
OutputBaseFilename=setup-{#MyAppName}-{#MyAppVersion}
SetupIconFile={#MyAppIconName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; -- TỐI ƯU 1: Giao diện Tiếng Việt cho trình cài đặt --
[Languages]
Name: "vietnamese"; MessagesFile: "compiler:Languages\Vietnamese.isl"

; -- TỐI ƯU 2: Thêm trang Chào mừng và Xác nhận trước khi cài --
[Setup]
DisableWelcomePage=no
DisableReadyPage=no

; -- TỐI ƯU 3: Thêm hình ảnh thương hiệu cho trình cài đặt --
;
(tổng hợp) Tạo 2 file ảnh và đặt vào thư mục assets:
;
WizardImageFile=assets\wizard_large.bmp  ; Kích thước 554x314 pixels
;
WizardSmallImageFile=assets\wizard_small.bmp ; Kích thước 164x314 pixels

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
; Lấy tất cả file từ thư mục build của PyInstaller
Source: "{#MyOutputFolder}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; -- TỐI ƯU 4: Gỡ cài đặt sạch sẽ, hỏi người dùng có muốn xóa dữ liệu không --
[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\TapLuyenK54"

; -- TỐI ƯU 5: Kiểm tra xem máy người dùng đã có Visual C++ Redistributable chưa --
[Code]
var
  VCRedistMissing: Boolean;

function IsVCppRedistInstalled(): Boolean;
var
  RegKey: string;
begin
  // Kiểm tra registry key cho bản Visual C++ 2015-2022 Redistributable (x64)
  RegKey := 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64';
  Result := RegKeyExists(HKLM, RegKey);
end;

function InitializeSetup(): Boolean;
begin
  if not IsVCppRedistInstalled() then
  begin
    VCRedistMissing := True;
    MsgBox('Để ứng dụng hoạt động, máy tính của bạn cần cài đặt "Microsoft Visual C++ Redistributable".'#13#13'Trình cài đặt sẽ mở trang tải về cho bạn. Vui lòng tải và cài đặt bản "X64".', mbInformation, MB_OK);
    // Mở trang tải về của Microsoft
    ShellExec('open', 'https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist', '', '', SW_SHOWNORMAL, ewNoWait, VCRedistMissing);
    Result := False; // Hủy cài đặt để người dùng cài đặt VC++ trước
  end
  else
  begin
    VCRedistMissing := False;
    Result := True; // Tiếp tục cài đặt
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssDone) and VCRedistMissing then
  begin
    // Một lần nữa nhắc người dùng sau khi trang tải về đã mở
    MsgBox('Vui lòng cài đặt "Visual C++ Redistributable" từ trang web vừa mở, sau đó chạy lại file cài đặt này.', mbInformation, MB_OK);
  end;
end;