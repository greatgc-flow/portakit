# xan 0.61.0 — local original ZIP preflight

**RESEARCH_ONLY / no admission / never downloads or executes software.**

This one-purpose optional read-only helper checks **a locally provided vendor-original xan Windows x64 MSVC ZIP** against the already recorded GitHub release metadata in [CSV alternatives](../research/CSV_ALTERNATIVES_20261031.json). It does not replace the PortaKit installer, alter its catalog or grant permission to download, run or redistribute anything.

## Operator path (Python 3.11+)

Only after obtaining the official asset through an authorized method, preserving its **original filename**, run:

~~~cmd
python -I scripts/xan_zip_preflight.py --original D:\ApprovedVendorArchives\xan-x86_64-pc-windows-msvc.zip
~~~

Optional separately approved **NEW** evidence JSON and byte-identical console log:

~~~cmd
python -I scripts/xan_zip_preflight.py --original D:\ApprovedVendorArchives\xan-x86_64-pc-windows-msvc.zip --out D:\LocalEvidence\xan-source-001.json
~~~

- No output flag: **no writes**, only console output; no extraction, vendor execution, installation, download, PATH/registry changes or network access.
- Optional output flag: creates **new** JSON and neighboring .log only. Neither may already exist; they must be at a separate safe path. Console lines are mirrored exactly into the log. Never upload actual enterprise workstation paths, personal information or original software binaries to this public repo.
- Exit **0** means only LOCAL_ORIGINAL_STRUCTURE_PASS; exit **2** means a local audit was rejected. Neither exit grants software/enterprise approval.

## What this inspects

- Official release API snapshot for **xan 0.61.0** Windows x64 MSVC ZIP (xan-x86_64-pc-windows-msvc.zip): expected **6,473,075 compressed bytes** and SHA-256 **5f7bef4dcffbfb3a3a937ac180ed76cdf966cb13647251beffddb84d01c1ae54**. The original size, filename and full SHA must match before the ZIP is opened.
- Re-read the **same open file handle** after inspection and reject changed digest/size.
- ZIP members limited by existing core archive settings to **4,096 members** and **512 MiB total declared expanded data**; member depth maximum 32, normal ZIP STORED/DEFLATED only.
- Normalize and reject unsafe Windows relative paths including parent traversal, absolute/drive/ADS, empty segments, Windows reserved names, trailing dot/space, backslash separators, duplicate/case-colliding names and file-as-parent conflicts.
- Reject encryption, reparse/symlink/special file modes, zero data files, and multiple/absent xan.exe targets.
- **Stream every regular member to EOF without extracting**. Verify ZIP CRC and declared expanded size on the data read, bounded by those archive limits.

Results include archive member count, root names, expanded logical bytes, xan EXE member count, original digest, local check outcome and explicitly pending real-world gates.

**Limitations:** The release SHA is a *GitHub release metadata value*; a matching locally provided file is **not** independent publisher authentication, a signed supply-chain attestation or virus/EDR assurance. This source audit cannot prove the actual vendor binary starts on an authorized Windows host, uses no network, writes only inside a sandbox, or meets company OSS/EULA/redistribution requirements. It does **not** execute xan, Miller or anything else from the archive.

Headless CI only uses **fabricated ZIP archives** and dummy bytes called xan.exe; even passing thousands of synthetic cases cannot certify the actual official ZIP or runtime. Actual original-file inspection remains operator-side **NOT_VERIFIED** until a permitted Windows original is supplied.

## Separate next acceptance checks

Keep [Issue #25](https://github.com/greatgc-flow/portakit/issues/25) open and record exact SHA and compressed/expanded size **without posting original vendor files**. After the independent enterprise approval of real vendor execution, run the existing optional [CSV operator smoke](CSV_OPERATOR_SMOKE.md) on an actually isolated nonproduction offline Windows host with explicit dual approval flags. Expand functional cases to BOM, UTF-16, deliberately malformed CSV, and repeatable 100k+ record CPU/RAM/disk observations **only after observing cross-tool compatibility on approved originals**. No tool catalog promotion, OSS/EDR/transfer claim, or new release Gate D until human validation.
