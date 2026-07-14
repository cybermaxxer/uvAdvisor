class InfoPoint:
    def __init__(self, time, uv, weather_code, temperature=None):
        self.time = time
        self.uv = uv
        self.weather_code = weather_code
        self.hour = int(time.split("T")[1].split(":")[0])  # Extract hour from time string
        if 6 <= self.hour < 12:
            self.time_of_day = "Morning"
        elif 12 <= self.hour < 17:
            self.time_of_day = "Afternoon"
        elif 17 <= self.hour < 21:
            self.time_of_day = "Evening"
        else:
            self.time_of_day = "Night"
        self.temperature = None  if temperature is None else float(temperature)
        


