# Design

- Same MQTT broker and connection as routes; QoS 0 for frames (an animation must not queue up).
- A frame always replaces the whole wall (all off, then set), one `push_to_driver` per frame.
- Invalid frames are rejected as a whole and logged once; the wall keeps the previous image.
- Success on the device: a symbol sent from the Mac appears on the wall in its colours.
