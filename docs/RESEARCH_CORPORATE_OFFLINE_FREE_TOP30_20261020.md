# 폐쇄망 기업 업무용 무료 Windows SW TOP 30 — 2026-10-20

**Scope:** Windows 10/11 x64 corporate workstations on an air-gapped or Internet-restricted network. Practical emphasis: Battery MES / CIM / EAS / EAP integration, Windows WCF/IIS, logs, network diagnosis and Java 8 / C# VS2015 support. This is an **evidence-based software shortlist**, NOT a legal opinion, IT approval, binary hash verification, proof of successful offline execution, or installation order.

## Selection method (practical rather than popularity-only)

Priority reflects (a) frequency and relevance to MES/CIM incidents; (b) evidence of permission for ordinary corporate use; (c) usable offline after authorized download; (d) low privilege, service/driver, outbound-network and OS impact; and (e) maintenance and trustworthy upstream provenance. Numbers denote recommended evaluation order **within this scenario**, not a statistically measured popularity ranking.

**Deployment classes:** `A` = standalone EXE/official ZIP with largely self-contained operation, assuming ordinary OS libraries; `B` = portable possible, but runtime, optional installation, registration, elevated-only subfeature or packaged-driver conditions need verification; `C` = driver/elevation, sensitive capture, high runtime impact or policy/permission-sensitive operation. **All thirty require company security/OSS management approval before deployment**. `P0/P1/P2` are utility assessment priorities, not automatic install permissions.

## TOP 30 (official upstream links)

