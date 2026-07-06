"""Nudge notifications (SPEC.md Section 9/12, task-33).

A nudge lets a user ping an underperforming consultant they hold or
roster. The message is always one fixed, static template string -- never
parameterized with caller-supplied text or any derived per-user status --
which is what enforces SPEC.md Section 12's privacy invariant (no billable
hours or description content may ever surface here) by construction,
rather than by a runtime content filter that a future change could
accidentally bypass.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Holding, Notification, Season, Team, TeamMembership

NUDGE_MESSAGE = (
    "Someone who holds or rosters you sent a friendly reminder to log your time!"
)


def _holds_shares(db: Session, sender_id: int, consultant_id: int) -> bool:
    holding = (
        db.query(Holding)
        .filter(
            Holding.user_id == sender_id,
            Holding.consultant_id == consultant_id,
            Holding.shares > 0,
        )
        .first()
    )
    return holding is not None


def _shares_a_roster(db: Session, sender_id: int, consultant_id: int) -> bool:
    active_season = (
        db.query(Season)
        .filter(Season.status == "active")
        .order_by(Season.start_date.desc())
        .first()
    )
    if active_season is None:
        return False

    season_team_ids = {
        row[0]
        for row in db.query(Team.id)
        .join(TeamMembership, TeamMembership.team_id == Team.id)
        .filter(
            Team.season_id == active_season.id,
            TeamMembership.user_id == sender_id,
        )
        .all()
    }
    if not season_team_ids:
        return False

    consultant_membership = (
        db.query(TeamMembership)
        .filter(
            TeamMembership.user_id == consultant_id,
            TeamMembership.team_id.in_(season_team_ids),
        )
        .first()
    )
    return consultant_membership is not None


def is_nudge_eligible(db: Session, sender_id: int, consultant_id: int) -> bool:
    return _holds_shares(db, sender_id, consultant_id) or _shares_a_roster(
        db, sender_id, consultant_id
    )


def send_nudge(
    db: Session, sender_id: int, consultant_id: int, now: datetime
) -> Notification:
    if not is_nudge_eligible(db, sender_id, consultant_id):
        raise ValueError(
            "not eligible to nudge this consultant -- hold shares in them "
            "or share a roster with them first"
        )

    notification = Notification(
        recipient_id=consultant_id,
        sender_id=sender_id,
        message=NUDGE_MESSAGE,
        created_at=now,
        read=False,
    )
    db.add(notification)
    db.flush()
    return notification


def list_notifications(db: Session, user_id: int) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.recipient_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .all()
    )
