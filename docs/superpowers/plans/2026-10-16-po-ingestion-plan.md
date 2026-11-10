# PO File Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PDF·스캔 PDF·xlsx·xls에서 PO 정보를 추출해 원본과 비교·수정한 후 등록하고 원본·버전·이력을 보관한다.

**Architecture:** 인증된 업로드를 private storage에 저장하고 인식 작업을 DB queue에 기록한다. 로컬 worker가 reader와 고객별 필드 매핑을 실행한다. 추출 결과는 확정 PO와 분리하며 사용자 확인 후 core 서비스를 통해 등록한다.

**Tech Stack:** core 스택, pypdfium2, Tesseract 5(kor+eng), pytesseract, Pillow, openpyxl, xlrd, Django tests, Playwright.

**Spec:** [설계](../specs/2026-10-16-po-management-calendar-design.md), [상위 계획](2026-10-16-po-management-implementation.md), [선행 core 계획](2026-10-16-po-core-plan.md).

## Global Constraints

상위 Global Constraints 전체를 적용한다. “필수값을 추측하여 확정하지 않는다. 등록 전 담당자가 확인한다.” “외부 OCR 서비스는 회사 승인 전에는 사용하지 않는다.” 원본·전화번호는 비로그인 사용자에게 공개하지 않는다. 인보이스·BL 업로드 기능은 만들지 않는다.

## Review Focus

확장자 위장·암호화·스캔·복수 페이지/시트·수식의 저장값 누락을 Task 8·9에서 검증한다. 고객마다 서식이 다르므로 모든 PO가 자동 추출된다고 가정하지 않는다.

---

## File Structure 및 계약

- `intake/models.py`: SourceFile(해시·private 경로·원래 이름·업로더·크기), ExtractionJob(상태·lease·시도·오류), ExtractionDraft(원문 evidence·필드·누락·경고), OrderSource(PO·버전 연결).
- `intake/storage.py`: 파일 검증·SHA-256·private 저장·인증 다운로드. 경로는 UUID로 만들고 사용자 파일명을 실제 경로에 사용하지 않는다.
- `intake/extractors/base.py`: `Evidence(page: int|None, sheet: str|None, cell: str|None, text: str)`, `ExtractedField(value: str|None, evidence: tuple[Evidence,...], needs_review: bool)`, `ExtractionResult(fields: dict[str,ExtractedField], lines: tuple[dict[str,ExtractedField],...], warnings: tuple[str,...], status: str)`.
- `intake/extractors/pdf.py`: `extract_pdf(path: Path) -> ExtractionResult`.
- `intake/extractors/excel.py`: `extract_excel(path: Path, extension: str) -> ExtractionResult`.
- `intake/extractors/mapping.py`: `map_evidence(evidence: tuple[Evidence,...], customer_id: UUID|None) -> ExtractionResult`. 고정 라벨·표 머리글·고객별 매핑을 사용한다.
- `intake/services.py`: `upload_source(file: UploadedFile, actor_id: int) -> UploadResult`, `confirm_draft(draft_id: UUID, data: OrderInput, actor_id: int, target_order_id: UUID|None, expected_order_version: int|None, expected_draft_version: int) -> Order`.
- `UploadResult(source_id: UUID, job_id: UUID|None, duplicate_order_ids: tuple[UUID,...])`는 base.py에 정의한다. 동일 파일에 연결된 기존 PO를 안내한다. 다른 고객·다른 PO로 써야 하는 예외는 명시적 확인 후 같은 source를 재사용하고 조용히 중복 생성하지 않는다.
- `intake/worker.py`: `process_extraction(job_id: UUID) -> ExtractionDraft`. management command는 짧은 DB lease로 작업을 claim하며 외부 API에 원문을 보내지 않는다.

## Task 8: private 업로드·중복·원본 버전

**Files:** Create `server/intake/{models.py,storage.py,services.py,views.py,urls.py}`, `server/intake/extractors/base.py`, `server/intake/tests/test_upload.py`, migrations; Modify `server/config/{settings.py,urls.py}`, `server/orders/models.py`, `server/requirements.in`, `server/requirements.lock`.

**Interfaces:** Consumes core의 User·Order·audit와 위 계약. Produces upload_source 및 GET `/sources/<id>/download/`, POST `/intake/upload/`. 업로드 중복 후보와 인식 job ID를 반환한다.

