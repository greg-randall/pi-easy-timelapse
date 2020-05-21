import time
from datetime import datetime
import os
import os.path
import re
import exifread
from ftplib import FTP
from ftpconfig import * #credentials for ftp. done this way to keep them from getting added to git

hdr=False

ideal_exposure = 125
delta_from_ideal = 10
isos = [200, 320, 400, 500, 640, 800] 

def shoot_photo(ss,iso,w,h,filename):
    os.system('raspistill -awb sun  -hf -vf -ss '+ str(ss) +' -w '+ str(w) +' -h '+ str(h) +' -ISO '+ str(iso) +' -o '+ filename)
    return True

def shoot_photo_auto(ev,w,h,filename):
    command = 'raspistill -awb sun  -hf -vf -ev '+ str(ev) +' -w '+ str(w) +' -h '+ str(h) +' -o '+ filename
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

def create_hdr(output_name):
    #raspistill  -ev 0 -o hdr-test/1.jpg
    #raspistill  -ev 20 -o hdr-test/2.jpg
    #raspistill  -ev -20 -o hdr-test/3.jpg
    #pfsinme *.jpg | pfssize --maxx 600 | pfshdrcalibrate --verbose -r linear --bpp 16 | pfstmo_reinhard05 | pfsout test.jpg
    #sudo apt install ufraw-batch
    os.system( 'pfsinme hdr1.jpg hdr2.jpg hdr3.jpg | pfshdrcalibrate -r linear --bpp 16 | pfstmo_reinhard05 | pfsout '+ output_name )
    return (True)

start_time = time.time()

print('testing exposures!')
shoot_photo_auto(0,1296,976,'test.jpg')
exposure = check_exposure('test.jpg')

if (ideal_exposure + delta_from_ideal) > exposure > (ideal_exposure - delta_from_ideal):
    print('exposure is '+ str(exposure) +'/255 which is within parameters!')
    filename = str(int(time.time())) + '.jpg'
    
    if hdr:
        print('hdr enabled, shooting several photos to combine')
        shoot_photo_auto(0,3280,2464,'hdr1.jpg')
        print('hdr photo 1 shot')
        shoot_photo_auto(20,3280,2464,'hdr2.jpg')
        print('hdr photo 2 shot')
        shoot_photo_auto(-20,3280,2464,'hdr3.jpg')
        print('hdr photo 3 shot')
        print('combining photos into one hdr image')
        create_hdr(filename)
        print('hdr creation finished')
    else:
        print('shooting photo')
        shoot_photo_auto(0,3280,2464,filename)

    print (filename +' shot!')
    auto = True
