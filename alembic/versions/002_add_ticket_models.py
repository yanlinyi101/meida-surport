"""Add ticket models

Revision ID: 002_add_ticket_models
Revises: 001_rbac_v2_add_category_and_system_roles
Create Date: 2025-09-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Use String for UUID in SQLite, UUID in PostgreSQL
def get_uuid_type():
    """Get appropriate UUID type based on database backend."""
    try:
        # Try to get current connection to determine database type
        conn = op.get_bind()
        if conn.dialect.name == 'sqlite':
            return sa.String(36)  # UUID as string for SQLite
        else:
            return postgresql.UUID(as_uuid=True)  # Native UUID for PostgreSQL
    except:
        # Default to String for compatibility
        return sa.String(36)

# revision identifiers, used by Alembic.
revision = '002_add_ticket_models'
down_revision = '001_rbac_v2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Skip enum creation for SQLite, use string constraints instead
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        # Create ticket status enum
        ticket_status_enum = postgresql.ENUM(
            'BOOKED', 'CONFIRMED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELED',
            name='ticketstatus'
        )
        ticket_status_enum.create(op.get_bind())
        
        # Create ticket action enum
        ticket_action_enum = postgresql.ENUM(
            'CONFIRM', 'ASSIGN', 'UPLOAD_RECEIPT', 'COMPLETE', 'CANCEL', 'STATUS_CHANGE',
            name='ticket_action'
        )
        ticket_action_enum.create(op.get_bind())
        
        # Create image type enum
        image_type_enum = postgresql.ENUM(
            'RECEIPT', 'BEFORE', 'AFTER', 'PARTS',
            name='imagetype'
        )
        image_type_enum.create(op.get_bind())
    
    # Create technicians table
    uuid_type = get_uuid_type()
    op.create_table(
        'technicians',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('phone_masked', sa.String(20), nullable=False),
        sa.Column('center_id', uuid_type, nullable=True),
        sa.Column('skills', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create tickets table
    op.create_table(
        'tickets',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('customer_name', sa.String(100), nullable=False),
        sa.Column('customer_phone_hash', sa.String(64), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('appointment_date', sa.Date(), nullable=False),
        sa.Column('appointment_time', sa.Time(), nullable=False),
        sa.Column('issue_desc', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='BOOKED'),  # Use String for SQLite
        sa.Column('center_id', uuid_type, nullable=True),
        sa.Column('technician_id', uuid_type, nullable=True),
        sa.Column('ai_run_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['technician_id'], ['technicians.id']),
    )
    
    # Create ticket_images table
    op.create_table(
        'ticket_images',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('ticket_id', uuid_type, nullable=False),
        sa.Column('type', sa.String(20), nullable=False, default='RECEIPT'),  # Use String for SQLite
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('checksum_sha256', sa.String(64), nullable=False),
        sa.Column('uploaded_by_user_id', uuid_type, nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id']),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id']),
    )
    
    # Create ticket_events table
    op.create_table(
        'ticket_events',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('ticket_id', uuid_type, nullable=False),
        sa.Column('actor_user_id', uuid_type, nullable=True),
        sa.Column('action', sa.String(20), nullable=False),  # Use String for SQLite
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id']),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id']),
    )
    
    # Create indexes
    op.create_index('idx_technician_center_id', 'technicians', ['center_id'])
    op.create_index('idx_technician_is_active', 'technicians', ['is_active'])
    
    op.create_index('idx_ticket_status', 'tickets', ['status'])
    op.create_index('idx_ticket_appointment_date', 'tickets', ['appointment_date'])
    op.create_index('idx_ticket_technician_id', 'tickets', ['technician_id'])
    op.create_index('idx_ticket_created_at', 'tickets', ['created_at'])
    
    op.create_index('idx_ticket_image_ticket_id', 'ticket_images', ['ticket_id'])
    op.create_index('idx_ticket_image_type', 'ticket_images', ['type'])
    op.create_index('idx_ticket_image_uploaded_at', 'ticket_images', ['uploaded_at'])
    
    op.create_index('idx_ticket_event_ticket_id', 'ticket_events', ['ticket_id'])
    op.create_index('idx_ticket_event_created_at', 'ticket_events', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()
    # Drop indexes
    op.drop_index('idx_ticket_event_created_at', table_name='ticket_events')
    op.drop_index('idx_ticket_event_ticket_id', table_name='ticket_events')
    
    op.drop_index('idx_ticket_image_uploaded_at', table_name='ticket_images')
    op.drop_index('idx_ticket_image_type', table_name='ticket_images')
    op.drop_index('idx_ticket_image_ticket_id', table_name='ticket_images')
    
    op.drop_index('idx_ticket_created_at', table_name='tickets')
    op.drop_index('idx_ticket_technician_id', table_name='tickets')
    op.drop_index('idx_ticket_appointment_date', table_name='tickets')
    op.drop_index('idx_ticket_status', table_name='tickets')
    
    op.drop_index('idx_technician_is_active', table_name='technicians')
    op.drop_index('idx_technician_center_id', table_name='technicians')
    
    # Drop tables
    op.drop_table('ticket_events')
    op.drop_table('ticket_images')
    op.drop_table('tickets')
    op.drop_table('technicians')
    
    # Drop enums (PostgreSQL only)
    if conn.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS imagetype')
        op.execute('DROP TYPE IF EXISTS ticket_action')
        op.execute('DROP TYPE IF EXISTS ticketstatus') 