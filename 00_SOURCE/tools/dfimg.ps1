<#
  dfimg.ps1 - downscale / crop a PNG so it can be inspected visually.
  Use -MaxW to keep within viewer limits; coordinates read off a scaled image
  are multiplied back by (OrigW / ScaledW) before being used for real clicks.
#>
param(
  [Parameter(Mandatory=$true)][string]$In,
  [Parameter(Mandatory=$true)][string]$Out,
  [int]$MaxW = 1400,
  [int]$MaxH = 1400,
  [int]$CropX = -1,
  [int]$CropY = -1,
  [int]$CropW = -1,
  [int]$CropH = -1,
  [int]$Quality = 72
)

Add-Type -AssemblyName System.Drawing

$src = [System.Drawing.Image]::FromFile($In)
try {
  $sw = $src.Width; $sh = $src.Height
  $sx = 0; $sy = 0; $cw = $sw; $ch = $sh
  if ($CropX -ge 0 -and $CropW -gt 0) { $sx = $CropX; $sy = $CropY; $cw = $CropW; $ch = $CropH }

  $scale = [Math]::Min($MaxW / $cw, $MaxH / $ch)
  if ($scale -gt 1.0) { $scale = 1.0 }
  $dw = [int]($cw * $scale); $dh = [int]($ch * $scale)
  if ($dw -lt 1) { $dw = 1 }; if ($dh -lt 1) { $dh = 1 }

  $bmp = New-Object System.Drawing.Bitmap($dw, $dh)
  $gr = [System.Drawing.Graphics]::FromImage($bmp)
  $gr.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $gr.DrawImage($src, (New-Object System.Drawing.Rectangle 0, 0, $dw, $dh),
                (New-Object System.Drawing.Rectangle $sx, $sy, $cw, $ch),
                [System.Drawing.GraphicsUnit]::Pixel)
  $gr.Dispose()
  # JPEG keeps these full-screen DF captures small enough to view.
  $enc = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
  $par = New-Object System.Drawing.Imaging.EncoderParameters(1)
  $par.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]$Quality)
  $bmp.Save($Out, $enc, $par)
  $bmp.Dispose()
  Write-Output "$Out  ${dw}x${dh}  scale=$([Math]::Round($scale,4))  source=${sw}x${sh} crop=@($sx,$sy) ${cw}x${ch}"
  Write-Output "click_x_on_output * $([Math]::Round($cw/$dw,4)) + $sx = real_x ; click_y * $([Math]::Round($ch/$dh,4)) + $sy = real_y"
}
finally { $src.Dispose() }