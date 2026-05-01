from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, select, text

from app.shared.infrastructure.db import AsyncSessionLocal, Base, engine

from app.modules.auth.infrastructure.orm import models as auth_models  # noqa: F401
from app.modules.auth.infrastructure.orm.models import UserModel
from app.modules.auth.infrastructure.security.password import hash_password
from app.modules.auth.presentation.routes import admin_router as admin_routes_router
from app.modules.auth.presentation.routes import router as auth_routes_router
from app.modules.lostfound.application.commands.create_item import CreateItemCommand, CreateItemHandler
from app.modules.lostfound.infrastructure.orm import models as lostfound_models  # noqa: F401
from app.modules.lostfound.infrastructure.orm.models import ItemModel
from app.modules.lostfound.domain.value_objects.report_type import ReportType
from app.modules.lostfound.infrastructure.repositories.audit_repo_sql import AuditLogRepositorySQL
from app.modules.lostfound.infrastructure.repositories.item_repo_sql import ItemRepositorySQL
from app.modules.lostfound.presentation.routes.claims import router as claims_router
from app.modules.lostfound.presentation.routes.items import router as items_router
from app.shared.infrastructure.settings import settings

LOSTFOUND_TABLES = (
    "claim_answers",
    "claims",
    "verification_questions",
    "audit_logs",
    "items",
    "item_images",
    "item_timeline_events",
    "notifications",
    "user_profiles",
)

EXPECTED_LOSTFOUND_COLUMNS = {
    "items": {
        "id",
        "report_type",
        "title",
        "description_public",
        "category",
        "location_text",
        "happened_at",
        "posted_by_user_id",
        "status",
        "active_claim_id",
        "created_at",
    },
    "verification_questions": {"id", "question", "item_id"},
    "claims": {"id", "item_id", "claimant_user_id", "status", "submitted_at"},
    "claim_answers": {"id", "answer", "claim_id"},
    "audit_logs": {"id", "actor_user_id", "action", "target_type", "target_id", "created_at"},
}


def _has_legacy_lostfound_schema(sync_conn) -> bool:
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())

    for table_name, required_columns in EXPECTED_LOSTFOUND_COLUMNS.items():
        if table_name not in existing_tables:
            continue

        existing_columns = {
            column["name"]
            for column in inspector.get_columns(table_name)
        }

        if not required_columns.issubset(existing_columns):
            return True

    return False


def _archive_legacy_lostfound_tables(sync_conn) -> None:
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())

    if not _has_legacy_lostfound_schema(sync_conn):
        return

    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")

    for table_name in LOSTFOUND_TABLES:
        if table_name in existing_tables:
            sync_conn.execute(
                text(
                    f'ALTER TABLE "{table_name}" RENAME TO "{table_name}_legacy_{suffix}"'
                )
            )


def _repair_users_schema(sync_conn) -> None:
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())

    if "users" not in existing_tables:
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    if "is_active" not in existing_columns:
        sync_conn.execute(
            text(
                'ALTER TABLE "users" ADD COLUMN "is_active" BOOLEAN NOT NULL DEFAULT TRUE'
            )
        )

    if "created_at" not in existing_columns:
        sync_conn.execute(
            text(
                'ALTER TABLE "users" ADD COLUMN "created_at" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP'
            )
        )

    sync_conn.execute(
        text(
            "UPDATE users SET role = 'MEMBER' WHERE role IN ('OWNER', 'FINDER')"
        )
    )


