<#
  dfwin.ps1 - diagnostics + focus helpers for the running Dwarf Fortress window.
  Uses the process MainWindowHandle because EnumWindows/IsWindowVisible are
  unreliable from this session (window-station isolation).
#>
param([string]$Action = 'info', [int]$ProcId = 0, [string]$Path = '')

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$code = @'
using System; using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int n);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,IntPtr p);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a,uint b,bool f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern IntPtr SetFocus(IntPtr h);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h,IntPtr a,int x,int y,int cx,int cy,uint f);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsZoomed(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, System.Text.StringBuilder s, int n);
  [StructLayout(LayoutKind.Sequential)] public struct R { public int L,T,Ri,B; }
}
'@
if (-not ('W' -as [type])) { Add-Type -TypeDefinition $code -Language CSharp }

function Get-DFProc {
  Get-Process | Where-Object { $_.Name -match '^Dwarf Fortress$' } | Select-Object -First 1
}

switch ($Action) {

  'info' {
    $p = Get-DFProc
    if (-not $p) { Write-Output 'DF NOT RUNNING'; exit 1 }
    $h = $p.MainWindowHandle
    $r = New-Object W+R; [void][W]::GetWindowRect($h, [ref]$r)
    $c = New-Object W+R; [void][W]::GetClientRect($h, [ref]$c)
    $sb = New-Object System.Text.StringBuilder 256
    [void][W]::GetWindowTextW($h, $sb, 256)
    $scr = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    Write-Output "pid       : $($p.Id)"
    Write-Output "handle    : $h"
    Write-Output "title     : $($sb.ToString())"
    Write-Output "windowRect: L=$($r.L) T=$($r.T) R=$($r.Ri) B=$($r.B)  [$(($r.Ri-$r.L))x$(($r.B-$r.T))]"
    Write-Output "clientRect: $(($c.Ri-$c.L))x$(($c.B-$c.T))"
    Write-Output "iconic    : $([W]::IsIconic($h))   zoomed: $([W]::IsZoomed($h))   visible: $([W]::IsWindowVisible($h))"
    Write-Output "screen    : $($scr.Width)x$($scr.Height)"
    Write-Output "foreground: $([W]::GetForegroundWindow())"
  }

  'place' {
    # force windowed 1600x900 at (40,30) and make it topmost
    $p = Get-DFProc
    if (-not $p) { Write-Output 'DF NOT RUNNING'; exit 1 }
    $h = $p.MainWindowHandle
    [void][W]::ShowWindow($h, 9)                       # SW_RESTORE
    [void][W]::SetWindowPos($h, [IntPtr](-1), 40, 30, 1600, 900, 0x0040)  # TOPMOST|SHOWWINDOW
    Start-Sleep -Milliseconds 600
    [void][W]::SetWindowPos($h, [IntPtr](-2), 40, 30, 1600, 900, 0x0040)  # NOTOPMOST
    $fg = [W]::GetForegroundWindow()
    $tgt = [W]::GetWindowThreadProcessId($h, [IntPtr]::Zero)
    $cur = [W]::GetCurrentThreadId()
    $fgt = [W]::GetWindowThreadProcessId($fg, [IntPtr]::Zero)
    [void][W]::AttachThreadInput($cur, $fgt, $true)
    [void][W]::SetForegroundWindow($h)
    [void][W]::AttachThreadInput($cur, $fgt, $false)
    Start-Sleep -Milliseconds 800
    Write-Output "placed; foreground=$([W]::GetForegroundWindow()) df=$h"
  }

  # Force DF to the foreground using the AttachThreadInput trick (beats the
  # Windows foreground lock that otherwise leaves the Cline window on top).
  'focusdf' {
    $p = Get-DFProc
    if (-not $p) { Write-Output 'DF NOT RUNNING'; exit 1 }
    $h = $p.MainWindowHandle
    [void][W]::ShowWindow($h, 9)
    [void][W]::SetWindowPos($h, [IntPtr](-1), 0, 0, 0, 0, 0x0043)
    $fg = [W]::GetForegroundWindow()
    $tgt = [W]::GetWindowThreadProcessId($h, [IntPtr]::Zero)
    $cur = [W]::GetCurrentThreadId()
    $fgt = [W]::GetWindowThreadProcessId($fg, [IntPtr]::Zero)
    [void][W]::AttachThreadInput($cur, $fgt, $true)
    [void][W]::SetForegroundWindow($h)
    [void][W]::SetFocus($h)
    [void][W]::BringWindowToTop($h)
    [void][W]::AttachThreadInput($cur, $fgt, $false)
    Start-Sleep -Milliseconds 500
    Write-Output "focused DF h=$h foreground=$([W]::GetForegroundWindow())"
  }

'minfg' {
    $fg = [W]::GetForegroundWindow()
    [void][W]::ShowWindow($fg, 6)   # SW_MINIMIZE
    Start-Sleep -Milliseconds 500
    Write-Output "minimized foreground $fg"
  }

  # Keep DF pinned above everything so absolute-coordinate clicks always land on it.
  # NOTE: never resize/move the window here - resizing a live DF 53 window crashes its renderer.
  'topmost' {
    $p = Get-DFProc
    if (-not $p) { Write-Output 'DF NOT RUNNING'; exit 1 }
    $h = $p.MainWindowHandle
    [void][W]::ShowWindow($h, 9)
    # SWP_NOSIZE|SWP_NOMOVE|SWP_SHOWWINDOW - keep geometry untouched
    [void][W]::SetWindowPos($h, [IntPtr](-1), 0, 0, 0, 0, 0x0043)
    Start-Sleep -Milliseconds 500
    $r = New-Object W+R; [void][W]::GetWindowRect($h, [ref]$r)
    Write-Output "DF TOPMOST h=$h rect=L$($r.L) T$($r.T) R$($r.Ri) B$($r.B) [$($r.Ri-$r.L)x$($r.B-$r.T)]"
  }

  'notopmost' {
    $p = Get-DFProc
    if (-not $p) { Write-Output 'DF NOT RUNNING'; exit 1 }
    [void][W]::SetWindowPos($p.MainWindowHandle, [IntPtr](-2), 0, 0, 0, 0, 0x0001)
    Write-Output 'DF no longer topmost'
  }

  # Screenshot cropped to the DF client area only.
  'snap' {
    $out = $Path
    if (-not $out) { $out = "$env:TEMP\df_snap.png" }
    $p = Get-DFProc
    if (-not $p) { Write-Output 'DF NOT RUNNING'; exit 1 }
    $h = $p.MainWindowHandle
    $r = New-Object W+R; [void][W]::GetWindowRect($h, [ref]$r)
    $x = $r.L; $y = $r.T; $ww = ($r.Ri - $r.L); $hh = ($r.B - $r.T)
    if ($ww -le 0 -or $hh -le 0) { $x = 0; $y = 0; $ww = 1920; $hh = 1080 }
    $bmp = New-Object System.Drawing.Bitmap($ww, $hh)
    $gr = [System.Drawing.Graphics]::FromImage($bmp)
    $gr.CopyFromScreen((New-Object System.Drawing.Point($x, $y)), [System.Drawing.Point]::Empty, (New-Object System.Drawing.Size($ww, $hh)))
    $gr.Dispose()
    $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Output "SNAP $out (${ww}x${hh} from $x,$y)"
  }
}