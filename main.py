	# todo:
		#* fix website manuele controle
		#* testen!
		#* fix led rood frequentie...

		#* fix botsingssensoren + torentjes sensibiliteit
		#* fix afstandsensor positie
		#* fix loskomende bouten
		#* pinnen aan motoren solderen

import socketpool
import wifi
import time
import sys # stop gracefully

from adafruit_httpserver import Server, Request, Response, GET, Websocket

import board
import digitalio
from analogio import AnalogIn # LDR
import pwmio # PWM
# import adafruit_us100 # afstandsensor, te traag!
import busio # afstandsensor
#import adafruit_hcsr04 # afstandsensor
import servo # servo

import math

# MARK: SETUP
SSID = "PICO-TEAM-208" #* param
PASSWORD = "newTries"  #* param

# ANDERE INIT
led_state = 0 # 0 = naar VOREN, 1 = naar ACHTEREN, 2 = OPNEMEN pin, 3 = GARAGE
MAX_PWM = 65535 # 2^16 - 1
ref_tijd_blink = time.monotonic() + 0.5

wifi.radio.start_ap(ssid=SSID, password=PASSWORD)

# print IP adres
print("My IP address is", wifi.radio.ipv4_address_ap)

pool = socketpool.SocketPool(wifi.radio)
server = Server(pool, "/static", debug=True)
websocket = None

# COMPONENTEN INITIALISATIE
led_bord = digitalio.DigitalInOut(board.LED)
led_bord.direction = digitalio.Direction.OUTPUT

led_r = pwmio.PWMOut(board.GP19,frequency=50) #! 50 is te laag!!
led_g = pwmio.PWMOut(board.GP20,frequency=1000)
led_b = pwmio.PWMOut(board.GP17,frequency=1000)

# Botsingssensor
switch_1 = digitalio.DigitalInOut(board.GP3)
switch_2 = digitalio.DigitalInOut(board.GP4)

# LDRs
ldr_r = AnalogIn(board.GP28) #LDR Rechts
ldr_l = AnalogIn(board.GP26) #LDR Links
ldr_a = AnalogIn(board.GP27) #LDR Achter
#ldr_a_treshold = 15000
ldr_a_treshold = 11000 #* param
#ldr_l_threshold = 10000
ldr_l_threshold = 8000 #* param
#ldr_r_threshold = 8500
ldr_r_threshold = 4000 #* param																								
diff_threshold = 2000 #* param

calib_phase = "none"
ldr_a_calib_val = []
ldr_l_calib_val = []
ldr_r_calib_val = []
calib_ref_time = time.monotonic()
CALIB_TIME = 5 #* param

# MOTOREN
motor_r_digital = digitalio.DigitalInOut(board.GP12)
motor_l_digital = digitalio.DigitalInOut(board.GP13)

motor_r_digital.direction = digitalio.Direction.OUTPUT
motor_l_digital.direction = digitalio.Direction.OUTPUT

motor_r_pwm = pwmio.PWMOut(board.GP14, frequency=1000)
motor_l_pwm = pwmio.PWMOut(board.GP15, frequency=1000)

# Afstandssensor
#afstandsensor = adafruit_hcsr04.HCSR04(trigger_pin=board.GP1, echo_pin=board.GP0)
#sonar = adafruit_hcsr04.HCSR04(trigger_pin=board.GP0, echo_pin=board.GP1)\
uart = busio.UART(board.GP0, board.GP1, baudrate=9600)
#us100 = adafruit_us100.US100(uart)

sonar_threshold = 15 #* param
AFST_DIST_ARR_SIZE = 5 #* param
sonarDistanceLast = [80] * AFST_DIST_ARR_SIZE

# Servo
pwm_servo = pwmio.PWMOut(board.GP2, duty_cycle=0, frequency=50)
servo = servo.Servo(pwm_servo, min_pulse=460, max_pulse=2500)
ref_tijd_servo = time.monotonic()
STARTANGLE = 0 #* param
ENDANGLE = 150 #* param
servo.angle = STARTANGLE
last_val_servo = STARTANGLE
servo_action = 0
INACTIVE = 0
UP = 1
DOWN = 2
pickup_manual = False