| Rank | Category | Software | Corporate-use license basis | Offline/portable assessment | Priority | Specific use | Critical caveat |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | Common | [Notepad++](https://github.com/notepad-plus-plus/notepad-plus-plus) | GPL | A · 공식 portable ZIP | P0 | MES/CIM 로그, XML/INI, 소스·설비 메시지 편집 | 플러그인과 업데이트는 별도 승인; 현 PortaKit 관리 |
| 2 | Common | [WinMerge](https://winmerge.org/source-code/) | GPL-2.0+ | A · ZIP | P0 | 서버별 설정/소스/배포본 차이 확인 | 문서 Office COM 비교는 실제 Office 설치 필요; 현 PortaKit 관리 |
| 3 | Common | [7-Zip](https://www.7-zip.org/) | LGPL/BSD 및 unRAR 조건 | B · 공식 설치본/CLI 분리 검토 | P0 | ZIP/7z 증적, 대용량 로그 압축·해제 | 포터블 추출 방식과 서브 라이선스 고지 검토 |
| 4 | Common | [Everything](https://www.voidtools.com/downloads/) | MIT형 공식 License.txt | B · 공식 portable ZIP | P0 | 로그·배포본·설정 파일 즉시 검색 | NTFS 검색에 서비스 또는 관리자 권한 필요; Enterprise Server 제품은 별도 유료 |
| 5 | Common | [SumatraPDF](https://github.com/sumatrapdfreader/sumatrapdf) | (A)GPL-3.0/BSD 혼합 | A · portable EXE | P0 | 폐쇄망 PDF·CHM·매뉴얼 오프라인 열람 | 사용 권한과 외부 링크 자동 열기 점검 |
| 6 | Common | [KeePassXC](https://keepassxc.org/download/) | GPL-2/3 계열 | B · 공식 portable ZIP | P1 | 비밀번호/계정 암호화 로컬 금고 | MSVC 재배포 런타임 필요 가능; 회사 비밀관리 정책 우선 |
| 7 | Common | [ShareX](https://github.com/ShareX/ShareX/releases) | GPL-3.0 | B · 공식 portable ZIP | P1 | 장애 화면 캡처·비식별 주석·증적 | 업로드/공유 기능·핫키·클립보드 기록 비활성화 확인 |
| 8 | OS | [Process Explorer](https://learn.microsoft.com/en-us/sysinternals/downloads/process-explorer) | Microsoft Sysinternals EULA | B · 압축형 실행파일 | P0 | WCF·CIM 프로세스의 핸들/DLL·자원 확인 | 다른 프로세스 상세 조회 시 권한 필요; 바이너리 재배포 제한 |
| 9 | OS | [Process Monitor](https://learn.microsoft.com/en-us/sysinternals/downloads/procmon) | Microsoft Sysinternals EULA | C · 실행 시 드라이버/상승 권한 | P0 | 파일·레지스트리·프로세스 I/O 원인 추적 | 커널 드라이버·고용량 로그·운영 부하, 별도 승인 |
| 10 | OS | [Autoruns](https://learn.microsoft.com/en-us/sysinternals/downloads/autoruns) | Microsoft Sysinternals EULA | B · 압축형 실행파일 | P1 | 자동실행/서비스/보안 도구 개입 점검 | 시작 항목 비활성화 등 변경 기능 사용 금지 기본 |
| 11 | OS | [ProcDump](https://learn.microsoft.com/en-us/sysinternals/downloads/procdump) | Microsoft Sysinternals EULA | C · 권한/덤프 쓰기 | P0 | WCF 지연·응답없음·예외 시점 덤프 확보 | 덤프에 비밀·개인정보 포함될 수 있음; 용량/부하 사전 검토 |
| 12 | OS | [Handle](https://learn.microsoft.com/en-us/sysinternals/downloads/handle) | Microsoft Sysinternals EULA | B · 단일 EXE | P1 | 파일/폴더 점유·배포 장애 진단 | 강제 핸들 종료 옵션 비활성 정책 |
| 13 | OS | [Sigcheck](https://learn.microsoft.com/en-us/sysinternals/downloads/sigcheck) | Microsoft Sysinternals EULA | A/B · 단일 EXE | P1 | EXE/DLL 서명·버전·해시 점검 | VirusTotal/온라인 조회 옵션 절대 기본 사용 금지 |
| 14 | OS | [RAMMap](https://learn.microsoft.com/en-us/sysinternals/downloads/rammap) | Microsoft Sysinternals EULA | C · 관리 권한 가능 | P2 | 메모리 맵·파일 캐시·사용량 분석 | 캐시 비우기 등 변경 기능 운영 중 사용 금지 기본 |
| 15 | NW | [TCPView](https://learn.microsoft.com/en-us/sysinternals/downloads/tcpview) | Microsoft Sysinternals EULA | B · 압축형 실행파일 | P0 | CIM↔MES TCP 연결·PID·세션 상태 확인 | 연결 종료 기능 통제; 바이너리 재배포 금지 |
| 16 | NW | [PsPing](https://learn.microsoft.com/en-us/sysinternals/downloads/psping) | Microsoft Sysinternals EULA | A/B · CLI | P0 | TCP 포트 레이턴시·접속시간 측정 | 대역폭/부하 테스트는 별도 승인, 타깃 제한 |
| 17 | NW | [Wireshark](https://www.wireshark.org/download.html) | GPL 계열 / Npcap 별도 | C · 분석은 오프라인; 캡처엔 Npcap | P0 | PCAP/PCAPNG 패킷·재전송/HTTP/TCP 분석 | 실시간 캡처는 드라이버·관리자·통신보안 승인 필수; Npcap OEM 조건 확인 |
| 18 | NW | [PuTTY](https://www.chiark.greenend.org.uk/~sgtatham/putty/) | MIT | A · standalone EXE | P1 | 사내 SSH/Telnet/Serial 클라이언트 | 허용된 시스템에만 접속; 약한 프로토콜 기본 사용 지양 |
| 19 | NW | [WinSCP](https://winscp.net/eng/docs/license) | GPL-3.0+ | A/B · portable EXE | P1 | 사내 SFTP/SCP 로그·증적 반출입 | 계정/키 저장·전송 경로 통제; 설치패키지/아이콘 별도 약관 |
| 20 | NW | [Packet Sender](https://github.com/dannagle/PacketSender) | GPL-2.0+ | A/B · 공식 portable mode | P1 | 모의 TCP/UDP/SSL/HTTP 통신·요청 응답 시험 | 패킷 송신 자체가 운영 영향 가능; 시험망·대상 allowlist |
| 21 | NW | [curl (CLI)](https://curl.se/docs/copyright.html) | curl license | A · Windows 내장 우선 | P0 | HTTP/WCF basicHttp 요청·응답/TLS 진단 | 윈도우 내장 기능 우선; 실 서버 부하 테스트 금지 |
| 22 | Dev | [Visual Studio Code](https://code.visualstudio.com/docs/setup/portable) | MS 제품 EULA (소스 MIT와 구별) | B · Windows ZIP + data 폴더 | P1 | 소스·스크립트·검색/디버깅 보조 | 오프라인 VSIX/확장 라이선스·원격/업데이트/텔레메트리 검토; VS2015 대체 아님 |
| 23 | Dev | [Git for Windows](https://git-scm.com/downloads/win) | GPL 및 번들 구성별 라이선스 | A/B · PortableGit | P1 | 소스 형상관리·오프라인 이력 비교 | Git hooks·신뢰하지 않는 저장소 실행 통제 |
| 24 | Dev | [ripgrep (rg)](https://github.com/BurntSushi/ripgrep) | MIT / Unlicense | A · ZIP | P0 | 대량 MES 로그/소스 빠른 문자열 검색 | 민감 로그 검색 결과 저장 위치·인코딩 점검 |
| 25 | Dev | [jq](https://github.com/jqlang/jq) | MIT(코드) + 제3자 고지 | A · EXE | P0 | JSON 프로토콜/로그 가공 및 자동화 | 현 PortaKit 관리; 2중 배포 방지 |
| 26 | Dev | [Eclipse Temurin JDK 8](https://adoptium.net/docs/faq) | GPL-2.0 + Classpath Exception | B · JDK ZIP | P0 | Java 1.8 전용 개발·재현 테스트 런타임 | 운영 JRE/JDK 전역 교체·JAVA_HOME 변경 자동화 금지 |
| 27 | Dev | [ILSpy](https://github.com/icsharpcode/ILSpy) | MIT(제3자 고지 별도) | B · ZIP, 버전별 .NET 의존성 | P1 | C# .NET Framework 4.x DLL 역분석·참조 | 타사 DLL 라이선스/영업비밀 정책, 실행 런타임 검증 |
| 28 | Data | [DBeaver Community](https://dbeaver.io/about/) | Apache-2.0(IDE); JDBC 별도 | B · 공식 Windows ZIP | P1 | 허용된 DB 연결·SQL 조회·CSV 내보내기 | JDBC 드라이버/인증자료 오프라인 사전 반입; 읽기전용 기본 |
| 29 | Data | [DB Browser for SQLite](https://sqlitebrowser.org/dl/) | MPL-2.0/GPL-3.0 선택 + 플러그인 | A · ZIP/PortableApps | P1 | 로컬 DB·테스트 데이터 확인 | 원본 DB 읽기/수정 분리, 파일 잠금 주의 |
| 30 | Data | [SQLite CLI](https://www.sqlite.org/copyright.html) | Public Domain(핵심) | A · sqlite-tools ZIP | P1 | 오프라인 SQL 조회·증적 추출 스크립트 | 쓰기 SQL 금지 기본; SQLite 상용 확장 별도 조건 |

## License and deployment interpretation

**Free use ≠ unrestricted packaging.** **Microsoft Sysinternals** terms allow any number of company-device installs, but the official FAQ refuses third-party distribution licenses. Thus do not commit Sysinternals ZIP/EXE into a public Git repository, private generic software bundle, or PortaKit-distributed archive without separate legal approval of the distribution method. The tool catalog may hold metadata/source/vendor official link and the company may make approved copies for its own devices per EULA; have the legal/IT team review the actual internal deployment workflow. [Official EULA](https://learn.microsoft.com/en-us/sysinternals/license-terms) · [Licensing FAQ](https://learn.microsoft.com/en-us/sysinternals/license-faq).

**Commercially free but distinct product restrictions.** 7-Zip explicitly permits commercial-organization use, but source/redistribution involves LGPL, BSD and unRAR conditions; [7-Zip official license](https://www.7-zip.org/). Everything *desktop* has a permissive [official license](https://www.voidtools.com/License.txt) and [portable ZIP](https://www.voidtools.com/downloads/), but [Everything Server enterprise](https://www.voidtools.com/en-us/enterprise/) is a distinct paid offering for business server-side use. WinSCP's [official GPL license](https://winscp.net/eng/docs/license) expressly allows business use and distribution, with distinct installer/icon terms. Packet Sender [explicitly permits business use](https://github.com/dannagle/PacketSender). PuTTY is [MIT licensed, including internal company distribution](https://www.chiark.greenend.org.uk/~sgtatham/putty/feedback.html).

**License distinctions important for audits.** Microsoft VS Code's distributable **product** is governed by the [Microsoft license](https://code.visualstudio.com/license), not solely the MIT license on its source; internal corporate development and testing are allowed. Temurin JDK is free under [GPLv2 with Classpath Exception](https://adoptium.net/docs/faq) (use a JDK 8 exact ZIP pin). SQLite's core CLI is [public domain](https://www.sqlite.org/copyright.html), but optional proprietary commercial extensions are not. DBeaver Community IDE is [Apache 2.0](https://dbeaver.io/about/), but database-specific JDBC drivers have individual licenses.

**Wireshark and Npcap are two different installation decisions.** Offline inspection of existing PCAP/PCAPNG is possible without starting a live capture. Windows live capture commonly needs Npcap, which installs a driver and is subject to its own [free-use and OEM deployment terms](https://npcap.com/oem/internal). The free edition's 5-system limit has exceptions for use only with Wireshark/Nmap/Microsoft Defender for Identity; it does **not** authorize generic bundling, automation of OEM-only silent installers, or driver installation without site IT permission. Never silently install Npcap in production or on MES/CIM hosts.

**Explicit corporate restrictions and privacy:** Process Monitor and other privileged OS tools may load kernel components; ProcDump snapshots may contain credentials, messages and personal data. ShareX supports external upload; turn off uploads and recording defaults for an air-gapped corporate baseline. Everything indexes file paths; ensure only explicitly permitted volumes and indexing privilege. PuTTY/WinSCP/Packet Sender/PsPing/curl must not initiate unexpected active traffic in production. Sigcheck must not use online VirusTotal mode without approval. Database browsers should start with read-only connections.

## Recommended rollout without compromising the existing PortaKit

| Phase | Scope | Decision |
| --- | --- | --- |
| 0 · retain | Existing validated Notepad++ / WinMerge / jq | Keep existing pins and exact behavior; avoid duplicate installations or silent upgrades |
| 1 · offline core | 7-Zip, SumatraPDF, ripgrep, Git for Windows (if needed), SQLite CLI | Evaluate one official ZIP/executable at a time; verify its source and SHA-256; avoid system-wide changes |
| 2 · targeted ops | Everything, Process Explorer, TCPView, PsPing, Sigcheck, Handle | Add only after staff IT approval, official-use license evidence and side-effect profiles |
| 3 · privileged diagnosis | Process Monitor, ProcDump, RAMMap, Wireshark live capture | Explicit elevation/driver, target, sampling duration, storage, PII and rollback checklists |
| 4 · conditional developer/network/data | Temurin JDK 8, VS Code, ILSpy, PuTTY, WinSCP, Packet Sender, DBeaver CE, DB Browser for SQLite, KeePassXC, ShareX, Autoruns | Select only per user role, local dependency and company policy; disable auto updates, cloud sign-ins/uploads, unapproved extensions and broad network activity |

**Closed-network intake checklist:** an externally connected, approved staging machine retrieves exact vendor binary/version → record canonical upstream URL, license and dependency notices, release signature and independently computed SHA-256 → IT malware/EDR + OSS/compliance screening → USB/approved transfer route → offline local hash verification → non-production x64 smoke test without Internet → record admin prompts, files/services/drivers/registry writes and process exit → publish **metadata-only** in Git + separate licensed binary escrow as permitted. Store license receipts/evidence; do not assume every open-source license has identical redistribution obligations. For stale Win7/legacy Windows Server, verify platform support separately.

**Integrity gate:** current PortaKit `catalog.json` tracks only 3 validated programs. The 27 additions here are **research only / not installed / no pinned download/SHA / no release**. The previously defined categories Common, OS, NW, Dev, Data and Diagnostics can reference tool IDs after the individual admission gates, with many-to-many category assignment and single physical installation per ID. Nothing in this document authorizes adding binaries automatically.

## Official authority references (major cross-product caveats)

- [Microsoft Sysinternals License Terms](https://learn.microsoft.com/en-us/sysinternals/license-terms) and [Licensing FAQ](https://learn.microsoft.com/en-us/sysinternals/license-faq)
- [Npcap commercial/enterprise internal-use rights](https://npcap.com/oem/internal) and [Npcap official free-edition wording](https://npcap.com/)
- [Everything software license](https://www.voidtools.com/License.txt), [download/portable ZIP](https://www.voidtools.com/downloads/) and [Everything Server enterprise license](https://www.voidtools.com/en-us/enterprise/)
- [7-Zip license FAQ](https://www.7-zip.org/faq.html), [WinSCP license](https://winscp.net/eng/docs/license), [Packet Sender project licensing](https://github.com/dannagle/PacketSender)
- [VS Code EULA](https://code.visualstudio.com/license), [VS Code portable mode](https://code.visualstudio.com/docs/setup/portable), [Temurin free use](https://adoptium.net/docs/faq)
- [DBeaver CE license](https://dbeaver.io/about/), [DB Browser SQLite project license](https://github.com/sqlitebrowser/sqlitebrowser/blob/master/LICENSE), [SQLite Public Domain](https://www.sqlite.org/copyright.html)
- [ShareX official portable release](https://github.com/ShareX/ShareX/releases), [KeePassXC portable ZIP/runtime requirement](https://keepassxc.org/download/), [Notepad++ official portable releases](https://github.com/notepad-plus-plus/notepad-plus-plus/releases)

**Research status:** official-source license and product/distribution form screening performed 2026-10-20. No vendor assets downloaded or executed; no current-license terms archived locally in this PR. Per-artifact SHA-256, version compatibility, offline dynamic behaviour and enterprise OSS/security approval remain separate evidence gates.
