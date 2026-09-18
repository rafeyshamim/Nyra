import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database.models import Base, Call, Task, OutboxNotification
from app.whatsapp.sender import MockWhatsAppSender, WhatsAppService
from app.whatsapp.commands import WhatsAppCommandProcessor
from app.whatsapp.outbox_worker import OutboxWorker

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def async_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_mock_whatsapp_sender():
    sender = MockWhatsAppSender()
    success = await sender.send_text("+919876543210", "Test notification message")
    assert success is True


@pytest.mark.asyncio
async def test_outbox_worker_processing(async_session: AsyncSession):
    # Enqueue mock outbox item
    item = OutboxNotification(
        call_id="call_outbox_1",
        recipient="+919876543210",
        payload="🤖 NYRA — NEW CALL\nSummary: Test summary",
        status="pending",
    )
    async_session.add(item)
    await async_session.commit()

    worker = OutboxWorker()
    processed_count = await worker.process_pending_outbox(async_session)

    assert processed_count == 1
    await async_session.refresh(item)
    assert item.status == "sent"


@pytest.mark.asyncio
async def test_whatsapp_commands_execution(async_session: AsyncSession):
    processor = WhatsAppCommandProcessor(owner_phone="+919876543210")

    # Add a call needing attention
    call = Call(
        call_id="call_cmd_1",
        phone_number="+919999988888",
        intent="Interview inquiry",
        requires_attention=True,
    )
    async_session.add(call)
    await async_session.commit()

    # Test CALL BACK command
    res1 = await processor.execute_command(async_session, "+919876543210", "CALL BACK")
    assert res1.success is True
    assert res1.action == "callback_created"

    # Test REMIND 10AM command
    res2 = await processor.execute_command(async_session, "+919876543210", "REMIND 10AM")
    assert res2.success is True
    assert res2.action == "reminder_created"

    # Test IGNORE command
    res3 = await processor.execute_command(async_session, "+919876543210", "IGNORE")
    assert res3.success is True
    assert res3.action == "ignored"

    # Test TRANSFER command
    res4 = await processor.execute_command(async_session, "+919876543210", "TRANSFER")
    assert res4.success is True
    assert res4.action == "transfer"
