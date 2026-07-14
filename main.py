
import sys
from InfoPoint import InfoPoint
from itertools import groupby
import helpers
import requests
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# AI use: Claude explained how to structure the requests calls used in this file
# (building query params into the url, calling .json() on the response, the geocoding -> weather two step flow).
from skin_type import SkinType as skin

#ai use (claude) asked to create helpers to make the text colorful
def red_text(text):
    return f"\033[31;1m{text}\033[0m"

def yellow_text(text):
    return f"\033[33;1m{text}\033[0m"

def green_text(text):
    return f"\033[32;1m{text}\033[0m"

def orange_text(text):
    return f"\033[1;38;5;208m{text}\033[0m"
def dim_text(text):
    return f"\033[38;5;244m{text}\033[0m"

def mode1():
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=weather_code,uv_index,temperature_2m&timezone=auto"
    weather_response = requests.get(weather_url).json()
    current = weather_response["current"]
    
    current_info = InfoPoint(
        time=current["time"], 
        uv=current["uv_index"], 
        weather_code=current["weather_code"],
        temperature = current["temperature_2m"],
    )
    min, max = helpers.get_exposure(user_skin_type, user_goal, current_info)
    print(orange_text(f"\nCalculating exposure times on {current_info.time.split('T')[0]} at {current_info.time.split('T')[1]} for skin type: {skin(user_skin_type).name},\n goal: {user_goal},\n UV index: {current_info.uv},\n temperature: {current_info.temperature},\n city {city},\n minutes outside: min: {min}, max: {max}\n"))
    return current_info.time.split('T')[0], None
def mode2():
    mode1()
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,weather_code,uv_index&forecast_days=1&timezone=auto"    
    weather_response = requests.get(weather_url).json()
    date_input = weather_response["hourly"]["time"][0].split('T')[0]
    infoPoints = []
    for i in range(24):
        time = weather_response["hourly"]["time"][i]
        uv_index = weather_response["hourly"]["uv_index"][i]
        wmo_code = weather_response["hourly"]["weather_code"][i]
        temperature = weather_response["hourly"]["temperature_2m"][i]
        infoPoints.append(InfoPoint(time, uv_index, wmo_code, temperature))

    rankedLists = helpers.get_best_intervals(infoPoints, user_skin_type, user_goal)
    #AI use: Claude suggested this edge case: say somebody lives in the arctic circle, and the sun never rises, so there are no safe sun exposure windows. In that case, we should print a note to the user.
    print(yellow_text(f"Circadian Rhythm Hours:"))
    for slot in rankedLists["circadian"]:
        print(yellow_text(f"{slot['hour']}:00 {slot['duration_required']} minutes to get the switch on, uv: {slot.get('uv', 'N/A')}, max time: {slot.get('max_time', 'N/A')}"))
    if not rankedLists["outside"]:
        print(orange_text("\nNote: no safe sun exposure windows today (UV was either too low or too dangerous all day). this isn't medical advice, but if this is a regular pattern for you, it might be worth asking a doctor about vitamin D another way."))
    else:
        uv_peak_hour = max(infoPoints, key=lambda x: x.uv).hour
        solar_day = uv_peak_hour + 1
        for slot in rankedLists["outside"]:
            if float(slot["max_time"]) > 60.0:
                if float(slot["hour"]) >= solar_day:
                    slot["max_time"] = "as much as you want, uv is going to only decline after this hour"
                else:
                    slot["max_time"] = "capped at 60 minutes, uv is going to increase after this hour"
        print(green_text(f"\nBest Outside Hours:"))
        for slot in rankedLists["outside"]:
            print(green_text(f"{slot['hour']}:00 min time(in mins) outside: {slot['min_time']} - max time outside(in mins): {slot['max_time']} (UV: {slot['uv']})"))

    if rankedLists["no_tanning"]:
        print(dim_text(f"\nNo Tanning Hours:"))
        for slot in rankedLists["no_tanning"]:
            print(dim_text(f"{slot['hour']}:00 (UV: {slot['uv']})"))

    if rankedLists["dangerous"]:
        print(red_text(f"\nDangerous Hours:"))
        for slot in rankedLists["dangerous"]:
            print(red_text(f"{slot['hour']}:00 {slot['message']} (UV: {slot['uv']})"))
    return date_input, rankedLists
