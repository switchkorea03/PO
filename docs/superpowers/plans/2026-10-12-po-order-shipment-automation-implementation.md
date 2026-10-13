# PO Order and Shipment Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 고객 PO 등록부터 국내 출고·해외 중계무역·iCUBE·Outlook·공유 Excel 반영까지를 통제형 자동화로 처리하는 사내 웹 시스템을 구축한다.

**Architecture:** .NET 10 Blazor Web App 기반 모듈형 모놀리스로 시작하고, 업무 규칙은 Domain/Application에, SQL Server·문서·Outlook·iCUBE·공유 Excel 연계는 Infrastructure 어댑터에 둔다. 외부 쓰기는 내구성 작업 큐와 중복방지 키를 통과하며, 생산요청과 최종 Excel 반영은 담당자 승인 전에는 실행되지 않는다.

**Tech Stack:** .NET 10 LTS, ASP.NET Core/Blazor interactive server, EF Core 10, SQL Server 2022+, Microsoft Graph v1.0, Open XML SDK, ClosedXML, Tesseract 5 OCR, LibreOffice headless PDF renderer, xUnit, bUnit, Playwright, WireMock.Net, Testcontainers for SQL Server

**Spec:** `docs/superpowers/specs/2026-10-12-po-order-shipment-automation-design.md`

## Global Constraints

- 내부 웹사이트와 데이터베이스가 PO 및 업무상태의 기준 원본이며 Excel은 입출력 결과물이다.
- 정상 문서 변환·조회·메일 처리는 자동화하되 생산요청 수량, 중요 불일치, 공유 Excel 쓰기는 담당자 승인 후 실행한다.
- 국내 재고는 iCUBE `일별재고현황`, 해외 납품 가능 판단은 `발주미납현황(수입)` 잔량을 사용한다.
- 생산요청은 담당자가 수량을 직접 입력하고 승인한 뒤 `발주등록(수입_기타)`에 등록한다.
- 국내 생산요청 납기일 기본값은 등록일 + 14일, 해외 기본값은 등록 당일이다.
- 해외 운송방식 기본값은 `VSL`이며 담당자가 `AIR`로 변경할 수 있다.
- 공유 Excel 행 키는 `담당자 + 거래처명 + 모델명 + 통화 + 단가`이며 담당자 미리보기 승인 전에는 수정하지 않는다.
- Outlook·iCUBE·공유 Excel 작업은 중복방지 키와 감사이력을 가져야 한다.
- 외부 자격증명은 코드·설정파일·Git에 저장하지 않고 개발환경은 user-secrets, 운영환경은 회사 비밀저장소를 사용한다.
- 모든 날짜·시간 저장은 UTC, 업무 규칙과 화면 표시는 `Asia/Seoul`, 업무일자는 `DateOnly`를 사용한다.
- nullable reference types와 warnings-as-errors를 활성화한다.
- 실제 iCUBE·Outlook·공유폴더 쓰기는 별도 시험환경의 계약시험을 통과하고 기능 플래그가 활성화된 후에만 허용한다.

## Review Focus

1. 같은 PO·Graph 메시지·작업이 재전달되거나 재시도되어도 주문, ERP 등록, 메일, Excel 수량이 중복 생성되지 않아야 한다. Task 3, 7, 8, 9에서 고정한다.
2. 국내 분할납품의 누적 실제수량이 PO 총수량을 넘지 않고, 일부 취소·수정 후 잔량이 정확해야 한다. Task 4에서 고정한다.
3. QP 제목은 맞지만 발신자가 미등록이거나 QY 후보가 둘 이상이면 자동 연결하지 않고 예외로 보내야 한다. Task 7에서 고정한다.
4. Excel 미리보기 뒤 파일이 바뀌거나 대상 셀에 다른 값이 생기면 승인을 무효화하고 재미리보기를 요구해야 한다. Task 9에서 고정한다.
5. iCUBE·Graph·파일공유가 일시 실패한 뒤 재시도되어도 이미 성공한 단계는 반복하지 않고 실패 단계부터 이어져야 한다. Task 8, 10에서 고정한다.

---

## Delivery Increments

이 명세는 여러 연계 하위 시스템을 포함하므로 다음 네 개의 독립 검토 단위로 전달한다.

1. **Core PO:** Task 1~3. 외부 쓰기 없이 PO 업로드·검토·검색이 가능한 시스템.
2. **Domestic:** Task 4~5. 국내 납품·잔량·생산요청 승인과 iCUBE 계약이 가능한 시스템.
3. **Overseas:** Task 6~8. QY 발송, QP·BL 수신·검증과 후속처리가 가능한 시스템.
4. **Excel & Operations:** Task 9~11. 공유 Excel 승인 반영, 예외·대시보드, 배포·인수시험이 가능한 시스템.

각 증분은 해당 Task의 전체 테스트가 통과하고 별도 리뷰를 받은 후 다음 증분으로 넘어간다.

## File Structure

