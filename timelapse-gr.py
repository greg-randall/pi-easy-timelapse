import time
from datetime import datetime
import os
import os.path
import re
import exifread
import math  
#from ftplib import FTP
#from ftpconfig import * #credentials for ftp. done this way to keep them from getting added to git


min_shutter_speed = 200 * 1000000 #200 seconds for the hq cam, 6 for v2 cam
image_x = 4056 #hq cam res
image_y = 3040

ideal_exposure = 125
delta_from_ideal = 10
isos = [200, 320, 400, 500, 640, 800]


def shoot_photo(ss,iso,w,h,filename):
    os.system('raspistill -n -awb sun -ss '+ str(ss) +' -w '+ str(w) +' -h '+ str(h) +' -ISO '+ str(iso) +' -o '+ filename)
    return True

def shoot_photo_auto(ev,w,h,filename):
    command = 'raspistill -n -awb sun -ev '+ str(ev) +' -w '+ str(w) +' -h '+ str(h) +' -o '+ filename
    #print(command)
    os.system(command)
    return True

def check_exposure (filename):
    os.system('convert '+ filename +' -set colorspace Gray -resize 1x1 -format %c histogram:info:- > info.txt')
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



start_time = round(time.time(),0) #time how long this takes

#shoot a test exposure
print('testing exposures!')
shoot_photo_auto(0,1296,976,'test.jpg')
exposure = check_exposure('test.jpg')

#see if the test exposure is inside of parameters
if (ideal_exposure + delta_from_ideal) > exposure > (ideal_exposure - delta_from_ideal):
    mode='automatic'
    print('exposure is '+ str(exposure) +'/255 which is within parameters!')
    ss_micro=''
    iso=''
    trials=''
else:#have to set exposure manually
    
    mode='manual'
    print('exposure is at '+ str(exposure) +'/255 which is outside parameters!')
    ss = get_exif('test.jpg') #getting exif shutter speed 
    print('camera chose ' + str(round(ss,3)) +' seconds for the shutter speed.')
    ss_micro = ss * 1000000
    iso=100


    
    print('---------------------------------------------')
    trials = 1
    while (ideal_exposure + delta_from_ideal) > exposure > (ideal_exposure - delta_from_ideal): #while the exposure is unacceptable try new exposures
        
        if exposure<=0:
            exposure=1
        
        adj=(1-math.log(exposure,125))*25
        
        print (str(trials)+':')      
        if adj>=0: #exposure is too dark
            if adj<1.25:
                adj=1.25
            print ('too dark! multipliying shutter speed by '+str(round(adj,2)))
            ss_micro = adj*ss_micro
        else: #exposure is too light
            if adj>-1.25:
                adj=-1.25
            print ('too light! dividing shutter speed by '+str(round(adj,2)))
            ss_micro = ss_micro/abs(adj)
           
        

        if ss_micro>=min_shutter_speed:
            ss_micro=min_shutter_speed
            print('min shutter speed hit - ' + str(round(ss_micro/1000000,3)) +' seconds')
            break
        
        print('trying ' + str(round(ss_micro/1000000,3))+' seconds')
        shoot_photo(ss_micro,iso,1296,976,'test.jpg')
        
        exposure = check_exposure('test.jpg')
        print('results: '+ str(exposure) +'/255')
        

        trials+=1
        if trials>=5:
            print('breaking after 5 trials')
            break
        print('---------------------------------------------')
        
print('shooting photo')
filename = 'hq_'+str(int(time.time())) + '.jpg'
print(mode)

if mode=='manual':
    shoot_photo(ss_micro,iso,image_x,image_y,filename)
else:
    shoot_photo_auto(0,image_x,image_y,filename)
    
final_exposure = check_exposure(filename)
print (filename +' shot! '+ str(final_exposure) +'/255')

#logging
f=open("timelapse-log-v2.txt", "a+")
timestamp = dateTimeObj = datetime.now()
end_time=round(time.time(),0)


seconds_elapsed = end_time-start_time

time_elapsed = str(int((seconds_elapsed-(seconds_elapsed%60))/60))+':'+str(int(seconds_elapsed%60))


f.write(str(timestamp) + ','+ mode +',' + str(final_exposure)+','+str(ss_micro)+','+str(iso)+','+ time_elapsed +','+str(trials)+'\n')
f.close()
print('---------------------------------------------')

print('finally done shooting. everything took ' + time_elapsed +' minutes:seconds')


#print('starting ftp')

#try: 
#    ftp = FTP()
#    ftp.connect(SERVER, PORT)
#    ftp.login(USER, PASS)
#    ftp.set_debuglevel(3)
#    ftp.storbinary('STOR ' + filename, open(filename, 'rb')) #upload the file
#    ftp.storbinary('STOR timelapse-log-v2.txt', open('timelapse-log-v2.txt', 'rb')) #upload the file
#    os.rename(filename, "uploaded/" + filename)
#    ftp.close()
#except:
#    print "\nCould not access " + SERVER + ". Will retry shortly." #if we can't get to the server then list that it failed

os.system('rm info.txt')
os.system('rm test.jpg')