# MARK: INIT path
FORWARDS = 0
LEFT = 1
RIGHT = 2
PICKUP = 3
ONE_EIGHTY = 4
EOS = 5 # end of sequence
#path_seq = [0, 1, 0, 2, 1, 3, 1, 3, 0, EOS] # complex test
path_seq = [0, 2, 0, 1, 0, 0, 1, EOS] # turning test
#path_seq = [FORWARDS, FORWARDS, LEF3T, FORWARDS, RIGHT, FORWARDS, LEFT, FORWARDS, LEFT, FORWARDS, FORWARDS, FORWARDS, EOS]
#path_seq = [0, 3, EOS]
path_seq_idx = 0
current_action = path_seq[path_seq_idx]
auto_control = False #* param
					# !Beginnen met handmatige

ldr_reftijd = time.monotonic()
driving = False
drove_forwards = 0
DIDNT_DRIVE = 0
DRIVING = 1
DROVE = 2

manual_control_direction = "F"
manual_control_speed = 0

stop_flag = False

continue_forward_time = .5 #* param
cont_turn_time = .25 #* param

# MARK: WEBSOCK
# WEBSOCKET CONNECT FUN
# Deze functie wordt uitgevoerd wanneer de server een HTTP request ontvangt
@server.route("/connect-websocket", GET)
def connect_client(request: Request):
	global websocket  # pylint: disable=global-statement

	if websocket is not None:
		websocket.close()  # Close any existing connection

	websocket = Websocket(request)
 
	return websocket

server.start(str(wifi.radio.ipv4_address_ap), 80)

# MARK: DEFS
def nood_stop(cause: str):
	print(f"Noodstop geactiveerd door {cause}")
	return True

def start_game():
    print("Spel wordt gestart")
    # todo: game thing
    
def motorcontrol(motor_l: bool, motor_r: bool, v_l: int, v_r: int):
    motor_r_digital.value = motor_r
    motor_l_digital.value = motor_l

    motor_l_pwm.duty_cycle = min(math.floor(v_l / 100 * MAX_PWM), MAX_PWM)
    motor_r_pwm.duty_cycle = min(math.floor(v_r / 100 * MAX_PWM), MAX_PWM)

# left, right turns specifically for automatic control
def turn_left():
	motorcontrol(False, True, 100, 0)
def turn_right():
	motorcontrol(True, False, 0, 100)
# drives forward but adjusts if not perfectly on the line
def drive_forwards():
	#if not (ldr_r.value < ldr_r_threshold or ldr_l.value < ldr_l_threshold):
	if abs(ldr_r.value - ldr_l.value) < diff_threshold:
		motorcontrol(True, True, 100, 100)
	elif abs(ldr_r.value - ldr_l.value) > diff_threshold:
		if ldr_r.value > ldr_l.value:
			motorcontrol(True, True, 50, 100)
		else:
			motorcontrol(True, True, 100, 50)

def drive_forwards_pure():
	motorcontrol(True, True, 100, 100)
def turn_left_pure():
	motorcontrol(False, True, 50, 50)
def turn_right_pure():
	motorcontrol(True, False, 50, 50)
		
def drive_backwards():
	motorcontrol(False, False, 100, 100)

def pickup(ref_tijd, action, last_val):
	if action == UP and last_val < ENDANGLE: # and time.monotonic() > ref_tijd + 0.8:
		last_value_return = last_val + 4
		#print(f"{ref_tijd} {last_value_return}")
		servo.angle = last_value_return
		return last_value_return
	if last_val >= ENDANGLE:
		last_value_return = STARTANGLE
		servo.angle = STARTANGLE
		return last_value_return
	return last_val

def get_distance_fast():
    """Faster implementation for US100 sensor in CircuitPython"""
    """(gotta love python libs)"""
    # Clear any pending data
    while uart.in_waiting:
        uart.read(1)
    
    # Send trigger command (0x55 for distance)
    uart.write(b'\x55')
    
    # Short wait for response
    start = time.monotonic()
    while uart.in_waiting < 2 and time.monotonic() - start < 0.05:
        pass
    
    # Read data if available
    if uart.in_waiting >= 2:
        data = uart.read(2)
        if data and len(data) == 2:
            # Calculate distance in cm
            return (data[0] * 256 + data[1]) / 10
    
    return None