```text
PoAutomation.sln
Directory.Build.props
src/
  PoAutomation.Domain/                 # 주문·납품·선적·승인 상태와 순수 업무 규칙
    Common/
    Customers/
    Orders/
    Domestic/
    Overseas/
    Workflows/
  PoAutomation.Application/            # 유스케이스, 명령·조회, 외부 포트
    Abstractions/
    Customers/
    Orders/
    Domestic/
    Overseas/
    Exceptions/
    SharedWorkbook/
  PoAutomation.Infrastructure/         # SQL Server와 외부 시스템 어댑터
    Persistence/
    Documents/
    Icube/
    Outlook/
    SharedWorkbook/
    Jobs/
  PoAutomation.Web/                    # Blazor 화면, 인증·인가, HTTP 호스트
    Components/
    Auth/
    Program.cs
tools/
  PoAutomation.IcubeProbe/             # iCUBE 연계수단 확인용 읽기 전용 진단도구
  PoAutomation.WorkbookProbe/          # 공유 Excel 구조·수식 보존 진단도구
tests/
  PoAutomation.Domain.Tests/
  PoAutomation.Application.Tests/
  PoAutomation.Infrastructure.Tests/
  PoAutomation.Web.Tests/
  PoAutomation.E2E.Tests/
docs/
  decisions/
  runbooks/
```

---

### Task 1: Solution Foundation, Authentication, Persistence, and Durable Jobs

**Files:**
- Create: `PoAutomation.sln`
- Create: `Directory.Build.props`
- Create: `src/PoAutomation.Domain/PoAutomation.Domain.csproj`
- Create: `src/PoAutomation.Domain/Common/Entity.cs`
- Create: `src/PoAutomation.Domain/Common/AuditEntry.cs`
- Create: `src/PoAutomation.Domain/Common/Quantity.cs`
- Create: `src/PoAutomation.Application/PoAutomation.Application.csproj`
- Create: `src/PoAutomation.Application/Abstractions/IClock.cs`
- Create: `src/PoAutomation.Application/Abstractions/ICurrentUser.cs`
- Create: `src/PoAutomation.Application/Abstractions/IUnitOfWork.cs`
- Create: `src/PoAutomation.Application/Abstractions/IWorkQueue.cs`
- Create: `src/PoAutomation.Application/Abstractions/IDocumentStore.cs`
- Create: `src/PoAutomation.Application/Abstractions/IMailGateway.cs`
- Create: `src/PoAutomation.Infrastructure/PoAutomation.Infrastructure.csproj`
- Create: `src/PoAutomation.Infrastructure/Persistence/AppDbContext.cs`
- Create: `src/PoAutomation.Infrastructure/Jobs/DurableWorkItem.cs`
- Create: `src/PoAutomation.Infrastructure/Jobs/SqlWorkQueue.cs`
- Create: `src/PoAutomation.Infrastructure/Jobs/WorkQueueHostedService.cs`
- Create: `src/PoAutomation.Web/PoAutomation.Web.csproj`
- Create: `src/PoAutomation.Web/Program.cs`
- Create: `src/PoAutomation.Web/Auth/AppRole.cs`
- Create: `tests/PoAutomation.Architecture.Tests/DependencyRulesTests.cs`
- Create: `tests/PoAutomation.Infrastructure.Tests/Jobs/SqlWorkQueueTests.cs`

**Interfaces:**
- Produces: `IClock.UtcNow`, `ICurrentUser.UserId`, `IUnitOfWork.SaveChangesAsync(CancellationToken)`, `IWorkQueue.EnqueueAsync(WorkRequest, CancellationToken)`.
- Produces: `IDocumentStore.SaveAsync`, `OpenReadAsync`, and `IMailGateway.SendAsync(OutgoingMail, string idempotencyKey, CancellationToken)` ports for later adapters.
- Produces: Entra ID OIDC in production, test authentication handler outside production, roles `Sales`, `Purchasing`, `SalesAdmin`, `Administrator`.
- Produces: durable work items with unique `IdempotencyKey`, states `Pending`, `Running`, `Succeeded`, `Failed`, and exponential retry metadata.

- [ ] **Step 1: Write failing architecture and queue tests**

Add tests named `domain_does_not_reference_infrastructure`, `duplicate_idempotency_key_returns_existing_work_item`, and `failed_work_item_is_reclaimed_after_next_attempt_at`.

```csharp
[Fact]
public async Task Duplicate_idempotency_key_returns_existing_work_item()
{
    var first = await queue.EnqueueAsync(new("mail:order-1:shipping", "SendMail", "{}"), ct);
    var second = await queue.EnqueueAsync(new("mail:order-1:shipping", "SendMail", "{}"), ct);
    Assert.Equal(first.Id, second.Id);
}
```

- [ ] **Step 2: Run tests and verify the foundation is absent**

Run: `dotnet test PoAutomation.sln --filter "DependencyRules|SqlWorkQueue"`

Expected: FAIL because the solution, projects, and queue types do not exist.

- [ ] **Step 3: Scaffold the solution and implement the minimal persistence and queue contracts**

Target `net10.0`; enable `Nullable`, `ImplicitUsings`, `TreatWarningsAsErrors`, deterministic builds, EF Core SQL Server, Entra OIDC, health checks, and OpenTelemetry logging. Implement SQL uniqueness on `DurableWorkItem.IdempotencyKey` and a hosted worker that claims one due item in a transaction.

- [ ] **Step 4: Run foundation tests**

Run: `dotnet test PoAutomation.sln --filter "DependencyRules|SqlWorkQueue"`

Expected: PASS with no warnings.

- [ ] **Step 5: Commit**

```bash
git add PoAutomation.sln Directory.Build.props src tests
git commit -m "feat: establish application foundation and durable work queue"
```

---

### Task 2: Customer, Template, Mailbox, and Workbook Master Data

