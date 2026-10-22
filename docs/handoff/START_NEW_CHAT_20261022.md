# PortaKit — 2026-10-22 최신 인수인계 복원·작업 재개

내 GitHub 저장소 **greatgc-flow/portakit**에서 진행한 폐쇄망 Windows 기업용 무료 포터블 툴셋 개발을 이전 채팅의 **최신 검증 상태 그대로** 이어가 줘.

**보안:** GitHub에서 2026-10-22 확인 당시 이 저장소는 **Public**이었다. 개인적인 채팅 메모리, 실제 회사/서버 세부사항, 내부 로그, 자격증명, 비공개 파일 또는 로컬 증적을 Public 저장소에 올리지 말고, 공개 가능한 PortaKit 범용 소스와 프로젝트 기술 정보만 기록해.

## 1. 최신 원본 우선 복구

먼저 GitHub 연결 앱으로 현재 main 최신 HEAD·커밋, 공개 여부, 열린 PR·Issues, Actions와 주요 워크플로를 **실제로 조회**해. 이전 인수인계 작업 시작 전 기준 main HEAD는 **09bd9fb0f44b77006f09f5d15fb4d22b3bd9dc25**이지만 이후 인수인계 커밋이 있으므로 **최신 main을 항상 우선**해.

다음 문서를 순서대로 읽어:
1. docs/handoff/2026-10-22_FULL_CONTEXT.md — 이 채팅의 프로젝트 목표, 요청과 결정, 18개 병합 PR, 테스트, 파일 맵, 미완료 과제
2. docs/handoff/2026-10-22_REPO_SOURCE_MAP.json — baseline main의 48개 실제 파일 경로, Git blob SHA, 크기; 현재 HEAD와 교차 대조
3. docs/HANDOFF.md, docs/DECISIONS.md, docs/SPEC.md, docs/TOOLSETS.md
4. docs/BACKLOG.md, docs/RELEASE_CHECKLIST.md
5. docs/GUI_ACCEPTANCE_20261021.md, docs/WINMERGE_OFFICE_ACCEPTANCE.md
6. catalog.json, toolsets.json, research/TOOLS_CANDIDATES_20261020.json, research/SYSINTERNALS_NETWORK_REVIEW_20261021.json
7. 현재 main의 portakit.py, scripts/, tests/, .github/workflows/ 실제 관련 소스 전체

과거 대화나 문서의 옛 수치보다 **실제 Git 파일·최신 Actions 증거**를 우선하고, 확인된 사실/추정/미확인을 구분해.

## 2. 인수인계 시점의 확정 기술 현황

