"""新增业务表（告警 / 事件 / 处置响应）

Revision ID: 0002_business_tables
Revises: 0001_initial
Create Date: 2026-09-23
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# 本迁移由 autogenerate 生成，手动调整 revision 标识为 0002_business_tables
revision: str = '0002_business_tables'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### 自动生成开始：创建 SOC 业务表 ###
    # 安全告警表：记录来自各数据源的安全告警
    op.create_table('soc_alerts',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('source', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('severity', sa.String(length=16), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('host', sa.String(length=128), nullable=False),
    sa.Column('incident_id', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_soc_alerts_incident_id'), 'soc_alerts', ['incident_id'], unique=False)
    op.create_index(op.f('ix_soc_alerts_severity'), 'soc_alerts', ['severity'], unique=False)
    op.create_index(op.f('ix_soc_alerts_source'), 'soc_alerts', ['source'], unique=False)
    op.create_index(op.f('ix_soc_alerts_status'), 'soc_alerts', ['status'], unique=False)
    op.create_index(op.f('ix_soc_alerts_title'), 'soc_alerts', ['title'], unique=False)
    # 安全事件表：告警聚合后的事件工单
    op.create_table('soc_incidents',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('severity', sa.String(length=16), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('owner', sa.String(length=128), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_soc_incidents_owner'), 'soc_incidents', ['owner'], unique=False)
    op.create_index(op.f('ix_soc_incidents_severity'), 'soc_incidents', ['severity'], unique=False)
    op.create_index(op.f('ix_soc_incidents_status'), 'soc_incidents', ['status'], unique=False)
    op.create_index(op.f('ix_soc_incidents_title'), 'soc_incidents', ['title'], unique=False)
    # 事件处置响应表：记录每次处置动作
    op.create_table('soc_responses',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('incident_id', sa.String(length=64), nullable=False),
    sa.Column('action', sa.String(length=200), nullable=False),
    sa.Column('operator', sa.String(length=128), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('note', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_soc_responses_incident_id'), 'soc_responses', ['incident_id'], unique=False)
    op.create_index(op.f('ix_soc_responses_status'), 'soc_responses', ['status'], unique=False)
    # ### 自动生成结束 ###


def downgrade() -> None:
    # ### 自动生成开始：回滚业务表 ###
    op.drop_index(op.f('ix_soc_responses_status'), table_name='soc_responses')
    op.drop_index(op.f('ix_soc_responses_incident_id'), table_name='soc_responses')
    op.drop_table('soc_responses')
    op.drop_index(op.f('ix_soc_incidents_title'), table_name='soc_incidents')
    op.drop_index(op.f('ix_soc_incidents_status'), table_name='soc_incidents')
    op.drop_index(op.f('ix_soc_incidents_severity'), table_name='soc_incidents')
    op.drop_index(op.f('ix_soc_incidents_owner'), table_name='soc_incidents')
    op.drop_table('soc_incidents')
    op.drop_index(op.f('ix_soc_alerts_title'), table_name='soc_alerts')
    op.drop_index(op.f('ix_soc_alerts_status'), table_name='soc_alerts')
    op.drop_index(op.f('ix_soc_alerts_source'), table_name='soc_alerts')
    op.drop_index(op.f('ix_soc_alerts_severity'), table_name='soc_alerts')
    op.drop_index(op.f('ix_soc_alerts_incident_id'), table_name='soc_alerts')
    op.drop_table('soc_alerts')
    # ### 自动生成结束 ###