def _repair_expanded_schema(sync_conn) -> None:
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())

    if "items" in existing_tables:
        item_columns = {column["name"] for column in inspector.get_columns("items")}

        if "description_private" not in item_columns:
            sync_conn.execute(text('ALTER TABLE "items" ADD COLUMN "description_private" TEXT'))
        if "brand" not in item_columns:
            sync_conn.execute(text('ALTER TABLE "items" ADD COLUMN "brand" VARCHAR(120)'))
        if "color" not in item_columns:
            sync_conn.execute(text('ALTER TABLE "items" ADD COLUMN "color" VARCHAR(80)'))
        if "contact_preference" not in item_columns:
            sync_conn.execute(text('ALTER TABLE "items" ADD COLUMN "contact_preference" VARCHAR(50)'))
        if "resolved_at" not in item_columns:
            sync_conn.execute(text('ALTER TABLE "items" ADD COLUMN "resolved_at" TIMESTAMP WITHOUT TIME ZONE'))

    if "claims" in existing_tables:
        claim_columns = {column["name"] for column in inspector.get_columns("claims")}

        if "proof_statement" not in claim_columns:
            sync_conn.execute(text('ALTER TABLE "claims" ADD COLUMN "proof_statement" TEXT'))
        if "decision_reason" not in claim_columns:
            sync_conn.execute(text('ALTER TABLE "claims" ADD COLUMN "decision_reason" TEXT'))
        if "decided_at" not in claim_columns:
            sync_conn.execute(text('ALTER TABLE "claims" ADD COLUMN "decided_at" TIMESTAMP WITHOUT TIME ZONE'))
        if "handover_note" not in claim_columns:
            sync_conn.execute(text('ALTER TABLE "claims" ADD COLUMN "handover_note" TEXT'))
        if "handover_arranged_at" not in claim_columns:
            sync_conn.execute(text('ALTER TABLE "claims" ADD COLUMN "handover_arranged_at" TIMESTAMP WITHOUT TIME ZONE'))
        if "handed_over_at" not in claim_columns:
            sync_conn.execute(text('ALTER TABLE "claims" ADD COLUMN "handed_over_at" TIMESTAMP WITHOUT TIME ZONE'))

    if "user_profiles" not in existing_tables:
        sync_conn.execute(
            text(
                'CREATE TABLE "user_profiles" ('
                '"user_id" INTEGER NOT NULL PRIMARY KEY REFERENCES "users" ("id") ON DELETE CASCADE,'
                '"full_name" VARCHAR(255),'
                '"phone" VARCHAR(50),'
                '"department" VARCHAR(120),'
                '"preferred_contact_method" VARCHAR(50),'
                '"created_at" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,'
                '"updated_at" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP'
                ')'
            )
        )

    if "item_images" not in existing_tables:
        sync_conn.execute(
            text(
                'CREATE TABLE "item_images" ('
                '"id" SERIAL NOT NULL PRIMARY KEY,'
                '"item_id" VARCHAR(36) NOT NULL REFERENCES "items" ("id") ON DELETE CASCADE,'
                '"image_url" VARCHAR(500) NOT NULL,'
                '"is_primary" BOOLEAN NOT NULL DEFAULT FALSE,'
                '"sort_order" INTEGER NOT NULL DEFAULT 0,'
                '"uploaded_at" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP'
                ')'
            )
        )
        sync_conn.execute(text('CREATE INDEX "ix_item_images_item_id" ON "item_images" ("item_id")'))

    if "item_timeline_events" not in existing_tables:
        sync_conn.execute(
            text(
                'CREATE TABLE "item_timeline_events" ('
                '"id" SERIAL NOT NULL PRIMARY KEY,'
                '"item_id" VARCHAR(36) NOT NULL REFERENCES "items" ("id") ON DELETE CASCADE,'
                '"event_type" VARCHAR(80) NOT NULL,'
                '"description" TEXT NOT NULL,'
                '"actor_user_id" INTEGER,'
                '"created_at" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP'
                ')'
            )
        )
        sync_conn.execute(text('CREATE INDEX "ix_item_timeline_events_item_id" ON "item_timeline_events" ("item_id")'))

    if "notifications" not in existing_tables:
        sync_conn.execute(
            text(
                'CREATE TABLE "notifications" ('
                '"id" SERIAL NOT NULL PRIMARY KEY,'
                '"user_id" INTEGER NOT NULL,'
                '"type" VARCHAR(80) NOT NULL,'
                '"title" VARCHAR(255) NOT NULL,'
                '"body" TEXT NOT NULL,'
                '"is_read" BOOLEAN NOT NULL DEFAULT FALSE,'
                '"related_item_id" VARCHAR(36),'
                '"related_claim_id" VARCHAR(36),'
                '"created_at" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP'
                ')'
            )
        )
        sync_conn.execute(text('CREATE INDEX "ix_notifications_user_id" ON "notifications" ("user_id")'))


