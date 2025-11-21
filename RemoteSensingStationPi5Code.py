import numpy as np
import matplotlib.pyplot as plt
from enum import Enum, auto
import time
import urllib.request
from matplotlib.animation import FuncAnimation
import asyncio
import aiosmtplib
from email.message import EmailMessage
import pylab
import matplotlib.animation as animation
import datetime
import os
from matplotlib.dates  import DateFormatter, MinuteLocator
import board
import busio
import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd  #the code above here imports all the packages and libraries that we required in our code

class DataHandling:
"""
Read in the web adresses for the different measurements from the sensors and extract the different measurements for each sensor. The temperature values for the DHT22 sensor are converted from Fahrenheit to degrees celcius and the results are returned as floats for use for calculations.  
"""

    def __init__(self, address_temp, address_humid, address_temp1, address_temp2):
        self.address_temp = address_temp
        self.address_humid = address_humid
        self.address_temp1 = address_temp1
        self.address_temp2 = address_temp2
       
    def get_data(self):
        data_temp = None
        data_humid = None
        data_temp1 = None
        data_temp2 = None
      
        now = datetime.datetime.now()


        try:
            with urllib.request.urlopen(self.address_temp) as response:
# Read in the temperature values from the DHT22 sensor
                temp_str = response.read()   
# Convert from fahrenheit to celcius
                data_temp  =( float( temp_str) - 32)  * (5/9)  
        except Exception as e:
            print(f"Error reading {self.address_temp}: {e}")

        try:
            with urllib.request.urlopen(self.address_humid) as response:
#Read in the humidity values from the DHT22 sensor
                data_2 = response.read() 
# Remove any symbols as to just leave the numbers we want for plotting and calculations in risk score sections
                humid_str = data_2.decode('utf-8').strip() 
                data_humid = humid_str
        except Exception as e:
            print(f"Error reading {self.address_humid}: {e}")
        try:
            with urllib.request.urlopen(self.address_temp1) as response:
                temp_str1 = response.read() 
# Read in the temperature value from the first DS18B20 sensor
                data_temp1 = (float(temp_str1))
        except Exception as e:
            print(f"Error reading {self.address_temp1}: {e}")
        try:
            with urllib.request.urlopen(self.address_temp2) as response:
# Read in the temperature value from the second DS18B20 sensor
                temp_str2 = response.read()
                data_temp2 = (float(temp_str2))
        except Exception as e:
            print(f"Error reading {self.address_temp2}: {e}")
        
        return float(data_temp), float(data_humid), now,float( data_temp1), float(data_temp2)  #returns all the temp and hum data

class DataPlotter:
    """
    Reads sensor measurement data from a CSV file and plots temperature and humidity
    in real time using a live-updating matplotlib graph.
    """
    def __init__(self):
  
        # Arrays to hold parsed time, temperature, and humidity 
        self.timeValues = []
        self.tempValues = []
        self.humValues = []
        plt.ion()

       
        self.fig, self.ax_temp = plt.subplots()
        self.ax_temp.set_xlabel("Current Time [H:m:s]")
        self.ax_temp.set_ylabel("Temperature (degrees)")  #creates axis labels and the figure

        self.temp_line, = self.ax_temp.plot([], [], 'r-', label="Temperature (°C)")
        self.ax_temp.tick_params(axis='y', labelcolor='r') #creates a temp line plot (that is empty at first)

        self.ax_hum = self.ax_temp.twinx()  
        self.ax_hum.set_ylabel("Humidity (%)")  #creates a twin axis so we can have a second humidty y axis on the same plot

        self.hum_line, = self.ax_hum.plot([], [], 'b-', label="Humidity (%)")
        self.ax_hum.tick_params(axis='y', labelcolor='b')  #same as temp above, creates humidity line thats empty at first (as we are just initialising atm)

        self.ax_temp.set_title("Live Temperature and Humidity (ESP8266 + DHT22)")
        self.ax_temp.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        self.ax_temp.xaxis.set_major_locator(MinuteLocator(interval=1)) 
        self.fig.legend(loc="upper left") #adds things like title and legend



    def plot_updated_data(self, temp, humid):
        if temp is not None and humid is not None:
            now = datetime.datetime.now() #only updates if both readings are valid and also records live time

            self.timeValues.append(now)
            self.tempValues.append(temp)
            self.humValues.append(humid)  #appends data to the lists initialised above

            self.temp_line.set_data(self.timeValues, self.tempValues)
            self.hum_line.set_data(self.timeValues, self.humValues)  #fills in the lines (that were created empty above) with the data stored in the array

            self.ax_temp.set_ylim(0, 100)
            self.ax_hum.set_ylim(0, 100)   #sets y axis limits to the full possible range
 
            window = 20
            self.ax_temp.set_xlim(self.timeValues[max(0, len(self.timeValues) - window)],self.timeValues[-1]) #this only displays the most recent 20 readings live, as to avoid a massive plot that lags and loses fine detail

            plt.gcf().autofmt_xdate()  #roates x axis labels for ease of reading

            plt.pause(0.01) #allows plot to refresh