def sonar_get_distance():
	#sonarBegin = time.monotonic()
	
 	#last_dist = us100.distance # wayyyy too slow (.1s)
	last_dist = get_distance_fast()
	#print(f"us100.distance time: {time.monotonic() - sonarBegin}")
	
 	# als de sensor iets leest
	if last_dist:
		sonarDistanceLast.append(last_dist)
		sonarDistanceLast.pop(0)
		
		# filter de spikes, spikes zullen altijd te hoog zijn
		# min nemen is dus ok
		dist = min(sonarDistanceLast)
		return dist
	else:
		return -1

def get_back_to_garage_idx(path):
	last_idx = -1
	for i in range(len(path) - 1):
		# if we still have to pickup anything, we're not going back to the garage
		if path[i] == PICKUP:
			last_idx = i
	return last_idx

to_garage_idx = get_back_to_garage_idx(path_seq)

init = False
while True:
	loop_start = time.monotonic()
	server.poll()

	# MARK: WEB PARSING
	if websocket is not None:
		data = websocket.receive(fail_silently=True)
  
		if not init:
			websocket.send_message("path_seq " + " ".join(str(el) for el in path_seq))
			init = True
  
		# als er nieuwe data is aangekomen, lezen we deze
		if data is not None:
			# we zenden de net verkregen data terug naar de zender (de browserapp) en zullen deze in de browserconsole afbeelden
			# om een geschiedenis te hebben van wat er is gebeurd tijdens een sessie (kan helpen bij het debuggen)
			websocket.send_message(data, fail_silently=True)
			splitted_data = data.split()
			if len(splitted_data) == 0:
				raise Exception("WebsocketInputError: Empty packet received")
			elif splitted_data[0] == "move_forward" and len(splitted_data) == 2:
				try:
					print(f"Moving forward at speed {int(splitted_data[1])}")
				except:
					raise Exception("WebsocketInputError: move_forward requires an int")
			elif splitted_data[0] == "controle_overnemen":
				auto_control = not auto_control
				print("Handmatige controle geswitcht")
			elif splitted_data[0] == "start":
				start_game()
    
			elif splitted_data[0] == "stop":
				print("Nood stop status veranderd door noodknop")
				stop_flag = not stop_flag
			elif splitted_data[0] == "joystick" and len(splitted_data) == 3:
				try:
					speed = int(splitted_data[2])
				except:
					print(splitted_data)
					raise Exception("WebsocketInputError: 'joystick' expects an int as second parameter (speed)")
				manual_control_direction = splitted_data[1]
				manual_control_speed = speed
			elif splitted_data[0] == "manual_pickup":
				pickup_manual = True
			elif splitted_data[0] == "calib" and len(splitted_data) == 2:
				if splitted_data[1] == "white" and calib_phase == "none":
					calib_phase = "white"
					calib_ref_time = time.monotonic()
				elif splitted_data == "black" and calib_phase == "white_done":
					calib_phase = "black"
					calib_ref_time = time.monotonic()
				else:
					raise Exception("WebsocketInputError: calibration expects either black or white")
			else:
				raise Exception("WebsocketInputError: invalid command")
 
	if auto_control and not stop_flag:
		if calib_phase != "done": # !! testing mode
			# MARK: AUTO DRIVE
			if current_action == LEFT or current_action == RIGHT: # must turn
				print(f"Turning, ldr_l: {ldr_l.value}, ldr_r: {ldr_r.value}")
				if drove_forwards == DIDNT_DRIVE:
					reftijd_forwards = time.monotonic()
					drove_forwards = DRIVING
				elif drove_forwards == DRIVING:
					if time.monotonic() >= reftijd_forwards + continue_forward_time:
						drove_forwards = DROVE
						ldr_reftijd = time.monotonic()
						led_state = 0
					else:
						drive_forwards_pure()
						print("Driving forward")
						led_state = 0
				elif (ldr_l.value < ldr_l_threshold or ldr_r.value < ldr_r_threshold) \
        				and time.monotonic() - ldr_reftijd > 1:
					continue_turning_ref = time.monotonic()
					# Nog een beetje verder blijven draaien, aangezien we de LDRs de lijn eerder gaan zien dan dat we loodrecht staan
					while time.monotonic() < continue_turning_ref + cont_turn_time:
						if current_action == LEFT:
							turn_left()
						elif current_action == RIGHT:
							# hoeft niet te draaien, blijkt uit tests
							break
						time.sleep(.02)
					
					path_seq_idx += 1
					if path_seq_idx > len(path_seq) + 1:
						print("Arrived at the end of the sequence!")
						stop_flag = True
					print("going to next index: " + str(path_seq_idx))
					current_action = path_seq[path_seq_idx]
					print("action: " + str(current_action))
					drove_forwards = DIDNT_DRIVE
					ldr_reftijd = time.monotonic()
				else:
					if current_action == LEFT:
						turn_left()
					elif current_action == RIGHT:
						turn_right()
					else:
						raise Exception("PythonError: unexpected value caught during regeltechniek")
			if current_action == FORWARDS: # if ipv elif om een tick te winnen bij eventuele verandering
				led_state = 0
				if path_seq[path_seq_idx + 1] == PICKUP:
					print(f"Driving forwards, botsings: {not switch_1.value} {not switch_2.value}")
				else:
					print(f"Driving forwards, ldr_a: {ldr_a.value}")

				if driving == False:
					driving = True
					ldr_reftijd = time.monotonic()
    
				if ((path_seq[path_seq_idx + 1] == PICKUP and (not switch_1.value or not switch_2.value)) \
        			or (path_seq[path_seq_idx + 1] != PICKUP and ldr_a.value < ldr_a_treshold)) \
               		and time.monotonic() - ldr_reftijd > 1:
					# !! stopt alleen voor pickup bij torentjes !!
					path_seq_idx += 1
					if path_seq_idx > len(path_seq) + 1:
						print("Arrived at the end of the sequence!")
						stop_flag = True
					print("going to next index: " + str(path_seq_idx))
					current_action = path_seq[path_seq_idx]
					print("action: " + str(current_action))
					driving = False
				else:
					drive_forwards()
			if current_action == PICKUP:
				motorcontrol(False, False, 0, 0)
				if servo_action == INACTIVE:
					ref_tijd_servo = time.monotonic() - 0.05
					servo_action = UP
				last_val_servo = pickup(ref_tijd_servo, servo_action, last_val_servo)
				if last_val_servo == STARTANGLE:
					servo_action = INACTIVE
				ref_tijd_servo = time.monotonic()
				if servo_action == INACTIVE:
					path_seq_idx += 1
					if path_seq_idx > len(path_seq) + 1:
						print("Arrived at the end of the sequence!")
						stop_flag = True
					print("going to next index: " + str(path_seq_idx))
					current_action = path_seq[path_seq_idx]
					print("action: " + str(current_action))
					while ldr_a.value < ldr_a_treshold:
						# !! blijft in alle situaties vooruit rijden
						drive_forwards()
			if current_action == ONE_EIGHTY:
				if ldr_a.value < ldr_a_treshold:
					path_seq_idx += 1
					if path_seq_idx > len(path_seq) + 1:
						print("Arrived at the end of the sequence!")
						stop_flag = True
					print("going to next index: " + str(path_seq_idx))
					current_action = path_seq[path_seq_idx]
					print("action: " + str(current_action))
				else: motorcontrol(False, True, 50, 50)
			if current_action == EOS:
				motorcontrol(True, True, 0, 0)
				servo.angle = STARTANGLE
				time.sleep(1)
				sys.exit("Graceful Exit") # exit gracefully when done
		elif time.monotonic() > ref_tijd_blink:
			print("Please calibrate LDRs")
	elif not stop_flag:
		# MARK: MANUAL
		print("manual control: " + manual_control_direction + " " + str(manual_control_speed))
		if manual_control_direction == "0":
			motorcontrol(False, False, 0, 0)
		elif manual_control_direction == "F":
			led_state = 0
			motorcontrol(True, True, manual_control_speed, manual_control_speed)
		elif manual_control_direction == "B":
			led_state = 1
			drive_backwards()
		elif manual_control_direction == "L":
			led_state = 0
			turn_left_pure()
		elif manual_control_direction == "R":
			led_state = 0
			turn_right_pure()
		else:
			raise Exception("RegeltechniekError: invalid direction")

		if pickup_manual:
			led_state = 2
			motorcontrol(False, False, 0, 0)
			if servo_action == INACTIVE:
				ref_tijd_servo = time.monotonic() - 0.05
				servo_action = UP
				last_val_servo = 0
			last_val_servo = pickup(ref_tijd_servo, servo_action, last_val_servo)
			if last_val_servo == 0:
				servo_action = INACTIVE
			ref_tijd_servo = time.monotonic()
			if servo_action == INACTIVE:
				pickup_manual = False
	elif time.monotonic() > ref_tijd_blink: # niet al te vaak printen
		motorcontrol(False, False, 0, 0)
		print("Stop actief") # ! reden melden? end of seq, noodstop, ...
 
	# MARK: OTH COMP
	# STATUS LED PICO
	if time.monotonic() > ref_tijd_blink:
		ref_tijd_blink = time.monotonic() + 0.5
		led_bord.value = not led_bord.value
  
	# LDR CALIB
	''' # Calibratie werkt nog niet volledig, ook niet perse nodig tenzij echt heel grote variaties van de omgeving
	if (calib_phase == "white" or calib_phase == "black") and time.monotonic() >= calib_ref_time() + CALIB_TIME:
		print(f"Calibrating for {calib_phase}")
		if calib_phase == "white":
			calib_phase = "white_done"
			websocket.send_message("calib white_done")			

			ldr_a_lo = math.mean(ldr_a_calib_val)
			ldr_l_lo = math.mean(ldr_l_calib_val)
			ldr_r_lo = math.mean(ldr_r_calib_val)
		elif calib_phase == "black":
			calib_phase = "done"
			websocket.send_message("calib done")
	
			ldr_a_treshold = math.mean([math.mean(ldr_a_calib_val) , ldr_a_lo])
			ldr_l_treshold = math.mean([math.mean(ldr_l_calib_val) , ldr_l_lo])
			ldr_r_treshold = math.mean([math.mean(ldr_r_calib_val) , ldr_r_lo])

		ldr_a_calib_val = []
		ldr_l_calib_val = []
		ldr_r_calib_val = []
	else:
		ldr_a_calib_val.append(ldr_a.value)
		ldr_l_calib_val.append(ldr_l.value)
		ldr_r_calib_val.append(ldr_r.value)
	'''
  
	# RGB LED HANDELING
	if path_seq_idx > to_garage_idx and auto_control: # GARAGE -> blauw ctu
		led_r.duty_cycle = 0
		led_g.duty_cycle = 0
		led_b.duty_cycle = MAX_PWM
	elif led_state == 0: # Naar VOOR -> cyclus
		current_cycle_state = math.floor(MAX_PWM/2 + MAX_PWM/2*(math.sin(2*math.pi*time.monotonic())))
		led_r.duty_cycle = current_cycle_state
		led_g.duty_cycle = MAX_PWM
		led_b.duty_cycle = current_cycle_state
	elif led_state == 1: # Naar ACHTER -> rood aan uit
		led_b.duty_cycle = 0
		led_g.duty_cycle = 0
		if led_bord.value: # Het alterneren gebeurd gelijktijdig met het alterneren van het de led op het bord
			led_r.duty_cycle = MAX_PWM
		else:
			led_r.duty_cycle = 0
	elif led_state == 2: # VERZAMELING -> oranje aan uit
		led_b.duty_cycle = 0
		if led_bord.value:
			led_r.duty_cycle = MAX_PWM
			led_g.duty_cycle = math.floor(MAX_PWM / 2)
		else:
			led_r.duty_cycle = 0
			led_g.duty_cycle = 0
	else:
		raise Exception("rgbOptionError: index out of bounds")

	# AFSTANDSSENSOR
	distance = sonar_get_distance() # uitvoer in cm
	# distance must be valid and setup time must have passed
	if distance == -1:
		#print(f"Sonar Failed: {sonarDistanceLast}")
		pass
	elif distance < sonar_threshold:
		stop_flag = nood_stop("afstandsensor")
	
	# loop duration calculation w/o sleep
	# loop_end = time.monotonic()
	# loop_duration = loop_end - loop_start
	# print(f"Loop duration: {loop_duration} seconds")
	
	time.sleep(0.05)
