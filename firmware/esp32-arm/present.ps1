Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# one-click presenter. run sends arm, then smooth. stop sends x.
# the button handler keeps the motion inline. a background worker cannot see script functions.

$script:port = $null
$script:gate = New-Object System.Object
$script:busy = $false
$script:statusText = "Ready"

function global:Set-Status([string]$text) {
  $script:statusText = $text
}

function global:Send-Line([string]$text) {
  [System.Threading.Monitor]::Enter($script:gate)
  try {
    if ($script:port -and $script:port.IsOpen) { $script:port.WriteLine($text) }
  } finally {
    [System.Threading.Monitor]::Exit($script:gate)
  }
}

function global:Read-Chunk {
  [System.Threading.Monitor]::Enter($script:gate)
  try {
    if ($script:port -and $script:port.IsOpen) { return $script:port.ReadExisting() }
    return ""
  } catch { return "" } finally {
    [System.Threading.Monitor]::Exit($script:gate)
  }
}

function global:Close-Port {
  [System.Threading.Monitor]::Enter($script:gate)
  try {
    if ($script:port) {
      if ($script:port.IsOpen) { $script:port.Close() }
      $script:port.Dispose()
      $script:port = $null
    }
  } catch {} finally {
    [System.Threading.Monitor]::Exit($script:gate)
  }
}

function global:Start-Motion {
  try {
    $names = [System.IO.Ports.SerialPort]::GetPortNames()
    $name = $null
    if ($names -contains "COM8") { $name = "COM8" }
    elseif ($names.Count -gt 0) { $name = $names[0] }
    if (-not $name) {
      Set-Status "ESP32 not plugged in"
      return
    }
    Set-Status "Connecting $name"
    Close-Port
    $opened = New-Object System.IO.Ports.SerialPort $name,115200,"None",8,"one"
    $opened.NewLine = "`n"
    $opened.ReadTimeout = 200
    $opened.DtrEnable = $false
    $opened.RtsEnable = $false
    $opened.Open()
    $script:port = $opened
    Start-Sleep -Milliseconds 150
    Send-Line "x"
    Start-Sleep -Milliseconds 200
    Send-Line "enc"
    $enc = ""
    $deadline = (Get-Date).AddSeconds(2)
    while ((Get-Date) -lt $deadline) {
      if ($script:cancel) { return }
      $enc += Read-Chunk
      if ($enc -match "el raw") { break }
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 40
    }
    Set-Status "Arming"
    Send-Line "arm"
    $armed = ""
    $deadline = (Get-Date).AddSeconds(6)
    while ((Get-Date) -lt $deadline) {
      if ($script:cancel) { return }
      $armed += Read-Chunk
      if ($armed -match "armed") { break }
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 40
    }
    if ($armed -notmatch "armed") {
      Set-Status "ESC did not arm"
      return
    }
    Send-Line "shloop"
    Set-Status "Shoulder 3s up, 3s base"
    $carry = ""
    $deadline = (Get-Date).AddSeconds(75)
    while ((Get-Date) -lt $deadline) {
      if ($script:cancel) { return }
      $piece = Read-Chunk
      if ($piece.Length -gt 0) {
        $carry += $piece
        $parts = $carry -split "`n", -1
        if ($carry.EndsWith("`n")) { $carry = "" }
        else {
          $carry = $parts[$parts.Length - 1]
          if ($parts.Length -gt 0) { $parts = $parts[0..($parts.Length - 2)] }
        }
        foreach ($line in $parts) {
          $line = $line.Trim()
          if ($line -match "^shoulder |^stopped |^CUT ") { Set-Status $line }
          if ($line -match "shoulder done") {
            Set-Status "Done. Shoulder is at base."
            return
          }
          if ($line -match "^CUT |^stopped ") { return }
        }
      }
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 30
    }
    Send-Line "x"
    Set-Status "Stopped on timeout"
  } catch {
    Set-Status $_.Exception.Message
  } finally {
    $script:busy = $false
  }
}

