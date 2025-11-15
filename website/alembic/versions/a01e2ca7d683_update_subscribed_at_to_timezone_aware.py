"""update_subscribed_at_to_timezone_aware

Revision ID: a01e2ca7d683
Revises: bebe9bae6f29
Create Date: 2025-11-15 21:13:07.341266

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a01e2ca7d683"
down_revision: str | None = "bebe9bae6f29"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade database schema to use timezone-aware datetime."""
    # For PostgreSQL, change the column type to TIMESTAMP WITH TIME ZONE
    # This will preserve existing data while making the column timezone-aware
    op.alter_column(
        "newsletter_subscribers",
        "subscribed_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade database schema to use non-timezone-aware datetime."""
    # Revert to TIMESTAMP WITHOUT TIME ZONE
    op.alter_column(
        "newsletter_subscribers",
        "subscribed_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
