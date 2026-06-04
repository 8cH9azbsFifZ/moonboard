# problem-database Specification

## Purpose
TBD - created by archiving change document-system-architecture. Update Purpose after archive.
## Requirements
### Requirement: Problem fetching from Moonboard API
The system SHALL fetch boulder problems from the Moonboard.com API (`/Problems/GetProblems`) in paginated batches, supporting multiple hold setups.

#### Scenario: Paginated fetch of all problems for a setup
- **WHEN** fetching problems for setup "master2017" (setupId=15)
- **THEN** the system SHALL request pages of 500 problems until all problems are retrieved or the max_fetch limit (30000) is reached

#### Scenario: Export to JSON
- **WHEN** all pages have been fetched
- **THEN** the system SHALL concatenate results and export to `moonboard_problems_setup_<setup>.json`

### Requirement: SQLite database schema for problems
The system SHALL store problems in a SQLite database with tables for holds, problems, problem moves, and setters.

#### Scenario: Database initialization
- **WHEN** `setup_problem_db` is called
- **THEN** the system SHALL create tables: `holds(Position, Setup, HoldSet, Hold, Orientation)`, `problems(Id, Name, Grade, IsBenchmark, IsAssessmentProblem, Method, Firstname, Lastname)`, `problemMoves(Problem, Position, Setup, IsStart, IsEnd)`, `setter(Firstname, Lastname)`

#### Scenario: Hold setup import
- **WHEN** `setup_holds` is called with `HoldSetup.json`
- **THEN** all holds for all setups SHALL be inserted into the `holds` table

#### Scenario: Problem insertion with moves
- **WHEN** a problem is inserted
- **THEN** the problem record, setter record, and all associated move records SHALL be committed atomically (rollback on failure)

### Requirement: Async problem query interface
The system SHALL provide async query functions for retrieving problems and holds from the database.

#### Scenario: Get holds for a problem
- **WHEN** `get_problem_holds(conn, Id)` is called
- **THEN** the system SHALL return a dict `{"START": [...], "TOP": [...], "MOVES": [...]}` with hold positions classified by IsStart/IsEnd flags

#### Scenario: User query with filters
- **WHEN** `user_query_get_problems` is called with grade filter, name pattern, and setter pattern
- **THEN** the system SHALL return matching problems up to the limit (default 2001), with result truncation indicator

#### Scenario: Hold positions for a setup and hold set
- **WHEN** `get_setup_hold_positions(conn, setup, holdSet)` is called
- **THEN** the system SHALL return a sorted list of all hold positions matching that setup and hold set

### Requirement: Problem visualization
The system SHALL render problems as PNG images with colored rectangles around hold positions on a background image of the wall.

#### Scenario: Draw problem on wall image
- **WHEN** `draw_Problem` is called with setup, holdset, and holds dict
- **THEN** the system SHALL load the appropriate background image, draw colored rectangles around each hold position, and return the annotated image

#### Scenario: Grid coordinate to pixel mapping
- **WHEN** converting hold coordinates to image pixels
- **THEN** columns A–K SHALL map to x-coordinates from XMIN=61 to XMAX=389, rows 1–18 SHALL map to y-coordinates from YMAX=612 (bottom) to YMIN=56 (top)

