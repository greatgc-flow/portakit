# Native adapter. Windows PowerShell 2.0 / .NET Framework 2.0 compatible.
# Reflection.Emit uses AssemblyBuilderAccess.Run: this adapter writes no files.
# All geometry is an OUTER rectangle in the current caller's DPI context.
# ProcessStart is the exact creation FILETIME, encoded as 16 uppercase hex digits.

function Get-AegisNativeField {
    param($Object, [string]$Name, $Default)
    if ($null -eq $Object) { return $Default }
    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) { return $Object[$Name] }
    } else {
        $property = $Object.PSObject.Properties[$Name]
        if ($null -ne $property) { return $property.Value }
    }
    return $Default
}

function Test-AegisNativeWindows {
    return ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT)
}

function Initialize-AegisNative {
    # Change this version if any emitted method or field changes. The API's own
    # assembly resolves its structs, so an unrelated old dynamic assembly cannot
    # supply a struct with the same short name.
    $prefix = 'Aegis_PS2_20261113_Native6'
    $cached = Get-Variable -Name AegisNativeCacheV4 -Scope Global -ErrorAction SilentlyContinue
    if ($null -ne $cached -and $cached.Value -is [hashtable]) {
        $cache = $cached.Value
        if ($cache.ContainsKey('Prefix') -and $cache.Prefix -eq $prefix -and $cache.ContainsKey('Api') -and $cache.Api -is [type] -and $cache.ContainsKey('Types') -and $cache.Types -is [hashtable]) {
            $script:AegisNativeApiType = $cache.Api
            $script:AegisNativeTypes = $cache.Types
            return
        }
    }
    $api = ($prefix + '.Api') -as [type]
    if ($null -eq $api) {
        $assemblyName = New-Object System.Reflection.AssemblyName ($prefix + '_' + [Guid]::NewGuid().ToString('N'))
        $assemblyArguments = [object[]]@($assemblyName.PSObject.BaseObject, [System.Reflection.Emit.AssemblyBuilderAccess]::Run)
        $assemblySignature = [type[]]@([System.Reflection.AssemblyName], [System.Reflection.Emit.AssemblyBuilderAccess])
        $factory = [AppDomain].GetMethod('DefineDynamicAssembly', $assemblySignature)
        if ($null -ne $factory) {
            $assembly = $factory.Invoke([AppDomain]::CurrentDomain, $assemblyArguments)
        } else {
            # This branch permits metadata-only tests under current PowerShell.
            # Windows PowerShell 2.0 takes the AppDomain branch above.
            $factory = [System.Reflection.Emit.AssemblyBuilder].GetMethod('DefineDynamicAssembly', $assemblySignature)
            if ($null -eq $factory) { throw 'DynamicAssemblyFactoryUnavailable' }
            $assembly = $factory.Invoke($null, $assemblyArguments)
        }
        $module = $assembly.DefineDynamicModule($prefix + '.Module')
        $types = @{}
        $definitions = @(
            @('Rect', [int], @('Left','Top','Right','Bottom')),
            @('Point', [int], @('X','Y')),
            @('MinMaxInfo', [int], @('ReservedX','ReservedY','MaxSizeX','MaxSizeY','MaxPositionX','MaxPositionY','MinTrackX','MinTrackY','MaxTrackX','MaxTrackY')),
            @('Placement', [int], @('length','flags','showCmd','minX','minY','maxX','maxY','nLeft','nTop','nRight','nBottom')),
            @('MonitorInfo', [int], @('Size','MonitorLeft','MonitorTop','MonitorRight','MonitorBottom','WorkLeft','WorkTop','WorkRight','WorkBottom','Flags')),
            @('FileTime', [uint32], @('Low','High'))
        )
        foreach ($definition in $definitions) {
            $builder = $module.DefineType(($prefix + '.' + $definition[0]), [System.Reflection.TypeAttributes]'Public,SequentialLayout,Sealed', [ValueType])
            foreach ($field in $definition[2]) {
                [void]$builder.DefineField($field, $definition[1], [System.Reflection.FieldAttributes]::Public)
            }
            $types[$definition[0]] = $builder.CreateType()
        }

        $delegateBuilder = $module.DefineType(($prefix + '.EnumCallback'), [System.Reflection.TypeAttributes]'Public,Sealed', [MulticastDelegate])
        $constructor = $delegateBuilder.DefineConstructor([System.Reflection.MethodAttributes]'RTSpecialName,HideBySig,Public', [System.Reflection.CallingConventions]::Standard, [type[]]@([object],[IntPtr]))
        $constructor.SetImplementationFlags([System.Reflection.MethodImplAttributes]'Runtime,Managed')
        $invoke = $delegateBuilder.DefineMethod('Invoke', [System.Reflection.MethodAttributes]'Public,HideBySig,NewSlot,Virtual', [bool], [type[]]@([IntPtr],[IntPtr]))
        $invoke.SetImplementationFlags([System.Reflection.MethodImplAttributes]'Runtime,Managed')
        $unmanagedConstructor = [System.Runtime.InteropServices.UnmanagedFunctionPointerAttribute].GetConstructor([type[]]@([System.Runtime.InteropServices.CallingConvention]))
        $unmanagedAttribute = New-Object System.Reflection.Emit.CustomAttributeBuilder ($unmanagedConstructor, [object[]]@([System.Runtime.InteropServices.CallingConvention]::Winapi))
        $delegateBuilder.SetCustomAttribute($unmanagedAttribute)
        $types['EnumCallback'] = $delegateBuilder.CreateType()

        $monitorDelegate = $module.DefineType(($prefix + '.MonitorCallback'), [System.Reflection.TypeAttributes]'Public,Sealed', [MulticastDelegate])
        $monitorConstructor = $monitorDelegate.DefineConstructor([System.Reflection.MethodAttributes]'RTSpecialName,HideBySig,Public', [System.Reflection.CallingConventions]::Standard, [type[]]@([object],[IntPtr]))
        $monitorConstructor.SetImplementationFlags([System.Reflection.MethodImplAttributes]'Runtime,Managed')
        $monitorInvoke = $monitorDelegate.DefineMethod('Invoke', [System.Reflection.MethodAttributes]'Public,HideBySig,NewSlot,Virtual', [bool], [type[]]@([IntPtr],[IntPtr],[IntPtr],[IntPtr]))
        $monitorInvoke.SetImplementationFlags([System.Reflection.MethodImplAttributes]'Runtime,Managed')
        $monitorDelegate.SetCustomAttribute($unmanagedAttribute)
        $types['MonitorCallback'] = $monitorDelegate.CreateType()

        $apiBuilder = $module.DefineType(($prefix + '.Api'), [System.Reflection.TypeAttributes]'Public,Abstract,Sealed')
        $rectRef = $types.Rect.MakeByRefType()
        $placementRef = $types.Placement.MakeByRefType()
        $fileTimeRef = $types.FileTime.MakeByRefType()
        $methods = @(
            @('kernel32.dll','SetLastError',[void],[type[]]@([uint32]),$false),
            @('kernel32.dll','GetCurrentProcessId',[uint32],[type[]]@(),$false),
            @('kernel32.dll','GetCurrentThreadId',[uint32],[type[]]@(),$false),
            @('kernel32.dll','ProcessIdToSessionId',[bool],[type[]]@([uint32],[uint32].MakeByRefType()),$true),
            @('kernel32.dll','GetConsoleWindow',[IntPtr],[type[]]@(),$false),
            @('kernel32.dll','OpenProcess',[IntPtr],[type[]]@([uint32],[bool],[uint32]),$true),
            @('kernel32.dll','CloseHandle',[bool],[type[]]@([IntPtr]),$true),
            @('kernel32.dll','GetProcessTimes',[bool],[type[]]@([IntPtr],$fileTimeRef,$fileTimeRef,$fileTimeRef,$fileTimeRef),$true),
            @('kernel32.dll','QueryFullProcessImageNameW',[bool],[type[]]@([IntPtr],[uint32],[System.Text.StringBuilder],[uint32].MakeByRefType()),$true),
            @('user32.dll','SetThreadDpiAwarenessContext',[IntPtr],[type[]]@([IntPtr]),$true),
            @('user32.dll','GetThreadDpiAwarenessContext',[IntPtr],[type[]]@(),$false),
            @('user32.dll','GetAwarenessFromDpiAwarenessContext',[int],[type[]]@([IntPtr]),$false),
            @('user32.dll','AreDpiAwarenessContextsEqual',[bool],[type[]]@([IntPtr],[IntPtr]),$false),
            @('shcore.dll','GetProcessDpiAwareness',[int],[type[]]@([IntPtr],[int].MakeByRefType()),$false),
            @('user32.dll','IsProcessDPIAware',[bool],[type[]]@(),$false),
            @('user32.dll','GetDC',[IntPtr],[type[]]@([IntPtr]),$false),
            @('user32.dll','ReleaseDC',[int],[type[]]@([IntPtr],[IntPtr]),$false),
            @('gdi32.dll','GetDeviceCaps',[int],[type[]]@([IntPtr],[int]),$false),
            @('user32.dll','GetProcessWindowStation',[IntPtr],[type[]]@(),$true),
            @('user32.dll','GetThreadDesktop',[IntPtr],[type[]]@([uint32]),$true),
            @('user32.dll','OpenInputDesktop',[IntPtr],[type[]]@([uint32],[bool],[uint32]),$true),
            @('user32.dll','CloseDesktop',[bool],[type[]]@([IntPtr]),$true),
            @('user32.dll','GetUserObjectInformationW',[bool],[type[]]@([IntPtr],[int],[System.Text.StringBuilder],[uint32],[uint32].MakeByRefType()),$true),
            @('wtsapi32.dll','WTSQuerySessionInformationW',[bool],[type[]]@([IntPtr],[uint32],[int],[IntPtr].MakeByRefType(),[uint32].MakeByRefType()),$true),
            @('wtsapi32.dll','WTSFreeMemory',[void],[type[]]@([IntPtr]),$false),
            @('user32.dll','EnumDisplayMonitors',[bool],[type[]]@([IntPtr],[IntPtr],$types.MonitorCallback,[IntPtr]),$true),
            @('user32.dll','EnumWindows',[bool],[type[]]@($types.EnumCallback,[IntPtr]),$true),
            @('user32.dll','IsWindow',[bool],[type[]]@([IntPtr]),$false),
            @('user32.dll','IsWindowVisible',[bool],[type[]]@([IntPtr]),$false),
            @('user32.dll','IsWindowEnabled',[bool],[type[]]@([IntPtr]),$false),
            @('user32.dll','IsIconic',[bool],[type[]]@([IntPtr]),$false),
            @('user32.dll','IsZoomed',[bool],[type[]]@([IntPtr]),$false),
            @('user32.dll','IsHungAppWindow',[bool],[type[]]@([IntPtr]),$false),
            @('user32.dll','GetWindow',[IntPtr],[type[]]@([IntPtr],[uint32]),$true),
            @('user32.dll','GetWindowLongW',[int],[type[]]@([IntPtr],[int]),$true),
            @('user32.dll','GetWindowRect',[bool],[type[]]@([IntPtr],$rectRef),$true),
            @('user32.dll','GetWindowPlacement',[bool],[type[]]@([IntPtr],$placementRef),$true),
            @('user32.dll','GetWindowTextW',[int],[type[]]@([IntPtr],[System.Text.StringBuilder],[int]),$true),
            @('user32.dll','GetClassNameW',[int],[type[]]@([IntPtr],[System.Text.StringBuilder],[int]),$true),
            @('user32.dll','GetWindowThreadProcessId',[uint32],[type[]]@([IntPtr],[uint32].MakeByRefType()),$true),
            @('user32.dll','SetWindowPos',[bool],[type[]]@([IntPtr],[IntPtr],[int],[int],[int],[int],[uint32]),$true),
            @('user32.dll','SendMessageTimeoutW',[IntPtr],[type[]]@([IntPtr],[uint32],[UIntPtr],$types.MinMaxInfo.MakeByRefType(),[uint32],[uint32],[UIntPtr].MakeByRefType()),$true),
            @('user32.dll','GetCursorPos',[bool],[type[]]@($types.Point.MakeByRefType()),$true),
            @('user32.dll','MonitorFromPoint',[IntPtr],[type[]]@($types.Point,[uint32]),$false),
            @('user32.dll','MonitorFromWindow',[IntPtr],[type[]]@([IntPtr],[uint32]),$false),
            @('user32.dll','GetMonitorInfoW',[bool],[type[]]@([IntPtr],$types.MonitorInfo.MakeByRefType()),$true),
            @('user32.dll','GetSystemMetrics',[int],[type[]]@([int]),$false),
            @('dwmapi.dll','DwmGetWindowAttribute',[int],[type[]]@([IntPtr],[uint32],[int].MakeByRefType(),[uint32]),$false)
        )
        $dllConstructor = [System.Runtime.InteropServices.DllImportAttribute].GetConstructor([type[]]@([string]))
        $dllFields = [System.Reflection.FieldInfo[]]@(
            [System.Runtime.InteropServices.DllImportAttribute].GetField('EntryPoint'),
            [System.Runtime.InteropServices.DllImportAttribute].GetField('ExactSpelling'),
            [System.Runtime.InteropServices.DllImportAttribute].GetField('CallingConvention'),
            [System.Runtime.InteropServices.DllImportAttribute].GetField('CharSet'),
            [System.Runtime.InteropServices.DllImportAttribute].GetField('SetLastError'),
            [System.Runtime.InteropServices.DllImportAttribute].GetField('PreserveSig')
        )
        foreach ($definition in $methods) {
            $method = $apiBuilder.DefinePInvokeMethod($definition[1], $definition[0], $definition[1], [System.Reflection.MethodAttributes]'Public,Static,PinvokeImpl', [System.Reflection.CallingConventions]::Standard, $definition[2], $definition[3], [System.Runtime.InteropServices.CallingConvention]::Winapi, [System.Runtime.InteropServices.CharSet]::Unicode)
            # DefinePInvokeMethod has no SetLastError parameter. Emit the complete
            # DllImport pseudo attribute so the defaults do not replace our
            # explicit entry point / calling convention / character set.
            $dllValues = [object[]]@($definition[1],$true,[System.Runtime.InteropServices.CallingConvention]::Winapi,[System.Runtime.InteropServices.CharSet]::Unicode,[bool]$definition[4],$true)
            $dllAttribute = New-Object System.Reflection.Emit.CustomAttributeBuilder ($dllConstructor, [object[]]@($definition[0]), $dllFields, $dllValues)
            $method.SetCustomAttribute($dllAttribute)
            $method.SetImplementationFlags([System.Reflection.MethodImplAttributes]::PreserveSig)
        }
        $api = $apiBuilder.CreateType()
    }

    $script:AegisNativeApiType = $api
    $script:AegisNativeTypes = @{}
    foreach ($name in @('Rect','Point','MinMaxInfo','Placement','MonitorInfo','FileTime','EnumCallback','MonitorCallback')) {
        $script:AegisNativeTypes[$name] = $api.Assembly.GetType(($prefix + '.' + $name), $true)
    }
    $expectedSizes = @{ Rect = 16; Point = 8; MinMaxInfo = 40; Placement = 44; MonitorInfo = 40; FileTime = 8 }
    foreach ($name in $expectedSizes.Keys) {
        $sizeProbe = [Activator]::CreateInstance($script:AegisNativeTypes[$name])
        if ([System.Runtime.InteropServices.Marshal]::SizeOf($sizeProbe) -ne $expectedSizes[$name]) {
            throw ('NativeStructSizeMismatch:' + $name)
        }
    }
    $global:AegisNativeCacheV4 = @{ Prefix=$prefix; Api=$api; Types=$script:AegisNativeTypes }
}