- [ ] **Step 1:** `UploadTests`에서 PDF/xlsx/xls 정상 저장·해시, 같은 파일 재업로드 시 source 중복 없음·기존 PO 안내, 원본 다운로드 비로그인 차단, 파일명 `../../x.pdf`가 private root를 벗어나지 않음, HTML을 .pdf로 바꾼 파일 거부를 assert한다. `test_cross_customer_same_po_number`는 수정본 후보를 고객+번호로 찾는지 검증한다.
- [ ] **Step 2:** `python manage.py test intake.tests.test_upload -v 2`로 요구 동작이 없어 실패함을 확인한다.
- [ ] **Step 3:** 확장자와 실제 파일 형식을 함께 검사하고 허용된 reader로 열 수 있는지 확인한다. 구현 기본 상한은 파일20MiB·PDF100페이지·Excel20만 셀, worker120초이며 설정으로 조정한다. 상한 초과는 사유와 수동입력 경로를 제공한다. 저장 경로는 웹 static/media 공개 매핑에서 제외하고 다운로드는 인증 뷰로 스트리밍한다. 업로드와 job 생성의 DB rollback·파일 정리 경계를 처리한다. 미연결 임시 파일은 별도 정리 대상으로 표시하고 원본 버전을 임의 삭제하지 않는다.
- [ ] **Step 4:** PDF·Excel 의존성을 추가해 lock을 갱신한다. Task 8 테스트를 통과시키고 임시 파일 정리 실패가 기존 원본을 삭제하지 않는지 검증한다.
- [ ] **Step 5:** `feat: store protected PO sources and revision candidates`로 해당 Files만 커밋한다.

## Task 9: 로컬 인식·확인·수정본 반영 화면

**Files:** Create `server/intake/extractors/{pdf.py,excel.py,mapping.py}`, `server/intake/worker.py`, `server/intake/management/commands/run_intake_worker.py`, `server/intake/tests/{test_extraction.py,test_review.py}`, `server/templates/intake/review.html`, `server/static/po/review.js`, `server/e2e/intake.spec.mjs`; Modify `server/intake/{services.py,views.py,urls.py}`, `server/templates/orders/detail.html`, `server/README.md`.

**Interfaces:** Produces 위 extract·process_extraction·confirm_draft 함수, GET `/intake/<draft_id>/review/`, POST `/intake/<draft_id>/confirm/`. Task 2 save_order와 Task 4 reconcile_order를 재사용하며 새 PO 저장 함수를 별도로 만들지 않는다.

- [ ] **Step 1:** 비식별 fixture를 `server/intake/tests/fixtures/`에 만든다. 국내 문자 PDF·해외 문자 PDF·스캔 PDF·다중시트xlsx·xls·암호화 PDF·깨진 파일·캐시 없는 수식 셀·원문 명령문을 포함한다. `ExtractionTests`에 다음 assertion을 작성한다.

```python
assert result.lines[0]['quantity'].value == '100'
assert result.lines[0]['quantity'].evidence  # 페이지 또는 시트/셀 위치
assert result.fields['etd'].value is None  # 원문에 없는 값은 생성하지 않음
assert formula_without_cache.needs_review is True
assert '수동입력' in unsupported_result.warnings
```

- [ ] **Step 2:** `ReviewTests`에서 확인 전 PO 미생성, 수정 후 원문·수정값 보존, 공급가액 불일치 표시, 국내 납기 필수·해외 원문 납기 무시, 같은 고객+PO 번호 다른 파일은 비교 화면, 수정본 확정 시 출고실적·수동일·완료 이력 보존을 assert한다. `python manage.py test intake.tests.test_extraction intake.tests.test_review -v 2`로 실패를 확인한다.
- [ ] **Step 3:** PDF는 pypdfium2로 문자와 위치를 읽고 문자가 없는 페이지는 이미지 렌더 후 Tesseract kor+eng으로 읽는다. 페이지별 OCR 혼합을 지원한다. xlsx는 openpyxl read_only/data_only로 저장값을 읽고 원 수식 여부를 별도로 확인한다. xls는 xlrd로 읽는다. 수식을 실행하거나 캐시 없는 값을 추측하지 않는다. 매핑은 명시적 라벨·표 머리글·고객별 규칙으로 하며 미인식 값은 None과 evidence로 남긴다. 여러 페이지의 반복 머리글을 품목으로 중복 수집하지 않는다. 단위·통화·날짜가 모호하면 경고한다.
- [ ] **Step 4:** worker는 job 상태·시작·종료·오류를 기록하고 프로세스 재시작 시 만료된 lease를 회수한다. OCR 없음·언어팩 없음·시간초과·암호화·손상은 확인 가능한 실패로 끝내고 수동 입력을 제공한다. 확인 화면은 원본과 evidence·수정 가능한 필드·누락값·비교 차이를 보여준다. confirm_draft는 row_version과 중복 확정 키를 검사해 이중 클릭으로 PO를 두 번 만들지 않는다. 동일 source 수정본 연결·PO 변경·업무 재계산은 한 DB 트랜잭션으로 처리한다.
- [ ] **Step 5:** `python manage.py test intake orders work -v 2` 및 `e2e/`의 `npx playwright test intake.spec.mjs`를 통과시킨다. E2E는 업로드→인식 대기→원본 비교→수량 수정→등록→원본 재다운로드 해시 동일을 검증한다. 스캔 테스트는 실제 Tesseract를 사용하는 통합 테스트를 분리하고 엔진 미설치 시 운영 인수 미완료로 표시한다.
- [ ] **Step 6:** `feat: extract and review local PDF and Excel PO files`로 커밋한다. 실제 고객 PO 샘플별 인식 필드·누락·보정 결과를 인수 문서에 기록한다. 샘플이 없으면 fixture 통과와 실파일 검수 미완료를 구별한다.

