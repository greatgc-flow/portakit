#requires -version 7.4
<#
Verification tool, run on the development host. The product does not need it.
Requires Microsoft PSScriptAnalyzer 1.24.0 (or specify its module manifest path).
These are static checks against a PS2 target, not execution on the PS2 engine.
#>
param([string]$ScriptPath='', [string]$AnalyzerPath='', [string]$ReportPath='', [switch]$IncludeFieldTools)
$ErrorActionPreference='Stop'
if ([string]::IsNullOrEmpty($ScriptPath)) {$ScriptPath=Join-Path (Split-Path -Parent $PSScriptRoot) 'Aegis.ps1'}
$sourcePath=(Resolve-Path -LiteralPath $ScriptPath).ProviderPath
if ([string]::IsNullOrEmpty($AnalyzerPath)) {Import-Module PSScriptAnalyzer -RequiredVersion 1.24.0}
else {Import-Module $AnalyzerPath}
$configuration=@{
    IncludeRules=@('PSUseCompatibleSyntax','PSUseCompatibleCmdlets','PSAvoidAssignmentToAutomaticVariable')
    Rules=@{
        PSUseCompatibleSyntax=@{Enable=$true;TargetVersions=@('2.0')}
        PSUseCompatibleCmdlets=@{compatibility=@('desktop-2.0-windows')}
    }
}
$tokens=$null;$parseErrors=$null
$null=[System.Management.Automation.Language.Parser]::ParseFile($sourcePath,[ref]$tokens,[ref]$parseErrors)
$diagnostics=@(Invoke-ScriptAnalyzer -Path $sourcePath -Settings $configuration)
$bytes=[IO.File]::ReadAllBytes($sourcePath)
$bom=($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191)
$source=[IO.File]::ReadAllText($sourcePath)
$crlf=($source -notmatch '(?<!\r)\n')
$passed=(@($parseErrors).Count -eq 0 -and $diagnostics.Count -eq 0 -and $bom -and $crlf)
$fieldTools=[Collections.Generic.List[object]]::new()
if ($IncludeFieldTools) {
    $packageRoot=Split-Path -Parent $sourcePath
    foreach ($relative in @('Aegis.Menu.ps1','tests/Test-AegisMenu.ps1','tests/Test-AegisV4.ps1','tests/Controller-V4-Cases.ps1','tests/Test-StorageV4.ps1','tests/Test-EntryPointV4.ps1','tests/ReportPathSafety.ps1','verification/Test-LayoutV4.ps1','verification/Test-WindowsPreflight.ps1','verification/Test-AegisServer.ps1','verification/Server-Check-Cases.ps1','verification/Test-ReportPathSafety.ps1','verification/Test-AlgorithmBoundaries.ps1')) {
        $fieldPath=Join-Path $packageRoot $relative
        if (-not (Test-Path -LiteralPath $fieldPath -PathType Leaf)) { throw ('Required field tool missing: '+$relative) }
        $fieldTokens=$null;$fieldErrors=$null
        $null=[System.Management.Automation.Language.Parser]::ParseFile($fieldPath,[ref]$fieldTokens,[ref]$fieldErrors)
        $fieldDiagnostics=@(Invoke-ScriptAnalyzer -Path $fieldPath -Settings $configuration)
        $fieldBytes=[IO.File]::ReadAllBytes($fieldPath)
        $fieldBom=($fieldBytes.Length -ge 3 -and $fieldBytes[0] -eq 239 -and $fieldBytes[1] -eq 187 -and $fieldBytes[2] -eq 191)
        $fieldCrLf=([IO.File]::ReadAllText($fieldPath) -notmatch '(?<!\r)\n')
        $fieldPassed=(@($fieldErrors).Count -eq 0 -and $fieldDiagnostics.Count -eq 0 -and $fieldBom -and $fieldCrLf)
        if (-not $fieldPassed) { $passed=$false }
        $fieldTools.Add([pscustomobject]@{
            SourceFile=$relative;SourceSha256=(Get-FileHash -LiteralPath $fieldPath -Algorithm SHA256).Hash.ToLowerInvariant()
            Status=$(if($fieldPassed){'PASS'}else{'FAIL'});Utf8Bom=$fieldBom;CrLfOnly=$fieldCrLf
            ParserErrorCount=@($fieldErrors).Count;DiagnosticCount=$fieldDiagnostics.Count
            ParserErrors=@($fieldErrors | Select-Object Message,ErrorId)
            Diagnostics=@($fieldDiagnostics | Select-Object RuleName,Line,Severity,Message)
        })
    }
}
$summary=[pscustomobject]@{
    Status=$(if($passed){'PASS'}else{'FAIL'})
    SourceFile='Aegis.ps1'
    SourceSha256=(Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
    PowerShellVersion=[string]$PSVersionTable.PSVersion
    AnalyzerVersion=[string](Get-Module PSScriptAnalyzer).Version
    TargetSyntax='2.0';TargetCmdlets='desktop-2.0-windows'
    ParserErrorCount=@($parseErrors).Count;DiagnosticCount=$diagnostics.Count
    Utf8Bom=$bom;CrLfOnly=$crlf
    ActualPS2Execution='NOT_RUN';WindowsNativeIntegration='NOT_RUN'
    ParserErrors=@($parseErrors | Select-Object Message,ErrorId)
    Diagnostics=@($diagnostics | Select-Object RuleName,Line,Severity,Message)
    FieldToolCount=$fieldTools.Count;FieldTools=$fieldTools
}
if (-not [string]::IsNullOrEmpty($ReportPath)) {$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ReportPath -Encoding UTF8}
$summary
if (-not $passed) {throw 'Compatibility static checks failed.'}
