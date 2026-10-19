def catalog(kind,erp_type="unspecified",currency="KRW"):
    export=erp_type=="export" or currency=="USD"
    known=erp_type!="unspecified" or currency in ("KRW","USD")
    request="출고의뢰등록(수출)" if export else "출고의뢰등록"
    voucher="거래명세서(수출)" if export else "출고처리"
    if not known:request=voucher="거래유형 지정 후 ERP 메뉴 확인"
    return {
      "domestic_share":("출고 내역 공유",("출고품·수량·출고일을 고객에게 메일 전달",)),
      "domestic_request":("의뢰서(ERP)+명세서(PDF) 전달",("거래명세서 PDF 저장·인쇄",f"{request}: 출고의뢰 등록·인쇄","명세서·의뢰서를 구매팀에 전달")),
      "domestic_statement":("명세서 공유",("거래명세서 PDF를 고객에게 전달",)),
      "domestic_excel":("엑셀 기입",("출하계획 Excel에 수량 입력",)),
      "domestic_voucher":("전표 인쇄",(f"{voucher}: 출고전표 인쇄","전표를 반으로 잘라 지정 바구니에 전달")),
      "overseas_invoice":("인보이스+ERP",("인보이스 작성·중국 공장에 메일 전달","ERP 주문등록(수출)")),
      "overseas_bl_eta":("BL, ETA 고객 공유",("BL 서류를 고객에게 전달","ETA를 고객에게 안내")),
      "overseas_erp":("ERP 2개 처리",("수입선적등록(수입)","입고처리(수입)")),
      "overseas_mail":("출고 메일",("중계무역 출고메일을 내부 영업관리팀에 공유",)),
      "overseas_excel":("엑셀 기입",("출하계획 Excel에 수량 입력",))
    }[kind]
