import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database.models import Base, Contact, Call, Task, OutboxNotification
from app.contacts.service import ContactService
from app.memory.service import MemoryService
from app.conversation.state import CallSession
from app.postcall.analyzer import PostCallProcessor
from app.llm.client import OllamaLLMProvider

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
async def test_contact_and_memory_service(async_session: AsyncSession):
    # Test Contact Creation
    contact = await ContactService.create_contact(
        session=async_session,
        name="Rahul Sharma",
        phone_number="+919876543210",
        organization="XYZ Tech",
        relationship="recruiter",
    )
    assert contact.id is not None
    assert contact.name == "Rahul Sharma"

    # Test Lookup
    fetched = await ContactService.get_contact_by_phone(async_session, "+919876543210")
    assert fetched is not None
    assert fetched.organization == "XYZ Tech"

    # Test Memory Storage
    mem = await MemoryService.set_memory(
        session=async_session,
        key="preferred_contact_time",
        value="10 AM - 12 PM",
    )
    assert mem.value == "10 AM - 12 PM"

    val = await MemoryService.get_memory(async_session, "preferred_contact_time")
    assert val == "10 AM - 12 PM"


@pytest.mark.asyncio
async def test_post_call_processing_pipeline(async_session: AsyncSession):
    llm = OllamaLLMProvider()
    processor = PostCallProcessor(llm_provider=llm)

    # Pre-create Call record in DB as done during /call/incoming
    pre_call = Call(call_id="call_test_99", phone_number="+919876543210", status="ringing")
    async_session.add(pre_call)
    await async_session.commit()

    call_session = CallSession(call_id="call_test_99", phone_number="+919876543210")
    call_session.add_assistant_message("Hi, I'm Nyra, Rafey's AI assistant. How can I help you?")
    call_session.add_user_message("Hi, I am Rahul from XYZ Tech. I am calling to reschedule Rafey's interview to Friday.")
    call_session.add_assistant_message("Understood Rahul. Should I ask Rafey to call you back?")
    call_session.add_user_message("Yes, please ask him to call me back.")

    call_record, analysis = await processor.process_completed_call(async_session, call_session)

    assert call_record.id is not None
    assert call_record.call_id == "call_test_99"
    assert analysis.callback_requested is True
