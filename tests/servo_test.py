import time
import board
import pwmio
import servo

pwm_servo = pwmio.PWMOut(board.GP2, duty_cycle=0, frequency=50)
servo = servo.Servo(pwm_servo, min_pulse=460, max_pulse=2500)

Startangle = 0
servo.angle = Startangle
time.sleep(5)
while True:
	for angle in range(Startangle, 130, 1):
		servo.angle = angle
		time.sleep(0.01)
	time.sleep(.5)
	for angle in range(130, Startangle, -1):
		servo.angle = angle
		if angle < 20:  # Slow down for the last 20 degrees
			time.sleep(0.02)  #! Longer delay at the extremes!
		else:
			time.sleep(0.01)
	time.sleep(2)
