"""
PlantAI - Raspberry Pi 综合传感器模块
支持: SHT30, BH1750, CCS811, YL69, DHT22
"""
import time
import board
import busio
import adafruit_bh1750
import adafruit_sht31d
import adafruit_ccs811
import adafruit_dht

from adafruit_mcp3xxx.mcp3008 import MCP3008
from adafruit_mcp3xxx.analog_in import AnalogIn
import digitalio

class SensorSuite:
    def __init__(self, i2c=None):
        self.i2c = i2c or busio.I2C(board.SCL, board.SDA)

        # --- 初始化各类传感器 ---
        self._init_sht30()
        self._init_bh1750()
        self._init_ccs811()
        self._init_yl69()
        self._init_dht22()

    def _init_sht30(self):
        try:
            self.sht30 = adafruit_sht31d.SHT31D(self.i2c, address=0x44)
            print("✅ SHT30 温湿度传感器已连接")
        except Exception as e:
            print("⚠️ SHT30 未检测到:", e)
            self.sht30 = None

    def _init_bh1750(self):
        try:
            self.bh1750 = adafruit_bh1750.BH1750(self.i2c)
            print("✅ BH1750 光照传感器已连接")
        except Exception as e:
            print("⚠️ BH1750 未检测到:", e)
            self.bh1750 = None

    def _init_ccs811(self):
        try:
            self.ccs811 = adafruit_ccs811.CCS811(self.i2c)
            while not self.ccs811.data_ready:
                time.sleep(0.5)
            print("✅ TVOC/CO2 传感器已连接")
        except Exception as e:
            print("⚠️ TVOC/CO2 传感器未检测到:", e)
            self.ccs811 = None

    def _init_yl69(self):
        try:
            spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
            cs = digitalio.DigitalInOut(board.D5)
            self.mcp = MCP3008(spi, cs)
            self.soil_ch = AnalogIn(self.mcp, 0)
            print("✅ YL-69 土壤湿度模块已连接")
        except Exception as e:
            print("⚠️ 土壤湿度模块未检测到:", e)
            self.soil_ch = None

    def _init_dht22(self):
        try:
            self.dht = adafruit_dht.DHT22(board.D4, use_pulseio=False)
            print("✅ DHT22 已连接 (GPIO4)")
        except Exception as e:
            print("⚠️ DHT22 未检测到:", e)
            self.dht = None

    def read_all(self):
        data = {"timestamp": time.time()}
        # --- 温湿度 (SHT30 优先) ---
        if self.sht30:
            data["temperature_c"] = round(self.sht30.temperature, 2)
            data["humidity_pct"] = round(self.sht30.relative_humidity, 2)
        elif self.dht:
            try:
                data["temperature_c"] = round(self.dht.temperature, 2)
                data["humidity_pct"] = round(self.dht.humidity, 2)
            except Exception:
                data["temperature_c"] = data["humidity_pct"] = None

        # --- 光照 ---
        data["light_lux"] = round(self.bh1750.lux, 2) if self.bh1750 else None

        # --- 空气质量 ---
        if self.ccs811:
            data["eCO2_ppm"] = self.ccs811.eco2
            data["TVOC_ppb"] = self.ccs811.tvoc
        else:
            data["eCO2_ppm"] = data["TVOC_ppb"] = None

        # --- 土壤湿度 ---
        if self.soil_ch:
            raw = self.soil_ch.value
            data["soil_raw"] = raw
            data["soil_moisture_pct"] = round(100 - (raw / 65535 * 100), 2)
        else:
            data["soil_raw"] = data["soil_moisture_pct"] = None

        return data


if __name__ == "__main__":
    sensors = SensorSuite()
    while True:
        data = sensors.read_all()
        print(f"\n🕒 时间戳: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌡 温度: {data.get('temperature_c')} °C")
        print(f"💧 湿度: {data.get('humidity_pct')} %")
        print(f"☀️ 光照强度: {data.get('light_lux')} lux")
        print(f"🌿 二氧化碳: {data.get('eCO2_ppm')} ppm")
        print(f"🌫 TVOC: {data.get('TVOC_ppb')} ppb")
        print(f"🌱 土壤湿度: {data.get('soil_moisture_pct')} %")
        time.sleep(1800)  # 每1800秒=30分钟输出一次

