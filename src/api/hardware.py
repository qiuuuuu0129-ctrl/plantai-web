# src/pi/hardware.py
import time
import board
import neopixel
import RPi.GPIO as GPIO

# ==============================
# 硬件控制类定义
# ==============================

class PumpController:
    """继电器/水泵控制"""
    def __init__(self, pin=23, active_high=False):
        self.pin = pin
        self.active_high = active_high
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW if self.active_high else GPIO.HIGH)

    def on(self):
        GPIO.output(self.pin, GPIO.HIGH if self.active_high else GPIO.LOW)
        print("💧 Pump ON")

    def off(self):
        GPIO.output(self.pin, GPIO.LOW if self.active_high else GPIO.HIGH)
        print("💧 Pump OFF")

    def pulse(self, duration_s=3):
        self.on()
        time.sleep(duration_s)
        self.off()


class SimpleLightController:
    """控制单色 LED 灯或普通继电器灯"""
    def __init__(self, pin=24, pwm=False):
        self.pin = pin
        self.pwm = pwm
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        if self.pwm:
            self.p = GPIO.PWM(self.pin, 1000)
            self.p.start(0)
        else:
            self.p = None

    def on(self):
        if self.pwm:
            self.p.ChangeDutyCycle(100)
        else:
            GPIO.output(self.pin, GPIO.HIGH)
        print("💡 Light ON")

    def off(self):
        if self.pwm:
            self.p.ChangeDutyCycle(0)
        else:
            GPIO.output(self.pin, GPIO.LOW)
        print("💡 Light OFF")

    def set_brightness(self, duty):
        """0~100"""
        if not self.pwm:
            return
        self.p.ChangeDutyCycle(max(0, min(100, duty)))
        print(f"💡 Brightness {duty}%")


class WS2812Controller:
    """WS2812 RGB 灯带控制"""
    def __init__(self, led_count=18, gpio_pin=18, brightness=0.5):
        self.led_count = led_count
        self.gpio_pin = gpio_pin
        self.brightness = brightness
        self.pixels = neopixel.NeoPixel(board.D18, self.led_count,
                                        brightness=self.brightness, auto_write=False)
        print(f"🌈 WS2812 初始化完成，共 {self.led_count} 个LED")

    def fill_color(self, color):
        """color = (R,G,B)"""
        self.pixels.fill(color)
        self.pixels.show()
        print(f"🌈 WS2812 显示颜色: {color}")

    def off(self):
        self.fill_color((0, 0, 0))
        print("🌈 WS2812 关闭")

    def demo_cycle(self):
        """简单的颜色循环示例"""
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255),
                  (255, 255, 0), (255, 255, 255)]
        for c in colors:
            self.fill_color(c)
            time.sleep(0.5)
        self.off()

# ==============================
# 模块测试
# ==============================
if __name__ == "__main__":
    pump = PumpController(pin=23, active_high=False)
    light = SimpleLightController(pin=24)
    ws = WS2812Controller(led_count=18, gpio_pin=18)

    try:
        pump.pulse(2)
        light.on()
        time.sleep(1)
        light.off()
        ws.demo_cycle()
    finally:
        GPIO.cleanup()
        print("GPIO 清理完成")