function global:Start-Continuous {
  try {
    $names = [System.IO.Ports.SerialPort]::GetPortNames()
    $name = $null
    if ($names -contains "COM8") { $name = "COM8" }
    elseif ($names.Count -gt 0) { $name = $names[0] }
    if (-not $name) {
      Set-Status "ESP32 not plugged in"
      return
    }
    Set-Status "Connecting $name"
    Close-Port
    $opened = New-Object System.IO.Ports.SerialPort $name,115200,"None",8,"one"
    $opened.NewLine = "`n"
    $opened.ReadTimeout = 200
    $opened.DtrEnable = $false
    $opened.RtsEnable = $false
    $opened.Open()
    $script:port = $opened
    Start-Sleep -Milliseconds 150
    Send-Line "x"
    Start-Sleep -Milliseconds 200
    Set-Status "Arming"
    Send-Line "arm"
    $armed = ""
    $deadline = (Get-Date).AddSeconds(6)
    while ((Get-Date) -lt $deadline) {
      if ($script:cancel) { return }
      $armed += Read-Chunk
      if ($armed -match "armed") { break }
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 40
    }
    if ($armed -notmatch "armed") {
      Set-Status "ESC did not arm"
      return
    }
    Send-Line "shcont"
    Set-Status "Shoulder running. Press Stop."
    while (-not $script:cancel) {
      $piece = Read-Chunk
      if ($piece -match "shoulder up") { Set-Status "Shoulder up" }
      if ($piece -match "shoulder base") { Set-Status "Shoulder base" }
      if ($piece -match "CUT ") { Set-Status "Stopped"; return }
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 30
    }
  } catch {
    Set-Status $_.Exception.Message
  } finally {
    $script:busy = $false
  }
}

function global:Start-Both {
  try {
    $names = [System.IO.Ports.SerialPort]::GetPortNames()
    $name = $null
    if ($names -contains "COM8") { $name = "COM8" }
    elseif ($names.Count -gt 0) { $name = $names[0] }
    if (-not $name) {
      Set-Status "ESP32 not plugged in"
      return
    }
    Set-Status "Connecting $name"
    Close-Port
    $opened = New-Object System.IO.Ports.SerialPort $name,115200,"None",8,"one"
    $opened.NewLine = "`n"
    $opened.ReadTimeout = 200
    $opened.DtrEnable = $false
    $opened.RtsEnable = $false
    $opened.Open()
    $script:port = $opened
    Start-Sleep -Milliseconds 150
    Send-Line "x"
    Start-Sleep -Milliseconds 200
    Send-Line "enc"
    $enc = ""
    $deadline = (Get-Date).AddSeconds(2)
    while ((Get-Date) -lt $deadline) {
      if ($script:cancel) { return }
      $enc += Read-Chunk
      if ($enc -match "el raw") { break }
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 40
    }
    if ($enc -notmatch "el raw ([0-9.]+) ok") {
      Set-Status "Elbow encoder is not talking"
      return
    }
    $raw = [double]$Matches[1]
    if ($raw -gt 40 -and $raw -lt 320) {
      Set-Status "Put the elbow down first"
      return
    }
    Set-Status "Arming"
    Send-Line "arm"
    $armed = ""
    $deadline = (Get-Date).AddSeconds(6)
    while ((Get-Date) -lt $deadline) {
      if ($script:cancel) { return }
      $armed += Read-Chunk
      if ($armed -match "armed") { break }
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 40
    }
    if ($armed -notmatch "armed") {
      Set-Status "ESC did not arm"
      return
    }
    Send-Line "both"
    Set-Status "Elbow 40 to 60, shoulder looping"
    $carry = ""
    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $deadline) {
      if ($script:cancel) { return }
      $piece = Read-Chunk
      if ($piece.Length -gt 0) {
        $carry += $piece
        $parts = $carry -split "`n", -1
        if ($carry.EndsWith("`n")) { $carry = "" }
        else {
          $carry = $parts[$parts.Length - 1]
          if ($parts.Length -gt 0) { $parts = $parts[0..($parts.Length - 2)] }
        }
        foreach ($line in $parts) {
          $line = $line.Trim()
          if ($line -match "^elbow |^shoulder |^both |^hold |^stopped |^CUT ") { Set-Status $line }
          if ($line -match "both done") {
            Set-Status "Done. Elbow is near 40."
            return
          }
          if ($line -match "^CUT |^stopped ") { return }
        }
      }
      [System.Windows.Forms.Application]::DoEvents()
      Start-Sleep -Milliseconds 30
    }
    Send-Line "x"
    Set-Status "Stopped on timeout"
  } catch {
    Set-Status $_.Exception.Message
  } finally {
    $script:busy = $false
  }
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Prime arm"
$form.Size = New-Object System.Drawing.Size(560, 640)
$form.StartPosition = "CenterScreen"
$form.BackColor = [System.Drawing.Color]::FromArgb(16, 16, 16)
$form.ForeColor = [System.Drawing.Color]::White
$form.Font = New-Object System.Drawing.Font("Segoe UI", 14)
$form.TopMost = $true

