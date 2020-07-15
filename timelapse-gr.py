import time
from datetime import datetime
import os
import os.path
from os import path
import re
import exifread
import math
import mmap

from ftplib import FTP
from ftpconfig import * #credentials for ftp. done this way to keep them from getting added to git

#settings for hq cam
#min_shutter_speed = 200 * 1000000 #200 seconds for the hq cam
#image_x = 4056 #hq cam res
#image_y = 3040

#settings for v2 cam
min_shutter_speed = 6 * 1000000 #6seconds for v2 cam
image_x = 3280 #v2 cam res
image_y = 2464


shoot_raw = True
ideal_exposure = 120
delta_from_ideal = 10
isos = [200, 320, 400, 500, 640, 800]
minimum_adjustment_multiplier = 1.33 



def shoot_photo(ss,iso,w,h,shoot_raw,filename):
    if shoot_raw:
        raw = ' --raw '
    else:
        raw = ''
    os.system(f"raspistill {raw} -hf -vf -n -awb sun -ss {ss} -w {w} -h {h} -ISO {iso} -o {filename}")
    return True

def shoot_photo_auto(ev,w,h,shoot_raw,filename):
    if shoot_raw:
        raw = ' --raw '
    else:
        raw = ''
    os.system(f"raspistill {raw} -hf -vf -n -awb sun -ev {ev} -w {w} -h {h} -o {filename}")
    return True

def check_exposure (filename):
    os.system(f"convert {filename} -set colorspace Gray -resize 1x1 -format %c histogram:info:- > info.txt")
    f = open('info.txt','r')
    exposure = f.read()
    f.close()
    exposure = re.search(r'\(\d{1,3}\)',exposure)
    exposure = re.search(r'\d{1,3}',exposure.group())
    return int(exposure.group())

def get_exif(filename):
    f = open(filename,'rb')
    data = exifread.process_file(f)
    ss_raw = str(data['EXIF ExposureTime'])
    ss_split = ss_raw.split('/')
    f.close()
    return (float(ss_split[0])/float(ss_split[1]))

def getlastline(fname):
    with open(fname) as source:
        mapping = mmap.mmap(source.fileno(), 0, prot=mmap.PROT_READ)
    return mapping[mapping.rfind(b'\n',0,-1)+1:]


start_time = int(time.time()) #time how long this takes


print(f"testing exposures! we want to be as close to {ideal_exposure}/255 as possible.")


if path.exists('log_v3.txt'):
    print('log file found, checking for previous exposure data')
    previous_settings=str(getlastline('log_v3.txt'))
    previous_settings = previous_settings.split(',')
    #print(previous_settings)
    if previous_settings[1]=='automatic':
        print('previous exposure was automatic, going to do that again')
        shoot_photo_auto(0,1296,976,False,'test.jpg')
        exposure = check_exposure('test.jpg')
        try_previous=False
    else:
        p_ss_micro=int(float(previous_settings[3]))
        p_iso=int(previous_settings[4])
        shoot_photo(p_ss_micro,p_iso,1296,976,False,'test.jpg')
        exposure = check_exposure('test.jpg')
        print(f"previous exposure was manual, trying previous settings {round(p_ss_micro/1000000,3)} seconds at {p_iso}")
        print(f"exposure is {exposure}/255")
        try_previous=True
    
else:
    print('no previous exposures foud, testing')
    shoot_photo_auto(0,1296,976,False,'test.jpg')
    exposure = check_exposure('test.jpg')
    try_previous=False


#see if the test exposure is inside of parameters
if (ideal_exposure + delta_from_ideal) > exposure > (ideal_exposure - delta_from_ideal) and not try_previous:
    mode='automatic'
    print(f"exposure is {exposure}/255 which is within parameters!")
    ss_micro=''
    iso=''
    trials=''
