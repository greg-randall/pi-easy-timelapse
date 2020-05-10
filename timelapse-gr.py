import time
import os
import re
import exifread
#from ftplib import FTP
#from ftpconfig import * #credentials for ftp. done this way to keep them from getting added to git


ideal_exposure = 125
delta_from_ideal = 10
isos = [200, 320, 400, 500, 640, 800] 

def shoot_photo(ss,iso,w,h,filename):
    os.system('raspistill -ss '+ str(ss) +' -w '+ str(w) +' -h '+ str(h) +' -ISO '+ str(iso) +' -o '+ filename)
    return True

def shoot_photo_auto(w,h,filename):
    os.system('raspistill -w '+ str(w) +' -h '+ str(h) +' -o '+ filename)
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


start_time = time.time()
print('testing exposures!')
shoot_photo_auto(1296,976,'test.jpg')
exposure = check_exposure('test.jpg')

if (ideal_exposure + delta_from_ideal) > exposure > (ideal_exposure - delta_from_ideal):
    print('exposure is '+ str(exposure) +'/255 which is within parameters!')
    filename = str(int(time.time())) + '.jpg'
    print('shooting photo')
    shoot_photo_auto(3280,2464,filename)
    print (filename +' shot!')
else:
    print('exposure is at '+ str(exposure) +'/255 which is outside parameters!')
    ss = get_exif('test.jpg')
    print('camera chose ' + str(round(ss,2)) +' seconds for the shutter speed.')

    ss_micro = ss * 1000000
    while exposure < (ideal_exposure - delta_from_ideal):
        ss_micro *=2

        if ss_micro>6000000:
            ss_micro=6000000
        
        print('trying ' + str(round(ss_micro/1000000,2))+' seconds')
        shoot_photo(ss_micro,100,1296,976,'test.jpg')
        exposure = check_exposure('test.jpg')
        print('exposure is at '+ str(exposure) +'/255')

        if ss_micro>=6000000:
            break

    if exposure > (ideal_exposure - delta_from_ideal):
        if (ideal_exposure + delta_from_ideal) < exposure: #in case we overshoot our exposure go back a half stop
            exposure *= 0.75 
        print('got it!' + str(round(ss_micro/1000000,2))+' seconds')
        filename = str(int(time.time())) + '.jpg'
        print('shooting photo')
        shoot_photo(ss_micro,100,3280,2464,filename)
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
        if iso==800:
            print('highest iso & longest shutter speed hit. going to shoot a photo anyway')

        filename = str(int(time.time())) + '.jpg'
        print('shooting photo')
        shoot_photo(ss_micro,iso,3280,2464,filename)
        print (filename +' shot!')

end_time=time.time()
print('finally done. everything took ' + str( (end_time-start_time)/60 ) +' decimal minutes')


#print('starting ftp')
#ftp = FTP()
#ftp.connect(SERVER, PORT)
#ftp.login(USER, PASS)
#ftp.set_debuglevel(3)
#ftp.storbinary('STOR ' + filename, open(filename, 'rb')) #upload the file
#os.rename(filename, "uploaded/" + filename)
#ftp.close()

#os.system('rm info.txt')
#os.system('rm test_exp.jpg')
    