function ConvertTo-AegisNativeHandle {
    param($Window)
    $handle = Get-AegisNativeField $Window 'Handle' $null
    if ($handle -is [IntPtr]) { return $handle }
    [long]$number = 0
    $id = Get-AegisNativeField $Window 'Id' ''
    if (-not [long]::TryParse([string]$id, [ref]$number)) { return [IntPtr]::Zero }
    try { return (New-Object IntPtr $number) }
    catch { return [IntPtr]::Zero }
}

function Get-AegisNativeProcess {
    param([uint32]$ProcessId, [bool]$ReadName)
    $api = $script:AegisNativeApiType
    $result = @{ ProcessStart = ''; ProcessName = ''; Ready = $false; ErrorCode = 0; Reason = 'ProcessIdentityUnavailable' }
    if ($ProcessId -eq 0) { return $result }
    $processHandle = [IntPtr]::Zero
    try {
        $processHandle = $api::OpenProcess(0x1000, $false, $ProcessId)
        $openError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
        if ($processHandle -eq [IntPtr]::Zero) {
            $processHandle = $api::OpenProcess(0x0400, $false, $ProcessId)
            $openError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
        }
        if ($processHandle -eq [IntPtr]::Zero) {
            $result.ErrorCode = $openError
        } else {
            $creation = [Activator]::CreateInstance($script:AegisNativeTypes.FileTime)
            $exitTime = [Activator]::CreateInstance($script:AegisNativeTypes.FileTime)
            $kernelTime = [Activator]::CreateInstance($script:AegisNativeTypes.FileTime)
            $userTime = [Activator]::CreateInstance($script:AegisNativeTypes.FileTime)
            $timesOk = $api::GetProcessTimes($processHandle, [ref]$creation, [ref]$exitTime, [ref]$kernelTime, [ref]$userTime)
            $timesError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
            if ($timesOk -and ($creation.High -ne 0 -or $creation.Low -ne 0)) {
                $culture = [Globalization.CultureInfo]::InvariantCulture
                $result.ProcessStart = $creation.High.ToString('X8', $culture) + $creation.Low.ToString('X8', $culture)
                $result.Ready = $true; $result.Reason = 'IdentityRead'
            } else { $result.ErrorCode = $timesError }
            if ($ReadName) {
                [uint32]$capacity = 1024
                $buffer = New-Object System.Text.StringBuilder ([int]$capacity)
                $nameOk = $api::QueryFullProcessImageNameW($processHandle, 0, $buffer, [ref]$capacity)
                $nameError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
                if (-not $nameOk -and $nameError -eq 122) {
                    $capacity = 32768
                    $buffer = New-Object System.Text.StringBuilder ([int]$capacity)
                    $nameOk = $api::QueryFullProcessImageNameW($processHandle, 0, $buffer, [ref]$capacity)
                }
                if ($nameOk) { $result.ProcessName = [IO.Path]::GetFileNameWithoutExtension($buffer.ToString()) }
            }
        }
    } catch {
        $result.Reason = 'ProcessIdentityException'
        $result.Detail = $_.Exception.Message
    } finally {
        if ($processHandle -ne [IntPtr]::Zero) { [void]$api::CloseHandle($processHandle) }
    }
    if ($ReadName -and [string]::IsNullOrEmpty($result.ProcessName)) {
        $processObject = $null
        try {
            $processObject = [Diagnostics.Process]::GetProcessById([int]$ProcessId)
            $result.ProcessName = $processObject.ProcessName
        } catch { }
        finally { if ($null -ne $processObject) { $processObject.Dispose() } }
    }
    return $result
}

