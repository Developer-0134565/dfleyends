<#
  dfui.ps1 - GUI automation helper for driving Dwarf Fortress 53.16 + DFHack.
  Read-only w.r.t. the save: only sends input / takes screenshots.

  Actions:
    shot                 - capture screen to -Path
    windows              - list visible top-level windows (title, pid, handle)
    focus   -TitleLike   - bring window whose title matches to foreground
    click   -X -Y [-Button left|right] [-Clicks n]
    keys    -Keys        - SendKeys string (^ = CTRL, % = ALT, + = SHIFT)
    wait    -TimeoutSec  - block until a matching window appears
    proc                  - list Dwarf Fortress / DFHack processes
#>
param(
  [string]$Action = 'shot',
  [string]$Path = "$env:TEMP\dfch_shot.png",
  [int]$X = 0,
  [int]$Y = 0,
  [string]$Keys = '',
  [string]$TitleLike = '',
  [int]$TimeoutSec = 60,
  [int]$Clicks = 1,
  [string]$Button = 'left'
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$src = @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public class U32 {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, int e);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
  public const uint LD=0x02, LU=0x04, RD=0x08, RU=0x10, MOVE=0x01, WHEEL=0x0800;
}
'@
if (-not ('U32' -as [type])) { Add-Type -TypeDefinition $src -Language CSharp }

function Get-Windows {
  if (-not ('WinList' -as [type])) {
    $src2 = @'
using System;
using System.Collections.Generic;
using System.Text;
using System.Runtime.InteropServices;
public class WinList {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
  public static string[] List() {
    var res = new List<string>();
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      if (!IsWindowVisible(h)) return true;
      int len = GetWindowText(h, null, 0);
      if (len <= 0) return true;
      var sb = new StringBuilder(len + 2);
      GetWindowText(h, sb, sb.Capacity);
      uint pid; GetWindowThreadProcessId(h, out pid);
      RECT r; GetWindowRect(h, out r);
      string t = sb.ToString().Replace("|", "/");
      res.Add(t + "|" + pid + "|" + h.ToInt64() + "|" + r.Left + "," + r.Top + "," +
             (r.Right - r.Left) + "," + (r.Bottom - r.Top));
      return true;
    }, IntPtr.Zero);
    return res.ToArray();
  }
  public static IntPtr Find(string like) {
    IntPtr found = IntPtr.Zero;
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      if (!IsWindowVisible(h)) return true;
      int len = GetWindowText(h, null, 0);
      if (len <= 0) return true;
      var sb = new StringBuilder(len + 2);
      GetWindowText(h, sb, sb.Capacity);
      if (sb.ToString().IndexOf(like, StringComparison.OrdinalIgnoreCase) >= 0) { found = h; return false; }
      return true;
    }, IntPtr.Zero);
    return found;
  }
}
'@
    Add-Type -TypeDefinition $src2 -Language CSharp
  }
  foreach ($s in [WinList]::List()) {
    $p = $s -split '\|'
    [PSCustomObject]@{
      Title = $p[0]; Pid = [int]$p[1]; Handle = [IntPtr][int64]$p[2]
      X = [int]($p[3] -split ',')[0]; Y = [int]($p[3] -split ',')[1]
      W = [int]($p[3] -split ',')[2]; H = [int]($p[3] -split ',')[3]
    }
  }
}

function Find-Win([string]$like) {
  if ([string]::IsNullOrEmpty($like)) { return $null }
  foreach ($w in Get-Windows) {
    if ($w.Title -like "*$like*") { return $w }
  }
  return $null
}

switch ($Action) {

  'windows' {
    Get-Windows | Sort-Object Title | Format-Table -AutoSize Title, Pid, X, Y, W, H | Out-String -Width 200 | Write-Output
  }

  'proc' {
    Get-Process | Where-Object { $_.Name -match 'Dwarf|dfhack|launchdf|lua' } |
      Select-Object Id, Name, MainWindowTitle | Format-Table -AutoSize | Out-String -Width 200 | Write-Output
  }

  'focus' {
    $w = Find-Win $TitleLike
    if (-not $w) { Write-Output "NOT FOUND: $TitleLike"; exit 1 }
    [void][U32]::ShowWindow($w.Handle, 9)   # SW_RESTORE
    [void][U32]::SetForegroundWindow($w.Handle)
    Start-Sleep -Milliseconds 400
    Write-Output "FOCUSED: $($w.Title)"
  }

  'wait' {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
      $w = Find-Win $TitleLike
      if ($w) { Write-Output "FOUND after $([int]$sw.Elapsed.TotalSeconds)s: $($w.Title)"; exit 0 }
      Start-Sleep -Milliseconds 500
    }
    Write-Output "TIMEOUT ${TimeoutSec}s waiting for: $TitleLike"
    exit 1
  }

  'click' {
    $w = Find-Win $TitleLike
    if ($w) { [void][U32]::SetForegroundWindow($w.Handle); Start-Sleep -Milliseconds 250 }
    [void][U32]::SetCursorPos($X, $Y)
    Start-Sleep -Milliseconds 180
    $dn = if ($Button -eq 'right') { [U32]::RD } else { [U32]::LD }
    $up = if ($Button -eq 'right') { [U32]::RU } else { [U32]::LU }
    for ($i = 0; $i -lt $Clicks; $i++) {
      [U32]::mouse_event($dn, 0, 0, 0, 0)
      Start-Sleep -Milliseconds 60
      [U32]::mouse_event($up, 0, 0, 0, 0)
      if ($i -lt $Clicks - 1) { Start-Sleep -Milliseconds 110 }
    }
    Start-Sleep -Milliseconds 350
    Write-Output "CLICKED $Clicks x ($Button) at $X,$Y"
  }

  'keys' {
    $w = Find-Win $TitleLike
    if ($w) { [void][U32]::SetForegroundWindow($w.Handle); Start-Sleep -Milliseconds 300 }
    [System.Windows.Forms.SendKeys]::SendWait($Keys)
    Start-Sleep -Milliseconds 350
    Write-Output "SENT: $Keys"
  }

  'shot' {
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
    $gr = [System.Drawing.Graphics]::FromImage($bmp)
    $gr.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    $gr.Dispose()
    $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Output "SHOT: $Path"
  }
}