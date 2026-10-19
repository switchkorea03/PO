# 백업과 격리 복구

## 백업

```powershell
.\ops\backup.ps1 -Destination 'D:\회사승인백업경로\po-2026-10-19'
```

새 디렉터리에만 생성합니다. 점검 표시로 웹 접근과 신규 worker 처리를 잠시 중지하고 PostgreSQL SHARE 잠금·exported snapshot으로 DB와 참조 원본을 일관되게 묶습니다. 파일·dump의 SHA-256, PO/원본/업무 개수, 완료 업무 ID를 manifest에 기록합니다.

운영 제안값은 매일18시 KST·최근30회 보존입니다. 경로·주기·보존은 회사 정책 확정 후 외부 스케줄러에서 설정합니다. 기존 백업 삭제는 자동 실행하지 않습니다. 비정상 종료 시 작업 프로세스를 확인한 후 `.runtime/maintenance`를 해제합니다.

## 격리 복구

```powershell
.\ops\restore.ps1 -Source 'D:\회사승인백업경로\po-2026-10-19' -TargetDatabase 'po_verify_restore' -TargetMedia 'D:\별도복구경로\po-media'
```

운영 DB와 다른 새 `*_restore` DB·새 media만 허용합니다. 기존 테이블이 있거나 media가 존재하면 덮어쓰지 않습니다. 해시 검증 후 복구하고 원본 경로를 새 media로 변경합니다. DB 개수·완료 업무 ID와 원본 파일을 대조합니다.

복구 DB의 문자 알림은 강제로 비활성화합니다. 검토 환경에 `PGDATABASE=po_verify_restore`, `PRIVATE_MEDIA_ROOT=복구media`, `SMS_PROVIDER=fake`, `SMS_LIVE_ENABLED=0`을 함께 지정합니다. 복구 outbox로 실문자 worker를 실행하지 않습니다.

이 스크립트는 운영 DB를 교체하지 않습니다. 운영 전환은 격리 복구 검증과 회사의 전환 승인을 거친 별도 작업입니다.