function Get-AegisNativeIdentity {
    param([IntPtr]$Handle, [bool]$ReadName = $false)
    $api = $script:AegisNativeApiType
    $result = @{
        Id = $Handle.ToInt64().ToString([Globalization.CultureInfo]::InvariantCulture); Handle = $Handle
        Exists = $false; IdentityReady = $false; ProcessId = [uint32]0; ThreadId = [uint32]0
        ProcessStart = ''; ProcessName = ''; ClassName = ''; ErrorCode = 0; Reason = 'WindowMissing'
    }
    if ($Handle -eq [IntPtr]::Zero) { $result.Reason = 'WindowHandleInvalid'; return $result }
    if (-not $api::IsWindow($Handle)) { return $result }
    $result.Exists = $true
    [uint32]$windowProcessId = 0
    $threadId = $api::GetWindowThreadProcessId($Handle, [ref]$windowProcessId)
    $threadError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $result.ProcessId = $windowProcessId; $result.ThreadId = $threadId
    if ($threadId -eq 0 -or $windowProcessId -eq 0) {
        $result.ErrorCode = $threadError; $result.Reason = 'WindowOwnerUnreadable'; return $result
    }
    $classBuffer = New-Object System.Text.StringBuilder 256
    $classLength = $api::GetClassNameW($Handle, $classBuffer, $classBuffer.Capacity)
    $classError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    if ($classLength -le 0) {
        $result.ErrorCode = $classError; $result.Reason = 'WindowClassUnreadable'; return $result
    }
    $result.ClassName = $classBuffer.ToString()
    $process = Get-AegisNativeProcess $windowProcessId $ReadName
    $result.ProcessStart = $process.ProcessStart; $result.ProcessName = $process.ProcessName
    if (-not $process.Ready) {
        $result.ErrorCode = $process.ErrorCode; $result.Reason = $process.Reason; return $result
    }
    # A window can disappear while the process handle is queried. Re-read the
    # cheap owner fields rather than publishing a known mixed identity.
    [uint32]$checkProcessId = 0
    $checkThreadId = $api::GetWindowThreadProcessId($Handle, [ref]$checkProcessId)
    $checkError = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $result.Exists = $api::IsWindow($Handle)
    if (-not $result.Exists) { $result.Reason = 'WindowMissing'; return $result }
    if ($checkThreadId -eq 0 -or $checkProcessId -eq 0) { $result.ErrorCode = $checkError; $result.Reason = 'WindowOwnerUnreadable'; return $result }
    if ($checkThreadId -ne $threadId -or $checkProcessId -ne $windowProcessId) { $result.Reason = 'IdentityChangedDuringRead'; return $result }
    $result.IdentityReady = $true; $result.Reason = 'IdentityRead'
    return $result
}

function Test-AegisNativeIdentity {
    param($Window, $Identity)
    if (-not $Identity.Exists) { return @{ Same = $false; Reason = 'WindowMissing' } }
    if (-not $Identity.IdentityReady) { return @{ Same = $false; Reason = $Identity.Reason } }
    if (-not [bool](Get-AegisNativeField $Window 'IdentityReady' $true)) { return @{ Same = $false; Reason = 'OriginalIdentityUnreadable' } }
    $id = [string](Get-AegisNativeField $Window 'Id' '')
    $start = [string](Get-AegisNativeField $Window 'ProcessStart' '')
    $className = [string](Get-AegisNativeField $Window 'ClassName' '')
    [uint32]$expectedProcess = 0; [uint32]$expectedThread = 0
    $processValid = [uint32]::TryParse([string](Get-AegisNativeField $Window 'ProcessId' ''), [ref]$expectedProcess)
    $threadValid = [uint32]::TryParse([string](Get-AegisNativeField $Window 'ThreadId' ''), [ref]$expectedThread)
    if ([string]::IsNullOrEmpty($id) -or [string]::IsNullOrEmpty($start) -or [string]::IsNullOrEmpty($className) -or -not $processValid -or -not $threadValid -or $expectedProcess -eq 0 -or $expectedThread -eq 0) {
        return @{ Same = $false; Reason = 'OriginalIdentityIncomplete' }
    }
    # A corrupted Handle/Id pair is an invalid snapshot, not evidence that the
    # original window was closed or that Windows reused its handle.
    $expectedHandle = ConvertTo-AegisNativeHandle $Window
    if ($expectedHandle -eq [IntPtr]::Zero) { return @{ Same = $false; Reason = 'OriginalHandleInvalid' } }
    if (-not [string]::Equals($id, $expectedHandle.ToInt64().ToString([Globalization.CultureInfo]::InvariantCulture), [StringComparison]::Ordinal)) {
        return @{ Same = $false; Reason = 'OriginalHandleIdMismatch' }
    }
    if (-not [string]::Equals($id, $Identity.Id, [StringComparison]::Ordinal) -or $expectedProcess -ne $Identity.ProcessId -or $expectedThread -ne $Identity.ThreadId -or -not [string]::Equals($start, $Identity.ProcessStart, [StringComparison]::Ordinal) -or -not [string]::Equals($className, $Identity.ClassName, [StringComparison]::Ordinal)) {
        return @{ Same = $false; Reason = 'IdentityMismatch' }
    }
    return @{ Same = $true; Reason = 'IdentityMatched' }
}

function Get-AegisNativePlacement {
    param([IntPtr]$Handle)
    $api = $script:AegisNativeApiType
    $placement = [Activator]::CreateInstance($script:AegisNativeTypes.Placement)
    $placement.length = 44
    $ok = $api::GetWindowPlacement($Handle, [ref]$placement)
    $errorCode = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    if (-not $ok) { return @{ Ready = $false; Value = $null; ErrorCode = $errorCode; Reason = 'PlacementUnavailable' } }
    $value = @{}
    foreach ($field in @('length','flags','showCmd','minX','minY','maxX','maxY','nLeft','nTop','nRight','nBottom')) {
        $value[$field] = [int]$placement.$field
    }
    [long]$normalWidth = [long]$value.nRight - $value.nLeft
    [long]$normalHeight = [long]$value.nBottom - $value.nTop
    if ($value.length -ne 44 -or $normalWidth -le 0 -or $normalHeight -le 0 -or $normalWidth -gt [int]::MaxValue -or $normalHeight -gt [int]::MaxValue) {
        return @{ Ready = $false; Value = $null; ErrorCode = 0; Reason = 'InvalidPlacement' }
    }
    return @{ Ready = $true; Value = $value; ErrorCode = 0; Reason = 'PlacementRead' }
}

function Get-AegisNativeMonitor {
    param([IntPtr]$Monitor)
    if ($Monitor -eq [IntPtr]::Zero) { return $null }
    $api = $script:AegisNativeApiType
    $info = [Activator]::CreateInstance($script:AegisNativeTypes.MonitorInfo)
    $info.Size = 40
    if (-not $api::GetMonitorInfoW($Monitor, [ref]$info)) { return $null }
    [long]$width = [long]$info.WorkRight - $info.WorkLeft
    [long]$height = [long]$info.WorkBottom - $info.WorkTop
    if ($width -le 0 -or $height -le 0 -or $width -gt [int]::MaxValue -or $height -gt [int]::MaxValue) { return $null }
    return @{
        Id = $Monitor.ToInt64().ToString([Globalization.CultureInfo]::InvariantCulture)
        Left = $info.WorkLeft; Top = $info.WorkTop; Width = [int]$width; Height = [int]$height
    }
}

