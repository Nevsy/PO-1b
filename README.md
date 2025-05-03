# PO-1b
Self-driving or manually controlled, self built vehicle as a group project for university

### Task
This project was made for a group project at university.

Tasks:
- follow lines on a 30x30cm grid, following an imposed path
- pick up pucks on the corners of this grid
- have a web interface to communicate with the Raspberry Pico (Pico) on the vehicle, which should be able to be controlled freely
- stop the vehicle when the sonar senses the wall is too close
- make a status led show what action the vehicle is currently executing
### Project structure:
- The use of PyCircuit was obligatory.
- The entirety of the code that runs on the Pico is situated in /main.py (I know, I should split it up), this file is automatically ran when the Pico starts.
- When an external computer is connected and sends the right HTTP GET request (some particular port on the Pico's network), the web files inside /static is served. (html, css, js, favicon, communication later switches to websockets)
- The files inside /lib are used during interpretation along with python's stdlib.
- /tests contains a few of the many tests we made during this project.