class states(Enum):
    
    '''
    Defines the states used within the FSM. The enum provides named constants for each state in the FSM. They range in danger         levels, from nominal to critical, plus a recovering state
    
    '''
    Nominal = auto()
    Warning = auto()
    Danger = auto()
    Critical = auto()
    Recovering = auto()    #provides named constants for each state in the FSM


class StateMachine:
    
    '''
    This class is the main code for the FSM, which initialises into a nominal state upon start, and records the time as               last_transition. It contains two methods, one to define what happens when moving between states (the transition method) and       the update class which outlines what limits and conditions have to be met in order to actually transition.
    '''
    def __init__(self):
        '''
        Variables: 
        self.state = the state of the system 
        self.last_transition = a timestamp to remember the time since last transition
        '''
        self.state = states.Nominal
        self.last_transition = time.time()   #defines current time and nominal starting state

    def transition(self, new_state):
        '''
        This method is called to transition between states, prints a message outlining the transition that is occuring, and               resets the variables self.state and self.last_transition 
        '''
        if new_state != self.state:  #if the new state and current (self.state) doesnt match then transition 
            print(f"[{time.strftime('%X')}] {self.state.name} → {new_state.name}")  #print statment for checking
            self.state = new_state   #updates the current state (self.state, to the new state passed in)
            self.last_transition = time.time()    #updates time of last transition 
  
    def update(self, risk_score):
        '''
        This is the main method for the FSM and outlines what risk score is needed to transition between states, and also what           states have to have occured previously.
        
        The risk score is passed into the method, and calculated in a different class
        
        '''
        if self.state == states.Nominal:   #defines what bounds need to be broken to leave the nominal state (anything above 0.4)
            if risk_score > 0.4:
                self.transition(states.Warning) #updates state to warning with transition method 

        elif self.state == states.Warning: #defines bounds needed to change out of warning state 
            if risk_score > 0.7:
                self.transition(states.Danger)  #if risk is high enough, transition to next state (danger state)
            elif risk_score < 0.2:
                self.transition(states.Nominal)  #but if the risk score recovers and drops low enough, enter back into nominal state

        elif self.state == states.Danger:  #defines bounds needed to change out of danger state 

            if risk_score > 0.9:   #if risk score is high enough then critical state is entered
                self.transition(states.Critical)
            elif risk_score < 0.5:   #if risk score starts to drop, the the state is recovering (even though a score of 0.5 would put you in a warning state, hence the utility of FSM, as it uses context)
                self.transition(states.Recovering)  

        elif self.state == states.Critical:  #defines bounds needed to change out of critical state 
            if risk_score < 0.7:   
                self.transition(states.Recovering)  #if risk score is low enough, enter recovering state

        elif self.state == states.Recovering:

            if risk_score < 0.3:    #defines bounds to re-enter nominal state and go back into a danger state
                self.transition(states.Nominal)
            elif risk_score > 0.7:
                self.transition(states.Danger)

        return self.state.name  #returns the name of state that the system is in, i.e. nominal, danger, recovering etc