function Enter-AegisDpiContext {
    Initialize-AegisNative
    $result = @{ Previous = [IntPtr]::Zero; Mode = 'CallerContext'; Changed = $false; ErrorCode = 0; Reason = 'ThreadDpiUnavailable' }
    if (-not (Test-AegisNativeWindows)) { $result.Reason = 'UnsupportedPlatform'; return $result }
    $api = $script:AegisNativeApiType
    foreach ($context in @(-4,-3)) {
        try {
            $previous = $api::SetThreadDpiAwarenessContext((New-Object IntPtr ([long]$context)))
            $errorCode = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
            if ($previous -ne [IntPtr]::Zero) {
                $result.Previous = $previous; $result.Changed = $true; $result.Reason = 'ThreadDpiChanged'
                if ($context -eq -4) { $result.Mode = 'PerMonitorV2' } else { $result.Mode = 'PerMonitorV1' }
                return $result
            }
            $result.ErrorCode = $errorCode
        } catch { $result.Detail = $_.Exception.Message }
    }
    return $result
}

function Exit-AegisDpiContext {
    param($Context)
    if ($null -eq $Context -or -not [bool](Get-AegisNativeField $Context 'Changed' $false)) {
        return @{ Accepted = $true; ErrorCode = 0; Reason = 'NoDpiChange' }
    }
    if (-not (Test-AegisNativeWindows)) { return @{ Accepted = $false; ErrorCode = 0; Reason = 'UnsupportedPlatform' } }
    try {
        $api = $script:AegisNativeApiType
        $previous = Get-AegisNativeField $Context 'Previous' ([IntPtr]::Zero)
        if (-not ($previous -is [IntPtr]) -or $previous -eq [IntPtr]::Zero) { return @{ Accepted = $false; ErrorCode = 0; Reason = 'InvalidDpiContext' } }
        $restored = $api::SetThreadDpiAwarenessContext($previous)
        $errorCode = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
        if ($restored -eq [IntPtr]::Zero) { return @{ Accepted = $false; ErrorCode = $errorCode; Reason = 'DpiRestoreRejected' } }
        return @{ Accepted = $true; ErrorCode = 0; Reason = 'DpiRestored' }
    } catch { return @{ Accepted = $false; ErrorCode = 0; Reason = 'DpiRestoreException'; Detail = $_.Exception.Message } }
}

# Desktop checks are observations, not a lock against a subsequent desktop
# switch. Every write rechecks; no API here switches desktops or sessions.
function Get-AegisNativeObjectName {
    param([IntPtr]$Handle)
    if ($Handle -eq [IntPtr]::Zero) { return '' }
    $api = $script:AegisNativeApiType
    $buffer = New-Object System.Text.StringBuilder 256
    [uint32]$required = 0
    if ($api::GetUserObjectInformationW($Handle, 2, $buffer, 512, [ref]$required)) { return $buffer.ToString() }
    return ''
}

function Get-AegisNativeDesktop {
    $result = @{ DesktopSafe=$false; DesktopKnown=$false; SessionId=[uint32]0; SessionState=-1; WindowStation=''; ThreadDesktop=''; InputDesktop=''; Reason='DesktopUnavailable'; ErrorCode=0 }
    $api = $script:AegisNativeApiType
    $inputDesktop = [IntPtr]::Zero
    $sessionBuffer = [IntPtr]::Zero
    try {
        [uint32]$sessionId = 0
        if (-not $api::ProcessIdToSessionId($api::GetCurrentProcessId(), [ref]$sessionId)) {
            $result.ErrorCode=[Runtime.InteropServices.Marshal]::GetLastWin32Error(); $result.Reason='SessionIdUnavailable'; return $result
        }
        $result.SessionId=$sessionId
        if ($sessionId -eq 0) { $result.DesktopKnown=$true; $result.Reason='SessionZeroPreserved'; return $result }
        [uint32]$sessionBytes = 0
        if (-not $api::WTSQuerySessionInformationW([IntPtr]::Zero,$sessionId,8,[ref]$sessionBuffer,[ref]$sessionBytes) -or $sessionBuffer -eq [IntPtr]::Zero -or $sessionBytes -lt 4) {
            $result.ErrorCode=[Runtime.InteropServices.Marshal]::GetLastWin32Error(); $result.Reason='SessionStateUnavailable'; return $result
        }
        $result.SessionState=[Runtime.InteropServices.Marshal]::ReadInt32($sessionBuffer)
        if ($result.SessionState -ne 0) { $result.DesktopKnown=$true; $result.Reason='SessionNotActive'; return $result }
        $result.WindowStation=Get-AegisNativeObjectName ($api::GetProcessWindowStation())
        if ([string]::IsNullOrEmpty($result.WindowStation)) { $result.Reason='WindowStationUnavailable'; return $result }
        if (-not [string]::Equals($result.WindowStation,'WinSta0',[StringComparison]::OrdinalIgnoreCase)) { $result.DesktopKnown=$true; $result.Reason='NonInteractiveWindowStation'; return $result }
        $result.ThreadDesktop=Get-AegisNativeObjectName ($api::GetThreadDesktop($api::GetCurrentThreadId()))
        # DESKTOP_READOBJECTS only. Never request switching or object-write rights.
        $inputDesktop=$api::OpenInputDesktop(0,$false,1)
        if ($inputDesktop -eq [IntPtr]::Zero) { $result.ErrorCode=[Runtime.InteropServices.Marshal]::GetLastWin32Error(); $result.Reason='InputDesktopUnavailable'; return $result }
        $result.InputDesktop=Get-AegisNativeObjectName $inputDesktop
        if ([string]::IsNullOrEmpty($result.ThreadDesktop) -or [string]::IsNullOrEmpty($result.InputDesktop)) { $result.Reason='DesktopNameUnavailable'; return $result }
        $result.DesktopKnown=$true
        if (-not [string]::Equals($result.ThreadDesktop,'Default',[StringComparison]::OrdinalIgnoreCase) -or -not [string]::Equals($result.InputDesktop,'Default',[StringComparison]::OrdinalIgnoreCase)) { $result.Reason='InputDesktopChanged'; return $result }
        $result.DesktopSafe=$true; $result.Reason='InteractiveDesktopObserved'; return $result
    } catch { $result.Reason='DesktopCheckException'; $result.Detail=$_.Exception.Message; return $result }
    finally {
        if ($sessionBuffer -ne [IntPtr]::Zero) { $api::WTSFreeMemory($sessionBuffer) }
        if ($inputDesktop -ne [IntPtr]::Zero) { [void]$api::CloseDesktop($inputDesktop) }
    }
}

# This signature describes the observed caller coordinate context. System
# LOGPIXELS is not per-monitor DPI; app DPI transitions still require Windows
# integration testing. Unknown observations produce a stable diagnostic token
# but never authorize a write.
function Get-AegisNativeCoordinateContext {
    $api=$script:AegisNativeApiType
    $result=@{ Known=$false; Signature='CallerUnknown;SystemDpi=Unknown'; Awareness='CallerUnknown'; SystemDpiX=0; SystemDpiY=0; Reason='CoordinateContextUnavailable'; Limitation='System DPI is not a per-monitor DPI measurement.' }
    $awareness=''; $threadContext=[IntPtr]::Zero
    try {
        $threadContext=$api::GetThreadDpiAwarenessContext()
        if ($threadContext -ne [IntPtr]::Zero) {
            foreach ($candidate in @(@(-4,'PerMonitorV2'),@(-3,'PerMonitorV1'),@(-2,'SystemAware'),@(-5,'UnawareGdiScaled'),@(-1,'Unaware'))) {
                if ($api::AreDpiAwarenessContextsEqual($threadContext,(New-Object IntPtr ([long]$candidate[0])))) { $awareness=('Thread:'+ $candidate[1]); break }
            }
            if ($awareness -eq '') {
                $level=$api::GetAwarenessFromDpiAwarenessContext($threadContext)
                if ($level -ge 0 -and $level -le 2) { $awareness=('ThreadLevel:'+ $level) }
            }
        }
    } catch { }
    if ($awareness -eq '') {
        try {
            [int]$level=-1
            $status=$api::GetProcessDpiAwareness([IntPtr]::Zero,[ref]$level)
            if ($status -eq 0 -and $level -ge 0 -and $level -le 2) { $awareness=('ProcessLevel:'+ $level) }
        } catch { }
    }
    if ($awareness -eq '') {
        try { if ($api::IsProcessDPIAware()) { $awareness='LegacyProcess:Aware' } else { $awareness='LegacyProcess:Unaware' } }
        catch { }
    }
    $dc=[IntPtr]::Zero; $released=$true
    try {
        $dc=$api::GetDC([IntPtr]::Zero)
        if ($dc -ne [IntPtr]::Zero) {
            $dpiX=$api::GetDeviceCaps($dc,88); $dpiY=$api::GetDeviceCaps($dc,90)
            if ($dpiX -gt 0 -and $dpiX -le 9600 -and $dpiY -gt 0 -and $dpiY -le 9600) { $result.SystemDpiX=$dpiX; $result.SystemDpiY=$dpiY }
        }
    } catch { }
    finally { if ($dc -ne [IntPtr]::Zero) { try { $released=($api::ReleaseDC([IntPtr]::Zero,$dc) -ne 0) } catch { $released=$false } } }
    if ($awareness -ne '') { $result.Awareness=$awareness }
    $dpi='Unknown'
    if ($result.SystemDpiX -gt 0 -and $result.SystemDpiY -gt 0) { $dpi=([string]$result.SystemDpiX+','+$result.SystemDpiY) }
    $result.Signature=$result.Awareness+';SystemDpi='+$dpi
    $result.Known=($awareness -ne '' -and $dpi -ne 'Unknown' -and $released)
    if ($result.Known) { $result.Reason='CoordinateContextObserved' }
    elseif (-not $released) { $result.Reason='DeviceContextReleaseFailed' }
    elseif ($awareness -eq '') { $result.Reason='DpiAwarenessUnavailable' }
    else { $result.Reason='SystemDpiUnavailable' }
    return $result
}

