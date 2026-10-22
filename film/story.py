TITLE = 'Am I enough?'
DURATION = 90.0
FPS = 24
POSE_FPS = 12

# Each shot has a purpose, a camera setup, and a sound cue. Seconds are absolute.
SHOTS = [
    (0, 4, 'opening', 'A question in the glass', 'room tone; solitary felt-piano notes'),
    (4, 9, 'reach', 'Almost tall enough', 'cloth movement; a delicate rising tone'),
    (9, 13, 'feed', 'Someone else is ahead', 'phone vibration and notification'),
    (13, 18, 'raise', 'The reflection changes the rules', 'glass shimmer; low bowed tone'),
    (18, 23, 'work', 'One more night', 'keyboard; pencil; ticking'),
    (23, 27, 'run', 'Before the city wakes', 'footsteps; breath; restrained pulse'),
    (27, 31, 'award', 'A small victory', 'medal chime, followed by the moving line'),
    (31, 36, 'late', 'Working past exhaustion', 'typing becomes uneven; clock'),
    (36, 41, 'measure', 'Still not enough', 'ruler extends; dissonant swell'),
    (41, 46, 'build', 'A tower of proof', 'books and boxes placed in sequence'),
    (46, 51, 'climb', 'Nearly there', 'effortful steps; creaking stack'),
    (51, 55, 'touch', 'The goal moves again', 'bright contact; upward pitch bend'),
    (55, 59, 'fall', 'Everything gives way', 'wood and paper impacts; score drops'),
    (59, 64, 'floor', 'The quiet afterward', 'air and settling paper; sparse music'),
    (64, 69, 'message', 'An invitation, not a measurement', 'soft notification; phone taps'),
    (69, 73, 'leave', 'Choose to go', 'footsteps; latch; room tone opens'),
    (73, 78, 'cafe', 'A place is made', 'cup on bench; gentle city ambience'),
    (78, 83, 'reflection', 'The old thought returns', 'muted glass/ruler motif'),
    (83, 87, 'connection', 'Attention turns outward', 'warm piano resolution; steam and air'),
    (87, 90, 'ending', 'The line is left behind', 'last chord and natural decay'),
]

def shot_at(t):
    for start, end, name, purpose, cue in SHOTS:
        if t < end:
            return start, end, name, purpose, cue
    return SHOTS[-1]