class RiskCalc:

    '''
    This class contains the method that calculates the risk score based on the heat index from the national weather service
    
    ''' 
    
    def risk_analysis(self, temp_c, humidity):
        
        '''
        Variables passed in:
        
        temp_c: the temperature in degrees celcius parsed from the webserver in the get_data method above
        humidity: the relative humidity also obtained by parsing the webserver in the get_data method 
        
        '''

        temp_f = temp_c * 9/5 + 32  #convers temp from celcius to farenheight (which is a little goofy since the sensor measures in F, we convert to c, just to turn back to F)
        rh = humidity

        if temp_f < 80:
            hi_f = temp_f   #this condition is due to the lower limit for the heat index calculations (see report for explanation)
            
        else:
            hi_f = (-42.379 + 2.04901523 * temp_f + 10.14333127 * rh
                    - 0.22475541 * temp_f * rh - 6.83783e-3 * temp_f**2
                    - 5.481717e-2 * rh**2 + 1.22874e-3 * temp_f**2 * rh
                    + 8.5282e-4 * temp_f * rh**2 - 1.99e-6 * temp_f**2 * rh**2)     #national weather servivce heat index calc

            if (rh < 13) and (80 <= temp_f <= 112):
                adj = ((13 - rh) / 4) * ((17 - abs(temp_f - 95)) / 17) ** 0.5
                hi_f -= adj   #the adjustment outlines if the temp is in the low region but with very low humidity
            elif (rh > 85) and (80 <= temp_f <= 87):
                adj = ((rh - 85) / 10) * ((87 - temp_f) / 5)
                hi_f += adj     #this adjustment accounts for the high humidty, low temperature region outlined by the national weather service 
  
        hi_c = (hi_f - 32) * 5/9   #converts the temperature back into celcius 

        hi_min, hi_max = 20.0, 50.0
        risk_score = (hi_c - hi_min) / (hi_max - hi_min)
        risk_score = max(0.0, min(1.0, risk_score))   #this sets bounds for our temperature range (20 - 50) which then scales the heat index to give a 'normalised' risk_score that falls between 0 and 1 which our FSM uses

        return round(hi_c, 2), round(risk_score, 3)   #returns the heat index and risk_score, rounded to 2 and 3 decimal places respectively



class SendEmail:
    
    '''
    This is the class that is responsible for sending the emails once a warning, danger or critical state is reached with our machine 
    '''
    def __init__(self, sending_address, app_password, receiving_address):
        
        '''
        The variables initialised in our main are the email addresses that are sending and receiving the email, as well as an app password to be able to send the email, but not have full access to my account.
        '''
        self.sending_address = sending_address
        self.app_password = app_password
        self.receiving_address = receiving_address   #initialises the emails and app password to be used in later methods

    async def send_email_alert(self, subject, content):
        
        '''
        Here, the subject and content is passed in depending on the state, and then the method sends the email to the person who wants to track the temperature/humidity
        
        async def is used so that other methods and classes can be run concurrently, as to try and avoid a bottleneck
        
        '''
        
        message = EmailMessage()
        message["From"] = self.sending_address
        message["To"] = self.receiving_address
        message["Subject"] = subject
        message.set_content(content)   #sets the content, subject and from who to who

        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=self.sending_address,
            password=self.app_password,      #uses the gmail smtp server to send the email
        )

        print(f"Email sent: {subject}")  