function Get-AegisNativeContext {
    param([int]$TimeoutMs=1000)
    $result = @{ Complete=$false; Ready=$false; DesktopSafe=$false; DesktopReason='UnsupportedPlatform'; TopologyReady=$false; TopologySignature=''; CoordinateSignature=''; CoordinateKnown=$false; CoordinateReason='CoordinateContextUnavailable'; Monitors=@(); SessionId=[uint32]0; SessionState=-1; WindowStation=''; ThreadDesktop=''; InputDesktop=''; Reason='UnsupportedPlatform'; ErrorCode=0 }
    if (-not (Test-AegisNativeWindows)) { return $result }
    Initialize-AegisNative
    if ($TimeoutMs -lt 1 -or $TimeoutMs -gt 120000) { throw 'InvalidContextTimeout' }
    $api=$script:AegisNativeApiType
    $desktop=Get-AegisNativeDesktop
    foreach ($key in @('DesktopSafe','SessionId','SessionState','WindowStation','ThreadDesktop','InputDesktop')) { $result[$key]=$desktop[$key] }
    $result.DesktopReason=$desktop.Reason
    $coordinate=Get-AegisNativeCoordinateContext
    $result.CoordinateSignature=$coordinate.Signature; $result.CoordinateKnown=$coordinate.Known; $result.CoordinateReason=$coordinate.Reason
    $result.CoordinateLimitation=$coordinate.Limitation
    $contextState=@{ Handles=(New-Object System.Collections.ArrayList); Watch=[Diagnostics.Stopwatch]::StartNew(); TimedOut=$false; Error=''; Limit=$false; Timeout=$TimeoutMs }
    try {
        $body={
            param([IntPtr]$MonitorHandle,[IntPtr]$DeviceContext,[IntPtr]$Rectangle,[IntPtr]$Parameter)
            try {
                if ($contextState.Watch.ElapsedMilliseconds -ge $contextState.Timeout) { $contextState.TimedOut=$true; return $false }
                if ($contextState.Handles.Count -ge 64) { $contextState.Limit=$true; return $false }
                [void]$contextState.Handles.Add($MonitorHandle); return $true
            } catch { $contextState.Error=$_.Exception.Message; return $false }
        }.GetNewClosure()
        $callback=[Management.Automation.LanguagePrimitives]::ConvertTo($body,$script:AegisNativeTypes.MonitorCallback)
        $api::SetLastError(0)
        $ok=$api::EnumDisplayMonitors([IntPtr]::Zero,[IntPtr]::Zero,$callback,[IntPtr]::Zero)
        $result.ErrorCode=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
        [GC]::KeepAlive($callback)
        if (-not $ok -or $contextState.Handles.Count -eq 0 -or $contextState.Limit -or $contextState.TimedOut -or -not [string]::IsNullOrEmpty($contextState.Error)) { $result.Reason='MonitorEnumerationIncomplete'; return $result }
        $monitors=New-Object System.Collections.ArrayList
        $tokens=New-Object System.Collections.ArrayList
        foreach ($handle in $contextState.Handles) {
            if ($contextState.Watch.ElapsedMilliseconds -ge $TimeoutMs) { $result.Reason='ContextBudgetExceeded'; return $result }
            $monitor=Get-AegisNativeMonitor $handle
            if ($null -eq $monitor) { $result.Reason='MonitorWorkAreaUnavailable'; return $result }
            [void]$monitors.Add($monitor)
            [void]$tokens.Add(($monitor.Id+','+$monitor.Left+','+$monitor.Top+','+$monitor.Width+','+$monitor.Height))
        }
        $sorted=@($tokens.ToArray() | Sort-Object)
        $result.Monitors=$monitors.ToArray()
        $result.TopologySignature=$coordinate.Signature+'|'+[string]::Join(';',[string[]]$sorted)
        $result.TopologyReady=$true
        $result.Complete=([bool]$desktop.DesktopKnown -and [bool]$coordinate.Known)
        $result.Ready=($result.Complete -and $result.DesktopSafe)
        $result.Reason=$desktop.Reason
        $result.ErrorCode=$desktop.ErrorCode
        if (-not $coordinate.Known) { $result.Reason=$coordinate.Reason }
        return $result
    } catch { $result.Reason='ContextException'; $result.Detail=$_.Exception.Message; return $result }
    finally { $contextState.Watch.Stop() }
}

# Name lookup deliberately precedes process-creation identity, placement and
# WM_GETMINMAXINFO. Names are only selection hints; writes use full identity.
function Get-AegisNativeProcessName {
    param([uint32]$ProcessId)
    if ($ProcessId -eq 0) { return '' }
    $api=$script:AegisNativeApiType
    $handle=[IntPtr]::Zero; $name=''
    try {
        $handle=$api::OpenProcess(0x1000,$false,$ProcessId)
        if ($handle -ne [IntPtr]::Zero) {
            [uint32]$capacity=1024
            $buffer=New-Object Text.StringBuilder ([int]$capacity)
            if ($api::QueryFullProcessImageNameW($handle,0,$buffer,[ref]$capacity)) { $name=[IO.Path]::GetFileNameWithoutExtension($buffer.ToString()) }
        }
    } catch { }
    finally { if ($handle -ne [IntPtr]::Zero) { [void]$api::CloseHandle($handle) } }
    if ([string]::IsNullOrEmpty($name)) {
        $process=$null
        try { $process=[Diagnostics.Process]::GetProcessById([int]$ProcessId); $name=$process.ProcessName }
        catch { }
        finally { if ($null -ne $process) { $process.Dispose() } }
    }
    return $name
}

function Get-AegisNativeWindowState {
    param([IntPtr]$Handle,[bool]$ReadGeometry=$true)
    $api=$script:AegisNativeApiType
    $state=@{ Exists=$false; Visible=$false; Minimized=$false; Maximized=$false; Enabled=$false; Hung=$false; Cloaked=$false; CloakReady=$false; Owned=$false; ToolWindow=$false; NoActivate=$false; Topmost=$false; Resizable=$false; StyleReady=$false; RectReady=$false; Left=0; Top=0; Width=0; Height=0; Monitor=$null; ErrorCode=0; Reason='WindowMissing' }
    if (-not $api::IsWindow($Handle)) { return $state }
    $state.Exists=$true
    $state.Visible=$api::IsWindowVisible($Handle); $state.Minimized=$api::IsIconic($Handle); $state.Maximized=$api::IsZoomed($Handle)
    $state.Enabled=$api::IsWindowEnabled($Handle); $state.Hung=$api::IsHungAppWindow($Handle)
    if (-not $ReadGeometry -and (-not $state.Visible -or $state.Minimized -or $state.Maximized -or -not $state.Enabled -or $state.Hung)) { $state.Reason='UserStatePreserved'; return $state }
    $state.Owned=($api::GetWindow($Handle,4) -ne [IntPtr]::Zero)
    $api::SetLastError(0); $style=$api::GetWindowLongW($Handle,-16); $styleError=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $api::SetLastError(0); $extended=$api::GetWindowLongW($Handle,-20); $extendedError=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $state.StyleReady=(($style -ne 0 -or $styleError -eq 0) -and ($extended -ne 0 -or $extendedError -eq 0))
    $state.Resizable=(($style -band 0x00040000) -ne 0); $state.ToolWindow=(($extended -band 0x80) -ne 0)
    $state.NoActivate=(($extended -band 0x08000000) -ne 0); $state.Topmost=(($extended -band 8) -ne 0)
    try {
        [int]$cloaked=0
        $status=$api::DwmGetWindowAttribute($Handle,14,[ref]$cloaked,4)
        if ($status -eq 0) { $state.Cloaked=($cloaked -ne 0); $state.CloakReady=$true }
    } catch { }
    # DWMWA_CLOAKED arrived in Windows 8; lack of that API on earlier Windows
    # is expected. On supporting systems an unreadable state cannot authorize.
    if (-not $state.CloakReady) {
        $version=[Environment]::OSVersion.Version
        if ($version.Major -lt 6 -or ($version.Major -eq 6 -and $version.Minor -lt 2)) { $state.CloakReady=$true }
    }
    if ($ReadGeometry) {
        $rect=[Activator]::CreateInstance($script:AegisNativeTypes.Rect)
        $api::SetLastError(0)
        $rectOk=$api::GetWindowRect($Handle,[ref]$rect)
        $rectError=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
        if ($rectOk) {
            [long]$width=[long]$rect.Right-$rect.Left; [long]$height=[long]$rect.Bottom-$rect.Top
            if ($width -gt 0 -and $height -gt 0 -and $width -le [int]::MaxValue -and $height -le [int]::MaxValue) {
                $state.Left=$rect.Left; $state.Top=$rect.Top; $state.Width=[int]$width; $state.Height=[int]$height; $state.RectReady=$true
            }
        }
        $state.Monitor=Get-AegisNativeMonitor ($api::MonitorFromWindow($Handle,2))
        if (-not $state.RectReady) { $state.ErrorCode=$rectError; $state.Reason='WindowRectUnavailable'; return $state }
        if ($null -eq $state.Monitor) { $state.Reason='WindowMonitorUnavailable'; return $state }
    }
    if (-not $state.StyleReady) { $state.ErrorCode=[Math]::Max($styleError,$extendedError); $state.Reason='WindowStyleUnavailable' }
    elseif (-not $state.CloakReady) { $state.Reason='CloakStateUnavailable' }
    else { $state.Reason='WindowStateRead' }
    return $state
}

