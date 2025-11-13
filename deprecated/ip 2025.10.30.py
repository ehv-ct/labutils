
import subprocess

#Run mokucli list in command line and store output
output = subprocess.run("mokucli list", capture_output=True, text=True)

#Store Moku device names and ip addresses in a dictionary 
elements = output.stdout.split()
device_elements = elements[7:]
device_ip_dict = {}

for k in range(len(device_elements)):
    if k%5 == 0:
        index = int(k/5 + 1)
        device_ip_dict[str(index)] = [device_elements[k], device_elements[k+4]]

#Proceed only if dictionary is not empty i.e. at least one device is found
if bool(device_ip_dict):

    #Output Moku devices and IP addresses in an ordered list
    print('Moku devices and IP addresses are as follows:\n')
    [print(f"{key}. {value[0]}: {value[1]}") for key, value in device_ip_dict.items()]

    #Ask user to select a device and store the corresponding IP address
    check = True
    while check: 
        x = input('Please type in the number of the moku device you would like to connect to: ')
        try: 
            if int(x) <= len(device_elements)/5 and int(x) > 0:
                check = False

            else:
                print('Invalid number, please pick an index from the list of devices. \n')

        except Exception as e:
            print(f"An error occurred: {e}")

    ip = device_ip_dict[str(x)][1]

    #Remove portion after and including % symbol at the end of IP address
    pos = ip.find('%')
    if pos != -1:
        ip = ip[:pos]

    #Return chosen IP address
    print('IP address has been set to', ip)

#Otherwise state that no devices have been found
else:
    print('No devices found.')