else:#have to set exposure manually
    mode='manual'
    min_exposure_first_try=True
    
    if try_previous:
        ss_micro = p_ss_micro
        iso=p_iso       
    else:
        print(f"exposure is {exposure}/255 which is within parameters!")
        ss = get_exif('test.jpg') #getting exif shutter speed 
        print(f"camera chose {round(ss,3)} seconds for the shutter speed.")
        ss_micro = ss * 1000000
        iso=100

    print('---------------------------------------------')
    trials = 1
    min_exposure_hit = False
    while (ideal_exposure + delta_from_ideal) < exposure or exposure < (ideal_exposure - delta_from_ideal): #while the exposure is unacceptable try new exposures
        
        if exposure<=0:
            exposure=1
        
        adj=(1-math.log(exposure,ideal_exposure))*12
        
        print (f"{trials}:")      
        if adj>=0: #exposure is too dark
            if adj<minimum_adjustment_multiplier:
                adj=minimum_adjustment_multiplier
            print (f"too dark! multipliying shutter speed by {round(adj,2)}")
            ss_micro = adj*ss_micro
        else: #exposure is too light
            if adj>(minimum_adjustment_multiplier*-1):
                adj=(minimum_adjustment_multiplier*-1)
            print (f"too light! dividing shutter speed by {round(adj,2)}")
            ss_micro = ss_micro/abs(adj)
           
        

        if ss_micro>=min_shutter_speed: #in case the minimum exposure is met set it to the minimum
            ss_micro=min_shutter_speed
            min_exposure_first_try = False #only let that happen once though, 
        
        if not min_exposure_first_try:
            print(f"min shutter speed hit - {round(ss_micro/1000000,3)} seconds")
            min_exposure_hit = True
            break
        
        print(f"trying {round(ss_micro/1000000,3)} seconds")
        shoot_photo(ss_micro,iso,1296,976,False,'test.jpg')
        
        exposure = check_exposure('test.jpg')
        print(f"results: {exposure}/255")
        

        trials+=1
        if trials>=5:
            print('breaking after 5 trials')
            break

    if exposure < (ideal_exposure - delta_from_ideal) and min_shutter_speed==ss_micro:
        print('need to bump iso :(')
        for iso in isos:
            print (f"trying {iso} iso at {round(ss_micro/1000000,3)} seconds")
            shoot_photo(ss_micro,iso,1296,976,False,'test.jpg')
            exposure = check_exposure('test.jpg')
            print(f"exposure is at {exposure}/255")
            if exposure > (ideal_exposure - delta_from_ideal):
                print(f"workable iso discovered {iso}")
                break
        #if the loop ends without finding an iso, it'll just shoot a shot with the highest iso.
        if iso==isos[-1]:
            print('highest iso & longest shutter speed hit. going to shoot a photo anyway') 
print('---------------------------------------------')

print('shooting photo')
filename_time = int(time.time())
filename = f"{filename_time}.jpg"
filename_dng = f"{filename_time}.dng"



if mode=='manual':
    shoot_photo(ss_micro,iso,image_x,image_y,True,filename)
else:
    shoot_photo_auto(0,image_x,image_y,True,filename)
    
final_exposure = check_exposure(filename)
print (f"{filename} shot! {final_exposure}/255")

print('---------------------------------------------')
if shoot_raw:
    print('extracting DNG!')
    command = f"python3 PyDNG/examples/utility.py {filename}"
    os.system(command)

    print('extracted. removing dng from jpg')
    os.system(f"convert {filename} {filename}")
    print('---------------------------------------------')
#logging
f=open("log_v3.txt", "a+")
timestamp = dateTimeObj = datetime.now()
end_time=int(time.time())


seconds_elapsed = end_time-start_time

time_elapsed = f"{(seconds_elapsed-(seconds_elapsed%60))/60}:{seconds_elapsed%60}"


f.write(f"{timestamp},{mode},{final_exposure},{ss_micro},{iso},{time_elapsed},{trials}\n")
f.close()


print(f"finally done shooting. everything took {time_elapsed} minutes:seconds")    
print('---------------------------------------------')
print('starting ftp')


try: 
    ftp = FTP(SERVER, USER, PASS, timeout=15)
    ftp.set_debuglevel(3)
    ftp.storbinary('STOR ' + filename, open(filename, 'rb')) #upload the file
    ftp.storbinary('STOR ' + filename_dng, open(filename_dng, 'rb')) #upload the file
    ftp.storbinary('STOR log_v3.txt', open('log_v3.txt', 'rb')) #upload the file
    ftp.close()
    ftp_worked=True
except:
    print (f"Could not access {SERVER}.") #if we can't get to the server then list that it failed
    ftp_worked=False
print('---------------------------------------------')
if ftp_worked:
    print(f"ftp worked, deleting local image copies {filename} & {filename_dng}")
    os.system(f"rm {filename}")
    os.system(f"rm {filename_dng}")

os.system('rm info.txt')
os.system('rm test.jpg')
