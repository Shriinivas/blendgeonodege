# BlendGeoNodGe

## The Engine (`geonodege.py`)
The `geonodege.py` script serves as a lightweight, generic input controller and engine manager for Blender Geometry Nodes-based games. It can be executed directly from Blender's Text Editor or installed persistently as a standard add-on. Once active, it captures real-time keyboard and mouse inputs via a modal operator and feeds them into custom properties on a target object. This architecture cleanly separates OS-level event handling from the simulation logic, allowing all physics and rendering to run at full speed on the GPU.

## Bricks Implementation (`bricks.blend`)
This project file includes a fully playable Breakout-style game as a proof-of-concept. To play, open the blend file, run geonodege.py from the text editor (or install the file as addon) to setup the engine, switch to Geonode Game workspace and switch the viewport to Rendered Mode (shortcut z), open the N-Panel (Geonode Engine tab), and click "Start Engine". Press **Enter** to launch the ball and use the **Left/Right Arrow Keys** (or A/D) to move the paddle. The entire game logic is powered by a Data-Oriented Entity Component System (ECS) built purely with Geometry Nodes. Modular node groups (like kinematics, paddle collision, and brick collision) act as systems that process a unified point cloud within a central Simulation Zone, ensuring exceptional performance. You can check out the game logic in Geometry Node Editor on Master_Engine object.

 [Demo Video](https://youtu.be/1BjBT2Qy0cE)

