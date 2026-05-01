import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.modules.auth.infrastructure.orm.models import UserModel
from app.modules.lostfound.application.commands.create_item import (
    CreateItemCommand,
    CreateItemHandler,
)
from app.modules.lostfound.domain.value_objects.report_type import ReportType
from app.modules.lostfound.infrastructure.repositories.audit_repo_sql import (
    AuditLogRepositorySQL,
)
from app.modules.lostfound.infrastructure.repositories.item_repo_sql import (
    ItemRepositorySQL,
)
from app.shared.infrastructure.db import AsyncSessionLocal


async def seed_demo_data():
    async with AsyncSessionLocal() as session:
        owner = await session.scalar(
            select(UserModel).where(UserModel.email == "owner@example.com").limit(1)
        )
        finder = await session.scalar(
            select(UserModel).where(UserModel.email == "finder@example.com").limit(1)
        )

        if owner is None or finder is None:
            raise RuntimeError(
                "Default owner/finder users are missing. Run scripts/seed_users.py first."
            )

        handler = CreateItemHandler(
            item_repo=ItemRepositorySQL(session),
            audit_repo=AuditLogRepositorySQL(session),
        )

        samples = (
            CreateItemCommand(
                report_type=ReportType.LOST,
                title="Lost Blue Water Bottle",
                description_public="Blue bottle left near lecture hall",
                description_private="Has a scratched lid and a faded robotics club sticker.",
                category="Bottle",
                location_text="Building A",
                brand="Hydro Flask",
                color="Blue",
                happened_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=2),
                posted_by_user_id=owner.id,
                contact_preference="EMAIL",
                verification_questions=[
                    "What brand is printed on the bottle?",
                    "Is there a sticker on it?",
                ],
                image_urls=["https://images.example.com/items/water-bottle.jpg"],
            ),
            CreateItemCommand(
                report_type=ReportType.FOUND,
                title="Found Student Card Holder",
                description_public="Black holder found near cafeteria",
                description_private="Contains a folded receipt and a worn campus shuttle card.",
                category="Card Holder",
                location_text="Campus Cafeteria",
                brand="Nike",
                color="Black",
                happened_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
                posted_by_user_id=finder.id,
                contact_preference="PHONE",
                verification_questions=[
                    "What color is the card lanyard?",
                    "What initials are on the holder?",
                ],
                image_urls=["https://images.example.com/items/card-holder.jpg"],
            ),
        )

        for command in samples:
            await handler.handle(command)

        await session.commit()
        print("Seeded demo lost/found items.")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
