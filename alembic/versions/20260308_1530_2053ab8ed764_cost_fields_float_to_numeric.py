"""cost fields: Float -> Numeric(20,8) + provider_api_keys composite index

Revision ID: 2053ab8ed764
Revises: 13a4c8f6d9e0
Create Date: 2026-03-08 15:30:00.000000+00:00

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "2053ab8ed764"
down_revision = "13a4c8f6d9e0"
branch_labels = None
depends_on = None


# (table_name, column_name, nullable, server_default)
_COST_COLUMNS: list[tuple[str, str, bool, str | None]] = [
    # api_keys
    ("api_keys", "total_cost_usd", True, "0.0"),
    # usage
    ("usage", "input_cost_usd", True, "0.0"),
    ("usage", "output_cost_usd", True, "0.0"),
    ("usage", "cache_cost_usd", True, "0.0"),
    ("usage", "cache_creation_cost_usd", True, "0.0"),
    ("usage", "cache_read_cost_usd", True, "0.0"),
    ("usage", "request_cost_usd", True, "0.0"),
    ("usage", "total_cost_usd", True, "0.0"),
    ("usage", "actual_input_cost_usd", True, "0.0"),
    ("usage", "actual_output_cost_usd", True, "0.0"),
    ("usage", "actual_cache_creation_cost_usd", True, "0.0"),
    ("usage", "actual_cache_read_cost_usd", True, "0.0"),
    ("usage", "actual_request_cost_usd", True, "0.0"),
    ("usage", "actual_total_cost_usd", True, "0.0"),
    ("usage", "rate_multiplier", True, "1.0"),
    ("usage", "input_price_per_1m", True, None),
    ("usage", "output_price_per_1m", True, None),
    ("usage", "cache_creation_price_per_1m", True, None),
    ("usage", "cache_read_price_per_1m", True, None),
    ("usage", "price_per_request", True, None),
    # providers
    ("providers", "monthly_quota_usd", True, None),
    ("providers", "monthly_used_usd", True, "0.0"),
    # global_models
    ("global_models", "default_price_per_request", True, None),
    # models
    ("models", "price_per_request", True, None),
    # stats_hourly
    ("stats_hourly", "total_cost", False, "0.0"),
    ("stats_hourly", "actual_total_cost", False, "0.0"),
    # stats_hourly_user
    ("stats_hourly_user", "total_cost", False, "0.0"),
    # stats_hourly_model
    ("stats_hourly_model", "total_cost", False, "0.0"),
    # stats_hourly_provider
    ("stats_hourly_provider", "total_cost", False, "0.0"),
    # stats_daily
    ("stats_daily", "total_cost", False, "0.0"),
    ("stats_daily", "actual_total_cost", False, "0.0"),
    ("stats_daily", "input_cost", False, "0.0"),
    ("stats_daily", "output_cost", False, "0.0"),
    ("stats_daily", "cache_creation_cost", False, "0.0"),
    ("stats_daily", "cache_read_cost", False, "0.0"),
    # stats_daily_model
    ("stats_daily_model", "total_cost", False, "0.0"),
    # stats_daily_provider
    ("stats_daily_provider", "total_cost", False, "0.0"),
    # stats_daily_api_key
    ("stats_daily_api_key", "total_cost", False, "0.0"),
    # stats_summary
    ("stats_summary", "all_time_cost", False, "0.0"),
    ("stats_summary", "all_time_actual_cost", False, "0.0"),
    # stats_user_daily
    ("stats_user_daily", "total_cost", False, "0.0"),
]

# rate_multiplier uses a smaller precision
_RATE_MULTIPLIER_TYPE = sa.Numeric(10, 6)
_COST_TYPE = sa.Numeric(20, 8)


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :col"
        ),
        {"table": table_name, "col": column_name},
    )
    return result.scalar() is not None


def _index_exists(index_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
        {"name": index_name},
    )
    return result.scalar() is not None


def _is_numeric_type(table_name: str, column_name: str) -> bool:
    """Check if a column is already numeric type (not float/double precision)."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :col"
        ),
        {"table": table_name, "col": column_name},
    )
    data_type = result.scalar()
    return data_type == "numeric"


def upgrade() -> None:
    # -- 1. cost fields: Float -> Numeric
    for table, col, _nullable, _default in _COST_COLUMNS:
        if not _column_exists(table, col):
            continue
        if _is_numeric_type(table, col):
            continue
        target_type = _RATE_MULTIPLIER_TYPE if col == "rate_multiplier" else _COST_TYPE
        op.alter_column(
            table,
            col,
            type_=target_type,
            existing_type=sa.Float(),
            postgresql_using=f"{col}::numeric",
        )

    # -- 2. provider_api_keys composite index
    if not _index_exists("idx_provider_api_keys_provider_active"):
        op.create_index(
            "idx_provider_api_keys_provider_active",
            "provider_api_keys",
            ["provider_id", "is_active"],
        )


def downgrade() -> None:
    # -- 2. drop composite index
    if _index_exists("idx_provider_api_keys_provider_active"):
        op.drop_index(
            "idx_provider_api_keys_provider_active",
            table_name="provider_api_keys",
        )

    # -- 1. Numeric -> Float
    for table, col, _nullable, _default in _COST_COLUMNS:
        if not _column_exists(table, col):
            continue
        if not _is_numeric_type(table, col):
            continue
        op.alter_column(
            table,
            col,
            type_=sa.Float(),
            existing_type=_COST_TYPE if col != "rate_multiplier" else _RATE_MULTIPLIER_TYPE,
            postgresql_using=f"{col}::double precision",
        )