$title = New-Object System.Windows.Forms.Label
$title.Text = "Run the arm"
$title.AutoSize = $true
$title.Font = New-Object System.Drawing.Font("Segoe UI", 28, [System.Drawing.FontStyle]::Bold)
$title.Location = New-Object System.Drawing.Point(28, 24)
$form.Controls.Add($title)

$hint = New-Object System.Windows.Forms.Label
$hint.Text = "12 V on. Elbow down before Run both."
$hint.AutoSize = $true
$hint.ForeColor = [System.Drawing.Color]::FromArgb(180, 180, 180)
$hint.Location = New-Object System.Drawing.Point(32, 84)
$form.Controls.Add($hint)

$status = New-Object System.Windows.Forms.Label
$status.Text = "Ready"
$status.AutoSize = $false
$status.Size = New-Object System.Drawing.Size(490, 36)
$status.Location = New-Object System.Drawing.Point(32, 124)
$form.Controls.Add($status)

$run = New-Object System.Windows.Forms.Button
$run.Text = "RUN"
$run.Size = New-Object System.Drawing.Size(490, 68)
$run.Location = New-Object System.Drawing.Point(28, 160)
$run.FlatStyle = "Flat"
$run.BackColor = [System.Drawing.Color]::FromArgb(22, 140, 70)
$run.ForeColor = [System.Drawing.Color]::White
$run.Font = New-Object System.Drawing.Font("Segoe UI", 32, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($run)
$form.AcceptButton = $run

$cont = New-Object System.Windows.Forms.Button
$cont.Text = "RUN FOREVER"
$cont.Size = New-Object System.Drawing.Size(490, 68)
$cont.Location = New-Object System.Drawing.Point(28, 236)
$cont.FlatStyle = "Flat"
$cont.BackColor = [System.Drawing.Color]::FromArgb(120, 84, 18)
$cont.ForeColor = [System.Drawing.Color]::White
$cont.Font = New-Object System.Drawing.Font("Segoe UI", 26, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($cont)

$both = New-Object System.Windows.Forms.Button
$both.Text = "RUN BOTH"
$both.Size = New-Object System.Drawing.Size(490, 68)
$both.Location = New-Object System.Drawing.Point(28, 312)
$both.FlatStyle = "Flat"
$both.BackColor = [System.Drawing.Color]::FromArgb(25, 90, 170)
$both.ForeColor = [System.Drawing.Color]::White
$both.Font = New-Object System.Drawing.Font("Segoe UI", 28, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($both)

$stop = New-Object System.Windows.Forms.Button
$stop.Text = "STOP"
$stop.Size = New-Object System.Drawing.Size(490, 68)
$stop.Location = New-Object System.Drawing.Point(28, 388)
$stop.FlatStyle = "Flat"
$stop.BackColor = [System.Drawing.Color]::FromArgb(170, 32, 32)
$stop.ForeColor = [System.Drawing.Color]::White
$stop.Font = New-Object System.Drawing.Font("Segoe UI", 28, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($stop)

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 80
$timer.Add_Tick({
  $status.Text = $script:statusText
  $run.Enabled = -not $script:busy
  $cont.Enabled = -not $script:busy
  $both.Enabled = -not $script:busy
})
$timer.Start()

$run.Add_Click({
  if ($script:busy) { return }
  $script:busy = $true
  $script:cancel = $false
  $script:statusText = "Starting"
  Start-Motion
})

$cont.Add_Click({
  if ($script:busy) { return }
  $script:busy = $true
  $script:cancel = $false
  $script:statusText = "Starting"
  Start-Continuous
})

$both.Add_Click({
  if ($script:busy) { return }
  $script:busy = $true
  $script:cancel = $false
  $script:statusText = "Starting both"
  Start-Both
})

$stop.Add_Click({
  $script:cancel = $true
  try { Send-Line "x" } catch {}
  $script:statusText = "Stopped"
})

$form.Add_FormClosing({
  try { Send-Line "x" } catch {}
  Close-Port
  $timer.Stop()
})

[void]$form.ShowDialog()
