# PO

사내 PO 관리·분할출고·업무 달력·문자 알림 웹앱입니다. 실제 앱, UI 목업, 설계·실행계획, DB 마이그레이션, 테스트, Windows 실행 스크립트를 함께 보관합니다.

## 다른 데스크탑에서 시작하기

**[새 데스크탑 설치·데이터 이전·ERP 연동 안내](docs/operations/new-desktop-setup.md)**를 먼저 읽어 주세요.

```powershell
git clone https://github.com/switchkorea03/PO.git
cd PO
```

그다음 Python·PostgreSQL·OCR를 준비하고 비공개 `.env`를 설정합니다. 고객 PO 원본·실사용 DB·인증정보·설치된 실행 프로그램은 소스에 포함하지 않습니다. 기존 고객 기록까지 사용하려면 별도 비공개 백업을 복원해야 합니다.

## 폴더 구성

| 경로 | 내용 |
|---|---|
| `server/` | 실제 Django 앱·API·모델·템플릿·JavaScript·마이그레이션·테스트 |
| `server/inventory/` | ERP 재고 연결 준비 화면과 공급자 인터페이스 |
| `ops/` | 로컬 실행·자동 시작·백업·복구 스크립트 |
| `ui-prototype/` | 최종 설계 기반 클릭형 목업. 실제 DB와 별도 |
| `po-calendar/`, `ui-mockup/` | 초기 목업·이전 설계 검토 자료. 실제 앱의 업무 규칙은 `server/` 기준 |
| `docs/superpowers/` | 초기부터 최종 설계·실행계획 이력 |
| `docs/operations/` | 기능 개선·검증·배포·PC 이전 안내 |

## 주요 기능과 연결 상태

고객·다품목 PO, PDF/이미지/Excel 확인 등록, 고객품목·자사품목 연결, 국내외 일정 계산, 분할출고·잔량·취소·정정, 업무 체크·수동 날짜 변경, 원본·변경 이력, 휴지통·Excel 내보내기를 포함합니다. Gemini 인식 보조와 문자 발송은 각 서비스의 비공개 인증정보 및 운영 설정이 있을 때 사용합니다.

**iCUBE ERP의 실제 재고 조회는 아직 연결되지 않았습니다.** `server/inventory/providers.py`는 미연결 상태를 반환하며, 실제 ERP의 승인된 조회 경로·회사/창고/품목코드/단위를 확인한 뒤 연결합니다. 자세한 내용은 [ERP 인계 문서](docs/operations/2026-11-09-desktop-erp-handoff.md)를 확인하세요.

## 실행·검증 안내

- [서버 실행 및 환경 설정](server/README.md)
- [새 데스크탑 환경 준비](docs/operations/new-desktop-setup.md)
- [DB·원본 파일 백업과 복구](docs/operations/backup-restore.md)
- [Windows 자동 실행](docs/operations/autostart.md)
- [화면 구성과 수정 위치](docs/operations/frontend.md)
- [UI 목업 사용법](ui-prototype/README.md)

현재 통합 소스의 확인 결과: 서버 테스트149개, 화면 수량·목업 계산 테스트40개 통과. 실제 ERP 연결·문자 수신·새 PC의 고객 데이터 복원은 해당 환경에서 별도 확인해야 합니다.

초기 GitHub 설계 문서는 보존했습니다. 현재 앱의 설계 기준은 [2026-10-16 설계서](docs/superpowers/specs/2026-10-16-po-management-calendar-design.md)와 이후 `docs/operations/`의 변경 기록을 함께 참고하세요.
