# PortaKit — 새 채팅 시작 프롬프트 (2026-10-23 최신)

내 GitHub **https://github.com/greatgc-flow/portakit** 의 PortaKit 프로젝트를 **이전 채팅의 전체 기술 맥락과 검증 상태 그대로** 이어가 줘. 가장 먼저 GitHub 연결 앱으로 실제 **repository visibility / 최신 main HEAD / 열린 PR·Issues / Actions 상태**를 확인하고, 이전 메모리나 아래 기준 SHA보다 **최신 main을 우선**해.

**2026-10-23 이 인수인계 직전 확인한 main:** `8e1d1250edef433a96392815bbe9b6c689218c75`; 이 인수인계 커밋/병합으로 변경될 수 있음. 해당 시점 **Public 저장소, 열린 PR 0건·Issues 0건**, main Windows CI [39767847308](https://github.com/greatgc-flow/portakit/actions/runs/39767847308) 성공. 이후 변동이 있다면 실제 현재값으로 교체해.

## 1. 전문 확인 순서

1. **`docs/handoff/PORTAKIT_HANDOFF_20261023.md`** — 이번 최신 인계 및 P0/P1 과제/변경금지 경계.
2. **`docs/handoff/PORTAKIT_COMPLETE_HANDOFF_20261022.md`** — 과거 작업 전체 맥락과 결정·검증 근거.
3. **`docs/handoff/START_NEW_CHAT_PORTAKIT_20261022.md`** — 이전 새 채팅 인계.
4. **`docs/handoff/2026-10-22_REPO_SOURCE_MAP.json`** — 당시 48개 파일의 원본 blob 매핑(최신 tree와 혼동 금지).
5. `README.md`, `catalog.json`, `toolsets.json`, `portakit.py`, `scripts/toolsets.py`, `scripts/gui_acceptance.py`, `scripts/context_menu.py`.
6. `docs/SPEC.md`, `docs/DECISIONS.md`, `docs/TOOLSETS.md`, `docs/BACKLOG.md`, `docs/RELEASE_CHECKLIST.md`, `docs/GUI_ACCEPTANCE_20261021.md`, `docs/WINMERGE_OFFICE_ACCEPTANCE.md`.
7. `research/TOOLS_CANDIDATES_20261020.json` 및 `research/SYSINTERNALS_NETWORK_REVIEW_20261021.json`; 전체 `tests/`, `.github/workflows/` 재귀 열람.

전문 열람 후 최신 Git tracked file tree/sha와 문서/테스트/코드가 MECE하게 상호 추적 가능한지 교차검증해. 10월 22일의 파일 원장은 기준 스냅샷이지 현재 파일 목록이 아니므로 최신 Git tree를 다시 가져와.

## 2. 작업 의도와 확인 기준

- 목표: **Windows 폐쇄망 회사용 무료·초경량·고효율 SW**를 **Very Simple** 구조로 선택형 툴셋 관리. 도구 목록→기업 무료 사용권/재배포 승인→공식 버전/SHA→오프라인 반입→선택 설치→검증/증적→피드백 백로그의 폐루프. 10개 배타적 주 기능 영역, 역할/업무 프로필은 중복 설치 없이 자유 조합.
- 현재 설치 가능 **17종**(카탈로그 SSOT): Notepad++, WinMerge, jq, ripgrep, fd, fzf, bat, sd, yq, delta, hyperfine, 7zr, Everything, grepWin, Miller, dasel, 전체 7-Zip. **108개 후보 원장** = 17 pinned + 27 Windows built-in/optional + 64 research-only. `sd` ZIP v1.1.0의 실행 버전 출력 1.0.0 불일치 유지.
- 안전 기본값: `plan` 완전 읽기 전용, `apply --yes` 필수, 이미 일치하는 pinned app은 no-op. `--archive`/`--offline-dir`로 **파일 원본 SHA를 오프라인 전수검증**. 옵션 없는 자동 업데이트·파일삭제·서비스·드라이버·레지스트리/우클릭·권한승격·외부 서버 통신은 금지.
- Notepad++/WinMerge 클래식 HKCU 우클릭 메뉴는 개별 opt-in 구현 완료. 7zr는 7z 전용, 전체 7-Zip은 공식 SFX EXE를 실행하지 않고 신뢰된 7zr를 통한 압축 데이터 해제만 허용. 실제 7z.exe ZIP 생성/검사 CI 성공, **GUI는 아직 사람이 검증하지 않음**.
- **Everything·grepWin·7-Zip GUI**: `scripts/GuiAcceptance.cmd` 기본 실행은 **GUI를 띄우지 않고 NOT_VERIFIED**. 사람의 `--review --launch` 승인 후 테스트 PC에서 실제 GUI 확인. Everything은 `--allow-everything-first-run` 추가 승인이 필요. Windows 서비스/전체 드라이브 NTFS 인덱싱/HTTP·ETP 기능은 자동 활성화 금지.
- **TCPView·PsPing**: Microsoft Sysinternals의 회사 사용 허용과 제3자 재배포는 별도. 현재 **research metadata-only**, 바이너리 커밋·무허가 자동배포·생산망 활성 테스트 금지. 공식 조건·IT/OSS/EDR/법무 확인 전 설치 가능 판정 금지.
- **WinMerge Office4 Excel/Word/PowerPoint/Visio 실제 COM 의미 비교는 NOT_VERIFIED**. Office 정품 설치·실제 GUI 기반 증거 필요. Windows11 네이티브 우클릭/WinMerge 2항목 ShellExtension도 보류.
- 언어 제약: PortaKit은 Python 3.11+ 표준라이브러리, 관련 **Java는 1.8**, **C#은 VS2015**, **PowerShell은 Windows PowerShell 2.x·5.x 호환**. 독립 테스트 가능한 작은 모듈, null·빈 목록 고려, 애매한 동작 옵션화, 화면 출력과 증적 파일 일치.
- 저장소는 **PUBLIC**이므로 내부 회사정보, IP, 계정, 개인 메모리, 원문 채팅, 서드파티 바이너리/저작권 미승인 파일을 커밋하지 마. 기술 관련 공개 가능한 정보만 커밋.

## 3. 새 채팅에서 바로 진행할 일

1. 실제 최신 소스/테스트/Actions/PR 확인 → 세부 상태표(팩트·미확인·추론).
2. 사용자가 제공한 **실제 GUI 결과 증거 ZIP**이 있으면 분석하고 GUI acceptance를 최종 판정. 없으면 미검증 상태 유지하고 가능한 비대화형 안전 점검을 진행해.
3. TCPView/PsPing 라이선스·공식 해시·사내 반입 경로의 미결정 지점 정리. 실제 승인 없으면 metadata-only.
4. MECE 교차 검증(카탈로그 17, 연구 108, 프로필·별칭, 사용자 데이터 보호, 소형 크기 검증), 낡은 문서가 있으면 최신 정보에 맞게 정리.
5. 검증된 범위 내에서 지속 개선, 독립 테스트·GitHub PR·Windows CI·핸드오프까지 완결. 테스트 미통과 PR 병합 금지. Release·운영환경 변경·외부 유출 행위는 명시 승인 없이 하지 마.

**답변은 한국어로**, 빠짐없는 사실 근거·공식 출처·안전 위험·남은 작업과 GitHub 커밋/CI 링크를 제시해. 임의로 성공했다고 판단하지 말고 인간 GUI와 Office4는 증적 없으면 NOT_VERIFIED라고 명확히 표현해. 가능하면 나에게 재차 같은 내용을 묻지 말고 접근 가능한 작업부터 진행해.
