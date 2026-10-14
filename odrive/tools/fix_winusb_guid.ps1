# registers a DeviceInterfaceGUID for the odrive v3.x native (winusb) interface.
# odrive fw 0.5.x asks windows for winusb via ms os descriptors but omits the guid,
# so libusb cannot find a device path and fails with LIBUSB_ERROR_NOT_FOUND.
# run as administrator. safe to re-run.

$ErrorActionPreference = 'Stop'
$guid = '{3c2cf4a2-6f0e-4d51-9a0b-0d32a5e10db1}'
$root = 'HKLM:\SYSTEM\CurrentControlSet\Enum\USB\VID_1209&PID_0D32&MI_02'

if (-not (Test-Path $root)) { Write-Output 'no odrive native interface found in registry'; exit 1 }

# add the guid to every known instance of the native interface
Get-ChildItem $root | ForEach-Object {
    $params = Join-Path $_.PSPath 'Device Parameters'
    New-ItemProperty -Path $params -Name 'DeviceInterfaceGUIDs' -PropertyType MultiString -Value @($guid) -Force | Out-Null
    Write-Output ("guid set: " + $_.PSChildName)
}

# restart the composite parent so the driver re-reads the guid
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB\\VID_1209&PID_0D32\\' } | ForEach-Object {
    pnputil /restart-device $_.InstanceId | Out-Null
    Write-Output ("restarted: " + $_.InstanceId)
}