**Files:**
- Create: `src/PoAutomation.Domain/Customers/Customer.cs`
- Create: `src/PoAutomation.Domain/Customers/CustomerCode.cs`
- Create: `src/PoAutomation.Domain/Customers/DocumentTemplate.cs`
- Create: `src/PoAutomation.Domain/Customers/FactorySender.cs`
- Create: `src/PoAutomation.Application/Customers/CustomerCommands.cs`
- Create: `src/PoAutomation.Application/Customers/CustomerQueries.cs`
- Create: `src/PoAutomation.Application/Customers/ICustomerRepository.cs`
- Create: `src/PoAutomation.Infrastructure/Persistence/Configurations/CustomerConfiguration.cs`
- Create: `src/PoAutomation.Web/Components/Pages/Admin/Customers.razor`
- Create: `src/PoAutomation.Web/Components/Pages/Admin/CustomerEdit.razor`
- Create: `tests/PoAutomation.Domain.Tests/Customers/CustomerTests.cs`
- Create: `tests/PoAutomation.Web.Tests/Admin/CustomerEditTests.cs`

**Interfaces:**
- Consumes: `IUnitOfWork`, `ICurrentUser` from Task 1.
- Produces: `Customer` with `TradeType`, `DocumentCode`, `AllowsSplitDelivery`, assigned sales user, PO/output template IDs, mail recipients, and active factory sender addresses/domains.
- Produces: `ICustomerRepository.GetByIdAsync`, `FindByPoFingerprintAsync`, and `IsAllowedFactorySenderAsync`.

- [ ] **Step 1: Write failing customer invariants and authorization tests**

Cover unique customer document code, editable domestic/overseas default, split-delivery flag default `false`, multiple active factory senders, and only `Administrator` access to edits.

- [ ] **Step 2: Run the focused tests**

Run: `dotnet test PoAutomation.sln --filter "Customer"`

Expected: FAIL because customer master types and pages do not exist.

- [ ] **Step 3: Implement master data domain, EF mapping, commands, and Blazor pages**

Use normalized e-mail addresses and case-insensitive uniqueness. Store template binaries through `IDocumentStore`; keep only document IDs and versions in SQL.

- [ ] **Step 4: Verify customer master behavior**

