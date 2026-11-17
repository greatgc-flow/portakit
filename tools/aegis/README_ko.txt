Aegis 4.1.0-ps2 — PortaKit 창 정렬 도구

1. 실행
=======
Start-Aegis.cmd를 실행하면 하나의 PowerShell 작업 세션에서 메뉴를 사용합니다.
처음에는 설정 파일을 최초 1회 준비하고 Inspect로 현재 상태를 확인합니다.
정렬/복귀/재분할/Undo는 메뉴에서 명시적으로 선택해야 실행됩니다.
자동 재정렬, 상주 타이머, 서비스, 네트워크 기능을 추가하지 않습니다.

기본 데이터 위치는 프로그램 폴더의 형제 폴더인 aegis-data입니다.
예: 프로그램 portable\aegis / 사용자 데이터 portable\aegis-data.
기존 사용자 CSV는 시작할 때 덮어쓰지 않습니다. 쓰기 권한이 없으면 승인된 경로를 지정합니다.
  powershell.exe -NoProfile -File .\Aegis.Menu.ps1 -DataDirectory "D:\Approved\AegisData"
프로필은 선택한 데이터 폴더의 profiles 아래에 저장합니다. 저장/불러오기는 명시적 동작입니다.
프로그램 설치 폴더는 데이터 저장 위치로 사용하지 않습니다.

2. 같은 세션에서 작업
====================
메뉴의 미리보기, 정렬, 제자리 복귀, 작업 크기 유지 복귀, 티어/그룹 재분할,
Undo, 설정 편집, 프로필 저장/불러오기를 같은 PowerShell 호스트에서 사용합니다.
일반 Return은 저장된 정상 크기/위치로 복귀합니다. KeepSize는 작업 크기를 유지합니다.
Reflow는 편집한 CSV를 다시 읽어 배치를 재계산합니다.

정상 홈/Undo/미확인 요청(Pending)은 세션 상태입니다. 저장 프로필은 정상 홈과 정책을
보존하지만 Undo/Pending을 저장하지 않습니다. Pending이 남으면 상태를 먼저 확인합니다.
새 PowerShell을 열어 미확인 요청 보호를 우회하지 마세요. 실행 중인 메뉴는 중복 실행을 막습니다.
세션을 끝낸 뒤 다시 사용하려면 저장한 프로필을 명시적으로 불러오거나 새 배치를 설정합니다.

3. 프로세스별 설정
=================
데이터 폴더의 Aegis.Processes.csv를 편집합니다. 예시는 procexp / putty / notepad입니다.
실제 사용할 프로세스로 바꾸고 Include, Tier, GroupId, Priority, SizeMode, Width, Height를 지정합니다.
프로세스명은 경로 없이 실행 파일 이름이며 .exe는 생략해도 됩니다.
ProcessName/ClassName은 OrdinalIgnoreCase, Title은 Ordinal로 정확히 비교합니다.
Id/GroupId는 ASCII 영문/숫자/점/밑줄/하이픈 1~64자만 허용합니다.
유니코드 ProcessName/ClassName/Title에는 위 ASCII 식별자 제한을 적용하지 않습니다.

Tier: 3,2,1 순서로 최소 공간을 확보한 뒤 남는 공간을 가중 배분합니다.
GroupPriority: 같은 티어 안의 그룹 수용 순서. Priority: 같은 그룹 안의 창 수용 순서.
같은 티어/그룹의 규칙은 GroupPriority와 GroupWeight가 같아야 합니다.
Exact: 지정한 폭/높이를 요구합니다. Preferred: 가능한 범위에서 지정 크기를 우선합니다.
Preserve: 현재 크기를 유지합니다. Fill: 허용된 셀 영역을 앱 제약 안에서 채웁니다.
Width/Height는 현재 DPI 좌표 문맥의 창 전체 사각형 기준이며 클라이언트 영역 크기가 아닙니다.

4. 창 상태와 동작 범위
=====================
허용목록의 보이는 일반 창을 대상으로 합니다. 작은 크기만으로 제외하지 않습니다.
숨김/최소화/최대화 창을 강제로 복원하지 않으며 예약 홈을 유지합니다.
트레이에서 앱을 사용자가 다시 표시한 뒤 복귀를 실행할 수 있습니다.
창 identity나 재연결이 모호하면 보류합니다. KeepSize 목표가 겹치면 관련 창을 보류합니다.
제약이나 모니터/DPI/세션 문맥을 확인할 수 없으면 이동하지 않습니다.
순간적인 외부 변경과 OS 요청을 원자적으로 통제하는 기능은 제공하지 않습니다.
시간 제한은 협력적 예산이며 진행 중인 OS 호출을 강제 취소하지 않습니다.

5. 독립 스크립트 사용
====================
PortaKit/Python 없이 기존 PowerShell 창에서 Aegis.ps1과 자신의 CSV로 사용할 수 있습니다.
  & .\Aegis.ps1 -ConfigPath .\Aegis.Processes.csv
  & .\Aegis.ps1 -Action Arrange -ConfigPath .\Aegis.Processes.csv
  & .\Aegis.ps1 -Action Return -RuleIds terminal
  & .\Aegis.ps1 -Action Return -RuleIds terminal -KeepSize
  & .\Aegis.ps1 -Action Reflow -Tier 2 -GroupId work -Preview
  & .\Aegis.ps1 -Action SaveProfile -ProfilePath .\Aegis.Home.xml
  & .\Aegis.ps1 -Action LoadProfile -ProfilePath .\Aegis.Home.xml
이 명령들도 같은 PowerShell 세션에서 실행합니다. 자동 실행 정책 우회나 권한 상승은 하지 않습니다.
PS2 기능을 설치하거나 -Version 2를 강제로 적용하지 않습니다.

6. 설치/업데이트/제거
====================
PortaKit은 버전과 SHA-256이 고정된 ZIP을 설치합니다. 승인된 ZIP의 --archive 오프라인 경로도 같습니다.
프로그램 portable\aegis와 별도 portable\aegis-data를 구분합니다.
PortaKit 업데이트/제거는 aegis 설치 폴더를 대상으로 하며 형제 aegis-data는 보존합니다.
사용자 데이터 경로를 별도로 옮겼다면 다음 실행에서 같은 -DataDirectory를 지정합니다.
정렬 메뉴를 닫은 뒤 업데이트하세요. 저장한 설정/프로필은 별도 백업할 수 있습니다.

7. 검증 범위
============
소스 대상은 Windows PowerShell 2.x/CLR2입니다. 소스 정적 검사 및 함수/모의 경계 검사는
실제 PS2/CLR2 엔진 또는 실제 Windows 업무 앱의 성공을 증명하지 않습니다.
실제 운영 자원 사용, 트레이 수명, RDP/혼합 DPI 실측은 이번 폐쇄망 작업 범위 밖입니다.
결과 반출이나 추가 현장 수행을 이번 코드 작업의 완료 조건으로 두지 않습니다.
배포 ZIP에는 실행에 필요한 파일과 SHA256SUMS.txt만 들어갑니다.
개발 소스/테스트/CI 설명은 PortaKit 저장소 tools/aegis 및 docs/AEGIS.md를 참고하세요.

라이선스: 동봉 LICENSE.txt (MIT).