function Get-AegisNativePreserveReason {
    param($State)
    if (-not $State.Exists) { return 'WindowMissing' }
    if (-not $State.Visible) { return 'HiddenWindowPreserved' }
    if ($State.Minimized) { return 'MinimizedWindowPreserved' }
    if ($State.Maximized) { return 'MaximizedWindowPreserved' }
    if (-not $State.Enabled) { return 'DisabledWindowPreserved' }
    if ($State.Hung) { return 'UnresponsiveWindow' }
    if ($State.Cloaked) { return 'CloakedWindowPreserved' }
    if (-not $State.CloakReady) { return 'CloakStateUnavailable' }
    if (-not $State.StyleReady) { return 'WindowStyleUnavailable' }
    return ''
}

function Get-AegisNativeMatchingRule {
    param($Window,[object[]]$Rules=@())
    if ($null -eq $Rules) { $Rules=@() }
    foreach ($rule in $Rules) {
        if ($rule -isnot [System.Collections.IDictionary]) { continue }
        $process=[string](Get-AegisNativeField $rule 'ProcessName' '')
        if ([string]::IsNullOrEmpty($process) -or -not [string]::Equals($process,[string]$Window.ProcessName,[StringComparison]::OrdinalIgnoreCase)) { continue }
        $class=[string](Get-AegisNativeField $rule 'ClassName' '')
        if (-not [string]::IsNullOrEmpty($class) -and -not [string]::Equals($class,[string]$Window.ClassName,[StringComparison]::OrdinalIgnoreCase)) { continue }
        $title=[string](Get-AegisNativeField $rule 'Title' '')
        if (-not [string]::IsNullOrEmpty($title) -and -not [string]::Equals($title,[string]$Window.Title,[StringComparison]::Ordinal)) { continue }
        return $rule
    }
    return $null
}

