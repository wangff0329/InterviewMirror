from app.config import Settings
from app.schemas import MemoryItem
from app.services.memory import (
    create_memory,
    delete_memory,
    init_memory_database,
    list_memories,
    update_memory,
)
from app.services.research import search_interview_experiences


def test_memory_is_persisted_and_scoped_to_user(tmp_path) -> None:
    settings = Settings(database_path=str(tmp_path / "memory.db"))
    init_memory_database(settings)

    created = create_memory(
        settings,
        1,
        MemoryItem(memory_type="weakness", content="需要加强缓存一致性"),
    )

    assert created.id is not None
    assert list_memories(settings, 1)[0].content == "需要加强缓存一致性"
    assert list_memories(settings, 2) == []
    duplicate = create_memory(
        settings,
        1,
        MemoryItem(memory_type="weakness", content="需要加强缓存一致性", confidence=0.95),
    )
    assert duplicate.id == created.id
    assert len(list_memories(settings, 1)) == 1
    updated = update_memory(
        settings,
        1,
        created.id,
        MemoryItem(memory_type="plan", content="完成缓存设计题", confidence=0.9),
    )
    assert updated is not None
    assert list_memories(settings, 1)[0].memory_type == "plan"
    assert delete_memory(settings, 2, created.id) is False
    assert delete_memory(settings, 1, created.id) is True
    assert list_memories(settings, 1) == []


def test_research_requires_api_key(tmp_path) -> None:
    settings = Settings(database_path=str(tmp_path / "research.db"))
    try:
        search_interview_experiences(settings, "某公司", "后端开发")
    except ValueError as error:
        assert "API Key" in str(error)
    else:
        raise AssertionError("搜索服务未配置 API Key 时应明确报错")
