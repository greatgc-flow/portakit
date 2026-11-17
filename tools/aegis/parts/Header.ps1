#requires -version 2.0
<#
Aegis 4.1.0-ps2 | Interactive, allowlisted, geometry-only window arrangement.
Default Inspect is read-only. Edit Aegis.Processes.csv, then Arrange explicitly.
Arrange establishes homes once, then returns to them. Reflow changes the layout.
Hidden/minimized/maximized windows keep their display state. No Z-order changes.
Profiles and Undo are separate. SaveProfile/LoadProfile perform explicit data I/O.
Windows PowerShell 2.x source target; see release evidence for runtime limits.
#>
[CmdletBinding()]
param(
    [ValidateSet('Inspect','Arrange','Return','Reflow','Undo','SaveProfile','LoadProfile','SelfTest','Library')][string]$Action='Inspect',
    [hashtable]$Options=@{},[object[]]$Rules=@(),[string]$ConfigPath='',
    [string]$ProfilePath='',[string[]]$RuleIds=@(),
    [ValidateRange(0,3)][int]$Tier=0,[string]$GroupId='',
    [switch]$KeepSize,[switch]$ReleaseAbsent,[switch]$Preview,
    [switch]$PassThru,[switch]$ExitWithCode
)

function Get-AegisVersion { return '4.1.0-ps2' }
