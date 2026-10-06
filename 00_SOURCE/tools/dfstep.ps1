<#
  dfstep.ps1 - one GUI step against Dwarf Fortress and return a viewable capture.
  DF is kept TOPMOST so absolute-coordinate clicks land on it without needing focus.

  -X/-Y        screen coords to click
  -Click       mouse button (left|right|middle)
  -Double      double-click
  -Keys        SendKeys string (^=CTRL %=ALT +=SHIFT); sent right after the click
  -Wait        seconds to wait before capturing (default 2)
  -Tag         filename tag; capture is written to <Tag>.png and <Tag>.jpg
#>
param(
  [int]$X = 0,
  [int]$Y = 0,
  [string]$Click = '',
  [switch]$Double,
  [string]$Keys = '',
  [int]$Wait = 2,
  [string]$Tag = 'step'
)

$tools = Split-Path -Parent $MyInvocation.MyCommand.Path
$ui  = Join-Path $tools 'dfui.ps1'
$win = Join-Path $tools 'dfwin.ps1'
$img = Join-Path $tools 'dfimg.ps1'

& $win -Action topmost | Out-Null

# Always grab real keyboard focus before sending keys - DF ignores SendKeys
# unless it is genuinely the foreground window.
if ($Keys) { & $win -Action focusdf | Out-Null }

if ($Click -or ($X -ne 0 -or $Y -ne 0)) {
  $btn = if ($Click) { $Click } else { 'left' }
  $clicks = if ($Double) { 2 } else { 1 }
  & $ui -Action click -X $X -Y $Y -Button $btn -Clicks $clicks | Out-Null
}
if ($Keys) {
  Start-Sleep -Milliseconds 250
  & $ui -Action keys -Keys $Keys | Out-Null
}

Start-Sleep -Seconds $Wait

$alive = (& $win -Action info) -match '^pid'
if (-not $alive) { Write-Output '!! DF PROCESS IS GONE !!'; exit 2 }

$png = Join-Path $tools "$Tag.png"
$jpg = Join-Path $tools "$Tag.jpg"
& $win -Action snap -Path $png | Out-Null
& $img -In $png -Out $jpg -MaxW 1100 -MaxH 1100 -Quality 60
Remove-Item $png -Force -ErrorAction SilentlyContinue