Run: `dotnet test PoAutomation.sln --filter "Customer"`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/PoAutomation.Domain/Customers src/PoAutomation.Application/Customers src/PoAutomation.Infrastructure/Persistence src/PoAutomation.Web/Components/Pages/Admin tests
git commit -m "feat: add customer and template master data"
```

---

### Task 3: PO Upload, Extraction, Validation, and Search

**Files:**
- Create: `src/PoAutomation.Domain/Orders/PurchaseOrder.cs`
- Create: `src/PoAutomation.Domain/Orders/PurchaseOrderLine.cs`
- Create: `src/PoAutomation.Domain/Orders/OrderStatus.cs`
- Create: `src/PoAutomation.Application/Orders/IPoExtractor.cs`
- Create: `src/PoAutomation.Application/Orders/IPurchaseOrderRepository.cs`
- Create: `src/PoAutomation.Application/Orders/RegisterPoCommand.cs`
- Create: `src/PoAutomation.Application/Orders/ConfirmPoCommand.cs`
- Create: `src/PoAutomation.Application/Orders/SearchOrdersQuery.cs`
- Create: `src/PoAutomation.Infrastructure/Documents/TemplatePoExtractor.cs`
- Create: `src/PoAutomation.Infrastructure/Documents/TesseractOcrService.cs`
- Create: `src/PoAutomation.Infrastructure/Documents/FileSystemDocumentStore.cs`
- Create: `src/PoAutomation.Web/Components/Pages/Orders/Upload.razor`
- Create: `src/PoAutomation.Web/Components/Pages/Orders/Review.razor`
- Create: `src/PoAutomation.Web/Components/Pages/Orders/Index.razor`
- Create: `tests/PoAutomation.Domain.Tests/Orders/PurchaseOrderTests.cs`
- Create: `tests/PoAutomation.Application.Tests/Orders/RegisterPoTests.cs`
- Create: `tests/PoAutomation.Infrastructure.Tests/Documents/TemplatePoExtractorTests.cs`
- Add fixtures: `tests/Fixtures/po/*.pdf`

**Interfaces:**
- Consumes: customer/template data from Task 2 and Task 1 persistence abstractions.
- Produces: `IPoExtractor.ExtractAsync(PoDocument document, CustomerTemplate template, CancellationToken) -> PoExtractionResult`.
- Produces: `RegisterPoCommand(Stream Content, string FileName, CustomerId CustomerId)` and `ConfirmPoCommand(OrderId, TradeType, IReadOnlyList<ConfirmedPoLine>)`.
- Produces: persisted original PDF, field-level source/confidence, extracted and corrected values, and status `ReviewPending` or `Processing`.

- [ ] **Step 1: Write failing PO domain and application tests**

Cover required fields, `SupplyAmount = Quantity * UnitPrice`, duplicate `(CustomerId, PoNumber)`, unsupported template, low-confidence required field, and same command retried twice returning one order.

```csharp
[Fact]
public async Task Duplicate_customer_po_number_is_rejected()
{
    await handler.Handle(command with { PoNumber = "PO-001" }, ct);
    var error = await Assert.ThrowsAsync<DuplicatePoException>(() => handler.Handle(command, ct));
    Assert.Equal("PO-001", error.PoNumber);
}
```

- [ ] **Step 2: Run the focused tests**

Run: `dotnet test PoAutomation.sln --filter "PurchaseOrder|RegisterPo|TemplatePoExtractor"`

Expected: FAIL because PO behavior is not implemented.

- [ ] **Step 3: Implement upload, extraction, review, confirmation, and search**

Reject non-PDF uploads, enforce a configurable size limit with a 20 MB default, calculate SHA-256 for document deduplication, and never discard the original. Use text extraction first and Tesseract only for pages/regions without usable text.

- [ ] **Step 4: Run PO tests and a browser component test**

Run: `dotnet test PoAutomation.sln --filter "PurchaseOrder|RegisterPo|TemplatePoExtractor|OrderUpload"`

Expected: PASS; duplicate retry creates one order and low-confidence fields remain in review.

- [ ] **Step 5: Commit**

```bash
git add src tests/Fixtures/po tests
git commit -m "feat: add PO upload extraction and review"
```

---

### Task 4: Domestic Delivery Schedules, Documents, and Remaining Quantity

**Files:**
- Create: `src/PoAutomation.Domain/Domestic/DeliverySchedule.cs`
- Create: `src/PoAutomation.Domain/Domestic/DeliveryLot.cs`
- Create: `src/PoAutomation.Application/Domestic/ScheduleDeliveryCommand.cs`
- Create: `src/PoAutomation.Application/Domestic/ConfirmActualDeliveryCommand.cs`
- Create: `src/PoAutomation.Application/Domestic/GenerateDomesticDocumentsCommand.cs`
- Create: `src/PoAutomation.Application/Abstractions/IDocumentGenerator.cs`
- Create: `src/PoAutomation.Infrastructure/Documents/ClosedXmlTemplateGenerator.cs`
- Create: `src/PoAutomation.Infrastructure/Documents/LibreOfficePdfRenderer.cs`
- Create: `src/PoAutomation.Web/Components/Pages/Orders/DomesticTab.razor`
- Create: `tests/PoAutomation.Domain.Tests/Domestic/DeliveryScheduleTests.cs`
- Create: `tests/PoAutomation.Application.Tests/Domestic/DomesticWorkflowTests.cs`
- Add fixtures: `tests/Fixtures/domestic-templates/*.xlsx`

**Interfaces:**
- Consumes: confirmed domestic `PurchaseOrder` from Task 3, customer `AllowsSplitDelivery` from Task 2, and `IMailGateway` from Task 1.
- Produces: `DeliverySchedule.AddLot(DateOnly plannedDate, Quantity plannedQuantity)`, `ConfirmActual(lotId, DateOnly actualDate, Quantity actualQuantity)`, `RemainingQuantity`.
- Produces: `IDocumentGenerator.GenerateAsync(DocumentTemplateId, IReadOnlyDictionary<string, object?>, CancellationToken) -> GeneratedDocument`.

- [ ] **Step 1: Write failing delivery and document tests**

Test one-shot default delivery, split delivery only for allowed customers, mixed later dates, correction/cancellation, `RemainingQuantity`, rejection when cumulative actual quantity exceeds PO quantity, purchasing mail on the day before each delivery, and customer transaction-statement mail on the actual delivery date.

```csharp
[Fact]
public void Split_delivery_cannot_exceed_order_quantity()
{
    var schedule = DeliverySchedule.ForSplitOrder(Quantity.Of(100));
    schedule.ConfirmActual(schedule.AddLot(date1, Quantity.Of(60)), date1, Quantity.Of(60));
    Assert.Throws<OverDeliveryException>(() =>
        schedule.ConfirmActual(schedule.AddLot(date2, Quantity.Of(50)), date2, Quantity.Of(50)));
}
```

- [ ] **Step 2: Run domestic tests**

Run: `dotnet test PoAutomation.sln --filter "DeliverySchedule|DomesticWorkflow"`

Expected: FAIL because delivery scheduling is absent.

- [ ] **Step 3: Implement delivery state and customer-template document generation**

Generate transaction statement Excel and PDF per delivery lot. Create human tasks for print, face-to-face purchasing handoff, and sales basket storage; do not mark physical tasks complete automatically.

- [ ] **Step 4: Verify domestic flow**

Run: `dotnet test PoAutomation.sln --filter "DeliverySchedule|DomesticWorkflow|ClosedXmlTemplateGenerator"`

Expected: PASS; generated fixtures preserve template formatting and over-delivery is blocked.

- [ ] **Step 5: Commit**

```bash
git add src tests/Fixtures/domestic-templates tests
git commit -m "feat: add domestic delivery scheduling and documents"
```

---

### Task 5: iCUBE Contracts, Read-Only Probe, Inventory, and Production Approval

**Files:**
- Create: `src/PoAutomation.Application/Abstractions/IIcubeGateway.cs`
- Create: `src/PoAutomation.Domain/Workflows/InventorySnapshot.cs`
- Create: `src/PoAutomation.Domain/Workflows/ProductionRequest.cs`
- Create: `src/PoAutomation.Application/Domestic/CheckDomesticInventoryCommand.cs`
- Create: `src/PoAutomation.Application/Overseas/CheckImportOutstandingCommand.cs`
- Create: `src/PoAutomation.Application/Orders/SubmitProductionRequestCommand.cs`
- Create: `src/PoAutomation.Application/Orders/ApproveProductionRequestCommand.cs`
- Create: `src/PoAutomation.Infrastructure/Icube/IcubeGateway.cs`
- Create: `src/PoAutomation.Infrastructure/Icube/IcubeContractOptions.cs`
- Create: `tools/PoAutomation.IcubeProbe/Program.cs`
- Create: `docs/decisions/ADR-0001-icube-transport.md`
- Create: `src/PoAutomation.Web/Components/Pages/Orders/ProductionRequestPanel.razor`
- Create: `tests/PoAutomation.Application.Tests/Icube/InventoryAndProductionTests.cs`
- Create: `tests/PoAutomation.Infrastructure.Tests/Icube/IcubeContractTests.cs`

**Interfaces:**
- Consumes: order and user data from Tasks 1~4.
- Produces: `IIcubeGateway.GetDailyInventoryAsync(ProductName, CancellationToken)`, `GetImportOutstandingAsync(ProductKey, CancellationToken)`, `RegisterImportOtherOrderAsync(ApprovedProductionRequest, CancellationToken)`, `RegisterImportShipmentAsync`, `RegisterReceiptAsync`.
- Produces: read-only probe report selecting the first company-approved transport in order: official interface, approved DB/file, approved UI automation.

- [ ] **Step 1: Write failing application contract tests using `FakeIcubeGateway`**

Cover domestic source=`일별재고현황`, overseas source=`발주미납현황(수입)`, immediate shortage notification, no automatic production quantity, domestic due date `+14 days`, overseas due date `same day`, and registration prohibited before the owning sales user approves.

- [ ] **Step 2: Run iCUBE application tests**

Run: `dotnet test tests/PoAutomation.Application.Tests --filter "InventoryAndProduction"`

Expected: FAIL because the iCUBE port and production workflow do not exist.

- [ ] **Step 3: Implement the port, domain workflow, UI, and read-only probe**

The probe must never write to iCUBE. It records version/module, available official interface, approved file/DB access, field samples for named menus, authentication method, and evidence for the chosen transport in ADR-0001. `IcubeGateway` then implements only that approved transport; keep write methods behind feature flag `Integrations:Icube:WritesEnabled=false` by default.

- [ ] **Step 4: Run fake tests, then the contract suite against a non-production iCUBE environment**

Run: `dotnet test PoAutomation.sln --filter "InventoryAndProduction|IcubeContract"`

Expected: application tests PASS; contract tests PASS only when `ICUBE_TEST_*` secrets point to the approved test environment, otherwise SKIP with a single explicit reason.

- [ ] **Step 5: Commit**

```bash
git add src tools tests docs/decisions/ADR-0001-icube-transport.md
git commit -m "feat: add iCUBE inventory and approved production workflow"
```

---

### Task 6: Overseas QY Invoice Numbering, Generation, and Sending

**Files:**
- Create: `src/PoAutomation.Domain/Overseas/TransportMode.cs`
- Create: `src/PoAutomation.Domain/Overseas/InvoiceNumber.cs`
- Create: `src/PoAutomation.Domain/Overseas/OverseasShipment.cs`
- Create: `src/PoAutomation.Application/Overseas/IInvoiceNumberService.cs`
- Create: `src/PoAutomation.Application/Overseas/CreateQyInvoiceCommand.cs`
- Create: `src/PoAutomation.Infrastructure/Persistence/InvoiceSequence.cs`
- Create: `src/PoAutomation.Infrastructure/Outlook/GraphMailGateway.cs`
- Create: `src/PoAutomation.Web/Components/Pages/Orders/OverseasTab.razor`
- Create: `tests/PoAutomation.Domain.Tests/Overseas/InvoiceNumberTests.cs`
- Create: `tests/PoAutomation.Application.Tests/Overseas/CreateQyInvoiceTests.cs`

**Interfaces:**
- Consumes: customer `DocumentCode`, document templates, work queue, and `IMailGateway` from Task 1.
- Produces: `IInvoiceNumberService.ReserveAsync(DateOnly exwDate, CustomerCode code, TransportMode mode, CancellationToken) -> InvoiceNumberReservation`.
- Produces: format `QY{yyMMdd}-{sequence}{customerCode}({VSL|AIR})`, never-resetting sequence, default `VSL`, and user-editable final number guarded by unique index.
- Produces: `GraphMailGateway` implementing `IMailGateway.SendAsync(OutgoingMail, string idempotencyKey, CancellationToken) -> MailSendReceipt`.

- [ ] **Step 1: Write failing invoice number and concurrent reservation tests**

Assert `QY261013-40CHVN(VSL)`, AIR override, no annual/monthly reset, duplicate manual number rejection, and 20 concurrent reservations producing 20 distinct consecutive numbers.

- [ ] **Step 2: Run QY tests**

Run: `dotnet test PoAutomation.sln --filter "InvoiceNumber|CreateQyInvoice"`

Expected: FAIL because numbering and generation are absent.

- [ ] **Step 3: Implement transactional sequence reservation, template generation, and queued Graph send**

Use a SQL transaction and unique index for sequence reservation. Generate the customer-specific Excel before queueing the mail. Persist the exact generated file hash and recipients with the send request.

- [ ] **Step 4: Verify QY creation and Graph request contract**

Run: `dotnet test PoAutomation.sln --filter "InvoiceNumber|CreateQyInvoice|GraphMailGateway"`

Expected: PASS; a retried send has one Graph request for its idempotency key.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat: generate and send overseas QY invoices"
```

---

### Task 7: Outlook QP Mail Ingestion and BL Workbook Parsing

**Files:**
- Create: `src/PoAutomation.Application/Overseas/IQpMailClassifier.cs`
- Create: `src/PoAutomation.Application/Overseas/IBlWorkbookReader.cs`
- Create: `src/PoAutomation.Application/Overseas/IngestFactoryMailCommand.cs`
- Create: `src/PoAutomation.Infrastructure/Outlook/GraphMailboxPoller.cs`
- Create: `src/PoAutomation.Infrastructure/Outlook/QpMailClassifier.cs`
- Create: `src/PoAutomation.Infrastructure/Documents/OpenXmlBlWorkbookReader.cs`
- Create: `src/PoAutomation.Infrastructure/Documents/OnBoardOcrParser.cs`
- Create: `tests/PoAutomation.Infrastructure.Tests/Outlook/QpMailClassifierTests.cs`
- Create: `tests/PoAutomation.Infrastructure.Tests/Documents/BlWorkbookReaderTests.cs`
- Create: `tests/PoAutomation.Application.Tests/Overseas/IngestFactoryMailTests.cs`
- Add fixtures: `tests/Fixtures/mail/qp-mail.json`
- Add fixtures: `tests/Fixtures/bl/*.xlsx`

**Interfaces:**
- Consumes: active factory senders from Task 2, QY shipments from Task 6, Graph mail gateway from Task 6.
- Produces: `IQpMailClassifier.Classify(FactoryMail) -> QpMailClassification` containing QP number, ETD, ETA, candidate QY ID, and confidence/issues.
- Produces: `IBlWorkbookReader.ReadAsync(Stream, CancellationToken) -> BlReadResult` containing BL sheet presence, ON BOARD date, actual quantities, original suffix, and OCR confidence.

- [ ] **Step 1: Write failing classifier and BL parser tests**

Cover `QP260922-39CHVN托盘`, mapping to `QY260922-39CHVN(VSL)`, body ETD `9.30`, approximate ETA `10.11`, missing PO number, Excel without `BL` sheet, duplicate Graph message ID, unregistered sender, and two matching QY candidates.

```csharp
[Fact]
public void Unregistered_sender_with_valid_qp_subject_is_exception()
{
    var result = classifier.Classify(mail with { Subject = "QP260922-39CHVN 资料及BL" });
    Assert.Equal(QpMailDisposition.Exception, result.Disposition);
    Assert.Contains("UNREGISTERED_FACTORY_SENDER", result.Issues);
}
```

- [ ] **Step 2: Run QP/BL tests**

Run: `dotnet test PoAutomation.sln --filter "QpMail|BlWorkbook|IngestFactoryMail"`

Expected: FAIL because ingestion is absent.

- [ ] **Step 3: Implement Graph delta polling, sender validation, parsing, matching, and document storage**

Persist the Graph message ID and delta token transactionally. Do not mark a message complete until all attachments and raw message metadata are stored. Treat Chinese suffix text as preserved metadata, not a required matching key.

- [ ] **Step 4: Verify duplicate delivery and ambiguous matching**

Run: `dotnet test PoAutomation.sln --filter "QpMail|BlWorkbook|IngestFactoryMail|DuplicateGraphMessage"`

Expected: PASS; redelivery yields one stored message and ambiguous/unregistered mail creates one exception without updating shipment dates.

- [ ] **Step 5: Commit**

```bash
git add src tests/Fixtures/mail tests/Fixtures/bl tests
git commit -m "feat: ingest QP mail and parse BL workbooks"
```

---

### Task 8: Overseas Validation and Ordered Follow-up Workflow

**Files:**
- Create: `src/PoAutomation.Domain/Overseas/ShipmentValidation.cs`
- Create: `src/PoAutomation.Application/Overseas/ValidateShipmentCommand.cs`
- Create: `src/PoAutomation.Application/Overseas/ResolveShipmentExceptionCommand.cs`
- Create: `src/PoAutomation.Application/Overseas/AdvanceOverseasWorkflowCommand.cs`
- Create: `src/PoAutomation.Infrastructure/Jobs/OverseasWorkflowHandler.cs`
- Create: `src/PoAutomation.Web/Components/Pages/Orders/ShipmentValidationPanel.razor`
- Create: `tests/PoAutomation.Domain.Tests/Overseas/ShipmentValidationTests.cs`
- Create: `tests/PoAutomation.Application.Tests/Overseas/OverseasWorkflowTests.cs`

**Interfaces:**
- Consumes: QY/QP/BL data, `IMailGateway`, `IIcubeGateway`, and durable queue.
- Produces: ordered steps `Validate -> SendCustomerStatus -> RegisterImportShipment -> RegisterReceipt -> NotifySalesAdmin -> MarkWorkbookPreviewPending`.
- Produces: exception resolution with corrected ETD/ETA/quantity, reason, approver, and resume-from-failed-step semantics.

- [ ] **Step 1: Write failing validation and resume tests**

Cover matching ETD/ON BOARD, mismatched dates, Invoice/BL quantity mismatch, customer mail only after validation, iCUBE receipt only after import shipment, internal mail only after both ERP steps, and retry after receipt failure not repeating the customer mail or import registration.

- [ ] **Step 2: Run overseas workflow tests**

Run: `dotnet test PoAutomation.sln --filter "ShipmentValidation|OverseasWorkflow"`

Expected: FAIL because ordered orchestration is absent.

- [ ] **Step 3: Implement validation state machine and one idempotent handler per step**

Assign one durable work idempotency key per shipment and step, for example `overseas:{shipmentId}:customer-status`. Persist successful receipts before queueing the next step.

- [ ] **Step 4: Verify all success, mismatch, and recovery paths**

Run: `dotnet test PoAutomation.sln --filter "ShipmentValidation|OverseasWorkflow"`

Expected: PASS; failed workflow resumes exactly at the failed step.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat: orchestrate validated overseas shipment processing"
```

---

### Task 9: Shared Monthly Workbook Preview, Approval, and Safe Write

**Files:**
- Create: `src/PoAutomation.Application/SharedWorkbook/ISharedWorkbookGateway.cs`
- Create: `src/PoAutomation.Domain/Workflows/WorkbookWriteApproval.cs`
- Create: `src/PoAutomation.Application/SharedWorkbook/CreateWorkbookPreviewCommand.cs`
- Create: `src/PoAutomation.Application/SharedWorkbook/ApproveWorkbookWriteCommand.cs`
- Create: `src/PoAutomation.Infrastructure/SharedWorkbook/OpenXmlSharedWorkbookGateway.cs`
- Create: `src/PoAutomation.Infrastructure/SharedWorkbook/WorkbookFingerprint.cs`
- Create: `tools/PoAutomation.WorkbookProbe/Program.cs`
- Create: `src/PoAutomation.Web/Components/Pages/SharedWorkbook/Preview.razor`
- Create: `tests/PoAutomation.Domain.Tests/Workflows/WorkbookWriteApprovalTests.cs`
- Create: `tests/PoAutomation.Infrastructure.Tests/SharedWorkbook/SharedWorkbookGatewayTests.cs`
- Add fixtures: `tests/Fixtures/workbooks/monthly-plan.xlsx`

**Interfaces:**
- Consumes: confirmed domestic actual delivery or overseas actual shipment from Tasks 4 and 8.
- Produces: `CreatePreviewAsync(WorkbookWriteRequest, CancellationToken) -> WorkbookWritePreview` with file hash, sheet, row, column, address, old value, proposed value, and projected totals.
- Produces: `ApplyAsync(ApprovedWorkbookWrite, CancellationToken) -> WorkbookWriteReceipt` with backup path, before/after hash, written address, and recalculation result.
- Uses row key `(SalesOwner, CustomerName, ModelName, Currency, UnitPrice)` and date column from actual domestic delivery date or overseas shipment date.

- [ ] **Step 1: Write failing preview and stale-file tests**

Cover exact row selection when customer/model repeats at different prices, missing row/date column, existing value from same job, existing value from another delivery requiring sum, locked file, stale hash after preview, and formula cells retained.

```csharp
[Fact]
public async Task Changed_file_after_preview_requires_new_approval()
{
    var preview = await gateway.CreatePreviewAsync(request, ct);
    await ChangeUnrelatedCellAsync(preview.FilePath);
    await Assert.ThrowsAsync<StaleWorkbookApprovalException>(() =>
        gateway.ApplyAsync(Approve(preview), ct));
}
```

- [ ] **Step 2: Run workbook tests**

Run: `dotnet test PoAutomation.sln --filter "Workbook"`

Expected: FAIL because preview/write behavior is absent.

- [ ] **Step 3: Implement probe, preview, approval, backup, write, and verification**

The probe records monthly filename rule, sheet name, date header format, formula ranges, named ranges, and backup directory. Apply must acquire an exclusive file lock, re-hash the workbook, create a timestamped backup, write one approved cell, set full recalculation on load, run the configured recalculation command, reopen and verify target and summary cells, then persist a receipt. Never create missing rows or columns automatically.

- [ ] **Step 4: Verify fixture and a copy of the real monthly workbook**

Run: `dotnet test PoAutomation.sln --filter "Workbook"`

Expected: PASS on fixtures; real-workbook contract test PASS when `WORKBOOK_TEST_COPY` points to a disposable copy, otherwise SKIP. Original test file hash must remain unchanged.

- [ ] **Step 5: Commit**

```bash
git add src tools tests/Fixtures/workbooks tests
git commit -m "feat: add approved shared workbook updates"
```

---

### Task 10: Exception Workbench, Notifications, Audit Timeline, and Dashboard

**Files:**
- Create: `src/PoAutomation.Domain/Workflows/BusinessException.cs`
- Create: `src/PoAutomation.Application/Exceptions/ListExceptionsQuery.cs`
- Create: `src/PoAutomation.Application/Exceptions/ResolveExceptionCommand.cs`
- Create: `src/PoAutomation.Application/Orders/GetOrderTimelineQuery.cs`
- Create: `src/PoAutomation.Application/Orders/GetDashboardQuery.cs`
- Create: `src/PoAutomation.Infrastructure/Jobs/FailureNotificationHandler.cs`
- Create: `src/PoAutomation.Web/Components/Pages/Exceptions/Index.razor`
- Create: `src/PoAutomation.Web/Components/Pages/Exceptions/Detail.razor`
- Create: `src/PoAutomation.Web/Components/Pages/Dashboard.razor`
- Create: `src/PoAutomation.Web/Components/Pages/Orders/Detail.razor`
- Create: `tests/PoAutomation.Application.Tests/Exceptions/ExceptionResolutionTests.cs`
- Create: `tests/PoAutomation.Web.Tests/DashboardTests.cs`

**Interfaces:**
- Consumes: exceptions, audit records, work items, order and shipment states from all prior tasks.
- Produces: filterable exception queue, resolve/reject/retry action, order timeline, dashboard counts, today/tomorrow schedule, and Outlook failure notifications.
- Produces: `ResolveExceptionCommand(ExceptionId, ResolutionAction, Corrections, Reason)` that resumes only the owning failed step.

- [ ] **Step 1: Write failing exception and dashboard tests**

Cover role visibility, no silent exception deletion, correction before retry, one notification per unresolved occurrence, updated dashboard counts, and recovery after Graph/iCUBE/file-share transient failures without repeating prior successful work.

- [ ] **Step 2: Run exception/UI tests**

Run: `dotnet test PoAutomation.sln --filter "Exception|Dashboard|Timeline"`

Expected: FAIL because the workbench and projections are absent.

- [ ] **Step 3: Implement projections, pages, resolution commands, and throttled notifications**

Use persisted read models updated in the same transaction as workflow state changes. Notification idempotency key is `exception:{exceptionId}:opened`; a reopened exception creates a new occurrence number.

- [ ] **Step 4: Verify application and component behavior**

Run: `dotnet test PoAutomation.sln --filter "Exception|Dashboard|Timeline|Recovery"`

Expected: PASS; resuming an exception never repeats a successful external step.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat: add exception workbench and operations dashboard"
```

---

### Task 11: End-to-End Acceptance, Security Hardening, Deployment, and Runbooks

**Files:**
- Create: `tests/PoAutomation.E2E.Tests/PoAutomation.E2E.Tests.csproj`
- Create: `tests/PoAutomation.E2E.Tests/DomesticHappyPathTests.cs`
- Create: `tests/PoAutomation.E2E.Tests/DomesticSplitDeliveryTests.cs`
- Create: `tests/PoAutomation.E2E.Tests/OverseasVslHappyPathTests.cs`
- Create: `tests/PoAutomation.E2E.Tests/OverseasMismatchTests.cs`
- Create: `tests/PoAutomation.E2E.Tests/WorkbookApprovalTests.cs`
- Create: `src/PoAutomation.Web/appsettings.json`
- Create: `src/PoAutomation.Web/appsettings.Production.json`
- Create: `deploy/windows-service.ps1`
- Create: `deploy/iis-web.config`
- Create: `docs/runbooks/deployment.md`
- Create: `docs/runbooks/backup-restore.md`
- Create: `docs/runbooks/integration-failures.md`
- Create: `docs/runbooks/monthly-workbook-rollover.md`
- Create: `docs/runbooks/user-acceptance.md`

**Interfaces:**
- Consumes: the complete system from Tasks 1~10.
- Produces: repeatable deployment, health endpoints, structured logs, backup/restore, monthly workbook rollover, integration-disable switches, and signed UAT evidence.

- [ ] **Step 1: Write failing Playwright acceptance scenarios**

Implement the spec's five critical flows using faked external adapters: normal domestic, split domestic, normal overseas VSL, overseas quantity/date mismatch, and workbook preview changed before approval. Assert visible statuses, sent-mail records, ERP call order, remaining quantity, and workbook cell address/value.

- [ ] **Step 2: Run the acceptance suite and capture the initial failures**

Run: `dotnet test tests/PoAutomation.E2E.Tests --logger "trx;LogFileName=e2e.trx"`

Expected: FAIL until all pages, adapter fakes, and workflows are wired through the production host.

- [ ] **Step 3: Wire production configuration, health checks, security headers, deployment, and runbooks**

Expose liveness and readiness separately; readiness checks SQL Server and document storage but reports external iCUBE/Graph/file-share health as named degraded dependencies. Configure request size limits, anti-forgery, secure cookies, role policies, log redaction, retention settings, and all external writes disabled by default.

- [ ] **Step 4: Run the complete verification matrix**

Run:

```bash
dotnet format PoAutomation.sln --verify-no-changes
dotnet build PoAutomation.sln -c Release
dotnet test PoAutomation.sln -c Release --collect:"XPlat Code Coverage"
dotnet test tests/PoAutomation.E2E.Tests -c Release
```

Expected: all commands exit 0; no warnings; all unit, integration, component, architecture, and E2E tests PASS. Environment-bound iCUBE, Graph, and real workbook contract suites may SKIP only when their documented test secrets are absent.

- [ ] **Step 5: Execute user acceptance in a non-production environment**

Follow `docs/runbooks/user-acceptance.md` with one real sample per configured customer template and record sign-off for extraction, domestic split delivery, QY/QP matching, exception correction, ERP test registration, and workbook preview/write on a disposable monthly-file copy.

- [ ] **Step 6: Commit**

```bash
git add tests/PoAutomation.E2E.Tests src/PoAutomation.Web deploy docs/runbooks
git commit -m "test: add deployment and end-to-end acceptance coverage"
```

---

## Release Gate

운영 기능 플래그는 다음 순서로 활성화한다.

1. 읽기 전용 PO·주문조회
2. Outlook 시험 메일함 수신
3. iCUBE 읽기
4. 문서 생성과 시험 메일 발송
5. iCUBE 시험환경 쓰기
6. 공유 Excel의 폐기 가능한 복사본 쓰기
7. 사용자 인수승인 후 운영 메일·iCUBE·공유 Excel 쓰기

각 단계는 이전 단계의 계약시험, 감사이력, 중복방지, 장애복구 증거가 있어야 활성화한다. 운영 활성화 후 첫 한 달은 자동 처리율, 예외 유형, 재시도 횟수, 문서 인식 수정률과 Excel 반영 취소율을 매주 검토한다.

## Technical References

- [.NET 10 support policy](https://dotnet.microsoft.com/en-us/platform/support/policy)
- [ASP.NET Core Blazor on .NET 10](https://learn.microsoft.com/aspnet/core/blazor/?view=aspnetcore-10.0)
- [Microsoft Graph Outlook mail API](https://learn.microsoft.com/graph/outlook-mail-concept-overview)
