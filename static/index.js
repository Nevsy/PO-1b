//import "Math"

// MARK: WEBSOCKET
let socket = undefined;
let path_seq = []

let status_text = document.getElementById("status");
let connect_view = document.getElementById("connected");
let disconnect_view = document.getElementById("disconnected");
let calib_view = document.getElementById("calib");
let connected = false;

let calib_bold = document.getElementById("calib_bold")
let calib_btn = document.getElementById("calib_btn")

function connect_socket() {
	// Close any existing sockets
	disconnect_socket();

	socket = new WebSocket("ws://192.168.4.1:80/connect-websocket");

	// Connection opened
	socket.addEventListener("open", (event) => {
		status_text.textContent = "Status: Connected";
		connect_view.style.display = "flex"
		disconnect_view.style.display = "none"
		calib_view.style.display = "none"
		connected = true
		
		// recompute rectangle bounds, as it has just been loaded!
		joy = document.getElementById("joy_div");
		rect = joy.getBoundingClientRect();
		rect_center_hori = rect.left + rect.width / 2;
		rect_center_verti = rect.top + rect.height / 2;
	});

	socket.addEventListener("close", (event) => {
		socket = undefined;
		status_text.textContent = "Status: Disconnected";
		connect_view.style.display = "none"
		disconnect_view.style.display = "flex"
		calib_view.style.display = "none"
		connected = false
	});
	
	socket.addEventListener("message", (event) => {
		console.log(event.data)

		let command = event.data.split(" ")
		if (command[0] == "path_seq") {
			for (let i = 1; i < command.length; i++) {
				path_seq.push(parseInt(command[i]))
			}
		}
		else if (command[0] == "calib" && command.length == 2) {
			calib_done(command[1])
		}
	});
	
	socket.addEventListener("error", (event) => {
		socket = undefined;
		status_text.textContent = "Status: Disconnected";
		connect_view.style.display = "none"
		disconnect_view.style.display = "flex"
		calib_view.style.display = "none"
		connected = false
	});
}

function disconnect_socket() {
	if(socket != undefined) {
		socket.close();
	}
}

function sendCommand(command) {
	//console.log(command)
	let to_send = ""
	if(socket != undefined) {
		if (command == "controle_overnemen") {
			socket.send("controle_overnemen")
		}
		else if (command == "start") {
			socket.send("start")
		}
		else if (command == "noodknop") {
			socket.send("stop")
			let noodknop_txt = document.getElementById("noodknop_txt")
			noodknop_txt.style.display = "block"
			window.setTimeout(() => {
				noodknop_txt.display = "none"
			}, 5000)
		}
		else if (command.split(' ')[0] == "joystick"){
			socket.send(command)
		}
		else if (command == "manual_pickup"){
			socket.send(command)
		}
	} else {
		alert("Not connected to the PICO")
	}
}

// MARK:JOYSTICK
let joy = document.getElementById("joy_div");
let rect = joy.getBoundingClientRect(); // This is loaded on website load, when the rectangle isn't yet loaded

let rect_center_hori = rect.left + rect.width / 2;
let rect_center_verti = rect.top + rect.height / 2;
const mouse = { x: 0, y: 0 };
let joy_data = { x: 3, y: 3, r: 3 };

document.addEventListener("mousemove", (e) => {
	mouse.x = e.clientX;
    mouse.y = e.clientY;
});

window.setInterval(() => {
	if (connected) {
		
		const diffxRaw = mouse.x - rect_center_hori;
		const diffyRaw = mouse.y - rect_center_verti;
		// Check if mouse is inside the joy_div
		if (
			Math.abs(diffxRaw) <= rect.width / 2 &&
			Math.abs(diffyRaw) <= rect.height / 2
		) {
			joy_data.x = diffxRaw;
			joy_data.y = -diffyRaw;
			
			joy_data.r = Math.sqrt(joy_data.x ** 2 + joy_data.y ** 2);
			//console.log(joy_data.x, joy_data.y, joy_data.r);
		} else {
			// If outside, reset (not moving when no active input)
			joy_data.x = 0;
			joy_data.y = 0;
			joy_data.r = 0;
		}
		
		direction = "0" // 0 = still, F = forwards, L = left, R = right, B = backwards
		if (joy_data.r < 20) {
			direction = "0"
		}
		else if (joy_data.y > 0) {
			if (joy_data.x >= 0) {
				if (joy_data.y >= joy_data.x) {
					direction = "F";
				}
				else if (joy_data.y < joy_data.x) {
					direction = "R";
				}
			}
			if (joy_data.x < 0) {
				if (joy_data.y >= -joy_data.x) {
					direction = "F";
				}
				else if (joy_data.y < -joy_data.x) {
					direction = "L";
				}
			}
		}
		else if (joy_data.y < 0) {
			if (joy_data.x >= 0) {
				if (-joy_data.y >= joy_data.x) {
					direction = "B";
				}
				else if (-joy_data.y < joy_data.x) {
					direction = "R";
				}
			}
			if (joy_data.x < 0) {
				if (-joy_data.y >= -joy_data.x) {
					direction = "F";
				}
				else if (-joy_data.y < -joy_data.x) {
					direction = "L";
				}
			}
		}
		
		//console.log(joy_data.x + " " +  joy_data.y + " " +  Math.floor(joy_data.r) + " " + direction)
		if (socket != undefined && connected) {
			if (Math.floor(joy_data.r) > 90) {
				console.log("joystick " + direction + " 100")
				sendCommand("joystick " + direction + " 100")
			}
			else {
				console.log("joystick " + direction + " " + Math.floor(joy_data.r * 100/90))
				sendCommand("joystick " + direction + " " + Math.floor(joy_data.r * 100/90))
			}
		}
	}
}, 100); // We use 100ms (0.100s) to ensure we have recent data on the pico

let calib_phase = "none"
function calib() {
	if (calib_phase == "none") {
		calib_phase = "white"
		sendCommand("calib white")
		calib_btn.style.display = "none"
		
		connect_view.style.display = "none"
		disconnect_view.style.display = "none"
		calib_view.style.display = "flex"
	}
	else if (calib_phase == "white_done") {
		calib_phase = "black"
		sendCommand("calib black")
		calib_btn.style.display = "none"
	}
	else {
		console.log("Too Fast")
	}
}

function calib_done(color) {
	if (color == "white") {
		calib_phase = "white_done"
		calib_bold.textContent = "Black"
		calib_btn.style.display = "block"
	}
	else if (color == "black") {
		calib_phase = "done"
		
		connect_view.style.display = "flex"
		disconnect_view.style.display = "none"
		calib_view.style.display = "none"
	}
}