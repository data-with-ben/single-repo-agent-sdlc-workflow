from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    display_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    roles = Column(JSON, nullable=False, default=list)  # ["admin", "consultant"]
    created_at = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)  # active|pto|inactive


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)  # active|archived
    created_at = Column(DateTime, nullable=False)


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    consultant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)


class TimeEntry(Base):
    """One consultant's work on one client for one workDate.

    Timestamps are only ever set going forward through the state machine
    (empty -> projected -> logged -> updated); firstSubmittedAt is written once
    and never changes, which is what makes the anti-gaming objective checks
    (SPEC.md Section 5) possible.
    """

    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True)
    consultant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    work_date = Column(DateTime, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    planned_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, nullable=True)
    description = Column(String, nullable=True)
    projected_at = Column(DateTime, nullable=True)
    logged_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    first_submitted_at = Column(DateTime, nullable=True)
    # empty|projected|logged|updated
    state = Column(String, nullable=False, default="empty")


class Season(Base):
    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)  # upcoming|active|complete
    team_size = Column(Integer, nullable=False)  # target, 3..5


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    name = Column(String, nullable=False)

    members = relationship("TeamMembership", back_populates="team")


class TeamMembership(Base):
    """Normalizes Team.memberIds[] into a join table so membership is
    foreign-key-enforced against users, per SPEC.md Section 4/AC #4.
    """

    __tablename__ = "team_memberships"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    team = relationship("Team", back_populates="members")


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    game_date = Column(DateTime, nullable=False)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_score = Column(Float, nullable=True)
    away_score = Column(Float, nullable=True)
    revealed = Column(Boolean, nullable=False, default=False)
    # scheduled|in_progress|final
    state = Column(String, nullable=False, default="scheduled")


class ObjectiveResult(Base):
    """Per-consultant, per-game-date box-score row.

    SPEC.md Section 4 lists gameDate directly on this entity (not a gameId
    FK). game_id is added here as a deliberate normalization so the row is
    foreign-key-enforced against a real Game, per AC #4; game_date is kept
    alongside it since SPEC.md names it explicitly and it's useful for
    date-range queries without a join.
    """

    __tablename__ = "objective_results"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game_date = Column(DateTime, nullable=False)
    consultant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    projected_by_11 = Column(Boolean, nullable=False, default=False)
    logged_same_day = Column(Boolean, nullable=False, default=False)
    eod_update = Column(Boolean, nullable=False, default=False)
    perfect_day = Column(Boolean, nullable=False, default=False)
    points = Column(Integer, nullable=False, default=0)


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    consultant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shares = Column(Integer, nullable=False, default=0)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    consultant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    side = Column(String, nullable=False)  # buy|sell
    shares = Column(Integer, nullable=False)
    price_per_share = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    executed_at = Column(DateTime, nullable=False)


class Dividend(Base):
    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    consultant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    game_date = Column(DateTime, nullable=False)
    reason = Column(String, nullable=False)  # team_win|perfect_day|star_of_game
    shares = Column(Integer, nullable=False)
    per_share = Column(Float, nullable=False)
    total = Column(Float, nullable=False)


class Wallet(Base):
    """SPEC.md Section 4 lists Wallet as (userId, balance) with no separate
    id field, implying userId is the natural primary key -- one wallet per
    user, not a synthetic autoincrement id like every other entity here.
    """

    __tablename__ = "wallets"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    balance = Column(Float, nullable=False, default=0)