function Get-AegisInventory {
    param([hashtable]$Options=@{},[object[]]$Rules=@())
    if ($null -eq $Rules) { $Rules=@() }
    $watch=[Diagnostics.Stopwatch]::StartNew()
    Initialize-AegisNative
    $windows=New-Object System.Collections.ArrayList; $warnings=New-Object System.Collections.ArrayList
    $result=@{ Windows=@(); Warnings=@(); Foreground=$null; CursorMonitor=$null; Complete=$true; ElapsedMs=0; DesktopSafe=$false; DesktopReason='UnsupportedPlatform'; TopologySignature=''; CoordinateSignature=''; CoordinateKnown=$false; CoordinateReason='CoordinateContextUnavailable'; Monitors=@(); Context=$null; SelectedCount=0 }
    if (-not (Test-AegisNativeWindows)) { $result.Complete=$false; $result.Warnings=@('UnsupportedPlatform'); return $result }
    $api=$script:AegisNativeApiType
    [int]$queryTimeout=0; [int]$totalTimeout=0; [int]$maxWindows=0; [int]$maxEnumerated=0
    if (-not [int]::TryParse([string](Get-AegisNativeField $Options 'QueryTimeoutMs' 50),[ref]$queryTimeout) -or $queryTimeout -lt 1 -or $queryTimeout -gt 5000) { throw 'InvalidQueryTimeoutMs' }
    if (-not [int]::TryParse([string](Get-AegisNativeField $Options 'TotalTimeoutMs' 10000),[ref]$totalTimeout) -or $totalTimeout -lt 1 -or $totalTimeout -gt 120000) { throw 'InvalidTotalTimeoutMs' }
    if (-not [int]::TryParse([string](Get-AegisNativeField $Options 'MaxWindows' 64),[ref]$maxWindows) -or $maxWindows -lt 1 -or $maxWindows -gt 512) { throw 'InvalidMaxWindows' }
    if (-not [int]::TryParse([string](Get-AegisNativeField $Options 'MaxEnumeratedWindows' 2048),[ref]$maxEnumerated) -or $maxEnumerated -lt 1 -or $maxEnumerated -gt 16384) { throw 'InvalidMaxEnumeratedWindows' }
    $context=Get-AegisNativeContext ([Math]::Min(1000,$totalTimeout))
    $result.Context=$context; $result.DesktopSafe=$context.DesktopSafe; $result.DesktopReason=$context.DesktopReason
    $result.TopologySignature=$context.TopologySignature; $result.Monitors=$context.Monitors
    $result.CoordinateSignature=$context.CoordinateSignature; $result.CoordinateKnown=$context.CoordinateKnown; $result.CoordinateReason=$context.CoordinateReason
    if (-not $context.CoordinateKnown) { $result.Complete=$false; [void]$warnings.Add($context.CoordinateReason) }
    if (-not $context.TopologyReady) { $result.Complete=$false; [void]$warnings.Add($context.Reason) }
    if (-not $context.DesktopSafe) { [void]$warnings.Add($context.DesktopReason) }
    [uint32]$ownProcessId=$api::GetCurrentProcessId(); $ownConsole=$api::GetConsoleWindow()
    $point=[Activator]::CreateInstance($script:AegisNativeTypes.Point)
    if ($api::GetCursorPos([ref]$point)) { $result.CursorMonitor=Get-AegisNativeMonitor ($api::MonitorFromPoint($point,2)) }
    $currentMonitorOnly=([string](Get-AegisNativeField $Options 'MonitorScope' 'EachMonitor') -eq 'CurrentMonitor')
    if ($currentMonitorOnly -and $null -eq $result.CursorMonitor) {
        $result.Complete=$false;[void]$warnings.Add('CurrentMonitorUnavailable')
        $watch.Stop();$result.ElapsedMs=$watch.ElapsedMilliseconds;$result.Warnings=$warnings.ToArray()
        return $result
    }
    $enumeration=@{ Handles=(New-Object System.Collections.ArrayList); Watch=$watch; Budget=$totalTimeout; Max=$maxEnumerated; TimedOut=$false; Limit=$false; Error='' }
    $body={
        param([IntPtr]$WindowHandle,[IntPtr]$Parameter)
        try {
            if ($enumeration.Watch.ElapsedMilliseconds -ge $enumeration.Budget) { $enumeration.TimedOut=$true; return $false }
            if ($enumeration.Handles.Count -ge $enumeration.Max) { $enumeration.Limit=$true; return $false }
            [void]$enumeration.Handles.Add($WindowHandle); return $true
        } catch { $enumeration.Error=$_.Exception.Message; return $false }
    }.GetNewClosure()
    $callback=[Management.Automation.LanguagePrimitives]::ConvertTo($body,$script:AegisNativeTypes.EnumCallback)
    $api::SetLastError(0); $ok=$api::EnumWindows($callback,[IntPtr]::Zero); $enumerationError=[Runtime.InteropServices.Marshal]::GetLastWin32Error(); [GC]::KeepAlive($callback)
    if (-not $ok) { $result.Complete=$false; [void]$warnings.Add(('EnumerationIncomplete:'+ $enumerationError)) }
    if ($enumeration.Limit) { [void]$warnings.Add('EnumerationLimitExceeded'); $result.Complete=$false }
    if (-not [string]::IsNullOrEmpty($enumeration.Error)) { [void]$warnings.Add('EnumerationCallbackFailed'); $result.Complete=$false }
    $processNames=@{}
    [int]$baselineWidth=[Math]::Max(1,$api::GetSystemMetrics(34)); [int]$baselineHeight=[Math]::Max(1,$api::GetSystemMetrics(35))
    [int]$order=0
    foreach ($handle in $enumeration.Handles) {
        $window=@{ Id=$handle.ToInt64().ToString([Globalization.CultureInfo]::InvariantCulture); Handle=$handle; Order=$order; ProcessId=[uint32]0; ThreadId=[uint32]0; ProcessStart=''; ProcessName=''; ClassName=''; Title=''; IsSelf=$false; Exists=$false; Visible=$false; Minimized=$false; Maximized=$false; Enabled=$false; Hung=$false; Cloaked=$false; CloakReady=$false; Owned=$false; ToolWindow=$false; NoActivate=$false; Topmost=$false; Resizable=$false; Left=0; Top=0; Width=0; Height=0; MinWidth=$baselineWidth; MinHeight=$baselineHeight; MaxWidth=0; MaxHeight=0; Monitor=$null; Placement=$null; PlacementReady=$false; RectReady=$false; StyleReady=$false; IdentityReady=$false; SnapshotReady=$false; MinMaxReady=$false; ConstraintReason='NotQueried'; NativeWarnings=@(); Selected=$false; Allowed=$false; MatchedRuleId=''; SelectionTitle=''; SelectionReason='NotAllowlisted'; TopologySignature=$result.TopologySignature }
        $order++
        [void]$windows.Add($window)
        if ($watch.ElapsedMilliseconds -ge $totalTimeout) { $enumeration.TimedOut=$true; $result.Complete=$false; $window.SelectionReason='InventoryBudgetExceeded'; continue }
        try {
            $state=Get-AegisNativeWindowState $handle $false
            foreach ($key in $state.Keys) { $window[$key]=$state[$key] }
            $preserve=Get-AegisNativePreserveReason $state
            if ($preserve -ne '') { $window.SelectionReason=$preserve; continue }
            [uint32]$owner=0; $window.ThreadId=$api::GetWindowThreadProcessId($handle,[ref]$owner); $window.ProcessId=$owner
            $window.IsSelf=($owner -eq $ownProcessId -or ($ownConsole -ne [IntPtr]::Zero -and $handle -eq $ownConsole))
            if ($window.IsSelf) { $window.SelectionReason='OwnHostWindow'; continue }
            if ($owner -eq 0 -or $window.ThreadId -eq 0) { $window.SelectionReason='WindowOwnerUnreadable'; continue }
            $classBuffer=New-Object Text.StringBuilder 256
            if ($api::GetClassNameW($handle,$classBuffer,$classBuffer.Capacity) -le 0) { $window.SelectionReason='WindowClassUnreadable'; continue }
            $window.ClassName=$classBuffer.ToString()
            if (@('Progman','WorkerW','Shell_TrayWnd','Shell_SecondaryTrayWnd','tooltips_class32','#32768','SysShadow') -contains $window.ClassName) { $window.SelectionReason='SystemWindowClass'; continue }
            $ownerKey=[string]$owner
            if (-not $processNames.ContainsKey($ownerKey)) { $processNames[$ownerKey]=Get-AegisNativeProcessName $owner }
            $window.ProcessName=[string]$processNames[$ownerKey]
            $possible=$false
            foreach ($rule in $Rules) {
                if ([string]::Equals([string](Get-AegisNativeField $rule 'ProcessName' ''),$window.ProcessName,[StringComparison]::OrdinalIgnoreCase)) { $possible=$true; break }
            }
            if (-not $possible) { continue }
            [int]$titleCapacity=1024 # Rule titles are limited to 512; truncation cannot equal a valid exact title.
            $titleBuffer=New-Object Text.StringBuilder $titleCapacity
            if ($api::GetWindowTextW($handle,$titleBuffer,$titleCapacity) -gt 0) { $window.Title=$titleBuffer.ToString() }
            $matched=Get-AegisNativeMatchingRule $window $Rules
            if ($null -eq $matched) { continue }
            $window.MatchedRuleId=[string](Get-AegisNativeField $matched 'Id' '')
            $window.SelectionTitle=[string](Get-AegisNativeField $matched 'Title' '')
            $include=Get-AegisNativeField $matched 'Include' $true
            if ($include -isnot [bool] -or -not $include) { $window.SelectionReason='ExplicitExcludeRule'; continue }
            $window.Allowed=$true
            # Scope is resolved before the detailed-query cap. Keep a cheap row
            # for reservation/identity uncertainty without querying another
            # monitor's process start time, rectangle, placement or min/max.
            if ($currentMonitorOnly) {
                $window.Monitor=Get-AegisNativeMonitor ($api::MonitorFromWindow($handle,2))
                if ($null -eq $window.Monitor) {
                    $window.SelectionReason='WindowMonitorUnavailable';$result.Complete=$false
                    [void]$warnings.Add('WindowMonitorUnavailable');continue
                }
                if ($window.Monitor.Id -ne $result.CursorMonitor.Id) { $window.SelectionReason='OutsideCurrentMonitor';continue }
            }
            if ($result.SelectedCount -ge $maxWindows) { $window.SelectionReason='TargetWindowLimitExceeded'; $result.Complete=$false; [void]$warnings.Add('TargetWindowLimitExceeded'); continue }
            $result.SelectedCount++
            if ($watch.ElapsedMilliseconds -ge $totalTimeout) { $enumeration.TimedOut=$true; $result.Complete=$false; $window.SelectionReason='InventoryBudgetExceeded'; continue }
            $identity=Get-AegisNativeIdentity $handle $true
            $window.ProcessStart=$identity.ProcessStart
            if (-not [string]::Equals($identity.ProcessName,$window.ProcessName,[StringComparison]::OrdinalIgnoreCase)) { $window.SelectionReason='IdentitySelectionChanged'; continue }
            if (-not $identity.IdentityReady -or $identity.ProcessId -ne $window.ProcessId -or $identity.ThreadId -ne $window.ThreadId -or -not [string]::Equals($identity.ClassName,$window.ClassName,[StringComparison]::Ordinal)) { $window.SelectionReason=('Identity:'+ $identity.Reason); continue }
            $window.IdentityReady=$true
            $state=Get-AegisNativeWindowState $handle $true
            foreach ($key in $state.Keys) { $window[$key]=$state[$key] }
            $preserve=Get-AegisNativePreserveReason $state
            if ($preserve -ne '') { $window.SelectionReason=$preserve; continue }
            if (-not $window.RectReady -or $null -eq $window.Monitor) { $window.SelectionReason=$state.Reason; continue }
            if ($currentMonitorOnly -and $window.Monitor.Id -ne $result.CursorMonitor.Id) {
                $window.SelectionReason='WindowMonitorChangedDuringInventory';$result.Complete=$false
                [void]$warnings.Add('WindowMonitorChangedDuringInventory');continue
            }
            $placement=Get-AegisNativePlacement $handle
            $window.PlacementReady=$placement.Ready; $window.Placement=$placement.Value
            if ($window.Resizable) {
                if ($watch.ElapsedMilliseconds -ge $totalTimeout) { $enumeration.TimedOut=$true; $result.Complete=$false; $window.SelectionReason='InventoryBudgetExceeded'; continue }
                $minmax=[Activator]::CreateInstance($script:AegisNativeTypes.MinMaxInfo)
                [UIntPtr]$messageResult=[UIntPtr]::Zero
                [uint32]$remaining=[Math]::Max(1,[Math]::Min([long]$queryTimeout,[long]$totalTimeout-$watch.ElapsedMilliseconds))
                $api::SetLastError(0)
                # ABORTIFHUNG | ERRORONEXIT; no NOTIMEOUTIFNOTHUNG.
                $query=$api::SendMessageTimeoutW($handle,0x0024,[UIntPtr]::Zero,[ref]$minmax,0x0022,$remaining,[ref]$messageResult)
                $queryError=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
                if ($query -ne [IntPtr]::Zero) {
                    $window.MinMaxReady=$true; $window.ConstraintReason='MinMaxRead'
                    if ($minmax.MinTrackX -gt 0) { $window.MinWidth=$minmax.MinTrackX }
                    if ($minmax.MinTrackY -gt 0) { $window.MinHeight=$minmax.MinTrackY }
                    if ($minmax.MaxTrackX -gt 0) { $window.MaxWidth=$minmax.MaxTrackX }
                    if ($minmax.MaxTrackY -gt 0) { $window.MaxHeight=$minmax.MaxTrackY }
                    if (($window.MaxWidth -gt 0 -and $window.MaxWidth -lt $window.MinWidth) -or ($window.MaxHeight -gt 0 -and $window.MaxHeight -lt $window.MinHeight)) { $window.MinMaxReady=$false; $window.ConstraintReason='AppBoundsConflict' }
                } else { $window.ConstraintReason='MinMaxUnavailable'; $window.NativeWarnings=@(('MinMaxUnavailable:'+ $queryError)) }
            } else {
                $window.MinWidth=$window.Width; $window.MinHeight=$window.Height; $window.MaxWidth=$window.Width; $window.MaxHeight=$window.Height
                $window.MinMaxReady=$true; $window.ConstraintReason='FixedSize'
            }
            $window.SnapshotReady=($window.IdentityReady -and $window.RectReady -and $window.StyleReady -and $window.CloakReady -and $null -ne $window.Monitor)
            $window.Selected=$window.SnapshotReady
            $window.SelectionReason='Selected'
        } catch { $window.SnapshotReady=$false; $window.Selected=$false; $window.SelectionReason='InventoryException'; $window.NativeWarnings=@($_.Exception.Message) }
    }
    if ($enumeration.TimedOut -or $watch.ElapsedMilliseconds -ge $totalTimeout) { $result.Complete=$false; [void]$warnings.Add('InventoryBudgetExceeded') }
    $watch.Stop(); $result.ElapsedMs=$watch.ElapsedMilliseconds; $result.Windows=$windows.ToArray(); $result.Warnings=@($warnings.ToArray() | Select-Object -Unique)
    return $result
}

