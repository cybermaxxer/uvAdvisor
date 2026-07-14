# AI use: asked Claude for the actual exposure formulas and skin multiplier/dangerous UV
# starting values below (not a dermatologist, needed a real starting point rather than guessing
# numbers). The constants in skin_multiplier, dangerous_uv, and the formulas inside get_exposure(),
# get_vitaminD_exposure(), and get_circadian_rhythm_exposure() came from that conversation.
# This is consumer-grade guidance, not clinical data, see tanning.md for the disclaimer.
from skin_type import SkinType as skin
import requests
skin_multiplier = {
    skin.VERY_FAIR: 1.6,
    skin.FAIR: 2.0,
    skin.MEDIUM: 2.7,
    skin.OLIVE: 3.3,
    skin.BROWN: 5.4,
    skin.BLACK: 10.8
}
dangerous_uv = {
    skin.VERY_FAIR: 3,
    skin.FAIR: 4,
    skin.MEDIUM: 5,
    skin.OLIVE: 6,
    skin.BROWN: 8,
    skin.BLACK: 10
}
skin_colors_rgb = {
    skin.VERY_FAIR: (255, 224, 196),
    skin.FAIR: (241, 194, 158),
    skin.MEDIUM: (224, 172, 134),
    skin.OLIVE: (198, 142, 101),
    skin.BROWN: (141, 85, 56),
    skin.BLACK: (87, 56, 38)
}
#all-in function to simplify the process of calculating the exposure time based on skin type, goal, uv index, weather code, and time of day. It returns the minimum and maximum exposure times in minutes.
# Change the signature to take an info_point object
# Change the signature to take an info_point object
def get_exposure(skin_type, goal, InfoPoint):
    multiplier = float(skin_multiplier[skin_type])
    
    # Extract values directly from the InfoPoint object
    uv = InfoPoint.uv
    wmo_code = InfoPoint.weather_code
    time_of_day = InfoPoint.time_of_day.lower() 

    if uv is None:
        raise ValueError("UV index is not provided.")
    if uv <= 0:
        return float("inf"), float("inf")  
        
    if goal == "avoid":
        max_time = (100 * multiplier) / (3 * uv)
        min_time = max(get_vitaminD_exposure(skin_type, goal, uv), get_circadian_rhythm_exposure(wmo_code, time_of_day))
        if min_time > max_time:
            min_time = max_time   
        return round(min_time, 1), round(max_time, 1)
    elif goal == "tan":
        max_time = (50 * multiplier) / (3 * uv)
        min_time = max((25 * multiplier) / (3 * uv), max(get_vitaminD_exposure(skin_type, goal, uv), get_circadian_rhythm_exposure(wmo_code, time_of_day))) 
        if min_time > max_time:
            min_time = max_time   
        return round(min_time, 1), round(max_time, 1)  
    else:
        raise ValueError("Invalid goal. Please choose 'avoid' or 'tan'.")
    
#how much vitamin D you need to get a day to stay healthy
def get_vitaminD_exposure(skin_type, goal, uv): #calculates how much time is needed to get vitamin D based on skin type and the goal (avoid/tan).
    multiplier = float(skin_multiplier[skin_type])
    vit_d_time = (33.3 * multiplier) / (3 * uv)
    return round(vit_d_time, 1)
#how much time you need to flip the switch for circadian rhythm, based on the weather code and time of day.
def get_circadian_rhythm_exposure(wmo_code, time_of_day = "morning"):
    if time_of_day != "morning":
        return 45.0
    if wmo_code == 0:
        return 10.0
    elif wmo_code in [1, 2]:
        return 15.0
    elif wmo_code in [3, 45, 48]:
        return 30.0  
    else:
        
        return 45.0 
    
#used claude here to suggest me the algorithm
def get_best_intervals(infoPoints, skin_type, goal):
    circadian_slots = []
    outside_slots = []
    no_tanning_slots = []
    dangerous_slots = []
    for point in infoPoints:
        tod_lower = point.time_of_day.lower()

        if point.time_of_day == "Morning":
            circadian_time = get_circadian_rhythm_exposure(point.weather_code, tod_lower)
            max = get_exposure(skin_type, goal, point)[1]
            circadian_slots.append({
                "hour": point.hour,
                "duration_required": circadian_time,
                "max_time": max,
                "uv": point.uv
            })
            
        if point.uv <= 0:
            no_tanning_slots.append({
                "hour": point.hour,
                "duration_required": 0,
                "uv": point.uv
            })
        else:
            try:
                min_time, max_time = get_exposure(skin_type, goal, point)
                if min_time > 60.0:
                    no_tanning_slots.append({
                        "hour": point.hour,
                        "duration_required": min_time,
                        "uv": point.uv
                    })
                elif point.uv >= dangerous_uv[skin_type]:
                    dangerous_slots.append({
                        "hour": point.hour,
                        "uv": point.uv,
                        "time": min_time,
                        "message": f"UV is {point.uv}, you can only stay outside for {min_time} minutes"
                    })    
                else:
                    outside_slots.append({
                        "hour": point.hour,
                        "uv": point.uv,
                        "min_time": min_time,
                        "max_time": max_time 
                    })
            except ValueError as e:
                print(f"Error calculating exposure for hour {point.hour}: {e}")
            except Exception as e: 
                print(f"Unexpected error calculating exposure for hour {point.hour}: {e}")
#functional programming, pretty much function is also an input, here we explain sort how to sort the things based on lambda
    #logic to rank the circadian is quite simple: the less time you need to hit the circadian rhythm, the better.
    rankedCircadian = sorted(circadian_slots, key=lambda x: x["duration_required"])
    rankedNoTanning = sorted(no_tanning_slots, key=lambda x: x["duration_required"], reverse=True)
    rankedDangerous = sorted(dangerous_slots, key=lambda x: x["uv"], reverse=True)
    if goal == "avoid": #the less uv the better
        rankedOutside = sorted(outside_slots, key=lambda x: x["uv"])
    elif goal == "tan": # the more uv the better
        rankedOutside = sorted(outside_slots, key=lambda x: x["uv"], reverse=True)
    else:
        rankedOutside = outside_slots
    return {
        "circadian": rankedCircadian,
        "outside": rankedOutside,
        "no_tanning": rankedNoTanning,
        "dangerous": rankedDangerous
    }
def get_current_city():
    try:
        response = requests.get("https://ipinfo.io/json")
        data = response.json()
        city = data.get("city", "Unknown")
        country = data.get("country", "")
        return city, country
    except Exception as e:
        print(f"Error fetching current city: {e}")
        return "Unknown", ""
def color_block(rgb):
    # AI use: gave Claude the spec ("print an actual color block in the terminal for this rgb
    # tuple, using ansi escape codes") and it wrote this function whole.
    r, g, b = rgb
    return f"\033[48;2;{r};{g};{b}m \033[0m" 
#\033 tells "a command follows, not text" 
#[ says start of the command
#48 set background color (38 means text color) 
#;2; i am giving rgb
# r g b are the numbers given the input tuple 
#m of the command 
# a literal space character (what is turned into this character)
# \033[0m resets the color back to default
