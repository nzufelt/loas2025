### Chasing game

I’d like the code, in PyGame, for a simple game with the following features.

1. The game world is a 500px by 500px square.
2. The player controls a small green circle, roughly 30px in diameter, via the mouse. The player’s “character” always moves toward where the mouse cursor lies, at a pretty quick speed but slowly enough to sense the lag. If the player character hits the edges of the game world, the player loses. 
3. There is a small red square (20px side length) that chases the player’s character, always moving toward them at a speed is a bit slower than the player character, but is fast enough to prove difficult to avoid. If ever this enemy touches the player’s character, the player loses.
4. Periodically, 5 blue rectangular areas appear on the screen in a random location and  configuration. Each is about 50px by 100px. The red enemy square cannot touch the rectangles. If it does, it is teleported to the corner that is closest to the player character. If the player character touches one of the rectangles, it is frozen for 1 second, then reappears slightly away from the box, maybe by just 40 px or so.
5. There is a timer that adds one point for every three seconds that a player survives.
6. If the player loses, the score is displayed temporarily, then the score starts at zero and the game resets.