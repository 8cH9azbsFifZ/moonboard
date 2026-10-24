## ADDED Requirements

### Requirement: Free-colour frame
The LED service SHALL accept messages on `moonboard/led/frame` with an object `pixels` mapping positions `A1`…`K18` to `[r, g, b]` (0–255) and SHALL light exactly these positions in these colours, all others off.

#### Scenario: Symbol
- **WHEN** a frame with 40 yellow pixels is published
- **THEN** exactly these 40 positions light yellow

#### Scenario: Empty frame
- **WHEN** a frame with no pixels is published
- **THEN** the wall is dark

### Requirement: Reject invalid frames
The LED service MUST reject a frame with an unknown position or an invalid colour as a whole and SHALL keep the current image.

#### Scenario: Invalid colour
- **WHEN** a frame contains `"A1": [300, 0, 0]`
- **THEN** nothing changes on the wall and one error is logged

### Requirement: Routes still work
A route message on `moonboard/ble/problem` SHALL replace a shown frame as before.

#### Scenario: Route after symbol
- **WHEN** a route is sent while a symbol is shown
- **THEN** the wall shows only the route in route colours