async def main():
    
    '''
    This is the main function that is called to run our code
    
    The structure is as follows:
        1) Initialses the different classes, passing in any required data (such as the URLs to parse the webserver)
        2) Sets up a while loop to continuously parse data from the webserver, and pass it into subsequent classes and methods to upodate our FSM, LCD screen, live plotter, and (not quite due to lab Wi-Fi) the email alerts.
        
        We utilised async as to avoid bottlenecking if any classes or methods got stuck on a task (especially the email sender)
    '''
    
    data = DataHandling("http://192.168.0.7/temp", "http://192.168.0.7/humidity", 'http://192.168.0.7/ds1', 'http://192.168.0.7/ds2')
    plotter = DataPlotter()
    risk = RiskCalc()
    zones = StateMachine()
    email = SendEmail('bentullett21@gmail.com', 'qehjityxsjxkwvqo', 'bentullett21@gmail.com')  #initialises the classes

    warning_alert_sent = False
    danger_alert_sent = False
    critical_alert_sent = False   #creates variables to log whether or not email alerts have been sent, as to avoid accidentally spamming 

    while True:
        try:

            reading_temp, reading_humid, times, temp1, temp2  = data.get_data()  #parses web server for temp and hum data
            print(reading_temp)
            print(temp1)
            print(temp2)
            print(reading_humid)
            print(times)  #prints everything to terminal just so we can see whats happening numerically in the lab 
            plotter.plot_updated_data(reading_temp, reading_humid)  #updates live plotter
            Hi_c,  risk_value = risk.risk_analysis(reading_temp, reading_humid) #calculates the heat index and risk score
            state_of_system = zones.update(risk_value) #updates the FSM based on the risk score calculated above
            print(state_of_system)  #prints state to terminal again for sanity check
            
            
            line = f'{reading_temp},{temp1},{temp2},{reading_humid},{times},{Hi_c},{risk_value},{state_of_system}\n'
            with open('DATAFILE.txt', 'a') as f:
                f.write(line)  #saves all the data that has just been gathered and calcualted to a txt file for easy analysis

            lcd_columns = 16   #the code from this pount down to the sleep line, is to live display our temperature and humidity on the LCD screen connected to the raspberry pi. It is colour coded to the state that the FSM is in.
            lcd_rows = 2
            i2c = busio.I2C(board.SCL, board.SDA)
            lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)

            if state_of_system == 'Danger':
                lcd.color = [255, 0, 0]
                lcd.message = f'System Danger\n{round(reading_temp,2)}C , {round(reading_humid,2)}%'
                #if danger_alert_sent = False:
                    #email.send_email_alert('Danger State Detected', f'A danger state has been detected with readings of                               {reading_temp} °C and {reading_humid}% relative humidity'
                    #danger_alert_sent = True
                                
            if state_of_system == 'Nominal':
                lcd.color = [0,255,0]
                lcd.message = f'System Nominal\n{round(reading_temp,2)}C, {round(reading_humid,2)}%'

            if state_of_system == 'Warning':
                lcd.color = [255, 255, 50]
                lcd.message = f'System Warning\n:{round(reading_temp,2)}C ,  {round(reading_humid,2)}%'
                #if warning_alert_sent = False:
                    #email.send_email_alert('Warning State Detected', f'A warning state has been detected with readings of                               {reading_temp} °C and {reading_humid}% relative humidity'
                    #warning_alert_sent = True

            if state_of_system == 'Critical':
                lcd.color = [153,0 ,153]
                lcd.message = f'System Critical\n{round(reading_temp,2)}C ,{round(reading_humid,2)}%'
                #if critical_alert_sent = False:
                    #email.send_email_alert('Critical State Detected', f'A critical state has been detected with readings of                               {reading_temp} °C and {reading_humid}% relative humidity'
                    #critical_alert_sent = True

            if state_of_system == 'Recovering':
                lcd.color =[ 100,180, 255]
                lcd.message = f'System Recovering\n{round(reading_temp,2)}C , {round(reading_humid,2)}
     

            await asyncio.sleep(1)   #waits a second 
   
        except KeyboardInterrupt:
            plotter.fig.savefig('Plot.pdf')
            break    #saves the final plot once the user on the pi 5 exits the code with ctrl+c

if __name__ == "__main__":
    asyncio.run(main())  #runs the main function 