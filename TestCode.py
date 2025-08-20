import pigpio
import time
import sys

pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("pigpio daemon not running")

# --- Motor pins ---
ENA, IN1, IN2 = 18, 23, 24
ENB, IN3, IN4 = 19, 27, 22

# --- Ultrasonic pins ---
TRIG = 5
ECHO = 6

# --- Button pin ---
BUTTON = 26  # active low

# --- Setup ---
for p in (ENA, IN1, IN2, ENB, IN3, IN4, TRIG):
    pi.set_mode(p, pigpio.OUTPUT)
pi.set_mode(ECHO, pigpio.INPUT)
pi.set_mode(BUTTON, pigpio.INPUT)
pi.set_pull_up_down(BUTTON, pigpio.PUD_UP)  # switch to GND

pi.set_PWM_frequency(ENA, 2000)
pi.set_PWM_frequency(ENB, 2000)

# --- Motor functions ---
def run_motor(enable_pin, pin1, pin2, value):
    forward = value >= 0
    pi.write(pin1, 1 if forward else 0)
    pi.write(pin2, 0 if forward else 1)
    pi.set_PWM_dutycycle(enable_pin, min(255, abs(int(value))))

def stop_motor(enable_pin, pin1, pin2, brake=False):
    pi.set_PWM_dutycycle(enable_pin, 0)
    if brake:
        pi.write(pin1, 1)
        pi.write(pin2, 1)
    else:
        pi.write(pin1, 0)
        pi.write(pin2, 0)

def stop_all(brake=False):
    stop_motor(ENA, IN1, IN2, brake)
    stop_motor(ENB, IN3, IN4, brake)

# --- Ultrasonic function ---
def get_distance():
    pi.write(TRIG, 1)
    time.sleep(0.00001)
    pi.write(TRIG, 0)

    start = time.time()
    while pi.read(ECHO) == 0:
        start = time.time()
    stop = time.time()
    while pi.read(ECHO) == 1:
        stop = time.time()

    elapsed = stop - start
    return (elapsed * 34300) / 2  # distance in cm

# --- Main loop ---
try:
    print("Hold button to move car. Release to stop. CTRL+C to exit.")
    while True:
        # Car runs only while button is pressed (active low)
        car_running = pi.read(BUTTON) == 0

        if car_running:
            distance = get_distance()
            print(f"Distance: {distance:.1f} cm")

            if distance <= 10:
                print("Obstacle detected! Stopping temporarily...")
                stop_all(brake=True)
                while get_distance() <= 10:
                    time.sleep(0.1)
                print("Path clear. Resuming forward motion.")
            else:
                run_motor(ENA, IN1, IN2, 150)
                run_motor(ENB, IN3, IN4, 150)
        else:
            stop_all()

        time.sleep(0.05)

except KeyboardInterrupt:
    print("CTRL+C detected, stopping.")
finally:
    stop_all(brake=True)
    pi.stop()
    sys.exit(0)