function Invoke-AegisNative {
    param([string]$Operation,$Window,$Target=$null)
    if ($Operation -eq 'Context') { return (Get-AegisNativeContext) }
    $observed=@{ Exists=$false; SameIdentity=$false; Visible=$false; Minimized=$false; Maximized=$false; Enabled=$false; Hung=$false; Cloaked=$false; CloakReady=$false; Owned=$false; ToolWindow=$false; NoActivate=$false; Topmost=$false; Resizable=$false; StyleReady=$false; RectReady=$false; Left=0; Top=0; Width=0; Height=0; Monitor=$null; Placement=$null; PlacementReady=$false; ErrorCode=0; Reason='UnsupportedPlatform' }
    $isObserve=($Operation -eq 'Observe')
    $failure=@{ Accepted=$false; RequestIssued=$false; MayBePending=$false; ErrorCode=0; Reason='UnsupportedPlatform' }
    # The operational adapter has no show, restore, activation or Z-order write.
    if (-not $isObserve -and $Operation -ne 'Move') { $failure.Reason='UnsupportedOperation'; return $failure }
    if (-not (Test-AegisNativeWindows)) { if ($isObserve) { return $observed }; return $failure }
    $requestEntered=$false
    try {
        Initialize-AegisNative
        $api=$script:AegisNativeApiType
        if (-not $isObserve) {
            $context=Get-AegisNativeContext
            if (-not $context.Ready) { $failure.Reason=$context.Reason; $failure.ErrorCode=$context.ErrorCode; return $failure }
            $expectedTopology=[string](Get-AegisNativeField $Target 'ExpectedTopologySignature' (Get-AegisNativeField $Window 'TopologySignature' ''))
            if (-not [string]::IsNullOrEmpty($expectedTopology) -and -not [string]::Equals($expectedTopology,$context.TopologySignature,[StringComparison]::Ordinal)) { $failure.Reason='TopologyChanged'; return $failure }
        }
        $handle=ConvertTo-AegisNativeHandle $Window
        if ($handle -eq [IntPtr]::Zero) { if ($isObserve) { $observed.Reason='OriginalHandleInvalid'; return $observed }; $failure.Reason='OriginalHandleInvalid'; return $failure }
        $identity=Get-AegisNativeIdentity $handle
        $comparison=Test-AegisNativeIdentity $Window $identity
        $observed.Exists=$identity.Exists; $observed.SameIdentity=$comparison.Same; $observed.ErrorCode=$identity.ErrorCode; $observed.Reason=$comparison.Reason
        if (-not $comparison.Same) { if ($isObserve) { return $observed }; $failure.Reason=$comparison.Reason; $failure.ErrorCode=$identity.ErrorCode; return $failure }
        $state=Get-AegisNativeWindowState $handle $true
        foreach ($key in $state.Keys) { $observed[$key]=$state[$key] }
        if ($isObserve) { return $observed }
        $preserve=Get-AegisNativePreserveReason $state
        if ($preserve -ne '') { $failure.Reason=$preserve; return $failure }
        $requiredTitle=[string](Get-AegisNativeField $Window 'SelectionTitle' '')
        if (-not [string]::IsNullOrEmpty($requiredTitle)) {
            $currentTitle=New-Object Text.StringBuilder 1024
            [void]$api::GetWindowTextW($handle,$currentTitle,$currentTitle.Capacity)
            if (-not [string]::Equals($requiredTitle,$currentTitle.ToString(),[StringComparison]::Ordinal)) { $failure.Reason='WindowTitleChanged'; return $failure }
        }
        if (-not $state.RectReady -or $null -eq $state.Monitor) { $failure.Reason=$state.Reason; return $failure }
        $expectedMonitor=Get-AegisNativeField $Target 'ExpectedMonitor' (Get-AegisNativeField $Window 'Monitor' $null)
        if ($null -ne $expectedMonitor) {
            $expectedId=[string](Get-AegisNativeField $expectedMonitor 'Id' $expectedMonitor)
            if (-not [string]::Equals($expectedId,[string]$state.Monitor.Id,[StringComparison]::Ordinal)) { $failure.Reason='WindowMonitorChanged'; return $failure }
            if ($expectedMonitor -is [System.Collections.IDictionary]) {
                foreach ($key in @('Left','Top','Width','Height')) {
                    if ([string](Get-AegisNativeField $expectedMonitor $key '') -ne [string]$state.Monitor[$key]) { $failure.Reason='MonitorWorkAreaChanged'; return $failure }
                }
            }
        }
        [int]$tolerance=0
        if (-not [int]::TryParse([string](Get-AegisNativeField $Target 'Tolerance' 0),[ref]$tolerance) -or $tolerance -lt 0 -or $tolerance -gt 8) { $failure.Reason='InvalidTolerance'; return $failure }
        $expectedRect=Get-AegisNativeField $Target 'ExpectedRect' $null
        if ($null -ne $expectedRect) {
            foreach ($key in @('Left','Top','Width','Height')) {
                [int]$expectedValue=0
                if (-not [int]::TryParse([string](Get-AegisNativeField $expectedRect $key ''),[ref]$expectedValue) -or [Math]::Abs([long]$state[$key]-$expectedValue) -gt $tolerance) { $failure.Reason='WindowGeometryChanged'; return $failure }
            }
        }
        [int]$left=0; [int]$top=0; [int]$width=$state.Width; [int]$height=$state.Height
        if (-not [int]::TryParse([string](Get-AegisNativeField $Target 'Left' ''),[ref]$left) -or -not [int]::TryParse([string](Get-AegisNativeField $Target 'Top' ''),[ref]$top)) { $failure.Reason='InvalidMovePosition'; return $failure }
        $resize=Get-AegisNativeField $Target 'Resize' $null
        if ($resize -isnot [bool]) { $failure.Reason='InvalidResizeFlag'; return $failure }
        if ($resize) {
            if (-not [int]::TryParse([string](Get-AegisNativeField $Target 'Width' ''),[ref]$width) -or -not [int]::TryParse([string](Get-AegisNativeField $Target 'Height' ''),[ref]$height) -or $width -le 0 -or $height -le 0) { $failure.Reason='InvalidMoveSize'; return $failure }
            if ($width -eq $state.Width -and $height -eq $state.Height) { $resize=$false }
            elseif (-not $state.Resizable) { $failure.Reason='FixedWindowResizePreserved'; return $failure }
            elseif (-not [bool](Get-AegisNativeField $Window 'MinMaxReady' $false)) { $failure.Reason='ResizeConstraintsUnavailable'; return $failure }
            if ($resize) {
                foreach ($axis in @(@('Width','MinWidth','MaxWidth',$width),@('Height','MinHeight','MaxHeight',$height))) {
                    [int]$minimum=0; [int]$maximum=0
                    if (-not [int]::TryParse([string](Get-AegisNativeField $Window $axis[1] ''),[ref]$minimum) -or -not [int]::TryParse([string](Get-AegisNativeField $Window $axis[2] ''),[ref]$maximum) -or $minimum -lt 1 -or $maximum -lt 0 -or [int]$axis[3] -lt $minimum -or ($maximum -gt 0 -and [int]$axis[3] -gt $maximum)) { $failure.Reason='TargetViolatesAppBounds'; return $failure }
                }
            }
        }
        $inside=$false
        foreach ($monitor in $context.Monitors) {
            if ([long]$left -ge [long]$monitor.Left -and [long]$top -ge [long]$monitor.Top -and ([long]$left+$width) -le ([long]$monitor.Left+$monitor.Width) -and ([long]$top+$height) -le ([long]$monitor.Top+$monitor.Height)) { $inside=$true; break }
        }
        if (-not $inside) { $failure.Reason='TargetOutsideWorkArea'; return $failure }
        # Recheck cheap user-state flags immediately before the only write. A
        # transition can still race this read; crucially the write has NO SHOW,
        # HIDE, ACTIVATE or Z-order effect and recovery never changes show state.
        if (-not $api::IsWindowVisible($handle) -or $api::IsIconic($handle) -or $api::IsZoomed($handle) -or -not $api::IsWindowEnabled($handle) -or $api::IsHungAppWindow($handle)) { $failure.Reason='WindowStateChangedBeforeMove'; return $failure }
        [uint32]$flags=0x4214 # ASYNCWINDOWPOS | NOACTIVATE | NOZORDER | NOOWNERZORDER
        if (-not $resize) { $flags=$flags -bor 1 }
        $api::SetLastError(0); $requestEntered=$true
        $accepted=$api::SetWindowPos($handle,[IntPtr]::Zero,$left,$top,$width,$height,$flags)
        $errorCode=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
        if ($accepted) { return @{ Accepted=$true; RequestIssued=$true; MayBePending=$true; ErrorCode=0; Reason='Accepted' } }
        return @{ Accepted=$false; RequestIssued=$true; MayBePending=$false; ErrorCode=$errorCode; Reason='MoveRejected' }
    } catch {
        if ($isObserve) { $observed.SameIdentity=$false; $observed.Reason='NativeException'; $observed.Detail=$_.Exception.Message; return $observed }
        return @{ Accepted=$false; RequestIssued=$requestEntered; MayBePending=$requestEntered; ErrorCode=0; Reason='NativeException'; Detail=$_.Exception.Message }
    }
}
