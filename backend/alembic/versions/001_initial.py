"""初始化数据库表结构

Revision ID: 001_initial
Revises: 
Create Date: 2026-03-31

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users 表
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('username', sa.String(50), nullable=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('real_name', sa.String(50), nullable=True),
        sa.Column('role', sa.Enum('student', 'instructor', 'admin', name='userrole'), nullable=False, server_default='student'),
        sa.Column('avatar', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('current_level', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # modules 表
    op.create_table('modules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('status', sa.Enum('draft', 'published', 'archived', name='coursestatus'), nullable=True, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_modules_id', 'modules', ['id'])

    # chapters 表
    op.create_table('chapters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_locked', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['module_id'], ['modules.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chapters_id', 'chapters', ['id'])

    # lessons 表
    op.create_table('lessons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('animation_url', sa.String(255), nullable=True),
        sa.Column('animation_duration', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_preview', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lessons_id', 'lessons', ['id'])

    # enrollments 表
    op.create_table('enrollments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.Integer(), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, server_default='in_progress'),
        sa.ForeignKeyConstraint(['module_id'], ['modules.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # learning_progress 表
    op.create_table('learning_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('is_completed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('watch_duration', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # questions 表
    op.create_table('questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=True),
        sa.Column('lesson_id', sa.Integer(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('question_type', sa.Enum('single_choice', 'multiple_choice', 'true_false', 'fill_blank', name='questiontype'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('options', sa.Text(), nullable=True),
        sa.Column('correct_answer', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('difficulty', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id']),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_questions_id', 'questions', ['id'])

    # exams 表
    op.create_table('exams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.Integer(), nullable=True),
        sa.Column('chapter_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('exam_type', sa.Enum('chapter_quiz', 'final_exam', 'practice', name='examtype'), nullable=False),
        sa.Column('status', sa.Enum('draft', 'published', 'archived', name='examstatus'), nullable=True, server_default='draft'),
        sa.Column('time_limit', sa.Integer(), nullable=True, server_default='60'),
        sa.Column('pass_score', sa.Integer(), nullable=True, server_default='80'),
        sa.Column('total_questions', sa.Integer(), nullable=True, server_default='20'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id']),
        sa.ForeignKeyConstraint(['module_id'], ['modules.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_exams_id', 'exams', ['id'])

    # exam_records 表
    op.create_table('exam_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_questions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('status', sa.Enum('in_progress', 'passed', 'failed', name='examrecordstatus'), nullable=True, server_default='in_progress'),
        sa.Column('answers', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('time_spent', sa.Integer(), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_exam_records_id', 'exam_records', ['id'])

    # wrong_answers 表
    op.create_table('wrong_answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('user_answer', sa.Text(), nullable=True),
        sa.Column('wrong_count', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('last_wrong_at', sa.DateTime(), nullable=True),
        sa.Column('is_mastered', sa.Boolean(), nullable=True, server_default='false'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_wrong_answers_id', 'wrong_answers', ['id'])


def downgrade() -> None:
    op.drop_table('wrong_answers')
    op.drop_table('exam_records')
    op.drop_table('exams')
    op.drop_table('questions')
    op.drop_table('learning_progress')
    op.drop_table('enrollments')
    op.drop_table('lessons')
    op.drop_table('chapters')
    op.drop_table('modules')
    op.drop_table('users')
