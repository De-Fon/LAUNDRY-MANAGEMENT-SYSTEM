from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.apps.analytics import models as analytics_models  # noqa: F401
from app.apps.auth import models as auth_models  # noqa: F401
from app.apps.bookings import models as bookings_models  # noqa: F401
from app.apps.catalog import models as catalog_models  # noqa: F401
from app.apps.credit_tab import models as credit_tab_models  # noqa: F401
from app.apps.health import models as health_models  # noqa: F401
from app.apps.idempotency import models as idempotency_models  # noqa: F401
from app.apps.ledger import models as ledger_models  # noqa: F401
from app.apps.notifications import models as notifications_models  # noqa: F401
from app.apps.order_management import models as order_management_models  # noqa: F401
from app.apps.payments import models as payments_models  # noqa: F401
from app.apps.pricing import models as pricing_models  # noqa: F401
from app.apps.users import models as users_models  # noqa: F401
from app.apps.vendor_dashboard import models as vendor_dashboard_models  # noqa: F401
from app.apps.waitlist import models as waitlist_models  # noqa: F401
from app.core.database import Base
from app.core.settings import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