def mode3():
    # AI use: GitHub Copilot autocompleted most of this function, it mirrors mode2's structure pretty much
    # almost exactly (same InfoPoint loop, same ranking calls, same print formatting) so copilot
    # picked up the pattern from mode2 and suggested the bulk of it.

    date_input = input("Enter the date (dd/mm/yyyy): ")
    day, month, year = map(int, date_input.split("/"))
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,weather_code,uv_index&start_date={year}-{month:02d}-{day:02d}&end_date={year}-{month:02d}-{day:02d}&timezone=auto"    
    weather_response = requests.get(weather_url).json()
    infoPoints = []
    for i in range(24):
        time = weather_response["hourly"]["time"][i]
        uv_index = weather_response["hourly"]["uv_index"][i]
        wmo_code = weather_response["hourly"]["weather_code"][i]
        temperature = weather_response["hourly"]["temperature_2m"][i]
        infoPoints.append(InfoPoint(time, uv_index, wmo_code, temperature))
        uv_peak_hour = max(infoPoints, key=lambda x: x.uv).hour
        solar_day = uv_peak_hour + 1

    rankedLists = helpers.get_best_intervals(infoPoints, user_skin_type, user_goal)
    print(f"Calculating exposure times for skin type: {user_skin_type}, goal: {user_goal}, city: {city}, date: {date_input}\n")
    for slot in rankedLists["outside"]:
        if float(slot["max_time"]) > 60.0:
            if float(slot["hour"]) >= solar_day:
                slot["max_time"] = "as much as you want, uv is going to only decline after this hour"
            else:
                slot["max_time"] = "capped at 60 minutes, uv is going to increase after this hour"
    print(yellow_text(f"Circadian Rhythm Hours:"))
    for slot in rankedLists["circadian"]:
        print(yellow_text(f"{slot['hour']}:00 {slot['duration_required']} minutes to get the switch on, uv: {slot.get('uv', 'N/A')}, max time: {slot.get('max_time', 'N/A')}"))
    
    print(green_text(f"\nBest Outside Hours:"))
    for slot in rankedLists["outside"]:
        print(green_text(f"{slot['hour']}:00 min time(in mins) outside: {slot['min_time']} - max time outside(in mins): {slot['max_time']} (UV: {slot['uv']})"))
    print(dim_text(f"\nNo Tanning Hours:"))
    for slot in rankedLists["no_tanning"]:
        print(dim_text(f"{slot['hour']}:00 (UV: {slot['uv']})"))

    print(red_text(f"\nDangerous Hours:"))
    for slot in rankedLists["dangerous"]:
        print(red_text(f"{slot['hour']}:00 {slot['message']} (UV: {slot['uv']})"))
    return date_input, rankedLists

