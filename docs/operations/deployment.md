# 내부 배포 및 실행

현재 로컬 서비스는127.0.0.1:8000으로 제한합니다. 회사 내부 주소·HTTPS 인증서·운영 DB 계정·실문자 계정은 미제공이므로 회사 운영 배포 완료를 뜻하지 않습니다.

운영 환경에는 Python3.12, PostgreSQL17, Tesseract5(kor/eng), requirements.lock 의존성을 준비합니다. 운영 앱 DB 계정에는 필요한 권한만 주며 로컬 initdb 관리자 계정을 재사용하지 않습니다.

## 설정 및 프로세스

`DEBUG=0`, 임의의 긴 `SECRET_KEY`, 실제 `ALLOWED_HOSTS`, HTTPS 원본의 `CSRF_TRUSTED_ORIGINS`, `PRIVATE_MEDIA_ROOT`, DB 연결정보를 비공개 환경에 설정합니다. `ENV_FILE`로 별도 설정 파일을 지정할 수 있습니다.

Waitress 앞에 HTTPS reverse proxy를 두고 신뢰할 수 있는 프록시가 `X-Forwarded-Proto`를 덮어쓰도록 설정합니다. collectstatic 결과만 정적 파일로 제공하고 private media는 공개 디렉터리에 매핑하지 않습니다.

```powershell
.\.venv\Scripts\python.exe server/manage.py migrate --noinput
.\.venv\Scripts\python.exe server/manage.py collectstatic --noinput
.\.venv\Scripts\python.exe server/manage.py check --deploy
```

웹, `run_intake_worker`, `run_notice_worker`를 각각 상주 실행합니다. 회사 승인 서비스 관리자 또는 작업 스케줄러에 재시작·로그 회전·절전 방지를 설정합니다. 이번 구현은 회사 OS 서비스를 자동 등록하지 않습니다.

문자 worker는30초마다 확인하므로09시 정기는 실행 주기 범위 내에 처리됩니다. 같은 평일에 재개하면 현재 업무로 그날의 첫 정기를 만듭니다. 지난 미접수 batch는 만료하고 다음 평일 지연 목록으로 안내합니다.

`.runtime/*-error.log`, worker heartbeat, 문자 실패·미확정 표시를 확인합니다. `.runtime`에는 현재 로컬 DB도 있으므로 폴더 전체를 정리하지 않습니다.

## 문자 공급자

SOLAPI 어댑터는 공식 [발송 API](https://solapi.com/developers/api/messages), [내역 조회](https://solapi.com/developers/api/msg-getList), [인증](https://solapi.com/developers/api/authentication-api-key)을 기준으로 구현했습니다. 회사 공급자가 다르면 동일 계약의 어댑터로 교체합니다. 서비스 가입·구매는 진행하지 않았습니다.

messageId가 없는 불명확 결과는 최근7일·최대2500건에서 customFields.clientKey를 조회합니다. 찾지 못해도 실패로 단정하지 않으며 자동 재발송하지 않습니다. 계정·발신번호·본인 수신번호 설정 후 실제 수신1건을 검수합니다.
