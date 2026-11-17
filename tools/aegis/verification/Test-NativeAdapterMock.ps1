#requires -version 7.4
<#
Development-only tests of the actual native adapter using managed Win32-shaped
mocks. Add-Type is used only in this harness, never in the product. No real
Windows windows are read or changed. PS2/Windows execution is NOT_RUN.
#>
param([string]$ScriptPath='', [string]$NativePath='', [string]$ReportPath='')
$ErrorActionPreference='Stop'
$started=[DateTime]::UtcNow.ToString('o')
$results=New-Object Collections.ArrayList
function Assert-Mock([bool]$Condition,[string]$Name) {
    $status='PASS'; if (-not $Condition) { $status='FAIL'; Write-Host ('FAIL: '+$Name) }
    [void]$results.Add([pscustomobject]@{Id=('NM{0:D3}' -f ($results.Count+1));Name=$Name;Status=$status})
}
$source='';$sourceHash='';$failureDetail=''
try {
    if ($ScriptPath -ne '' -and $NativePath -ne '') { throw 'Specify ScriptPath or NativePath.' }
    if ($ScriptPath -eq '' -and $NativePath -eq '') { $ScriptPath=Join-Path (Split-Path -Parent $PSScriptRoot) 'Aegis.ps1' }
    if ($ScriptPath -ne '') { $source=(Resolve-Path -LiteralPath $ScriptPath).ProviderPath; . $source -Action Library }
    else { $source=(Resolve-Path -LiteralPath $NativePath).ProviderPath; . $source }
    $sourceHash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
    Initialize-AegisNative
    $emittedApi=$script:AegisNativeApiType; $firstTypes=$script:AegisNativeTypes
    Initialize-AegisNative
    Assert-Mock ([object]::ReferenceEquals($firstTypes,$script:AegisNativeTypes)) 'Successful native initialization reuses verified type dictionary'
    Assert-Mock ($null -eq $emittedApi.GetMethod('SetWindowPlacement') -and $null -eq $emittedApi.GetMethod('SetForegroundWindow')) 'Operational native metadata has no placement/show-state or foreground write imports'
    Assert-Mock ($null -ne $emittedApi.GetMethod('EnumDisplayMonitors') -and $null -ne $emittedApi.GetMethod('WTSQuerySessionInformationW')) 'Context observation imports are present'
    foreach ($pair in @(@('Rect',16),@('Point',8),@('MinMaxInfo',40),@('Placement',44),@('MonitorInfo',40),@('FileTime',8))) {
        Assert-Mock ([Runtime.InteropServices.Marshal]::SizeOf([Activator]::CreateInstance($script:AegisNativeTypes[$pair[0]])) -eq $pair[1]) ('ABI size: '+$pair[0])
    }
    Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public delegate bool AegisV4Enum(IntPtr h,IntPtr p);
public delegate bool AegisV4MonitorEnum(IntPtr h,IntPtr dc,IntPtr r,IntPtr p);
[StructLayout(LayoutKind.Sequential)] public struct AegisV4Rect { public int Left,Top,Right,Bottom; }
[StructLayout(LayoutKind.Sequential)] public struct AegisV4Point { public int X,Y; }
[StructLayout(LayoutKind.Sequential)] public struct AegisV4Time { public uint Low,High; }
[StructLayout(LayoutKind.Sequential)] public struct AegisV4Mmi { public int ReservedX,ReservedY,MaxSizeX,MaxSizeY,MaxPositionX,MaxPositionY,MinTrackX,MinTrackY,MaxTrackX,MaxTrackY; }
[StructLayout(LayoutKind.Sequential)] public struct AegisV4Placement { public int length,flags,showCmd,minX,minY,maxX,maxY,nLeft,nTop,nRight,nBottom; }
[StructLayout(LayoutKind.Sequential)] public struct AegisV4Monitor { public int Size,MonitorLeft,MonitorTop,MonitorRight,MonitorBottom,WorkLeft,WorkTop,WorkRight,WorkBottom,Flags; }
public class AegisV4Row {
 public int Id,Left=-1800,Top=20,Width=800,Height=600; public uint Pid,Tid;
 public string Name="editor",Class="UnitTestClass",Title="Editor";
 public bool Visible=true,Enabled=true,Minimized,Maximized,Hung,Cloaked,Fixed,Owned;
 public int Monitor=1;
 public AegisV4Row(int i) { Id=i; Pid=(uint)i+1000;Tid=(uint)i+2000; }
}
public static class AegisV4Mock {
 public static Dictionary<int,AegisV4Row> Rows;
 public static int Moves,ProcessTimes,Messages,RectReads,PlacementReads,NameReads,DesktopOpens,DesktopCloses,SessionAllocs,SessionFrees,EnumDelay,MonitorShift,SessionState,SessionId,VisibleReads,HideOnFinal,DcAcquired,DcReleased,ThreadAwareness,ProcessAwareness,SystemDpi;
 public static uint LastFlags,LastTimeout;
 public static bool TwoMonitors,CursorUnavailable;
 public static int SwitchMonitorOnRect;
 public static bool AccessDenied,ClassUnreadable,OwnerUnreadable,ThrowOnRead,StyleUnreadable,RectUnavailable,MinMaxUnavailable,RejectMove,ThrowDuringMove,MonitorUnavailable,NoMonitors,DesktopUnavailable,SessionUnavailable,ThreadDpiUnavailable,ProcessDpiUnavailable,LegacyDpiUnavailable,DcUnavailable,LegacyAware,ReleaseDcFailure,ProcessNameChanges;
 public static string InputDesktop="Default",ThreadDesktop="Default",Station="WinSta0";
 public static void Reset() {
  Rows=new Dictionary<int,AegisV4Row>();for(int i=101;i<=111;i++) Rows[i]=new AegisV4Row(i);
  Rows[102].Fixed=true; Rows[102].Width=180;Rows[102].Height=120;Rows[102].Title="";
  Rows[103].Name="excluded";Rows[104].Minimized=true;Rows[105].Visible=false;Rows[106].Maximized=true;
  Rows[107].Hung=true;Rows[108].Cloaked=true;Rows[109].Enabled=false;Rows[110].Class="WorkerW";Rows[111].Pid=9000;
  Moves=ProcessTimes=Messages=RectReads=PlacementReads=NameReads=DesktopOpens=DesktopCloses=SessionAllocs=SessionFrees=EnumDelay=MonitorShift=SessionState=VisibleReads=HideOnFinal=0;
  SessionId=1;LastFlags=LastTimeout=0;DcAcquired=DcReleased=0;ThreadAwareness=-4;ProcessAwareness=2;SystemDpi=96;LegacyAware=true;ThreadDpiUnavailable=ProcessDpiUnavailable=LegacyDpiUnavailable=DcUnavailable=ReleaseDcFailure=ProcessNameChanges=false;
  AccessDenied=ClassUnreadable=OwnerUnreadable=ThrowOnRead=StyleUnreadable=RectUnavailable=MinMaxUnavailable=RejectMove=ThrowDuringMove=MonitorUnavailable=NoMonitors=DesktopUnavailable=SessionUnavailable=false;
  InputDesktop=ThreadDesktop="Default";Station="WinSta0";
  TwoMonitors=CursorUnavailable=false;SwitchMonitorOnRect=0;
 }
 static AegisV4Row R(IntPtr h) { return Rows[(int)h]; }
 public static void SetLastError(uint n) { Marshal.SetLastPInvokeError((int)n); }
 public static uint GetCurrentProcessId() { return 9000; }
 public static uint GetCurrentThreadId() { return 9001; }
 public static bool ProcessIdToSessionId(uint p,ref uint s) { s=(uint)SessionId;return true; }
 public static IntPtr GetConsoleWindow() { return IntPtr.Zero; }
 public static IntPtr OpenProcess(uint a,bool b,uint p) { if(AccessDenied) {Marshal.SetLastPInvokeError(5);return IntPtr.Zero;} return (IntPtr)p; }
 public static bool CloseHandle(IntPtr h) { return true; }
 public static bool GetProcessTimes(IntPtr h,ref AegisV4Time c,ref AegisV4Time e,ref AegisV4Time k,ref AegisV4Time u) { ProcessTimes++;c.Low=42;c.High=1234;return true; }
 public static bool QueryFullProcessImageNameW(IntPtr h,uint f,StringBuilder b,ref uint n) {NameReads++;string name="unknown";foreach(var r in Rows.Values)if(r.Pid==(uint)h)name=r.Name;if(ProcessNameChanges&&ProcessTimes>0)name="changed-image";b.Append("/mock/"+name+".exe");n=(uint)b.Length;return true;}
 public static IntPtr SetThreadDpiAwarenessContext(IntPtr h) {return (IntPtr)(-2);}
 public static IntPtr GetThreadDpiAwarenessContext() {if(ThreadDpiUnavailable)throw new EntryPointNotFoundException();return (IntPtr)ThreadAwareness;}
 public static bool AreDpiAwarenessContextsEqual(IntPtr a,IntPtr b) {return a==b;}
 public static int GetAwarenessFromDpiAwarenessContext(IntPtr h) {return h==(IntPtr)(-1)?0:(h==(IntPtr)(-2)?1:2);}
 public static int GetProcessDpiAwareness(IntPtr h,ref int a) {if(ProcessDpiUnavailable)throw new DllNotFoundException();a=ProcessAwareness;return 0;}
 public static bool IsProcessDPIAware() {if(LegacyDpiUnavailable)throw new EntryPointNotFoundException();return LegacyAware;}
 public static IntPtr GetDC(IntPtr h) {if(DcUnavailable)return IntPtr.Zero;DcAcquired++;return (IntPtr)800;}
 public static int GetDeviceCaps(IntPtr h,int i) {return SystemDpi;}
 public static int ReleaseDC(IntPtr h,IntPtr dc) {DcReleased++;return ReleaseDcFailure?0:1;}
 public static IntPtr GetProcessWindowStation() {return (IntPtr)701;}
 public static IntPtr GetThreadDesktop(uint t) {return (IntPtr)702;}
 public static IntPtr OpenInputDesktop(uint f,bool i,uint a) { if(DesktopUnavailable) {Marshal.SetLastPInvokeError(5);return IntPtr.Zero;}DesktopOpens++;return (IntPtr)703;}
 public static bool CloseDesktop(IntPtr h) {DesktopCloses++;return true;}
 public static bool GetUserObjectInformationW(IntPtr h,int i,StringBuilder b,uint n,ref uint need) {string v=h==(IntPtr)701?Station:(h==(IntPtr)702?ThreadDesktop:InputDesktop);b.Append(v);need=(uint)(v.Length+1)*2;return true;}
 public static bool WTSQuerySessionInformationW(IntPtr s,uint id,int c,ref IntPtr p,ref uint n) {if(SessionUnavailable){Marshal.SetLastPInvokeError(5);return false;}p=Marshal.AllocHGlobal(4);Marshal.WriteInt32(p,SessionState);n=4;SessionAllocs++;return true;}
 public static void WTSFreeMemory(IntPtr p) {Marshal.FreeHGlobal(p);SessionFrees++;}
 public static bool EnumDisplayMonitors(IntPtr d,IntPtr r,AegisV4MonitorEnum c,IntPtr p) {if(NoMonitors)return false;return c((IntPtr)1,IntPtr.Zero,IntPtr.Zero,p) && (!TwoMonitors || c((IntPtr)2,IntPtr.Zero,IntPtr.Zero,p));}
 public static bool EnumWindows(AegisV4Enum c,IntPtr p) {if(EnumDelay>0)System.Threading.Thread.Sleep(EnumDelay);foreach(int id in Rows.Keys)if(!c((IntPtr)id,p))return false;return true;}
 public static bool IsWindow(IntPtr h) {if(ThrowOnRead)throw new InvalidOperationException("ReadFault");return Rows.ContainsKey((int)h);}
 public static bool IsWindowVisible(IntPtr h) {if(HideOnFinal==(int)h){VisibleReads++;if(VisibleReads>=2)R(h).Visible=false;}return R(h).Visible;}
 public static bool IsWindowEnabled(IntPtr h) {return R(h).Enabled;}
 public static bool IsIconic(IntPtr h) {return R(h).Minimized;}
 public static bool IsZoomed(IntPtr h) {return R(h).Maximized;}
 public static bool IsHungAppWindow(IntPtr h) {return R(h).Hung;}
 public static IntPtr GetWindow(IntPtr h,uint f) {return R(h).Owned?(IntPtr)101:IntPtr.Zero;}
 public static int GetWindowLongW(IntPtr h,int i) {if(StyleUnreadable){Marshal.SetLastPInvokeError(5);return 0;}return i==-16&&!R(h).Fixed?0x40000:0;}
 public static bool GetWindowRect(IntPtr h,ref AegisV4Rect r) {RectReads++;if(RectUnavailable){Marshal.SetLastPInvokeError(5);return false;}var a=R(h);if(SwitchMonitorOnRect==(int)h){a.Monitor=2;a.Left=20;}r.Left=a.Left;r.Top=a.Top;r.Right=a.Left+a.Width;r.Bottom=a.Top+a.Height;return true;}
 public static bool GetWindowPlacement(IntPtr h,ref AegisV4Placement p) {PlacementReads++;var a=R(h);p.length=44;p.showCmd=a.Minimized?2:(a.Maximized?3:1);p.nLeft=a.Left;p.nTop=a.Top;p.nRight=a.Left+a.Width;p.nBottom=a.Top+a.Height;return true;}
 public static int GetWindowTextLengthW(IntPtr h) {return R(h).Title.Length;}
 public static int GetWindowTextW(IntPtr h,StringBuilder b,int n) {string t=R(h).Title;if(t.Length>=n)t=t.Substring(0,n-1);b.Append(t);return b.Length;}
 public static int GetClassNameW(IntPtr h,StringBuilder b,int n) {if(ClassUnreadable){Marshal.SetLastPInvokeError(5);return 0;}b.Append(R(h).Class);return b.Length;}
 public static uint GetWindowThreadProcessId(IntPtr h,ref uint p) {if(OwnerUnreadable){p=0;Marshal.SetLastPInvokeError(5);return 0;}p=R(h).Pid;return R(h).Tid;}
 public static bool SetWindowPos(IntPtr h,IntPtr z,int x,int y,int w,int t,uint f) {Moves++;LastFlags=f;if(RejectMove){Marshal.SetLastPInvokeError(5);return false;}var r=R(h);r.Left=x;r.Top=y;if((f&1)==0){r.Width=w;r.Height=t;}if(ThrowDuringMove)throw new InvalidOperationException("WriteCompletionUnknown");return true;}
 public static IntPtr GetForegroundWindow() {return (IntPtr)101;}
 public static IntPtr SendMessageTimeoutW(IntPtr h,uint m,UIntPtr w,ref AegisV4Mmi p,uint f,uint t,ref UIntPtr r) {Messages++;LastTimeout=t;if(MinMaxUnavailable)return IntPtr.Zero;p.MinTrackX=100;p.MinTrackY=80;return (IntPtr)1;}
 public static bool GetCursorPos(ref AegisV4Point p) {p.X=-1800;p.Y=100;return !CursorUnavailable;}
 public static IntPtr MonitorFromPoint(AegisV4Point p,uint f) {return (IntPtr)1;}
 public static IntPtr MonitorFromWindow(IntPtr h,uint f) {return (IntPtr)R(h).Monitor;}
 public static bool GetMonitorInfoW(IntPtr h,ref AegisV4Monitor m) {if(MonitorUnavailable)return false;m.WorkLeft=h==(IntPtr)1?-1920:0;m.WorkTop=0;m.WorkRight=h==(IntPtr)1?MonitorShift:1920;m.WorkBottom=1040;return true;}
 public static int GetSystemMetrics(int x) {return x==34?112:27;}
 public static int DwmGetWindowAttribute(IntPtr h,uint a,ref int v,uint n) {v=R(h).Cloaked?1:0;return 0;}
}
'@
    function Initialize-AegisNative { }
    function Test-AegisNativeWindows { return $true }
    $script:AegisNativeApiType=[AegisV4Mock]
    $script:AegisNativeTypes=@{ Rect=[AegisV4Rect];Point=[AegisV4Point];MinMaxInfo=[AegisV4Mmi];Placement=[AegisV4Placement];MonitorInfo=[AegisV4Monitor];FileTime=[AegisV4Time];EnumCallback=[AegisV4Enum];MonitorCallback=[AegisV4MonitorEnum] }
    [AegisV4Mock]::Reset()
    Set-StrictMode -Version 2.0
    $rules=@(@{Id='editor';ProcessName='editor';Include=$true})
    $options=@{TotalTimeoutMs=10000;QueryTimeoutMs=50;MaxWindows=64;MaxEnumeratedWindows=2048}
    $inventory=Get-AegisInventory -Options $options -Rules $rules
    $one=$inventory.Windows[0];$small=$inventory.Windows[1]
    Assert-Mock ($inventory.Complete -and $inventory.DesktopSafe) 'Normal connected desktop yields complete inventory'
    Assert-Mock (@($inventory.Windows).Count -eq 11) 'One inventory row per enumerated HWND'
    Assert-Mock ($inventory.SelectedCount -eq 2 -and @($inventory.Windows|Where-Object {$_.Selected}).Count -eq 2) 'Only explicit allowed visible normal windows receive snapshots'
    Assert-Mock ([AegisV4Mock]::ProcessTimes -eq 2 -and [AegisV4Mock]::Messages -eq 1 -and [AegisV4Mock]::RectReads -eq 2) 'Excluded/state-preserved rows avoid detailed identity, rectangle and minmax messages'
    Assert-Mock ($one.ProcessStart -eq '000004D20000002A' -and $one.SnapshotReady -and $one.MinMaxReady) 'Selected identity and app bounds are ready'
    Assert-Mock ($small.Title -eq '' -and $small.Width -eq 180 -and $small.Height -eq 120 -and $small.MinWidth -eq 180) 'Small fixed untitled window remains movable with actual-size constraints'
    Assert-Mock ($inventory.Windows[3].SelectionReason -eq 'MinimizedWindowPreserved' -and $inventory.Windows[4].SelectionReason -eq 'HiddenWindowPreserved' -and $inventory.Windows[5].SelectionReason -eq 'MaximizedWindowPreserved') 'Minimized, hidden and maximized intent is preserved at inventory'
    Assert-Mock ($inventory.Windows[10].SelectionReason -eq 'OwnHostWindow') 'Own process is excluded before name/detail queries'
    Assert-Mock ($inventory.TopologySignature -eq 'Thread:PerMonitorV2;SystemDpi=96,96|1,-1920,0,1920,1040') 'Topology captures monitor handle and work area including negative coordinates'
    Assert-Mock ([AegisV4Mock]::DesktopOpens -eq [AegisV4Mock]::DesktopCloses -and [AegisV4Mock]::SessionAllocs -eq [AegisV4Mock]::SessionFrees) 'Context releases owned desktop and WTS buffers'
    Assert-Mock ($inventory.CoordinateKnown -and $inventory.CoordinateSignature -eq 'Thread:PerMonitorV2;SystemDpi=96,96' -and [AegisV4Mock]::DcAcquired -eq [AegisV4Mock]::DcReleased) 'Coordinate context records thread awareness/system DPI and releases screen DC'
    $observation=Invoke-AegisNative Observe $one
    Assert-Mock ($observation.SameIdentity -and $observation.RectReady -and $observation.StyleReady -and $observation.Visible -and -not $observation.Minimized) 'Observe includes fresh user-state flags and geometry'
    $target=@{Left=-1700;Top=80;Width=640;Height=480;Resize=$true;ExpectedRect=@{Left=-1800;Top=20;Width=800;Height=600};ExpectedMonitor=$one.Monitor;ExpectedTopologySignature=$inventory.TopologySignature}
    $request=Invoke-AegisNative Move $one $target
    Assert-Mock ($request.Accepted -and $request.RequestIssued -and $request.MayBePending -and [AegisV4Mock]::LastFlags -eq 0x4214) 'Resize request is async, preserves visibility, activation and Z order'
    $request=Invoke-AegisNative Move $small @{Left=-1700;Top=600;Resize=$false}
    Assert-Mock ($request.Accepted -and [AegisV4Mock]::LastFlags -eq 0x4215 -and [AegisV4Mock]::Rows[102].Width -eq 180) 'Move-only uses NOSIZE for small fixed window'
    $before=[AegisV4Mock]::Moves
    foreach ($operation in @('Restore','Place','Raise','Focus','Order')) {
        $request=Invoke-AegisNative $operation $one
        Assert-Mock (-not $request.Accepted -and -not $request.RequestIssued -and $request.Reason -eq 'UnsupportedOperation' -and [AegisV4Mock]::Moves -eq $before) ('Unsafe/unneeded operation is absent: '+$operation)
    }
    $plainTarget=@{Left=-1700;Top=80;Width=640;Height=480;Resize=$true}
    foreach ($property in @('Visible','Minimized','Maximized','Enabled','Hung','Cloaked')) {
        [AegisV4Mock]::Reset()
        if ($property -eq 'Visible' -or $property -eq 'Enabled') {[AegisV4Mock]::Rows[101].$property=$false} else {[AegisV4Mock]::Rows[101].$property=$true}
        $request=Invoke-AegisNative Move $one $plainTarget
        Assert-Mock (-not $request.Accepted -and -not $request.RequestIssued -and [AegisV4Mock]::Moves -eq 0) ('Prewrite state gate: '+$property)
    }
    [AegisV4Mock]::Reset();[AegisV4Mock]::HideOnFinal=101
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'WindowStateChangedBeforeMove' -and [AegisV4Mock]::Moves -eq 0) 'Hide between detailed state read and final write check prevents request'
    [AegisV4Mock]::Reset();[AegisV4Mock]::Rows[101].Class='ReusedClass'
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'IdentityMismatch' -and [AegisV4Mock]::Moves -eq 0) 'Fully read reused identity prevents request'
    [AegisV4Mock]::Reset();[AegisV4Mock]::AccessDenied=$true
    $observation=Invoke-AegisNative Observe $one
    Assert-Mock ($observation.Exists -and -not $observation.SameIdentity -and $observation.Reason -eq 'ProcessIdentityUnavailable') 'Unknown process identity is not treated as closed/reused'
    [AegisV4Mock]::Reset();[AegisV4Mock]::ClassUnreadable=$true
    $observation=Invoke-AegisNative Observe $one
    Assert-Mock ($observation.Exists -and -not $observation.SameIdentity -and $observation.Reason -eq 'WindowClassUnreadable') 'Unknown class identity remains unavailable'
    [AegisV4Mock]::Reset();[AegisV4Mock]::OwnerUnreadable=$true
    $observation=Invoke-AegisNative Observe $one
    Assert-Mock ($observation.Exists -and -not $observation.SameIdentity -and $observation.Reason -eq 'WindowOwnerUnreadable') 'Unknown owner identity remains unavailable'
    [AegisV4Mock]::Reset();[void][AegisV4Mock]::Rows.Remove(101)
    $observation=Invoke-AegisNative Observe $one
    Assert-Mock (-not $observation.Exists -and $observation.Reason -eq 'WindowMissing') 'Confirmed missing HWND is distinguished from unreadable identity'
    [AegisV4Mock]::Reset();[AegisV4Mock]::ThrowOnRead=$true
    $observation=Invoke-AegisNative Observe $one
    Assert-Mock (-not $observation.SameIdentity -and $observation.Reason -eq 'NativeException') 'Observation exceptions do not claim identity disappearance'
    [AegisV4Mock]::Reset();$bad=$one.Clone();$bad.Id='999'
    $observation=Invoke-AegisNative Observe $bad
    Assert-Mock ($observation.Reason -eq 'OriginalHandleIdMismatch') 'Corrupt original HWND/Id pair cannot authorize request'
    [AegisV4Mock]::Reset();[AegisV4Mock]::StyleUnreadable=$true
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'WindowStyleUnavailable') 'Unreadable style cannot be treated as a resizable normal window'
    [AegisV4Mock]::Reset();[AegisV4Mock]::RectUnavailable=$true
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'WindowRectUnavailable') 'Unreadable current geometry blocks request'
    [AegisV4Mock]::Reset();[AegisV4Mock]::Rows[101].Monitor=2
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'WindowMonitorChanged') 'Window moved to another monitor since plan is preserved'
    [AegisV4Mock]::Reset();[AegisV4Mock]::Rows[101].Top=99
    $request=Invoke-AegisNative Move $one $target
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'WindowGeometryChanged') 'Manual geometry change since expected observation is preserved'
    [AegisV4Mock]::Reset();[AegisV4Mock]::MonitorShift=100
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'TopologyChanged') 'Topology/work-area change blocks stale plan'
    [AegisV4Mock]::Reset();$unsafe=$one.Clone();$unsafe.MinMaxReady=$false
    $request=Invoke-AegisNative Move $unsafe $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'ResizeConstraintsUnavailable') 'Unknown app constraints block actual resizing'
    $request=Invoke-AegisNative Move $unsafe @{Left=-1700;Top=20;Resize=$false}
    Assert-Mock $request.Accepted 'Unknown app constraints still permit verified move-only request'
    [AegisV4Mock]::Reset();$tooSmall=$plainTarget.Clone();$tooSmall.Width=50
    $request=Invoke-AegisNative Move $one $tooSmall
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'TargetViolatesAppBounds') 'App minimum violations block resizing'
    $outside=$plainTarget.Clone();$outside.Left=-2000
    $request=Invoke-AegisNative Move $one $outside
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'TargetOutsideWorkArea') 'Target must fit a current monitor work area'
    [AegisV4Mock]::Reset();[AegisV4Mock]::SessionState=4
    $context=Invoke-AegisNative Context $null
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $context.DesktopSafe -and $context.Reason -eq 'SessionNotActive' -and -not $request.Accepted -and [AegisV4Mock]::Moves -eq 0) 'Disconnected RDP is blocked even if Default input desktop would be readable'
    [AegisV4Mock]::Reset();[AegisV4Mock]::SessionId=0
    $context=Invoke-AegisNative Context $null
    Assert-Mock (-not $context.DesktopSafe -and $context.Reason -eq 'SessionZeroPreserved') 'Session zero is not an interactive execution target'
    [AegisV4Mock]::Reset();[AegisV4Mock]::InputDesktop='Winlogon'
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'InputDesktopChanged') 'Secure/locked input desktop blocks request'
    [AegisV4Mock]::Reset();[AegisV4Mock]::Station='Service-0x0'
    $context=Invoke-AegisNative Context $null
    Assert-Mock (-not $context.DesktopSafe -and $context.Reason -eq 'NonInteractiveWindowStation') 'Noninteractive window station is not treated as user desktop'
    [AegisV4Mock]::Reset();[AegisV4Mock]::SessionUnavailable=$true
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'SessionStateUnavailable') 'Unreadable session status fails closed'
    [AegisV4Mock]::Reset();[AegisV4Mock]::DesktopUnavailable=$true
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'InputDesktopUnavailable') 'Unreadable input desktop fails closed'
    [AegisV4Mock]::Reset();[AegisV4Mock]::NoMonitors=$true
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'MonitorEnumerationIncomplete') 'Incomplete topology fails closed'
    [AegisV4Mock]::Reset();[AegisV4Mock]::MonitorUnavailable=$true
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'MonitorWorkAreaUnavailable') 'Unreadable monitor work area fails closed'
    [AegisV4Mock]::Reset();[AegisV4Mock]::RejectMove=$true
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.RequestIssued -and -not $request.MayBePending -and $request.ErrorCode -eq 5) 'Explicit native rejection is distinct from an accepted async request'
    [AegisV4Mock]::Reset();[AegisV4Mock]::ThrowDuringMove=$true
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.RequestIssued -and $request.MayBePending -and [AegisV4Mock]::Rows[101].Width -eq 640) 'Exception after entering native move reports uncertain completion'
    [AegisV4Mock]::Reset();$empty=Get-AegisInventory -Options $options -Rules @()
    Assert-Mock ($empty.Complete -and $empty.SelectedCount -eq 0 -and [AegisV4Mock]::ProcessTimes -eq 0 -and [AegisV4Mock]::Messages -eq 0 -and [AegisV4Mock]::RectReads -eq 0) 'Empty allowlist never queries detailed snapshots or minmax'
    [AegisV4Mock]::Reset();[AegisV4Mock]::ProcessNameChanges=$true
    $changedSelection=Get-AegisInventory -Options $options -Rules $rules
    Assert-Mock (-not $changedSelection.Windows[0].SnapshotReady -and $changedSelection.Windows[0].SelectionReason -eq 'IdentitySelectionChanged' -and [AegisV4Mock]::Messages -eq 0) 'Name selection is tied to detailed identity instead of stale per-PID cache'
    [AegisV4Mock]::Reset();$exclude=Get-AegisInventory -Options $options -Rules @(@{Id='exclude';ProcessName='editor';Include=$false},@{Id='later';ProcessName='editor';Include=$true})
    Assert-Mock ($exclude.SelectedCount -eq 0 -and [AegisV4Mock]::ProcessTimes -eq 0 -and [AegisV4Mock]::Messages -eq 0) 'First matching exclude rule prevents later include and expensive queries'
    [AegisV4Mock]::Reset();$titleMatch=Get-AegisInventory -Options $options -Rules @(@{Id='exact';ProcessName='editor';ClassName='UnitTestClass';Title='Editor';Include=$true})
    Assert-Mock ($titleMatch.SelectedCount -eq 1 -and $titleMatch.Windows[1].SelectionReason -eq 'NotAllowlisted') 'Exact process/class/title filters limit snapshots before expensive query'
    [AegisV4Mock]::Rows[101].Title='Different document'
    $request=Invoke-AegisNative Move $titleMatch.Windows[0] $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'WindowTitleChanged' -and [AegisV4Mock]::Moves -eq 0) 'Exact title selector is rechecked before writing the same HWND'
    [AegisV4Mock]::Reset();[AegisV4Mock]::Rows[101].Title=('x'*1400)
    $titleMatch=Get-AegisInventory -Options $options -Rules @(@{Id='long';ProcessName='editor';Title=('x'*512);Include=$true})
    Assert-Mock ($titleMatch.SelectedCount -eq 0) 'Truncated long title cannot match a valid exact title selector'
    [AegisV4Mock]::Reset();[AegisV4Mock]::MinMaxUnavailable=$true
    $unknown=Get-AegisInventory -Options $options -Rules $rules
    Assert-Mock ($unknown.Windows[0].SnapshotReady -and -not $unknown.Windows[0].MinMaxReady -and $unknown.Windows[0].ConstraintReason -eq 'MinMaxUnavailable') 'Geometry snapshot does not pretend app size constraints were read'
    [AegisV4Mock]::Reset();$limited=$options.Clone();$limited.MaxWindows=1
    $inventory=Get-AegisInventory -Options $limited -Rules $rules
    Assert-Mock (-not $inventory.Complete -and $inventory.Warnings -contains 'TargetWindowLimitExceeded' -and [AegisV4Mock]::Messages -eq 1) 'Target cap marks whole inventory incomplete without querying extra targets'
    [AegisV4Mock]::Reset();[AegisV4Mock]::TwoMonitors=$true;[AegisV4Mock]::Rows[101].Monitor=2;[AegisV4Mock]::Rows[101].Left=20
    $currentOnly=$options.Clone();$currentOnly.MonitorScope='CurrentMonitor';$currentOnly.MaxWindows=1
    $inventory=Get-AegisInventory -Options $currentOnly -Rules $rules
    Assert-Mock ($inventory.Complete -and $inventory.SelectedCount -eq 1 -and $inventory.Windows[1].Selected -and $inventory.Windows[0].SelectionReason -eq 'OutsideCurrentMonitor') 'An outside-monitor window cannot exhaust the current-monitor target cap'
    Assert-Mock ([AegisV4Mock]::ProcessTimes -eq 1 -and [AegisV4Mock]::RectReads -eq 1 -and [AegisV4Mock]::PlacementReads -eq 1 -and [AegisV4Mock]::Messages -eq 0) 'Outside-monitor rows avoid detailed identity, geometry, placement and minmax work'
    Assert-Mock ($inventory.Windows[0].Exists -and $inventory.Windows[0].Monitor.Id -eq '2' -and -not $inventory.Windows[0].IdentityReady -and -not $inventory.Windows[0].SnapshotReady) 'Outside-monitor hints preserve uncertainty without claiming an absent or verified identity'
    [AegisV4Mock]::Reset();[AegisV4Mock]::CursorUnavailable=$true
    $inventory=Get-AegisInventory -Options $currentOnly -Rules $rules
    Assert-Mock (-not $inventory.Complete -and $inventory.Warnings -contains 'CurrentMonitorUnavailable' -and $inventory.SelectedCount -eq 0 -and [AegisV4Mock]::ProcessTimes -eq 0) 'Unknown current-monitor selection blocks before detailed target queries'
    [AegisV4Mock]::Reset();[AegisV4Mock]::TwoMonitors=$true;[AegisV4Mock]::SwitchMonitorOnRect=101
    $currentOnly.MaxWindows=64
    $inventory=Get-AegisInventory -Options $currentOnly -Rules $rules
    Assert-Mock (-not $inventory.Complete -and $inventory.Warnings -contains 'WindowMonitorChangedDuringInventory' -and -not $inventory.Windows[0].Selected -and [AegisV4Mock]::Messages -eq 0) 'A monitor change between scope selection and detailed geometry blocks the batch'
    [AegisV4Mock]::Reset();$limited=$options.Clone();$limited.MaxEnumeratedWindows=2
    $inventory=Get-AegisInventory -Options $limited -Rules $rules
    Assert-Mock (-not $inventory.Complete -and @($inventory.Windows).Count -eq 2 -and $inventory.Warnings -contains 'EnumerationLimitExceeded') 'Enumeration cap cannot silently produce a complete plan'
    [AegisV4Mock]::Reset();[AegisV4Mock]::EnumDelay=5;$limited=$options.Clone();$limited.TotalTimeoutMs=1
    $inventory=Get-AegisInventory -Options $limited -Rules $rules
    Assert-Mock (-not $inventory.Complete -and $inventory.Warnings -contains 'InventoryBudgetExceeded') 'Elapsed cooperative budget marks inventory incomplete'
    [AegisV4Mock]::Reset();[AegisV4Mock]::ThreadAwareness=-2
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'TopologyChanged') 'Changed DPI-awareness host rejects a saved geometry signature'
    [AegisV4Mock]::Reset();[AegisV4Mock]::SystemDpi=144
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $request.Accepted -and $request.Reason -eq 'TopologyChanged') 'Changed observed system DPI rejects a saved geometry signature'
    [AegisV4Mock]::Reset();[AegisV4Mock]::ThreadDpiUnavailable=$true
    $context=Invoke-AegisNative Context $null
    Assert-Mock ($context.Ready -and $context.CoordinateSignature -eq 'ProcessLevel:2;SystemDpi=96,96') 'Windows 8.1 process DPI fallback works without modern thread APIs'
    [AegisV4Mock]::ProcessDpiUnavailable=$true
    $context=Invoke-AegisNative Context $null
    Assert-Mock ($context.Ready -and $context.CoordinateSignature -eq 'LegacyProcess:Aware;SystemDpi=96,96') 'Vista/Server2008 legacy process-awareness fallback remains usable'
    [AegisV4Mock]::LegacyAware=$false
    $context=Invoke-AegisNative Context $null
    Assert-Mock ($context.Ready -and $context.CoordinateSignature -eq 'LegacyProcess:Unaware;SystemDpi=96,96') 'Legacy DPI-unaware caller receives a distinct stable signature'
    [AegisV4Mock]::LegacyDpiUnavailable=$true
    $context=Invoke-AegisNative Context $null
    $request=Invoke-AegisNative Move $one $plainTarget
    Assert-Mock (-not $context.CoordinateKnown -and $context.CoordinateSignature -eq 'CallerUnknown;SystemDpi=96,96' -and -not $request.Accepted -and $request.Reason -eq 'DpiAwarenessUnavailable') 'Unknown awareness has stable diagnostic signature and cannot authorize writes'
    [AegisV4Mock]::Reset();[AegisV4Mock]::DcUnavailable=$true
    $context=Invoke-AegisNative Context $null
    Assert-Mock (-not $context.Ready -and $context.Reason -eq 'SystemDpiUnavailable') 'Unreadable system DPI fails closed'
    [AegisV4Mock]::Reset();[AegisV4Mock]::ReleaseDcFailure=$true
    $context=Invoke-AegisNative Context $null
    Assert-Mock (-not $context.Ready -and $context.Reason -eq 'DeviceContextReleaseFailed' -and [AegisV4Mock]::DcReleased -eq 1) 'Failed DC cleanup is reported instead of silently enabling writes'
    [AegisV4Mock]::Reset();$dpi=Enter-AegisDpiContext;$exit=Exit-AegisDpiContext $dpi
    Assert-Mock ($dpi.Changed -and $dpi.Mode -eq 'PerMonitorV2' -and $exit.Accepted) 'DPI context is restored to previous thread value'
} catch {
    $failureDetail=($_.Exception.Message+' | '+$_.ScriptStackTrace)
    [void]$results.Add([pscustomobject]@{Id='HARNESS';Name='Harness completion';Status='FAIL';Detail=$failureDetail})
    Write-Host ('FAIL: '+$failureDetail)
}
$passed=@($results|Where-Object {$_.Status -eq 'PASS'}).Count
$failed=@($results|Where-Object {$_.Status -eq 'FAIL'}).Count
$report=[ordered]@{SchemaVersion=2;Suite='V4NativeAdapterMock';StartedUtc=$started;CompletedUtc=[DateTime]::UtcNow.ToString('o');PowerShellVersion=$PSVersionTable.PSVersion.ToString();DotNetVersion=[Environment]::Version.ToString();Platform=[Environment]::OSVersion.Platform.ToString();AdapterNativeCallsMocked=$true;ActualWindowsIntegrationExecuted=$false;WindowsPowerShell2Executed=$false;SourcePath=$source;SourceSha256=$sourceHash;Passed=$passed;Failed=$failed;Total=$results.Count;Results=@($results.ToArray())}
if ($ReportPath -ne '') { $report|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $ReportPath -Encoding utf8NoBOM }
if ($failed -gt 0) { throw ('Native adapter: '+$failed+' failures of '+$results.Count) }
Write-Host ('PASS '+$passed+' native adapter mock checks; actual Windows / PS2 NOT_RUN.')
