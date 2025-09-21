"""rbac_v2_add_category_and_system_roles

Revision ID: 001_rbac_v2
Revises: 
Create Date: 2024-09-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_rbac_v2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add category column to permissions table
    op.add_column('permissions', sa.Column('category', sa.String(length=50), nullable=False, server_default='general'))
    op.add_column('permissions', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # Add is_system column to roles table
    op.add_column('roles', sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create indexes for better performance
    op.create_index(op.f('ix_permissions_category'), 'permissions', ['category'], unique=False)
    op.create_index(op.f('ix_roles_is_system'), 'roles', ['is_system'], unique=False)


def downgrade() -> None:
    # Remove indexes
    op.drop_index(op.f('ix_roles_is_system'), table_name='roles')
    op.drop_index(op.f('ix_permissions_category'), table_name='permissions')
    
    # Remove columns
    op.drop_column('roles', 'is_system')
    op.drop_column('permissions', 'updated_at')
    op.drop_column('permissions', 'category') 