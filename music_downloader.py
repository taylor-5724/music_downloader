import threading
import time
import os
import re

import requests
import urllib.request
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from mutagen.mp3 import MP3  
from mutagen.easyid3 import EasyID3  
import mutagen.id3  
from mutagen.id3 import ID3, TIT2, TIT3, TALB, TPE1, TRCK, TYER

download_dir = '/home/taylor/Music/'
yt_api_key = 'AIzaSyBAv6YrslGaD61RqGd2S31wpTNarna6tbA'

artist = ''
album = ''
release_date = 0
track_name = ['']
track_number = [0]
queued_items = 0
quit_signal = 0

print ('Starting...')

#Add tracks to the download queue
tracks_added = 0
def user_interface():
    global download_dir
    global quit_signal
    global artist
    global album
    global release_date
    global track_name
    global track_number
    global queued_items
    global tracks_added
    global selenium_started
    global driver

    #Get artist name from user
    print ('Input artist name')
    artist = input()
    if artist == '':
        print ('No artist, exiting...')
        quit_signal = 3
        while selenium_started == False:
            time.sleep(0.1)
        else:
            driver.quit()
        exit()

    #Get album details from user
    print ('Input Album Name or press ENTER to skip')
    album = input()
    print ('Input album release date or press ENTER to skip')
    while (True):
        release_date = input()
        if re.match('^[0-9]*$', release_date) or release_date == '':
            break
        else:
            print ('Please use only numbers')

    #Generate file path
    download_dir  += artist + '/' + album
    print('Tracks will be placed in: ' + download_dir)
    download_dir += '/'

    #Get track info from user
    while (True):

        track_name.append('')
        tracks_added += 1

        #Get track name from user
        while (track_name[tracks_added] == ''):
            print ('Input song name or \'Q\' to quit')
            track_name[tracks_added] = input()
        if (track_name[tracks_added] == 'Q' or track_name[tracks_added] == 'q'):
            quit_signal = 1
            break
        
        #Get track number from user or assume next track
        print ('Input track number, input \'-\' to skip, or press ENTER to continue as track ' + str(track_number[tracks_added - 1] + 1))
        while (True):
            user_input = input().replace(' ', '')
            if re.match('^[0-9]*$', user_input) or user_input == '' or user_input == '-':
                if (user_input == '-'):
                    track_number.append(0)
                elif(user_input == ''):
                    track_number.append(track_number[tracks_added - 1] + 1)
                elif (user_input != ''):
                    track_number.append(int(user_input))
                break
            else:
                print ('Please only use numbers')

        queued_items += 1
        print('Added to queue')

#Thread to start Selenium so that the user doesnt have to wait
driver = 0
selenium_started = False
def start_selenium():
    global driver
    global selenium_started

    #Hide selenium browser entirely
    os.environ['MOZ_HEADLESS'] = '1'

    #Start selenium
    driver = webdriver.Firefox()
    selenium_started = True

    
#Start Selenium
thread1 = threading.Thread(target = start_selenium)
thread1.start()
#Run the ui in a seperate thread so you don't have to wait for a file to download to input a new one
thread2 = threading.Thread(target = user_interface)
thread2.start()

#Get the download
search_query = ''
working_track = 0
while True:

    working_track += 1
    #Wait for selenium to start
    while selenium_started == 0:
        time.sleep(0.2)
    #Wait for user input
    while(queued_items == 0 and quit_signal == 0):
        time.sleep(0.2)

    #Exit loop after queue is finished and quit signal has been sent
    if quit_signal > 0 and queued_items == 0:
        if quit_signal == 3:
            exit()
        break
    
    #Search Youtube for requested song
    search_query = 'https://www.youtube.com/results?search_query=' + track_name[working_track] + '+' + artist + '+' + album
    search_results = requests.get(search_query).text

    #Search Youtube page for video links
    search_results = re.findall(r'watch\?v=(\S{11})(?=["])', search_results)

    #Check length of track and select search result
    chosen_link = 0
    while chosen_link < len(search_results):
        search_results[chosen_link] = search_results[chosen_link].replace('watch\?v=', '')

        track_length = requests.get('https://www.googleapis.com/youtube/v3/videos?id=' + search_results[chosen_link] + '&part=contentDetails&key=' + yt_api_key).text
        track_length = re.findall(r'(?<="duration": "PT).*?(?=")', track_length)
        track_length = re.findall(r'([0-9][0-9]|[0-9])', str(track_length))
        if len(track_length) == 2 and int(track_length[0]) < 15:
            chosen_link = 'https://www.youtube.com/watch\?v=' + search_results[chosen_link]
            break
        chosen_link += 1

    #Open yt downloader website in selenium
    driver.get('https://yt1s.com/en409/youtube-to-mp3')

    #Send youtube link to downloader website
    element = driver.find_element(By.ID, 's_input')
    element.send_keys(chosen_link, Keys.ENTER)

    #Wait until download button appears and click it
    try:
        element = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, 'btn-action'))
        )
    except:
        driver.save_screenshot('debug.png')
        print('FAILED. Check debug screenshot')
        exit()
    get_link_button = driver.find_element(By.ID, 'btn-action')
    get_link_button.click()

    #Wait until download button element appears 
    element = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, 'asuccess'))
    )

    #Wait for download button element to contain the download link and then save the download link
    wait_time = 0
    correct_link = 0
    while wait_time < 30 and correct_link == 0:
        time.sleep(1)
        wait_time += 1
        download_link = driver.find_element(By.ID, 'asuccess')
        download_link = download_link.get_attribute('href')
        correct_link = download_link.count('y2mate.com/?file')

    #Create a file name for the track
    file_name = track_name[working_track] + ' - ' + artist

    #Remove 's' from 'https' so that the script works. Don't ask me why, I don't know, but it works
    download_link = download_link.replace('https', 'http')

    #Stream the file into buffer
    download_buffer = requests.get(download_link, stream = True)

    #Make sure download directory exists
    try:
        os.makedirs(download_dir)
    except:
        #I know this is bad practice but for now I'm too lazy to care
        pass

    #Save buffer to file
    with open(download_dir + file_name + '.mp3', 'wb') as file:
        for chunk in download_buffer.iter_content(chunk_size = 1024*1024):
            if chunk:
                file.write(chunk)

    #Add tags to mp3 files
    mp3file = MP3(download_dir + file_name + '.mp3', ID3=EasyID3)
    mp3file['title'] = [track_name[working_track]]
    mp3file['albumartist'] = [artist]
    mp3file['artist'] = [artist]
    mp3file['album'] = [album]
    mp3file['tracknumber'] = [str(track_number)]
    mp3file['date'] = [release_date]
    mp3file.save() 
    
    #Move on to the next item in queue
    queued_items -= 1

#Close out program
print ('Saving...')
driver.quit()
os.remove('geckodriver.log')