# Entity-Relationship Diagram

Reflects the SQLAlchemy models in `app/models.py`, which implement the domain
data model in `backlog/docs/doc-1 - Fantasy-Timesheets-—-Product-Technical-Spec.md`
Section 4. Update this diagram whenever a model's fields or relationships
change.

```mermaid
erDiagram
    USER ||--o{ ASSIGNMENT : "consultant_id"
    CLIENT ||--o{ ASSIGNMENT : "client_id"
    USER ||--o{ TIME_ENTRY : "consultant_id"
    CLIENT ||--o{ TIME_ENTRY : "client_id"
    SEASON ||--o{ TEAM : "season_id"
    TEAM ||--o{ TEAM_MEMBERSHIP : "team_id"
    USER ||--o{ TEAM_MEMBERSHIP : "user_id"
    SEASON ||--o{ GAME : "season_id"
    TEAM ||--o{ GAME : "home_team_id"
    TEAM ||--o{ GAME : "away_team_id"
    GAME ||--o{ OBJECTIVE_RESULT : "game_id"
    USER ||--o{ OBJECTIVE_RESULT : "consultant_id"
    TEAM ||--o{ OBJECTIVE_RESULT : "team_id"
    USER ||--o{ HOLDING : "user_id / consultant_id"
    USER ||--o{ TRANSACTION : "user_id / consultant_id"
    USER ||--o{ DIVIDEND : "user_id / consultant_id"
    USER ||--|| WALLET : "user_id"

    USER {
        int id PK
        string display_name
        string email
        json roles
        datetime created_at
        string status
    }
    CLIENT {
        int id PK
        string name
        string status
        datetime created_at
    }
    ASSIGNMENT {
        int id PK
        int consultant_id FK
        int client_id FK
        datetime start_date
        datetime end_date
    }
    TIME_ENTRY {
        int id PK
        int consultant_id FK
        datetime work_date
        int client_id FK
        float planned_hours
        float actual_hours
        string description
        datetime projected_at
        datetime logged_at
        datetime updated_at
        datetime first_submitted_at
        string state
    }
    SEASON {
        int id PK
        string name
        datetime start_date
        datetime end_date
        string status
        int team_size
    }
    TEAM {
        int id PK
        int season_id FK
        string name
    }
    TEAM_MEMBERSHIP {
        int id PK
        int team_id FK
        int user_id FK
    }
    GAME {
        int id PK
        datetime game_date
        int season_id FK
        int home_team_id FK
        int away_team_id FK
        float home_score
        float away_score
        bool revealed
        string state
    }
    OBJECTIVE_RESULT {
        int id PK
        int game_id FK
        datetime game_date
        int consultant_id FK
        int team_id FK
        bool projected_by_11
        bool logged_same_day
        bool eod_update
        bool perfect_day
        int points
    }
    HOLDING {
        int id PK
        int user_id FK
        int consultant_id FK
        int shares
    }
    TRANSACTION {
        int id PK
        int user_id FK
        int consultant_id FK
        string side
        int shares
        float price_per_share
        float total
        datetime executed_at
    }
    DIVIDEND {
        int id PK
        int user_id FK
        int consultant_id FK
        datetime game_date
        string reason
        int shares
        float per_share
        float total
    }
    WALLET {
        int user_id PK, FK
        float balance
    }
```

## Deliberate deviations from the spec's literal field list

- **TeamMembership** is a new join table, not in the spec's entity list. `Team.memberIds[]` is normalized into it so membership is foreign-key-enforced against `users`, per AC #4.
- **ObjectiveResult.game_id** is a new FK column, not in the spec's field list for this entity (which only lists `gameDate`). Added so the row is foreign-key-enforced against a real `Game`; `game_date` is kept alongside it since the spec names it explicitly and it avoids a join for date-range queries.
- **Wallet** uses `user_id` as its primary key (no separate `id` column), matching the spec's field list of `(userId, balance)` — the only entity without a synthetic autoincrement id.