- Windows 전용, Python 3.11+ 표준 라이브러리. 기능별 독립 모듈/테스트와 콘솔 출력의 로컬 증적을 유지하며, 별도 PowerShell 예시는 Windows PowerShell 2.0 및 5.x 호환을 고려.
- 현재 catalog.json에는 벤더 URL/고정 버전/SHA-256이 검증된 **17개 설치 가능 ID**가 있음. 단, 사용자의 PC에 모두 실제 설치되었다는 뜻은 아님.
- 연구 원장은 **108종 = 17 설치 가능 + 27 Windows 기본·선택기능 + 64 추가 연구**. 주 기능 분류 정확히 하나를 강제하는 MECE 10개 도메인: files, text, structured-data, system, network, security, development, automation, documents, transfer.
- 역할별 설치 프로필은 선택적으로 조합하되 ID 중복 설치 금지. old common/os/nw/dev/data/diag 및 minimal/mes-support/developer 명칭은 기존 대상과 동일하게 호환 유지.
- 기본은 list/plan 읽기 전용, 설치는 apply --yes만. 오프라인 개별 --archive FILE, 일괄 --offline-dir DIR는 모든 새 원본 ZIP/EXE의 존재·크기·SHA를 검사하고 안전한 설치 처리. 자동 업데이트/삭제/서비스/드라이버/레지스트리/PATH/외부 업로드 금지.
- 전체 7-Zip은 7zr 선행 설치 및 해시 검증 후, 공식 서명/해시 고정된 x64 SFX를 **설치 프로그램으로 실행하지 않고 압축 데이터로만 해제**. 실제 Windows CLI ZIP 생성/테스트 통과, GUI는 실제 사용자 검증 미완료.
- Notepad++/WinMerge 우클릭 메뉴는 옵셔널 HKCU classic, Windows11 모던 컨텍스트/WinMerge 2파일 ShellExtension은 미구현.
- Everything/grepWin/7-Zip GUI: scripts/gui_acceptance.py 기본 NOT_VERIFIED 안전 검사, 명시적 --review --launch 및 Everything 추가 승인 옵션. GUI 실사용 성공 증적은 아직 없음.
- TCPView/PsPing은 Microsoft Sysinternals 기업 사용권과 바이너리 재배포 제한을 구별해 연구 메타데이터만 기록. 벤더 배포물 재패키징, 회사 법무/보안 승인 전에는 설치 가능 카탈로그로 편입하지 마.
- WinMerge의 Word/Excel/PowerPoint/Visio Office4 실제 COM/GUI 비교는 라이선스 설치 데스크톱 실검증 미완료. CI 프리체크/증적 ZIP만으로 PASS라고 하지 마.
- 공식 sd 1.1.0 ZIP 내 실행 파일이 sd 1.0.0으로 표시되는 불일치는 별도 백로그 유지.
- 출시는 자동화하지 말고 release acceptance 및 사내 사용권/보안 승인별로 게이트 유지.

이전 실제 최신 main 검증: [Windows CI 39715051982](https://github.com/greatgc-flow/portakit/actions/runs/39715051982) 성공, Python 3.11과 3.14에서 각각 **282개 테스트 PASS**. 이전 실물 검증: [39714408046](https://github.com/greatgc-flow/portakit/actions/runs/39714408046), [전체 7-Zip 39513889906](https://github.com/greatgc-flow/portakit/actions/runs/39513889906). **새 커밋에서는 실제 최신 HEAD 기준으로 다시 확인**해.

## 3. 이어서 수행할 작업

1. 이관된 자료와 최신 main의 파일·카탈로그·프로필·코드·테스트·docs/백로그를 **종·횡으로 재귀적 MECE 교차 대조**하고, 구버전 숫자·중복·누락·깨진 링크를 재확인해. 기존 git 원본은 보존하고 명확한 결함만 수정.
2. Everything·grepWin·전체 7-Zip의 실제 GUI 사용성은 승인된 테스트 PC와 사람의 확인이 필요한 영역인지 명확히 구분. 가능한 합법적·비파괴적 테스트와 증적까지 준비하되 운영 서버나 승인 없는 PC에서 GUI/서비스/네트워크를 자동 실행하지 마.
3. TCPView/PsPing의 공식 현행 라이선스, 회사 내부 반입/공유 허용 범위, EXE SHA/서명, 권한 및 네트워크 부하를 조사하고, 배포권이 모호하면 metadata-only 그대로 유지.
4. WinMerge Office4 실제 GUI/COM 검증은 미완료 상태 유지. 유효한 현장 증적이 없는 PASS 주장 금지.
5. 기업 무료·폐쇄망 안전·용량 대비 업무효율 우선으로 후보를 단계별로 확대. 임의 결정은 옵션화, null/빈 배열/충돌/복구·로그 고려, 변경과 테스트는 독립 단위로 구성.
6. 실질적 변경은 GitHub PR과 Windows 3.11/3.14 테스트, SHA 및 실제 runner 로그로 검증. 이 채팅의 핵심 지향점 Very Simple, MECE, 재사용 가능한 기능 단위, 안전한 선택 설치, 로컬 증적 보존을 유지해.

**궁극적 요구:** 작업을 실제로 진행하면서 검증된 사실과 남은 인간·법무·IT 승인을 분리해. 변경사항과 인수인계는 공개 가능한 범위만 커밋하고, 마지막에 최신 main/PR/Actions 상태를 확인해 다음 채팅에서도 완결적으로 계승할 수 있게 해.