def create_pdf(date_input, rankedLists, city, skin_type, goal):
    print(f"PDF for {date_input} in {city} for skin type {skin_type.name} and goal {goal}")
    pdf = FPDF() 
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 20)
    pdf.cell(0, 20, f"UV Advisor Report for {skin(user_skin_type).name}, goal = {goal}, city {city}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.cell(0, 10, f"time is provided in minutes", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font("Helvetica", 'B', 16)
    #circdian rhythm section
    pdf.set_text_color(255, 165, 0)  # Orange color for Circadian Rhythm
    pdf.cell(0, 10, f"Circadian Rhythm Hours for {date_input} in {city}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(42, 8, "Hour", border=1, fill=True, align='C')
    pdf.cell(100, 8, "Duration Required", border=1, fill=True, align='C')
    pdf.cell(48, 8, "Max Time", border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_font("Helvetica", '', 12)
    if not rankedLists["circadian"]:
        pdf.cell(0, 8, "No Circadian Rhythm Hours available.", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    else:
        for slot in rankedLists["circadian"]:
            pdf.cell(42, 8, f"{slot['hour']}:00", border=1, align='C')
            pdf.cell(100, 8, f"{slot['duration_required']} minutes", border=1, align='C')
            if float(slot["max_time"]) == float("inf") or float(slot["max_time"]) >= 120.0:
                pdf.set_font("Helvetica", 'I', 12)  # Italic no risk label, slightly larger
                pdf.cell(48, 8, f"no risk", border=1, align='C')
                pdf.set_font("Helvetica", '', 12)  # Reset to normal font
            elif float(slot["max_time"]) < 120.0 and float(slot["max_time"]) > 60.0:
                pdf.set_font("Helvetica", '', 12)
                pdf.cell(48, 8, f"capped at 60 min", border=1, align='C')
            else:
                pdf.cell(48, 8, f"{slot['max_time']} minutes", border=1, align='C')
            pdf.ln()
    pdf.ln(10)
    #copilot generated the rest of this function, it mirrors the print statements in mode2 and mode3, but uses pdf.cell() instead of print() to write to the PDF. i honed it a bit thoguh.
    #outside section
    pdf.set_text_color(0, 128, 0)  # Green color for Best Outside Hours
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"Best Outside Hours for {date_input} in {city}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(40, 8, "Hour", border=1, fill=True, align='C')
    pdf.cell(40, 8, "Min Time", border=1, fill=True, align='C')
    pdf.cell(80, 8, "Max Time", border=1, fill=True, align='C')
    pdf.cell(30, 8, "UV Index", border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_font("Helvetica", '', 12)
    if not rankedLists["outside"]:
        pdf.cell(0, 8, "No Best Outside Hours available.", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    else:
        for slot in rankedLists["outside"]:
            pdf.cell(40, 8, f"{slot['hour']}:00", border=1, align='C')
            pdf.cell(40, 8, f"{slot['min_time']} minutes", border=1, align='C')
            if slot["max_time"] == "as much as you want, uv is going to only decline after this hour" or slot["max_time"] == "capped at 60 minutes, uv is going to increase after this hour":
                pdf.set_font("Helvetica", 'I', 8)  # Italic and smaller font for the note
                pdf.cell(80, 8, f"{slot['max_time']}", border=1, align='C')
                pdf.set_font("Helvetica", '', 12)  # Reset to normal font
            else:
                pdf.cell(80, 8, f"{slot['max_time']} minutes", border=1, align='C')
            pdf.set_font("Helvetica", '', 12)
            pdf.cell(30, 8, f"{slot['uv']}", border=1, align='C')
            pdf.ln()
    pdf.ln(10)
    pdf.add_page()
    pdf.add_action
    #no tanning section    
    pdf.set_text_color(128, 128, 128)  # Gray color for No Tanning Hours
    pdf.set_font("Helvetica", 'B', 16)

    pdf.cell(0, 10, f"No Tanning Hours for {date_input} in {city}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(42, 8, "Hour", border=1, fill=True, align='C')
    pdf.cell(30, 8, "UV Index", border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_font("Helvetica", '', 12)
    if not rankedLists["no_tanning"]:
        pdf.cell(0, 8, "No No Tanning Hours available.", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    else:
        for slot in rankedLists["no_tanning"]:
            pdf.cell(42, 8, f"{slot['hour']}:00", border=1, align='C')
            pdf.cell(30, 8, f"UV: {slot['uv']}", border=1, align='C')
            pdf.ln()
    pdf.ln(10)
    #dangerous section
    pdf.set_text_color(255, 0, 0)  # Red color for Dangerous Hours
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"Dangerous Hours for {date_input} in {city}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(42, 8, "Hour", border=1, fill=True, align='C')
    pdf.cell(110, 8, "Message", border=1, fill=True, align='C')
    pdf.cell(30, 8, "UV Index", border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_font("Helvetica", '', 12)
    if not rankedLists["dangerous"]:
        pdf.cell(0, 8, "No Dangerous Hours available.", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    else:
        for slot in rankedLists["dangerous"]:
            pdf.cell(42, 8, f"{slot['hour']}:00", border=1, align='C')
            pdf.cell(110, 8, f"{slot['message']}", border=1, align='C')
            pdf.cell(30, 8, f"{slot['uv']}", border=1, align='C')
            pdf.ln()
    
    safe_date = date_input.replace("/", "-")
    filename = f"uvAdvisor_{city.lower().replace(' ', '_')}_{safe_date}.pdf"
    pdf.output(filename)
is_default_mode = len(sys.argv) > 1 and sys.argv[1].lower() == "default"

if is_default_mode:
    user_skin_type = skin.MEDIUM
    user_goal = "avoid"
    city, country = helpers.get_current_city()
    sub_mode = sys.argv[2].lower() if len(sys.argv) > 2 else "hourly"
    if sub_mode == "current":
        mode = 1
    if sub_mode == "hourly":
        mode = 2

else:
    print("Enter your skin type:")
    for s in skin:
        block = helpers.color_block(helpers.skin_colors_rgb[s])
        print(f"{s.value}. {s.name} {block}")
    user_skin_type = input("> ")
    user_skin_type = user_skin_type.strip().upper()
    # AI use: Claude wrote the block below, accepting either the skin type name (e.g. "MEDIUM")
    # or its numeric value (e.g. "3") as valid input, since the menu printed above shows both.
    if user_skin_type.isdigit():
        try:
            user_skin_type = skin(int(user_skin_type))
        except ValueError:
            user_skin_type = skin.MEDIUM
    elif user_skin_type in skin.__members__:
        user_skin_type = skin[user_skin_type]
    else:
        user_skin_type = skin.MEDIUM
    user_goal = input("Enter your goal (avoid/tan) or (a/t): ").strip().lower()
    if user_goal == 'a':
        user_goal = "avoid"
    elif user_goal == 't':
        user_goal = "tan"
    
    city = input("Enter your city: ").strip()
    country =""  # placeholder 
    mode = int(input("Enter 1 for current 2 for the intervals for today 3 for a specific day (dd/mm/yyyy):"))
country_param = f"&countryCode={country}" if country else ""
geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=10&format=json{country_param}"
response = requests.get(geo_url).json()
result = response["results"]
if len(result) > 1:
    print(f"found multiple cities named {city} please choose one of the following:")
    for i, match in enumerate(result):
        print(f"{i + 1}. {match['name']}, {match['country']}, {match['admin1']}")
    choice = int(input("Enter the number of your choice: "))
    result = result[choice - 1]
else:
    result = result[0]
lat = result["latitude"]
lon = result["longitude"]
city = result["name"]    
#get the current weather data for the specified location

if mode == 1:
    date_input, rankedLists = mode1()
elif mode == 2:
    date_input, rankedLists = mode2()
elif mode == 3:
    date_input, rankedLists = mode3()
if mode in [2, 3]:
    answer = input("Do you want to generate a PDF report? (y/n): ").strip().lower()
    if answer == 'y':
        create_pdf(date_input, rankedLists, city, user_skin_type, user_goal)
else:
    print("PDF report generation skipped.")
    