async def _seed_default_users() -> None:
    if not settings.seed_default_users_on_startup:
        return

    default_users = (
        (settings.seed_admin_email, settings.seed_admin_password, "ADMIN"),
        (settings.seed_owner_email, settings.seed_owner_password, "MEMBER"),
        (settings.seed_finder_email, settings.seed_finder_password, "MEMBER"),
    )

    async with AsyncSessionLocal() as session:
        for email, password, role in default_users:
            normalized_email = email.strip().lower()
            if not normalized_email or not password:
                continue

            existing_user = await session.scalar(
                select(UserModel).where(UserModel.email == normalized_email).limit(1)
            )

            if existing_user is None:
                session.add(
                    UserModel(
                        email=normalized_email,
                        password_hash=hash_password(password),
                        role=role,
                        is_active=True,
                    )
                )
            else:
                existing_user.password_hash = hash_password(password)
                existing_user.role = role
                existing_user.is_active = True

        await session.commit()


async def _seed_demo_items() -> None:
    if not settings.seed_demo_items_on_startup:
        return

    async with AsyncSessionLocal() as session:
        owner = await session.scalar(
            select(UserModel).where(UserModel.email == settings.seed_owner_email.strip().lower()).limit(1)
        )
        finder = await session.scalar(
            select(UserModel).where(UserModel.email == settings.seed_finder_email.strip().lower()).limit(1)
        )

        if owner is None or finder is None:
            return

        handler = CreateItemHandler(
            item_repo=ItemRepositorySQL(session),
            audit_repo=AuditLogRepositorySQL(session),
        )
        now = datetime.now(UTC).replace(tzinfo=None)
        samples = (
            CreateItemCommand(
                report_type=ReportType.LOST,
                title="Lost Blue Water Bottle",
                description_public="Blue bottle left near the lecture hall after morning class.",
                description_private="Has a scratched lid and a faded robotics club sticker.",
                category="Bottle",
                location_text="Building A Lecture Hall",
                brand="Hydro Flask",
                color="Blue",
                happened_at=now - timedelta(days=2),
                posted_by_user_id=owner.id,
                contact_preference="EMAIL",
                verification_questions=[
                    "What brand is printed on the bottle?",
                    "What sticker is on it?",
                ],
                image_urls=["https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=900&q=80"],
            ),
            CreateItemCommand(
                report_type=ReportType.FOUND,
                title="Found Black Card Holder",
                description_public="Black card holder found on a cafeteria table.",
                description_private="Contains a folded receipt and a worn campus shuttle card.",
                category="Documents",
                location_text="Campus Cafeteria",
                brand="Nike",
                color="Black",
                happened_at=now - timedelta(days=1),
                posted_by_user_id=finder.id,
                contact_preference="PHONE",
                verification_questions=[
                    "What color is the card lanyard?",
                    "What initials are on the holder?",
                ],
                image_urls=["https://images.unsplash.com/photo-1627123424574-724758594e93?auto=format&fit=crop&w=900&q=80"],
            ),
            CreateItemCommand(
                report_type=ReportType.LOST,
                title="Lost Wireless Earbuds Case",
                description_public="White earbuds case misplaced near the library entrance.",
                description_private="Small ink mark on the underside and one missing silicone tip inside.",
                category="Electronics",
                location_text="Main Library Entrance",
                brand="Apple",
                color="White",
                happened_at=now - timedelta(days=4),
                posted_by_user_id=owner.id,
                contact_preference="EMAIL",
                verification_questions=[
                    "What mark is on the case?",
                    "What accessory is missing?",
                ],
                image_urls=["https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?auto=format&fit=crop&w=900&q=80"],
            ),
        )

        for command in samples:
            existing_item = await session.scalar(
                select(ItemModel).where(ItemModel.title == command.title).limit(1)
            )
            if existing_item is None:
                await handler.handle(command)

        await session.commit()


async def startup():
    async with engine.begin() as conn:
        if settings.repair_schema_on_startup:
            await conn.run_sync(_archive_legacy_lostfound_tables)
            await conn.run_sync(_repair_users_schema)
            await conn.run_sync(_repair_expanded_schema)

        if settings.auto_create_schema_on_startup:
            await conn.run_sync(Base.metadata.create_all)

    await _seed_default_users()
    await _seed_demo_items()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes_router)
app.include_router(admin_routes_router)
app.include_router(items_router)
app.include_router(claims_router)