else:
    print('exposure is at '+ str(exposure) +'/255 which is outside parameters!')
    ss = get_exif('test.jpg')
    print('camera chose ' + str(round(ss,3)) +' seconds for the shutter speed.')

    ss_micro = ss * 1000000
    iso=100
    while exposure < (ideal_exposure - delta_from_ideal):
        ss_micro *=2

        if ss_micro>6000000:
            ss_micro=6000000
        
        print('trying ' + str(round(ss_micro/1000000,3))+' seconds')
        shoot_photo(ss_micro,iso,1296,976,'test.jpg')
        exposure = check_exposure('test.jpg')
        print('exposure is at '+ str(exposure) +'/255')

        if ss_micro>=6000000:
            break

    if exposure > (ideal_exposure - delta_from_ideal):
        if (ideal_exposure + delta_from_ideal) < exposure: #in case we overshoot our exposure go back a half stop
            print('overshot a bit. dialing back')
            
            while (ideal_exposure + delta_from_ideal) < exposure:
                ss_micro *=.75            
                print('reducing exposure, trying ' + str(round(ss_micro/1000000,5))+' seconds')
                shoot_photo(ss_micro,iso,1296,976,'test.jpg')
                exposure = check_exposure('test.jpg')
                print('exposure is at '+ str(exposure) +'/255')

        else:
            print('got it! ' + str(round(ss_micro/1000000,3))+' seconds')
        filename = str(int(time.time())) + '.jpg'
        if hdr:
            if ss_micro>=6000000:
                print('hdr enabled, but we maxed out exposure, so one shot will have to push iso.')
                shoot_photo(ss_micro,iso,3280,2464,'hdr1.jpg')
                print('hdr photo 1 shot')
                shoot_photo(ss_micro,400,3280,2464,'hdr2.jpg')
                print('hdr photo 2 shot')
                shoot_photo(ss_micro/2,iso,3280,2464,'hdr3.jpg')
                print('hdr photo 3 shot')
                print('combining photos into one hdr image')
                create_hdr(filename)
                print('hdr creation finished')
            else:
                print('hdr enabled, shooting several photos to combine')
                shoot_photo(ss_micro,iso,3280,2464,'hdr1.jpg')
                print('hdr photo 1 shot')
                if ss_micro*2>=6000000: #if the longer hdr shutter speed is greater than 6 seconds, we'll just cap it at 6 seconds
                    shoot_photo(6000000,iso,3280,2464,'hdr2.jpg')
                else:
                    shoot_photo(ss_micro*2,iso,3280,2464,'hdr2.jpg')
                print('hdr photo 2 shot')
                shoot_photo(ss_micro/2,iso,3280,2464,'hdr3.jpg')
                print('hdr photo 3 shot')
                print('combining photos into one hdr image')
                create_hdr(filename)
                print('hdr creation finished')
        else:
            print('shooting photo')
            shoot_photo(ss_micro,iso,3280,2464,filename)

        print (filename +' shot!')
    else:
        print('need to bump iso :(')
        for iso in isos:
            print ( 'trying ' + str(iso) +' iso at 6 seconds')
            shoot_photo(ss_micro,iso,1296,976,'test.jpg')
            exposure = check_exposure('test.jpg')
            print('exposure is at '+ str(exposure) +'/255')
            if exposure > (ideal_exposure - delta_from_ideal):
                print('workable iso discovered ' + str(iso))
                break
        #if the loop ends without finding an iso, it'll just shoot a shot with the highest iso.
        filename = str(int(time.time())) + '.jpg'
        if iso==800:
            print('highest iso & longest shutter speed hit. going to shoot a photo anyway')

        if hdr:
            print('hdr enabled, shooting several photos to combine')
            shoot_photo(ss_micro,iso,3280,2464,'hdr1.jpg')
            print('hdr photo 1 shot')
            shoot_photo(ss_micro/2,iso,3280,2464,'hdr2.jpg')
            print('hdr photo 2 shot')
            if iso*2<800: #if we can get away with it, we'll increase the iso for one of the HDR shots
                shoot_photo(ss_micro,iso*2,3280,2464,'hdr3.jpg')
            else: #if we already hit 800 iso, then we'll just shoot an additional shot to help average iso noise away
                print('iso already maxed out, we will shoot an extra photo for noise reduction')
                shoot_photo(ss_micro,iso,3280,2464,'hdr3.jpg')
            print('hdr photo 3 shot')
            print('combining photos into one hdr image')
            create_hdr(filename)
            print('hdr creation finished')
        else:
            print('shooting photo')
            shoot_photo(ss_micro,iso,3280,2464,filename)
            print (filename +' shot!')
    auto = False

end_time=time.time()
f=open("timelapse-log-v2.txt", "a+")

timestamp = dateTimeObj = datetime.now()

final_exposure = check_exposure(filename)

if hdr:
    hdr_note='hdr was enabled. '
else:
    hdr_note=''

if auto:
    f.write(str(timestamp) + ',auto,' + str(final_exposure)+',,,'+str( (end_time-start_time)/60 ) +'\n')
else:
    f.write(str(timestamp) + ',manual,' + str(final_exposure)+','+str(ss_micro)+','+str(iso)+','+str( (end_time-start_time)/60 ) +'\n')
f.close()
print('finally done shooting. everything took ' + str( (end_time-start_time)/60 ) +' decimal minutes')


print('starting ftp')

try: 
    ftp = FTP()
    ftp.connect(SERVER, PORT)
    ftp.login(USER, PASS)
    ftp.set_debuglevel(3)
    ftp.storbinary('STOR ' + filename, open(filename, 'rb')) #upload the file
    ftp.storbinary('STOR timelapse-log-v2.txt', open('timelapse-log-v2.txt', 'rb')) #upload the file
    os.rename(filename, "uploaded/" + filename)
    ftp.close()
except:
    print "\nCould not access " + SERVER + ". Will retry shortly." #if we can't get to the server then list that it failed

os.system('rm info.txt')
os.system('rm test.jpg')