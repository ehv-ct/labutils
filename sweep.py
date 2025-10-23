import numpy as np
import time
import sys
import yaml
from moku.instruments import ArbitraryWaveformGenerator

#Copy paste IP address of Moku box from liquid instruments interface (right-click on connected box)
ip = '[fe80::c2ce:d8f3:9e1f:645]'

#Set default parameters
amp = 1 #Amplitude of waveform
base_freq = 1 #Frequency at time 0
T = 5 #duration of sweep
no_points = 1000 #Number of datapoints in generated waveform 
no_dead_cycles = 2 #Number of dead cycles  when using pulsed mode
max_time = 5 #Maximum time for program to run (after a waveform is generated)

#Read configuration from yaml file
try: 
    with open('conf.yaml', 'r') as file:
        loaded_conf = yaml.safe_load(file)

    print("Data read from 'conf.yaml':")
    print(loaded_conf)
    amp = loaded_conf['amp']
    base_freq = loaded_conf['base frequency']
    T = loaded_conf['sweep duration']
    no_points = loaded_conf['number of points']
    no_dead_cycles = loaded_conf['number of dead cycles between pulses']
    max_time = loaded_conf['program duration']


except Exception as e:
    print(f"An error occurred in trying to load conf.yaml: {e}")
    print('Using default parameters.')

#Save configuration to yaml file
conf = {
    'amp': amp,
    'base frequency': base_freq,
    'sweep duration' : T,
    'number of points': no_points,
    'number of dead cycles between pulses': no_dead_cycles,
    'program duration': max_time

}

with open('conf.yaml','w') as file:
    yaml.dump(conf, file)
print('Configuration has been saved to conf.yaml')



t = np.linspace(0, T, no_points)  # Evaluate waveform at no_points points over T seconds

#Swept sine waveform generation

R = 1 #Variable controlling speed of sweep
y = np.sin(2*np.pi*(-1+(2**(R*t)))/(R*np.log(2))) #Swept sine waveform formula

#Plot waveform for reference
import matplotlib.pyplot as plt
plt.plot(t,y)
plt.xlabel('Time (s)')
plt.ylabel('Voltage (V)')
plt.title('Generated Pulse sent to Moku')
plt.show()

def off():
    i.enable_output(1, enable=False)


# Connect to your Moku by its ip address ip
# force_connect will overtake an existing connection
i = ArbitraryWaveformGenerator(ip, force_connect=True)

try:
    # Load and configure the waveform.
    i.generate_waveform(channel=1, sample_rate='Auto',
                        lut_data=list(y), frequency=base_freq,
                        amplitude=amp)


    # Set channel 1 to pulse mode
    # 2 dead cycles at 0Vpp
    i.pulse_modulate(channel=1, dead_cycles=no_dead_cycles, dead_voltage=0)

    print('Printing summary of current state: \n')
    print(i.summary())

    time_elapsed = 0
    while time_elapsed < max_time:
        print('Running... Press Ctrl + C to stop.')
        time.sleep(2)
        time_elapsed += 2
    
    print('More than ', max_time,'s elasped. Terminating program.')


except KeyboardInterrupt:
    print("Program to be terminated at user's request.")

finally:
    i.enable_output(1, enable=False)

    print('Printing endstate summary: \n')
    print(i.summary())

    i.relinquish_ownership()
    sys.exit("Program terminated.")
