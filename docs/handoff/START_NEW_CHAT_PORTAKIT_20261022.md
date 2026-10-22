# PortaKit — 새 채팅 시작 프롬프트 (2026-10-22)

다음 내용을 새 ChatGPT 채팅 첫 메시지로 그대로 붙여넣어 줘. GitHub 저장소의 **실제 최신 상태를 먼저 확인**하고 그 증거를 우선시해.

---

내 GitHub 저장소 **[greatgc-flow/portakit](https://github.com/greatgc-flow/portakit)**에서 개발 중인 **PortaKit — 폐쇄망 기업용 Windows 포터블 소프트웨어 관리 도구** 작업을 이전 채팅에서 이어가 줘.

목표는 가볍고 기업에서 사용 가능한 무료 SW를 업무 효율 중심으로 MECE하게 관리하고, 온·오프라인 모두에서 선택적으로 설치·검증·증적·복구할 수 있는 **Very Simple**, 안전한 포터블 툴셋을 만드는 것이야. 내 확인 없이 대량 설치하거나 관리자 권한/레지스트리/서비스/네트워크 캡처를 수행하지 마.

**추가 출처 검증:** `docs/handoff/2026-10-22_REPO_SOURCE_MAP.json`에는 인수인계 이전 기준점 `09bd9fb0...`의 **실제 Git 추적 파일 48개 전부에 대한 경로·Git blob SHA·크기**가 보관되어 있어. 최신 main에 있는 이후 파일까지 포함하는 현재 원장이 아니므로 최신 Git tree를 새로 조회해 추가/수정분을 대조해.

## A. 가장 먼저 실제 최신 상태 복원

1. GitHub에서 repository public/private, `main` 최신 HEAD, 열린 PR·Issues, Actions 워크플로와 최근 run 결과를 **실제로 확인**해. 2026-10-22 마지막 점검 기준 `main`은 **`09bd9fb0f44b77006f09f5d15fb4d22b3bd9dc25`**였고, **PR #1~#18 모두 병합, 열린 PR 0건**이었지만 이후 변경이 있으면 반드시 최신 `main`을 우선해. 이 프롬프트·인수인계 자체의 커밋으로 HEAD가 바뀔 수 있음.
2. 먼저 **`docs/handoff/PORTAKIT_COMPLETE_HANDOFF_20261022.md` 전문**, **`docs/handoff/START_NEW_CHAT_PORTAKIT_20261022.md`**, `README.md`, `catalog.json`, `toolsets.json` 순서로 읽어. 이후 `docs/SPEC.md`, `docs/DECISIONS.md`, `docs/TOOLSETS.md`, `docs/RELEASE_CHECKLIST.md`, `docs/BACKLOG.md`, `docs/HANDOFF.md`, `docs/GUI_ACCEPTANCE_20261021.md`, `docs/WINMERGE_OFFICE_ACCEPTANCE.md`, `research/TOOLS_CANDIDATES_20261020.json`, `research/SYSINTERNALS_NETWORK_REVIEW_20261021.json`를 교차 검증해.
3. 실제 `portakit.py`, `scripts/*.py`, `scripts/*.cmd`, `scripts/*.ps1`, `tests/test_*.py`, `.github/workflows/*.yml`을 보고 문서의 기능·제약·테스트 숫자와 정확히 대조해. 잘못되거나 오래된 과거 섹션은 최신 SSOT와 구별하고 최신 HEAD보다 이전 것으로 롤백하지 마.

## B. 마지막 검증 기준 (반드시 다시 확인)

- **17개 실제 설치 가능한 SHA-256 고정 소프트웨어:** Notepad++ 8.7.5, WinMerge 2.16.46, jq 1.7.1, ripgrep 15.2.0, fd 10.5.0, fzf 0.74.5, bat 0.26.1, sd vendor ZIP 1.1.0(실행 파일의 `--version` 출력은 1.0.0으로 불일치), yq 4.54.1, delta 0.20.1, hyperfine 2.0.0, 7zr 26.04, Everything Desktop 1.4.1.1032, grepWin 2.1.12, Miller 6.22.0, dasel 3.11.2, 전체 7-Zip 26.04. 설치 주소와 원본 SHA는 `catalog.json`이 유일한 SSOT.
- **108개 조사 항목:** 17개 설치 가능, Windows 기본 제공/선택 내장 27개, 추가 검토 64개. `research/TOOLS_CANDIDATES_20261020.json` 참조. 연구 후보는 실제 설치 가능 프로그램으로 취급하지 마.
- **10개 배타적 주 분류:** `files`, `text`, `structured-data`, `system`, `network`, `security`, `development`, `automation`, `documents`, `transfer`. 주 분류당 도구 소속은 정확히 한 번, 업무 프로필은 여러 카테고리를 조합해도 중복 설치하지 않음. 기존 `common/os/nw/dev/data/diag`는 구버전 명칭 호환 별칭으로 유지하고, `minimal/mes-support/developer`도 원래 구성대로 유지.
- **안전 계약:** 평소 `plan`은 읽기 전용, 설치는 `apply --yes` 명시 옵션, 동일 핀 설치는 no-op, 구버전/타인 폴더/백업/심볼릭링크는 실패로 차단. 원본 ZIP/EXE 사내 반입 설치는 `portakit.py --archive FILE install ID` 또는 `Toolsets.cmd apply PROFILE --yes --offline-dir DIR`; 전체 SHA를 먼저 확인하며 인터넷 연결이 필요하지 않음. 옵션 없이 앱 설정·플러그인·우클릭 메뉴·Windows PATH·서비스·드라이버·레지스트리 수정 금지.
- **전체 7-Zip**은 별도 `7zr`를 먼저 설치하고, 공식 x64 SFX EXE를 실행하지 않고 SHA 고정된 압축 데이터로만 해제. 파일 경로·암호화·링크·압축 해제 한도 검증, `7z.exe`로 실제 ZIP 생성/무결성 테스트까지 Windows CI 통과. `7zFM.exe` 실제 GUI 업무 검증은 남음.
- **Explorer 우클릭**은 Notepad++·WinMerge용 현재 사용자 HKCU 클래식 메뉴만 opt-in 구현됨. Windows 11 최신 메뉴/WinMerge 2개 동시 선택 ShellExtension은 보류.
- **WinMerge의 Office4**는 Excel·Word·PowerPoint·Visio 필터/COM 사전 조건과 근거 ZIP 정합성 테스트까지만 확인. 실제 사용권 있는 Office 데스크톱 GUI에서 semantic compare한 증적이 없으므로 **NOT_VERIFIED**. `scripts/Run-WinMerge-Office4.ps1` 및 독립 ZIP verifier는 준비됨.
- **Everything·grepWin·전체 7-Zip GUI**는 `scripts/gui_acceptance.py`와 `scripts/GuiAcceptance.cmd`로 로컬 증적을 남길 수 있음. 기본은 앱 GUI를 전혀 띄우지 않는 조사 모드로 항상 `NOT_VERIFIED`; 실제 GUI 열기는 `--review --launch`가 필요하고 Everything 첫 실행은 추가 `--allow-everything-first-run` 승인이 있어야 함. 사내 운영 서버에서 자동 실행하거나 Everything NTFS 인덱싱·Windows 서비스·HTTP/ETP를 자동 활성화하지 마.
- **TCPView·PsPing**은 Microsoft Sysinternals EULA상 기업 장비 무료 사용과 **제3자 재배포 권한**이 별개. Microsoft가 제3자 배포 라이선스를 제공하지 않으므로 현재는 metadata-only 검토 단계이며 카탈로그 자동 설치/바이너리 커밋 금지. PsPing 활성 트래픽 테스트는 대상·포트·부하·기간에 대한 네트워크 소유자 승인 필수. `research/SYSINTERNALS_NETWORK_REVIEW_20261021.json` 참조.
- **CI:** 2026-10-22 기준 main [Windows run 39715051982](https://github.com/greatgc-flow/portakit/actions/runs/39715051982)에서 Python 3.11과 3.14 각각 **282개 테스트 모두 통과**. PR #18에서 Actions 버전 태그를 검증된 immutable SHA로 교체했으므로 임의로 태그로 되돌리지 마. [Live vendor archive run 39714408046](https://github.com/greatgc-flow/portakit/actions/runs/39714408046) 성공. 소스·문서·실제 최신 CI 기준으로 재검증해.
- **절대 주장하지 말 것:** 회사 OSS/보안 승인 완료, Sysinternals 배포 승인, 실제 사용자 PC GUI PASS, Office4 실사용 PASS, 아직 발행하지 않은 정식 Release, 임의로 설치할 수 없는 조사 후보가 이미 설치됐다는 표현.

## C. 설계·구현 원칙

Windows 전용 PortaKit은 Python 3.11+ 표준 라이브러리로 가볍게 구현하고, 실제 내가 업무에서 쓰는 Java 코드는 **JDK 1.8**, C# 코드는 **VS2015**, Windows PowerShell은 **2.0 / 5.x 호환**을 지켜줘. 코드는 기능·테스트 단위로 분리하고 빈 배열/null, 파일 충돌, 드라이브 경계, 경로 조작, SHA 불일치, 실패 시 원복, 보안 권한, 중복 설치, 라이선스, CPU/메모리/용량을 고려해. 애매한 동작은 모두 명시적인 옵션으로 만들고 간단한 기본값을 유지해. 콘솔 실행 결과는 가능한 한 화면 출력 그대로 로컬 증적 파일로 남기고, 자동 업로드하지 마.

## D. 다음 라운드의 실제 우선순위

1. 최신 main/PR/Actions/SSOT와 전체 문서 간 **상호 MECE 재귀적 검증**으로 drift·누락·중복·잘못된 PASS 표현을 확인하고, 고칠 필요가 있으면 단위 테스트부터 추가해.
2. `Everything`, `grepWin`, `7-Zip GUI`의 **사내 승인된 비운영 Windows PC** 실제 GUI 검증에 필요한 명령/기대결과/증적을 한 번에 준비해. 내가 직접 실행할 수 있게 하되, 실제 실행 결과 없이 GUI PASS로 승격하지 마.
3. `TCPView`와 `PsPing`의 공식 버전/사용권/사내 재배포·반입 방식과 현재 운영 영향도를 객관적으로 검토하고, 법률·보안 승인 전엔 metadata-only를 유지해. 가능한 한 **Windows 내장 도구 우선**.
4. 소형 고효율 SW 후보를 계속 비교하되 출처·기업 사용권·재배포권·실제 다운로드 크기(압축 해제 후 크기와 구별)·의존성·관리자 권한·비활성 네트워크 동작·실제 테스트와 설치 가능 여부를 구분해.
5. 변경이 필요하면 테스트/문서/코드/검증/피드백까지 폐루프로 정리하고 PR·CI가 실제 통과한 경우에만 병합해. 사내 민감정보·제3자 바이너리는 PUBLIC 저장소에 올리지 말고, 위험하거나 되돌리기 어려운 시스템 변경은 나에게 별도 승인을 요청해. 정식 Release는 수동 승인 전 게시하지 마.

## E. 결과·보고 요구

복원한 실제 최신 HEAD, 열린 PR·Issues·Actions, 도구·후보·MECE 카운트, 완료/미완료/보류 구분, 검증 증거(URL/경로/SHA), 새로 발견한 리스크와 다음 액션을 **팩트 / 추론 / 미확인으로 구분**해서 알려줘. 중간 질문 없이 확인 가능한 곳까지 완결적으로 처리하되, 실제 접근 권한이나 PC GUI 검증이 불가한 부분은 솔직하게 남겨줘. 필요한 작업은 GitHub에 커밋/PR/병합하고, 새 채팅을 다시 이어갈 수 있도록 문서와 시작 프롬프트도 최신화해.

---

**주의:** 이 프롬프트는 2026-10-22 시점의 PortaKit 대화 인수인계용이며 원문 비공개 채팅 전체를 재배포하는 용도가 아니다. 가장 신뢰할 증거는 새로운 GitHub 최신 main의 실제 코드/문서/테스트와 `docs/handoff/PORTAKIT_COMPLETE_HANDOFF_20261022.md`이다.
